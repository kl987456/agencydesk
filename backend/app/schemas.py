from datetime import date
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from .models import ApprovalStatus, Priority, TaskStatus


class LoginIn(BaseModel):
    email: str
    password: str
    agency_id: UUID | None = None


class LoginOut(BaseModel):
    token: str
    identity_id: UUID
    memberships: list[dict]
    active_agency_id: UUID


class AgencySwitchIn(BaseModel):
    agency_id: UUID


class ProjectIn(BaseModel):
    name: str
    client_id: UUID
    description: str = ""


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    client_id: UUID
    description: str


class TaskIn(BaseModel):
    title: str
    description: str = ""
    status: TaskStatus = TaskStatus.todo
    priority: Priority = Priority.medium
    due_date: date | None = None
    is_client_visible: bool = False
    assignee_membership_id: UUID | None = None


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    project_id: UUID
    title: str
    description: str
    status: TaskStatus
    priority: Priority
    due_date: date | None
    is_client_visible: bool


class CommentIn(BaseModel):
    body: str = Field(min_length=1)
    is_client_visible: bool = True


class TimeIn(BaseModel):
    minutes: int = Field(gt=0)
    note: str = ""
    work_date: date


class InviteIn(BaseModel):
    email: str
    client_id: UUID


class AcceptInviteIn(BaseModel):
    token: str
    display_name: str
    password: str = Field(min_length=8)


class AttachmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    external_token: str
    original_name: str
    is_client_visible: bool
    approval_status: ApprovalStatus
