import asyncio
import hashlib
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated, List, Literal, Optional
from urllib.parse import urlparse

from dotenv import load_dotenv
from email_validator import EmailNotValidError, validate_email

# server.py is inside the backend folder; the .env file is in the project root.
ROOT_DIR = Path(__file__).resolve().parent
load_dotenv(ROOT_DIR / ".env")

import bcrypt
import jwt
from bson import ObjectId
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, Response
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import DuplicateKeyError
from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)
from starlette.middleware.cors import CORSMiddleware

# Import sibling modules through the backend package.
from backend import emailer
from backend.arena import build_router as build_arena_router, setup_arena
from backend.core_utils import (
    app_url,
    app_environment,
    audit,
    cleanup_pending_private_files,
    clean_doc,
    enforce_rate_limit,
    frontend_url,
    new_public_id,
    new_token,
    normalize_email,
    normalize_phone,
    normalize_usn,
    now_iso,
    now_utc,
    public_user,
    request_ip,
    safe_url,
    token_hash,
    validate_password,
)
from backend.notification_service import create_notification
from backend.phase1 import (
    build_router as build_phase1_router,
    consolidated_results,
    public_meta,
    setup_phase1,
)


client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = client[os.environ["DB_NAME"]]
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, debug=False)
api = APIRouter(prefix="/api")
logger = logging.getLogger("sankalp")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

JWT_ALGORITHM = "HS256"
ACCESS_MINUTES = 15
REFRESH_DAYS = 7
TRACKS = [
    {"topic_id": "drone", "short": "Defence AI", "title": "AI-Enabled Drone & Counter-Drone Threat Simulation Trainer",
     "description": "Explore AI-driven simulation and training systems designed to study drone-related threats and improve threat-response preparedness."},
    {"topic_id": "food", "short": "Sustainability", "title": "AI-Powered Smart Food Waste Reduction & Sustainable Redistribution Ecosystem",
     "description": "Develop intelligent solutions for institutional kitchens and food processing units to reduce food waste and support sustainable redistribution."},
    {"topic_id": "v2v", "short": "Mobility", "title": "V2V Visionaries: Collision Avoidance & Road Safety",
     "description": "Reimagine safer roads through vehicle-to-vehicle communication, intelligent sensing, and next-generation collision avoidance solutions."},
    {"topic_id": "stethoscope", "short": "HealthTech", "title": "Edge-AI Smart Stethoscope for Cardiopulmonary Screening",
     "description": "Explore smart, edge-enabled stethoscope systems that support preliminary cardiopulmonary screening in rural Primary Health Centres."},
    {"topic_id": "sanitation", "short": "Sanitation", "title": "On-Site Containment-Based Toilets",
     "description": "Technological, biochemical, or nature-based approaches for treating excreta on-site while protecting the environment and groundwater."},
    {"topic_id": "water", "short": "Smart Infra", "title": "Indigenous Water Pipeline Leak Detection Sensors",
     "description": "Develop indigenous sensor-based systems for detecting pipeline leaks and improving water-supply operation and maintenance."},
]


PyObjectId = Annotated[str, BeforeValidator(lambda value: str(value) if isinstance(value, ObjectId) else value)]


class BaseDocument(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    id: Optional[PyObjectId] = Field(default=None, alias="_id")

    @classmethod
    def from_mongo(cls, doc):
        return cls.model_validate(doc) if doc else None


class User(BaseDocument):
    email: str
    name: str
    role: Literal["team", "member", "judge", "admin"] = "team"
    team_id: Optional[str] = None
    password_hash: Optional[str] = None
    is_active: bool = True
    email_verified: bool = True
    must_change_password: bool = False
    session_version: int = 0
    team_name: Optional[str] = None
    college: Optional[str] = None
    phone: Optional[str] = None
    usn: Optional[str] = None
    track: Optional[str] = None
    abstract: Optional[dict] = None
    members: List[dict] = []
    created_at: str = Field(default_factory=now_iso)

    def public(self):
        return public_user(self.model_dump())


class MemberIn(BaseModel):
    name: str = Field(default="", max_length=100)
    usn: str = Field(default="", max_length=20)
    email: str = Field(default="", max_length=254)
    college: str = Field(default="", max_length=180)
    phone: str = Field(default="", max_length=32)

    @model_validator(mode="after")
    def complete_member(self):
        self.name = self.name.strip()
        self.usn = self.usn.strip()
        self.email = self.email.strip()
        self.college = self.college.strip()
        self.phone = self.phone.strip()
        values = [self.name, self.usn, self.email, self.college, self.phone]
        if any(values) and not all(values[:3]):
            raise ValueError("Each member needs a full name, USN and email")
        if any(values):
            self.usn = normalize_usn(self.usn)
            try:
                self.email = normalize_email(validate_email(self.email, check_deliverability=False).normalized)
            except EmailNotValidError:
                raise ValueError("Enter a valid member email")
            try:
                self.phone = normalize_phone(self.phone)
            except ValueError as exc:
                raise ValueError("Each member needs a valid phone number") from exc
        return self


class RegisterIn(BaseModel):
    email: EmailStr
    password: str
    name: str = Field(min_length=2, max_length=100)
    usn: str
    team_name: str = Field(min_length=2, max_length=100)
    college: str = Field(min_length=2, max_length=180)
    phone: str
    topic_id: str
    members: List[MemberIn] = Field(default_factory=list, max_length=2)

    @field_validator("password")
    @classmethod
    def password_policy(cls, value):
        return validate_password(value)

    @field_validator("usn")
    @classmethod
    def usn_policy(cls, value):
        return normalize_usn(value)

    @field_validator("phone")
    @classmethod
    def phone_policy(cls, value):
        return normalize_phone(value)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class ActivationIn(BaseModel):
    token: str = Field(min_length=20, max_length=200)
    password: Optional[str] = None


class TokenIn(BaseModel):
    token: str = Field(min_length=20, max_length=200)


class ForgotIn(BaseModel):
    email: EmailStr


class ResetIn(BaseModel):
    token: str = Field(min_length=20, max_length=200)
    password: str

    @field_validator("password")
    @classmethod
    def reset_policy(cls, value):
        return validate_password(value)


class ChangePasswordIn(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str

    @field_validator("new_password")
    @classmethod
    def new_policy(cls, value):
        return validate_password(value)


class SettingsIn(BaseModel):
    phase: Optional[Literal["registration", "hackathon", "evaluation", "results"]] = None
    leaderboard_public: Optional[bool] = None


DUMMY_HASH = bcrypt.hashpw(b"invalid-password", bcrypt.gensalt(rounds=4)).decode()


async def hash_password(password: str) -> str:
    return (await asyncio.to_thread(bcrypt.hashpw, password.encode(), bcrypt.gensalt(rounds=12))).decode()


async def verify_password(password: str, hashed: Optional[str]) -> bool:
    if len(password.encode("utf-8")) > 72:
        return False
    try:
        return await asyncio.to_thread(bcrypt.checkpw, password.encode(), (hashed or DUMMY_HASH).encode()) if hashed else False
    except ValueError:
        return False


def make_token(user: User, kind: str, sid: str, expires: timedelta) -> str:
    now = now_utc()
    return jwt.encode({"sub": user.id, "type": kind, "sid": sid, "sv": user.session_version,
                       "iat": now, "exp": now + expires, "jti": secrets.token_hex(12)},
                      os.environ["JWT_SECRET"], algorithm=JWT_ALGORITHM)


def set_session_cookies(response: Response, access: str, refresh: str, csrf: str, request: Request):
    forwarded_proto = request.headers.get("x-forwarded-proto", "").split(",")[0].strip()
    secure = app_environment() == "production" or (forwarded_proto or request.url.scheme) == "https"
    response.set_cookie("access_token", access, httponly=True, secure=secure, samesite="lax", max_age=ACCESS_MINUTES * 60, path="/")
    response.set_cookie("refresh_token", refresh, httponly=True, secure=secure, samesite="lax", max_age=REFRESH_DAYS * 86400, path="/api/auth")
    response.set_cookie("csrf_token", csrf, httponly=False, secure=secure, samesite="lax", max_age=REFRESH_DAYS * 86400, path="/")


async def issue_session(response: Response, user: User, request: Request):
    sid = secrets.token_urlsafe(24)
    csrf = secrets.token_urlsafe(24)
    access = make_token(user, "access", sid, timedelta(minutes=ACCESS_MINUTES))
    refresh = make_token(user, "refresh", sid, timedelta(days=REFRESH_DAYS))
    await db.sessions.insert_one({"sid": sid, "user_id": user.id, "refresh_hash": token_hash(refresh),
                                  "created_at": now_iso(), "last_seen_at": now_iso(), "ip": request_ip(request),
                                  "expires_at": now_utc() + timedelta(days=REFRESH_DAYS), "revoked_at": None})
    set_session_cookies(response, access, refresh, csrf, request)
    return access, csrf


def decode_token(token: str, expected: str):
    try:
        payload = jwt.decode(token, os.environ["JWT_SECRET"], algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Session expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid session")
    if payload.get("type") != expected or not payload.get("sid") or not ObjectId.is_valid(payload.get("sub", "")):
        raise HTTPException(401, "Invalid session")
    return payload


async def current_user(request: Request) -> User:
    token = request.cookies.get("access_token")
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
    if not token:
        raise HTTPException(401, "Not authenticated")
    payload = decode_token(token, "access")
    user = User.from_mongo(await db.users.find_one({"_id": ObjectId(payload["sub"])}))
    if not user or not user.is_active or payload.get("sv", 0) != user.session_version:
        raise HTTPException(401, "Session is no longer active")
    session = await db.sessions.find_one({"sid": payload["sid"], "user_id": user.id, "revoked_at": None})
    if not session:
        raise HTTPException(401, "Session is no longer active")
    return user


def require(*roles):
    async def dependency(user: User = Depends(current_user)):
        if user.role not in roles:
            raise HTTPException(403, "Forbidden")
        return user
    return dependency


async def create_invitation(target, purpose: str, team_id: Optional[str], base_url: str, hours: int):
    target_id = target.id if isinstance(target, User) else target["id"]
    token, hashed = new_token()
    invitation_id = new_public_id("INV")
    expires_at = now_utc() + timedelta(hours=hours)
    await db.invitations.insert_one({"invitation_id": invitation_id, "token_hash": hashed, "purpose": purpose,
                                     "target_user_id": target_id, "team_id": team_id, "expires_at": expires_at,
                                     "used_at": None, "revoked_at": None, "created_at": now_iso()})
    if team_id and purpose == "member_activation":
        await db.team_memberships.update_one({"team_id": team_id, "user_id": target_id}, {"$set": {
            "invitation_id": invitation_id, "invitation_expires_at": expires_at, "status": "invited"}})
    user_doc = await db.users.find_one({"_id": ObjectId(target_id)}, {"_id": 0, "name": 1, "email": 1})
    if purpose == "verify_email":
        url = f"{base_url}/activate?token={token}"
        content = emailer.verification_email(user_doc["name"], url)
    elif purpose == "judge_activation":
        url = f"{base_url}/activate?token={token}"
        content = emailer.judge_invitation_email(user_doc["name"], url)
    else:
        team = await db.teams.find_one({"team_id": team_id}, {"_id": 0, "name": 1})
        url = f"{base_url}/activate?token={token}"
        content = emailer.invitation_email(user_doc["name"], team["name"], url, hours)
    notice = await create_notification(db, user_id=target_id, kind=purpose, title=content[0],
                                       message="Use the private, single-use activation link sent to your email.",
                                       emailer=emailer, email_content=content, action_path="/activate")
    email_status = notice["email_status"]
    await db.invitations.update_one({"invitation_id": invitation_id}, {"$set": {
        "email_status": email_status, "email_updated_at": now_iso()}})
    if team_id and purpose == "member_activation":
        await db.team_memberships.update_one({"team_id": team_id, "user_id": target_id}, {"$set": {
            "invitation_email_status": email_status, "invitation_email_updated_at": now_iso()}})
    return {"invitation_id": invitation_id, "email_status": email_status}


@app.middleware("http")
async def security_middleware(request: Request, call_next):
    unsafe = request.method in {"POST", "PUT", "PATCH", "DELETE"} and request.url.path.startswith("/api/")
    bearer = request.headers.get("Authorization", "").startswith("Bearer ")
    cookie_session = request.cookies.get("access_token") or request.cookies.get("refresh_token")
    exempt = request.url.path.startswith(("/api/auth/login", "/api/auth/register", "/api/auth/activate",
                                          "/api/auth/invitations/inspect", "/api/auth/forgot-password", "/api/auth/reset-password",
                                          "/api/auth/resend-activation"))
    if unsafe and cookie_session and not bearer and not exempt:
        if not secrets.compare_digest(request.cookies.get("csrf_token", ""), request.headers.get("X-CSRF-Token", "")):
            response = Response(content='{"detail":"CSRF validation failed"}', status_code=403, media_type="application/json")
            csrf = request.cookies.get("csrf_token")
            if csrf:
                response.headers["X-CSRF-Token"] = csrf
            return response
    response = await call_next(request)
    csrf = request.cookies.get("csrf_token")
    if csrf:
        response.headers["X-CSRF-Token"] = csrf
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    # Allow localhost connections in development; all HTTPS/WSS in production
    is_local = request.url.hostname in ("localhost", "127.0.0.1") or (request.headers.get("host", "").split(":")[0] in ("localhost", "127.0.0.1"))
    connect_extra = " http://localhost:* ws://localhost:* http://127.0.0.1:* ws://127.0.0.1:*" if is_local else ""
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; img-src 'self' blob: data: https://static.prod-images.emergentagent.com https://images.unsplash.com; "
        "frame-src https://www.youtube.com https://youtube.com; "
        f"connect-src 'self' https: wss:{connect_extra}; object-src 'none'; "
        "base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
    )
    if request.headers.get("x-forwarded-proto") == "https" or request.url.scheme == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@api.post("/auth/register", status_code=201)
async def register(body: RegisterIn, request: Request, response: Response):
    await enforce_rate_limit(db, f"register:{request_ip(request)}", 30, 3600)
    meta = await public_meta(db)
    if not meta["portals"]["application"]:
        raise HTTPException(400, "Registrations are closed")
    topic = await db.topics.find_one({"topic_id": body.topic_id, "enabled": True}, {"_id": 0})
    if not topic:
        raise HTTPException(400, "Choose an available challenge topic")
    email = normalize_email(str(body.email))
    member_rows = [member for member in body.members if member.name]
    member_frontend_url = frontend_url(request) if member_rows else None
    all_emails = [email] + [member.email for member in member_rows]
    all_usns = [body.usn] + [member.usn for member in member_rows]
    if len(set(all_emails)) != len(all_emails) or len(set(all_usns)) != len(all_usns):
        raise HTTPException(400, "Team emails and USNs must be unique")
    if await db.users.find_one({"email": {"$in": all_emails}}) or await db.users.find_one({"usn": {"$in": all_usns}}):
        raise HTTPException(400, "An email or USN is already registered")
    name_key = body.team_name.strip().lower()
    if await db.teams.find_one({"name_key": name_key}):
        raise HTTPException(400, "Team name is already registered")
    leader_id = ObjectId()
    team_id = str(leader_id)
    leader_doc = {"_id": leader_id, "email": email, "name": body.name.strip(), "role": "team", "team_id": team_id,
                  "password_hash": await hash_password(body.password), "is_active": True, "email_verified": True,
                  "must_change_password": False, "session_version": 0, "team_name": body.team_name.strip(),
                  "college": body.college.strip(), "phone": body.phone, "usn": body.usn, "track": topic["title"],
                  "members": [member.model_dump() for member in member_rows], "created_at": now_iso()}
    team_doc = {"_id": leader_id, "team_id": team_id, "name": body.team_name.strip(), "name_key": name_key,
                "college": body.college.strip(), "leader_id": team_id, "topic_id": topic["topic_id"], "topic_title": topic["title"],
                "registration_status": "registered", "created_at": now_iso(), "updated_at": now_iso()}
    created_user_ids = [leader_id]
    try:
        await db.users.insert_one(leader_doc)
        await db.teams.insert_one(team_doc)
        await db.team_memberships.insert_one({"membership_id": new_public_id("MEM"), "team_id": team_id, "user_id": team_id,
                                              "name": leader_doc["name"], "email": email, "usn": body.usn, "college": body.college.strip(),
                                              "phone": body.phone, "role": "leader", "status": "pending_verification", "created_at": now_iso()})
        for member in member_rows:
            member_id = ObjectId()
            created_user_ids.append(member_id)
            member_doc = {"_id": member_id, "email": member.email, "name": member.name, "role": "member", "team_id": team_id,
                          "password_hash": None, "is_active": False, "email_verified": False, "must_change_password": False,
                          "session_version": 0, "team_name": body.team_name.strip(), "college": member.college or body.college.strip(),
                          "usn": member.usn, "phone": member.phone, "track": topic["title"], "created_at": now_iso()}
            await db.users.insert_one(member_doc)
            await db.team_memberships.insert_one({"membership_id": new_public_id("MEM"), "team_id": team_id, "user_id": str(member_id),
                                                  "name": member.name, "email": member.email, "usn": member.usn,
                                                  "college": member.college or body.college.strip(), "phone": member.phone,
                                                  "role": "member", "status": "invited", "created_at": now_iso()})
    except DuplicateKeyError as exc:
        await db.users.delete_many({"_id": {"$in": created_user_ids}})
        await db.teams.delete_one({"team_id": team_id})
        await db.team_memberships.delete_many({"team_id": team_id})
        raise HTTPException(400, "A team member email, USN or team name is already registered") from exc
    except Exception:
        await db.users.delete_many({"_id": {"$in": created_user_ids}})
        await db.teams.delete_one({"team_id": team_id})
        await db.team_memberships.delete_many({"team_id": team_id})
        raise
    # Auto-activate leader membership
    await db.team_memberships.update_one({"team_id": team_id, "user_id": team_id}, {"$set": {"status": "active"}})
    # Auto-login the leader after successful registration
    leader_user = User.from_mongo(await db.users.find_one({"_id": leader_id}))
    access, csrf = await issue_session(response, leader_user, request)
    # Send welcome notification
    await create_notification(db, user_id=str(leader_id), kind="registration_success",
                              title="Registration successful",
                              message=f"Welcome to SANKALP'26! Your team '{body.team_name.strip()}' has been registered successfully.",
                              action_path="/dashboard")
    member_invitations = []
    for member in member_rows:
        target = clean_doc(await db.users.find_one({"email": member.email}))
        invitation = await create_invitation(target, "member_activation", team_id, member_frontend_url, 72)
        member_invitations.append({"email": member.email, **invitation})
    await audit(db, leader_user, "team.registered", "team", team_id, request, {"member_count": 1 + len(member_rows)})
    return {"user": leader_user.public(), "token": access, "csrf_token": csrf, "team_id": team_id,
            "verification_required": False, "member_invitations": member_invitations}


@api.post("/auth/invitations/inspect")
async def inspect_invitation(body: TokenIn):
    invitation = await db.invitations.find_one({"token_hash": token_hash(body.token), "used_at": None, "revoked_at": None,
                                                "expires_at": {"$gt": now_utc()}}, {"_id": 0, "token_hash": 0})
    if not invitation:
        raise HTTPException(400, "This link is invalid or expired")
    user = await db.users.find_one({"_id": ObjectId(invitation["target_user_id"])}, {"_id": 0, "name": 1, "email": 1})
    return {"purpose": invitation["purpose"], "name": user["name"], "email_hint": user["email"][:2] + "***@" + user["email"].split("@")[-1]}


@api.post("/auth/activate")
async def activate(body: ActivationIn, request: Request, response: Response):
    await enforce_rate_limit(db, f"activate-ip:{request_ip(request)}", 100, 3600)
    await enforce_rate_limit(db, f"activate-token:{token_hash(body.token)}", 5, 3600)
    invitation = await db.invitations.find_one({"token_hash": token_hash(body.token), "used_at": None, "revoked_at": None,
                                                "expires_at": {"$gt": now_utc()}})
    if not invitation:
        raise HTTPException(400, "This link is invalid or expired")
    user = User.from_mongo(await db.users.find_one({"_id": ObjectId(invitation["target_user_id"])}))
    if not user or (user.is_active and user.password_hash):
        raise HTTPException(400, "This account is already active or unavailable")
    if invitation.get("team_id"):
        team = await db.teams.find_one({"team_id": invitation["team_id"]}, {"_id": 0, "registration_review_status": 1})
        if team and team.get("registration_review_status") == "not_confirmed":
            raise HTTPException(400, "This account is inactive because the team registration is not confirmed")
    updates = {"is_active": True, "email_verified": True, "activated_at": now_iso()}
    if invitation["purpose"] in ("member_activation", "judge_activation"):
        if not body.password:
            raise HTTPException(422, "Create a password to activate this account")
        try:
            validate_password(body.password)
        except ValueError as exc:
            raise HTTPException(422, str(exc))
        updates["password_hash"] = await hash_password(body.password)
    if invitation["purpose"] == "judge_activation":
        if user.role != "judge":
            raise HTTPException(400, "This invitation is invalid or expired")
        updates["activation_status"] = "active"
    claimed = await db.invitations.find_one_and_update(
        {"_id": invitation["_id"], "used_at": None, "revoked_at": None, "expires_at": {"$gt": now_utc()}},
        {"$set": {"used_at": now_iso()}},
    )
    if not claimed:
        raise HTTPException(400, "This link is invalid or expired")
    await db.users.update_one({"_id": ObjectId(user.id)}, {"$set": updates})
    if invitation.get("team_id"):
        team = await db.teams.find_one({"team_id": invitation["team_id"]}, {"_id": 0, "registration_review_status": 1})
        if team and team.get("registration_review_status") == "not_confirmed":
            await db.users.update_one({"_id": ObjectId(user.id)}, {"$set": {"is_active": False}})
            raise HTTPException(400, "This account is inactive because the team registration is not confirmed")
    if invitation.get("team_id"):
        await db.team_memberships.update_one({"team_id": invitation["team_id"], "user_id": user.id}, {"$set": {
            "status": "active", "activated_at": now_iso(), "invitation_accepted_at": now_iso()}})
        if invitation["purpose"] == "verify_email":
            await db.teams.update_one({"team_id": invitation["team_id"]}, {"$set": {"registration_status": "registered", "updated_at": now_iso()}})
    user = User.from_mongo(await db.users.find_one({"_id": ObjectId(user.id)}))
    access, csrf = await issue_session(response, user, request)
    await audit(db, user, "account.activated", "user", user.id, request)
    return {"user": user.public(), "token": access, "csrf_token": csrf}


@api.post("/auth/login")
async def login(body: LoginIn, request: Request, response: Response):
    email = normalize_email(str(body.email))
    await enforce_rate_limit(db, f"login-ip:{request_ip(request)}", 100, 900)
    identifier = email
    user = User.from_mongo(await db.users.find_one({"email": email}))
    if not user or not await verify_password(body.password, user.password_hash):
        await enforce_rate_limit(db, f"login-fail:{hashlib.sha256(identifier.encode()).hexdigest()}", 5, 900)
        await audit(db, None, "auth.login_failed", "account", hashlib.sha256(email.encode()).hexdigest()[:12], request)
        raise HTTPException(401, "Invalid email or password")
    # Auto-activate accounts that were registered before email-verification was removed
    if not user.is_active and user.role in ("team",):
        team = await db.teams.find_one({"team_id": user.team_id}, {"_id": 0, "registration_review_status": 1})
        if not team or team.get("registration_review_status") != "not_confirmed":
            await db.users.update_one({"_id": ObjectId(user.id)}, {"$set": {"is_active": True, "email_verified": True}})
            await db.teams.update_one({"team_id": user.team_id}, {"$set": {"registration_status": "registered", "updated_at": now_iso()}})
            await db.team_memberships.update_one({"team_id": user.team_id, "user_id": user.id}, {"$set": {"status": "active"}})
            user = User.from_mongo(await db.users.find_one({"_id": ObjectId(user.id)}))
    if not user.is_active:
        raise HTTPException(403, "Account is not active. Please contact the administrator.")
    await db.rate_limits.delete_many({"key": f"login-fail:{hashlib.sha256(identifier.encode()).hexdigest()}"})
    access, csrf = await issue_session(response, user, request)
    await audit(db, user, "auth.login", "user", user.id, request)
    return {"user": user.public(), "token": access, "csrf_token": csrf}


@api.post("/auth/logout")
async def logout(request: Request, response: Response):
    token = request.cookies.get("access_token")
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
    revoked = False
    if token:
        try:
            payload = decode_token(token, "access")
            await db.sessions.update_one({"sid": payload["sid"]}, {"$set": {"revoked_at": now_iso()}})
            revoked = True
        except HTTPException:
            pass
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token and not revoked:
        try:
            payload = decode_token(refresh_token, "refresh")
            await db.sessions.update_one({"sid": payload["sid"]}, {"$set": {"revoked_at": now_iso()}})
        except HTTPException:
            pass
    forwarded_proto = request.headers.get("x-forwarded-proto", "").split(",")[0].strip()
    secure = app_environment() == "production" or (forwarded_proto or request.url.scheme) == "https"
    for key, path in (("access_token", "/"), ("refresh_token", "/api/auth"), ("csrf_token", "/")):
        response.delete_cookie(key, path=path, secure=secure, samesite="lax")
    return {"ok": True}


@api.get("/auth/me")
async def me(user: User = Depends(current_user)):
    return user.public()


@api.post("/auth/refresh")
async def refresh(request: Request, response: Response):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(401, "No refresh session")
    payload = decode_token(token, "refresh")
    session = await db.sessions.find_one({"sid": payload["sid"], "user_id": payload["sub"], "revoked_at": None})
    user = User.from_mongo(await db.users.find_one({"_id": ObjectId(payload["sub"])}))
    if not session or not user or not user.is_active or payload.get("sv", 0) != user.session_version or not secrets.compare_digest(session["refresh_hash"], token_hash(token)):
        raise HTTPException(401, "Refresh session is no longer active")
    new_refresh = make_token(user, "refresh", payload["sid"], timedelta(days=REFRESH_DAYS))
    access = make_token(user, "access", payload["sid"], timedelta(minutes=ACCESS_MINUTES))
    csrf = secrets.token_urlsafe(24)
    await db.sessions.update_one({"sid": payload["sid"]}, {"$set": {"refresh_hash": token_hash(new_refresh), "last_seen_at": now_iso(),
                                                                 "expires_at": now_utc() + timedelta(days=REFRESH_DAYS)}})
    set_session_cookies(response, access, new_refresh, csrf, request)
    return {"token": access, "csrf_token": csrf}


@api.post("/auth/change-password")
async def change_password(body: ChangePasswordIn, request: Request, response: Response, user: User = Depends(current_user)):
    await enforce_rate_limit(db, f"password-change:{user.id}", 5, 3600)
    if not await verify_password(body.current_password, user.password_hash):
        raise HTTPException(400, "Current password is incorrect")
    if await verify_password(body.new_password, user.password_hash):
        raise HTTPException(400, "Choose a different password")
    new_version = user.session_version + 1
    await db.users.update_one({"_id": ObjectId(user.id)}, {"$set": {"password_hash": await hash_password(body.new_password),
                                                                      "must_change_password": False, "session_version": new_version,
                                                                      "password_changed_at": now_iso()}})
    await db.sessions.update_many({"user_id": user.id, "revoked_at": None}, {"$set": {"revoked_at": now_iso()}})
    updated = User.from_mongo(await db.users.find_one({"_id": ObjectId(user.id)}))
    access, csrf = await issue_session(response, updated, request)
    await audit(db, updated, "auth.password_changed", "user", user.id, request)
    return {"user": updated.public(), "token": access, "csrf_token": csrf}


@api.post("/auth/forgot-password")
async def forgot_password(body: ForgotIn, request: Request):
    await enforce_rate_limit(db, f"forgot:{request_ip(request)}", 5, 3600)
    reset_frontend_url = frontend_url(request)

    email = normalize_email(str(body.email))
    user = await db.users.find_one({"email": email, "is_active": True})
    if user:
        token, hashed = new_token()
        await db.password_reset_tokens.update_many({"user_id": str(user["_id"]), "used_at": None}, {"$set": {"used_at": now_iso()}})
        await db.password_reset_tokens.insert_one({"token_hash": hashed, "user_id": str(user["_id"]),
                                                   "expires_at": now_utc() + timedelta(hours=1), "used_at": None, "created_at": now_iso()})
        content = emailer.password_reset_email(
            user["name"],
            f"{reset_frontend_url}/reset-password?token={token}",
        )
        await create_notification(db, user_id=str(user["_id"]), kind="password_reset", title="Password reset requested",
                                  message="A one-hour password reset link was requested.", emailer=emailer, email_content=content)
    return {"ok": True, "message": "If an active account matches, a reset link will be sent."}


@api.post("/auth/resend-activation")
async def resend_activation(body: ForgotIn, request: Request):
    await enforce_rate_limit(db, f"activation-resend:{request_ip(request)}", 5, 3600)
    user = User.from_mongo(await db.users.find_one({
        "email": normalize_email(str(body.email)),
        "$or": [
            {"is_active": False},
            {"role": "member", "is_active": True, "password_hash": None},
        ],
    }))
    if user:
        team = await db.teams.find_one({"team_id": user.team_id}, {"_id": 0, "registration_review_status": 1}) if user.team_id else None
        if not team or team.get("registration_review_status") != "not_confirmed":
            purpose = "judge_activation" if user.role == "judge" else "member_activation" if user.role == "member" else "verify_email"
            await db.invitations.update_many({"target_user_id": user.id, "used_at": None}, {"$set": {"revoked_at": now_iso()}})
            base_url = frontend_url(request) if purpose in ("judge_activation", "member_activation") else app_url(request)
            await create_invitation(user, purpose, user.team_id, base_url, 72 if purpose != "verify_email" else 24)
    return {"ok": True, "message": "If an account needs activation, a fresh activation link was attempted."}


@api.post("/auth/reset-password")
async def reset_password(body: ResetIn, request: Request):
    await enforce_rate_limit(db, f"reset:{request_ip(request)}", 8, 3600)
    record = await db.password_reset_tokens.find_one_and_update(
        {"token_hash": token_hash(body.token), "used_at": None, "expires_at": {"$gt": now_utc()}},
        {"$set": {"used_at": now_iso()}},
    )
    if not record:
        raise HTTPException(400, "This reset link is invalid or expired")
    user = User.from_mongo(await db.users.find_one({"_id": ObjectId(record["user_id"])}))
    if not user:
        raise HTTPException(400, "This reset link is invalid or expired")
    await db.users.update_one({"_id": ObjectId(user.id)}, {"$set": {"password_hash": await hash_password(body.password),
                                                                      "session_version": user.session_version + 1,
                                                                      "must_change_password": False, "password_changed_at": now_iso()}})
    await db.sessions.update_many({"user_id": user.id, "revoked_at": None}, {"$set": {"revoked_at": now_iso()}})
    await audit(db, user, "auth.password_reset", "user", user.id, request)
    return {"ok": True}


@api.get("/")
async def root():
    return {"message": "SANKALP'26 API online"}


@api.get("/leaderboard")
async def leaderboard(request: Request):
    settings = await db.settings.find_one({"key": "global"}, {"_id": 0}) or {}
    if not settings.get("leaderboard_public") and settings.get("phase") != "results":
        try:
            user = await current_user(request)
        except HTTPException:
            user = None
        if not user or user.role in ("team", "member"):
            return {"hidden": True, "configured": False, "rows": []}
    result = await consolidated_results(db)
    return {"hidden": False, **result, "phase": settings.get("phase", "registration")}


@api.put("/admin/settings")
async def admin_settings(body: SettingsIn, request: Request, user: User = Depends(require("admin"))):
    patch = {key: value for key, value in body.model_dump().items() if value is not None}
    await db.settings.update_one({"key": "global"}, {"$set": {"key": "global", **patch, "updated_at": now_iso()}}, upsert=True)
    await audit(db, user, "settings.updated", "settings", "global", request, patch)
    return await db.settings.find_one({"key": "global"}, {"_id": 0})


api.include_router(build_phase1_router(db, current_user, require, hash_password, create_invitation))
api.include_router(build_arena_router(db, current_user, require))
app.include_router(api)

cors_origins = [item.strip() for item in os.environ["CORS_ORIGINS"].split(",") if item.strip() and item.strip() != "*"]
app.add_middleware(CORSMiddleware, allow_credentials=True, allow_origins=cors_origins,
                   allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
                   allow_headers=["Authorization", "Content-Type", "X-CSRF-Token"],
                   expose_headers=["Retry-After", "X-CSRF-Token"])


async def seed_user(email, password, name, role):
    email = email.lower()
    existing = await db.users.find_one({"email": email})
    if not existing:
        await db.users.insert_one(User(email=email, name=name, role=role, password_hash=await hash_password(password),
                                       must_change_password=False, is_active=True, email_verified=True).model_dump(by_alias=True, exclude_none=True))
        return

    password_matches = existing.get("password_hash") and await verify_password(password, existing.get("password_hash"))
    if not password_matches:
        await db.users.update_one({"_id": existing["_id"]}, {"$set": {
            "password_hash": await hash_password(password),
            "must_change_password": False,
            "is_active": True,
            "email_verified": True,
            "session_version": existing.get("session_version", 0),
            "role": role,
            "name": name,
        }})
        return

    updates = {
        "must_change_password": False,
        "is_active": True,
        "email_verified": True,
        "session_version": existing.get("session_version", 0),
        "role": role,
        "name": name,
    }
    await db.users.update_one({"_id": existing["_id"]}, {"$set": updates})


@app.on_event("startup")
async def startup():
    await seed_user(os.environ["ADMIN_EMAIL"], os.environ["ADMIN_PASSWORD"], "Sankalp Admin", "admin")
    await seed_user(os.environ["JUDGE_EMAIL"], os.environ["JUDGE_PASSWORD"], "Demo Judge", "judge")
    await setup_phase1(db, TRACKS)
    await cleanup_pending_private_files(db)
    await db.login_attempts.create_index("identifier")
    await setup_arena(db)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()