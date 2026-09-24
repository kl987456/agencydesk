# Product hardening status

## Implemented and tested

- Admin/member drag-and-drop task movement with API persistence.
- Client portal remains read-only for task creation, task status, assignment, time logging, and uploads.
- Active task-created automations emit tenant-scoped staff notifications.
- File MIME allowlist and 10 MB upload limit.
- Session-expiry handling returns the browser to login.
- Animated loading/hover/detail states with reduced-motion support.
- Cross-tenant, visibility, invite-race, identity-context, removal, notification, and upload-validation tests.

## Intentionally outside the current local build

- Database-backed sessions, password reset, MFA, and email delivery require a production identity/email provider.
- S3/Azure object storage and virus scanning require deployed infrastructure.
- CI/CD, Sentry, backups, and production observability require deployment credentials and hosting configuration.
- Timeline/Gantt remains discussion-only per the assignment.
- Full CRM remains out of scope per the assignment; the lightweight bonus CRM is included.
