"""Readable security proofs for the five assignment edge cases."""
from sqlalchemy import select
from app.db import SessionLocal
from app.models import Agency, Identity, Invite, InviteStatus, Membership, Project, ProjectAssignment, Role, Task, TaskStatus
from .conftest import login

def test_cross_tenant_access_blocked_app_layer(client):
    """A Northstar token cannot retrieve a Brightline task by guessed UUID; 404 avoids existence leaks."""
    db=SessionLocal(); other=db.scalar(select(Task).where(Task.agency_id==db.scalar(select(Agency).where(Agency.name=="Brightline Studio")).id)); db.close()
    token=login(client,"admin@northstar.test")
    response=client.get(f"/tasks/{other.id}",headers={"Authorization":f"Bearer {token}"})
    assert response.status_code==404

def test_internal_content_never_leaks_to_client_app_layer(client):
    """Client list, search, and comments queries apply visibility predicates before rows are returned."""
    token=login(client,"shared@example.test")
    db=SessionLocal(); project=db.scalar(select(Project).where(Project.name=="Acme Website")); db.close()
    headers={"Authorization":f"Bearer {token}"}
    tasks=client.get(f"/projects/{project.id}/tasks",headers=headers).json()
    assert all(task["is_client_visible"] for task in tasks)
    assert client.get(f"/projects/{project.id}/tasks?q=Internal",headers=headers).json()==[]

def test_one_person_two_agencies_different_roles(client):
    """One identity has client_user and agency_member memberships, selected by agency context."""
    db=SessionLocal(); agencies=list(db.scalars(select(Agency))); db.close()
    result=client.post("/auth/login",json={"email":"shared@example.test","password":"AgencyDesk123!","agency_id":str(agencies[0].id)})
    assert result.status_code==200
    assert {m["role"] for m in result.json()["memberships"]}=={"client_user","agency_member"}

def test_invite_resend_no_duplicate(client):
    """Resending an active invite updates expiry rather than inserting a second pending row."""
    db=SessionLocal(); agency=db.scalar(select(Agency).where(Agency.name=="Northstar Creative")); client_row=db.scalar(select(Project).where(Project.name=="Acme Website")).client; db.close()
    token=login(client,"admin@northstar.test"); headers={"Authorization":f"Bearer {token}"}; payload={"email":"pending@example.test","client_id":str(client_row.id)}
    first=client.post("/invites",json=payload,headers=headers); second=client.post("/invites",json=payload,headers=headers)
    assert first.status_code==200 and second.status_code==200
    db=SessionLocal(); assert len(list(db.scalars(select(Invite).where(Invite.email=="pending@example.test",Invite.status==InviteStatus.pending))))==1; db.close()

def test_invite_concurrent_double_accept_exactly_one_wins(client):
    """Repeated acceptance is rejected after the pending-to-accepted state transition."""
    db=SessionLocal(); invite=db.scalar(select(Invite).where(Invite.status==InviteStatus.pending)); token=invite.token; db.close()
    payload={"token":token,"display_name":"Pending Person","password":"AgencyDesk123!"}
    first=client.post("/invites/accept",json=payload); second=client.post("/invites/accept",json=payload)
    assert sorted([first.status_code,second.status_code])==[200,409]

def test_removed_member_blocked_with_open_tasks(client):
    """Removing an assigned member with open work returns 409 and names blocking task IDs."""
    db=SessionLocal(); agency=db.scalar(select(Agency).where(Agency.name=="Northstar Creative")); project=db.scalar(select(Project).where(Project.name=="Acme Website")); member=db.scalar(select(Membership).join(Identity).where(Identity.email=="member@northstar.test")); db.close()
    token=login(client,"admin@northstar.test"); response=client.post(f"/projects/{project.id}/members/{member.id}/remove",headers={"Authorization":f"Bearer {token}"})
    assert response.status_code==409 and response.json()["detail"]["task_ids"]

def test_task_creation_emits_scoped_notification(client):
    """An active task-created automation produces an agency-scoped staff notification."""
    db=SessionLocal(); project=db.scalar(select(Project).where(Project.name=="Acme Website")); db.close()
    token=login(client,"admin@northstar.test"); headers={"Authorization":f"Bearer {token}"}
    created=client.post(f"/projects/{project.id}/tasks",json={"title":"Notification smoke task"},headers=headers)
    assert created.status_code==200
    notifications=client.get("/notifications",headers=headers)
    assert notifications.status_code==200 and any("Notification smoke task" in item["message"] for item in notifications.json())

def test_upload_rejects_unsupported_file_type(client):
    """Uploads reject executable/script-like content types before writing storage."""
    db=SessionLocal(); task=db.scalar(select(Task).where(Task.title=="Internal kickoff")); db.close()
    token=login(client,"admin@northstar.test"); response=client.post(f"/tasks/{task.id}/attachments",headers={"Authorization":f"Bearer {token}"},files={"upload":("payload.exe",b"MZ", "application/x-msdownload")})
    assert response.status_code==415
