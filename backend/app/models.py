from typing import Any
from pydantic import BaseModel, Field, HttpUrl, EmailStr


# ---- Auth ----
class RegisterRequest(BaseModel):
    email: str = Field(min_length=5, max_length=200)
    password: str = Field(min_length=6, max_length=200)
    full_name: str = Field(default="", max_length=200)

class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=200)
    password: str = Field(min_length=1, max_length=200)

class OnboardingData(BaseModel):
    """Bulk profile data submitted during onboarding or profile update."""
    fields: dict[str, str] = Field(default_factory=dict)
    category: str = Field(default="general", max_length=50)


# ---- Workflow ----
class CreateWorkflowRequest(BaseModel):
    goal: str = Field(min_length=3, max_length=2000)

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    workflow_id: str | None = None

class OTPRequest(BaseModel):
    otp: str = Field(min_length=4, max_length=12)

class CredentialsRequest(BaseModel):
    username: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=1, max_length=200)
    action_type: str = Field(default="login", max_length=30)

class ApprovalRequest(BaseModel):
    approved: bool = True
    overrides: dict[str, Any] = Field(default_factory=dict)

class ActionChoiceRequest(BaseModel):
    action: str = Field(min_length=1, max_length=100)

class PortalConfirmRequest(BaseModel):
    url: HttpUrl

class HumanConfirmationRequest(BaseModel):
    confirmed: bool
    note: str = Field(default="", max_length=500)


# ---- Browser ----
class BrowserOpenRequest(BaseModel):
    workflow_id: str = Field(min_length=1, max_length=100)
    url: HttpUrl

class BrowserInspectRequest(BaseModel):
    workflow_id: str = Field(min_length=1, max_length=100)

class BrowserSuggestRequest(BaseModel):
    workflow_id: str = Field(min_length=1, max_length=100)
    profile: dict[str, Any] = Field(default_factory=dict)

class ApprovedFieldMapping(BaseModel):
    field_index: int = Field(ge=0)
    value: str = Field(max_length=2000)
    profile_key: str = Field(default="", max_length=100)
    expected_label: str = Field(default="", max_length=300)

class BrowserFillRequest(BaseModel):
    workflow_id: str = Field(min_length=1, max_length=100)
    approved_mappings: list[ApprovedFieldMapping] = Field(default_factory=list, max_length=100)
