"""
Data models for MCP Server.
"""

from typing import Optional, List, Literal
from pydantic import BaseModel, Field
from datetime import datetime


class BalanceResponse(BaseModel):
    """Balance response model."""
    account_type: str = Field(..., description="Account type (checking, savings, credit_card)")
    account_number: str = Field(..., description="Masked account number (****1234)")
    balance: float = Field(..., description="Account balance")
    currency: str = Field(default="USD", description="Currency code")
    credit_limit: Optional[float] = Field(None, description="Credit limit (for credit cards)")
    available_credit: Optional[float] = Field(None, description="Available credit (for credit cards)")


class BalanceRequest(BaseModel):
    """Balance request model."""
    account_type: Optional[str] = Field(None, description="Specific account type to query (optional)")


class TransactionResponse(BaseModel):
    """Transaction response model."""
    date: str = Field(..., description="Transaction date (YYYY-MM-DD)")
    description: str = Field(..., description="Transaction description (masked)")
    amount: float = Field(..., description="Transaction amount (negative for debits)")
    type: Literal["debit", "credit", "transfer", "payment"] = Field(..., description="Transaction type")
    account_number: str = Field(..., description="Masked account number")


class TransactionsRequest(BaseModel):
    """Transactions request model."""
    account_type: Optional[str] = Field(None, description="Account type filter")
    start_date: Optional[str] = Field(None, description="Start date (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="End date (YYYY-MM-DD)")
    limit: int = Field(default=10, ge=1, le=100, description="Maximum number of transactions")


class LoanResponse(BaseModel):
    """Loan response model."""
    loan_type: str = Field(..., description="Type of loan")
    loan_account_number: str = Field(..., description="Masked loan account number")
    balance: float = Field(..., description="Outstanding loan balance")
    interest_rate: float = Field(..., description="Annual interest rate (%)")
    monthly_payment: float = Field(..., description="Monthly payment amount")
    remaining_term_months: Optional[int] = Field(None, description="Remaining term in months")
    next_payment_date: Optional[str] = Field(None, description="Next payment date (YYYY-MM-DD)")


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str = Field(..., description="Error message")
    status_code: int = Field(..., description="HTTP status code")
    detail: Optional[str] = Field(None, description="Additional error details")

