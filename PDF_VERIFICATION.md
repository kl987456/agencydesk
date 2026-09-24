# AgencyDesk PDF verification checklist

This is the acceptance note for `Sapyon-take-home-assignment.pdf`. Items are gated: an item is marked complete only after implementation and an end-to-end check.

## Required scope

- [x] Project and task boards: projects are client-owned; tasks have status, priority, assignee field, due date, description, and internal/client-visible visibility. Agency users can create tasks and update status; client users cannot.
- [x] Client portal / guest access: client identity context returns only its client projects and client-visible tasks/comments/files. Client users can comment and approve files, but cannot create tasks, change task status, log agency time, or access CRM/admin tools.
- [x] Time tracking: agency users can log positive duration, work date, and note; dashboard exposes scoped hours per project.
- [x] File uploads and approval: multipart task upload, inherited visibility, scoped listing, and client approval / needs-changes actions.
- [x] Dashboards and reporting: project task counts by status and scoped hours logged are available to the viewer.

## Bonus scope

- [x] Client intake forms: agency admin creates a form for a client; client submits a response.
- [x] Automations and notifications: agency admin can persist task-event notification rules; creating a matching task emits scoped notifications to active agency staff, which are available through the notifications API.
- [x] Lightweight CRM enhancement: agency-only leads, deals, and contracts are available and tenant-scoped.

## Edge-case verification

- [x] Cross-tenant access: every required query is filtered by active agency and client visibility; guessed IDs return not-found rather than another tenant's record. Postgres RLS is enabled for required and bonus tenant tables.
- [x] Internal-content leakage: task list search, task detail, comments, attachments, dashboard, and client portal all apply visibility filters.
- [x] One identity in two agencies: memberships are separate agency contexts; login returns memberships and context switching creates a scoped session. The seeded shared identity was verified in both contexts.
- [x] Invite races: pending invite creation is idempotent for the same agency/email; resend updates the existing pending invite; accepting an already accepted invite is rejected and does not duplicate membership/account state.
- [x] Removed team member mid-task: removal is rejected with a 409 while open tasks remain assigned, forcing reassignment before removal.

## Explicit non-build scope from the PDF

- [x] Timeline / Gantt: discussed only; no build included.
- [x] Full CRM: the PDF marks it out of scope; a small bonus CRM surface was added, but contracts/deals are intentionally not a full sales system.

## Verification commands

- `backend`: `pytest -q` — 8 passed.
- `frontend`: `npm run build` — production build passed.
- Browser smoke: admin work board, search, task detail, comments, time entry, file controls, drag-and-drop status movement, CRM, intake, automations; client portal filtering and restricted controls; shared-identity context selector.

Last reviewed: 2026-09-24.
