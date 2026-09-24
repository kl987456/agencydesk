from collections.abc import Generator
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from .config import get_settings

settings = get_settings()
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


@event.listens_for(Session, "after_begin")
def apply_tenant_context(session, transaction, connection):
    agency_id = session.info.get("agency_id")
    if agency_id and connection.dialect.name == "postgresql":
        connection.execute(text("select set_config('app.current_agency_id', :agency_id, true)"), {"agency_id": str(agency_id)})


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
