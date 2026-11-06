import re
import uuid
from datetime import datetime, timezone
from typing import List, Literal, Optional

from bson import ObjectId
from gridfs.errors import NoFile
from motor.motor_asyncio import AsyncIOMotorGridFSBucket
from pymongo.errors import DuplicateKeyError
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile
from pydantic import BaseModel, EmailStr, Field, field_validator

from backend import emailer
from backend.core_utils import (
    TEAM_ROLES, app_url, audit, clean_doc, delete_private_file, enforce_rate_limit, frontend_url, new_public_id, new_token,
    normalize_email, normalize_usn, now_iso, now_utc, safe_url, store_private_file,
    token_hash, valid_oid,
)
from backend.notification_service import create_notification


APPLICATION_STATUSES = ("pending", "under_review", "selected", "rejected")
PAYMENT_STATUSES = ("pending", "payment_under_verification", "correction_required", "payment_verified", "registration_confirmed")
TIMELINE_DEFAULTS = {
    "application_open": None,
    "application_close": "2026-11-10T23:59:00+05:30",
    "abstract_deadline": "2026-11-10T23:59:00+05:30",
    "selection_announcement": "2026-11-15T23:59:00+05:30",
    "payment_deadline": "2026-11-25T23:59:00+05:30",
    "hackathon_start": "2026-11-27T09:00:00+05:30",
    "hackathon_end": "2026-11-28T09:00:00+05:30",
    "project_open": "2026-11-27T09:00:00+05:30",
    "project_close": "2026-11-28T09:00:00+05:30",
    "application_override": "auto",
    "abstract_override": "auto",
    "project_override": "auto",
}


class TopicIn(BaseModel):
    title: str = Field(min_length=5, max_length=180)
    description: str = Field(min_length=10, max_length=1200)
    short: str = Field(default="", max_length=80)
    enabled: bool = True


class TopicOrderIn(BaseModel):
    topic_ids: List[str] = Field(min_length=1, max_length=100)


class TimelineIn(BaseModel):
    application_open: Optional[str] = None
    application_close: Optional[str] = None
    abstract_deadline: Optional[str] = None
    selection_announcement: Optional[str] = None
    payment_deadline: Optional[str] = None
    hackathon_start: Optional[str] = None
    hackathon_end: Optional[str] = None
    project_open: Optional[str] = None
    project_close: Optional[str] = None
    application_override: Literal["auto", "open", "closed"] = "auto"
    abstract_override: Literal["auto", "open", "closed"] = "auto"
    project_override: Literal["auto", "open", "closed"] = "auto"

    @field_validator("application_open", "application_close", "abstract_deadline", "selection_announcement",
                     "payment_deadline", "hackathon_start", "hackathon_end", "project_open", "project_close")
    @classmethod
    def valid_date(cls, value):
        if value:
            parsed = datetime.fromisoformat(value)
            if parsed.tzinfo is None:
                raise ValueError("Date and time must include a timezone")
        return value


class ApplicationReviewIn(BaseModel):
    status: Literal["pending", "under_review", "selected", "rejected"]
    admin_notes: str = Field(default="", max_length=3000)


class ManualApplicationIn(BaseModel):
    team_name: str = Field(min_length=2, max_length=100)
    college: str = Field(min_length=2, max_length=180)
    leader_name: str = Field(min_length=2, max_length=100)
    contact_email: EmailStr
    topic_id: str
    submission_date: str
    notes: str = Field(default="", max_length=3000)
    status: Literal["pending", "under_review", "selected", "rejected"] = "pending"

    @field_validator("submission_date")
    @classmethod
    def valid_submission_date(cls, value):
        try:
            parsed = datetime.fromisoformat(value)
            if parsed.tzinfo is None:
                raise ValueError
        except ValueError:
            raise ValueError("Submission date must be a valid timezone-aware date")
        return value


class PaymentSettingsIn(BaseModel):
    upi_id: str = Field(default="", max_length=100)
    bank_details: str = Field(default="", max_length=2000)
    amount: Optional[float] = Field(default=None, ge=0, le=1_000_000)
    deadline: Optional[str] = None
    instructions: str = Field(default="", max_length=3000)

    @field_validator("deadline")
    @classmethod
    def payment_date(cls, value):
        if value and datetime.fromisoformat(value).tzinfo is None:
            raise ValueError("Payment deadline must include a timezone")
        return value


class PaymentDecisionIn(BaseModel):
    action: Literal["approve", "reject", "request_correction"]
    reason: str = Field(default="", max_length=1000)


class ProjectIn(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    description: str = Field(min_length=20, max_length=10000)
    github_url: str
    demo_url: str
    video_url: str = ""

    @field_validator("github_url", "demo_url")
    @classmethod
    def required_url(cls, value):
        return safe_url(value)

    @field_validator("video_url")
    @classmethod
    def optional_url(cls, value):
        return safe_url(value, optional=True)


class LinkResourceIn(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    resource_type: Literal["external_link", "other_resource"]
    url: str
    description: str = Field(default="", max_length=1000)

    @field_validator("url")
    @classmethod
    def link_url(cls, value):
        return safe_url(value)


class CriteriaIn(BaseModel):
    phase: Literal["phase1", "phase2"]
    title: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=1000)
    max_marks: float = Field(gt=0, le=1000)
    weight: float = Field(gt=0, le=100)
    active: bool = True


class AssignmentIn(BaseModel):
    judge_id: str
    team_id: str
    phases: List[Literal["phase1", "phase2"]] = Field(min_length=1, max_length=2)


class ScoreItem(BaseModel):
    criterion_id: str
    marks: float = Field(ge=0)


class EvaluationIn(BaseModel):
    phase: Literal["phase1", "phase2"]
    scores: List[ScoreItem]
    comment: str = Field(default="", max_length=3000)
    action: Literal["save", "submit"] = "save"


class FormulaIn(BaseModel):
    phase1_weight: float = Field(ge=0, le=100)
    phase2_weight: float = Field(ge=0, le=100)


class JudgingWindowsIn(BaseModel):
    phase1_open: bool = False
    phase2_open: bool = False


class JudgeInviteIn(BaseModel):
    email: EmailStr
    name: str = Field(min_length=2, max_length=100)


def _team_id(user):
    return user.team_id or user.id


async def _team(db, user):
    team = await db.teams.find_one({"team_id": _team_id(user)}, {"_id": 0})
    if not team:
        raise HTTPException(404, "Team record not found")
    return team


async def _timeline(db):
    doc = await db.settings.find_one({"key": "timeline"}, {"_id": 0})
    return {**TIMELINE_DEFAULTS, **(doc or {})}


def _is_open(timeline, name):
    override = timeline.get(f"{name}_override", "auto")
    if override != "auto":
        return override == "open"
    now = now_utc()
    start_key, close_key = {
        "application": ("application_open", "application_close"),
        "abstract": ("application_open", "abstract_deadline"),
        "project": ("project_open", "project_close"),
    }[name]
    start = datetime.fromisoformat(timeline[start_key]) if timeline.get(start_key) else None
    close = datetime.fromisoformat(timeline[close_key]) if timeline.get(close_key) else None
    return (not start or now >= start) and (not close or now <= close)


async def public_meta(db):
    settings = await db.settings.find_one({"key": "global"}, {"_id": 0}) or {}
    timeline = await _timeline(db)
    topics = await db.topics.find({"enabled": True}, {"_id": 0}).sort("order", 1).to_list(100)
    return {
        "topics": topics,
        "tracks": [x["title"] for x in topics],
        "timeline": timeline,
        "portals": {x: _is_open(timeline, x) for x in ("application", "abstract", "project")},
        "phase": settings.get("phase", "registration"),
        "leaderboard_public": settings.get("leaderboard_public", False),
        "teams": await db.teams.count_documents({}),
        "submissions": await db.submissions.count_documents({}),
    }


async def consolidated_results(db):
    formula = await db.settings.find_one({"key": "judging_formula"}, {"_id": 0})
    if not formula or not formula.get("configured"):
        return {"configured": False, "rows": []}
    teams = {x["team_id"]: x for x in await db.teams.find({}, {"_id": 0}).to_list(5000)}
    evaluations = await db.evaluations.find({"status": "submitted"}, {"_id": 0}).to_list(20000)
    rows = []
    for team_id, team in teams.items():
        phases = {}
        for phase in ("phase1", "phase2"):
            values = [e["normalized_total"] for e in evaluations if e.get("team_id") == team_id and e.get("phase") == phase]
            phases[phase] = round(sum(values) / len(values), 2) if values else None
        if phases["phase1"] is None and phases["phase2"] is None:
            continue
        if any(phases[p] is None and formula.get(f"{p}_weight", 0) > 0 for p in phases):
            score = None
        else:
            total_weight = formula["phase1_weight"] + formula["phase2_weight"]
            score = round(sum((phases[p] or 0) * formula[f"{p}_weight"] for p in phases) / total_weight, 2)
        rows.append({"team_id": team_id, "team_name": team["name"], **phases, "score": score})
    rows.sort(key=lambda x: (x["score"] is None, -(x["score"] or 0), x["team_name"]))
    rank = 0
    previous = None
    for index, row in enumerate(rows, 1):
        if row["score"] != previous:
            rank = index
        row["rank"] = rank if row["score"] is not None else None
        previous = row["score"]
    return {"configured": True, "formula": formula, "rows": rows}


def build_router(db, current_user, require, hash_password, create_invitation):
    router = APIRouter()
    participant = require(*TEAM_ROLES)
    leader = require("team")
    admin = require("admin")
    judge = require("judge", "admin")

    async def send_member_invitation(membership, team, actor, request):
        if membership.get("role") != "member":
            raise HTTPException(404, "Team member not found")
        team_id = team["team_id"]
        target = None
        member_id = membership.get("user_id")
        if member_id and ObjectId.is_valid(member_id):
            target = await db.users.find_one({"_id": ObjectId(member_id)})
        if not target:
            email = normalize_email(membership["email"])
            target = await db.users.find_one({"email": email})
            if target:
                if target.get("role") != "member" or target.get("team_id") != team_id:
                    raise HTTPException(409, "This email is already associated with another account")
                member_id = str(target["_id"])
                await db.team_memberships.update_one(
                    {"membership_id": membership["membership_id"], "team_id": team_id},
                    {"$set": {"user_id": member_id}},
                )
            else:
                member_id = str(ObjectId())
                member_doc = {
                    "_id": ObjectId(member_id),
                    "email": email,
                    "name": membership.get("name", "").strip(),
                    "role": "member",
                    "team_id": team_id,
                    "password_hash": None,
                    "is_active": False,
                    "email_verified": False,
                    "must_change_password": False,
                    "session_version": 0,
                    "team_name": team.get("name"),
                    "college": membership.get("college") or team.get("college"),
                    "usn": membership.get("usn"),
                    "track": team.get("topic_title"),
                    "created_at": now_iso(),
                }
                if member_doc["usn"] and await db.users.find_one({"usn": member_doc["usn"]}):
                    raise HTTPException(409, "This member USN is already associated with another account")
                try:
                    await db.users.insert_one(member_doc)
                except DuplicateKeyError as exc:
                    raise HTTPException(409, "This member email or USN is already associated with another account") from exc
                target = member_doc
                await db.team_memberships.update_one(
                    {"membership_id": membership["membership_id"], "team_id": team_id},
                    {"$set": {"user_id": member_id}},
                )
        if (target.get("role") != "member" or target.get("team_id") != team_id
                or normalize_email(target.get("email", "")) != normalize_email(membership.get("email", ""))):
            raise HTTPException(409, "This account does not match the team member record")
        if target.get("is_active") or target.get("password_hash"):
            raise HTTPException(400, "This account is already active")
        await db.invitations.update_many(
            {"target_user_id": member_id, "purpose": "member_activation", "used_at": None, "revoked_at": None},
            {"$set": {"revoked_at": now_iso()}},
        )
        invitation = await create_invitation(clean_doc(target), "member_activation", team_id, frontend_url(request), 72)
        await audit(db, actor, "invitation.resent", "invitation", invitation["invitation_id"], request)
        return {"ok": True, "email_status": invitation["email_status"]}

    @router.get("/public/meta")
    async def meta():
        return await public_meta(db)

    @router.get("/participant/dashboard")
    async def participant_dashboard(user=Depends(participant)):
        team = await _team(db, user)
        team_id = team["team_id"]
        memberships = await db.team_memberships.find({"team_id": team_id}, {"_id": 0}).sort("role", -1).to_list(20)
        application = await db.applications.find_one({"team_id": team_id}, {"_id": 0})
        payment = await db.payments.find_one({"team_id": team_id}, {"_id": 0})
        project = await db.submissions.find_one({"team_id": team_id}, {"_id": 0})
        notices = await db.notifications.find({"user_id": user.id}, {"_id": 0}).sort("created_at", -1).to_list(30)
        settings = None
        if application and application.get("status") == "selected":
            settings = await db.settings.find_one({"key": "payment"}, {"_id": 0})
        elif team.get("registration_status") in ("selected_awaiting_payment",):
            # Team was selected directly (e.g. from People panel) — show payment settings
            settings = await db.settings.find_one({"key": "payment"}, {"_id": 0})
        return {"team": team, "memberships": memberships, "application": application, "payment": payment,
                "payment_settings": settings, "project": project, "notifications": notices,
                "timeline": await _timeline(db)}

    @router.patch("/notifications/{notification_id}/read")
    async def read_notice(notification_id: str, user=Depends(participant)):
        result = await db.notifications.update_one(
            {"notification_id": notification_id, "user_id": user.id}, {"$set": {"read_at": now_iso()}})
        if not result.matched_count:
            raise HTTPException(404, "Notification not found")
        return {"ok": True}

    @router.post("/invitations/{invitation_id}/resend")
    async def resend_invitation(invitation_id: str, request: Request, user=Depends(leader)):
        await enforce_rate_limit(db, f"invite:{user.id}", 5, 3600)
        membership = await db.team_memberships.find_one({
            "team_id": _team_id(user), "role": "member",
            "$or": [{"invitation_id": invitation_id}, {"membership_id": invitation_id}],
        }, {"_id": 0})
        if not membership:
            raise HTTPException(404, "Invitation not found")
        team = await _team(db, user)
        return await send_member_invitation(membership, team, user, request)

    @router.post("/memberships/{membership_id}/invitation/resend")
    async def resend_membership_invitation(membership_id: str, request: Request, user=Depends(leader)):
        await enforce_rate_limit(db, f"invite:{user.id}", 5, 3600)
        membership = await db.team_memberships.find_one({
            "membership_id": membership_id, "team_id": _team_id(user), "role": "member",
        }, {"_id": 0})
        if not membership:
            raise HTTPException(404, "Team member not found")
        return await send_member_invitation(membership, await _team(db, user), user, request)

    @router.delete("/invitations/{invitation_id}")
    async def revoke_invitation(invitation_id: str, request: Request, user=Depends(leader)):
        invite = await db.invitations.find_one({"invitation_id": invitation_id, "team_id": _team_id(user),
                                                "purpose": "member_activation", "used_at": None})
        if not invite:
            raise HTTPException(404, "Active invitation not found")
        await db.invitations.update_one({"_id": invite["_id"]}, {"$set": {"revoked_at": now_iso()}})
        await db.team_memberships.update_one({"team_id": _team_id(user), "user_id": invite["target_user_id"]},
                                             {"$set": {"status": "invitation_revoked"}})
        await audit(db, user, "invitation.revoked", "invitation", invitation_id, request)
        return {"ok": True}

    @router.post("/applications/abstract")
    async def submit_abstract(request: Request, topic_id: str = Form(...), file: UploadFile = File(...), user=Depends(leader)):
        await enforce_rate_limit(db, f"abstract:{user.id}", 8, 3600)
        timeline = await _timeline(db)
        if not _is_open(timeline, "abstract"):
            raise HTTPException(400, "Abstract submissions are closed")
        topic = await db.topics.find_one({"topic_id": topic_id, "enabled": True}, {"_id": 0})
        if not topic:
            raise HTTPException(400, "Choose an available challenge topic")
        team = await _team(db, user)
        old = await db.applications.find_one({"team_id": team["team_id"]}, {"_id": 0})
        if old and old.get("status") == "selected":
            raise HTTPException(400, "Selected applications are locked; contact the administrator for corrections")
        file_meta = await store_private_file(
            db, file=file, owner_id=user.id, team_id=team["team_id"], kind="abstract",
            max_bytes=3 * 1024 * 1024, allowed={"pdf"}, topic=topic,
        )
        application_id = old.get("application_id") if old else new_public_id("SK26-AB")
        event = {"status": "pending", "at": now_iso(), "by": user.id, "note": "Abstract submitted on website"}
        doc = {"application_id": application_id, "team_id": team["team_id"], "leader_id": team["leader_id"],
               "method": "website", "topic_id": topic_id, "topic_title": topic["title"], "file": file_meta,
               "status": "pending", "admin_notes": old.get("admin_notes", "") if old else "",
               "submitted_at": now_iso(), "updated_at": now_iso()}
        update = {"$set": doc, "$push": {"history": event}, "$setOnInsert": {"created_at": now_iso()}}
        application_filter = {"team_id": team["team_id"]}
        if old:
            application_filter["application_id"] = old["application_id"]
            old_file_id = (old.get("file") or {}).get("file_id")
            if old_file_id:
                application_filter["file.file_id"] = old_file_id
            else:
                application_filter["$or"] = [
                    {"file.file_id": {"$exists": False}},
                    {"file": None},
                ]
        try:
            result = await db.applications.update_one(application_filter, update, upsert=not old)
        except DuplicateKeyError as exc:
            await delete_private_file(db, file_meta["file_id"])
            raise HTTPException(409, "Abstract submission changed concurrently; reload and try again") from exc
        if old and not result.matched_count:
            await delete_private_file(db, file_meta["file_id"])
            raise HTTPException(409, "Abstract submission changed concurrently; reload and try again")
        if old and (old.get("file") or {}).get("file_id"):
            await delete_private_file(db, old["file"]["file_id"])
        await db.users.update_one({"_id": ObjectId(user.id)}, {"$set": {"abstract": file_meta, "track": topic["title"]}})
        await db.teams.update_one({"team_id": team["team_id"]}, {"$set": {"topic_id": topic_id, "topic_title": topic["title"]}})
        await audit(db, user, "abstract.submitted", "application", application_id, request)
        saved = await db.applications.find_one({"application_id": application_id}, {"_id": 0})
        return saved

    @router.get("/applications/me")
    async def my_application(user=Depends(participant)):
        return {"application": await db.applications.find_one({"team_id": _team_id(user)}, {"_id": 0})}

    @router.get("/files/{file_id}")
    async def private_file(file_id: str, user=Depends(current_user)):
        if user.must_change_password:
            raise HTTPException(403, "Password change required before accessing private files")
        rec = await db.files.find_one({"file_id": file_id, "is_deleted": False}, {"_id": 0})
        if not rec:
            raise HTTPException(404, "File not found")
        allowed = user.role == "admin"
        if rec.get("kind") != "abstract":
            if user.role in TEAM_ROLES:
                if rec.get("team_id") == _team_id(user):
                    allowed = True
                elif rec.get("kind") == "payment_qr":
                    app = await db.applications.find_one({"team_id": _team_id(user), "status": "selected"})
                    allowed = bool(app)
            if user.role == "judge":
                judge_kinds = {"abstract", "project-presentation", "project-resource"}
                allowed = rec.get("kind") in judge_kinds and bool(await db.judge_assignments.find_one({"judge_id": user.id, "team_id": rec.get("team_id")}))
        if not allowed:
            raise HTTPException(403, "You do not have access to this file")
        gridfs_id = rec.get("gridfs_id")
        if not gridfs_id or not ObjectId.is_valid(gridfs_id):
            raise HTTPException(410, "This file is not available in MongoDB GridFS")
        try:
            grid_out = await AsyncIOMotorGridFSBucket(db).open_download_stream(ObjectId(gridfs_id))
            data = await grid_out.read()
        except NoFile as exc:
            raise HTTPException(404, "File not found") from exc
        disposition = "inline" if rec["content_type"].startswith("image/") else "attachment"
        safe_name = re.sub(r"[^\w. -]", "_", rec["filename"])
        return Response(content=data, media_type=rec["content_type"],
                        headers={"Content-Disposition": f'{disposition}; filename="{safe_name}"', "Cache-Control": "private, no-store"})

    @router.get("/payments/me")
    async def my_payment(user=Depends(participant)):
        app = await db.applications.find_one({"team_id": _team_id(user)}, {"_id": 0})
        settings = await db.settings.find_one({"key": "payment"}, {"_id": 0}) if app and app.get("status") == "selected" else None
        return {"eligible": bool(settings), "settings": settings,
                "payment": await db.payments.find_one({"team_id": _team_id(user)}, {"_id": 0})}

    @router.post("/payments/proof")
    async def payment_proof(request: Request, transaction_ref: str = Form(...), payment_date: str = Form(...),
                            amount_paid: float = Form(...), remarks: str = Form(""), file: UploadFile = File(...),
                            user=Depends(leader)):
        await enforce_rate_limit(db, f"payment-proof:{user.id}", 6, 3600)
        if not re.fullmatch(r"[A-Za-z0-9 /_-]{4,80}", transaction_ref.strip()):
            raise HTTPException(400, "Enter a valid transaction reference")
        try:
            datetime.fromisoformat(payment_date)
        except ValueError:
            raise HTTPException(400, "Enter a valid payment date")
        if amount_paid <= 0 or amount_paid > 1_000_000:
            raise HTTPException(400, "Enter a valid amount")
        app = await db.applications.find_one({"team_id": _team_id(user), "status": "selected"}, {"_id": 0})
        if not app:
            raise HTTPException(403, "Payment proof is available only to selected teams")
        existing = await db.payments.find_one({"team_id": _team_id(user)}, {"_id": 0}) or {}
        if existing.get("status") in ("payment_verified", "registration_confirmed"):
            raise HTTPException(400, "Verified payment proof cannot be replaced")
        if existing.get("status") == "payment_under_verification" or (
            existing.get("status") == "pending" and existing.get("proof")
        ):
            raise HTTPException(409, "Payment proof is already under verification")
        payment_settings = await db.settings.find_one({"key": "payment"}, {"_id": 0}) or {}
        deadline = payment_settings.get("deadline") or (await _timeline(db)).get("payment_deadline")
        if deadline and now_utc() > datetime.fromisoformat(deadline):
            raise HTTPException(400, "The payment submission deadline has passed")
        file_meta = await store_private_file(db, file=file, owner_id=user.id, team_id=_team_id(user),
                                             kind="payment-proof", max_bytes=5 * 1024 * 1024,
                                             allowed={"pdf", "png", "jpg"})
        history = {"status": "payment_under_verification", "at": now_iso(), "by": user.id, "note": "Payment proof submitted"}
        try:
            result = await db.payments.update_one(
                {"team_id": _team_id(user), "$or": [
                    {"status": "correction_required"},
                    {"status": "pending", "proof": {"$exists": False}},
                    {"status": {"$exists": False}, "proof": {"$exists": False}},
                ]},
                {"$set": {
                    "payment_id": existing.get("payment_id") or new_public_id("PAY"), "team_id": _team_id(user),
                    "transaction_ref": transaction_ref.strip(), "payment_date": payment_date, "amount_paid": amount_paid,
                    "remarks": remarks[:1000], "proof": file_meta, "status": "payment_under_verification",
                    "submitted_at": now_iso(), "updated_at": now_iso()},
                 "$push": {"history": history}},
                upsert=True,
            )
        except DuplicateKeyError:
            await delete_private_file(db, file_meta["file_id"])
            raise HTTPException(409, "Payment proof is already under verification")
        if not result.matched_count and result.upserted_id is None:
            await delete_private_file(db, file_meta["file_id"])
            raise HTTPException(409, "Payment proof is already under verification")
        if (existing.get("proof") or {}).get("file_id"):
            await delete_private_file(db, existing["proof"]["file_id"])
        await audit(db, user, "payment.proof_submitted", "team", _team_id(user), request)
        await create_notification(db, user_id=user.id, kind="payment_proof_submitted",
                                  title="Payment proof submitted",
                                  message="Your proof is under independent administrator verification.",
                                  action_path="/dashboard?section=payment")
        admin_user = await db.users.find_one({"role": "admin", "is_active": True}, {"_id": 1})
        if admin_user:
            await create_notification(db, user_id=str(admin_user["_id"]), kind="payment_review_required",
                                      title="Payment proof requires verification",
                                      message=f"{(await _team(db, user))['name']} submitted payment proof for independent review.",
                                      action_path="/admin?section=payments")
        return await db.payments.find_one({"team_id": _team_id(user)}, {"_id": 0})

    async def require_project_eligibility(user):
        team = await _team(db, user)
        if team.get("registration_status") != "registration_confirmed":
            raise HTTPException(403, "Project submission is available only after registration confirmation")
        if not _is_open(await _timeline(db), "project"):
            raise HTTPException(400, "Project submission portal is closed")
        return team

    @router.get("/projects/me")
    async def my_project(user=Depends(participant)):
        team = await _team(db, user)
        return {"eligible": team.get("registration_status") == "registration_confirmed",
                "portal_open": _is_open(await _timeline(db), "project"),
                "submission": await db.submissions.find_one({"team_id": team["team_id"]}, {"_id": 0})}

    @router.put("/projects/me")
    async def save_project(body: ProjectIn, request: Request, user=Depends(participant)):
        team = await require_project_eligibility(user)
        existing = await db.submissions.find_one({"team_id": team["team_id"]}, {"_id": 0}) or {}
        if existing.get("status") == "submitted":
            raise HTTPException(400, "Submitted projects are locked")
        doc = {"submission_id": existing.get("submission_id") or new_public_id("SK26-PRJ"), "team_id": team["team_id"],
               "team_name": team["name"], **body.model_dump(), "status": "draft", "resources": existing.get("resources", []),
               "presentation_file": existing.get("presentation_file"), "updated_at": now_iso()}
        if existing:
            result = await db.submissions.update_one(
                {"team_id": team["team_id"], "status": {"$ne": "submitted"}}, {"$set": doc})
            if not result.matched_count:
                raise HTTPException(400, "Submitted projects are locked")
        else:
            try:
                await db.submissions.insert_one({**doc, "created_at": now_iso()})
            except DuplicateKeyError:
                raise HTTPException(409, "Project draft changed concurrently; reload and try again")
        await db.project_history.insert_one({"history_id": new_public_id("HIS"), "team_id": team["team_id"],
                                             "submission_id": doc["submission_id"], "action": "saved", "by": user.id, "at": now_iso()})
        await audit(db, user, "project.saved", "submission", doc["submission_id"], request)
        return await db.submissions.find_one({"team_id": team["team_id"]}, {"_id": 0})

    @router.post("/projects/me/presentation")
    async def upload_presentation(request: Request, file: UploadFile = File(...), user=Depends(participant)):
        team = await require_project_eligibility(user)
        sub = await db.submissions.find_one({"team_id": team["team_id"]}, {"_id": 0})
        if not sub or sub.get("status") == "submitted":
            raise HTTPException(400, "Save an editable project draft first")
        meta = await store_private_file(db, file=file, owner_id=user.id, team_id=team["team_id"],
                                        kind="project-presentation", max_bytes=10 * 1024 * 1024,
                                        allowed={"pdf", "doc", "docx"})
        result = await db.submissions.update_one(
            {"team_id": team["team_id"], "status": {"$ne": "submitted"}},
            {"$set": {"presentation_file": meta, "updated_at": now_iso()}})
        if not result.matched_count:
            await delete_private_file(db, meta["file_id"])
            raise HTTPException(400, "Project was finalized while the upload was processing")
        if (sub.get("presentation_file") or {}).get("file_id"):
            await delete_private_file(db, sub["presentation_file"]["file_id"])
        await db.project_history.insert_one({"history_id": new_public_id("HIS"), "team_id": team["team_id"],
                                             "submission_id": sub["submission_id"], "action": "presentation_uploaded",
                                             "by": user.id, "at": now_iso()})
        await audit(db, user, "project.presentation_uploaded", "submission", sub["submission_id"], request)
        return meta

    @router.post("/projects/me/resources/link")
    async def add_link_resource(body: LinkResourceIn, request: Request, user=Depends(participant)):
        team = await require_project_eligibility(user)
        sub = await db.submissions.find_one({"team_id": team["team_id"], "status": {"$ne": "submitted"}}, {"_id": 0})
        if not sub:
            raise HTTPException(400, "Save an editable project draft first")
        resource = {"resource_id": uuid.uuid4().hex, **body.model_dump(), "created_at": now_iso()}
        result = await db.submissions.update_one(
            {"team_id": team["team_id"], "status": {"$ne": "submitted"}},
            {"$push": {"resources": resource}, "$set": {"updated_at": now_iso()}})
        if not result.matched_count:
            raise HTTPException(400, "Project was finalized while the resource was being added")
        await db.project_history.insert_one({"history_id": new_public_id("HIS"), "team_id": team["team_id"],
                                             "submission_id": sub["submission_id"], "action": "link_resource_added",
                                             "resource_id": resource["resource_id"], "by": user.id, "at": now_iso()})
        await audit(db, user, "project.resource_added", "submission", sub["submission_id"], request)
        return resource

    @router.post("/projects/me/resources/file")
    async def add_file_resource(request: Request, title: str = Form(...), resource_type: str = Form(...),
                                description: str = Form(""), file: UploadFile = File(...), user=Depends(participant)):
        if resource_type not in ("additional_pdf", "project_document", "other_resource"):
            raise HTTPException(400, "Invalid resource type")
        team = await require_project_eligibility(user)
        sub = await db.submissions.find_one({"team_id": team["team_id"], "status": {"$ne": "submitted"}}, {"_id": 0})
        if not sub:
            raise HTTPException(400, "Save an editable project draft first")
        meta = await store_private_file(db, file=file, owner_id=user.id, team_id=team["team_id"],
                                        kind="project-resource", max_bytes=10 * 1024 * 1024,
                                        allowed={"pdf", "doc", "docx"})
        resource = {"resource_id": uuid.uuid4().hex, "title": title[:120], "resource_type": resource_type,
                    "description": description[:1000], "file": meta, "created_at": now_iso()}
        result = await db.submissions.update_one(
            {"team_id": team["team_id"], "status": {"$ne": "submitted"}},
            {"$push": {"resources": resource}, "$set": {"updated_at": now_iso()}})
        if not result.matched_count:
            await delete_private_file(db, meta["file_id"])
            raise HTTPException(400, "Project was finalized while the resource was being added")
        await db.project_history.insert_one({"history_id": new_public_id("HIS"), "team_id": team["team_id"],
                                             "submission_id": sub["submission_id"], "action": "file_resource_added",
                                             "resource_id": resource["resource_id"], "by": user.id, "at": now_iso()})
        await audit(db, user, "project.resource_added", "submission", sub["submission_id"], request)
        return resource

    @router.delete("/projects/me/resources/{resource_id}")
    async def remove_resource(resource_id: str, request: Request, user=Depends(participant)):
        team = await require_project_eligibility(user)
        sub = await db.submissions.find_one({"team_id": team["team_id"], "status": {"$ne": "submitted"}}, {"_id": 0})
        resource = next((x for x in (sub or {}).get("resources", []) if x["resource_id"] == resource_id), None)
        if not resource:
            raise HTTPException(404, "Resource not found")
        result = await db.submissions.update_one(
            {"team_id": team["team_id"], "status": {"$ne": "submitted"}},
            {"$pull": {"resources": {"resource_id": resource_id}}, "$set": {"updated_at": now_iso()}})
        if not result.matched_count:
            raise HTTPException(400, "Project was finalized while the resource was being removed")
        if (resource.get("file") or {}).get("file_id"):
            await delete_private_file(db, resource["file"]["file_id"])
        await db.project_history.insert_one({"history_id": new_public_id("HIS"), "team_id": team["team_id"],
                                             "submission_id": sub["submission_id"], "action": "resource_removed",
                                             "resource_id": resource_id, "by": user.id, "at": now_iso()})
        await audit(db, user, "project.resource_removed", "submission", sub["submission_id"], request)
        return {"ok": True}

    @router.post("/projects/me/submit")
    async def finalize_project(request: Request, user=Depends(participant)):
        team = await require_project_eligibility(user)
        sub = await db.submissions.find_one({"team_id": team["team_id"]}, {"_id": 0})
        if not sub or not sub.get("presentation_file"):
            raise HTTPException(400, "Project details and presentation/documentation are required")
        if sub.get("status") == "submitted":
            raise HTTPException(400, "Project already submitted")
        result = await db.submissions.update_one(
            {"team_id": team["team_id"], "status": "draft"},
            {"$set": {"status": "submitted", "submitted_at": now_iso(), "updated_at": now_iso()}})
        if not result.matched_count:
            raise HTTPException(400, "Project was already finalized or changed concurrently")
        await db.project_history.insert_one({"history_id": new_public_id("HIS"), "team_id": team["team_id"],
                                             "submission_id": sub["submission_id"], "action": "submitted",
                                             "by": user.id, "at": now_iso()})
        await audit(db, user, "project.submitted", "submission", sub["submission_id"], request)
        return await db.submissions.find_one({"team_id": team["team_id"]}, {"_id": 0})

    # ---------------- Admin ----------------
    @router.get("/admin/overview")
    async def admin_overview(user=Depends(admin)):
        return {"teams": await db.teams.count_documents({}), "participants": await db.users.count_documents({"role": {"$in": TEAM_ROLES}}),
                "applications": await db.applications.count_documents({}), "selected": await db.applications.count_documents({"status": "selected"}),
                "payments_pending": await db.payments.count_documents({"status": "payment_under_verification"}),
                "confirmed": await db.teams.count_documents({"registration_status": "registration_confirmed"}),
                "submissions": await db.submissions.count_documents({"status": "submitted"}),
                "notifications": await db.notifications.find({"user_id": user.id}, {"_id": 0}).sort("created_at", -1).to_list(20),
                "settings": await db.settings.find_one({"key": "global"}, {"_id": 0}) or {}}

    @router.get("/admin/teams")
    async def admin_teams(_: object = Depends(admin)):
        teams = await db.teams.find({}, {"_id": 0}).sort("created_at", -1).to_list(5000)
        out = []
        for team in teams:
            memberships = await db.team_memberships.find({"team_id": team["team_id"]}, {"_id": 0}).to_list(20)
            for membership in memberships:
                member_user = await db.users.find_one(
                    {"_id": ObjectId(membership["user_id"])} if ObjectId.is_valid(membership.get("user_id", "")) else {"_id": None},
                    {"_id": 0, "is_active": 1, "password_hash": 1},
                )
                membership["account_active"] = bool(member_user and member_user.get("is_active"))
                membership["account_activated"] = bool(member_user and member_user.get("password_hash"))
                expires_at = membership.get("invitation_expires_at")
                if isinstance(expires_at, str):
                    expires_at = datetime.fromisoformat(expires_at)
                if isinstance(expires_at, datetime) and expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
                membership["invitation_expired"] = bool(
                    not membership["account_active"] and expires_at and expires_at <= now_utc()
                )
                membership["invitation_email_status"] = membership.get("invitation_email_status", "not_sent")
            app = await db.applications.find_one({"team_id": team["team_id"]}, {"_id": 0})
            payment = await db.payments.find_one({"team_id": team["team_id"]}, {"_id": 0})
            out.append({**team, "memberships": memberships, "application": app, "payment": payment})
        return out

    @router.post("/admin/teams/{team_id}/members/{membership_id}/invitation/resend")
    async def admin_resend_member_invitation(team_id: str, membership_id: str, request: Request, user=Depends(admin)):
        await enforce_rate_limit(db, f"admin-invite:{user.id}", 20, 3600)
        team = await db.teams.find_one({"team_id": team_id}, {"_id": 0})
        if not team:
            raise HTTPException(404, "Team not found")
        membership = await db.team_memberships.find_one({
            "membership_id": membership_id, "team_id": team_id, "role": "member",
        }, {"_id": 0})
        if not membership:
            raise HTTPException(404, "Team member not found")
        result = await send_member_invitation(membership, team, user, request)
        await audit(db, user, "admin.member_invitation_resent", "membership", membership_id, request,
                    {"team_id": team_id, "email_status": result["email_status"]})
        return result

    @router.delete("/admin/teams/{team_id}")
    async def delete_team(team_id: str, request: Request, user=Depends(admin)):
        team = await db.teams.find_one({"team_id": team_id}, {"_id": 0, "leader_id": 1})
        if not team:
            raise HTTPException(404, "Team not found")

        memberships = await db.team_memberships.find(
            {"team_id": team_id}, {"_id": 0, "user_id": 1}
        ).to_list(100)
        participant_ids = {
            membership["user_id"]
            for membership in memberships
            if ObjectId.is_valid(membership.get("user_id", ""))
        }
        if ObjectId.is_valid(team.get("leader_id", "")):
            participant_ids.add(team["leader_id"])
        participant_object_ids = [ObjectId(participant_id) for participant_id in participant_ids]
        participants = await db.users.find(
            {
                "role": {"$in": TEAM_ROLES},
                "$or": [
                    {"team_id": team_id},
                    {"_id": {"$in": participant_object_ids}},
                ],
            },
            {"_id": 1},
        ).to_list(100)
        participant_ids.update(str(participant["_id"]) for participant in participants)
        participant_object_ids = [ObjectId(participant_id) for participant_id in participant_ids]
        participant_id_list = list(participant_ids)

        files = await db.files.find(
            {"$or": [
                {"team_id": team_id},
                {"owner_id": {"$in": participant_id_list}},
            ]},
            {"_id": 0, "file_id": 1},
        ).to_list(1000)
        for file in files:
            await delete_private_file(db, file["file_id"])
            await db.files.delete_one({"file_id": file["file_id"]})

        await db.sessions.delete_many({"user_id": {"$in": participant_id_list}})
        await db.invitations.delete_many(
            {"$or": [
                {"team_id": team_id},
                {"target_user_id": {"$in": participant_id_list}},
            ]}
        )
        await db.password_reset_tokens.delete_many({"user_id": {"$in": participant_id_list}})
        await db.notifications.delete_many({"user_id": {"$in": participant_id_list}})
        for collection in (
            "arena_attempts", "arena_xp", "arena_badges", "arena_opens",
            "arena_rapid_runs", "arena_events",
        ):
            await db[collection].delete_many({"user_id": {"$in": participant_id_list}})
        for collection in (
            "team_memberships", "applications", "payments", "submissions",
            "project_history", "evaluations", "judge_assignments",
        ):
            await db[collection].delete_many({"team_id": team_id})
        await db.users.delete_many({"_id": {"$in": participant_object_ids}, "role": {"$in": TEAM_ROLES}})
        await db.teams.delete_one({"team_id": team_id})
        await audit(db, user, "team.deleted", "team", team_id, request)
        return {"ok": True}

    class TeamRegistrationIn(BaseModel):
        confirmed: bool

    @router.patch("/admin/teams/{team_id}/registration")
    async def set_team_registration(team_id: str, body: TeamRegistrationIn, request: Request, user=Depends(admin)):
        team = await db.teams.find_one({"team_id": team_id}, {"_id": 0})
        if not team:
            raise HTTPException(404, "Team not found")
        status = "confirmed" if body.confirmed else "not_confirmed"
        changed = team.get("registration_review_status") != status
        user_filter = {"role": {"$in": TEAM_ROLES}, "$or": [{"team_id": team_id}]}
        if ObjectId.is_valid(team.get("leader_id", "")):
            user_filter["$or"].append({"_id": ObjectId(team["leader_id"])})

        if changed:
            expected_status = team.get("registration_review_status")
            status_filter = {"team_id": team_id}
            status_filter["registration_review_status"] = (
                expected_status
                if "registration_review_status" in team
                else {"$exists": False}
            )
            result = await db.teams.update_one(status_filter, {"$set": {
                "registration_review_status": status,
                "updated_at": now_iso(),
            }})
            if not result.matched_count:
                raise HTTPException(409, "Team registration changed concurrently; reload and try again")

        await db.users.update_many(user_filter, {"$set": {
            "is_active": body.confirmed,
            "updated_at": now_iso(),
        }})
        if not body.confirmed:
            await db.sessions.update_many(
                {"user_id": {"$in": [str(user["_id"]) for user in await db.users.find(user_filter, {"_id": 1}).to_list(100)]},
                 "revoked_at": None},
                {"$set": {"revoked_at": now_iso()}},
            )
        if changed:
            await create_notification(
                db,
                user_id=team["leader_id"],
                kind=f"registration_{status}",
                title=f"Team registration {status.replace('_', ' ')}",
                message=(
                    "Your team's registration has been confirmed and participant accounts are active."
                    if body.confirmed else
                    "Your team's registration is not confirmed and participant accounts are inactive. Contact the organizers for assistance."
                ),
                action_path="/dashboard",
            )
            await audit(db, user, f"team.registration_{status}", "team", team_id, request)
        return {"ok": True, "registration_review_status": status, "participant_accounts_active": body.confirmed}

    class TeamSelectionIn(BaseModel):
        selected: bool

    @router.patch("/admin/teams/{team_id}/selection")
    async def set_team_selection(team_id: str, body: TeamSelectionIn, request: Request, user=Depends(admin)):
        """Toggle a team's selection status and notify the team leader."""
        team = await db.teams.find_one({"team_id": team_id}, {"_id": 0})
        if not team:
            raise HTTPException(404, "Team not found")
        new_status = "selected" if body.selected else "not_selected"
        if team.get("selection_status") == new_status:
            return {"ok": True, "selection_status": new_status}
        if not body.selected and (await db.payments.find_one(
            {"team_id": team_id, "status": {"$in": [
                "payment_under_verification", "payment_verified", "registration_confirmed"
            ]}},
            {"_id": 0, "payment_id": 1},
        )):
            raise HTTPException(400, "Selection cannot be withdrawn after payment proof is submitted")
        selection_update = await db.teams.update_one(
            {"team_id": team_id, "selection_status": {"$ne": new_status}},
            {"$set": {
                "selection_status": new_status,
                "selected_by": user.id if body.selected else None,
                "selected_at": now_iso() if body.selected else None,
                "updated_at": now_iso(),
            }},
        )
        if not selection_update.matched_count:
            return {"ok": True, "selection_status": new_status}
        # If selecting, create/update application record to "selected" and send notification
        if body.selected:
            app = await db.applications.find_one({"team_id": team_id}, {"_id": 0})
            event = {"status": "selected", "at": now_iso(), "by": user.id, "note": "Selected from People section"}
            if app:
                await db.applications.update_one({"team_id": team_id}, {
                    "$set": {"status": "selected", "reviewed_at": now_iso(), "updated_at": now_iso()},
                    "$push": {"history": event}
                })
            else:
                # Create a minimal application record so payment settings become visible
                await db.applications.update_one(
                    {"team_id": team_id},
                    {"$setOnInsert": {
                        "application_id": new_public_id("SK26-AB"),
                        "team_id": team_id,
                        "leader_id": team["leader_id"],
                        "method": "admin_selection",
                        "topic_id": team.get("topic_id", ""),
                        "topic_title": team.get("topic_title", ""),
                        "admin_notes": "Selected directly from admin People section",
                        "history": [event],
                        "created_at": now_iso(),
                        "submitted_at": now_iso(),
                    }, "$set": {
                        "status": "selected",
                        "reviewed_at": now_iso(),
                        "updated_at": now_iso(),
                    }},
                    upsert=True
                )
            # Update team registration status if not in a protected state
            protected_states = {"payment_verified", "registration_confirmed"}
            if team.get("registration_status") not in protected_states:
                await db.teams.update_one({"team_id": team_id}, {"$set": {"registration_status": "selected_awaiting_payment", "updated_at": now_iso()}})
            # Ensure a payment record exists
            await db.payments.update_one({"team_id": team_id}, {
                "$setOnInsert": {"payment_id": new_public_id("PAY"), "team_id": team_id, "status": "pending", "history": [], "created_at": now_iso()},
                "$set": {"updated_at": now_iso()}
            }, upsert=True)
            # Notify the leader
            notice = await create_notification(
                db, user_id=team["leader_id"], kind="team_selected",
                title="Congratulations! Your team has been selected.",
                message="Congratulations! Your team has been selected. Kindly proceed with the registration payment.",
                action_path="/dashboard?section=payment"
            )
            await audit(db, user, "team.selected", "team", team_id, request)
            return {"ok": True, "selection_status": new_status, "email_status": notice.get("email_status")}
        else:
            await db.applications.update_one(
                {"team_id": team_id, "status": "selected"},
                {"$set": {"status": "rejected", "reviewed_at": now_iso(), "updated_at": now_iso()},
                 "$push": {"history": {"status": "rejected", "at": now_iso(), "by": user.id,
                                       "note": "Not selected from People section"}}},
            )
            if team.get("registration_status") not in {"payment_verified", "registration_confirmed"}:
                await db.teams.update_one({"team_id": team_id}, {"$set": {
                    "registration_status": "not_selected", "updated_at": now_iso()
                }})
            await audit(db, user, "team.deselected", "team", team_id, request)
            return {"ok": True, "selection_status": new_status}

    @router.get("/admin/participants")
    async def admin_participants(_: object = Depends(admin)):
        participants = [
            clean_doc(x) for x in await db.users.find(
                {"role": {"$in": TEAM_ROLES}},
                {"password_hash": 0, "session_version": 0},
            ).sort("created_at", -1).to_list(10000)
        ]
        teams = await db.teams.find(
            {"team_id": {"$in": list({row.get("team_id") for row in participants if row.get("team_id")})}},
            {"_id": 0, "team_id": 1, "registration_review_status": 1},
        ).to_list(5000)
        registration_by_team = {team["team_id"]: team.get("registration_review_status", "not_confirmed") for team in teams}
        for participant in participants:
            participant["registration_review_status"] = registration_by_team.get(
                participant.get("team_id"), "not_confirmed"
            )
        return participants

    @router.get("/admin/topics")
    async def topics(_: object = Depends(admin)):
        return await db.topics.find({}, {"_id": 0}).sort("order", 1).to_list(100)

    @router.post("/admin/topics")
    async def create_topic(body: TopicIn, request: Request, user=Depends(admin)):
        topic = {"topic_id": new_public_id("TOP"), **body.model_dump(), "order": await db.topics.count_documents({}) + 1,
                 "created_at": now_iso(), "updated_at": now_iso()}
        await db.topics.insert_one(topic.copy())
        await audit(db, user, "topic.created", "topic", topic["topic_id"], request)
        return topic

    @router.put("/admin/topics/order")
    async def order_topics(body: TopicOrderIn, request: Request, user=Depends(admin)):
        existing = await db.topics.distinct("topic_id")
        if len(body.topic_ids) != len(set(body.topic_ids)) or set(body.topic_ids) != set(existing):
            raise HTTPException(400, "Topic order must include every topic exactly once")
        for order, topic_id in enumerate(body.topic_ids, 1):
            await db.topics.update_one({"topic_id": topic_id}, {"$set": {"order": order, "updated_at": now_iso()}})
        await audit(db, user, "topics.reordered", "topics", "all", request, {"topic_ids": body.topic_ids})
        return await db.topics.find({}, {"_id": 0}).sort("order", 1).to_list(100)

    @router.put("/admin/topics/{topic_id}")
    async def update_topic(topic_id: str, body: TopicIn, request: Request, user=Depends(admin)):
        result = await db.topics.update_one({"topic_id": topic_id}, {"$set": {**body.model_dump(), "updated_at": now_iso()}})
        if not result.matched_count:
            raise HTTPException(404, "Topic not found")
        await audit(db, user, "topic.updated", "topic", topic_id, request)
        return await db.topics.find_one({"topic_id": topic_id}, {"_id": 0})

    @router.delete("/admin/topics/{topic_id}")
    async def delete_topic(topic_id: str, request: Request, user=Depends(admin)):
        if await db.applications.find_one({"topic_id": topic_id}):
            raise HTTPException(400, "Disable this topic instead; applications already reference it")
        result = await db.topics.delete_one({"topic_id": topic_id})
        if not result.deleted_count:
            raise HTTPException(404, "Topic not found")
        await audit(db, user, "topic.deleted", "topic", topic_id, request)
        return {"ok": True}

    @router.get("/admin/applications")
    async def applications(q: str = "", _: object = Depends(admin)):
        docs = await db.applications.find({}, {"_id": 0}).sort("submitted_at", -1).to_list(10000)
        if q:
            needle = q.lower()
            docs = [x for x in docs if needle in " ".join(str(x.get(k, "")) for k in ("team_name", "leader_name", "contact_email", "topic_title", "application_id")).lower()]
        for doc in docs:
            if doc.get("team_id"):
                team = await db.teams.find_one({"team_id": doc["team_id"]}, {"_id": 0})
                doc["team"] = team
                doc["memberships"] = await db.team_memberships.find({"team_id": doc["team_id"]}, {"_id": 0}).to_list(20)
        return docs

    @router.post("/admin/applications/manual")
    async def manual_application(body: ManualApplicationIn, request: Request, user=Depends(admin)):
        topic = await db.topics.find_one({"topic_id": body.topic_id}, {"_id": 0})
        if not topic:
            raise HTTPException(400, "Topic not found")
        doc = {"application_id": new_public_id("SK26-EMAIL"), "method": "email", "team_id": None,
               "team_name": body.team_name.strip(), "college": body.college.strip(), "leader_name": body.leader_name.strip(),
               "contact_email": normalize_email(str(body.contact_email)), "topic_id": body.topic_id, "topic_title": topic["title"],
               "submitted_at": body.submission_date, "status": body.status, "admin_notes": body.notes,
               "history": [{"status": body.status, "at": now_iso(), "by": user.id, "note": "Manually recorded email submission"}],
               "created_at": now_iso(), "updated_at": now_iso()}
        await db.applications.insert_one(doc.copy())
        await audit(db, user, "application.manual_created", "application", doc["application_id"], request)
        return doc

    @router.patch("/admin/applications/{application_id}")
    async def review_application(application_id: str, body: ApplicationReviewIn, request: Request, user=Depends(admin)):
        app = await db.applications.find_one({"application_id": application_id}, {"_id": 0})
        if not app:
            raise HTTPException(404, "Application not found")
        status_changed = app.get("status") != body.status
        update = {"$set": {"admin_notes": body.admin_notes, "updated_at": now_iso()}}
        application_filter = {"application_id": application_id}
        if status_changed:
            event = {"status": body.status, "at": now_iso(), "by": user.id, "note": body.admin_notes}
            update["$set"].update({"status": body.status, "reviewed_at": now_iso()})
            update["$push"] = {"history": event}
            application_filter["status"] = app.get("status") if "status" in app else {"$exists": False}
        result = await db.applications.update_one(application_filter, update)
        if status_changed and not result.matched_count:
            raise HTTPException(409, "Application status changed concurrently; reload and try again")
        email_status = "not_applicable"
        if status_changed and app.get("team_id"):
            team = await db.teams.find_one({"team_id": app["team_id"]}, {"_id": 0})
            leader_user = await db.users.find_one({"_id": ObjectId(team["leader_id"])}, {"_id": 0})
            if body.status == "selected":
                protected_states = {"payment_verified", "registration_confirmed"}
                next_state = team.get("registration_status") if team.get("registration_status") in protected_states else "selected_awaiting_payment"
                await db.teams.update_one({"team_id": app["team_id"]}, {"$set": {"registration_status": next_state, "updated_at": now_iso()}})
                await db.payments.update_one({"team_id": app["team_id"]}, {"$setOnInsert": {"payment_id": new_public_id("PAY"), "team_id": app["team_id"], "status": "pending", "history": [], "created_at": now_iso()}, "$set": {"updated_at": now_iso()}}, upsert=True)
                subject, html = emailer.shortlist_email(leader_user, f"{app_url(request)}/dashboard?section=payment")
                notice = await create_notification(db, user_id=team["leader_id"], kind="abstract_selected", title="Abstract selected — payment required",
                                                   message="Your abstract was selected. Review the organizer-configured payment instructions to continue registration.",
                                                   emailer=emailer, email_content=(subject, html), action_path="/dashboard?section=payment")
                email_status = notice["email_status"]
            elif body.status == "rejected":
                await db.teams.update_one({"team_id": app["team_id"]}, {"$set": {"registration_status": "abstract_rejected", "updated_at": now_iso()}})
                subject, html = emailer.status_email(leader_user["name"], "Abstract application update",
                                                     "Your SANKALP'26 abstract was not selected for this edition.", f"{app_url(request)}/dashboard")
                notice = await create_notification(db, user_id=team["leader_id"], kind="abstract_rejected", title="Abstract application update",
                                                   message="Your abstract was not selected for this edition.", emailer=emailer,
                                                   email_content=(subject, html), action_path="/dashboard")
                email_status = notice["email_status"]
            else:
                status_message = {
                    "pending": "Your abstract is pending review.",
                    "under_review": "Your abstract is now under review.",
                }[body.status]
                await create_notification(
                    db,
                    user_id=team["leader_id"],
                    kind=f"abstract_{body.status}",
                    title=f"Abstract {body.status.replace('_', ' ')}",
                    message=status_message,
                    action_path="/dashboard?section=abstract",
                )
        await audit(db, user, f"application.{body.status}", "application", application_id, request)
        return {"application": await db.applications.find_one({"application_id": application_id}, {"_id": 0}), "email_status": email_status}

    @router.get("/admin/payment-settings")
    async def payment_settings(_: object = Depends(admin)):
        return await db.settings.find_one({"key": "payment"}, {"_id": 0}) or {"key": "payment"}

    @router.put("/admin/payment-settings")
    async def update_payment_settings(body: PaymentSettingsIn, request: Request, user=Depends(admin)):
        patch = {**body.model_dump(), "key": "payment", "updated_at": now_iso()}
        await db.settings.update_one({"key": "payment"}, {"$set": patch}, upsert=True)
        await audit(db, user, "payment.settings_updated", "settings", "payment", request)
        return await db.settings.find_one({"key": "payment"}, {"_id": 0})

    @router.post("/admin/payment-settings/qr")
    async def payment_qr(request: Request, file: UploadFile = File(...), user=Depends(admin)):
        meta = await store_private_file(db, file=file, owner_id=user.id, team_id="global", kind="payment_qr",
                                        max_bytes=3 * 1024 * 1024, allowed={"png", "jpg", "pdf"})
        old = await db.settings.find_one({"key": "payment"}, {"_id": 0, "qr_file": 1})
        await db.settings.update_one({"key": "payment"}, {"$set": {"qr_file": meta, "updated_at": now_iso()}}, upsert=True)
        if old and (old.get("qr_file") or {}).get("file_id"):
            await delete_private_file(db, old["qr_file"]["file_id"])
        await audit(db, user, "payment.qr_updated", "settings", "payment", request)
        return meta

    @router.get("/admin/payments")
    async def payments(_: object = Depends(admin)):
        docs = await db.payments.find({}, {"_id": 0}).sort("updated_at", -1).to_list(10000)
        for doc in docs:
            doc["team"] = await db.teams.find_one({"team_id": doc["team_id"]}, {"_id": 0})
        return docs

    @router.patch("/admin/payments/{payment_id}")
    async def decide_payment(payment_id: str, body: PaymentDecisionIn, request: Request, user=Depends(admin)):
        payment = await db.payments.find_one({"payment_id": payment_id}, {"_id": 0})
        if not payment:
            raise HTTPException(404, "Payment not found")
        if payment.get("status") != "payment_under_verification":
            raise HTTPException(400, "Only submitted proof can be decided")
        if body.action in {"reject", "request_correction"} and not body.reason.strip():
            raise HTTPException(400, "Provide a reason for rejecting or requesting a correction")
        status = {"approve": "payment_verified", "reject": "correction_required", "request_correction": "correction_required"}[body.action]
        event = {"status": status, "at": now_iso(), "by": user.id, "note": body.reason}
        result = await db.payments.update_one(
            {"payment_id": payment_id, "status": "payment_under_verification"},
            {"$set": {"status": status, "decision_reason": body.reason,
                      "verified_at": now_iso() if status == "payment_verified" else None,
                      "verified_by": user.id if status == "payment_verified" else None,
                      "updated_at": now_iso()},
             "$push": {"history": event}},
        )
        if not result.matched_count:
            raise HTTPException(409, "Payment proof was already decided")
        team = await db.teams.find_one({"team_id": payment["team_id"]}, {"_id": 0})
        await db.teams.update_one({"team_id": payment["team_id"]}, {"$set": {"registration_status": status, "updated_at": now_iso()}})
        title = "Payment verified" if status == "payment_verified" else "Payment proof correction required"
        message = "Your payment was independently verified. Final registration approval is still pending." if status == "payment_verified" else f"Please replace your payment proof. {body.reason}".strip()
        lead = await db.users.find_one({"_id": ObjectId(team["leader_id"])}, {"_id": 0})
        mail = emailer.status_email(lead["name"], title, message, f"{app_url(request)}/dashboard?section=payment")
        notice = await create_notification(db, user_id=team["leader_id"], kind=status, title=title, message=message,
                                           emailer=emailer, email_content=mail, action_path="/dashboard?section=payment")
        await audit(db, user, f"payment.{body.action}", "payment", payment_id, request, {"reason": body.reason})
        return {"payment": await db.payments.find_one({"payment_id": payment_id}, {"_id": 0}), "email_status": notice["email_status"]}

    @router.post("/admin/payments/{payment_id}/confirm-registration")
    async def confirm_registration(payment_id: str, request: Request, user=Depends(admin)):
        payment = await db.payments.find_one({"payment_id": payment_id, "status": "payment_verified"}, {"_id": 0})
        if not payment:
            raise HTTPException(400, "Payment must be verified before registration approval")
        event = {"status": "registration_confirmed", "at": now_iso(), "by": user.id, "note": "Explicit final registration approval"}
        result = await db.payments.update_one(
            {"payment_id": payment_id, "status": "payment_verified"},
            {"$set": {"status": "registration_confirmed", "confirmed_at": now_iso(),
                      "confirmed_by": user.id, "updated_at": now_iso()},
             "$push": {"history": event}},
        )
        if not result.matched_count:
            raise HTTPException(409, "Registration was already confirmed")
        await db.teams.update_one({"team_id": payment["team_id"]}, {"$set": {"registration_status": "registration_confirmed", "updated_at": now_iso()}})
        team = await db.teams.find_one({"team_id": payment["team_id"]}, {"_id": 0})
        lead = await db.users.find_one({"_id": ObjectId(team["leader_id"])}, {"_id": 0})
        message = "Your team's SANKALP'26 registration has been approved."
        mail = emailer.status_email(lead["name"], "Registration confirmed", message, f"{app_url(request)}/dashboard")
        notice = await create_notification(db, user_id=team["leader_id"], kind="registration_confirmed", title="Registration confirmed",
                                           message=message, emailer=emailer, email_content=mail, action_path="/dashboard")
        await audit(db, user, "registration.confirmed", "team", payment["team_id"], request)
        return {"ok": True, "email_status": notice["email_status"]}

    @router.get("/admin/timeline")
    async def get_timeline(_: object = Depends(admin)):
        return await _timeline(db)

    @router.put("/admin/timeline")
    async def update_timeline(body: TimelineIn, request: Request, user=Depends(admin)):
        data = {**body.model_dump(), "key": "timeline", "updated_at": now_iso()}
        await db.settings.update_one({"key": "timeline"}, {"$set": data}, upsert=True)
        await audit(db, user, "timeline.updated", "settings", "timeline", request)
        return await _timeline(db)

    @router.get("/admin/projects")
    async def admin_projects(_: object = Depends(admin)):
        docs = await db.submissions.find({}, {"_id": 0}).sort("updated_at", -1).to_list(10000)
        for doc in docs:
            doc["team"] = await db.teams.find_one({"team_id": doc["team_id"]}, {"_id": 0})
            doc["history"] = await db.project_history.find({"submission_id": doc["submission_id"]}, {"_id": 0}).sort("at", -1).to_list(100)
        return docs

    @router.post("/admin/projects/{submission_id}/reopen")
    async def reopen_project(submission_id: str, request: Request, user=Depends(admin)):
        submission = await db.submissions.find_one({"submission_id": submission_id, "status": "submitted"}, {"_id": 0})
        if not submission:
            raise HTTPException(404, "Finalized project not found")
        await db.submissions.update_one({"submission_id": submission_id}, {"$set": {
            "status": "draft", "reopened_at": now_iso(), "reopened_by": user.id, "updated_at": now_iso()}})
        await db.project_history.insert_one({"history_id": new_public_id("HIS"), "team_id": submission["team_id"],
                                             "submission_id": submission_id, "action": "reopened_by_admin",
                                             "by": user.id, "at": now_iso()})
        await audit(db, user, "project.reopened", "submission", submission_id, request,
                    {"team_id": submission["team_id"]})
        return await db.submissions.find_one({"submission_id": submission_id}, {"_id": 0})

    @router.get("/admin/notifications")
    async def admin_notifications(_: object = Depends(admin)):
        docs = await db.notifications.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)
        for doc in docs:
            if ObjectId.is_valid(doc.get("user_id", "")):
                recipient = await db.users.find_one({"_id": ObjectId(doc["user_id"])}, {"_id": 0, "name": 1, "email": 1})
                doc["recipient"] = recipient
        return docs

    @router.get("/admin/audit-log")
    async def audit_log(_: object = Depends(admin)):
        return await db.audit_logs.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)

    @router.post("/admin/notifications/{notification_id}/retry")
    async def retry_notification(notification_id: str, request: Request, user=Depends(admin)):
        notice = await db.notifications.find_one({"notification_id": notification_id, "email_status": "failed"}, {"_id": 0})
        if not notice:
            raise HTTPException(404, "Failed notification not found")
        if notice.get("kind") in {"verify_email", "member_activation", "judge_activation", "password_reset"}:
            raise HTTPException(400, "Security-link emails require a newly generated token")
        recipient = await db.users.find_one({"_id": valid_oid(notice["user_id"])}, {"_id": 0, "email": 1, "name": 1})
        if not recipient:
            raise HTTPException(404, "Recipient account not found")
        destination = f"{app_url(request)}{notice.get('action_path') or '/dashboard'}"
        subject, html = emailer.status_email(recipient["name"], notice["title"], notice["message"], destination)
        provider_id = await emailer.send_email(to=recipient["email"], subject=subject, html=html)
        status = "sent" if provider_id else "failed"
        await db.notifications.update_one({"notification_id": notification_id}, {"$set": {
            "email_status": status, "email_provider_id": provider_id, "email_updated_at": now_iso()}})
        await audit(db, user, "notification.email_retried", "notification", notification_id, request, {"result": status})
        return {"email_status": status}

    @router.get("/admin/judges")
    async def judges(_: object = Depends(admin)):
        raw = await db.users.find({"role": "judge"}, {"password_hash": 0, "session_version": 0}).to_list(1000)
        docs = [clean_doc(doc) for doc in raw]
        for doc in docs:
            doc["assignments"] = await db.judge_assignments.count_documents({"judge_id": doc["id"]})
        return docs

    @router.post("/admin/judges")
    async def invite_judge(body: JudgeInviteIn, request: Request, user=Depends(admin)):
        email = normalize_email(str(body.email))
        existing = await db.users.find_one({"email": email})
        if existing and (existing.get("role") != "judge" or existing.get("is_active") or existing.get("password_hash")):
            raise HTTPException(400, "An active account already uses this email")
        if existing:
            uid = existing["_id"]
            await db.invitations.update_many(
                {"target_user_id": str(uid), "purpose": "judge_activation", "used_at": None, "revoked_at": None},
                {"$set": {"revoked_at": now_iso()}},
            )
            await db.users.update_one({"_id": uid}, {"$set": {
                "name": body.name.strip(), "activation_status": "pending", "is_active": False,
                "email_verified": False, "updated_at": now_iso(),
            }})
            judge_doc = await db.users.find_one({"_id": uid})
            action = "judge.activation_resent"
        else:
            uid = ObjectId()
            judge_doc = {"_id": uid, "email": email, "name": body.name.strip(), "role": "judge", "password_hash": None,
                         "is_active": False, "email_verified": False, "activation_status": "pending",
                         "must_change_password": False, "session_version": 0, "created_at": now_iso()}
            await db.users.insert_one(judge_doc)
            action = "judge.invited"
        invite = await create_invitation(clean_doc(judge_doc), "judge_activation", None, frontend_url(request), 72)
        await audit(db, user, action, "judge", str(uid), request)
        return {"user": {k: v for k, v in clean_doc(judge_doc).items() if k != "password_hash"}, "email_status": invite["email_status"]}

    @router.post("/admin/judge-assignments")
    async def assign_judge(body: AssignmentIn, request: Request, user=Depends(admin)):
        if not await db.users.find_one({"_id": valid_oid(body.judge_id), "role": "judge"}) or not await db.teams.find_one({"team_id": body.team_id}):
            raise HTTPException(404, "Judge or team not found")
        doc = {"assignment_id": new_public_id("ASN"), "judge_id": body.judge_id, "team_id": body.team_id,
               "phases": sorted(set(body.phases)), "created_at": now_iso(), "updated_at": now_iso()}
        await db.judge_assignments.update_one({"judge_id": body.judge_id, "team_id": body.team_id}, {"$set": doc}, upsert=True)
        await audit(db, user, "judge.assignment_updated", "team", body.team_id, request, {"judge_id": body.judge_id, "phases": body.phases})
        return doc

    @router.delete("/admin/judge-assignments/{assignment_id}")
    async def remove_assignment(assignment_id: str, request: Request, user=Depends(admin)):
        result = await db.judge_assignments.delete_one({"assignment_id": assignment_id})
        if not result.deleted_count:
            raise HTTPException(404, "Assignment not found")
        await audit(db, user, "judge.assignment_removed", "assignment", assignment_id, request)
        return {"ok": True}

    @router.get("/admin/judging")
    async def judging_config(_: object = Depends(admin)):
        return {"criteria": await db.judging_criteria.find({}, {"_id": 0}).sort([("phase", 1), ("order", 1)]).to_list(200),
                "assignments": await db.judge_assignments.find({}, {"_id": 0}).to_list(10000),
                "formula": await db.settings.find_one({"key": "judging_formula"}, {"_id": 0}),
                "windows": await db.settings.find_one({"key": "judging_windows"}, {"_id": 0}) or {"phase1_open": False, "phase2_open": False},
                "evaluations": await db.evaluations.find({}, {"_id": 0}).to_list(20000)}

    @router.put("/admin/judging/windows")
    async def judging_windows(body: JudgingWindowsIn, request: Request, user=Depends(admin)):
        doc = {"key": "judging_windows", **body.model_dump(), "updated_at": now_iso(), "updated_by": user.id}
        await db.settings.update_one({"key": "judging_windows"}, {"$set": doc}, upsert=True)
        await audit(db, user, "judging.windows_updated", "settings", "judging_windows", request, body.model_dump())
        return doc

    @router.post("/admin/judging/criteria")
    async def create_criterion(body: CriteriaIn, request: Request, user=Depends(admin)):
        doc = {"criterion_id": new_public_id("CRT"), **body.model_dump(),
               "order": await db.judging_criteria.count_documents({"phase": body.phase}) + 1, "created_at": now_iso(), "updated_at": now_iso()}
        await db.judging_criteria.insert_one(doc.copy())
        await audit(db, user, "judging.criterion_created", "criterion", doc["criterion_id"], request)
        return doc

    @router.put("/admin/judging/criteria/{criterion_id}")
    async def update_criterion(criterion_id: str, body: CriteriaIn, request: Request, user=Depends(admin)):
        result = await db.judging_criteria.update_one({"criterion_id": criterion_id}, {"$set": {**body.model_dump(), "updated_at": now_iso()}})
        if not result.matched_count:
            raise HTTPException(404, "Criterion not found")
        await audit(db, user, "judging.criterion_updated", "criterion", criterion_id, request)
        return await db.judging_criteria.find_one({"criterion_id": criterion_id}, {"_id": 0})

    @router.delete("/admin/judging/criteria/{criterion_id}")
    async def delete_criterion(criterion_id: str, request: Request, user=Depends(admin)):
        if await db.evaluations.find_one({"scores.criterion_id": criterion_id}):
            raise HTTPException(400, "Deactivate this criterion; evaluations already reference it")
        result = await db.judging_criteria.delete_one({"criterion_id": criterion_id})
        if not result.deleted_count:
            raise HTTPException(404, "Criterion not found")
        await audit(db, user, "judging.criterion_deleted", "criterion", criterion_id, request)
        return {"ok": True}

    @router.put("/admin/judging/formula")
    async def formula(body: FormulaIn, request: Request, user=Depends(admin)):
        if body.phase1_weight + body.phase2_weight <= 0:
            raise HTTPException(400, "At least one phase must have weight")
        doc = {"key": "judging_formula", **body.model_dump(), "configured": True, "updated_at": now_iso(), "updated_by": user.id}
        await db.settings.update_one({"key": "judging_formula"}, {"$set": doc}, upsert=True)
        await audit(db, user, "judging.formula_configured", "settings", "judging_formula", request)
        return doc

    @router.post("/admin/evaluations/{evaluation_id}/reopen")
    async def reopen_evaluation(evaluation_id: str, request: Request, user=Depends(admin)):
        result = await db.evaluations.update_one({"evaluation_id": evaluation_id, "status": "submitted"}, {"$set": {"status": "draft", "reopened_at": now_iso(), "reopened_by": user.id}})
        if not result.matched_count:
            raise HTTPException(404, "Submitted evaluation not found")
        await audit(db, user, "evaluation.reopened", "evaluation", evaluation_id, request)
        return {"ok": True}

    @router.get("/admin/results")
    async def admin_results(_: object = Depends(admin)):
        phases = {}
        for phase in ("phase1", "phase2"):
            phases[phase] = await db.evaluations.find({"phase": phase, "status": "submitted"}, {"_id": 0}).to_list(10000)
        return {"phases": phases, "consolidated": await consolidated_results(db)}

    # ---------------- Judge ----------------
    @router.get("/judge/submissions")
    async def judge_submissions(user=Depends(judge)):
        if user.role == "admin":
            team_ids = await db.teams.distinct("team_id")
            assignments = [{"team_id": x, "phases": ["phase1", "phase2"]} for x in team_ids]
        else:
            assignments = await db.judge_assignments.find({"judge_id": user.id}, {"_id": 0}).to_list(5000)
            team_ids = [x["team_id"] for x in assignments]
        allowed = {x["team_id"]: x["phases"] for x in assignments}
        subs = await db.submissions.find({"team_id": {"$in": team_ids}, "status": {"$in": ["draft", "submitted"]}}, {"_id": 0}).to_list(5000)
        out = []
        for sub in subs:
            sub["team"] = await db.teams.find_one({"team_id": sub["team_id"]}, {"_id": 0})
            sub["application"] = await db.applications.find_one({"team_id": sub["team_id"]}, {"_id": 0})
            sub["allowed_phases"] = [phase for phase in allowed[sub["team_id"]] if phase == "phase1" or sub.get("status") == "submitted"]
            if not sub["allowed_phases"]:
                continue
            sub["evaluations"] = await db.evaluations.find({"team_id": sub["team_id"], "judge_id": user.id}, {"_id": 0}).to_list(10)
            out.append(sub)
        return out

    @router.get("/judge/criteria/{phase}")
    async def judge_criteria(phase: Literal["phase1", "phase2"], _: object = Depends(judge)):
        return await db.judging_criteria.find({"phase": phase, "active": True}, {"_id": 0}).sort("order", 1).to_list(100)

    @router.put("/judge/evaluations/{team_id}")
    async def save_evaluation(team_id: str, body: EvaluationIn, request: Request, user=Depends(judge)):
        windows = await db.settings.find_one({"key": "judging_windows"}, {"_id": 0}) or {}
        if user.role != "admin" and not windows.get(f"{body.phase}_open", False):
            raise HTTPException(400, "This evaluation phase is closed")
        if user.role != "admin":
            assignment = await db.judge_assignments.find_one({"judge_id": user.id, "team_id": team_id, "phases": body.phase})
            if not assignment:
                raise HTTPException(403, "This team and phase are not assigned to you")
        valid_statuses = ["draft", "submitted"] if body.phase == "phase1" else ["submitted"]
        submission = await db.submissions.find_one({"team_id": team_id, "status": {"$in": valid_statuses}}, {"_id": 0})
        if not submission:
            raise HTTPException(404, "Submitted project not found")
        existing = await db.evaluations.find_one({"team_id": team_id, "judge_id": user.id, "phase": body.phase}, {"_id": 0})
        if existing and existing.get("status") == "submitted":
            raise HTTPException(400, "Submitted evaluation is locked")
        criteria = await db.judging_criteria.find({"phase": body.phase, "active": True}, {"_id": 0}).to_list(100)
        if not criteria:
            raise HTTPException(400, "No active criteria are configured for this phase")
        by_id = {x["criterion_id"]: x for x in criteria}
        scores = []
        score_ids = [x.criterion_id for x in body.scores]
        if len(score_ids) != len(set(score_ids)) or set(score_ids) != set(by_id):
            raise HTTPException(400, "Provide a score for every active criterion")
        weighted = weight_total = 0
        for item in body.scores:
            criterion = by_id[item.criterion_id]
            if item.marks > criterion["max_marks"]:
                raise HTTPException(400, f"{criterion['title']} exceeds its maximum marks")
            normalized = item.marks / criterion["max_marks"] * 100
            weighted += normalized * criterion["weight"]
            weight_total += criterion["weight"]
            scores.append({"criterion_id": item.criterion_id, "title": criterion["title"], "marks": item.marks,
                           "max_marks": criterion["max_marks"], "weight": criterion["weight"]})
        doc = {"evaluation_id": existing.get("evaluation_id") if existing else new_public_id("EVAL"), "team_id": team_id,
               "submission_id": submission["submission_id"], "judge_id": user.id, "judge_name": user.name, "phase": body.phase,
               "scores": scores, "comment": body.comment, "normalized_total": round(weighted / weight_total, 2),
               "status": "submitted" if body.action == "submit" else "draft", "updated_at": now_iso()}
        if body.action == "submit":
            doc["submitted_at"] = now_iso()
        await db.evaluations.update_one({"team_id": team_id, "judge_id": user.id, "phase": body.phase}, {"$set": doc, "$setOnInsert": {"created_at": now_iso()}}, upsert=True)
        await db.evaluation_history.insert_one({"history_id": new_public_id("EVH"), "evaluation_id": doc["evaluation_id"],
                                                "snapshot": doc, "action": body.action, "by": user.id, "at": now_iso()})
        await audit(db, user, f"evaluation.{body.action}", "evaluation", doc["evaluation_id"], request)
        return doc

    return router


async def setup_phase1(db, topics):
    await db.users.create_index("email", unique=True)
    await db.users.create_index("usn", unique=True, sparse=True)
    await db.teams.create_index("team_id", unique=True)
    await db.teams.create_index("name_key", unique=True)
    await db.team_memberships.create_index([("team_id", 1), ("email", 1)], unique=True)
    await db.invitations.create_index("token_hash", unique=True)
    await db.invitations.create_index("expires_at", expireAfterSeconds=0)
    await db.password_reset_tokens.create_index("token_hash", unique=True)
    await db.password_reset_tokens.create_index("expires_at", expireAfterSeconds=0)
    await db.sessions.create_index("sid", unique=True)
    await db.sessions.create_index("expires_at", expireAfterSeconds=0)
    await db.rate_limits.create_index([("key", 1), ("bucket", 1)], unique=True)
    await db.rate_limits.create_index("expires_at", expireAfterSeconds=0)
    await db.topics.create_index("topic_id", unique=True)
    await db.applications.create_index("application_id", unique=True)
    application_indexes = await db.applications.index_information()
    if "team_id_1" in application_indexes and not application_indexes["team_id_1"].get("partialFilterExpression"):
        await db.applications.drop_index("team_id_1")
    await db.applications.create_index("team_id", unique=True,
                                       partialFilterExpression={"team_id": {"$type": "string"}})
    await db.payments.create_index("payment_id", unique=True)
    await db.payments.create_index("team_id", unique=True)
    await db.submissions.create_index("team_id", unique=True)
    await db.judge_assignments.create_index([("judge_id", 1), ("team_id", 1)], unique=True)
    await db.judging_criteria.create_index("criterion_id", unique=True)
    evaluation_indexes = await db.evaluations.index_information()
    if "submission_id_1_judge_id_1" in evaluation_indexes:
        await db.evaluations.drop_index("submission_id_1_judge_id_1")
    await db.files.create_index("file_id", unique=True)
    await db.notifications.create_index("notification_id", unique=True)
    await db.audit_logs.create_index("created_at")
    for index, topic in enumerate(topics, 1):
        await db.topics.update_one({"topic_id": topic["topic_id"]}, {"$setOnInsert": {**topic, "order": index, "enabled": True, "created_at": now_iso(), "updated_at": now_iso()}}, upsert=True)
    await db.settings.update_one({"key": "timeline"}, {"$setOnInsert": {"key": "timeline", **TIMELINE_DEFAULTS}}, upsert=True)
    await db.settings.update_one({"key": "judging_windows"}, {"$setOnInsert": {"key": "judging_windows", "phase1_open": False, "phase2_open": False}}, upsert=True)
    # Migrate teams still stuck in email_verification_pending → registered (email verification removed)
    await db.teams.update_many(
        {"registration_status": "email_verification_pending"},
        {"$set": {"registration_status": "registered", "updated_at": now_iso()}}
    )
    # Activate users who were created before email-verification was removed
    await db.users.update_many(
        {"role": "team", "is_active": False},
        {"$set": {"is_active": True, "email_verified": True}}
    )
    await db.team_memberships.update_many(
        {"role": "leader", "status": "pending_verification"},
        {"$set": {"status": "active"}}
    )
    # Preserve existing leaders and their IDs as team IDs so submissions and Arena relationships stay valid.
    async for leader in db.users.find({"role": "team"}):
        team_id = str(leader["_id"])
        await db.users.update_one({"_id": leader["_id"]}, {"$set": {"team_id": team_id, "is_active": leader.get("is_active", True),
                                                                     "email_verified": leader.get("email_verified", True), "session_version": leader.get("session_version", 0)}})
        team = {"team_id": team_id, "name": leader.get("team_name") or leader.get("name"),
                "name_key": (leader.get("team_name") or leader.get("name") or team_id).strip().lower(), "college": leader.get("college", ""),
                "leader_id": team_id, "topic_title": leader.get("track"), "registration_status": "registered",
                "created_at": leader.get("created_at", now_iso()), "updated_at": now_iso()}
        await db.teams.update_one({"team_id": team_id}, {"$setOnInsert": team}, upsert=True)
        await db.team_memberships.update_one({"team_id": team_id, "email": leader["email"]}, {"$setOnInsert": {
            "membership_id": new_public_id("MEM"), "team_id": team_id, "user_id": team_id, "name": leader.get("name", ""),
            "email": leader["email"], "usn": leader.get("usn", "LEGACY-" + team_id[-6:]), "college": leader.get("college", ""),
            "role": "leader", "status": "active", "created_at": now_iso()}}, upsert=True)
        for member in leader.get("members", []):
            if member.get("email"):
                await db.team_memberships.update_one({"team_id": team_id, "email": member["email"].lower()}, {"$setOnInsert": {
                    "membership_id": new_public_id("MEM"), "team_id": team_id, "user_id": None, "name": member.get("name", ""),
                    "email": member["email"].lower(), "usn": member.get("usn") or "LEGACY-" + uuid.uuid4().hex[:6].upper(),
                    "college": leader.get("college", ""), "role": "member", "status": "pending", "created_at": now_iso()}}, upsert=True)
    await db.files.update_many({"team_id": {"$exists": False}}, [{"$set": {"team_id": "$owner_id"}}])
    async for submission in db.submissions.find({"submission_id": {"$exists": False}}):
        await db.submissions.update_one({"_id": submission["_id"]}, {"$set": {
            "submission_id": new_public_id("SK26-PRJ"), "status": "submitted", "submitted_at": submission.get("updated_at", now_iso()),
            "resources": submission.get("resources", []), "legacy": True}})
    # Preserve legacy scores as Phase 2 records without overwriting their original fields.
    async for evaluation in db.evaluations.find({"phase": {"$exists": False}}):
        submission = None
        if ObjectId.is_valid(evaluation.get("submission_id", "")):
            submission = await db.submissions.find_one({"_id": ObjectId(evaluation["submission_id"])}, {"team_id": 1})
        patch = {"phase": "phase2", "status": "submitted", "legacy": True,
                 "evaluation_id": evaluation.get("evaluation_id") or new_public_id("EVAL")}
        if submission:
            patch["team_id"] = submission["team_id"]
        if "total" in evaluation:
            patch["normalized_total"] = round(float(evaluation["total"]) / 40 * 100, 2)
        await db.evaluations.update_one({"_id": evaluation["_id"]}, {"$set": patch})
    await db.evaluations.create_index(
        [("team_id", 1), ("judge_id", 1), ("phase", 1)], unique=True,
        partialFilterExpression={"team_id": {"$type": "string"}, "judge_id": {"$type": "string"}, "phase": {"$type": "string"}},
    )
    existing_criteria = [
        ("innovation", "Innovation"), ("technical", "Technical depth"),
        ("feasibility", "Feasibility"), ("presentation", "Presentation / UX"),
    ]
    for order, (criterion_id, title) in enumerate(existing_criteria, 1):
        await db.judging_criteria.update_one({"criterion_id": criterion_id}, {"$setOnInsert": {
            "criterion_id": criterion_id, "phase": "phase2", "title": title, "description": "Existing SANKALP'26 criterion",
            "max_marks": 10, "weight": 1, "active": True, "order": order, "created_at": now_iso(), "updated_at": now_iso()}}, upsert=True)