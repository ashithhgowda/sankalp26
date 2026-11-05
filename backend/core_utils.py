import hashlib
import ipaddress
import logging
import os
import re
import secrets
import uuid
import zipfile
from datetime import datetime, timezone, timedelta
from io import BytesIO
from typing import Optional
from urllib.parse import urlparse

from bson import ObjectId
from fastapi import HTTPException, Request, UploadFile
from gridfs.errors import NoFile
from motor.motor_asyncio import AsyncIOMotorGridFSBucket


IST_OFFSET = timedelta(hours=5, minutes=30)
TEAM_ROLES = ("team", "member")
PASSWORD_MESSAGE = "Use at least 12 characters with upper, lower, number and symbol"
logger = logging.getLogger(__name__)


def now_utc():
    return datetime.now(timezone.utc)


def now_iso():
    return now_utc().isoformat()


def token_hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def new_public_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10].upper()}"


def valid_oid(value: str) -> ObjectId:
    if not ObjectId.is_valid(value):
        raise HTTPException(404, "Record not found")
    return ObjectId(value)


def clean_doc(doc):
    if doc is None:
        return None
    out = {}
    for key, value in doc.items():
        if key == "_id":
            out["id"] = str(value)
        elif isinstance(value, ObjectId):
            out[key] = str(value)
        elif isinstance(value, datetime):
            out[key] = value.astimezone(timezone.utc).isoformat()
        elif isinstance(value, dict):
            out[key] = clean_doc(value)
        elif isinstance(value, list):
            out[key] = [clean_doc(x) if isinstance(x, dict) else str(x) if isinstance(x, ObjectId) else x for x in value]
        else:
            out[key] = value
    return out


def public_user(doc):
    data = clean_doc(doc)
    for key in ("password_hash", "session_version", "seeded_account"):
        data.pop(key, None)
    return data


def normalize_email(value: str) -> str:
    return value.strip().lower()


def normalize_usn(value: str) -> str:
    value = value.strip().upper()
    if not re.fullmatch(r"[A-Z0-9][A-Z0-9/-]{2,19}", value):
        raise ValueError("Enter a valid USN (3–20 letters, numbers, / or -)")
    return value


def normalize_phone(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    if not re.fullmatch(r"[6-9]\d{9}", digits):
        raise ValueError("Enter a valid 10-digit Indian mobile number")
    return digits


def validate_password(value: str) -> str:
    if (len(value) < 12 or len(value.encode("utf-8")) > 72 or not re.search(r"[A-Z]", value)
            or not re.search(r"[a-z]", value) or not re.search(r"\d", value)
            or not re.search(r"[^A-Za-z0-9]", value)):
        raise ValueError(PASSWORD_MESSAGE + " and no more than 72 UTF-8 bytes")
    return value


def safe_url(value: str, *, optional=False) -> str:
    value = value.strip()
    if optional and not value:
        return ""
    try:
        parsed = urlparse(value)
        if parsed.scheme not in ("https", "http") or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError
        try:
            ip = ipaddress.ip_address(parsed.hostname)
        except ValueError:
            ip = None
        if ip and (ip.is_private or ip.is_loopback or ip.is_link_local):
            raise ValueError
        return value
    except Exception:
        raise ValueError("Enter a valid http or https URL")


def request_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    return forwarded or (request.client.host if request.client else "unknown")


def app_url(request: Request) -> str:
    proto = request.headers.get("x-forwarded-proto") or request.url.scheme
    host = request.headers.get("x-forwarded-host") or request.headers.get("host")
    if not host:
        raise HTTPException(500, "Application URL is unavailable")
    if proto != "https" and not host.startswith(("localhost", "127.0.0.1")):
        proto = "https"
    return f"{proto}://{host}".rstrip("/")


def app_environment() -> str:
    value = os.environ.get("APP_ENV", "development").strip().lower()
    if value not in ("development", "production"):
        raise HTTPException(500, "APP_ENV must be 'development' or 'production'")
    return value


def frontend_url(request: Request) -> str:
    value = os.environ.get("FRONTEND_URL", "").strip().rstrip("/")
    if not value:
        origin = request.headers.get("origin", "").rstrip("/")
        allowed_origins = {item.strip().rstrip("/") for item in os.environ.get("CORS_ORIGINS", "").split(",") if item.strip()}
        if origin and origin in allowed_origins:
            value = origin
        elif request.url.hostname in ("localhost", "127.0.0.1", "testserver"):
            value = app_url(request)
        else:
            raise HTTPException(500, "Frontend URL is not configured")
    parsed = urlparse(value)
    if (parsed.scheme not in ("https", "http") or not parsed.hostname or parsed.username or parsed.password
            or parsed.query or parsed.fragment):
        raise HTTPException(500, "Frontend URL configuration is invalid")
    try:
        parsed.port
    except ValueError as exc:
        raise HTTPException(500, "Frontend URL configuration has an invalid port") from exc
    if parsed.hostname.lower().endswith((".example", ".example.com")) or "your-" in parsed.hostname.lower():
        raise HTTPException(500, "Frontend URL is not configured")
    local_http = app_environment() == "development" and parsed.scheme == "http" and parsed.hostname.lower() in ("localhost", "127.0.0.1")
    if parsed.scheme != "https" and not local_http:
        raise HTTPException(500, "Email links must use HTTPS; development HTTP is limited to localhost and 127.0.0.1")
    return value


async def enforce_rate_limit(db, key: str, limit: int, window_seconds: int):
    timestamp = int(now_utc().timestamp())
    bucket = timestamp // window_seconds
    expires = now_utc() + timedelta(seconds=window_seconds * 2)
    result = await db.rate_limits.find_one_and_update(
        {"key": key, "bucket": bucket},
        {"$inc": {"count": 1}, "$setOnInsert": {"expires_at": expires}},
        upsert=True,
        return_document=True,
    )
    if result and result.get("count", 0) > limit:
        retry_after = window_seconds - (timestamp % window_seconds)
        raise HTTPException(429, "Too many requests. Please wait and try again.",
                            headers={"Retry-After": str(retry_after)})


async def audit(db, actor, action: str, target_type: str, target_id: str, request: Request = None, details=None):
    await db.audit_logs.insert_one({
        "audit_id": new_public_id("AUD"),
        "actor_id": getattr(actor, "id", None) if actor else None,
        "actor_email": getattr(actor, "email", None) if actor else None,
        "actor_role": getattr(actor, "role", "system") if actor else "system",
        "action": action,
        "target_type": target_type,
        "target_id": str(target_id),
        "details": details or {},
        "ip": request_ip(request) if request else None,
        "created_at": now_iso(),
    })


def sniff_file(data: bytes, filename: str, allowed: set[str]):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    detected = None
    if data.startswith(b"%PDF-"):
        detected = ("pdf", "application/pdf")
    elif data.startswith(b"\x89PNG\r\n\x1a\n"):
        detected = ("png", "image/png")
    elif data.startswith(b"\xff\xd8\xff"):
        detected = ("jpg", "image/jpeg")
    elif data.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
        detected = ("doc", "application/msword")
    elif data.startswith(b"PK\x03\x04"):
        try:
            with zipfile.ZipFile(BytesIO(data)) as zf:
                names = set(zf.namelist())
            if "[Content_Types].xml" in names and any(n.startswith("word/") for n in names):
                detected = ("docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        except zipfile.BadZipFile:
            detected = None
    if not detected or detected[0] not in allowed:
        raise HTTPException(400, "The file content does not match an allowed file type")
    if ext == "jpeg" and detected[0] == "jpg":
        return "jpg", detected[1]
    if ext != detected[0]:
        raise HTTPException(400, "The file extension does not match its content")
    return detected


async def read_upload(file: UploadFile, max_bytes: int, allowed: set[str]):
    filename = (file.filename or "upload").strip()[:180]
    data = await file.read(max_bytes + 1)
    if not data:
        raise HTTPException(400, "File is empty")
    if len(data) > max_bytes:
        raise HTTPException(400, f"File exceeds the {max_bytes // (1024 * 1024)} MB limit")
    ext, content_type = sniff_file(data, filename, allowed)
    return filename, data, ext, content_type


async def store_private_file(db, *, file: UploadFile, owner_id: str, team_id: str,
                             kind: str, max_bytes: int, allowed: set[str], topic: Optional[dict] = None):
    filename, data, ext, content_type = await read_upload(file, max_bytes, allowed)
    file_id = str(uuid.uuid4())
    uploaded_at = now_iso()
    metadata = {
        "owner_id": owner_id,
        "team_id": team_id,
        "kind": kind,
        "filename": filename,
        "size": len(data),
        "content_type": content_type,
        "uploaded_at": uploaded_at,
    }
    if topic:
        metadata.update({"topic_id": topic["topic_id"], "topic_title": topic["title"]})
    gridfs = AsyncIOMotorGridFSBucket(db)
    try:
        gridfs_id = await gridfs.upload_from_stream(
            filename, BytesIO(data), metadata=metadata.copy()
        )
        record = {
            "file_id": file_id,
            "gridfs_id": str(gridfs_id),
            **metadata,
            "is_deleted": False,
        }
        await db.files.insert_one(record.copy())
    except Exception as exc:
        if "gridfs_id" in locals():
            try:
                await gridfs.delete(gridfs_id)
            except NoFile:
                pass
            except Exception:
                logger.exception("Failed to clean up incomplete private file upload")
        logger.exception("Private file upload failed")
        raise HTTPException(503, "Private file storage is temporarily unavailable") from exc
    return {k: v for k, v in record.items() if k not in ("owner_id", "team_id", "kind", "is_deleted")}


async def delete_private_file(db, file_id: str):
    record = await db.files.find_one({"file_id": file_id}, {"_id": 0, "gridfs_id": 1})
    if not record:
        return
    await db.files.update_one(
        {"file_id": file_id},
        {"$set": {"is_deleted": True, "deleted_at": now_iso(), "cleanup_pending": True}},
    )
    gridfs_id = record.get("gridfs_id")
    if gridfs_id:
        if not ObjectId.is_valid(gridfs_id):
            logger.error("Invalid GridFS ID while deleting private file %s", file_id)
            raise HTTPException(500, "Stored file metadata is invalid")
        try:
            await AsyncIOMotorGridFSBucket(db).delete(ObjectId(gridfs_id))
        except NoFile:
            pass
        except Exception as exc:
            logger.exception("Failed to delete private file from GridFS")
            raise HTTPException(503, "Private file cleanup is temporarily unavailable") from exc
    await db.files.update_one(
        {"file_id": file_id},
        {"$unset": {"cleanup_pending": ""}},
    )


async def cleanup_pending_private_files(db):
    async for record in db.files.find({"cleanup_pending": True}, {"_id": 0, "file_id": 1}):
        try:
            await delete_private_file(db, record["file_id"])
        except HTTPException as exc:
            logger.error("GridFS cleanup remains pending for file %s: %s", record["file_id"], exc.detail)


def new_token():
    value = secrets.token_urlsafe(32)
    return value, token_hash(value)