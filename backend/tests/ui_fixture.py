# Helper for UI tests: `python ui_fixture.py setup` creates TEST_UI team (+member email listed), `cleanup` removes all TEST_UI data
import os, sys, asyncio, requests
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
load_dotenv('/app/frontend/.env'); load_dotenv('/app/backend/.env')
API = os.environ['REACT_APP_BACKEND_URL'].rstrip('/') + "/api"
LEAD, MEM, MEM2 = "delivered+uilead@resend.dev", "test_ui_mem@example.com", "test_ui_mem2@example.com"


def admin():
    return {"Authorization": "Bearer " + requests.post(f"{API}/auth/login", json={"email": "admin@sankalp26.com", "password": "Sankalp@2026"}).json()["token"]}


if sys.argv[1] == "setup":
    A = admin()
    requests.put(f"{API}/admin/settings", headers=A, json={"phase": "registration"})
    r = requests.post(f"{API}/auth/register", json={"email": LEAD, "password": "Team@123", "name": "TEST UI Lead", "team_name": "TEST_UI_Team", "college": "AJIET",
                                                    "phone": "9999999999", "track": "V2V Visionaries: Collision Avoidance & Road Safety",
                                                    "members": [{"name": "M1", "usn": "1", "email": MEM}, {"name": "M2", "usn": "2", "email": MEM2}]})
    print("register", r.status_code, r.text[:200])
    requests.put(f"{API}/admin/settings", headers=A, json={"phase": "hackathon"})
else:
    async def clean():
        db = AsyncIOMotorClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]
        users = await db.users.find({"$or": [{"email": {"$in": [LEAD, MEM, MEM2]}}, {"team_name": {"$regex": "^TEST_UI"}}]}).to_list(50)
        ids = [str(u["_id"]) for u in users]
        for c in ["arena_attempts", "arena_xp", "arena_badges", "arena_opens", "arena_rapid_runs", "arena_events"]:
            await db[c].delete_many({"user_id": {"$in": ids}})
        await db.arena_settings.update_one({"key": "arena"}, {"$pull": {"disqualified": {"$in": ids}}})
        await db.files.delete_many({"owner_id": {"$in": ids}})
        subs = await db.submissions.find({"team_id": {"$in": ids}}).to_list(10)
        await db.evaluations.delete_many({"submission_id": {"$in": [str(s["_id"]) for s in subs]}})
        await db.submissions.delete_many({"team_id": {"$in": ids}})
        await db.users.delete_many({"_id": {"$in": [u["_id"] for u in users]}})
        await db.arena_questions.delete_many({"slug": {"$regex": "^custom-"}, "prompt": {"$regex": "^TEST"}})
        print("cleaned", len(ids))
    asyncio.run(clean())
    A = admin()
    requests.post(f"{API}/arena/admin/reopen", headers=A)
    requests.put(f"{API}/arena/admin/settings", headers=A, json={"prize": "", "announcement": ""})
    requests.put(f"{API}/admin/settings", headers=A, json={"phase": "hackathon", "leaderboard_public": True})
