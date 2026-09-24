import os
os.environ["DATABASE_URL"] = "sqlite:///./test_agencydesk.db"
import pytest
from fastapi.testclient import TestClient
from app.db import Base, engine
from app.main import app
from app.seed import run

@pytest.fixture(scope="session", autouse=True)
def database():
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine); run(); yield; Base.metadata.drop_all(engine)

@pytest.fixture
def client():
    return TestClient(app)

def login(client, email):
    result = client.post("/auth/login", json={"email": email, "password": "AgencyDesk123!"})
    assert result.status_code == 200
    return result.json()["token"]
