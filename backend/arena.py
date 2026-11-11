import hashlib
import random
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Literal

from bson import ObjectId
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from pymongo.errors import DuplicateKeyError

from backend.arena_questions import SEED_QUESTIONS
from backend.arena_generators import generate_sudoku, generate_kenken, validate_grid

CATEGORIES = { 
    "logic": "Brain Teasers & Logic",
    "kenken": "KenKen",
    "predict": "Predict the Output",
    "sudoku": "Sudoku"}
RAPID_SETS = {"binary": ("Binary Blitz", "Convert binary to decimal"), "gates": ("Gate Rush", "Identify the logic gate"),
              "protocols": ("Protocol Match", "Match the protocol to its purpose"), "false": ("Spot the Lie", "Find the incorrect statement")}
DIFF_XP = {"easy": 10, "medium": 20, "hard": 35}



def xp_for(category, difficulty):
    if category == "rapid":
        return 0
    return DIFF_XP[difficulty]
BADGES = {
     "first_blood": ("First Blood", "Your first correct answer", 10),
    "logic_master": ("Logic Master", "Solve 5 logic puzzles", 25),
    "kenken_master": ("KenKen Master", "Solve 5 KenKen puzzles", 25),
    "output_oracle": ("Output Oracle", "Predict 5 outputs correctly", 25),
    "sudoku_master": ("Sudoku Master", "Solve 3 Sudoku puzzles", 25),
    "lightning": ("Lightning Reflex", "Score a perfect rapid-fire run", 30),
    "polymath": ("Polymath", "Complete all four puzzle categories", 40),
    "arena_champion": ("Arena Champion", "Finish #1 when the Arena closes", 0),
}
BADGE_RULES = {"logic_master": ("logic", 5),
    "kenken_master": ("kenken", 5),
    "output_oracle": ("predict", 5),
    "sudoku_master": ("sudoku", 3),}
MILESTONE_XP, DAILY_XP = 25, 10
RAPID_SECONDS, RAPID_GRACE, RAPID_N = 60, 5, 5
PARTICIPANTS = ("team", "member")
IST = timezone(timedelta(hours=5, minutes=30))
DEFAULTS = {
    "key": "arena",
    "starts_at": None,
    "closes_at": "2026-11-28T09:00:00+05:30",
    "prize": "",
    "announcement": "",
    "frozen": False,
    "paused": False,
    "manually_closed": False,
    "finalized": False,
    "champion": None,
    "tie_candidates": [],
    "disqualified": [],
    "enabled_games": {
        "logic": True,
        "kenken": True,
        "predict": True,
        "sudoku": True,
        "rapid": True,
    },
    "daily_enabled": True,
    "difficulty_xp": {"easy": 10, "medium": 20, "hard": 35},
    "daily_xp": 10,
    "rapid_correct_xp": 8,
    "rapid_time_bonus_max": 10,
}


class QuestionIn(BaseModel):
    category: Literal["logic", "kenken", "predict", "sudoku", "rapid"]
    set: Optional[Literal["gates", "protocols", "false"]] = None
    difficulty: Literal["easy", "medium", "hard"]
    prompt: str = Field(min_length=3)
    code: str = ""
    code_lang: str = ""
    options: List[str] = Field(min_length=2, max_length=6)
    answer_index: int = Field(ge=0)
    explanation: str = Field(min_length=3)
    xp: Optional[int] = Field(default=None, ge=0, le=100)
    published: bool = True


class AnswerIn(BaseModel):
    selected: int = Field(ge=0, le=10)


class RapidStartIn(BaseModel):
    set: Literal["binary", "gates", "protocols", "false"]


class RapidSubmitIn(BaseModel):
    answers: List[Optional[int]]


# NEW: Sudoku and KenKen request models
class PuzzleStartIn(BaseModel):
    game: Literal["sudoku", "kenken"]
    difficulty: Literal["easy", "medium", "hard"]


class PuzzleSubmitIn(BaseModel):
    grid: List[List[int]]


class ArenaSettingsIn(BaseModel):
    starts_at: Optional[str] = None
    closes_at: Optional[str] = None
    prize: Optional[str] = None
    announcement: Optional[str] = None


class FinalizeIn(BaseModel):
    champion_user_id: Optional[str] = None


class ArenaControlsIn(BaseModel):
    enabled_games: Optional[Dict[str, bool]] = None
    daily_enabled: Optional[bool] = None
    difficulty_xp: Optional[Dict[str, int]] = None
    daily_xp: Optional[int] = Field(default=None, ge=0, le=50)
    rapid_correct_xp: Optional[int] = Field(default=None, ge=0, le=20)
    rapid_time_bonus_max: Optional[int] = Field(default=None, ge=0, le=20)


class FlagIn(BaseModel):
    value: bool


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def parse_dt(v):
    return datetime.fromisoformat(v) if v else None


def status_of(s):
    if s.get("finalized", False):
        return "final"

    now = datetime.now(timezone.utc)

    if s.get("manually_closed", False):
        return "closed"

    if s.get("closes_at") and now >= parse_dt(s["closes_at"]):
        return "closed"

    if s.get("paused", False):
        return "paused"

    if s.get("starts_at") and now < parse_dt(s["starts_at"]):
        return "upcoming"

    return "live"


def public_q(d):
    return {"id": str(d["_id"]), "slug": d.get("slug"), "category": d["category"], "set": d.get("set"),
            "difficulty": d["difficulty"], "prompt": d["prompt"], "code": d.get("code", ""), "code_lang": d.get("code_lang", ""),
            "options": d["options"], "xp": d["xp"]}


def admin_q(d):
    return {**public_q(d), "answer_index": d["answer_index"], "explanation": d["explanation"], "published": d.get("published", True)}


def binary_question(rng):
    n = rng.randint(5, 63)
    wrong = set()
    while len(wrong) < 3:
        w = n + rng.choice([-8, -4, -2, -1, 1, 2, 4, 8, 16])
        if 0 < w < 128 and w != n:
            wrong.add(w)
    opts = [str(x) for x in list(wrong) + [n]]
    rng.shuffle(opts)
    return {"qid": None, "prompt": f"Convert {n:b}₂ to decimal.", "code": "", "options": opts,
            "answer_index": opts.index(str(n)), "explanation": f"{n:b}₂ = {n}."}


def build_router(db, current_user, require):
    r = APIRouter(prefix="/arena")
    participant = require(*PARTICIPANTS)
    admin = require("admin")

    async def settings():
        s = await db.arena_settings.find_one({"key": "arena"}, {"_id": 0})
        return {**DEFAULTS, **(s or {})}

    async def ensure_game_available(game, snapshot=None):
        s = snapshot if snapshot is not None else await settings()

        if s.get("paused", False):
            raise HTTPException(423, "The Arena is temporarily paused.")

        enabled = s.get("enabled_games", DEFAULTS["enabled_games"])
        if not enabled.get(game, True):
            raise HTTPException(403, f"{game.title()} is currently disabled.")

        return s

    async def optional_user(request: Request):
        try:
            return await current_user(request)
        except HTTPException:
            return None

    async def daily_question():
        today = datetime.now(IST).date().isoformat()
        pool = await db.arena_questions.find({
            "published": True,
            "category": {"$in": ["logic", "predict"]},
            "difficulty": {"$in": ["medium", "hard"]},
        }).sort("slug", 1).to_list(1000)

        if not pool:
            return today, None

        index = int(hashlib.md5(today.encode()).hexdigest(), 16) % len(pool)
        return today, pool[index]
    async def award(user_id, ref, amount, reason, kind):
        try:
            await db.arena_xp.insert_one({"user_id": user_id, "ref": ref, "amount": amount, "reason": reason, "kind": kind, "created_at": now_iso()})
            return {"reason": reason, "xp": amount, "kind": kind}
        except DuplicateKeyError:
            return None

    async def give_badge(user_id, key):
        try:
            await db.arena_badges.insert_one({"user_id": user_id, "badge": key, "created_at": now_iso()})
        except DuplicateKeyError:
            return None
        name, _, xp = BADGES[key]
        return await award(user_id, f"badge:{key}", xp, f"Badge unlocked · {name}", "badge") if xp else {"reason": name, "xp": 0, "kind": "badge"}

    async def check_awards(user_id):
        rows = await db.arena_attempts.aggregate([
            {"$match": {"user_id": user_id, "category": {"$in": list(CATEGORIES.keys())}}},
            {"$group": {"_id": "$category", "attempted": {"$sum": 1}, "correct": {"$sum": {"$cond": ["$correct", 1, 0]}}}}]).to_list(20)
        stats = {x["_id"]: x for x in rows}
        totals = {x["_id"]: x["n"] for x in await db.arena_questions.aggregate([
            {"$match": {"published": True, "category": {"$in": list(CATEGORIES.keys())}}}, {"$group": {"_id": "$category", "n": {"$sum": 1}}}]).to_list(20)}
        out = []
        if sum(x["correct"] for x in rows) >= 1:
            out.append(await give_badge(user_id, "first_blood"))
        for key, (cat, need) in BADGE_RULES.items():
            if stats.get(cat, {}).get("correct", 0) >= need:
                out.append(await give_badge(user_id, key))
        if all(stats.get(c, {}).get("correct", 0) >= 1 for c in CATEGORIES):
            out.append(await give_badge(user_id, "polymath"))
        for cat, st in stats.items():
            if cat not in CATEGORIES:
                continue
            if totals.get(cat) and st["attempted"] >= totals[cat] and st["correct"] / st["attempted"] >= 0.6:
                out.append(await award(user_id, f"milestone:{cat}", MILESTONE_XP, f"Category cleared · {CATEGORIES[cat]}", "milestone"))
        return [a for a in out if a]

    async def standings(include_dq=False):
        s = await settings()
        agg = await db.arena_xp.aggregate([{"$group": {
            "_id": "$user_id", "xp": {"$sum": "$amount"}, "last": {"$max": "$created_at"},
            "completed": {"$sum": {"$cond": [{"$in": ["$kind", ["question", "rapid"]]}, 1, 0]}}}}]).to_list(10000)
        ids = [ObjectId(a["_id"]) for a in agg]
        users = {str(u["_id"]): u for u in await db.users.find({"_id": {"$in": ids}}, {"name": 1, "team_name": 1, "role": 1}).to_list(10000)}
        badges = {}
        for b in await db.arena_badges.find({}, {"_id": 0}).to_list(100000):
            badges.setdefault(b["user_id"], []).append(b["badge"])
        rows = []
        for a in agg:
            u = users.get(a["_id"])
            if not u or (a["_id"] in s["disqualified"] and not include_dq):
                continue
            rows.append({"user_id": a["_id"], "name": u["name"], "team_name": u.get("team_name") or "", "xp": a["xp"],
                         "completed": a["completed"], "last_scored_at": a["last"], "badges": badges.get(a["_id"], []),
                         "disqualified": a["_id"] in s["disqualified"]})
        rows.sort(key=lambda x: (-x["xp"], -x["completed"], x["last_scored_at"]))
        for i, x in enumerate(rows):
            p = rows[i - 1] if i else None
            same = p and (p["xp"], p["completed"], p["last_scored_at"]) == (x["xp"], x["completed"], x["last_scored_at"])
            x["rank"] = p["rank"] if same else i + 1
        return rows

    # ---------- public ----------
    @r.get("/state")
    async def state():
        s = await settings()
        counts = {x["_id"]: x["n"] for x in await db.arena_questions.aggregate([
            {"$match": {"published": True}}, {"$group": {"_id": {"$ifNull": ["$set", "$category"]}, "n": {"$sum": 1}}}]).to_list(50)}
        today, dq = await daily_question()
        return {
            "status": status_of(s), "starts_at": s["starts_at"], "closes_at": s["closes_at"], "prize": s["prize"],
            "announcement": s["announcement"], "champion": s["champion"] if s["finalized"] else None,
            "categories": [
                {
                    "key": k,
                    "name": v,
                    "count": counts.get(k, 0),
                    "enabled": s.get("enabled_games", DEFAULTS["enabled_games"]).get(k, True),
                }
                for k, v in CATEGORIES.items()
            ],
            "rapid_sets": [
                {
                    "key": k,
                    "name": v[0],
                    "desc": v[1],
                    "count": RAPID_N if k == "binary" else counts.get(k, 0),
                    "enabled": s.get("enabled_games", DEFAULTS["enabled_games"]).get("rapid", True),
                }
                for k, v in RAPID_SETS.items()
            ],
            "badges": [{"key": k, "name": v[0], "desc": v[1], "xp": v[2]} for k, v in BADGES.items()],
            "daily": (
                {"available": True, "bonus": s.get("daily_xp", DAILY_XP), "date": today}
                if dq and s.get("daily_enabled", True) else None
            ),
            "paused": s.get("paused", False),
            "frozen": s.get("frozen", False),
            "enabled_games": s.get("enabled_games", DEFAULTS["enabled_games"]),
            "daily_enabled": s.get("daily_enabled", True),
            "xp_rules": {
                **s.get("difficulty_xp", DEFAULTS["difficulty_xp"]),
                "milestone": MILESTONE_XP,
                "daily": s.get("daily_xp", DAILY_XP),
                "rapid_max": min(
                    50,
                    RAPID_N * s.get("rapid_correct_xp", 8)
                    + s.get("rapid_time_bonus_max", 10),
                ),
            },
        }

    @r.get("/leaderboard")
    async def leaderboard():
        s = await settings()
        rows = await standings()
        return {"status": status_of(s), "rows": rows[:200], "champion": s["champion"] if s["finalized"] else None,
                "prize": s["prize"], "announcement": s["announcement"], "participants": len(rows)}

    @r.get("/questions")
    async def questions():
        raise HTTPException(
            status_code=404,
            detail="Bulk question access is disabled.",
        )

    @r.get("/questions/next")
    async def next_question(
        category: Literal["logic", "predict"],
        user=Depends(participant),
    ):
        await ensure_game_available(category)

        question_filter = {
            "published": True,
            "category": category,
        }

        # Previously attempted questions cannot earn XP again.
        attempts = await db.arena_attempts.find(
            {"user_id": user.id},
            {"_id": 0, "question_id": 1},
        ).to_list(5000)

        opened = await db.arena_opens.find(
            {"user_id": user.id},
            {"_id": 0, "question_id": 1},
        ).to_list(5000)

        attempted_ids = {
            str(item["question_id"])
            for item in attempts
            if item.get("question_id")
        }

        seen_ids = attempted_ids | {
            str(item["question_id"])
            for item in opened
            if item.get("question_id")
        }

        excluded_ids = [
            ObjectId(qid)
            for qid in seen_ids
            if ObjectId.is_valid(qid)
        ]

        fresh_filter = dict(question_filter)
        if excluded_ids:
            fresh_filter["_id"] = {"$nin": excluded_ids}

        # Prefer questions this participant has not seen.
        docs = await db.arena_questions.aggregate([
            {"$match": fresh_filter},
            {"$sample": {"size": 1}},
        ]).to_list(1)

        # Once the available pool is exhausted, allow practice replays.
        if not docs:
            docs = await db.arena_questions.aggregate([
                {"$match": question_filter},
                {"$sample": {"size": 1}},
            ]).to_list(1)

        if not docs:
            raise HTTPException(
                status_code=404,
                detail=f"No published questions are available in {category} yet.",
            )

        question = docs[0]
        qid = str(question["_id"])

        return {
            **public_q(question),
            "attempted": qid in attempted_ids,
        }

    @r.get("/questions/daily")
    async def daily_challenge(user=Depends(participant)):
        s = await settings()

        if s.get("paused", False):
            raise HTTPException(423, "The Arena is temporarily paused.")

        if not s.get("daily_enabled", True):
            raise HTTPException(404, "Daily Challenges are currently disabled.")

        today, question = await daily_question()

        if question:
            await ensure_game_available(question["category"], s)

        if not question:
            raise HTTPException(
                status_code=404,
                detail="Today's Daily Challenge is unavailable.",
            )

        qid = str(question["_id"])

        previous_attempt = await db.arena_attempts.find_one({
            "user_id": user.id,
            "question_id": qid,
        })

        return {
            **public_q(question),
            "attempted": bool(previous_attempt),
            "daily": True,
            "date": today,
            "bonus": s.get("daily_xp", DAILY_XP),
        }
    # ---------- participant ----------
    @r.post("/questions/{qid}/open")
    async def open_question(qid: str, user=Depends(participant)):
        if not ObjectId.is_valid(qid):
            raise HTTPException(404, "Question not found")
        question = await db.arena_questions.find_one(
            {"_id": ObjectId(qid), "published": True}
        )
        if not question or question.get("category") not in CATEGORIES:
            raise HTTPException(404, "Question not found")
        await db.arena_opens.update_one({"user_id": user.id, "question_id": qid}, {"$setOnInsert": {"opened_at": now_iso()}}, upsert=True)
        return {"ok": True}

    @r.post("/questions/{qid}/answer")
    async def answer(qid: str, body: AnswerIn, user=Depends(participant)):
        q = await db.arena_questions.find_one({"_id": ObjectId(qid), "published": True}) if ObjectId.is_valid(qid) else None
        if not q or q.get("category") not in CATEGORIES:
            raise HTTPException(404, "Question not found")
        if body.selected >= len(q["options"]):
            raise HTTPException(400, "Invalid option")
        s = await settings()
        st = status_of(s)
        game_enabled = s.get("enabled_games", DEFAULTS["enabled_games"]).get(q["category"], True)
        correct = body.selected == q["answer_index"]
        await db.arena_events.insert_one({"user_id": user.id, "at": now_iso(), "type": "answer"})
        res = {"correct": correct, "correct_index": q["answer_index"], "explanation": q["explanation"], "xp_awarded": 0, "awards": [], "practice": True, "note": ""}
        if (st != "live" or s.get("paused", False) or s.get("frozen", False)
                or not game_enabled or user.id in s.get("disqualified", [])):
            res["note"] = "Practice mode — scoring is currently disabled for this game or account."
            return res
        opened = await db.arena_opens.find_one({"user_id": user.id, "question_id": qid})
        elapsed = int((datetime.now(timezone.utc) - parse_dt(opened["opened_at"])).total_seconds() * 1000) if opened else None
        try:
            await db.arena_attempts.insert_one({"user_id": user.id, "question_id": qid, "category": q["category"], "selected": body.selected,
                                                "correct": correct, "elapsed_ms": elapsed, "created_at": now_iso()})
        except DuplicateKeyError:
            res["note"] = "Already attempted — replays are practice only, no XP."
            return res
        res["practice"] = False
        if correct:
            awards = [await award(user.id, f"q:{qid}", q["xp"], f"Solved · {q['prompt'][:60]}", "question")]
            today, dq = await daily_question()
            if (
                dq
                and str(dq["_id"]) == qid
                and s.get("daily_enabled", True)
            ):
                awards.append(await award(
                    user.id,
                    f"daily:{today}",
                    s.get("daily_xp", DAILY_XP),
                    "Daily challenge bonus",
                    "daily",
                ))
            awards += await check_awards(user.id)
            res["awards"] = [a for a in awards if a]
            res["xp_awarded"] = sum(a["xp"] for a in res["awards"])
        else:
            res["awards"] = await check_awards(user.id)
            res["xp_awarded"] = sum(a["xp"] for a in res["awards"])
            res["note"] = "Your first answer is the one that counts — no XP for this one."
        return res
        # ---------- generated Sudoku and KenKen ----------

    @r.post("/puzzles/start")
    async def puzzle_start(body: PuzzleStartIn, user=Depends(participant)):
        s = await ensure_game_available(body.game)

        if body.game == "sudoku":
            puzzle = generate_sudoku(body.difficulty)
        else:
            puzzle = generate_kenken(body.difficulty)

        scored = (
            status_of(s) == "live"
            and not s.get("frozen", False)
            and user.id not in s["disqualified"]
        )

        xp_table = s.get("difficulty_xp", DEFAULTS["difficulty_xp"])
        puzzle_xp = int(xp_table.get(body.difficulty, DIFF_XP[body.difficulty]))

        doc = {
            "user_id": user.id,
            "game": body.game,
            "difficulty": body.difficulty,
            "grid": puzzle["grid"],
            "solution": puzzle["solution"],
            "cages": puzzle.get("cages", []),
            "xp": puzzle_xp,
            "scored": scored,
            "finished": False,
            "started_at": now_iso(),
            "created_at": now_iso(),
            "submission_count": 0,
        }

        result = await db.arena_puzzles.insert_one(doc)

        return {
            "puzzle_id": str(result.inserted_id),
            "game": body.game,
            "difficulty": body.difficulty,
            "grid": puzzle["grid"],
            "cages": puzzle.get("cages", []),
            "clues": puzzle.get("clues"),
            "xp": doc["xp"],
            "scored": scored,
        }

    @r.post("/puzzles/{puzzle_id}/submit")
    async def puzzle_submit(
        puzzle_id: str,
        body: PuzzleSubmitIn,
        user=Depends(participant)
    ):
        if not ObjectId.is_valid(puzzle_id):
            raise HTTPException(404, "Puzzle not found")

        puzzle = await db.arena_puzzles.find_one({
            "_id": ObjectId(puzzle_id),
            "user_id": user.id
        })

        if not puzzle:
            raise HTTPException(404, "Puzzle not found")

        if puzzle["finished"]:
            raise HTTPException(400, "This puzzle has already been completed")

        correct = validate_grid(
            body.grid,
            puzzle["solution"],
            len(puzzle["solution"])
        )

        if not correct:
            await db.arena_puzzles.update_one(
                {"_id": puzzle["_id"], "finished": False},
                {
                    "$inc": {"submission_count": 1},
                    "$set": {"last_submitted_at": now_iso()}
                }
            )
            return {
                "correct": False,
                "xp_awarded": 0,
                "message": "Not quite. Check your grid and try again."
            }

        completed = await db.arena_puzzles.find_one_and_update(
            {"_id": puzzle["_id"], "user_id": user.id, "finished": False},
            {"$set": {"finished": True, "finished_at": now_iso()}},
            return_document=True
        )

        if not completed:
            raise HTTPException(400, "This puzzle has already been completed")

        current = await settings()
        eligible = (
            puzzle["scored"]
            and status_of(current) == "live"
            and not current.get("frozen", False)
            and not current.get("paused", False)
            and current.get("enabled_games", DEFAULTS["enabled_games"]).get(puzzle["game"], True)
            and user.id not in current["disqualified"]
        )

        awards = []

        if eligible:
            result = await award(
                user.id,
                f"puzzle:{puzzle_id}",
                puzzle["xp"],
                f"Solved {puzzle['game'].title()} · {puzzle['difficulty']}",
                "question"
            )
            if result:
                awards.append(result)

        xp_awarded = sum(a["xp"] for a in awards)

        await db.arena_events.insert_one({
            "user_id": user.id,
            "at": now_iso(),
            "type": "puzzle_completed",
            "game": puzzle["game"],
            "difficulty": puzzle["difficulty"],
        })

        return {
            "correct": True,
            "xp_awarded": xp_awarded,
            "practice": not eligible,
            "message": "Puzzle solved!",
            "awards": awards,
        }

    @r.post("/rapid/start")
    async def rapid_start(body: RapidStartIn, user=Depends(participant)):
        s = await ensure_game_available("rapid")
        rng = random.Random()
        if body.set == "binary":
            qs = [binary_question(rng) for _ in range(RAPID_N)]
        else:
            pool = await db.arena_questions.find({"published": True, "category": "rapid", "set": body.set}).to_list(200)
            if len(pool) < RAPID_N:
                raise HTTPException(400, "Not enough questions in this set yet")
            qs = [{"qid": str(d["_id"]), "prompt": d["prompt"], "code": d.get("code", ""), "options": d["options"],
                   "answer_index": d["answer_index"], "explanation": d["explanation"]} for d in rng.sample(pool, RAPID_N)]
        scored = (
            status_of(s) == "live"
            and not s.get("frozen", False)
            and user.id not in s["disqualified"]
        )
        run = {"user_id": user.id, "set": body.set, "questions": qs, "started_at": now_iso(), "finished": False, "scored": scored}
        try:
            res = await db.arena_rapid_runs.insert_one(run)
        except DuplicateKeyError:
            run["scored"] = False
            run.pop("_id", None)
            res = await db.arena_rapid_runs.insert_one(run)
        await db.arena_events.insert_one({"user_id": user.id, "at": now_iso(), "type": "rapid_start"})
        return {"run_id": str(res.inserted_id), "seconds": RAPID_SECONDS, "scored": run["scored"],
                "questions": [{"prompt": q["prompt"], "code": q.get("code", ""), "options": q["options"]} for q in qs]}

    @r.post("/rapid/{run_id}/submit")
    async def rapid_submit(run_id: str, body: RapidSubmitIn, user=Depends(participant)):
        if not ObjectId.is_valid(run_id):
            raise HTTPException(404, "Run not found")

        run = await db.arena_rapid_runs.find_one_and_update({"_id": ObjectId(run_id), "user_id": user.id, "finished": False}, {"$set": {"finished": True, "finished_at": now_iso()}})
        if not run:
            raise HTTPException(400, "This run was already submitted")
        elapsed = (datetime.now(timezone.utc) - parse_dt(run["started_at"])).total_seconds()
        late = elapsed > RAPID_SECONDS + RAPID_GRACE
        answers = (body.answers + [None] * RAPID_N)[:RAPID_N]
        results = [{"prompt": q["prompt"], "selected": a, "correct_index": q["answer_index"], "correct": a == q["answer_index"], "explanation": q["explanation"]}
                   for q, a in zip(run["questions"], answers)]
        n_correct = sum(x["correct"] for x in results)
        secs_left = max(0, RAPID_SECONDS - int(elapsed))
        current = await settings()
        correct_xp = current.get("rapid_correct_xp", 8)
        time_bonus_max = current.get("rapid_time_bonus_max", 10)
        time_bonus = (
            min(time_bonus_max, secs_left * time_bonus_max // RAPID_SECONDS)
            if time_bonus_max > 0 else 0
        )
        xp = min(50, n_correct * correct_xp + (time_bonus if n_correct >= 4 else 0))
        awards, note = [], ""
        if late:
            note = "Time expired — this run does not score."
        elif not run["scored"]:
            note = "Practice run — XP for this set is only awarded on your first run."
        elif (
            status_of(current) != "live"
            or current.get("frozen", False)
            or not current.get("enabled_games", DEFAULTS["enabled_games"]).get("rapid", True)
        ):
            note = "The Arena is not currently accepting scores."
        elif n_correct:
            awards.append(await award(user.id, f"rapid:{run['set']}", xp, f"Rapid fire · {RAPID_SETS[run['set']][0]} ({n_correct}/5)", "rapid"))
            if n_correct == RAPID_N:
                awards.append(await give_badge(user.id, "lightning"))
        awards = [a for a in awards if a]
        await db.arena_rapid_runs.update_one({"_id": run["_id"]}, {"$set": {"correct": n_correct, "xp": sum(a["xp"] for a in awards)}})
        return {"results": results, "correct": n_correct, "xp_awarded": sum(a["xp"] for a in awards), "awards": awards, "note": note, "elapsed": int(elapsed)}

    @r.get("/me")
    async def me(user=Depends(participant)):
        rows = await standings(include_dq=True)
        mine = next((x for x in rows if x["user_id"] == user.id), None)
        cats = {x["_id"]: x for x in await db.arena_attempts.aggregate([
            {"$match": {"user_id": user.id, "category": {"$in": list(CATEGORIES.keys())}}},
            {"$group": {"_id": "$category", "attempted": {"$sum": 1}, "correct": {"$sum": {"$cond": ["$correct", 1, 0]}}}}]).to_list(20)}
        totals = {x["_id"]: x["n"] for x in await db.arena_questions.aggregate([
            {"$match": {"published": True, "category": {"$in": list(CATEGORIES.keys())}}}, {"$group": {"_id": {"$ifNull": ["$set", "$category"]}, "n": {"$sum": 1}}}]).to_list(50)}
        history = await db.arena_xp.find({"user_id": user.id}, {"_id": 0, "user_id": 0}).sort("created_at", -1).to_list(60)
        rapid_done = [x["ref"].split(":")[1] for x in history if x["kind"] == "rapid"]
        rapid_tried = await db.arena_rapid_runs.distinct("set", {"user_id": user.id, "scored": True})
        today, dq = await daily_question()
        daily_done = bool(dq) and bool(await db.arena_attempts.find_one({"user_id": user.id, "question_id": str(dq["_id"])}))
        public_rows = [x for x in rows if not x["disqualified"]]
        return {
            "name": user.name, "team_name": user.team_name or "", "xp": mine["xp"] if mine else 0,
            "rank": next((x["rank"] for x in public_rows if x["user_id"] == user.id), None), "participants": len(public_rows),
            "completed": mine["completed"] if mine else 0, "badges": mine["badges"] if mine else [],
            "categories": {k: {"attempted": cats.get(k, {}).get("attempted", 0), "correct": cats.get(k, {}).get("correct", 0), "total": totals.get(k, 0)} for k in CATEGORIES},
            "rapid_done": rapid_done, "rapid_used": rapid_tried, "history": history, "daily_done": daily_done,
            "disqualified": user.id in (await settings())["disqualified"],
        }

    # ---------- admin ----------
    @r.get("/admin/questions")
    async def admin_questions(_=Depends(admin)):
        supported = [*CATEGORIES.keys(), "rapid"]
        return [admin_q(d) for d in await db.arena_questions.find(
            {"category": {"$in": supported}}
        ).sort([("category", 1), ("slug", 1)]).to_list(2000)]

    def _validate(body: QuestionIn):
        if body.answer_index >= len(body.options):
            raise HTTPException(400, "answer_index is out of range")
        if any(not o.strip() for o in body.options):
            raise HTTPException(400, "Options cannot be empty")
        if (body.category == "rapid") != bool(body.set):
            raise HTTPException(400, "Rapid questions need a set; other categories must not have one")
        d = body.model_dump()
        d["xp"] = d["xp"] if d["xp"] is not None else xp_for(body.category, body.difficulty)
        return d

    @r.post("/admin/questions")
    async def admin_create(body: QuestionIn, _=Depends(admin)):
        d = {**_validate(body), "slug": f"custom-{ObjectId()}", "created_at": now_iso()}
        res = await db.arena_questions.insert_one(d)
        return admin_q({**d, "_id": res.inserted_id})

    @r.put("/admin/questions/{qid}")
    async def admin_update(qid: str, body: QuestionIn, _=Depends(admin)):
        if not ObjectId.is_valid(qid):
            raise HTTPException(404, "Not found")
        doc = await db.arena_questions.find_one_and_update({"_id": ObjectId(qid)}, {"$set": _validate(body)}, return_document=True)
        if not doc:
            raise HTTPException(404, "Not found")
        return admin_q(doc)

    @r.patch("/admin/questions/{qid}/publish")
    async def admin_publish(qid: str, body: FlagIn, _=Depends(admin)):
        if not ObjectId.is_valid(qid):
            raise HTTPException(404, "Not found")
        await db.arena_questions.update_one({"_id": ObjectId(qid)}, {"$set": {"published": body.value}})
        return {"ok": True}

    @r.delete("/admin/questions/{qid}")
    async def admin_delete(qid: str, _=Depends(admin)):
        if not ObjectId.is_valid(qid):
            raise HTTPException(404, "Not found")
        await db.arena_questions.delete_one({"_id": ObjectId(qid)})
        return {"ok": True}

    @r.get("/admin/settings")
    async def admin_get_settings(_=Depends(admin)):
        s = await settings()
        return {**s, "status": status_of(s)}

    @r.put("/admin/settings")
    async def admin_put_settings(body: ArenaSettingsIn, _=Depends(admin)):
        patch = body.model_dump(exclude_unset=True)
        for k in ("starts_at", "closes_at"):
            if patch.get(k):
                try:
                    if parse_dt(patch[k]).tzinfo is None:
                        raise ValueError
                except ValueError:
                    raise HTTPException(400, f"{k} must be an ISO date-time with timezone")
            elif k in patch:
                patch[k] = None
        await db.arena_settings.update_one({"key": "arena"}, {"$set": patch}, upsert=True)
        return await admin_get_settings()

    @r.put("/admin/controls")
    async def admin_update_controls(body: ArenaControlsIn, _=Depends(admin)):
        patch = body.model_dump(exclude_unset=True)
        current = await settings()

        if "enabled_games" in patch:
            allowed = {"logic", "kenken", "predict", "sudoku", "rapid"}
            supplied = patch["enabled_games"]

            if not isinstance(supplied, dict) or not set(supplied).issubset(allowed):
                raise HTTPException(400, "Invalid game control key")

            if any(not isinstance(v, bool) for v in supplied.values()):
                raise HTTPException(400, "Game switches must be true or false")

            patch["enabled_games"] = {
                **current.get("enabled_games", DEFAULTS["enabled_games"]),
                **supplied,
            }

        if "difficulty_xp" in patch:
            supplied = patch["difficulty_xp"]
            allowed = {"easy", "medium", "hard"}

            if not isinstance(supplied, dict) or not set(supplied).issubset(allowed):
                raise HTTPException(400, "Invalid difficulty XP key")

            if any(
                isinstance(v, bool) or not isinstance(v, int) or v < 0 or v > 100
                for v in supplied.values()
            ):
                raise HTTPException(400, "Difficulty XP must be between 0 and 100")

            patch["difficulty_xp"] = {
                **current.get("difficulty_xp", DEFAULTS["difficulty_xp"]),
                **supplied,
            }

        await db.arena_settings.update_one(
            {"key": "arena"},
            {"$set": patch},
            upsert=True,
        )
        return await admin_get_settings()

    @r.post("/admin/start-now")
    async def admin_start_now(_=Depends(admin)):
        s = await settings()

        if s.get("finalized") or s.get("manually_closed"):
            raise HTTPException(409, "Reopen the Arena before starting it again")

        if s.get("closes_at") and datetime.now(timezone.utc) >= parse_dt(s["closes_at"]):
            raise HTTPException(409, "The scheduled closing time has already passed")

        await db.arena_settings.update_one(
            {"key": "arena"},
            {"$set": {
                "starts_at": now_iso(),
                "paused": False,
            }},
            upsert=True,
        )
        return await admin_get_settings()

    @r.post("/admin/pause")
    async def admin_pause(_=Depends(admin)):
        s = await settings()

        if status_of(s) != "live":
            raise HTTPException(409, "Only a live Arena can be paused")

        await db.arena_settings.update_one(
            {"key": "arena"},
            {"$set": {"paused": True}},
            upsert=True,
        )
        return await admin_get_settings()

    @r.post("/admin/resume")
    async def admin_resume(_=Depends(admin)):
        s = await settings()

        if s.get("finalized") or s.get("manually_closed"):
            raise HTTPException(409, "Reopen the Arena before resuming")

        if s.get("closes_at") and datetime.now(timezone.utc) >= parse_dt(s["closes_at"]):
            raise HTTPException(409, "The scheduled closing time has already passed")

        await db.arena_settings.update_one(
            {"key": "arena"},
            {"$set": {"paused": False}},
            upsert=True,
        )
        return await admin_get_settings()

    @r.post("/admin/close")
    async def admin_close(_=Depends(admin)):
        await db.arena_settings.update_one(
            {"key": "arena"},
            {"$set": {
                "manually_closed": True,
                "paused": False,
                "frozen": True,
            }},
            upsert=True,
        )
        return await admin_get_settings()

    @r.post("/admin/freeze")
    async def admin_freeze(body: FlagIn, _=Depends(admin)):
        await db.arena_settings.update_one({"key": "arena"}, {"$set": {"frozen": body.value}}, upsert=True)
        return await admin_get_settings()

    @r.post("/admin/finalize")
    async def admin_finalize(body: FinalizeIn, _=Depends(admin)):
        s = await settings()
        if (
            status_of(s) in ("live", "upcoming", "paused")
            and not s.get("frozen", False)
        ):
            raise HTTPException(400, "Freeze scoring or close the Arena before finalising")
        rows = await standings()
        if not rows:
            raise HTTPException(400, "No scored participants yet")
        top = [x for x in rows if x["rank"] == 1]
        if len(top) > 1 and not body.champion_user_id:
            await db.arena_settings.update_one({"key": "arena"}, {"$set": {"tie_candidates": [x["user_id"] for x in top]}}, upsert=True)
            return {"tie": True, "candidates": top}
        pick = next((x for x in top if x["user_id"] == body.champion_user_id), None) if body.champion_user_id else top[0]
        if not pick:
            raise HTTPException(400, "The champion must be one of the tied #1 participants")
        champ = {k: pick[k] for k in ("user_id", "name", "team_name", "xp", "completed")}
        champ["tie_resolved_by_admin"] = len(top) > 1
        await db.arena_settings.update_one({"key": "arena"}, {"$set": {"finalized": True, "frozen": True, "champion": champ, "tie_candidates": []}}, upsert=True)
        try:
            await db.arena_badges.insert_one({"user_id": pick["user_id"], "badge": "arena_champion", "created_at": now_iso()})
        except DuplicateKeyError:
            pass
        return {"tie": False, "champion": champ}

    @r.post("/admin/reopen")
    async def admin_reopen(_=Depends(admin)):
        await db.arena_badges.delete_many({"badge": "arena_champion"})
        await db.arena_settings.update_one(
            {"key": "arena"},
            {"$set": {
                "finalized": False,
                "frozen": False,
                "paused": False,
                "manually_closed": False,
                "champion": None,
                "tie_candidates": [],
            }},
            upsert=True,
        )
        return await admin_get_settings()

    @r.get("/admin/participants")
    async def admin_participants(_=Depends(admin)):
        rows = await standings(include_dq=True)
        att = {x["_id"]: x for x in await db.arena_attempts.aggregate([{"$match": {"category": {"$in": list(CATEGORIES.keys())}}}, {"$group": {
            "_id": "$user_id", "attempts": {"$sum": 1}, "correct": {"$sum": {"$cond": ["$correct", 1, 0]}},
            "fast": {"$sum": {"$cond": [{"$and": ["$correct", {"$lt": [{"$ifNull": ["$elapsed_ms", 999999]}, 3000]}]}, 1, 0]}},
            "unopened": {"$sum": {"$cond": [{"$eq": ["$elapsed_ms", None]}, 1, 0]}}}}]).to_list(10000)}
        bursts = {x["_id"]: x["peak"] for x in await db.arena_events.aggregate([
            {"$group": {"_id": {"u": "$user_id", "m": {"$substrBytes": ["$at", 0, 16]}}, "n": {"$sum": 1}}},
            {"$group": {"_id": "$_id.u", "peak": {"$max": "$n"}}}]).to_list(10000)}
        out = []
        for x in rows:
            a = att.get(x["user_id"], {})
            flags = []
            if a.get("fast", 0) >= 3:
                flags.append(f"{a['fast']} correct answers under 3s")
            if a.get("unopened", 0) >= 2:
                flags.append(f"{a['unopened']} answers without opening the question")
            if bursts.get(x["user_id"], 0) >= 15:
                flags.append(f"{bursts[x['user_id']]} submissions in one minute")
            out.append({**x, "attempts": a.get("attempts", 0), "accuracy": round(100 * a["correct"] / a["attempts"]) if a.get("attempts") else 0,
                        "flags": flags})
        return out

    @r.post("/admin/participants/{user_id}/disqualify")
    async def admin_disqualify(user_id: str, body: FlagIn, _=Depends(admin)):
        op = "$addToSet" if body.value else "$pull"
        await db.arena_settings.update_one({"key": "arena"}, {op: {"disqualified": user_id}}, upsert=True)
        return {"ok": True}

    return r


async def setup_arena(db):
    await db.arena_questions.create_index("slug", unique=True)
    await db.arena_puzzles.create_index(
    [("user_id", 1), ("created_at", -1)])
    await db.arena_attempts.create_index([("user_id", 1), ("question_id", 1)], unique=True)
    await db.arena_xp.create_index([("user_id", 1), ("ref", 1)], unique=True)
    await db.arena_badges.create_index([("user_id", 1), ("badge", 1)], unique=True)
    await db.arena_opens.create_index([("user_id", 1), ("question_id", 1)], unique=True)
    await db.arena_rapid_runs.create_index([("user_id", 1), ("set", 1)], unique=True, partialFilterExpression={"scored": True})
    await db.arena_events.create_index("user_id")
    supported_seed_categories = set(CATEGORIES) | {"rapid"}
    for q in SEED_QUESTIONS:
        if q.get("category") not in supported_seed_categories:
            continue
        doc = {**q, "xp": xp_for(q["category"], q["difficulty"]), "published": True, "created_at": now_iso()}
        await db.arena_questions.update_one({"slug": q["slug"]}, {"$setOnInsert": doc}, upsert=True)
