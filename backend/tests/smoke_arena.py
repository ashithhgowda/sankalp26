import requests, sys, time
API = open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split()[0] + "/api"
s = requests.Session()
def tok(email, pw):
    r = s.post(f"{API}/auth/login", json={"email": email, "password": pw}); r.raise_for_status(); return {"Authorization": "Bearer " + r.json()["token"]}
A = tok("admin@sankalp26.com", "Sankalp@2026")
s.put(f"{API}/admin/settings", headers=A, json={"phase": "registration"})
ts = str(int(time.time()))
lead = f"delivered+{ts}@resend.dev"; mem = f"smoke_mem_{ts}@example.com"
r = s.post(f"{API}/auth/register", json={"email": lead, "password": "Team@123", "name": "Smoke Lead", "team_name": f"SMOKE_{ts}", "college": "AJIET", "phone": "9999999999",
    "track": "V2V Visionaries: Collision Avoidance & Road Safety", "members": [{"name": "Mem", "usn": "4AJ", "email": mem.upper(), "phone": "9876543210"}]})
print("register", r.status_code); T = {"Authorization": "Bearer " + r.json()["token"]}; team_id = r.json()["user"]["id"]
r = s.post(f"{API}/auth/member-join", json={"email": mem, "password": "Mem@1234", "name": "Smoke Member"}); print("member-join", r.status_code, r.json()["user"]["team_name"])
M = {"Authorization": "Bearer " + r.json()["token"]}
print("member-join bad", s.post(f"{API}/auth/member-join", json={"email": "nobody@x.com", "password": "Mem@1234", "name": "x"}).status_code)
qs = s.get(f"{API}/arena/admin/questions", headers=A).json()
print("team cannot admin", s.get(f"{API}/arena/admin/questions", headers=T).status_code)
pub = s.get(f"{API}/arena/questions", headers=M).json(); print("leak answer?", "answer_index" in pub[0])
q = next(x for x in qs if x["slug"] == "quiz-and-gate")
s.post(f"{API}/arena/questions/{q['id']}/open", headers=M)
r = s.post(f"{API}/arena/questions/{q['id']}/answer", headers=M, json={"selected": q["answer_index"]}).json(); print("correct", r["correct"], r["xp_awarded"], [a["reason"] for a in r["awards"]])
r = s.post(f"{API}/arena/questions/{q['id']}/answer", headers=M, json={"selected": q["answer_index"]}).json(); print("replay xp", r["xp_awarded"], r["note"])
q2 = next(x for x in qs if x["slug"] == "quiz-lifo")
r = s.post(f"{API}/arena/questions/{q2['id']}/answer", headers=M, json={"selected": (q2["answer_index"] + 1) % 4}).json(); print("wrong", r["correct"], r["xp_awarded"])
r = s.post(f"{API}/arena/questions/{q2['id']}/answer", headers=M, json={"selected": q2["answer_index"]}).json(); print("retry after wrong xp", r["xp_awarded"])
run = s.post(f"{API}/arena/rapid/start", headers=M, json={"set": "binary"}).json(); print("rapid scored", run["scored"], "leak", "answer_index" in run["questions"][0])
r = s.post(f"{API}/arena/rapid/{run['run_id']}/submit", headers=M, json={"answers": [0, 0, 0, 0, 0]}).json(); print("rapid", r["correct"], r["xp_awarded"], r["note"])
print("resubmit", s.post(f"{API}/arena/rapid/{run['run_id']}/submit", headers=M, json={"answers": [0]*5}).status_code)
run2 = s.post(f"{API}/arena/rapid/start", headers=M, json={"set": "binary"}).json(); print("rapid2 scored", run2["scored"])
me = s.get(f"{API}/arena/me", headers=M).json(); print("me", me["xp"], me["rank"], me["completed"], me["badges"])
lb = s.get(f"{API}/arena/leaderboard").json(); print("lb", lb["status"], [(x["name"], x["xp"]) for x in lb["rows"][:3]])
files = {"file": ("abstract.pdf", b"%PDF-1.4 smoke test", "application/pdf")}
r = s.post(f"{API}/submissions/abstract", headers=T, files=files); print("upload", r.status_code, r.json())
fid = r.json()["file_id"]
print("download admin", s.get(f"{API}/files/{fid}", headers=A).status_code, "member", s.get(f"{API}/files/{fid}", headers=M).status_code)
print("bad ext", s.post(f"{API}/submissions/abstract", headers=T, files={"file": ("a.exe", b"x", "application/octet-stream")}).status_code)
print("big", s.post(f"{API}/submissions/abstract", headers=T, files={"file": ("a.pdf", b"x" * (3 * 1024 * 1024 + 5), "application/pdf")}).status_code)
print("shortlist", s.put(f"{API}/admin/teams/{team_id}/shortlist", headers=A, json={"shortlisted": True}).json())
time.sleep(4)
print("freeze", s.post(f"{API}/arena/admin/freeze", headers=A, json={"value": True}).json()["status"])
r = s.post(f"{API}/arena/questions/{qs[5]['id']}/answer", headers=M, json={"selected": 0}).json(); print("frozen note", r["practice"], r["note"])
print("finalize", s.post(f"{API}/arena/admin/finalize", headers=A, json={}).json())
print("reopen", s.post(f"{API}/arena/admin/reopen", headers=A).json()["status"])
print("TEAM_ID", team_id)
s.put(f"{API}/admin/settings", headers=A, json={"phase": "hackathon"})
