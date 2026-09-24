# Contributing

Run `ruff check backend` and `ruff format --check backend` before committing. Alembic autogenerate is only a draft: every generated migration must be reviewed by hand, especially foreign keys, partial indexes, and RLS policies.

CI, distributed tracing, object storage, and a production secret manager are deliberately out of scope for this time-boxed take-home. The design calls out where those would be added.
