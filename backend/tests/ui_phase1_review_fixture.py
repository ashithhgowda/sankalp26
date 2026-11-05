# Isolated browser workflow fixture; never modifies existing teams, settings or Arena.
import hashlib
import json
import os
import secrets
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import bcrypt
from bson import ObjectId
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv('/app/backend/.env')
client = MongoClient(os.environ['MONGO_URL'])
db = client[os.environ['DB_NAME']]
path = Path('/app/test_reports/ui_review_fixture.json')
if sys.argv[1] == 'setup':
    suffix = secrets.token_hex(4)
    leader_id, member_id = ObjectId(), ObjectId()
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    data = {'leader_email': f'test_ui_review_{suffix}@example.com', 'leader_password': 'TEST_UI!2026Leader',
            'member_email': f'test_ui_member_{suffix}@example.com', 'member_password': 'TEST_UI!2026Member',
            'team_id': str(leader_id), 'member_id': str(member_id), 'token': token, 'name': 'TEST_UI_' + suffix}
    db.teams.insert_one({'team_id': str(leader_id), 'name': data['name'], 'name_key': data['name'].lower(),
        'leader_id': str(leader_id), 'college': 'TEST College', 'topic_id': 'drone',
        'topic_title': db.topics.find_one({'topic_id': 'drone'})['title'], 'registration_status': 'registered',
        'created_at': now.isoformat(), 'updated_at': now.isoformat()})
    for uid, email, name, role, password in [(leader_id, data['leader_email'], 'TEST UI Leader', 'team', data['leader_password']),
                                           (member_id, data['member_email'], 'TEST UI Member', 'member', None)]:
        db.users.insert_one({'_id': uid, 'email': email, 'name': name, 'team_name': data['name'], 'role': role,
            'team_id': str(leader_id), 'college': 'TEST College', 'usn': ('UL' if role == 'team' else 'UM') + suffix,
            'password_hash': bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode() if password else None,
            'is_active': bool(password), 'email_verified': bool(password), 'must_change_password': False,
            'session_version': 0, 'created_at': now.isoformat()})
        db.team_memberships.insert_one({'membership_id': 'TEST_MEM_' + str(uid), 'team_id': str(leader_id),
            'user_id': str(uid), 'name': name, 'email': email, 'usn': ('UL' if role == 'team' else 'UM') + suffix,
            'role': 'leader' if role == 'team' else 'member', 'status': 'active' if password else 'invited',
            'college': 'TEST College', 'created_at': now.isoformat()})
    db.invitations.insert_one({'invitation_id': 'TEST_INV_' + suffix, 'token_hash': hashlib.sha256(token.encode()).hexdigest(),
        'purpose': 'member_activation', 'team_id': str(leader_id), 'target_user_id': str(member_id),
        'expires_at': now + timedelta(hours=1), 'used_at': None, 'revoked_at': None, 'created_at': now.isoformat()})
    path.write_text(json.dumps(data))
    print(json.dumps(data))
else:
    data = json.loads(path.read_text())
    team = data['team_id']; users = [team, data['member_id']]
    for coll in ['teams', 'team_memberships', 'applications', 'payments', 'submissions', 'files', 'judge_assignments', 'evaluations', 'project_history']:
        db[coll].delete_many({'team_id': team})
    db.evaluation_history.delete_many({'snapshot.team_id': team})
    for coll, field in [('sessions', 'user_id'), ('invitations', 'target_user_id'), ('password_reset_tokens', 'user_id'), ('notifications', 'user_id')]:
        db[coll].delete_many({field: {'$in': users}})
    db.users.delete_many({'_id': {'$in': [ObjectId(x) for x in users]}})
    db.audit_logs.delete_many({'target_id': {'$in': users}})
    path.unlink()
    print('Cleaned isolated UI team and member')
client.close()