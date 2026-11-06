import hashlib
import os
import re
import secrets
import uuid
from datetime import timedelta, timezone
from pathlib import Path

import bcrypt
import pytest
from bson import ObjectId
from dotenv import load_dotenv
from fastapi import FastAPI
from gridfs import GridFSBucket
from gridfs.errors import NoFile
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from starlette.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


def _auth_for(db, server, role, team_id=None, user_id=None):
    user_id = user_id or ObjectId()
    sid = secrets.token_urlsafe(24)
    user = {
        "_id": user_id,
        "email": f"{role}-{user_id}@example.com",
        "name": f"People test {role}",
        "role": role,
        "team_id": team_id,
        "team_name": "People test team" if team_id else None,
        "track": "People test topic",
        "password_hash": (
            bcrypt.hashpw(b"Valid!Leader2026", bcrypt.gensalt()).decode()
            if role == "team"
            else None
        ),
        "is_active": True,
        "email_verified": True,
        "must_change_password": False,
        "session_version": 0,
    }
    db.users.replace_one({"_id": user_id}, user, upsert=True)
    db.sessions.insert_one({"sid": sid, "user_id": str(user_id), "revoked_at": None})
    token = server.make_token(server.User.from_mongo(user), "access", sid, timedelta(minutes=5))
    return user, {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def api():
    required = ("MONGO_URL", "DB_NAME", "JWT_SECRET", "INTEGRATION_PROXY_URL")
    if any(not os.environ.get(key) for key in required):
        pytest.skip("MongoDB or application configuration is not available")

    client = MongoClient(os.environ["MONGO_URL"], serverSelectionTimeoutMS=8000)
    try:
        client.admin.command("ping")
    except PyMongoError as exc:
        client.close()
        pytest.skip(f"MongoDB Atlas is unavailable: {type(exc).__name__}")

    import backend.server as server
    from backend.arena import build_router as build_arena_router
    from backend.phase1 import build_router

    original_db = server.db
    db_name = f"sppl_{uuid.uuid4().hex[:16]}"
    test_db = client[db_name]
    motor_client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    motor_db = motor_client[db_name]
    server.db = motor_db
    try:
        app = FastAPI()
        app.add_api_route("/api/auth/activate", server.activate, methods=["POST"])
        app.add_api_route("/api/auth/forgot-password", server.forgot_password, methods=["POST"])
        app.add_api_route("/api/auth/invitations/inspect", server.inspect_invitation, methods=["POST"])
        app.add_api_route("/api/auth/login", server.login, methods=["POST"])
        app.add_api_route("/api/auth/me", server.me, methods=["GET"])
        app.add_api_route("/api/auth/register", server.register, methods=["POST"], status_code=201)
        app.add_api_route("/api/auth/refresh", server.refresh, methods=["POST"])
        app.add_api_route("/api/auth/resend-activation", server.resend_activation, methods=["POST"])
        app.add_api_route("/api/auth/reset-password", server.reset_password, methods=["POST"])
        app.include_router(
            build_router(motor_db, server.current_user, server.require, server.hash_password, server.create_invitation),
            prefix="/api",
        )
        app.include_router(build_arena_router(motor_db, server.current_user, server.require), prefix="/api")
        with TestClient(app) as http:
            yield {"db": test_db, "http": http, "server": server}
    finally:
        server.db = original_db
        motor_client.close()
        client.drop_database(db_name)
        client.close()


def test_existing_registration_and_login_remain_available(api, monkeypatch):
    db, http, server = api["db"], api["http"], api["server"]
    deliveries = []

    async def email_stub(*, to, subject, html):
        deliveries.append((to, subject, html))
        return None if len(deliveries) == 1 else "test-provider-id"

    monkeypatch.setattr(server.emailer, "send_email", email_stub)
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("FRONTEND_URL", "http://localhost:3000")
    suffix = uuid.uuid4().hex[:8]
    topic_id = "TEST-" + suffix
    db.topics.insert_one({"topic_id": topic_id, "title": "People test topic", "enabled": True})
    db.settings.insert_one({"key": "timeline", "application_override": "open"})
    payload = {
        "email": f"leader-{suffix}@example.com",
        "password": "Valid!Leader2026",
        "name": "Registration test leader",
        "usn": f"TL{suffix.upper()}",
        "team_name": f"Registration test {suffix}",
        "college": "Test College",
        "phone": "9876543210",
        "topic_id": topic_id,
        "members": [{
            "name": "Registration test member",
            "usn": f"TM{suffix.upper()}",
            "email": f"member-{suffix}@example.com",
        }],
    }

    incomplete = {**payload, "members": [{"name": "Incomplete member"}]}
    assert http.post("/api/auth/register", json=incomplete).status_code == 422
    duplicate_email = {
        **payload,
        "members": [{
            "name": "Duplicate email member",
            "usn": f"TM{suffix}X",
            "email": payload["email"],
        }],
    }
    assert http.post("/api/auth/register", json=duplicate_email).status_code == 400

    registered = http.post("/api/auth/register", json=payload)
    assert registered.status_code == 201, registered.text
    data = registered.json()
    assert data["verification_required"] is False
    assert data["member_invitations"][0]["email_status"] == "failed"
    first_link = re.search(
        r"http://localhost:3000/activate\?token=([A-Za-z0-9_-]+)",
        deliveries[0][2],
    )
    assert first_link and deliveries[0][0] == payload["members"][0]["email"]
    assert http.get(
        "/api/participant/dashboard",
        headers={"Authorization": f"Bearer {data['token']}"},
    ).status_code == 200
    login = http.post(
        "/api/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    assert login.status_code == 200
    assert login.json()["user"]["team_id"] == data["team_id"]
    assert db.users.find_one({"email": payload["email"]})["is_active"] is True
    member_doc = db.users.find_one({"email": payload["members"][0]["email"]})
    assert member_doc["is_active"] is False
    assert member_doc["team_id"] == data["team_id"]
    member_membership = db.team_memberships.find_one({"team_id": data["team_id"], "role": "member"})
    assert member_membership["invitation_email_status"] == "failed"
    _, admin_auth = _auth_for(db, server, "admin")
    admin_team = next(
        team for team in http.get("/api/admin/teams", headers=admin_auth).json()
        if team["team_id"] == data["team_id"]
    )
    admin_member = next(row for row in admin_team["memberships"] if row["role"] == "member")
    assert admin_member["invitation_email_status"] == "failed"
    assert admin_member["account_active"] is False

    expired_at = server.now_utc() - timedelta(seconds=1)
    db.invitations.update_one(
        {"invitation_id": data["member_invitations"][0]["invitation_id"]},
        {"$set": {"expires_at": expired_at}},
    )
    db.team_memberships.update_one(
        {"membership_id": member_membership["membership_id"]},
        {"$set": {"invitation_expires_at": expired_at}},
    )
    expired_team = next(
        team for team in http.get("/api/admin/teams", headers=admin_auth).json()
        if team["team_id"] == data["team_id"]
    )
    assert next(row for row in expired_team["memberships"] if row["role"] == "member")["invitation_expired"]
    assert http.post(
        "/api/auth/invitations/inspect", json={"token": first_link.group(1)}
    ).status_code == 400
    resent = http.post(
        f"/api/admin/teams/{data['team_id']}/members/{member_membership['membership_id']}/invitation/resend",
        headers=admin_auth,
    )
    assert resent.status_code == 200 and resent.json()["email_status"] == "sent", resent.text
    second_link = re.search(
        r"http://localhost:3000/activate\?token=([A-Za-z0-9_-]+)",
        deliveries[-1][2],
    )
    assert second_link and deliveries[-1][0] == payload["members"][0]["email"]

    activated = http.post(
        "/api/auth/activate",
        json={"token": second_link.group(1), "password": "Valid!Member2026"},
    )
    assert activated.status_code == 200, activated.text
    assert activated.json()["user"]["role"] == "member"
    assert activated.json()["user"]["team_id"] == data["team_id"]
    assert http.post(
        "/api/auth/activate",
        json={"token": second_link.group(1), "password": "Valid!Member2026"},
    ).status_code == 400
    member_login = http.post(
        "/api/auth/login",
        json={"email": payload["members"][0]["email"], "password": "Valid!Member2026"},
    )
    assert member_login.status_code == 200 and member_login.json()["user"]["role"] == "member"
    member_auth = {"Authorization": f"Bearer {member_login.json()['token']}"}
    assert http.get("/api/participant/dashboard", headers=member_auth).json()["team"]["team_id"] == data["team_id"]
    assert http.get("/api/arena/me", headers=member_auth).status_code == 200
    abstract = http.post(
        "/api/applications/abstract",
        headers=member_auth,
        data={"topic_id": topic_id},
        files={"file": ("abstract.pdf", b"%PDF-1.4 test", "application/pdf")},
    )
    assert abstract.status_code == 403


def test_admin_can_invite_legacy_team_member(api, monkeypatch):
    db, http, server = api["db"], api["http"], api["server"]
    deliveries = []

    async def email_stub(*, to, subject, html):
        deliveries.append((to, subject, html))
        return "test-provider-id"

    monkeypatch.setattr(server.emailer, "send_email", email_stub)
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("FRONTEND_URL", "http://localhost:3000")
    team_id = str(ObjectId())
    team = {"team_id": team_id, "name": "Legacy team", "college": "Legacy college"}
    membership = {
        "membership_id": f"LEGACY-{uuid.uuid4().hex[:8]}",
        "team_id": team_id,
        "user_id": None,
        "name": "Legacy member",
        "email": f"legacy-{uuid.uuid4().hex[:8]}@example.com",
        "usn": f"LM{uuid.uuid4().hex[:6].upper()}",
        "role": "member",
        "status": "pending",
    }
    db.teams.insert_one(team)
    db.team_memberships.insert_one(membership)
    _, admin_auth = _auth_for(db, server, "admin")

    resent = http.post(
        f"/api/admin/teams/{team_id}/members/{membership['membership_id']}/invitation/resend",
        headers=admin_auth,
    )
    assert resent.status_code == 200 and resent.json()["email_status"] == "sent", resent.text
    member = db.users.find_one({"email": membership["email"]})
    assert member["role"] == "member" and member["team_id"] == team_id
    activation_link = re.search(
        r"http://localhost:3000/activate\?token=([A-Za-z0-9_-]+)",
        deliveries[0][2],
    )
    assert activation_link
    activated = http.post(
        "/api/auth/activate",
        json={"token": activation_link.group(1), "password": "Valid!Member2026"},
    )
    assert activated.status_code == 200
    assert activated.json()["user"]["team_id"] == team_id


def test_admin_delete_team_cascades_only_selected_team(api):
    db, http, server = api["db"], api["http"], api["server"]
    suffix = uuid.uuid4().hex[:8]
    team_id = str(ObjectId())
    leader_id = ObjectId(team_id)
    leader, team_auth = _auth_for(db, server, "team", team_id, leader_id)
    member, _ = _auth_for(db, server, "member", team_id)
    other_team_id = str(ObjectId())
    other_leader, _ = _auth_for(db, server, "team", other_team_id)
    _, admin_auth = _auth_for(db, server, "admin")
    db.teams.insert_many([
        {"team_id": team_id, "leader_id": team_id, "name": f"Delete test {suffix}"},
        {"team_id": other_team_id, "leader_id": str(other_leader["_id"]), "name": f"Keep test {suffix}"},
    ])
    db.team_memberships.insert_many([
        {"team_id": team_id, "user_id": team_id},
        {"team_id": team_id, "user_id": str(member["_id"])},
        {"team_id": other_team_id, "user_id": str(other_leader["_id"])},
    ])
    db.applications.insert_many([{"application_id": f"DEL-{suffix}", "team_id": team_id},
                                 {"application_id": f"KEEP-{suffix}", "team_id": other_team_id}])
    db.payments.insert_one({"payment_id": f"DEL-{suffix}", "team_id": team_id})
    db.submissions.insert_one({"submission_id": f"DEL-{suffix}", "team_id": team_id})
    db.project_history.insert_one({"history_id": f"DEL-{suffix}", "team_id": team_id})
    db.evaluations.insert_one({"team_id": team_id, "judge_id": "test"})
    db.judge_assignments.insert_one({"team_id": team_id, "judge_id": "test"})
    db.arena_xp.insert_one({"user_id": team_id, "ref": f"DEL-{suffix}"})
    db.sessions.insert_one({"sid": f"DEL-{suffix}", "user_id": str(member["_id"])})
    db.invitations.insert_one({"invitation_id": f"DEL-{suffix}", "team_id": team_id})
    db.notifications.insert_one({"notification_id": f"DEL-{suffix}", "user_id": str(member["_id"])})

    gridfs = GridFSBucket(db)
    deleted_file = gridfs.upload_from_stream(f"abstract-{suffix}.pdf", b"%PDF-1.4 test")
    kept_file = gridfs.upload_from_stream(f"abstract-keep-{suffix}.pdf", b"%PDF-1.4 keep")
    db.files.insert_many([
        {"file_id": f"FILE-DEL-{suffix}", "gridfs_id": str(deleted_file), "team_id": team_id,
         "owner_id": team_id, "kind": "abstract", "is_deleted": False},
        {"file_id": f"FILE-KEEP-{suffix}", "gridfs_id": str(kept_file), "team_id": other_team_id,
         "owner_id": str(other_leader["_id"]), "kind": "abstract", "is_deleted": False},
    ])
    before_overview = http.get("/api/admin/overview", headers=admin_auth)
    assert before_overview.status_code == 200

    http.cookies.clear()
    assert http.delete(f"/api/admin/teams/{team_id}").status_code == 401
    assert http.delete(f"/api/admin/teams/{team_id}", headers=team_auth).status_code == 403
    assert db.teams.find_one({"team_id": team_id})

    deleted = http.delete(f"/api/admin/teams/{team_id}", headers=admin_auth)
    assert deleted.status_code == 200, deleted.text
    assert db.teams.find_one({"team_id": team_id}) is None
    assert db.users.find_one({"_id": leader_id}) is None
    assert db.users.find_one({"_id": member["_id"]}) is None
    assert db.users.find_one({"_id": other_leader["_id"]}) is not None
    assert db.team_memberships.count_documents({"team_id": team_id}) == 0
    assert db.applications.find_one({"team_id": team_id}) is None
    assert db.payments.find_one({"team_id": team_id}) is None
    assert db.submissions.find_one({"team_id": team_id}) is None
    assert db.project_history.find_one({"team_id": team_id}) is None
    assert db.evaluations.find_one({"team_id": team_id}) is None
    assert db.judge_assignments.find_one({"team_id": team_id}) is None
    assert db.arena_xp.find_one({"user_id": team_id}) is None
    assert db.sessions.find_one({"sid": f"DEL-{suffix}"}) is None
    assert db.invitations.find_one({"invitation_id": f"DEL-{suffix}"}) is None
    assert db.notifications.find_one({"notification_id": f"DEL-{suffix}"}) is None
    assert db.files.find_one({"file_id": f"FILE-DEL-{suffix}"}) is None
    assert db.files.find_one({"file_id": f"FILE-KEEP-{suffix}"}) is not None
    with pytest.raises(NoFile):
        gridfs.open_download_stream(deleted_file)
    with gridfs.open_download_stream(kept_file) as stored:
        assert stored.read() == b"%PDF-1.4 keep"
    overview = http.get("/api/admin/overview", headers=admin_auth)
    assert overview.status_code == 200
    assert overview.json()["teams"] == before_overview.json()["teams"] - 1
    assert overview.json()["participants"] == before_overview.json()["participants"] - 2
    assert overview.json()["applications"] == before_overview.json()["applications"] - 1


def test_timeline_ist_dates_persist_and_drive_auto_portals(api):
    db, http, server = api["db"], api["http"], api["server"]
    _, admin_auth = _auth_for(db, server, "admin")
    now = server.now_utc()
    ist = timezone(timedelta(hours=5, minutes=30))
    timeline = http.get("/api/admin/timeline", headers=admin_auth).json()
    timeline.update({
        "application_open": (now - timedelta(hours=1)).astimezone(ist).isoformat(),
        "application_close": (now + timedelta(hours=1)).astimezone(ist).isoformat(),
        "abstract_deadline": (now + timedelta(hours=2)).astimezone(ist).isoformat(),
        "project_open": (now + timedelta(hours=2)).astimezone(ist).isoformat(),
        "project_close": (now + timedelta(hours=3)).astimezone(ist).isoformat(),
        "application_override": "auto",
        "abstract_override": "auto",
        "project_override": "auto",
    })

    saved = http.put("/api/admin/timeline", headers=admin_auth, json=timeline)
    assert saved.status_code == 200, saved.text
    reloaded = http.get("/api/admin/timeline", headers=admin_auth)
    assert reloaded.status_code == 200
    assert reloaded.json()["application_open"] == timeline["application_open"]
    assert reloaded.json()["project_open"] == timeline["project_open"]
    portals = http.get("/api/public/meta").json()["portals"]
    assert portals == {"application": True, "abstract": True, "project": False}


def test_registration_confirmation_updates_every_account_and_activity(api, monkeypatch):
    db, http, server = api["db"], api["http"], api["server"]
    deliveries = []

    async def email_stub(**kwargs):
        deliveries.append(kwargs)
        return "test-provider-id"

    monkeypatch.setattr(server.emailer, "send_email", email_stub)
    monkeypatch.setenv("FRONTEND_URL", "https://testserver")
    team_id = str(ObjectId())
    leader_id = ObjectId(team_id)
    leader, _ = _auth_for(db, server, "team", team_id, leader_id)
    member, _ = _auth_for(db, server, "member", team_id)
    _, admin_auth = _auth_for(db, server, "admin")
    db.teams.insert_one({
        "team_id": team_id,
        "leader_id": team_id,
        "name": "People test team",
        "registration_status": "registered",
    })
    for user, role in ((leader, "leader"), (member, "member")):
        db.team_memberships.insert_one({
            "membership_id": uuid.uuid4().hex,
            "team_id": team_id,
            "user_id": str(user["_id"]),
            "name": user["name"],
            "email": user["email"],
            "role": role,
            "status": "active" if role == "leader" else "invited",
        })

    raw_activation = secrets.token_urlsafe(32)
    db.invitations.insert_one({
        "token_hash": hashlib.sha256(raw_activation.encode()).hexdigest(),
        "target_user_id": str(member["_id"]),
        "team_id": team_id,
        "purpose": "member_activation",
        "used_at": None,
        "revoked_at": None,
        "expires_at": server.now_utc() + timedelta(hours=1),
    })
    raw_leader_activation = secrets.token_urlsafe(32)
    db.invitations.insert_one({
        "token_hash": hashlib.sha256(raw_leader_activation.encode()).hexdigest(),
        "target_user_id": str(leader["_id"]),
        "team_id": team_id,
        "purpose": "verify_email",
        "used_at": None,
        "revoked_at": None,
        "expires_at": server.now_utc() + timedelta(hours=1),
    })

    no_response = http.patch(
        f"/api/admin/teams/{team_id}/registration",
        headers=admin_auth,
        json={"confirmed": False},
    )
    assert no_response.status_code == 200
    assert db.teams.find_one({"team_id": team_id})["registration_review_status"] == "not_confirmed"
    assert all(not db.users.find_one({"_id": user["_id"]})["is_active"] for user in (leader, member))
    assert db.sessions.count_documents({"user_id": {"$in": [str(leader_id), str(member["_id"])]}, "revoked_at": None}) == 0
    participants = http.get("/api/admin/participants", headers=admin_auth).json()
    assert all(not row["is_active"] for row in participants if row.get("team_id") == team_id)
    assert all(row["registration_review_status"] == "not_confirmed" for row in participants if row.get("team_id") == team_id)
    team_payload = next(row for row in http.get("/api/admin/teams", headers=admin_auth).json() if row["team_id"] == team_id)
    assert all(not member_row["account_active"] for member_row in team_payload["memberships"])
    blocked_login = http.post(
        "/api/auth/login",
        json={"email": leader["email"], "password": "Valid!Leader2026"},
    )
    assert blocked_login.status_code == 403
    blocked_activation = http.post(
        "/api/auth/activate",
        json={"token": raw_activation, "password": "Valid!Member2026"},
    )
    assert blocked_activation.status_code == 400
    assert http.post(
        "/api/auth/activate",
        json={"token": raw_leader_activation},
    ).status_code == 400

    yes_response = http.patch(
        f"/api/admin/teams/{team_id}/registration",
        headers=admin_auth,
        json={"confirmed": True},
    )
    assert yes_response.status_code == 200
    assert db.teams.find_one({"team_id": team_id})["registration_status"] == "registered"
    assert all(db.users.find_one({"_id": user["_id"]})["is_active"] for user in (leader, member))
    assert http.patch(
        f"/api/admin/teams/{team_id}/registration",
        headers=admin_auth,
        json={"confirmed": True},
    ).status_code == 200
    assert db.notifications.count_documents({"user_id": team_id, "kind": {"$in": ["registration_confirmed", "registration_not_confirmed"]}}) == 2

    resend = http.post("/api/auth/resend-activation", json={"email": member["email"]})
    assert resend.status_code == 200
    activation_link = re.search(r"https://testserver/activate\?token=([A-Za-z0-9_-]+)", deliveries[-1]["html"])
    assert activation_link
    activated = http.post(
        "/api/auth/activate",
        json={"token": activation_link.group(1), "password": "Valid!Member2026"},
    )
    assert activated.status_code == 200
    assert db.users.find_one({"_id": member["_id"]})["password_hash"]
    assert db.users.find_one({"_id": member["_id"]})["is_active"] is True
    member_login = http.post(
        "/api/auth/login",
        json={"email": member["email"], "password": "Valid!Member2026"},
    )
    leader_login = http.post(
        "/api/auth/login",
        json={"email": leader["email"], "password": "Valid!Leader2026"},
    )
    assert member_login.status_code == leader_login.status_code == 200
    _, leader_auth = _auth_for(db, server, "team", team_id, leader_id)
    activity = http.get("/api/participant/dashboard", headers=leader_auth).json()["notifications"]
    messages = [notice["message"] for notice in activity]
    assert any("registration has been confirmed" in message for message in messages)
    assert any("registration is not confirmed" in message for message in messages)


def test_abstract_status_activity_is_transition_only(api, monkeypatch):
    db, http, server = api["db"], api["http"], api["server"]
    async def email_stub(**_kwargs):
        return "test-provider-id"

    monkeypatch.setattr(server.emailer, "send_email", email_stub)
    team_id = str(ObjectId())
    leader_id = ObjectId(team_id)
    leader, _ = _auth_for(db, server, "team", team_id, leader_id)
    _, admin_auth = _auth_for(db, server, "admin")
    db.teams.insert_one({
        "team_id": team_id,
        "leader_id": team_id,
        "name": "People test team",
        "registration_status": "registered",
        "registration_review_status": "confirmed",
    })
    db.applications.insert_one({
        "application_id": "TEST-" + uuid.uuid4().hex,
        "team_id": team_id,
        "status": "pending",
        "history": [],
        "team_name": "People test team",
        "topic_title": "People test topic",
    })
    application_id = db.applications.find_one({"team_id": team_id})["application_id"]

    for status in ("under_review", "selected", "rejected", "pending", "pending"):
        response = http.patch(
            f"/api/admin/applications/{application_id}",
            headers=admin_auth,
            json={"status": status, "admin_notes": "Test review"},
        )
        assert response.status_code == 200, response.text

    notifications = list(db.notifications.find({"user_id": team_id, "kind": {"$regex": "^abstract_"}}))
    assert [notice["kind"] for notice in notifications].count("abstract_under_review") == 1
    assert [notice["kind"] for notice in notifications].count("abstract_selected") == 1
    assert [notice["kind"] for notice in notifications].count("abstract_rejected") == 1
    assert [notice["kind"] for notice in notifications].count("abstract_pending") == 1
    assert db.teams.find_one({"team_id": team_id})["registration_review_status"] == "confirmed"
    assert db.users.find_one({"_id": leader_id})["is_active"] is True


def test_password_reset_mail_link_hash_and_single_use(api, monkeypatch):
    db, http, server = api["db"], api["http"], api["server"]
    deliveries = []

    async def email_stub(*, to, subject, html):
        deliveries.append((to, subject, html))
        return "test-provider-id"

    monkeypatch.setattr(server.emailer, "send_email", email_stub)
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("FRONTEND_URL", "http://localhost:3000")
    user, _ = _auth_for(db, server, "team", str(ObjectId()))
    user["email"] = f"reset-{user['_id']}@example.com"
    db.users.update_one({"_id": user["_id"]}, {"$set": {"email": user["email"]}})

    expected = {"ok": True, "message": "If an active account matches, a reset link will be sent."}
    requested = http.post("/api/auth/forgot-password", json={"email": user["email"]})
    unknown = http.post("/api/auth/forgot-password", json={"email": f"missing-{user['_id']}@example.com"})
    assert requested.status_code == unknown.status_code == 200
    assert requested.json() == unknown.json() == expected
    assert len(deliveries) == 1

    link = re.search(r"http://localhost:3000/reset-password\?token=([A-Za-z0-9_-]+)", deliveries[0][2])
    assert link
    raw_token = link.group(1)
    token_record = db.password_reset_tokens.find_one({"user_id": str(user["_id"])})
    assert token_record["token_hash"] == hashlib.sha256(raw_token.encode()).hexdigest()
    assert raw_token not in str(token_record)

    reset = http.post(
        "/api/auth/reset-password",
        json={"token": raw_token, "password": "Valid!Reset2026"},
    )
    replay = http.post(
        "/api/auth/reset-password",
        json={"token": raw_token, "password": "Valid!Reset2026"},
    )
    assert reset.status_code == 200
    assert replay.status_code == 400
    assert db.password_reset_tokens.find_one({"_id": token_record["_id"]})["used_at"] is not None
    saved_user = db.users.find_one({"_id": user["_id"]})
    assert server.bcrypt.checkpw(b"Valid!Reset2026", saved_user["password_hash"].encode())
    assert db.sessions.count_documents({"user_id": str(user["_id"]), "revoked_at": None}) == 0
    assert http.post(
        "/api/auth/login",
        json={"email": user["email"], "password": "Valid!Reset2026"},
    ).status_code == 200

    requested_again = http.post("/api/auth/forgot-password", json={"email": user["email"]})
    assert requested_again.status_code == 200
    expired_link = re.search(r"http://localhost:3000/reset-password\?token=([A-Za-z0-9_-]+)", deliveries[-1][2])
    assert expired_link
    db.password_reset_tokens.update_one(
        {"token_hash": hashlib.sha256(expired_link.group(1).encode()).hexdigest()},
        {"$set": {"expires_at": server.now_utc() - timedelta(seconds=1)}},
    )
    assert http.post(
        "/api/auth/reset-password",
        json={"token": expired_link.group(1), "password": "Valid!Reset2026"},
    ).status_code == 400


def test_email_link_validation_is_environment_aware(api, monkeypatch):
    server = api["server"]
    monkeypatch.setenv("APP_ENV", "development")
    for template in (
        server.emailer.password_reset_email("Validation test", "http://localhost:3000/reset-password?token=DIAGNOSTIC_ONLY"),
        server.emailer.judge_invitation_email("Validation test", "http://127.0.0.1:3000/activate?token=DIAGNOSTIC_ONLY"),
    ):
        server.emailer._assert_safe_email(*template)

    external = server.emailer.password_reset_email(
        "Validation test", "http://external.test/reset-password?token=DIAGNOSTIC_ONLY",
    )
    with pytest.raises(ValueError, match="G3: every email link and asset must use absolute HTTPS") as error:
        server.emailer._assert_safe_email(*external)
    assert "DIAGNOSTIC_ONLY" not in str(error.value)

    monkeypatch.setenv("APP_ENV", "production")
    local = server.emailer.judge_invitation_email(
        "Validation test", "http://localhost:3000/activate?token=DIAGNOSTIC_ONLY",
    )
    with pytest.raises(ValueError, match="G3: every email link and asset must use absolute HTTPS"):
        server.emailer._assert_safe_email(*local)
    production_link = server.emailer.judge_invitation_email(
        "Validation test", "https://judges.sankalp.test/activate?token=DIAGNOSTIC_ONLY",
    )
    server.emailer._assert_safe_email(*production_link)


def test_production_rejects_local_http_frontend_url(api, monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("FRONTEND_URL", "http://localhost:3000")
    response = api["http"].post("/api/auth/forgot-password", json={"email": "unknown@example.net"})
    assert response.status_code == 500
    assert "must use HTTPS" in response.json()["detail"]


def test_forgot_password_rate_limit_returns_retry_after(api, monkeypatch):
    db, http = api["db"], api["http"]
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("FRONTEND_URL", "http://localhost:3000")
    db.rate_limits.delete_many({"key": "forgot:testclient"})
    for _ in range(5):
        response = http.post("/api/auth/forgot-password", json={"email": "unknown@example.net"})
        assert response.status_code == 200
    limited = http.post("/api/auth/forgot-password", json={"email": "unknown@example.net"})
    assert limited.status_code == 429
    assert 0 < int(limited.headers["retry-after"]) <= 3600
    assert limited.json()["detail"] == "Too many requests. Please wait and try again."


def test_local_http_auth_session_cookies_and_expected_unauthenticated_401(api, monkeypatch):
    db, http, server = api["db"], api["http"], api["server"]
    monkeypatch.setenv("APP_ENV", "development")
    http.cookies.clear()
    assert http.get("/api/auth/me").status_code == 401
    assert http.post("/api/auth/refresh").status_code == 401

    user, _ = _auth_for(db, server, "team", str(ObjectId()))
    login = http.post("/api/auth/login", json={"email": user["email"], "password": "Valid!Leader2026"})
    assert login.status_code == 200
    set_cookies = login.headers.get_list("set-cookie")
    assert all("secure" not in item.lower() for item in set_cookies)
    assert http.get("/api/auth/me").status_code == 200
    refreshed = http.post("/api/auth/refresh")
    assert refreshed.status_code == 200
    assert all("secure" not in item.lower() for item in refreshed.headers.get_list("set-cookie"))
    assert http.get("/api/auth/me").status_code == 200

    monkeypatch.setenv("APP_ENV", "production")
    production_user, _ = _auth_for(db, server, "team", str(ObjectId()))
    production_login = http.post(
        "/api/auth/login",
        json={"email": production_user["email"], "password": "Valid!Leader2026"},
    )
    assert production_login.status_code == 200
    assert all("secure" in item.lower() for item in production_login.headers.get_list("set-cookie"))


def test_judge_invite_resend_activation_login_and_evaluation(api, monkeypatch):
    db, http, server = api["db"], api["http"], api["server"]
    deliveries = []

    async def email_stub(*, to, subject, html):
        deliveries.append((to, subject, html))
        return "test-provider-id"

    monkeypatch.setattr(server.emailer, "send_email", email_stub)
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("FRONTEND_URL", "http://localhost:3000")
    _, admin_auth = _auth_for(db, server, "admin")
    email = f"judge-{uuid.uuid4().hex[:8]}@example.com"
    payload = {"name": "Invitation test judge", "email": email}

    invited = http.post("/api/admin/judges", headers=admin_auth, json=payload)
    assert invited.status_code == 200, invited.text
    judge_id = invited.json()["user"]["id"]
    assert invited.json()["email_status"] == "sent"
    first_link = re.search(r"http://localhost:3000/activate\?token=([A-Za-z0-9_-]+)", deliveries[-1][2])
    assert first_link

    resent = http.post("/api/admin/judges", headers=admin_auth, json=payload)
    assert resent.status_code == 200, resent.text
    assert resent.json()["user"]["id"] == judge_id
    assert resent.json()["email_status"] == "sent"
    assert db.users.count_documents({"email": email, "role": "judge"}) == 1
    assert http.post("/api/auth/invitations/inspect", json={"token": first_link.group(1)}).status_code == 400
    second_link = re.search(r"http://localhost:3000/activate\?token=([A-Za-z0-9_-]+)", deliveries[-1][2])
    assert second_link

    token_hash = hashlib.sha256(second_link.group(1).encode()).hexdigest()
    db.invitations.update_one(
        {"token_hash": token_hash},
        {"$set": {"expires_at": server.now_utc() - timedelta(seconds=1)}},
    )
    assert http.post("/api/auth/invitations/inspect", json={"token": second_link.group(1)}).status_code == 400
    assert http.post(
        "/api/auth/activate",
        json={"token": second_link.group(1), "password": "Valid!Judge2026"},
    ).status_code == 400

    resent_expired = http.post("/api/admin/judges", headers=admin_auth, json=payload)
    assert resent_expired.status_code == 200, resent_expired.text
    assert resent_expired.json()["user"]["id"] == judge_id
    active_link = re.search(r"http://localhost:3000/activate\?token=([A-Za-z0-9_-]+)", deliveries[-1][2])
    assert active_link
    activated = http.post(
        "/api/auth/activate",
        json={"token": active_link.group(1), "password": "Valid!Judge2026"},
    )
    assert activated.status_code == 200, activated.text
    assert activated.json()["user"]["role"] == "judge"
    assert http.post(
        "/api/auth/activate",
        json={"token": active_link.group(1), "password": "Valid!Judge2026"},
    ).status_code == 400
    login = http.post("/api/auth/login", json={"email": email, "password": "Valid!Judge2026"})
    assert login.status_code == 200
    judge_auth = {"Authorization": f"Bearer {login.json()['token']}"}
    assert http.get("/api/admin/judges", headers=judge_auth).status_code == 403

    team_id = str(ObjectId())
    db.teams.insert_one({"team_id": team_id, "name": "Evaluation test team"})
    db.submissions.insert_one({
        "submission_id": f"SUB-{uuid.uuid4().hex[:10].upper()}", "team_id": team_id,
        "status": "draft", "title": "Evaluation test project",
    })
    criterion_id = f"CRT-{uuid.uuid4().hex[:10].upper()}"
    db.judging_criteria.insert_one({
        "criterion_id": criterion_id, "phase": "phase1", "title": "Evaluation test criterion",
        "description": "", "max_marks": 10, "weight": 1, "active": True, "order": 1,
    })
    db.settings.update_one(
        {"key": "judging_windows"}, {"$set": {"key": "judging_windows", "phase1_open": True}}, upsert=True,
    )
    assignment = http.post(
        "/api/admin/judge-assignments", headers=admin_auth,
        json={"judge_id": judge_id, "team_id": team_id, "phases": ["phase1"]},
    )
    assert assignment.status_code == 200, assignment.text
    evaluated = http.put(
        f"/api/judge/evaluations/{team_id}", headers=judge_auth,
        json={"phase": "phase1", "scores": [{"criterion_id": criterion_id, "marks": 8}], "action": "submit"},
    )
    assert evaluated.status_code == 200, evaluated.text
    assert evaluated.json()["status"] == "submitted"
    duplicate_active = http.post("/api/admin/judges", headers=admin_auth, json=payload)
    assert duplicate_active.status_code == 400
