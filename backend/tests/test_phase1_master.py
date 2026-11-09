import base64
import copy
import concurrent.futures
import hashlib
import os
import re
import time
from pathlib import Path

import bcrypt
import pytest
import requests
from bson import ObjectId
from dotenv import load_dotenv
from pymongo import MongoClient


load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")
BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"
CREDS = Path("/app/memory/test_credentials.md")
LEADER_EMAIL = "phase1qa-leader@example.com"
MEMBER_EMAIL = "phase1qa-member@example.com"
LEADER_PASSWORD = "Phase1!Leader2026"
MEMBER_PASSWORD = "Phase1!Member2026"
RESET_PASSWORD = "Phase1!ResetLeader2026"
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl2n6sAAAAASUVORK5CYII=")
PDF = b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF"


@pytest.fixture(scope="module")
def database():
    client = MongoClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]
    settings_before = {key: copy.deepcopy(db.settings.find_one({"key": key}))
                       for key in ["payment", "timeline", "judging_windows", "judging_formula"]}
    old = list(db.users.find({"email": {"$in": [LEADER_EMAIL, MEMBER_EMAIL]}}))
    old_ids = [str(x["_id"]) for x in old]
    team_ids = list({x.get("team_id") for x in old if x.get("team_id")})
    db.sessions.delete_many({"user_id": {"$in": old_ids}})
    db.invitations.delete_many({"target_user_id": {"$in": old_ids}})
    db.password_reset_tokens.delete_many({"user_id": {"$in": old_ids}})
    db.notifications.delete_many({"user_id": {"$in": old_ids}})
    db.team_memberships.delete_many({"team_id": {"$in": team_ids}})
    db.applications.delete_many({"team_id": {"$in": team_ids}})
    db.applications.delete_many({"team_name": "Manual Email QA"})
    db.payments.delete_many({"team_id": {"$in": team_ids}})
    db.submissions.delete_many({"team_id": {"$in": team_ids}})
    db.files.delete_many({"team_id": {"$in": team_ids}})
    db.judge_assignments.delete_many({"team_id": {"$in": team_ids}})
    db.evaluations.delete_many({"team_id": {"$in": team_ids}})
    db.judging_criteria.delete_many({"description": "QA criterion"})
    db.teams.delete_many({"team_id": {"$in": team_ids}})
    db.users.delete_many({"email": {"$in": [LEADER_EMAIL, MEMBER_EMAIL]}})
    db.rate_limits.delete_many({"key": {"$regex": "^(register|forgot|reset|activate):"}})
    yield db
    current = list(db.users.find({"email": {"$in": [LEADER_EMAIL, MEMBER_EMAIL]}}))
    current_ids = [str(x["_id"]) for x in current]
    current_teams = list({x.get("team_id") for x in current if x.get("team_id")})
    db.sessions.delete_many({"user_id": {"$in": current_ids}})
    db.invitations.delete_many({"target_user_id": {"$in": current_ids}})
    db.password_reset_tokens.delete_many({"user_id": {"$in": current_ids}})
    db.notifications.delete_many({"user_id": {"$in": current_ids}})
    for collection in ["team_memberships", "applications", "payments", "submissions", "files", "judge_assignments", "evaluations", "project_history"]:
        db[collection].delete_many({"team_id": {"$in": current_teams}})
    db.applications.delete_many({"team_name": "Manual Email QA"})
    db.judging_criteria.delete_many({"description": "QA criterion"})
    db.teams.delete_many({"team_id": {"$in": current_teams}})
    db.users.delete_many({"email": {"$in": [LEADER_EMAIL, MEMBER_EMAIL]}})
    for key, document in settings_before.items():
        if document:
            db.settings.replace_one({"key": key}, document, upsert=True)
        else:
            db.settings.delete_one({"key": key})
    client.close()


def credentials(role):
    text = CREDS.read_text()
    email = re.search(rf"## {role}\n- Email: (.+)", text).group(1)
    password = re.search(rf"## {role}\n- Email: .+\n- Password: (.+)", text).group(1)
    return email, password


def login(email, password):
    response = requests.post(BASE + "/auth/login", json={"email": email, "password": password}, timeout=60)
    assert response.status_code == 200, response.text
    return response.json()["token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def replace_invitation_token(db, email, raw):
    user = db.users.find_one({"email": email})
    result = db.invitations.update_one({"target_user_id": str(user["_id"]), "used_at": None},
                                       {"$set": {"token_hash": hashlib.sha256(raw.encode()).hexdigest()}})
    assert result.matched_count == 1


def test_01_security_headers_and_cors():
    response = requests.get(BASE + "/", headers={"Origin": "https://evil.example"}, timeout=30)
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers
    for name in ("content-security-policy", "strict-transport-security", "x-content-type-options", "referrer-policy", "permissions-policy"):
        assert response.headers.get(name)


def test_02_register_activate_and_individual_login(database):
    topic = requests.get(BASE + "/public/meta", timeout=30).json()["topics"][0]
    payload = {"email": LEADER_EMAIL, "password": LEADER_PASSWORD, "name": "Phase One Leader", "usn": "4AJ26QA001",
               "team_name": "Phase One QA Core", "college": "A J Institute of Engineering and Technology",
               "phone": "9876543210", "topic_id": topic["topic_id"], "members": [
                   {"name": "Phase One Member", "usn": "4AJ26QA002", "email": MEMBER_EMAIL, "college": "", "phone": "9876543211"}]}
    response = requests.post(BASE + "/auth/register", json=payload, timeout=180)
    assert response.status_code == 201, response.text
    assert response.json()["verification_required"] is True
    duplicate = requests.post(BASE + "/auth/register", json=payload, timeout=60)
    assert duplicate.status_code == 400
    leader_token = "qa-leader-activation-token-2026-secure"
    member_token = "qa-member-activation-token-2026-secure"
    replace_invitation_token(database, LEADER_EMAIL, leader_token)
    replace_invitation_token(database, MEMBER_EMAIL, member_token)
    activated = requests.post(BASE + "/auth/activate", json={"token": leader_token, "password": None}, timeout=60)
    assert activated.status_code == 200, activated.text
    member = requests.post(BASE + "/auth/activate", json={"token": member_token, "password": MEMBER_PASSWORD}, timeout=60)
    assert member.status_code == 200, member.text
    assert member.json()["user"]["role"] == "member"
    assert member.json()["user"]["team_id"] == activated.json()["user"]["team_id"]
    assert requests.post(BASE + "/auth/activate", json={"token": member_token, "password": MEMBER_PASSWORD}, timeout=30).status_code == 400
    assert login(LEADER_EMAIL, LEADER_PASSWORD)
    assert login(MEMBER_EMAIL, MEMBER_PASSWORD)


def test_03_authorization_abstract_and_selection(database):
    leader = login(LEADER_EMAIL, LEADER_PASSWORD)
    member = login(MEMBER_EMAIL, MEMBER_PASSWORD)
    admin_email, admin_password = credentials("Admin")
    admin = login(admin_email, admin_password)
    assert requests.get(BASE + "/admin/overview", headers=auth(member), timeout=30).status_code == 403
    topic_id = requests.get(BASE + "/public/meta", timeout=30).json()["topics"][0]["topic_id"]
    invalid = requests.post(BASE + "/applications/abstract", headers=auth(leader), data={"topic_id": topic_id},
                            files={"file": ("fake.pdf", b"not-pdf", "application/pdf")}, timeout=60)
    assert invalid.status_code == 400
    submitted = requests.post(BASE + "/applications/abstract", headers=auth(leader), data={"topic_id": topic_id},
                              files={"file": ("abstract.pdf", PDF, "application/pdf")}, timeout=180)
    assert submitted.status_code == 200, submitted.text
    application = submitted.json()
    assert application["application_id"].startswith("SK26-AB-")
    member_view = requests.get(BASE + "/applications/me", headers=auth(member), timeout=30).json()["application"]
    assert member_view["application_id"] == application["application_id"]
    manual = requests.post(BASE + "/admin/applications/manual", headers=auth(admin), json={"team_name": "Manual Email QA",
        "college": "AJIET", "leader_name": "Manual Leader", "contact_email": "manual@example.com", "topic_id": topic_id,
        "submission_date": "2026-11-01T12:00:00+05:30", "notes": "Received through official email", "status": "pending"}, timeout=60)
    assert manual.status_code == 200, manual.text
    selected = requests.patch(BASE + f"/admin/applications/{application['application_id']}", headers=auth(admin),
                              json={"status": "selected", "admin_notes": "Selected in QA"}, timeout=120)
    assert selected.status_code == 200, selected.text
    assert selected.json()["email_status"] in ("sent", "failed")


def test_04_manual_payment_verification_and_confirmation(database):
    leader = login(LEADER_EMAIL, LEADER_PASSWORD)
    admin_email, admin_password = credentials("Admin")
    admin = login(admin_email, admin_password)
    settings = requests.put(BASE + "/admin/payment-settings", headers=auth(admin), json={"upi_id": "qa-only@upi",
        "bank_details": "QA configuration — not real bank details", "amount": 600, "deadline": "2026-11-25T23:59:00+05:30",
        "instructions": "QA payment instructions only"}, timeout=60)
    assert settings.status_code == 200, settings.text
    qr = requests.post(BASE + "/admin/payment-settings/qr", headers=auth(admin),
                       files={"file": ("qa-qr.png", PNG, "image/png")}, timeout=180)
    assert qr.status_code == 200, qr.text
    participant = requests.get(BASE + "/payments/me", headers=auth(leader), timeout=30).json()
    assert participant["eligible"] is True and participant["settings"]["amount"] == 600
    proof = requests.post(BASE + "/payments/proof", headers=auth(leader), data={"transaction_ref": "QA-UTR-2026-0001",
        "payment_date": "2026-11-01", "amount_paid": "600", "remarks": "QA proof"},
        files={"file": ("payment.png", PNG, "image/png")}, timeout=180)
    assert proof.status_code == 200, proof.text
    assert proof.json()["status"] == "payment_under_verification"
    payment_id = proof.json()["payment_id"]
    approved = requests.patch(BASE + f"/admin/payments/{payment_id}", headers=auth(admin),
                               json={"action": "approve", "reason": "Independently verified in QA"}, timeout=120)
    assert approved.status_code == 200 and approved.json()["payment"]["status"] == "payment_verified"
    before = requests.get(BASE + "/participant/dashboard", headers=auth(leader), timeout=30).json()
    assert before["team"]["registration_status"] == "payment_verified"
    confirmed = requests.post(BASE + f"/admin/payments/{payment_id}/confirm-registration", headers=auth(admin), timeout=120)
    assert confirmed.status_code == 200, confirmed.text
    after = requests.get(BASE + "/participant/dashboard", headers=auth(leader), timeout=30).json()
    assert after["team"]["registration_status"] == "registration_confirmed"


def test_05_project_submission_private_files_and_judging(database):
    leader = login(LEADER_EMAIL, LEADER_PASSWORD)
    member = login(MEMBER_EMAIL, MEMBER_PASSWORD)
    admin_email, admin_password = credentials("Admin")
    judge_email, judge_password = credentials("Judge")
    admin = login(admin_email, admin_password)
    judge = login(judge_email, judge_password)
    timeline = requests.get(BASE + "/admin/timeline", headers=auth(admin), timeout=30).json()
    timeline["project_override"] = "open"
    assert requests.put(BASE + "/admin/timeline", headers=auth(admin), json=timeline, timeout=60).status_code == 200
    project = requests.put(BASE + "/projects/me", headers=auth(leader), json={"title": "Secure Core QA Project",
        "description": "A complete Phase 1 quality assurance project with secure private deliverables.",
        "github_url": "https://github.com/example/sankalp26-qa", "demo_url": "https://example.com/demo", "video_url": ""}, timeout=60)
    assert project.status_code == 200, project.text
    member_edit = requests.put(BASE + "/projects/me", headers=auth(member), json={"title": "Secure Core QA Project",
        "description": "An activated member collaborated on this secure Phase 1 project draft.",
        "github_url": "https://github.com/example/sankalp26-qa", "demo_url": "https://example.com/demo", "video_url": ""}, timeout=60)
    assert member_edit.status_code == 200, member_edit.text
    presentation = requests.post(BASE + "/projects/me/presentation", headers=auth(member),
                                 files={"file": ("presentation.pdf", PDF, "application/pdf")}, timeout=180)
    assert presentation.status_code == 200, presentation.text
    resource = requests.post(BASE + "/projects/me/resources/link", headers=auth(leader), json={"title": "Architecture",
        "resource_type": "external_link", "url": "https://example.com/architecture", "description": "Optional QA resource"}, timeout=60)
    assert resource.status_code == 200
    finalized = requests.post(BASE + "/projects/me/submit", headers=auth(member), timeout=60)
    assert finalized.status_code == 200 and finalized.json()["status"] == "submitted"
    reopened = requests.post(BASE + f"/admin/projects/{finalized.json()['submission_id']}/reopen", headers=auth(admin), timeout=60)
    assert reopened.status_code == 200 and reopened.json()["status"] == "draft"
    assert requests.put(BASE + "/projects/me", headers=auth(member), json={"title": "Secure Core QA Project",
        "description": "The project was reopened by an administrator and edited by an activated member.",
        "github_url": "https://github.com/example/sankalp26-qa", "demo_url": "https://example.com/demo", "video_url": ""}, timeout=60).status_code == 200
    finalized = requests.post(BASE + "/projects/me/submit", headers=auth(leader), timeout=60)
    assert finalized.status_code == 200
    assert requests.get(BASE + f"/files/{presentation.json()['file_id']}", headers=auth(member), timeout=60).status_code == 200
    team_id = finalized.json()["team_id"]
    judge_id = database.users.find_one({"email": judge_email})["_id"]
    assigned = requests.post(BASE + "/admin/judge-assignments", headers=auth(admin), json={"judge_id": str(judge_id),
        "team_id": team_id, "phases": ["phase1", "phase2"]}, timeout=60)
    assert assigned.status_code == 200, assigned.text
    criteria = requests.post(BASE + "/admin/judging/criteria", headers=auth(admin), json={"phase": "phase1",
        "title": "Intermediate progress", "description": "QA criterion", "max_marks": 10, "weight": 1, "active": True}, timeout=60)
    assert criteria.status_code == 200, criteria.text
    criterion = criteria.json()
    assert requests.put(BASE + "/admin/judging/windows", headers=auth(admin),
                        json={"phase1_open": True, "phase2_open": True}, timeout=60).status_code == 200
    judge_rows = requests.get(BASE + "/judge/submissions", headers=auth(judge), timeout=60)
    assert judge_rows.status_code == 200 and any(x["team_id"] == team_id for x in judge_rows.json())
    evaluation = requests.put(BASE + f"/judge/evaluations/{team_id}", headers=auth(judge), json={"phase": "phase1",
        "scores": [{"criterion_id": criterion["criterion_id"], "marks": 8}], "comment": "QA intermediate review", "action": "submit"}, timeout=60)
    assert evaluation.status_code == 200, evaluation.text
    assert evaluation.json()["phase"] == "phase1" and evaluation.json()["status"] == "submitted"
    assert requests.put(BASE + f"/judge/evaluations/{ObjectId()}", headers=auth(judge), json={"phase": "phase1",
        "scores": [{"criterion_id": criterion["criterion_id"], "marks": 8}], "comment": "Unauthorized", "action": "save"}, timeout=30).status_code == 403
    results = requests.get(BASE + "/admin/results", headers=auth(admin), timeout=60).json()
    assert any(x["team_id"] == team_id for x in results["phases"]["phase1"])


def test_06_csrf_reset_session_invalidation_and_credential_record(database):
    session = requests.Session()
    login_response = session.post(BASE + "/auth/login", json={"email": LEADER_EMAIL, "password": LEADER_PASSWORD}, timeout=60)
    assert login_response.status_code == 200
    missing_csrf = session.post(BASE + "/auth/change-password", json={"current_password": "wrong", "new_password": RESET_PASSWORD}, timeout=30)
    assert missing_csrf.status_code == 403
    bearer = login_response.json()["token"]
    assert requests.post(BASE + "/auth/forgot-password", json={"email": "unknown@example.com"}, timeout=30).status_code == 200
    assert requests.post(BASE + "/auth/forgot-password", json={"email": LEADER_EMAIL}, timeout=120).status_code == 200
    raw = "qa-password-reset-token-2026-secure"
    leader = database.users.find_one({"email": LEADER_EMAIL})
    database.password_reset_tokens.delete_many({"token_hash": hashlib.sha256(raw.encode()).hexdigest()})
    database.password_reset_tokens.update_one({"user_id": str(leader["_id"]), "used_at": None},
                                              {"$set": {"token_hash": hashlib.sha256(raw.encode()).hexdigest()}})
    reset = requests.post(BASE + "/auth/reset-password", json={"token": raw, "password": RESET_PASSWORD}, timeout=60)
    assert reset.status_code == 200, reset.text
    assert requests.get(BASE + "/auth/me", headers=auth(bearer), timeout=30).status_code == 401
    assert login(LEADER_EMAIL, RESET_PASSWORD)


def test_07_finalization_is_atomic_against_concurrent_upload(database):
    leader = login(LEADER_EMAIL, RESET_PASSWORD)
    member = login(MEMBER_EMAIL, MEMBER_PASSWORD)
    admin_email, admin_password = credentials("Admin")
    admin = login(admin_email, admin_password)
    current = requests.get(BASE + "/projects/me", headers=auth(leader), timeout=30).json()["submission"]
    assert requests.post(BASE + f"/admin/projects/{current['submission_id']}/reopen", headers=auth(admin), timeout=60).status_code == 200
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        upload = pool.submit(requests.post, BASE + "/projects/me/presentation", headers=auth(member),
                             files={"file": ("concurrent.pdf", PDF, "application/pdf")}, timeout=180)
        time.sleep(0.06)
        finalized = requests.post(BASE + "/projects/me/submit", headers=auth(leader), timeout=60)
        uploaded = upload.result()
    assert finalized.status_code == 200, finalized.text
    after = requests.get(BASE + "/projects/me", headers=auth(leader), timeout=30).json()["submission"]
    assert after["status"] == "submitted"
    assert after["presentation_file"]["file_id"] == finalized.json()["presentation_file"]["file_id"]
    assert uploaded.status_code in (200, 400), uploaded.text