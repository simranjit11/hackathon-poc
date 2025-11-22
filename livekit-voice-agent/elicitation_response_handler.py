"""
Elicitation Response Handler
=============================
Handles elicitation responses from clients and resumes payment execution.
This handler receives OTP/confirmation from the frontend and calls the MCP server's
confirm_payment tool to complete the transaction.
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import httpx

from elicitation_manager import get_elicitation_manager, ElicitationStatus
from mcp_client import get_mcp_client

logger = logging.getLogger(__name__)


class ElicitationResponseHandler:
    """Handles elicitation responses and payment resumption via MCP tools."""

    def __init__(self):
        """Initialize response handler with MCP client."""
        self.manager = get_elicitation_manager()
        self.mcp_client = get_mcp_client()
        self.http_client = httpx.AsyncClient(timeout=30.0)

    async def handle_response(
        self,
        elicitation_id: str,
        user_input: Dict[str, Any],
        biometric_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Handle elicitation response from client.
        
        Args:
            elicitation_id: Elicitation identifier
            user_input: User-provided input values
            biometric_token: Optional biometric token from mobile
            
        Returns:
            Dict with status and result/error
        """
        logger.info(f"Handling elicitation response for {elicitation_id}")

        try:
            # Step 1: Retrieve elicitation state from Redis
            state = self.manager.get_elicitation(elicitation_id)
            if not state:
                logger.error(f"Elicitation {elicitation_id} not found in Redis")
                return {
                    "status": "error",
                    "error": "Elicitation not found or has expired"
                }

            # Step 2: Validate elicitation status
            if state.status != ElicitationStatus.PENDING:
                logger.error(
                    f"Elicitation {elicitation_id} has invalid status: {state.status}"
                )
                return {
                    "status": "error",
                    "error": f"Elicitation is {state.status.value}, cannot process"
                }

            # Step 3: Check if expired
            if datetime.utcnow() > state.expires_at:
                logger.error(f"Elicitation {elicitation_id} has expired")
                self.manager.mark_expired(elicitation_id)
                return {
                    "status": "error",
                    "error": "Elicitation has expired. Please try again."
                }

            # Step 4: Update status to processing
            self.manager.update_elicitation_status(
                elicitation_id,
                ElicitationStatus.PROCESSING
            )

            # Step 5: Call MCP confirm_payment tool
            logger.info(f"Calling MCP confirm_payment for {elicitation_id}")
            result = await self._call_confirm_payment(
                elicitation_id,
                user_input,
                state.suspended_tool_arguments
            )

            if result["status"] == "completed":
                # Step 6: Mark as completed and clean up
                self.manager.update_elicitation_status(
                    elicitation_id,
                    ElicitationStatus.COMPLETED
                )
                self.manager.remove_from_queue(state.session_id, elicitation_id)
                
                logger.info(
                    f"Elicitation {elicitation_id} completed successfully: "
                    f"{result.get('payment_result', {}).get('confirmation_number')}"
                )
                
                return result
            else:
                # Step 7: Handle failure
                self.manager.update_elicitation_status(
                    elicitation_id,
                    ElicitationStatus.FAILED
                )
                
                logger.error(
                    f"Elicitation {elicitation_id} failed: {result.get('error')}"
                )
                
                return result

        except Exception as e:
            logger.error(f"Error handling elicitation response: {e}", exc_info=True)
            
            # Update status to failed
            try:
                self.manager.update_elicitation_status(
                    elicitation_id,
                    ElicitationStatus.FAILED
                )
            except Exception:
                pass
            
            return {
                "status": "error",
                "error": f"Internal error: {str(e)}"
            }

    async def _call_confirm_payment(
        self,
        elicitation_id: str,
        user_input: Dict[str, Any],
        suspended_arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Call MCP confirm_payment tool to complete the payment.
        
        Args:
            elicitation_id: Elicitation identifier (payment_session_id)
            user_input: User-provided values (must contain otp_code)
            suspended_arguments: Original payment arguments with user_id
            
        Returns:
            Payment confirmation result
        """
        try:
            # Extract user context from suspended arguments
            user_id = suspended_arguments.get("user_id")
            payment_session_id = suspended_arguments.get("payment_session_id", elicitation_id)
            
            if not user_id:
                logger.error("No user_id in suspended arguments")
                return {
                    "status": "failed",
                    "error": "Missing user context"
                }
            
            # Check if this is an OTP or confirmation type elicitation
            otp_code = user_input.get("otp_code")
            confirmed = user_input.get("confirmed")
            
            # Determine the OTP to use
            # For confirmation-only (no OTP field), use a dummy OTP since backend doesn't validate
            if otp_code:
                final_otp = otp_code
                logger.info(
                    f"Confirming payment with OTP via MCP: session={payment_session_id}, "
                    f"user={user_id}, otp={final_otp[:2]}***"
                )
            elif confirmed is True:
                # Simple confirmation for low-value transactions - use dummy OTP
                final_otp = "000000"
                logger.info(
                    f"Confirming payment with user confirmation via MCP: session={payment_session_id}, "
                    f"user={user_id}, using dummy OTP"
                )
            else:
                logger.error("No OTP code or confirmation provided in user input")
                return {
                    "status": "failed",
                    "error": "OTP code or confirmation is required"
                }
            
            # Call MCP confirm_payment tool with OTP
            logger.info(
                f"Calling MCP confirm_payment with: "
                f"payment_session_id={payment_session_id}, otp_code={final_otp}"
            )
            result = await self.mcp_client._call_mcp_tool(
                tool_name="confirm_payment",
                user_id=user_id,
                session_id="elicitation_handler",
                scopes=["transact"],
                payment_session_id=payment_session_id,
                otp_code=final_otp
            )
            
            logger.info(f"MCP confirm_payment result: {result}")
            
            # Transform MCP result to expected format
            if result and not result.get("isError"):
                # Extract the actual result from MCP content format
                content = result.get("content", [])
                if content and isinstance(content, list):
                    text_content = content[0].get("text", "{}")
                    try:
                        payment_data = json.loads(text_content)
                        return {
                            "status": "completed",
                            "payment_result": payment_data
                        }
                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse MCP result: {text_content}")
                        return {
                            "status": "failed",
                            "error": "Invalid response format from payment service"
                        }
                
                # Fallback: return raw result
                return {
                    "status": "completed",
                    "payment_result": result
                }
            else:
                # Payment failed
                error_msg = "Payment confirmation failed"
                if result and result.get("content"):
                    try:
                        error_msg = result["content"][0].get("text", error_msg)
                    except (KeyError, IndexError, TypeError):
                        pass
                
                return {
                    "status": "failed",
                    "error": error_msg
                }
            
        except Exception as e:
            logger.error(f"Error calling MCP confirm_payment: {e}", exc_info=True)
            return {
                "status": "failed",
                "error": f"Failed to confirm payment: {str(e)}"
            }

    async def close(self):
        """Close HTTP client."""
        await self.http_client.aclose()


# Global response handler instance
_response_handler: Optional[ElicitationResponseHandler] = None


def get_response_handler() -> ElicitationResponseHandler:
    """Get or create the global response handler instance."""
    global _response_handler
    if _response_handler is None:
        _response_handler = ElicitationResponseHandler()
    return _response_handler

