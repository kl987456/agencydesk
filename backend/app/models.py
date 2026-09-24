import enum
import uuid
from datetime import date, datetime
from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, ForeignKeyConstraint, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base


class Role(str, enum.Enum):
    agency_admin = "agency_admin"
    agency_member = "agency_member"
    client_user = "client_user"


class InviteStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    expired = "expired"


class TaskStatus(str, enum.Enum):
    todo = "todo"
    in_progress = "in_progress"
    review = "review"
    done = "done"


class Priority(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"


class ApprovalStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    needs_changes = "needs_changes"


class Agency(Base):
    __tablename__ = "agencies"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    memberships = relationship("Membership", back_populates="agency")
    clients = relationship("Client", back_populates="agency")


class Identity(Base):
    __tablename__ = "identities"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    memberships = relationship("Membership", back_populates="identity", cascade="all, delete-orphan")


class Membership(Base):
    __tablename__ = "memberships"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    identity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("identities.id", ondelete="CASCADE"), nullable=False)
    agency_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[Role] = mapped_column(String(32), nullable=False)
    client_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    __table_args__ = (UniqueConstraint("identity_id", "agency_id", name="uq_membership_identity_agency"), Index("ix_membership_agency_identity", "agency_id", "identity_id"))
    identity = relationship("Identity", back_populates="memberships")
    agency = relationship("Agency", back_populates="memberships")


class Client(Base):
    __tablename__ = "clients"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    agency_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    agency = relationship("Agency", back_populates="clients")
    projects = relationship("Project", back_populates="client")
    __table_args__ = (UniqueConstraint("agency_id", "id", name="uq_client_agency_id"), Index("ix_client_agency", "agency_id"))


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    agency_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    client_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    __table_args__ = (ForeignKeyConstraint(["agency_id", "client_id"], ["clients.agency_id", "clients.id"], name="fk_project_client_same_agency", ondelete="CASCADE"), UniqueConstraint("agency_id", "id", name="uq_project_agency_id"), Index("ix_project_agency_client", "agency_id", "client_id"))
    client = relationship("Client", back_populates="projects")
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")
    assignments = relationship("ProjectAssignment", back_populates="project", cascade="all, delete-orphan")


class ProjectAssignment(Base):
    __tablename__ = "project_assignments"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    agency_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    membership_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("memberships.id", ondelete="CASCADE"), nullable=False)
    __table_args__ = (ForeignKeyConstraint(["agency_id", "project_id"], ["projects.agency_id", "projects.id"], name="fk_assignment_project_same_agency", ondelete="CASCADE"), UniqueConstraint("project_id", "membership_id", name="uq_project_assignment"), Index("ix_assignment_membership", "membership_id"))
    project = relationship("Project", back_populates="assignments")


class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    agency_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    assignee_membership_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("memberships.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[TaskStatus] = mapped_column(String(32), default=TaskStatus.todo, nullable=False)
    priority: Mapped[Priority] = mapped_column(String(32), default=Priority.medium, nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_client_visible: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    __table_args__ = (ForeignKeyConstraint(["agency_id", "project_id"], ["projects.agency_id", "projects.id"], name="fk_task_project_same_agency", ondelete="CASCADE"), Index("ix_task_agency_project_visibility", "agency_id", "project_id", "is_client_visible"), Index("ix_task_agency_status", "agency_id", "status"))
    project = relationship("Project", back_populates="tasks")
    comments = relationship("Comment", back_populates="task", cascade="all, delete-orphan")
    time_entries = relationship("TimeEntry", back_populates="task", cascade="all, delete-orphan")
    attachments = relationship("FileAttachment", back_populates="task", cascade="all, delete-orphan")


class Comment(Base):
    __tablename__ = "comments"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    agency_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    task_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    author_identity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("identities.id"), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_client_visible: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    __table_args__ = (ForeignKeyConstraint(["agency_id", "task_id"], ["tasks.agency_id", "tasks.id"], name="fk_comment_task_same_agency", ondelete="CASCADE"), Index("ix_comment_task_visibility", "agency_id", "task_id", "is_client_visible"))
    task = relationship("Task", back_populates="comments")


class TimeEntry(Base):
    __tablename__ = "time_entries"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    agency_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    task_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    identity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("identities.id"), nullable=False)
    minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    work_date: Mapped[date] = mapped_column(Date, nullable=False)
    __table_args__ = (ForeignKeyConstraint(["agency_id", "task_id"], ["tasks.agency_id", "tasks.id"], name="fk_time_task_same_agency", ondelete="CASCADE"), CheckConstraint("minutes > 0", name="ck_time_positive"), Index("ix_time_task", "agency_id", "task_id"))
    task = relationship("Task", back_populates="time_entries")


class FileAttachment(Base):
    __tablename__ = "file_attachments"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    agency_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    task_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    external_token: Mapped[str] = mapped_column(String(64), unique=True, default=lambda: uuid.uuid4().hex + uuid.uuid4().hex[:16], nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    is_client_visible: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    approval_status: Mapped[ApprovalStatus] = mapped_column(String(32), default=ApprovalStatus.pending, nullable=False)
    __table_args__ = (ForeignKeyConstraint(["agency_id", "task_id"], ["tasks.agency_id", "tasks.id"], name="fk_attachment_task_same_agency", ondelete="CASCADE"), Index("ix_attachment_task_visibility", "agency_id", "task_id", "is_client_visible"))
    task = relationship("Task", back_populates="attachments")


class Invite(Base):
    __tablename__ = "invites"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    agency_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False)
    client_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    token: Mapped[str] = mapped_column(String(64), unique=True, default=lambda: uuid.uuid4().hex, nullable=False)
    status: Mapped[InviteStatus] = mapped_column(String(32), default=InviteStatus.pending, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    __table_args__ = (ForeignKeyConstraint(["agency_id", "client_id"], ["clients.agency_id", "clients.id"], name="fk_invite_client_same_agency", ondelete="CASCADE"), Index("ix_invite_pending_agency_email", "agency_id", "email", unique=True, sqlite_where=(status == "pending"), postgresql_where=(status == "pending")))


class Lead(Base):
    __tablename__ = "leads"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    agency_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False)
    client_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    email: Mapped[str] = mapped_column(String(320), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="new", nullable=False)
    __table_args__ = (Index("ix_lead_agency_status", "agency_id", "status"),)


class Deal(Base):
    __tablename__ = "deals"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    agency_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False)
    client_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    value_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="open", nullable=False)
    __table_args__ = (CheckConstraint("value_cents >= 0", name="ck_deal_value_nonnegative"), Index("ix_deal_agency_status", "agency_id", "status"))


class Contract(Base):
    __tablename__ = "contracts"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    agency_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False)
    client_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    starts_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    ends_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    __table_args__ = (Index("ix_contract_agency_status", "agency_id", "status"),)


class IntakeForm(Base):
    __tablename__ = "intake_forms"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    agency_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False)
    client_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    fields_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    __table_args__ = (Index("ix_intake_agency_active", "agency_id", "is_active"),)


class IntakeResponse(Base):
    __tablename__ = "intake_responses"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    agency_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False)
    form_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("intake_forms.id", ondelete="CASCADE"), nullable=False)
    client_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    submitted_by_identity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("identities.id"), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    __table_args__ = (Index("ix_intake_response_agency_form", "agency_id", "form_id"),)


class Automation(Base):
    __tablename__ = "automations"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    agency_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    __table_args__ = (Index("ix_automation_agency_active", "agency_id", "active"),)


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    agency_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False)
    identity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("identities.id", ondelete="CASCADE"), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    __table_args__ = (Index("ix_notification_identity_unread", "agency_id", "identity_id", "read"),)
