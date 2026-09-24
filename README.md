# AgencyDesk

AgencyDesk is a multi-tenant client/project workspace built for the Sapyon take-home assignment. The security thesis is layered: explicit application scoping first, composite tenant-safe foreign keys and Postgres RLS as the database backstop.

## Run locally in under 10 minutes

Prerequisites: Python 3.12, Node 20, Docker Desktop.

```powershell
docker compose up -d db
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:PYTHONPATH='.'
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload
```

In another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The seeded password for all accounts is `AgencyDesk123!`:

- `admin@northstar.test` — agency admin
- `member@northstar.test` — agency member
- `shared@example.test` — client user in Northstar and agency member in Brightline; pass the desired `agency_id` to `/auth/login` to switch context
- `admin@brightline.test` — second agency admin

Run tests with `cd backend; $env:PYTHONPATH='.'; pytest -q`. The single migration is intentionally reviewed by hand; autogenerate is a draft, not a substitute for reviewing constraint/RLS changes.

## Layout

`backend/app/models.py` contains the schema and composite keys, `auth.py` owns identity/session context, and `main.py` contains scoped resource APIs. The React surface includes Work, CRM, Intake, and Automations views. CRM covers leads, deals, and contracts; Intake covers client brief submission; Automations covers event-to-notification rules. The Work board supports task creation, status editing, drag-and-drop movement, search, scoped comments, time logging, file approval, and animated responsive states. Uploads enforce a 10 MB limit and an allowlist of document/image/archive types. `tests/test_edge_cases.py` is the readable proof of the required exploits plus notification and upload validation.

## Product hardening completed

- Tenant-scoped notifications are emitted when an active `task.created` automation matches.
- Client users cannot drag, create, update, assign, log time, or upload agency work.
- Agency users can move tasks by drag-and-drop or the task detail status control.
- Unauthorized API responses clear the client session and return the UI to login.
- File uploads reject unsupported MIME types and files over 10 MB.
- Motion respects `prefers-reduced-motion`.
