# Isolated collaboration/browser fixtures; real public APIs, file storage and email delivery.
import json
import os
import re
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path

from bson import ObjectId
import bcrypt
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv('/app/frontend/.env')
load_dotenv('/app/backend/.env')
BASE = os.environ['REACT_APP_BACKEND_URL'].rstrip('/')
PDF = b'%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF'
FIXTURE_PATH = Path('/app/test_reports/new_requirements_fixture.json')


def credentials(role):
    return re.search(rf'## {role}\n- Email: (.+)\n- Password: (.+)', Path('/app/memory/test_credentials.md').read_text()).groups()


def setup():
    client = MongoClient(os.environ['MONGO_URL'])
    db = client[os.environ['DB_NAME']]
    suffix = secrets.token_hex(4)
    leader, member, outsider = ObjectId(), ObjectId(), ObjectId()
    now = datetime.now(timezone.utc).isoformat()
    team = str(leader)
    data = {'team_id': team, 'member_id': str(member), 'name': 'TEST_collaboration_' + suffix,
            'suffix': suffix, 'users': [], 'topics': list(db.topics.find({}, {'_id': 0})),
            'timeline': db.settings.find_one({'key': 'timeline'}, {'_id': 0})}
    role_passwords = {'team': 'Fixture!Leader2026', 'member': 'Fixture!Member2026'}
    for uid, role in [(leader, 'team'), (member, 'member')]:
        password = role_passwords[role]
        email = f'test_collaboration_{role}_{suffix}@example.com'
        name = 'TEST Collaboration ' + role
        db.users.insert_one({'_id': uid, 'email': email, 'name': name, 'role': role, 'team_id': team,
                             'password_hash': bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode(), 'is_active': True, 'email_verified': True,
                             'must_change_password': False, 'session_version': 0, 'created_at': now})
        db.team_memberships.insert_one({'membership_id': 'TEST_MEM_' + str(uid), 'team_id': team,
                                        'user_id': str(uid), 'name': name, 'email': email,
                                        'role': 'leader' if role == 'team' else 'member', 'status': 'active', 'created_at': now})
        data['users'].append(str(uid))
        data[role + '_email'] = email
        data[role + '_password'] = password
    outsider_password = 'Fixture!Outsider2026'
    outsider_email = f'test_collaboration_outsider_{suffix}@example.com'
    db.users.insert_one({'_id': outsider, 'email': outsider_email, 'name': 'TEST Collaboration outsider',
                         'role': 'member', 'team_id': str(outsider),
                         'password_hash': bcrypt.hashpw(outsider_password.encode(), bcrypt.gensalt()).decode(),
                         'is_active': True, 'email_verified': True, 'must_change_password': False,
                         'session_version': 0, 'created_at': now})
    data['users'].append(str(outsider)); data['outsider_email'] = outsider_email; data['outsider_password'] = outsider_password
    db.teams.insert_one({'team_id': team, 'leader_id': team, 'name': data['name'], 'name_key': data['name'].lower(),
                         'college': 'TEST College', 'registration_status': 'registration_confirmed', 'created_at': now})
    db.settings.update_one({'key': 'timeline'}, {'$set': {'project_override': 'open'}}, upsert=True)
    _, _ = credentials('Judge')
    judge = db.users.find_one({'email': credentials('Judge')[0]})
    db.judge_assignments.insert_one({'assignment_id': 'TEST_ASN_' + suffix, 'team_id': team, 'judge_id': str(judge['_id']),
                                     'phases': ['phase1', 'phase2'], 'created_at': now})
    for kind in ['registration_confirmed', 'member_activation']:
        nid = 'TEST_NOTICE_' + kind + '_' + suffix
        db.notifications.insert_one({'notification_id': nid, 'user_id': team, 'kind': kind,
                                      'title': 'TEST delivery ' + kind, 'message': 'TEST notification management',
                                      'action_path': '/dashboard', 'email_status': 'failed', 'created_at': now, 'read_at': None})
        data[kind + '_notice'] = nid
    client.close()
    return data


def cleanup(data):
    client = MongoClient(os.environ['MONGO_URL'])
    db = client[os.environ['DB_NAME']]
    tid = data['team_id']
    submission_ids = db.submissions.distinct('submission_id', {'team_id': tid})
    resource_file_ids = db.files.distinct('file_id', {'team_id': tid})
    for coll in ['teams', 'team_memberships', 'applications', 'payments', 'submissions', 'files',
                 'judge_assignments', 'evaluations', 'project_history']:
        db[coll].delete_many({'team_id': tid})
    for coll, field in [('sessions', 'user_id'), ('notifications', 'user_id')]:
        db[coll].delete_many({field: {'$in': data['users']}})
    db.users.delete_many({'_id': {'$in': [ObjectId(uid) for uid in data['users']]}})
    db.audit_logs.delete_many({'target_id': {'$in': data['users'] + submission_ids + resource_file_ids +
                                             [data['registration_confirmed_notice'], data['member_activation_notice']]}})
    db.settings.delete_many({'key': 'timeline'})
    if data['timeline']:
        db.settings.insert_one(data['timeline'])
    for topic in data['topics']:
        db.topics.update_one({'topic_id': topic['topic_id']}, {'$set': {'order': topic['order']}})
    client.close()


if __name__ == '__main__':
    if sys.argv[1] == 'setup':
        data = setup()
        FIXTURE_PATH.write_text(json.dumps(data))
        print(json.dumps(data))
    else:
        cleanup(json.loads(FIXTURE_PATH.read_text()))
        FIXTURE_PATH.unlink()
        print('PASS isolated fixture removed; timeline and topic order restored')