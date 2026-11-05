# Read-only dependency audit and auth configuration inventory for review handoff.
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv('/app/backend/.env')
audit = Path('/app/test_reports/yarn_audit_review.jsonl')
seen = set()
for line in audit.read_text().splitlines():
    record = json.loads(line)
    if record.get('type') == 'auditSummary':
        print('Yarn audit summary:', json.dumps(record['data']))
    if record.get('type') == 'auditAdvisory':
        item = record['data']['advisory']
        key = item['id']
        if key not in seen:
            seen.add(key)
            print('Advisory:', item['module_name'], item['severity'], item['title'], 'patched:', item.get('patched_versions'), item.get('url'))
print('Configured CORS origins:', os.environ['CORS_ORIGINS'])
python_audit = Path('/app/test_reports/pip_audit_review.json')
if python_audit.exists():
    for item in json.loads(python_audit.read_text()).get('dependencies', []):
        if item.get('vulns'):
            print('Python advisory package:', item['name'], item['version'], 'count:', len(item['vulns']),
                  'ids:', ','.join(v['id'] for v in item['vulns']),
                  'fix versions:', sorted({version for v in item['vulns'] for version in v.get('fix_versions', [])}))
client = MongoClient(os.environ['MONGO_URL'])
db = client[os.environ['DB_NAME']]
for role in ['admin', 'judge']:
    user = db.users.find_one({'role': role})
    print(role, 'bcrypt prefix:', user['password_hash'][:4], 'must_change_password:', user.get('must_change_password'))
for coll in ['users', 'sessions', 'invitations', 'password_reset_tokens', 'rate_limits']:
    print(coll, 'indexes:', json.dumps(db[coll].index_information(), default=str))
print('Remaining review users:', db.users.count_documents({'email': {'$regex': '^test_(ui_review|ui_member|review|member|forced)_'}}))
client.close()