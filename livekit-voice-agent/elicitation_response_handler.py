"""
Elicitation Response Handler
=============================
Handles elicitation responses from clients and resumes payment execution.
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import httpx

from elicitation_manager import get_elicitation_manager, ElicitationStatus

logger = logging.getLogger(__name__)


class ElicitationResponseHandler:
    """Handles elicitation responses and payment resumption."""

    def __init__(self, next_js_base_url: str = "http://localhost:3000"):
        """
        Initialize response handler.
        
        Args:
            next_js_base_url: Base URL for Next.js API endpoints
        """
        self.manager = get_elicitation_manager()
        self.next_js_base_url = next_js_base_url
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

            # Step 5: Call Next.js resume endpoint
            logger.info(f"Calling resume endpoint for {elicitation_id}")
            result = await self._call_resume_endpoint(
                elicitation_id,
                state.tool_call_id,
                user_input,
                state.suspended_tool_arguments,
                biometric_token
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

    async def _call_resume_endpoint(
        self,
        elicitation_id: str,
        tool_call_id: str,
        user_input: Dict[str, Any],
        suspended_arguments: Dict[str, Any],
        biometric_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Call Next.js resume endpoint to complete payment.
        
        Args:
            elicitation_id: Elicitation identifier
            tool_call_id: Tool call ID
            user_input: User-provided values
            suspended_arguments: Original payment arguments
            biometric_token: Optional biometric token
            
        Returns:
            Resume endpoint response
        """
        url = f"{self.next_js_base_url}/api/elicitation/resume"
        
        payload = {
            "elicitation_id": elicitation_id,
            "tool_call_id": tool_call_id,
            "user_input": user_input,
            "suspended_arguments": suspended_arguments,
        }
        
        if biometric_token:
            payload["biometric_token"] = biometric_token

        try:
            response = await self.http_client.post(url, json=payload)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Resume endpoint response: {result.get('status')}")
            
            return result
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error calling resume endpoint: {e.response.status_code}")
            try:
                error_detail = e.response.json()
                return {
                    "status": "failed",
                    "error": error_detail.get("error", "Resume endpoint failed")
                }
            except Exception:
                return {
                    "status": "failed",
                    "error": f"HTTP {e.response.status_code}: {e.response.text}"
                }
        except httpx.HTTPError as e:
            logger.error(f"Network error calling resume endpoint: {e}")
            return {
                "status": "failed",
                "error": "Network error contacting payment service"
            }
        except Exception as e:
            logger.error(f"Unexpected error calling resume endpoint: {e}")
            return {
                "status": "failed",
                "error": f"Unexpected error: {str(e)}"
            }

    async def close(self):
        """Close HTTP client."""
        await self.http_client.aclose()


# Global response handler instance
_response_handler: Optional[ElicitationResponseHandler] = None


def get_response_handler(next_js_base_url: str = "http://localhost:3000") -> ElicitationResponseHandler:
    """Get or create the global response handler instance."""
    global _response_handler
    if _response_handler is None:
        _response_handler = ElicitationResponseHandler(next_js_base_url)
    return _response_handler

