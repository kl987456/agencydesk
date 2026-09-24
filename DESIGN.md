# AgencyDesk design

## Tenant isolation

Every tenant-scoped row stores a non-null `agency_id`. Composite foreign keys such as `Task(agency_id, project_id) -> Project(agency_id, id)` and `Project(agency_id, client_id) -> Client(agency_id, id)` make cross-tenant references invalid at the database boundary. Postgres migrations also enable RLS on every tenant table, using `app.current_agency_id` set by the request auth dependency. Application queries still add explicit agency, client, and assignment predicates: RLS is the backstop, not a reason to stop reviewing query scope. I chose denormalization of `agency_id` for fast RLS/index lookups and paid for it with composite keys that keep the redundant value consistent.

## Internal content

Client task list/search/filter/detail queries add `Task.is_client_visible = true` before execution. Comment threads add `Comment.is_client_visible = true`, attachment downloads require both a client-visible attachment and task, and dashboard `GROUP BY`/sum queries include the same predicate. The client bundle only calls these scoped endpoints; it does not request an agency-wide feed and hide internal rows in CSS.

## Identity and context

An `Identity` is globally unique by normalized email. `Membership` is the agency-scoped role and optional client link, so one identity can be a client in one agency and a member in another. Login accepts an agency context when needed and creates a short-lived server-side session containing `(identity_id, agency_id)`. Each protected request resolves exactly one membership and sets `app.current_agency_id` on the SQLAlchemy session before tenant queries execute.

## Edge case I am proudest of

Invite acceptance is not a read-then-insert flow: the pending state and unique pending invite index are the concurrency boundary, and acceptance transitions the invite once before creating the membership. Replays receive a clean conflict. Likewise, member removal is blocked when open tasks remain; silently nullifying an assignee looks convenient but creates unowned production work.

## Known limitations

Timeline/Gantt remains intentionally discussion-only because the assignment marks it “no build.” Local tests use SQLite, so Postgres RLS must also be exercised in CI against the Docker database. Sessions are in-process rather than Redis-backed, uploads use local disk rather than S3, automations persist rules but do not include a distributed worker queue, and rate limiting is process-local. A production deployment would add migrations in CI, Redis/session storage, object storage, a job queue, structured log shipping, tracing, CSRF protection for cookie sessions, and a real secrets manager.
