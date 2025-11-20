"""
Payment Tool with Elicitation Support
======================================
Mock payment tool that returns elicitation request for testing the elicitation flow.
This tool simulates the elicitation trigger from MCP server.
"""

import uuid
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def create_payment_elicitation_response(
    user_id: str,
    from_account: str,
    to_account: str,
    amount: float,
    description: str = "",
    tool_call_id: str = None,
    platform: str = "web"
) -> Dict[str, Any]:
    """
    Create elicitation response for payment confirmation.
    
    This simulates an MCP tool returning an elicitation requirement
    instead of immediately processing the payment.
    
    Args:
        user_id: User identifier
        from_account: Source account
        to_account: Destination account
        amount: Payment amount
        description: Payment description
        tool_call_id: Tool call ID for tracking
        platform: Platform type (web/mobile)
        
    Returns:
        Elicitation response dict
    """
    elicitation_id = str(uuid.uuid4())
    
    # Determine elicitation type based on amount
    # High value transactions require OTP
    requires_otp = amount >= 1000.0
    
    # Create masked context for display
    context = {
        "amount": f"₹{amount:,.2f}",
        "payee": _mask_payee(to_account),
        "account": _mask_account(from_account),
        "description": description or "Payment transfer"
    }
    
    # Build elicitation schema
    if requires_otp:
        schema = {
            "elicitation_id": elicitation_id,
            "elicitation_type": "otp",
            "fields": [
                {
                    "name": "otp_code",
                    "label": "Enter OTP",
                    "field_type": "otp",
                    "validation": {
                        "required": True,
                        "min_length": 6,
                        "max_length": 6,
                        "pattern": r"^\d{6}$"
                    },
                    "placeholder": "000000",
                    "help_text": "Enter the 6-digit OTP sent to your registered mobile number"
                }
            ],
            "context": context,
            "platform_requirements": {
                "web": {"biometric_required": False},
                "mobile": {"biometric_required": True}
            },
            "timeout_seconds": 300
        }
    else:
        # Simple confirmation for lower amounts
        schema = {
            "elicitation_id": elicitation_id,
            "elicitation_type": "confirmation",
            "fields": [
                {
                    "name": "confirmed",
                    "label": "Confirm Payment",
                    "field_type": "boolean",
                    "validation": {"required": True},
                    "help_text": "Please confirm that you want to proceed with this payment"
                }
            ],
            "context": context,
            "platform_requirements": {
                "web": {"biometric_required": False},
                "mobile": {"biometric_required": True}
            },
            "timeout_seconds": 300
        }
    
    # Return elicitation response
    # This signals to the orchestrator that elicitation is required
    response = {
        "status": "elicitation_required",
        "elicitation_id": elicitation_id,
        "tool_call_id": tool_call_id or str(uuid.uuid4()),
        "schema": schema,
        "suspended_arguments": {
            "user_id": user_id,
            "from_account": from_account,
            "to_account": to_account,
            "amount": amount,
            "description": description
        }
    }
    
    logger.info(
        f"Created elicitation {elicitation_id} for payment: "
        f"user={user_id}, amount={amount}, type={schema['elicitation_type']}"
    )
    
    return response


def _mask_payee(account: str) -> str:
    """Mask payee account number for display."""
    if not account:
        return "Unknown"
    
    # If it's a name, return as is
    if not account.replace(" ", "").isdigit():
        return account
    
    # If it's an account number, mask middle digits
    if len(account) > 4:
        return f"****{account[-4:]}"
    
    return account


def _mask_account(account: str) -> str:
    """Mask source account for display."""
    if not account:
        return "Unknown"
    
    # For account types like 'checking', 'savings'
    if account.lower() in ["checking", "savings", "credit"]:
        return account.capitalize()
    
    # For account numbers, mask middle
    if len(account) > 4:
        return f"****{account[-4:]}"
    
    return account


def validate_elicitation_response(
    user_input: Dict[str, Any],
    elicitation_type: str
) -> tuple[bool, str]:
    """
    Validate user input from elicitation response.
    
    Args:
        user_input: User-provided input values
        elicitation_type: Type of elicitation
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if elicitation_type == "otp":
        otp_code = user_input.get("otp_code", "")
        
        # Mock OTP validation (in production, verify with actual OTP service)
        # For testing, accept "123456" as valid OTP
        if otp_code == "123456":
            return True, ""
        else:
            return False, "Invalid OTP code. Please try again."
    
    elif elicitation_type == "confirmation":
        confirmed = user_input.get("confirmed", False)
        
        if confirmed:
            return True, ""
        else:
            return False, "Payment confirmation denied"
    
    elif elicitation_type == "supervisor_approval":
        supervisor_id = user_input.get("supervisor_id", "")
        approval_code = user_input.get("approval_code", "")
        
        # Mock validation
        if supervisor_id and approval_code:
            return True, ""
        else:
            return False, "Invalid supervisor approval"
    
    return False, "Unknown elicitation type"


def complete_payment_after_elicitation(
    suspended_arguments: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Complete payment after successful elicitation validation.
    
    This is a mock implementation that returns a successful payment confirmation.
    In production, this would call the actual Cashfree UPI SDK.
    
    Args:
        suspended_arguments: Original payment arguments
        
    Returns:
        Payment confirmation dict
    """
    confirmation_number = f"TXN{uuid.uuid4().hex[:12].upper()}"
    
    result = {
        "status": "completed",
        "confirmation_number": confirmation_number,
        "from_account": suspended_arguments.get("from_account"),
        "to_account": suspended_arguments.get("to_account"),
        "amount": suspended_arguments.get("amount"),
        "description": suspended_arguments.get("description", ""),
        "timestamp": "2024-01-01T12:00:00Z",  # Mock timestamp
        "message": "Payment processed successfully"
    }
    
    logger.info(
        f"Completed payment: confirmation={confirmation_number}, "
        f"amount={suspended_arguments.get('amount')}"
    )
    
    return result

