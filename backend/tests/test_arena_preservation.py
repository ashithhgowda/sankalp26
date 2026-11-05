import os
import re
from pathlib import Path

import requests
import bcrypt
import pytest
from bson import ObjectId
from dotenv import load_dotenv
from pymongo import MongoClient


load_dotenv("/app/frontend/.env")
BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"
ARENA_EMAIL = "arena-preservation@example.com"
ARENA_PASSWORD = "Arena!Preserve2026"


@pytest.fixture(scope="module", autouse=True)
def arena_user():
    load_dotenv("/app/backend/.env")
    client = MongoClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]
    db.users.delete_many({"email": ARENA_EMAIL})
    uid = ObjectId()
    db.users.insert_one({"_id": uid, "email": ARENA_EMAIL, "name": "Arena Preservation QA", "role": "member",
                         "team_id": str(uid), "password_hash": bcrypt.hashpw(ARENA_PASSWORD.encode(), bcrypt.gensalt()).decode(),
                         "is_active": True, "email_verified": True, "must_change_password": False, "session_version": 0,
                         "created_at": "2026-11-01T00:00:00+00:00"})
    yield
    db.sessions.delete_many({"user_id": str(uid)})
    for collection in ("arena_attempts", "arena_xp", "arena_badges", "arena_opens", "arena_rapid_runs", "arena_events"):
        db[collection].delete_many({"user_id": str(uid)})
    db.users.delete_one({"_id": uid})
    client.close()


def credential(role):
    text = Path("/app/memory/test_credentials.md").read_text()
    email = re.search(rf"## {role}\n- Email: (.+)", text).group(1)
    password = re.search(rf"## {role}\n- Email: .+\n- Password: (.+)", text).group(1)
    return email, password


def login(role):
    email, password = credential(role)
    response = requests.post(BASE + "/auth/login", json={"email": email, "password": password}, timeout=30)
    assert response.status_code == 200, response.text
    return {"Authorization": "Bearer " + response.json()["token"]}


def test_existing_arena_remains_available_without_exposing_answers():
    response = requests.post(BASE + "/auth/login", json={"email": ARENA_EMAIL, "password": ARENA_PASSWORD}, timeout=30)
    assert response.status_code == 200, response.text
    member = {"Authorization": "Bearer " + response.json()["token"]}
    public = requests.get(BASE + "/arena/questions", timeout=30)
    assert public.status_code == 200
    assert public.json() and all("answer_index" not in question for question in public.json())
    profile = requests.get(BASE + "/arena/me", headers=member, timeout=30)
    assert profile.status_code == 200


def test_existing_arena_admin_route_remains_protected():
    admin = login("Admin")
    questions = requests.get(BASE + "/arena/admin/questions", headers=admin, timeout=30)
    assert questions.status_code == 200 and questions.json()
    response = requests.post(BASE + "/auth/login", json={"email": ARENA_EMAIL, "password": ARENA_PASSWORD}, timeout=30)
    member = {"Authorization": "Bearer " + response.json()["token"]}
    assert requests.get(BASE + "/arena/admin/questions", headers=member, timeout=30).status_code == 403