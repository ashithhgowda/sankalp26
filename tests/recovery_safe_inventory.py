from pathlib import Path
from dotenv import dotenv_values
from pymongo import MongoClient
import json

# Recovery inventory: report only non-secret flags, schema, and public app URL.
credentials = Path('/app/memory/test_credentials.md')
text = credentials.read_text() if credentials.exists() else ''
env = dotenv_values('/app/backend/.env')
front = dotenv_values('/app/frontend/.env')
db = MongoClient(env['MONGO_URL'])[env['DB_NAME']]
user = db.users.find_one({'email': env['ADMIN_EMAIL'].strip().lower()})
events = list(db.audit_logs.find({'action': {'$in': ['admin.recovery_initiated', 'admin.recovery_flow_verified']}}))
print(json.dumps({
    'credentials_file_present': credentials.exists(), 'credentials_file_nonempty': bool(text.strip()),
    'credentials_guidance_mentions_recovery': 'recovery' in text.lower(),
    'public_url': front['REACT_APP_BACKEND_URL'],
    'matching_admin_count': db.users.count_documents({'email': env['ADMIN_EMAIL'].strip().lower()}),
    'active': user.get('is_active') if user else None,
    'must_change_password': user.get('must_change_password') if user else None,
    'audit_events': [{'action': e['action'], 'detail_keys': list(e.get('details', {}).keys()), 'matches_admin': e.get('target_id') == str(user['_id'])} for e in events],
    'legacy_attempt_count': db.login_attempts.count_documents({'identifier': env['ADMIN_EMAIL'].strip().lower()})
}, indent=2))