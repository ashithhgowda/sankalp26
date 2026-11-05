from backend.core_utils import clean_doc, now_iso


async def create_notification(db, *, user_id: str, kind: str, title: str, message: str,
                              emailer=None, email_content=None, action_path=None):
    record = {
        "notification_id": __import__("uuid").uuid4().hex,
        "user_id": user_id,
        "kind": kind,
        "title": title,
        "message": message,
        "action_path": action_path,
        "read_at": None,
        "email_status": "not_requested" if not email_content else "pending",
        "email_provider_id": None,
        "created_at": now_iso(),
        "email_updated_at": now_iso(),
    }
    await db.notifications.insert_one(record.copy())
    if emailer and email_content:
        user = await db.users.find_one({"_id": __import__("bson").ObjectId(user_id)}, {"_id": 0, "email": 1})
        provider_id = None
        if user:
            subject, html = email_content
            provider_id = await emailer.send_email(to=user["email"], subject=subject, html=html)
        status = "sent" if provider_id else "failed"
        await db.notifications.update_one(
            {"notification_id": record["notification_id"]},
            {"$set": {"email_status": status, "email_provider_id": provider_id, "email_updated_at": now_iso()}},
        )
        record.update({"email_status": status, "email_provider_id": provider_id, "email_updated_at": now_iso()})
    record.pop("_id", None)
    return clean_doc(record)