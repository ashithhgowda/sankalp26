# Iteration 2: Abstract upload, shortlist/results emails, member accounts, ARENA (XP, rapid, security, admin, finalize/tie, DQ)
import os, re, time, asyncio
import pytest, requests
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

pytestmark = pytest.mark.skip(reason="Superseded Arena mutation suite paused for Phase 1; preserved by read-only regression coverage")

load_dotenv('/app/frontend/.env')
load_dotenv('/app/backend/.env')
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
API = f"{BASE_URL}/api"
TS = str(int(time.time()))
LEAD = f"delivered+t2lead{TS}@resend.dev"
LEAD2 = f"delivered+t2lead2{TS}@resend.dev"
MEM = f"test_mem_{TS}@example.com"
REAL_TEAMS_GUARD = []  # real non-resend teams we temporarily mark results_email_sent


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro) if False else asyncio.new_event_loop().run_until_complete(coro)


def dbh():
    return AsyncIOMotorClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]


def login(email, pw):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}


S = {}


@pytest.fixture(scope="module", autouse=True)
def setup_module_data():
    A = login("admin@sankalp26.com", "Sankalp@2026")
    S["A"] = A
    S["J"] = login("judge@sankalp26.com", "Judge@2026")
    requests.put(f"{API}/admin/settings", headers=A, json={"phase": "registration"})
    base = {"password": "Team@123", "college": "AJIET", "phone": "9999999999", "track": "V2V Visionaries: Collision Avoidance & Road Safety"}
    r = requests.post(f"{API}/auth/register", json={**base, "email": LEAD, "name": "TEST Lead", "team_name": f"TEST_T2_{TS}",
                                                    "members": [{"name": "Mem", "usn": "4AJ", "email": MEM.upper()}]})
    assert r.status_code == 200, r.text
    S["T"] = {"Authorization": "Bearer " + r.json()["token"]}; S["team_id"] = r.json()["user"]["id"]
    r = requests.post(f"{API}/auth/register", json={**base, "email": LEAD2, "name": "TEST Lead2", "team_name": f"TEST_T2b_{TS}", "members": []})
    assert r.status_code == 200, r.text
    S["T2"] = {"Authorization": "Bearer " + r.json()["token"]}; S["team2_id"] = r.json()["user"]["id"]
    requests.put(f"{API}/admin/settings", headers=A, json={"phase": "hackathon"})
    S["qs"] = requests.get(f"{API}/arena/admin/questions", headers=A).json()
    yield
    # ---- cleanup ----
    requests.post(f"{API}/arena/admin/reopen", headers=A)
    requests.put(f"{API}/arena/admin/settings", headers=A, json={"prize": "", "announcement": ""})
    requests.put(f"{API}/admin/settings", headers=A, json={"phase": "hackathon", "leaderboard_public": True})

    async def clean():
        db = dbh()
        users = await db.users.find({"$or": [{"email": {"$in": [LEAD, LEAD2, MEM]}}, {"team_name": {"$regex": "^TEST_T2"}}]}).to_list(100)
        ids = [str(u["_id"]) for u in users]
        for c in ["arena_attempts", "arena_xp", "arena_badges", "arena_opens", "arena_rapid_runs", "arena_events"]:
            await db[c].delete_many({"user_id": {"$in": ids}})
        await db.arena_settings.update_one({"key": "arena"}, {"$pull": {"disqualified": {"$in": ids}}})
        await db.files.delete_many({"owner_id": {"$in": ids}})
        await db.users.delete_many({"_id": {"$in": [u["_id"] for u in users]}})
        await db.arena_questions.delete_many({"slug": {"$regex": "^custom-"}, "prompt": {"$regex": "^TEST_"}})
        for e in REAL_TEAMS_GUARD:
            await db.users.update_one({"email": e}, {"$unset": {"results_email_sent": ""}})
    run(clean())


def q_by(slug):
    return next(x for x in S["qs"] if x["slug"] == slug)


# ---------- member accounts ----------
def test_member_join_and_unknown():
    r = requests.post(f"{API}/auth/member-join", json={"email": MEM, "password": "Mem@1234", "name": "TEST Member"})
    assert r.status_code == 200, r.text
    assert r.json()["user"]["role"] == "member" and r.json()["user"]["team_name"] == f"TEST_T2_{TS}"
    S["M"] = {"Authorization": "Bearer " + r.json()["token"]}; S["mem_id"] = r.json()["user"]["id"]
    r = requests.post(f"{API}/auth/member-join", json={"email": f"nobody{TS}@x.com", "password": "Mem@1234", "name": "x"})
    assert r.status_code == 400
    r = requests.post(f"{API}/auth/member-join", json={"email": MEM, "password": "Mem@1234", "name": "dup"})
    assert r.status_code == 400


# ---------- security ----------
def test_no_answer_keys_exposed():
    for h in [{}, S["M"]]:
        pub = requests.get(f"{API}/arena/questions", headers=h).json()
        assert len(pub) > 0
        assert all("answer_index" not in q and "explanation" not in q for q in pub)
    st = requests.get(f"{API}/arena/state").json()
    assert st["daily"] is None or "answer_index" not in st["daily"]
    r = requests.post(f"{API}/arena/rapid/start", headers=S["T2"], json={"set": "gates"})
    assert r.status_code == 200, r.text
    assert all("answer_index" not in q and "explanation" not in q for q in r.json()["questions"])
    S["t2_gates_run"] = r.json()["run_id"]


def test_role_guards():
    for h in [S["T"], S["M"]]:
        assert requests.get(f"{API}/arena/admin/questions", headers=h).status_code == 403
        assert requests.get(f"{API}/arena/admin/participants", headers=h).status_code == 403
        assert requests.post(f"{API}/arena/admin/freeze", headers=h, json={"value": True}).status_code == 403
    qid = S["qs"][0]["id"]
    assert requests.post(f"{API}/arena/questions/{qid}/answer", json={"selected": 0}).status_code == 401
    assert requests.post(f"{API}/arena/questions/{qid}/answer", headers=S["A"], json={"selected": 0}).status_code == 403
    assert requests.post(f"{API}/arena/questions/{qid}/answer", headers=S["J"], json={"selected": 0}).status_code == 403


# ---------- XP rules ----------
def test_correct_first_answer_awards_xp():
    q = next(x for x in S["qs"] if x["category"] == "quiz" and x["difficulty"] == "easy" and x["published"])
    S["q_easy"] = q
    requests.post(f"{API}/arena/questions/{q['id']}/open", headers=S["M"])
    r = requests.post(f"{API}/arena/questions/{q['id']}/answer", headers=S["M"], json={"selected": q["answer_index"]}).json()
    assert r["correct"] is True and r["practice"] is False
    reasons = [a["reason"] for a in r["awards"]]
    assert any("First Blood" in x for x in reasons), reasons
    assert r["xp_awarded"] == 20, r  # 10 easy + 10 first blood
    r = requests.post(f"{API}/arena/questions/{q['id']}/answer", headers=S["M"], json={"selected": q["answer_index"]}).json()
    assert r["xp_awarded"] == 0 and r["practice"] is True and "Already attempted" in r["note"]


def test_wrong_then_retry_no_xp():
    q = next(x for x in S["qs"] if x["category"] == "logic" and x["difficulty"] == "medium" and x["published"])
    r = requests.post(f"{API}/arena/questions/{q['id']}/answer", headers=S["M"], json={"selected": (q["answer_index"] + 1) % len(q["options"])}).json()
    assert r["correct"] is False and r["xp_awarded"] == 0 and r["note"]
    r = requests.post(f"{API}/arena/questions/{q['id']}/answer", headers=S["M"], json={"selected": q["answer_index"]}).json()
    assert r["correct"] is True and r["xp_awarded"] == 0 and r["practice"] is True


def test_invalid_option_and_bad_id():
    q = S["q_easy"]
    assert requests.post(f"{API}/arena/questions/{q['id']}/answer", headers=S["M"], json={"selected": 9}).status_code == 400
    assert requests.post(f"{API}/arena/questions/badid/answer", headers=S["M"], json={"selected": 0}).status_code == 404


# ---------- rapid fire ----------
def test_rapid_binary_perfect_then_practice():
    r = requests.post(f"{API}/arena/rapid/start", headers=S["M"], json={"set": "binary"}).json()
    assert r["scored"] is True and r["seconds"] == 60 and len(r["questions"]) == 5
    ans = []
    for q in r["questions"]:
        n = str(int(re.search(r"Convert ([01]+)", q["prompt"]).group(1), 2))
        ans.append(q["options"].index(n))
    res = requests.post(f"{API}/arena/rapid/{r['run_id']}/submit", headers=S["M"], json={"answers": ans}).json()
    assert res["correct"] == 5 and res["xp_awarded"] > 40, res
    assert any("Lightning" in a["reason"] for a in res["awards"])
    assert requests.post(f"{API}/arena/rapid/{r['run_id']}/submit", headers=S["M"], json={"answers": ans}).status_code == 400
    r2 = requests.post(f"{API}/arena/rapid/start", headers=S["M"], json={"set": "binary"}).json()
    assert r2["scored"] is False
    res2 = requests.post(f"{API}/arena/rapid/{r2['run_id']}/submit", headers=S["M"], json={"answers": [0] * 5}).json()
    assert res2["xp_awarded"] == 0 and "Practice" in res2["note"]


def test_rapid_other_user_cannot_submit_run():
    assert requests.post(f"{API}/arena/rapid/{S['t2_gates_run']}/submit", headers=S["M"], json={"answers": [0] * 5}).status_code == 400
    res = requests.post(f"{API}/arena/rapid/{S['t2_gates_run']}/submit", headers=S["T2"], json={"answers": [0] * 5})
    assert res.status_code == 200


# ---------- me / leaderboard ----------
def test_me_and_leaderboard():
    me = requests.get(f"{API}/arena/me", headers=S["M"]).json()
    assert me["xp"] >= 60 and me["rank"] == 1 and "first_blood" in me["badges"] and "lightning" in me["badges"]
    assert me["completed"] == 2
    lb = requests.get(f"{API}/arena/leaderboard").json()
    assert lb["status"] == "live"
    xps = [(x["xp"], x["completed"]) for x in lb["rows"]]
    assert xps == sorted(xps, key=lambda t: (-t[0], -t[1]))
    assert lb["rows"][0]["user_id"] == S["mem_id"]


# ---------- abstract upload ----------
def test_abstract_upload_rules_and_download():
    T = S["T"]
    r = requests.post(f"{API}/submissions/abstract", headers=T, files={"file": ("TEST_abstract.pdf", b"%PDF-1.4 test", "application/pdf")})
    assert r.status_code == 200, r.text
    fid = r.json()["file_id"]; assert r.json()["filename"] == "TEST_abstract.pdf"
    assert requests.post(f"{API}/submissions/abstract", headers=T, files={"file": ("a.exe", b"x", "application/octet-stream")}).status_code == 400
    assert requests.post(f"{API}/submissions/abstract", headers=T, files={"file": ("a.pdf", b"x" * (3 * 1024 * 1024 + 5), "application/pdf")}).status_code == 400
    assert requests.post(f"{API}/submissions/abstract", headers=T, files={"file": ("a.docx", b"PK docx", "application/octet-stream")}).status_code == 200
    r = requests.post(f"{API}/submissions/abstract", headers=T, files={"file": ("TEST_abstract.pdf", b"%PDF-1.4 final", "application/pdf")})
    fid = r.json()["file_id"]
    d = requests.get(f"{API}/files/{fid}", headers=S["A"]); assert d.status_code == 200 and d.content == b"%PDF-1.4 final"
    assert requests.get(f"{API}/files/{fid}", headers=S["J"]).status_code == 200
    assert requests.get(f"{API}/files/{fid}", headers=T).status_code == 200
    assert requests.get(f"{API}/files/{fid}", headers=S["T2"]).status_code == 403
    teams = requests.get(f"{API}/admin/teams", headers=S["A"]).json()
    mine = next(t for t in teams if t["id"] == S["team_id"])
    assert mine["abstract"]["file_id"] == fid


# ---------- shortlist email ----------
def test_shortlist_email_queued_once():
    A = S["A"]
    r = requests.put(f"{API}/admin/teams/{S['team_id']}/shortlist", headers=A, json={"shortlisted": True}).json()
    assert r["email_queued"] is True
    time.sleep(6)
    requests.put(f"{API}/admin/teams/{S['team_id']}/shortlist", headers=A, json={"shortlisted": False})
    r = requests.put(f"{API}/admin/teams/{S['team_id']}/shortlist", headers=A, json={"shortlisted": True}).json()
    assert r["email_queued"] is False
    me = requests.get(f"{API}/auth/me", headers=S["T"]).json()
    u = me.get("user", me)
    assert u.get("shortlisted") is True


def test_results_emails_trigger():
    async def guard():
        db = dbh()
        async for u in db.users.find({"role": "team", "email": {"$not": {"$regex": "@resend\\.dev$"}}, "results_email_sent": {"$ne": True}}):
            REAL_TEAMS_GUARD.append(u["email"])
            await db.users.update_one({"_id": u["_id"]}, {"$set": {"results_email_sent": True}})
    run(guard())
    r = requests.put(f"{API}/admin/settings", headers=S["A"], json={"phase": "results"})
    assert r.status_code == 200
    time.sleep(10)
    async def check():
        db = dbh()
        return [u.get("results_email_sent") for u in await db.users.find({"email": {"$in": [LEAD, LEAD2]}}).to_list(5)]
    sent = run(check())
    requests.put(f"{API}/admin/settings", headers=S["A"], json={"phase": "hackathon"})
    assert sent == [True, True], sent


# ---------- admin arena ----------
def test_admin_settings_validation():
    A = S["A"]
    assert requests.put(f"{API}/arena/admin/settings", headers=A, json={"closes_at": "2026-11-28T09:00"}).status_code == 400
    r = requests.put(f"{API}/arena/admin/settings", headers=A, json={"prize": "TEST prize", "announcement": "TEST ann"}).json()
    assert r["prize"] == "TEST prize" and r["status"] == "live"
    st = requests.get(f"{API}/arena/state").json()
    assert st["prize"] == "TEST prize" and st["announcement"] == "TEST ann"


def test_questions_crud_and_publish():
    A = S["A"]
    body = {"category": "trivia", "difficulty": "easy", "prompt": "TEST_ question?", "options": ["a", "b"], "answer_index": 1, "explanation": "because"}
    assert requests.post(f"{API}/arena/admin/questions", headers=A, json={**body, "answer_index": 5}).status_code == 400
    assert requests.post(f"{API}/arena/admin/questions", headers=A, json={**body, "set": "gates"}).status_code == 400
    c = requests.post(f"{API}/arena/admin/questions", headers=A, json=body).json()
    assert c["slug"].startswith("custom-") and c["xp"] == 10
    ids = [q["id"] for q in requests.get(f"{API}/arena/questions").json()]
    assert c["id"] in ids
    u = requests.put(f"{API}/arena/admin/questions/{c['id']}", headers=A, json={**body, "prompt": "TEST_ edited?", "difficulty": "hard"}).json()
    assert u["prompt"] == "TEST_ edited?" and u["xp"] == 30
    requests.patch(f"{API}/arena/admin/questions/{c['id']}/publish", headers=A, json={"value": False})
    assert c["id"] not in [q["id"] for q in requests.get(f"{API}/arena/questions").json()]
    assert requests.post(f"{API}/arena/questions/{c['id']}/answer", headers=S["M"], json={"selected": 1}).status_code == 404
    requests.delete(f"{API}/arena/admin/questions/{c['id']}", headers=A)
    assert c["id"] not in [q["id"] for q in requests.get(f"{API}/arena/admin/questions", headers=A).json()]


def test_disqualify_hides_and_practice():
    A = S["A"]
    # team2 scores a question first
    q = S["q_easy"]
    r = requests.post(f"{API}/arena/questions/{q['id']}/answer", headers=S["T2"], json={"selected": q["answer_index"]}).json()
    assert r["xp_awarded"] > 0
    requests.post(f"{API}/arena/admin/participants/{S['team2_id']}/disqualify", headers=A, json={"value": True})
    lb = requests.get(f"{API}/arena/leaderboard").json()
    assert S["team2_id"] not in [x["user_id"] for x in lb["rows"]]
    parts = requests.get(f"{API}/arena/admin/participants", headers=A).json()
    p = next(x for x in parts if x["user_id"] == S["team2_id"]); assert p["disqualified"] is True and "flags" in p
    q2 = next(x for x in S["qs"] if x["category"] == "trivia" and x["published"])
    r = requests.post(f"{API}/arena/questions/{q2['id']}/answer", headers=S["T2"], json={"selected": q2["answer_index"]}).json()
    assert r["practice"] is True and r["xp_awarded"] == 0
    assert requests.get(f"{API}/arena/me", headers=S["T2"]).json()["disqualified"] is True
    requests.post(f"{API}/arena/admin/participants/{S['team2_id']}/disqualify", headers=A, json={"value": False})
    assert S["team2_id"] in [x["user_id"] for x in requests.get(f"{API}/arena/leaderboard").json()["rows"]]


def test_freeze_finalize_reopen():
    A = S["A"]
    assert requests.post(f"{API}/arena/admin/finalize", headers=A, json={}).status_code == 400  # live
    assert requests.post(f"{API}/arena/admin/freeze", headers=A, json={"value": True}).json()["status"] == "closed"
    q = next(x for x in S["qs"] if x["category"] == "debug" and x["published"])
    r = requests.post(f"{API}/arena/questions/{q['id']}/answer", headers=S["M"], json={"selected": q["answer_index"]}).json()
    assert r["practice"] is True and r["xp_awarded"] == 0
    f = requests.post(f"{API}/arena/admin/finalize", headers=A, json={}).json()
    assert f["tie"] is False and f["champion"]["user_id"] == S["mem_id"]
    st = requests.get(f"{API}/arena/state").json(); assert st["status"] == "final" and st["champion"]["user_id"] == S["mem_id"]
    assert "arena_champion" in requests.get(f"{API}/arena/me", headers=S["M"]).json()["badges"]
    assert requests.post(f"{API}/arena/admin/reopen", headers=A).json()["status"] == "live"
    assert "arena_champion" not in requests.get(f"{API}/arena/me", headers=S["M"]).json()["badges"]


def test_tie_requires_admin_review():
    A = S["A"]
    async def inject():
        db = dbh()
        for uid in [S["mem_id"], S["team2_id"]]:
            await db.arena_xp.delete_many({"user_id": uid})
            await db.arena_xp.insert_one({"user_id": uid, "ref": "q:tie", "amount": 9999, "reason": "TEST tie", "kind": "question", "created_at": "2026-01-01T00:00:00+00:00"})
    run(inject())
    lb = requests.get(f"{API}/arena/leaderboard").json()
    assert lb["rows"][0]["rank"] == 1 and lb["rows"][1]["rank"] == 1
    requests.post(f"{API}/arena/admin/freeze", headers=A, json={"value": True})
    f = requests.post(f"{API}/arena/admin/finalize", headers=A, json={}).json()
    assert f["tie"] is True and len(f["candidates"]) == 2
    assert requests.post(f"{API}/arena/admin/finalize", headers=A, json={"champion_user_id": S["team_id"]}).status_code == 400
    f = requests.post(f"{API}/arena/admin/finalize", headers=A, json={"champion_user_id": S["team2_id"]}).json()
    assert f["champion"]["user_id"] == S["team2_id"] and f["champion"]["tie_resolved_by_admin"] is True
    assert requests.post(f"{API}/arena/admin/reopen", headers=A).json()["status"] == "live"


# ---------- regression ----------
def test_regression_core():
    assert requests.get(f"{API}/public/meta").status_code == 200
    assert requests.get(f"{API}/leaderboard").status_code == 200
    js = requests.get(f"{API}/judge/submissions", headers=S["J"])
    assert js.status_code == 200 and isinstance(js.json(), list) and all("abstract" in s for s in js.json())
    assert requests.get(f"{API}/submissions/me", headers=S["T"]).status_code == 200
    assert requests.get(f"{API}/submissions/me", headers=S["M"]).status_code == 403
