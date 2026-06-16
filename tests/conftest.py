import os
import tempfile

import pytest

import database.db as db_module
from database.db import init_db, seed_db
from app import app as flask_app


@pytest.fixture
def client(monkeypatch):
    fd, path = tempfile.mkstemp()
    monkeypatch.setattr(db_module, "DB_PATH", path)
    flask_app.config["TESTING"] = True

    with flask_app.app_context():
        init_db()
        seed_db()

    with flask_app.test_client() as c:
        yield c

    os.close(fd)
    os.remove(path)
