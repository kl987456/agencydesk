# AgencyDesk — 3–5 minute submission walkthrough

## 0:00–0:20 — Product introduction

“This is AgencyDesk, a multi-tenant agency workspace. It combines project boards, client collaboration, time tracking, file approvals, dashboards, intake forms, and lightweight automations. The key design principle is that every request is scoped to one agency context.”

## 0:20–1:10 — Agency workspace

“I’m signing in as an agency administrator. The Work screen shows a project board with Todo, In Progress, Review, and Done columns. Tasks carry priority and internal/client-visible badges.”

“Agency users can create tasks, search the visible task set, open task details, comment, log time, upload files, and move tasks by drag-and-drop. The dashboard shows task counts and project hours.”

“I’ll move this task from In Progress to Review. The board updates immediately and the status is persisted by the API.”

## 1:10–1:45 — Files, approvals, and notifications

“Inside task detail, agency users can upload a file and choose whether it is client-visible. Uploads enforce a file-type allowlist and a 10 MB size limit.”

“The Automations view contains task-event notification rules. When an active task-created rule matches, the API creates tenant-scoped notifications for active agency staff.”

## 1:45–2:30 — Client portal

“Now I’m signing in as the shared identity in its client context. The client sees only its own project and client-visible tasks. Internal tasks do not appear in the board or search results.”

“The client can comment on visible tasks, submit an intake response, and approve or request changes on visible files. Client controls for task creation, status changes, time logging, uploads, CRM, and automations are not available.”

## 2:30–3:00 — One person, two agencies

“This identity belongs to two agencies with different roles. The context selector switches the active agency. The server session binds the selected agency, and resource endpoints use that session context instead of trusting a client-provided tenant filter.”

## 3:00–3:40 — Security and edge cases

“The backend tests cover cross-tenant ID guessing, internal-content leakage through search and comments, two-agency identity contexts, invite resend and double-accept races, removing an assigned member with open work, notification scoping, and unsafe upload rejection.”

“Tenant isolation is layered: explicit application predicates, composite tenant-safe foreign keys, and Postgres row-level security policies. Removing a team member is blocked while open tasks remain assigned, so work is not silently orphaned.”

## 3:40–4:00 — Verification and scope

“The final verification is eight passing backend tests and a passing Vite production build. The PDF checklist, DESIGN.md, README.md, and this walkthrough script are included in the repository.”

“Timeline/Gantt remains discussion-only as required by the assignment. The included CRM is a lightweight bonus surface, not a full CRM replacement. Production follow-ups are documented: persistent sessions, email delivery, object storage, virus scanning, CI/CD, monitoring, and backups.”

## Closing line

“AgencyDesk is ready as a take-home submission: the required workflows are implemented, tenant and client visibility boundaries are tested, and the main admin and client journeys have been verified in the browser.”
