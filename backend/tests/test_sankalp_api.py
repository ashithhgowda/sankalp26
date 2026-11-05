# SANKALP'26 API regression tests: auth, phases, submissions, judging, leaderboard, admin, role protection
import os
import uuid
import bcrypt
import pytest
import requests
from pymongo import MongoClient

pytestmark = pytest.mark.skip(reason="Superseded by the Phase 1 master workflow and rotated-credential security suite")
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/") + "/api"
TRACK = "V2V Visionaries: Collision Avoidance & Road Safety"
ADMIN = ("admin@sankalp26.com", "Sankalp@2026")
JUDGE = ("judge@sankalp26.com", "Judge@2026")


def login(email, pw):
    r = requests.post(f"{BASE_URL}/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200, r.text
    return r


def hdr(tok):
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture(scope="module")
def admin_tok():
    return login(*ADMIN).json()["token"]


@pytest.fixture(scope="module")
def judge_tok():
    return login(*JUDGE).json()["token"]


def set_settings(tok, **kw):
    r = requests.put(f"{BASE_URL}/admin/settings", json=kw, headers=hdr(tok))
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture(scope="module")
def team(admin_tok):
    set_settings(admin_tok, phase="registration", leaderboard_public=True)
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    r = requests.post(f"{BASE_URL}/auth/register", json={
        "email": email, "password": "Team@123", "name": "TEST Leader", "team_name": f"TEST_Team_{email[5:13]}",
        "college": "AJIET", "phone": "9999999999", "track": TRACK,
        "members": [{"name": "M2", "usn": "4JK1", "email": ""}, {"name": "", "usn": "", "email": ""}]})
    assert r.status_code == 200, r.text
    d = r.json()
    yield {"email": email, "token": d["token"], "id": d["user"]["id"], "user": d["user"]}
    requests.delete(f"{BASE_URL}/admin/teams/{d['user']['id']}", headers=hdr(admin_tok))
    set_settings(admin_tok, phase="registration", leaderboard_public=True)


# --- Health/public
def test_root_and_meta():
    assert requests.get(f"{BASE_URL}/").json()["message"].startswith("SANKALP")
    m = requests.get(f"{BASE_URL}/public/meta").json()
    assert len(m["tracks"]) == 6 and "phase" in m


# --- Auth
def test_login_admin_sets_httponly_cookie():
    r = login(*ADMIN)
    assert r.json()["user"]["role"] == "admin"
    assert "password_hash" not in r.json()["user"]
    sc = r.headers.get("set-cookie", "")
    assert "access_token" in sc and "HttpOnly" in sc


def test_bcrypt_hash_format():
    db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    u = db.users.find_one({"email": ADMIN[0]})
    assert u["password_hash"].startswith("$2b$")
    assert bcrypt.checkpw(ADMIN[1].encode(), u["password_hash"].encode())


def test_login_invalid():
    r = requests.post(f"{BASE_URL}/auth/login", json={"email": "nouser_x@example.com", "password": "bad"})
    assert r.status_code == 401


def test_brute_force_lockout():
    email = f"lock_{uuid.uuid4().hex[:6]}@example.com"
    codes = [requests.post(f"{BASE_URL}/auth/login", json={"email": email, "password": "x"}).status_code for _ in range(6)]
    assert codes[:5] == [401] * 5 and codes[5] == 429, codes


def test_me_and_register(team):
    r = requests.get(f"{BASE_URL}/auth/me", headers=hdr(team["token"]))
    assert r.status_code == 200 and r.json()["email"] == team["email"]
    assert r.json()["role"] == "team" and len(r.json()["members"]) == 1


def test_duplicate_register(team):
    r = requests.post(f"{BASE_URL}/auth/register", json={
        "email": team["email"], "password": "Team@123", "name": "x", "team_name": "xx", "college": "xx",
        "phone": "999999", "track": TRACK})
    assert r.status_code == 400


def test_unauth_me():
    assert requests.get(f"{BASE_URL}/auth/me").status_code == 401


# --- Role protection
def test_team_forbidden_admin_judge(team):
    h = hdr(team["token"])
    assert requests.get(f"{BASE_URL}/admin/overview", headers=h).status_code == 403
    assert requests.get(f"{BASE_URL}/admin/teams", headers=h).status_code == 403
    assert requests.get(f"{BASE_URL}/judge/submissions", headers=h).status_code == 403
    assert requests.put(f"{BASE_URL}/admin/settings", json={"phase": "results"}, headers=h).status_code == 403


def test_judge_forbidden_admin(judge_tok):
    assert requests.get(f"{BASE_URL}/admin/overview", headers=hdr(judge_tok)).status_code == 403


# --- Submission + judging + leaderboard flow
SUB = {"title": "TEST Project", "tagline": "tag", "description": "A long enough description",
       "github_url": "https://github.com/x/y", "demo_url": "", "video_url": "https://youtu.be/dQw4w9WgXcQ",
       "tech_stack": ["React", "FastAPI"], "category": TRACK}


def test_submission_create_update(team):
    h = hdr(team["token"])
    assert requests.get(f"{BASE_URL}/submissions/me", headers=h).json()["submission"] is None
    r = requests.put(f"{BASE_URL}/submissions/me", json=SUB, headers=h)
    assert r.status_code == 200 and r.json()["title"] == "TEST Project"
    r = requests.put(f"{BASE_URL}/submissions/me", json={**SUB, "title": "TEST Project v2"}, headers=h)
    assert r.status_code == 200
    g = requests.get(f"{BASE_URL}/submissions/me", headers=h).json()["submission"]
    assert g["title"] == "TEST Project v2" and g["tech_stack"] == ["React", "FastAPI"]


def test_submission_validation(team):
    h = hdr(team["token"])
    assert requests.put(f"{BASE_URL}/submissions/me", json={**SUB, "github_url": "nope"}, headers=h).status_code == 422
    assert requests.put(f"{BASE_URL}/submissions/me", json={**SUB, "category": "bogus"}, headers=h).status_code == 400


def test_judge_evaluate_and_leaderboard(team, judge_tok):
    subs = requests.get(f"{BASE_URL}/judge/submissions", headers=hdr(judge_tok)).json()
    mine = [s for s in subs if s["team_id"] == team["id"]]
    assert mine
    sid = mine[0]["id"]
    r = requests.post(f"{BASE_URL}/judge/evaluations/{sid}", headers=hdr(judge_tok),
                      json={"innovation": 9, "technical": 8.5, "feasibility": 7, "presentation": 6, "comment": "gg"})
    assert r.status_code == 200 and r.json()["total"] == 30.5
    assert requests.post(f"{BASE_URL}/judge/evaluations/{sid}", headers=hdr(judge_tok),
                         json={"innovation": 11, "technical": 1, "feasibility": 1, "presentation": 1}).status_code == 422
    assert requests.post(f"{BASE_URL}/judge/evaluations/badid", headers=hdr(judge_tok),
                         json={"innovation": 1, "technical": 1, "feasibility": 1, "presentation": 1}).status_code == 404
    subs = requests.get(f"{BASE_URL}/judge/submissions", headers=hdr(judge_tok)).json()
    assert [s for s in subs if s["id"] == sid][0]["my_evaluation"]["total"] == 30.5
    lb = requests.get(f"{BASE_URL}/leaderboard").json()
    row = [x for x in lb["rows"] if x["submission_id"] == sid][0]
    assert row["score"] == 30.5 and row["judges"] >= 1 and row["rank"] >= 1


# --- Admin controls & phase rules
def test_admin_overview_teams(admin_tok, team):
    o = requests.get(f"{BASE_URL}/admin/overview", headers=hdr(admin_tok)).json()
    assert o["teams"] >= 1 and "settings" in o
    t = requests.get(f"{BASE_URL}/admin/teams", headers=hdr(admin_tok)).json()
    assert any(x["email"] == team["email"] for x in t)


def test_admin_judge_crud(admin_tok):
    email = f"test_judge_{uuid.uuid4().hex[:6]}@example.com"
    r = requests.post(f"{BASE_URL}/admin/judges", json={"email": email, "name": "TEST Judge", "password": "Judge@1"}, headers=hdr(admin_tok))
    assert r.status_code == 200 and r.json()["role"] == "judge"
    jid = r.json()["id"]
    assert requests.post(f"{BASE_URL}/admin/judges", json={"email": email, "name": "x", "password": "Judge@1"}, headers=hdr(admin_tok)).status_code == 400
    login(email, "Judge@1")
    assert requests.delete(f"{BASE_URL}/admin/judges/{jid}", headers=hdr(admin_tok)).status_code == 200
    j = requests.get(f"{BASE_URL}/admin/judges", headers=hdr(admin_tok)).json()
    assert not any(x["email"] == email for x in j)


def test_leaderboard_hidden(admin_tok, team, judge_tok):
    set_settings(admin_tok, leaderboard_public=False)
    try:
        assert requests.get(f"{BASE_URL}/leaderboard").json()["hidden"] is True
        assert requests.get(f"{BASE_URL}/leaderboard", headers=hdr(team["token"])).json()["hidden"] is True
        assert requests.get(f"{BASE_URL}/leaderboard", headers=hdr(judge_tok)).json()["hidden"] is False
    finally:
        set_settings(admin_tok, leaderboard_public=True)


def test_phase_rules(admin_tok, team):
    try:
        set_settings(admin_tok, phase="hackathon")
        r = requests.post(f"{BASE_URL}/auth/register", json={
            "email": f"test_{uuid.uuid4().hex[:6]}@example.com", "password": "Team@123", "name": "x",
            "team_name": "xx", "college": "xx", "phone": "999999", "track": TRACK})
        assert r.status_code == 400
        assert requests.put(f"{BASE_URL}/submissions/me", json=SUB, headers=hdr(team["token"])).status_code == 200
        set_settings(admin_tok, phase="evaluation")
        r = requests.put(f"{BASE_URL}/submissions/me", json=SUB, headers=hdr(team["token"]))
        assert r.status_code == 400
        set_settings(admin_tok, phase="results", leaderboard_public=False)
        assert requests.get(f"{BASE_URL}/leaderboard").json()["hidden"] is False
    finally:
        s = set_settings(admin_tok, phase="registration", leaderboard_public=True)
        assert s["phase"] == "registration"


def test_admin_delete_team_cascade(admin_tok, judge_tok):
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    r = requests.post(f"{BASE_URL}/auth/register", json={
        "email": email, "password": "Team@123", "name": "x", "team_name": "TEST_Del", "college": "xx",
        "phone": "999999", "track": TRACK}).json()
    tid, tok = r["user"]["id"], r["token"]
    sid = requests.put(f"{BASE_URL}/submissions/me", json=SUB, headers=hdr(tok)).json()["id"]
    assert requests.delete(f"{BASE_URL}/admin/teams/{tid}", headers=hdr(admin_tok)).status_code == 200
    t = requests.get(f"{BASE_URL}/admin/teams", headers=hdr(admin_tok)).json()
    assert not any(x["email"] == email for x in t)
    assert not any(x["submission_id"] == sid for x in requests.get(f"{BASE_URL}/leaderboard").json()["rows"])
    # deleted user's token should be rejected
    assert requests.get(f"{BASE_URL}/auth/me", headers=hdr(tok)).status_code == 401
