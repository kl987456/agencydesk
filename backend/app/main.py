import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session, selectinload
from .auth import AuthContext, create_session, get_auth_context, hash_password, rate_limit, verify_password, role_required
from .config import get_settings
from .db import Base, engine, get_db
from .models import Agency, ApprovalStatus, Automation, Client, Comment, Contract, Deal, FileAttachment, Identity, IntakeForm, IntakeResponse, Invite, InviteStatus, Lead, Membership, Notification, Project, ProjectAssignment, Role, Task, TaskStatus, TimeEntry
from .schemas import AcceptInviteIn, AgencySwitchIn, AttachmentOut, CommentIn, InviteIn, LoginIn, LoginOut, ProjectIn, ProjectOut, TaskIn, TaskOut, TimeIn

logging.basicConfig(level=logging.INFO, format='{"level":"%(levelname)s","message":"%(message)s"}')
log = logging.getLogger("agencydesk")
app = FastAPI(title="AgencyDesk API")
settings = get_settings()
app.add_middleware(CORSMiddleware, allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.middleware("http")
async def request_id_middleware(request, call_next):
    request.state.request_id = str(uuid.uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    return response


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/auth/login", response_model=LoginOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    rate_limit(f"login:{body.email.lower()}")
    identity = db.scalar(select(Identity).where(func.lower(Identity.email) == body.email.lower()))
    if not identity or not verify_password(body.password, identity.password_hash):
        raise HTTPException(401, "Invalid credentials")
    memberships = list(db.scalars(select(Membership).where(Membership.identity_id == identity.id, Membership.active.is_(True))))
    if not memberships:
        raise HTTPException(403, "No active memberships")
    active = next((m for m in memberships if body.agency_id and str(m.agency_id) == str(body.agency_id)), None) if body.agency_id else memberships[0]
    if not active:
        raise HTTPException(403, "Agency context is not available to this identity")
    return LoginOut(token=create_session(str(identity.id), str(active.agency_id)), identity_id=identity.id, memberships=[{"agency_id": str(m.agency_id), "role": m.role} for m in memberships], active_agency_id=active.agency_id)


@app.post("/auth/logout")
def logout(ctx: AuthContext = Depends(get_auth_context)):
    return {"status": "ok"}


@app.post("/auth/switch", response_model=LoginOut)
def switch_agency(body: AgencySwitchIn, ctx: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    membership = db.scalar(select(Membership).where(Membership.identity_id == ctx.identity.id, Membership.agency_id == body.agency_id, Membership.active.is_(True)))
    if not membership: raise HTTPException(403, "Agency context is not available to this identity")
    memberships = list(db.scalars(select(Membership).where(Membership.identity_id == ctx.identity.id, Membership.active.is_(True))))
    return LoginOut(token=create_session(str(ctx.identity.id), str(body.agency_id)), identity_id=ctx.identity.id, memberships=[{"agency_id": str(m.agency_id), "role": m.role} for m in memberships], active_agency_id=body.agency_id)


def scoped_project_query(ctx: AuthContext, db: Session):
    query = select(Project).where(Project.agency_id == ctx.agency_id)
    if ctx.membership.role == Role.agency_member:
        query = query.join(ProjectAssignment, ProjectAssignment.project_id == Project.id).where(ProjectAssignment.membership_id == ctx.membership.id)
    elif ctx.membership.role == Role.client_user:
        query = query.where(Project.client_id == ctx.membership.client_id)
    return query


def scoped_task_query(ctx: AuthContext, db: Session):
    query = select(Task).join(Project, Task.project_id == Project.id).where(Task.agency_id == ctx.agency_id)
    if ctx.membership.role == Role.agency_member:
        query = query.join(ProjectAssignment, ProjectAssignment.project_id == Project.id).where(ProjectAssignment.membership_id == ctx.membership.id)
    elif ctx.membership.role == Role.client_user:
        query = query.where(Project.client_id == ctx.membership.client_id, Task.is_client_visible.is_(True))
    return query


@app.get("/projects", response_model=list[ProjectOut])
def list_projects(ctx: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    return list(db.scalars(scoped_project_query(ctx, db)))


@app.post("/projects", response_model=ProjectOut)
def create_project(body: ProjectIn, ctx: AuthContext = Depends(role_required(Role.agency_admin)), db: Session = Depends(get_db)):
    client = db.scalar(select(Client).where(Client.id == body.client_id, Client.agency_id == ctx.agency_id))
    if not client:
        raise HTTPException(404, "Client not found")
    project = Project(agency_id=ctx.agency_id, client_id=client.id, name=body.name, description=body.description)
    db.add(project); db.commit(); db.refresh(project)
    return project


@app.get("/projects/{project_id}/tasks", response_model=list[TaskOut])
def list_tasks(project_id: uuid.UUID, q: str | None = Query(default=None), status: TaskStatus | None = None, ctx: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    query = scoped_task_query(ctx, db).where(Task.project_id == project_id).options(selectinload(Task.comments), selectinload(Task.attachments))
    if q: query = query.where(or_(Task.title.ilike(f"%{q}%"), Task.description.ilike(f"%{q}%")))
    if status: query = query.where(Task.status == status)
    return list(db.scalars(query))


@app.get("/projects/{project_id}/members")
def list_project_members(project_id: uuid.UUID, ctx: AuthContext = Depends(role_required(Role.agency_admin)), db: Session = Depends(get_db)):
    project = db.scalar(select(Project).where(Project.id == project_id, Project.agency_id == ctx.agency_id))
    if not project: raise HTTPException(404, "Project not found")
    rows = db.execute(select(ProjectAssignment.membership_id, Identity.display_name, Identity.email).join(Membership, ProjectAssignment.membership_id == Membership.id).join(Identity, Membership.identity_id == Identity.id).where(ProjectAssignment.project_id == project_id, ProjectAssignment.agency_id == ctx.agency_id)).all()
    return [{"membership_id": str(row.membership_id), "display_name": row.display_name, "email": row.email} for row in rows]


@app.post("/projects/{project_id}/tasks", response_model=TaskOut)
def create_task(project_id: uuid.UUID, body: TaskIn, ctx: AuthContext = Depends(role_required(Role.agency_admin, Role.agency_member)), db: Session = Depends(get_db)):
    project = db.scalar(scoped_project_query(ctx, db).where(Project.id == project_id))
    if not project: raise HTTPException(404, "Project not found")
    task = Task(agency_id=ctx.agency_id, project_id=project.id, **body.model_dump())
    db.add(task); db.commit(); db.refresh(task)
    rules = list(db.scalars(select(Automation).where(Automation.agency_id == ctx.agency_id, Automation.event_type == "task.created", Automation.action_type == "notify", Automation.active.is_(True))))
    if rules:
        recipients = list(db.scalars(select(Membership).where(Membership.agency_id == ctx.agency_id, Membership.active.is_(True), Membership.role.in_([Role.agency_admin, Role.agency_member]))))
        db.add_all([Notification(agency_id=ctx.agency_id, identity_id=membership.identity_id, message=f"Task created: {task.title}") for membership in recipients])
        db.commit()
    return task


@app.get("/tasks/{task_id}", response_model=TaskOut)
def get_task(task_id: uuid.UUID, ctx: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    task = db.scalar(scoped_task_query(ctx, db).where(Task.id == task_id))
    if not task: raise HTTPException(404, "Task not found")
    return task


@app.patch("/tasks/{task_id}", response_model=TaskOut)
def update_task(task_id: uuid.UUID, body: TaskIn, ctx: AuthContext = Depends(role_required(Role.agency_admin, Role.agency_member)), db: Session = Depends(get_db)):
    task = db.scalar(scoped_task_query(ctx, db).where(Task.id == task_id))
    if not task: raise HTTPException(404, "Task not found")
    for key, value in body.model_dump().items(): setattr(task, key, value)
    db.commit(); db.refresh(task); return task


@app.get("/tasks/{task_id}/comments")
def list_comments(task_id: uuid.UUID, ctx: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    task = db.scalar(scoped_task_query(ctx, db).where(Task.id == task_id))
    if not task: raise HTTPException(404, "Task not found")
    query = select(Comment).where(Comment.task_id == task_id, Comment.agency_id == ctx.agency_id)
    if ctx.membership.role == Role.client_user: query = query.where(Comment.is_client_visible.is_(True))
    return [{"id": str(c.id), "body": c.body, "is_client_visible": c.is_client_visible, "created_at": c.created_at} for c in db.scalars(query)]


@app.post("/tasks/{task_id}/comments")
def create_comment(task_id: uuid.UUID, body: CommentIn, ctx: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    task = db.scalar(scoped_task_query(ctx, db).where(Task.id == task_id))
    if not task: raise HTTPException(404, "Task not found")
    comment = Comment(agency_id=ctx.agency_id, task_id=task_id, author_identity_id=ctx.identity.id, body=body.body, is_client_visible=True if ctx.membership.role == Role.client_user else body.is_client_visible)
    db.add(comment); db.commit(); db.refresh(comment)
    return {"id": str(comment.id), "body": comment.body, "is_client_visible": comment.is_client_visible}


@app.post("/tasks/{task_id}/time")
def add_time(task_id: uuid.UUID, body: TimeIn, ctx: AuthContext = Depends(role_required(Role.agency_admin, Role.agency_member)), db: Session = Depends(get_db)):
    task = db.scalar(scoped_task_query(ctx, db).where(Task.id == task_id))
    if not task: raise HTTPException(404, "Task not found")
    entry = TimeEntry(agency_id=ctx.agency_id, task_id=task_id, identity_id=ctx.identity.id, **body.model_dump())
    db.add(entry); db.commit(); return {"id": str(entry.id), "minutes": entry.minutes}


@app.get("/projects/{project_id}/dashboard")
def dashboard(project_id: uuid.UUID, ctx: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    project = db.scalar(scoped_project_query(ctx, db).where(Project.id == project_id))
    if not project: raise HTTPException(404, "Project not found")
    visible = Task.is_client_visible.is_(True) if ctx.membership.role == Role.client_user else True
    counts = db.execute(select(Task.status, func.count(Task.id)).where(Task.agency_id == ctx.agency_id, Task.project_id == project_id, visible).group_by(Task.status)).all()
    hours = db.scalar(select(func.coalesce(func.sum(TimeEntry.minutes), 0)).join(Task, TimeEntry.task_id == Task.id).where(TimeEntry.agency_id == ctx.agency_id, Task.project_id == project_id, visible)) or 0
    return {"task_counts": {str(status): count for status, count in counts}, "hours_logged": round(hours / 60, 2)}


@app.post("/invites")
def create_invite(body: InviteIn, ctx: AuthContext = Depends(role_required(Role.agency_admin)), db: Session = Depends(get_db)):
    client = db.scalar(select(Client).where(Client.id == body.client_id, Client.agency_id == ctx.agency_id))
    if not client: raise HTTPException(404, "Client not found")
    invite = db.scalar(select(Invite).where(Invite.agency_id == ctx.agency_id, Invite.email == body.email.lower(), Invite.status == InviteStatus.pending))
    if invite:
        invite.expires_at = datetime.now(timezone.utc) + timedelta(days=2)
    else:
        invite = Invite(agency_id=ctx.agency_id, client_id=client.id, email=body.email.lower(), expires_at=datetime.now(timezone.utc) + timedelta(days=2))
        db.add(invite)
    db.commit(); db.refresh(invite)
    return {"id": str(invite.id), "token": invite.token, "status": invite.status}


@app.post("/invites/accept")
def accept_invite(body: AcceptInviteIn, db: Session = Depends(get_db)):
    rate_limit(f"invite:{hash(body.token)}")
    invite = db.scalar(select(Invite).where(Invite.token == body.token))
    expires_at = invite.expires_at.replace(tzinfo=timezone.utc) if invite and invite.expires_at.tzinfo is None else (invite.expires_at if invite else None)
    if not invite or invite.status != InviteStatus.pending or expires_at < datetime.now(timezone.utc):
        raise HTTPException(409, "Invite is not pending")
    identity = db.scalar(select(Identity).where(func.lower(Identity.email) == invite.email.lower()))
    if not identity:
        identity = Identity(email=invite.email.lower(), display_name=body.display_name, password_hash=hash_password(body.password)); db.add(identity); db.flush()
    existing = db.scalar(select(Membership).where(Membership.identity_id == identity.id, Membership.agency_id == invite.agency_id))
    if not existing: db.add(Membership(identity_id=identity.id, agency_id=invite.agency_id, client_id=invite.client_id, role=Role.client_user))
    invite.status = InviteStatus.accepted; invite.accepted_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "accepted", "identity_id": str(identity.id)}


@app.post("/projects/{project_id}/members/{membership_id}/remove")
def remove_member(project_id: uuid.UUID, membership_id: uuid.UUID, ctx: AuthContext = Depends(role_required(Role.agency_admin)), db: Session = Depends(get_db)):
    blockers = list(db.scalars(select(Task).where(Task.agency_id == ctx.agency_id, Task.project_id == project_id, Task.assignee_membership_id == membership_id, Task.status != TaskStatus.done)))
    if blockers: raise HTTPException(409, detail={"message": "Reassign open tasks before removing member", "task_ids": [str(t.id) for t in blockers]})
    assignment = db.scalar(select(ProjectAssignment).where(ProjectAssignment.agency_id == ctx.agency_id, ProjectAssignment.project_id == project_id, ProjectAssignment.membership_id == membership_id))
    if not assignment: raise HTTPException(404, "Assignment not found")
    db.delete(assignment); db.commit(); return {"status": "removed"}


@app.post("/tasks/{task_id}/attachments", response_model=AttachmentOut)
def upload_attachment(task_id: uuid.UUID, upload: UploadFile = File(...), is_client_visible: bool = False, ctx: AuthContext = Depends(role_required(Role.agency_admin, Role.agency_member)), db: Session = Depends(get_db)):
    task = db.scalar(scoped_task_query(ctx, db).where(Task.id == task_id))
    if not task: raise HTTPException(404, "Task not found")
    allowed_types = {"application/pdf", "text/plain", "text/markdown", "image/png", "image/jpeg", "image/webp", "application/zip"}
    if upload.content_type and upload.content_type not in allowed_types:
        raise HTTPException(415, "Unsupported file type")
    content = upload.file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(413, "File exceeds the 10 MB limit")
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    token = uuid.uuid4().hex + uuid.uuid4().hex
    path = settings.upload_dir / token
    path.write_bytes(content)
    attachment = FileAttachment(agency_id=ctx.agency_id, task_id=task_id, external_token=token, original_name=upload.filename or "upload", storage_path=str(path), is_client_visible=is_client_visible)
    db.add(attachment); db.commit(); db.refresh(attachment); return attachment


@app.get("/tasks/{task_id}/attachments", response_model=list[AttachmentOut])
def list_attachments(task_id: uuid.UUID, ctx: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    task = db.scalar(scoped_task_query(ctx, db).where(Task.id == task_id))
    if not task: raise HTTPException(404, "Task not found")
    query = select(FileAttachment).where(FileAttachment.task_id == task_id, FileAttachment.agency_id == ctx.agency_id)
    if ctx.membership.role == Role.client_user: query = query.where(FileAttachment.is_client_visible.is_(True))
    return list(db.scalars(query))


@app.get("/files/{token}")
def download_attachment(token: str, ctx: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    query = select(FileAttachment).join(Task, FileAttachment.task_id == Task.id).join(Project, Task.project_id == Project.id).where(FileAttachment.external_token == token, FileAttachment.agency_id == ctx.agency_id)
    if ctx.membership.role == Role.client_user: query = query.where(Project.client_id == ctx.membership.client_id, FileAttachment.is_client_visible.is_(True), Task.is_client_visible.is_(True))
    attachment = db.scalar(query)
    if not attachment: raise HTTPException(404, "File not found")
    return FileResponse(attachment.storage_path, filename=attachment.original_name)


@app.post("/files/{token}/approval")
def approve_attachment(token: str, status: ApprovalStatus, ctx: AuthContext = Depends(role_required(Role.client_user)), db: Session = Depends(get_db)):
    attachment = db.scalar(select(FileAttachment).join(Task).join(Project).where(FileAttachment.external_token == token, FileAttachment.agency_id == ctx.agency_id, FileAttachment.is_client_visible.is_(True), Project.client_id == ctx.membership.client_id))
    if not attachment: raise HTTPException(404, "File not found")
    attachment.approval_status = status; db.commit(); return {"status": attachment.approval_status}


def agency_records(model, ctx: AuthContext, db: Session):
    query = select(model).where(model.agency_id == ctx.agency_id)
    if ctx.membership.role == Role.client_user:
        query = query.where(model.client_id == ctx.membership.client_id)
    return list(db.scalars(query))


@app.get("/crm/leads")
def list_leads(ctx: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    if ctx.membership.role == Role.client_user: raise HTTPException(403, "CRM is agency-only")
    return [{"id": str(row.id), "name": row.name, "email": row.email, "status": row.status} for row in agency_records(Lead, ctx, db)]


@app.post("/crm/leads")
def create_lead(body: dict, ctx: AuthContext = Depends(role_required(Role.agency_admin, Role.agency_member)), db: Session = Depends(get_db)):
    row = Lead(agency_id=ctx.agency_id, name=body.get("name", ""), email=body.get("email", ""), status=body.get("status", "new")); db.add(row); db.commit(); db.refresh(row)
    return {"id": str(row.id), "name": row.name, "email": row.email, "status": row.status}


@app.get("/crm/deals")
def list_deals(ctx: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    if ctx.membership.role == Role.client_user: raise HTTPException(403, "CRM is agency-only")
    return [{"id": str(row.id), "name": row.name, "value_cents": row.value_cents, "status": row.status} for row in agency_records(Deal, ctx, db)]


@app.post("/crm/deals")
def create_deal(body: dict, ctx: AuthContext = Depends(role_required(Role.agency_admin, Role.agency_member)), db: Session = Depends(get_db)):
    row = Deal(agency_id=ctx.agency_id, name=body.get("name", ""), value_cents=int(body.get("value_cents", 0)), status=body.get("status", "open")); db.add(row); db.commit(); db.refresh(row)
    return {"id": str(row.id), "name": row.name, "value_cents": row.value_cents, "status": row.status}


@app.get("/crm/contracts")
def list_contracts(ctx: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    if ctx.membership.role == Role.client_user: raise HTTPException(403, "CRM is agency-only")
    return [{"id": str(row.id), "title": row.title, "status": row.status, "starts_on": row.starts_on, "ends_on": row.ends_on} for row in agency_records(Contract, ctx, db)]


@app.post("/crm/contracts")
def create_contract(body: dict, ctx: AuthContext = Depends(role_required(Role.agency_admin, Role.agency_member)), db: Session = Depends(get_db)):
    row = Contract(agency_id=ctx.agency_id, title=body.get("title", ""), status=body.get("status", "draft")); db.add(row); db.commit(); db.refresh(row)
    return {"id": str(row.id), "title": row.title, "status": row.status}


@app.get("/intake/forms")
def list_intake_forms(ctx: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    query = select(IntakeForm).where(IntakeForm.agency_id == ctx.agency_id, IntakeForm.is_active.is_(True))
    if ctx.membership.role == Role.client_user: query = query.where(IntakeForm.client_id == ctx.membership.client_id)
    return [{"id": str(row.id), "name": row.name, "client_id": str(row.client_id) if row.client_id else None, "fields": json.loads(row.fields_json)} for row in db.scalars(query)]


@app.post("/intake/forms")
def create_intake_form(body: dict, ctx: AuthContext = Depends(role_required(Role.agency_admin)), db: Session = Depends(get_db)):
    row = IntakeForm(agency_id=ctx.agency_id, client_id=body.get("client_id"), name=body.get("name", "New intake form"), fields_json=json.dumps(body.get("fields", [{"name": "request", "label": "How can we help?"}]))); db.add(row); db.commit(); db.refresh(row)
    return {"id": str(row.id), "name": row.name, "fields": json.loads(row.fields_json)}


@app.post("/intake/forms/{form_id}/responses")
def submit_intake(form_id: uuid.UUID, body: dict, ctx: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    form = db.scalar(select(IntakeForm).where(IntakeForm.id == form_id, IntakeForm.agency_id == ctx.agency_id, IntakeForm.is_active.is_(True)))
    if not form or (ctx.membership.role == Role.client_user and form.client_id != ctx.membership.client_id): raise HTTPException(404, "Form not found")
    row = IntakeResponse(agency_id=ctx.agency_id, form_id=form.id, client_id=ctx.membership.client_id if ctx.membership.role == Role.client_user else form.client_id, submitted_by_identity_id=ctx.identity.id, payload_json=json.dumps(body)); db.add(row); db.commit()
    return {"id": str(row.id), "status": "submitted"}


@app.get("/automations")
def list_automations(ctx: AuthContext = Depends(role_required(Role.agency_admin)), db: Session = Depends(get_db)):
    return [{"id": str(row.id), "name": row.name, "event_type": row.event_type, "action_type": row.action_type, "active": row.active} for row in db.scalars(select(Automation).where(Automation.agency_id == ctx.agency_id))]


@app.post("/automations")
def create_automation(body: dict, ctx: AuthContext = Depends(role_required(Role.agency_admin)), db: Session = Depends(get_db)):
    row = Automation(agency_id=ctx.agency_id, name=body.get("name", "New automation"), event_type=body.get("event_type", "task.created"), action_type=body.get("action_type", "notify")); db.add(row); db.commit(); db.refresh(row)
    return {"id": str(row.id), "name": row.name, "event_type": row.event_type, "action_type": row.action_type, "active": row.active}


@app.get("/notifications")
def list_notifications(ctx: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    return [{"id": str(row.id), "message": row.message, "read": row.read, "created_at": row.created_at} for row in db.scalars(select(Notification).where(Notification.agency_id == ctx.agency_id, Notification.identity_id == ctx.identity.id).order_by(Notification.created_at.desc()))]
