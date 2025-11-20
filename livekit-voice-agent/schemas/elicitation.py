"""
Elicitation Schemas for Payment Authorization
==============================================
Defines schemas for elicitation requests, responses, and state management.
"""

from enum import Enum
from typing import Optional, Dict, Any, List, Literal
from pydantic import BaseModel, Field
from datetime import datetime


class ElicitationType(str, Enum):
    """Types of elicitation requests."""
    OTP = "otp"
    CONFIRMATION = "confirmation"
    BIOMETRIC = "biometric"
    FORM = "form"
    SUPERVISOR_APPROVAL = "supervisor_approval"


class ElicitationStatus(str, Enum):
    """Elicitation lifecycle states."""
    CREATED = "created"
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    EXPIRED = "expired"
    FAILED = "failed"
    CANCELLED = "cancelled"


class FieldValidation(BaseModel):
    """Validation rules for form fields."""
    required: bool = True
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None  # Regex pattern
    min_value: Optional[float] = None
    max_value: Optional[float] = None


class ElicitationField(BaseModel):
    """Schema definition for an elicitation field."""
    name: str = Field(..., description="Field name/identifier")
    label: str = Field(..., description="Human-readable label")
    field_type: Literal["text", "number", "otp", "boolean", "select", "biometric"] = Field(..., description="Field type")
    validation: FieldValidation = Field(default_factory=FieldValidation)
    placeholder: Optional[str] = None
    help_text: Optional[str] = None
    options: Optional[List[str]] = None  # For select fields


class PlatformRequirements(BaseModel):
    """Platform-specific requirements for elicitation."""
    web: Dict[str, bool] = Field(default_factory=dict)  # e.g., {"biometric_required": False}
    mobile: Dict[str, bool] = Field(default_factory=dict)  # e.g., {"biometric_required": True}


class ElicitationContext(BaseModel):
    """Context information displayed to user during elicitation."""
    amount: str = Field(..., description="Masked amount (e.g., '₹1,000.00')")
    payee: str = Field(..., description="Masked payee name")
    account: str = Field(..., description="Masked account number")
    description: Optional[str] = None
    additional_info: Optional[Dict[str, Any]] = None


class ElicitationSchema(BaseModel):
    """Complete elicitation schema sent to client."""
    elicitation_id: str = Field(..., description="Unique elicitation identifier (UUID)")
    elicitation_type: ElicitationType = Field(..., description="Type of elicitation")
    fields: List[ElicitationField] = Field(..., description="Fields to collect")
    context: ElicitationContext = Field(..., description="Payment context for display")
    platform_requirements: PlatformRequirements = Field(default_factory=PlatformRequirements)
    timeout_seconds: int = Field(default=300, description="Timeout in seconds (5 minutes default)")
    ui_hints: Optional[Dict[str, Any]] = None  # Additional UI rendering hints


class ElicitationRequest(BaseModel):
    """Elicitation request message sent to client via data channel."""
    type: Literal["elicitation"] = "elicitation"
    elicitation_id: str
    tool_call_id: str = Field(..., description="ID of the suspended tool call")
    schema: ElicitationSchema


class ElicitationResponse(BaseModel):
    """Elicitation response from client."""
    type: Literal["elicitation_response"] = "elicitation_response"
    elicitation_id: str
    user_input: Dict[str, Any] = Field(..., description="User-provided values")
    biometric_token: Optional[str] = None  # For mobile biometric auth
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ElicitationState(BaseModel):
    """Elicitation state stored in Redis."""
    elicitation_id: str
    tool_call_id: str
    mcp_endpoint: str  # Which MCP tool/endpoint created this
    user_id: str
    session_id: str
    room_name: str
    status: ElicitationStatus
    schema: ElicitationSchema
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime
    suspended_tool_arguments: Dict[str, Any] = Field(default_factory=dict)  # Arguments to resume tool with


class ElicitationCancellation(BaseModel):
    """Elicitation cancellation message."""
    type: Literal["elicitation_cancelled"] = "elicitation_cancelled"
    elicitation_id: str
    reason: str = Field(default="Cancelled by system")


class ElicitationExpiration(BaseModel):
    """Elicitation expiration message."""
    type: Literal["elicitation_expired"] = "elicitation_expired"
    elicitation_id: str
    message: str = Field(default="Elicitation has expired. Please try again.")


# Helper functions for creating common elicitation schemas

def create_otp_elicitation(
    elicitation_id: str,
    context: ElicitationContext,
    platform: str = "web"
) -> ElicitationSchema:
    """Create OTP elicitation schema."""
    return ElicitationSchema(
        elicitation_id=elicitation_id,
        elicitation_type=ElicitationType.OTP,
        fields=[
            ElicitationField(
                name="otp_code",
                label="Enter OTP",
                field_type="otp",
                validation=FieldValidation(
                    required=True,
                    min_length=6,
                    max_length=6,
                    pattern=r"^\d{6}$"
                ),
                placeholder="000000",
                help_text="Enter the 6-digit OTP sent to your registered mobile number"
            )
        ],
        context=context,
        platform_requirements=PlatformRequirements(
            web={"biometric_required": False},
            mobile={"biometric_required": True}  # Mobile requires biometric before OTP
        )
    )


def create_confirmation_elicitation(
    elicitation_id: str,
    context: ElicitationContext,
    platform: str = "web"
) -> ElicitationSchema:
    """Create simple confirmation elicitation schema."""
    return ElicitationSchema(
        elicitation_id=elicitation_id,
        elicitation_type=ElicitationType.CONFIRMATION,
        fields=[
            ElicitationField(
                name="confirmed",
                label="Confirm Payment",
                field_type="boolean",
                validation=FieldValidation(required=True),
                help_text="Please confirm that you want to proceed with this payment"
            )
        ],
        context=context,
        platform_requirements=PlatformRequirements(
            web={"biometric_required": False},
            mobile={"biometric_required": True}
        )
    )


def create_supervisor_approval_elicitation(
    elicitation_id: str,
    context: ElicitationContext
) -> ElicitationSchema:
    """Create supervisor approval elicitation schema."""
    return ElicitationSchema(
        elicitation_id=elicitation_id,
        elicitation_type=ElicitationType.SUPERVISOR_APPROVAL,
        fields=[
            ElicitationField(
                name="supervisor_id",
                label="Supervisor ID",
                field_type="text",
                validation=FieldValidation(required=True),
                help_text="Enter your supervisor's employee ID"
            ),
            ElicitationField(
                name="approval_code",
                label="Approval Code",
                field_type="text",
                validation=FieldValidation(
                    required=True,
                    min_length=8,
                    max_length=20
                ),
                help_text="Enter the approval code provided by your supervisor"
            )
        ],
        context=context,
        platform_requirements=PlatformRequirements(
            web={"biometric_required": False},
            mobile={"biometric_required": False}
        ),
        timeout_seconds=600  # 10 minutes for supervisor approval
    )

