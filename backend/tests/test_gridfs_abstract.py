import os
import secrets
import uuid
from datetime import timedelta
from pathlib import Path

import pytest
from bson import ObjectId
from dotenv import load_dotenv
from fastapi import FastAPI
from gridfs import GridFSBucket
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from starlette.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


def _pdf(text):
    content = f"BT /F1 18 Tf 72 720 Td ({text}) Tj ET".encode()
    stream = b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        stream,
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    data = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for index, obj in enumerate(objects, 1):
        offsets.append(len(data))
        data.extend(f"{index} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref_offset = len(data)
    data.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    data.extend(b"0000000000 65535 f \n")
    for offset in offsets:
        data.extend(f"{offset:010} 00000 n \n".encode())
    data.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n".encode()
    )
    return bytes(data)


def _auth_for(db, server, role, team_id=None):
    user_id = ObjectId()
    sid = secrets.token_urlsafe(24)
    user = {
        "_id": user_id,
        "email": f"{role}-{user_id}@gridfs-test.invalid",
        "name": f"GridFS {role}",
        "role": role,
        "team_id": team_id,
        "is_active": True,
        "email_verified": True,
        "must_change_password": False,
        "session_version": 0,
    }
    db.users.insert_one(user)
    db.sessions.insert_one({"sid": sid, "user_id": str(user_id), "revoked_at": None})
    token = server.make_token(server.User.from_mongo(user), "access", sid, timedelta(minutes=5))
    return {"Authorization": f"Bearer {token}"}


def test_abstract_upload_gridfs_replacement_and_admin_download():
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
    from backend.emailer import EMAIL_BASE_URL, _assert_safe_email, verification_email
    from backend.phase1 import build_router

    original_db = server.db
    test_db = client[f"skgfs_{uuid.uuid4().hex}"]
    motor_db = server.client[test_db.name]
    server.db = motor_db
    try:
        team_id = str(ObjectId())
        topic_id = f"gridfs-test-{uuid.uuid4().hex}"
        test_db.teams.insert_one({"team_id": team_id, "leader_id": team_id, "name": "GridFS test"})
        test_db.topics.insert_one({
            "topic_id": topic_id,
            "title": "GridFS Abstract Topic",
            "enabled": True,
        })
        replacement_topic_id = f"gridfs-test-{uuid.uuid4().hex}"
        test_db.topics.insert_one({
            "topic_id": replacement_topic_id,
            "title": "GridFS Replacement Topic",
            "enabled": True,
        })
        test_db.settings.insert_one({"key": "timeline", "abstract_override": "open"})
        leader = _auth_for(test_db, server, "team", team_id)
        member = _auth_for(test_db, server, "member", team_id)
        judge = _auth_for(test_db, server, "judge")
        admin = _auth_for(test_db, server, "admin")

        app = FastAPI()
        app.include_router(build_router(
            motor_db, server.current_user, server.require, server.hash_password, server.create_invitation,
        ), prefix="/api")
        with TestClient(app) as http:
            assert http.post(
                "/api/applications/abstract",
                headers=member,
                data={"topic_id": topic_id},
                files={"file": ("member.pdf", _pdf("Not a leader"), "application/pdf")},
            ).status_code == 403
            assert http.post(
                "/api/applications/abstract",
                headers=leader,
                data={"topic_id": topic_id},
                files={"file": ("invalid.pdf", b"not a PDF", "application/pdf")},
            ).status_code == 400
            assert http.post(
                "/api/applications/abstract",
                headers=leader,
                data={"topic_id": topic_id},
                files={"file": ("large.pdf", b"%PDF-" + b"A" * (3 * 1024 * 1024), "application/pdf")},
            ).status_code == 400
            assert test_db.fs.files.count_documents({}) == 0

            first_pdf = _pdf("First GridFS submission")
            response = http.post(
                "/api/applications/abstract",
                headers=leader,
                data={"topic_id": topic_id},
                files={"file": ("first.pdf", first_pdf, "application/pdf")},
            )
            assert response.status_code == 200, response.text
            first_file = response.json()["file"]
            first_record = test_db.files.find_one({"file_id": first_file["file_id"]})
            first_gridfs_id = ObjectId(first_record["gridfs_id"])
            stored = test_db.fs.files.find_one({"_id": first_gridfs_id})
            assert stored["metadata"]["team_id"] == team_id
            assert stored["metadata"]["topic_id"] == topic_id
            assert stored["filename"] == "first.pdf"
            assert first_record["topic_title"] == "GridFS Abstract Topic"
            assert first_record["uploaded_at"]
            with GridFSBucket(test_db).open_download_stream(first_gridfs_id) as download:
                assert download.read() == first_pdf

            second_pdf = _pdf("Replacement GridFS submission")
            replacement = http.post(
                "/api/applications/abstract",
                headers=leader,
                data={"topic_id": replacement_topic_id},
                files={"file": ("replacement.pdf", second_pdf, "application/pdf")},
            )
            assert replacement.status_code == 200, replacement.text
            second_file = replacement.json()["file"]
            second_record = test_db.files.find_one({"file_id": second_file["file_id"]})
            second_gridfs_id = ObjectId(second_record["gridfs_id"])
            assert test_db.fs.files.find_one({"_id": first_gridfs_id}) is None
            assert test_db.fs.chunks.count_documents({"files_id": first_gridfs_id}) == 0
            assert test_db.files.find_one({"file_id": first_file["file_id"]})["is_deleted"] is True
            assert second_record["topic_id"] == replacement_topic_id
            assert test_db.fs.files.find_one({"_id": second_gridfs_id})["metadata"]["topic_id"] == replacement_topic_id

            endpoint = f"/api/files/{second_file['file_id']}"
            assert http.get(endpoint, headers=member).status_code == 403
            assert http.get(endpoint, headers=judge).status_code == 403
            assert http.get(endpoint).status_code == 401
            downloaded = http.get(endpoint, headers=admin)
            assert downloaded.status_code == 200
            assert downloaded.content == second_pdf

        assert EMAIL_BASE_URL == os.environ["INTEGRATION_PROXY_URL"].strip()
        email = verification_email("GridFS test", "https://example.org/activate")
        _assert_safe_email(*email)
    finally:
        server.db = original_db
        client.drop_database(test_db.name)
        client.close()
