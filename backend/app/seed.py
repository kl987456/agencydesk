from datetime import date, datetime, timedelta, timezone
from sqlalchemy import select
from .auth import hash_password
from .db import Base, SessionLocal, engine
from .models import Agency, Automation, Client, Comment, Contract, Deal, FileAttachment, Identity, IntakeForm, Invite, InviteStatus, Lead, Membership, Project, ProjectAssignment, Role, Task, TaskStatus, TimeEntry
import json

PASSWORD = "AgencyDesk123!"

def identity(db, email, name):
    found = db.scalar(select(Identity).where(Identity.email == email))
    if found: return found
    found = Identity(email=email, display_name=name, password_hash=hash_password(PASSWORD)); db.add(found); db.flush(); return found

def run():
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        a = db.scalar(select(Agency).where(Agency.name == "Northstar Creative")) or Agency(name="Northstar Creative")
        b = db.scalar(select(Agency).where(Agency.name == "Brightline Studio")) or Agency(name="Brightline Studio")
        db.add_all([a, b]); db.flush()
        ca = db.scalar(select(Client).where(Client.agency_id == a.id, Client.name == "Acme Retail")) or Client(agency_id=a.id, name="Acme Retail")
        cb = db.scalar(select(Client).where(Client.agency_id == b.id, Client.name == "Globex Labs")) or Client(agency_id=b.id, name="Globex Labs")
        db.add_all([ca, cb]); db.flush()
        admin_a = identity(db, "admin@northstar.test", "Northstar Admin")
        member_a = identity(db, "member@northstar.test", "Northstar Member")
        shared = identity(db, "shared@example.test", "Shared Contact")
        admin_b = identity(db, "admin@brightline.test", "Brightline Admin")
        memberships = [(admin_a,a,Role.agency_admin,None),(member_a,a,Role.agency_member,None),(shared,a,Role.client_user,ca.id),(admin_b,b,Role.agency_admin,None),(shared,b,Role.agency_member,None)]
        mem = {}
        for ident, agency, role, client_id in memberships:
            row = db.scalar(select(Membership).where(Membership.identity_id == ident.id, Membership.agency_id == agency.id))
            if not row: row = Membership(identity_id=ident.id, agency_id=agency.id, role=role, client_id=client_id); db.add(row); db.flush()
            mem[(ident.email, agency.id)] = row
        p = db.scalar(select(Project).where(Project.agency_id == a.id, Project.name == "Acme Website")) or Project(agency_id=a.id, client_id=ca.id, name="Acme Website", description="A public website redesign")
        db.add(p); db.flush()
        pb = db.scalar(select(Project).where(Project.agency_id == b.id, Project.name == "Globex Launch")) or Project(agency_id=b.id, client_id=cb.id, name="Globex Launch", description="A Brightline launch project")
        db.add(pb); db.flush()
        if not db.scalar(select(ProjectAssignment).where(ProjectAssignment.project_id == p.id, ProjectAssignment.membership_id == mem[("member@northstar.test",a.id)].id)):
            db.add(ProjectAssignment(agency_id=a.id, project_id=p.id, membership_id=mem[("member@northstar.test",a.id)].id))
        if not db.scalar(select(Task).where(Task.project_id == p.id, Task.title == "Internal kickoff")):
            internal = Task(agency_id=a.id, project_id=p.id, title="Internal kickoff", description="Agency-only planning", status=TaskStatus.in_progress, is_client_visible=False, assignee_membership_id=mem[("member@northstar.test",a.id)].id)
            visible = Task(agency_id=a.id, project_id=p.id, title="Approve homepage", description="Review the proposed homepage", status=TaskStatus.review, is_client_visible=True)
            db.add_all([internal, visible]); db.flush()
            db.add(Comment(agency_id=a.id, task_id=visible.id, author_identity_id=admin_a.id, body="Ready for client review", is_client_visible=True))
            db.add(TimeEntry(agency_id=a.id, task_id=internal.id, identity_id=member_a.id, minutes=90, note="Planning", work_date=date.today()))
        if not db.scalar(select(Task).where(Task.project_id == pb.id, Task.title == "Brightline planning")):
            db.add(Task(agency_id=b.id, project_id=pb.id, title="Brightline planning", description="Internal planning", status=TaskStatus.todo, is_client_visible=False))
        if not db.scalar(select(Invite).where(Invite.agency_id == a.id, Invite.email == "pending@example.test", Invite.status == InviteStatus.pending)):
            db.add(Invite(agency_id=a.id, client_id=ca.id, email="pending@example.test", expires_at=datetime.now(timezone.utc)+timedelta(days=2)))
        if not db.scalar(select(Invite).where(Invite.agency_id == a.id, Invite.email == "accepted@example.test")):
            db.add(Invite(agency_id=a.id, client_id=ca.id, email="accepted@example.test", status=InviteStatus.accepted, expires_at=datetime.now(timezone.utc)+timedelta(days=2), accepted_at=datetime.now(timezone.utc)))
        if not db.scalar(select(Lead).where(Lead.agency_id == a.id, Lead.email == "prospect@example.test")):
            db.add(Lead(agency_id=a.id, name="Seed Prospect", email="prospect@example.test", status="new"))
        if not db.scalar(select(Deal).where(Deal.agency_id == a.id, Deal.name == "Seed Website Deal")):
            db.add(Deal(agency_id=a.id, name="Seed Website Deal", value_cents=250000, status="open"))
        if not db.scalar(select(Contract).where(Contract.agency_id == a.id, Contract.title == "Seed MSA")):
            db.add(Contract(agency_id=a.id, title="Seed MSA", status="draft"))
        if not db.scalar(select(IntakeForm).where(IntakeForm.agency_id == a.id, IntakeForm.name == "Website brief")):
            db.add(IntakeForm(agency_id=a.id, client_id=ca.id, name="Website brief", fields_json=json.dumps([{"name": "request", "label": "What should we build?"}])))
        if not db.scalar(select(Automation).where(Automation.agency_id == a.id, Automation.name == "Notify on task creation")):
            db.add(Automation(agency_id=a.id, name="Notify on task creation", event_type="task.created", action_type="notify"))
        db.commit()
        print("Seeded AgencyDesk. Password for all seeded accounts:", PASSWORD)
    finally: db.close()

if __name__ == "__main__": run()
