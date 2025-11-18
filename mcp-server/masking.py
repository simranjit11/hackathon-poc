"""
Data Masking Utilities
=======================
Masks sensitive information before returning to orchestrator.
"""

import re


def mask_account_number(account_number: str) -> str:
    """
    Mask account number, showing only last 4 digits.
    
    Args:
        account_number: Full account number
        
    Returns:
        Masked account number (e.g., ****1234)
    """
    if not account_number:
        return "****"
    
    # Extract last 4 digits
    last_four = account_number[-4:] if len(account_number) >= 4 else account_number
    
    return f"****{last_four}"


def mask_merchant_info(description: str) -> str:
    """
    Mask sensitive merchant information in transaction descriptions.
    
    Args:
        description: Transaction description
        
    Returns:
        Masked description
    """
    if not description:
        return ""
    
    # For now, return as-is. In production, this would mask
    # specific merchant names or locations based on policy.
    # Example: "Grocery Store" -> "Merchant ****"
    
    return description


def mask_for_logging(data: dict) -> dict:
    """
    Mask sensitive data for logging purposes.
    
    Args:
        data: Dictionary containing potentially sensitive data
        
    Returns:
        Dictionary with masked values
    """
    masked = data.copy()
    
    # Mask account numbers
    for key in ["account_number", "loan_account_number", "from_account", "to_account"]:
        if key in masked and isinstance(masked[key], str):
            masked[key] = mask_account_number(masked[key])
    
    # Mask amounts (optional - may want to show in logs)
    # for key in ["amount", "balance"]:
    #     if key in masked:
    #         masked[key] = "***"
    
    return masked

