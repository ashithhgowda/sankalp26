# Phase 1 public-API workflows and security regression checks; temporary data/settings restored after run.
import base64
import hashlib
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

import bcrypt
import pytest
import requests
from bson import ObjectId
from dotenv import load_dotenv
from gridfs import GridFSBucket
from pymongo import MongoClient

load_dotenv('/app/frontend/.env')
load_dotenv('/app/backend/.env')
BASE = os.environ['REACT_APP_BACKEND_URL'].rstrip('/')
API = BASE + '/api'
PDF = b'%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF'
PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl2n6sAAAAASUVORK5CYII=')


def call(method, path, token=None, **kwargs):
    headers = kwargs.pop('headers', {})
    if token:
        headers['Authorization'] = 'Bearer ' + token
    return requests.request(method, API + path, headers=headers, timeout=180, **kwargs)


def login(email, password):
    r = call('POST', '/auth/login', json={'email': email, 'password': password})
    assert r.status_code == 200, r.text
    return r.json()['token']


@pytest.fixture(scope='module')
def state():
    client = MongoClient(os.environ['MONGO_URL'])
    db = client[os.environ['DB_NAME']]
    suffix = secrets.token_hex(4)
    s = {'db': db, 'suffix': suffix, 'email': f'TEST_review_{suffix}@example.com'.lower(),
         'member_email': f'TEST_member_{suffix}@example.com'.lower(), 'password': 'TEST_Review!2026Leader',
         'member_password': 'TEST_Review!2026Member', 'team_ids': [], 'user_ids': [], 'manual_ids': [], 'topic_ids': [],
         'topic': call('GET', '/public/meta').json()['topics'][0]['topic_id']}
    keys = ['timeline', 'payment', 'judging_windows', 'judging_formula']
    backups = {key: db.settings.find_one({'key': key}) for key in keys}
    credential_text = Path('/app/memory/test_credentials.md').read_text()
    for role in ['Admin', 'Judge']:
        email, password = re.search(rf'## {role}\n- Email: (.+)\n- Password: (.+)', credential_text).groups()
        s[role.lower()] = login(email, password)
        s[role.lower() + '_id'] = str(db.users.find_one({'email': email})['_id'])
    yield s
    for key, old in backups.items():
        db.settings.delete_many({'key': key})
        if old:
            db.settings.insert_one(old)
    ids = s['team_ids']
    users = s['user_ids']
    gridfs = GridFSBucket(db)
    for coll in ['teams', 'team_memberships', 'applications', 'payments', 'submissions', 'files',
                 'judge_assignments', 'evaluations', 'project_history']:
        if coll == "files":
            for record in db.files.find({"team_id": {"$in": ids}}, {"gridfs_id": 1}):
                if record.get("gridfs_id"):
                    gridfs.delete(ObjectId(record["gridfs_id"]))
        db[coll].delete_many({'team_id': {'$in': ids}})
    db.applications.delete_many({'application_id': {'$in': s['manual_ids']}})
    db.topics.delete_many({'topic_id': {'$in': s['topic_ids']}})
    db.judging_criteria.delete_many({'description': 'TEST_' + suffix})
    db.evaluation_history.delete_many({'snapshot.team_id': {'$in': ids}})
    db.users.delete_many({'_id': {'$in': [ObjectId(x) for x in users]}})
    for coll, field in [('sessions', 'user_id'), ('invitations', 'target_user_id'),
                        ('password_reset_tokens', 'user_id'), ('notifications', 'user_id')]:
        db[coll].delete_many({field: {'$in': users}})
    db.login_attempts.delete_many({'identifier': {'$regex': suffix}})
    db.audit_logs.delete_many({'target_id': {'$in': ids + users + s['manual_ids'] + s['topic_ids']}})
    client.close()


def test_01_public_topics_headers_and_cors(state):
    r = call('GET', '/public/meta', headers={'Origin': 'https://evil.example'})
    assert r.status_code == 200 and len(r.json()['topics']) == 6
    assert r.json()['timeline']['hackathon_start'].startswith('2026-11-27')
    assert r.json()['timeline']['hackathon_end'].startswith('2026-11-28')
    assert 'access-control-allow-origin' not in r.headers
    assert r.headers['x-content-type-options'] == 'nosniff'
    allowed = call('OPTIONS', '/auth/login', headers={'Origin': BASE, 'Access-Control-Request-Method': 'POST'})
    assert allowed.headers.get('access-control-allow-origin') == BASE
    assert allowed.headers.get('access-control-allow-credentials') == 'true'
    state['topic'] = r.json()['topics'][0]['topic_id']


def test_02_registration_validation_activation_and_member_login(state):
    s = state
    timeline = call('GET', '/admin/timeline', s['admin']).json()
    timeline.update(application_override='open', abstract_override='open')
    assert call('PUT', '/admin/timeline', s['admin'], json=timeline).status_code == 200
    payload = {'email': s['email'], 'password': s['password'], 'name': 'TEST Review Leader',
               'usn': 'TL' + s['suffix'], 'team_name': 'TEST_review_' + s['suffix'], 'college': 'TEST College',
               'phone': '9876543210', 'topic_id': s['topic'], 'members': [
                   {'name': 'TEST Member', 'usn': 'TM' + s['suffix'], 'email': s['member_email']}]}
    invalid = call('POST', '/auth/register', json={**payload, 'password': 'short'})
    assert invalid.status_code == 422 and 'detail' in invalid.json()
    r = call('POST', '/auth/register', json=payload)
    assert r.status_code == 201, r.text
    s['team'] = r.json()['team_id']; s['team_ids'].append(s['team'])
    assert r.json()['verification_required'] is True
    assert call('POST', '/auth/register', json=payload).status_code == 400
    for email, password, purpose in [(s['email'], None, 'verify_email'), (s['member_email'], s['member_password'], 'member_activation')]:
        user = s['db'].users.find_one({'email': email})
        s['user_ids'].append(str(user['_id']))
        raw = secrets.token_urlsafe(32)
        # Controlled token fixture: integration delivery is real; no inbox access is simulated as delivery.
        s['db'].invitations.update_one({'target_user_id': str(user['_id']), 'used_at': None},
                                     {'$set': {'token_hash': hashlib.sha256(raw.encode()).hexdigest()}})
        inspect = call('POST', '/auth/invitations/inspect', json={'token': raw})
        assert inspect.status_code == 200 and inspect.json()['purpose'] == purpose
        activated = call('POST', '/auth/activate', json={'token': raw, 'password': password})
        assert activated.status_code == 200 and activated.json()['user']['team_id'] == s['team']
        assert call('POST', '/auth/activate', json={'token': raw, 'password': password}).status_code == 400
    s['leader'] = login(s['email'], s['password'])
    s['member'] = login(s['member_email'], s['member_password'])
    user = s['db'].users.find_one({'email': s['email']})
    assert user['password_hash'].startswith('$2b$')
    assert s['db'].users.find_one({'email': s['member_email']})['password_hash'] != user['password_hash']


def test_03_cookie_refresh_csrf_logout(state):
    s = state; session = requests.Session()
    r = session.post(API + '/auth/login', json={'email': s['email'], 'password': s['password']}, timeout=60)
    assert r.status_code == 200 and 'HttpOnly' in r.headers['Set-Cookie'] and 'Secure' in r.headers['Set-Cookie']
    assert session.post(API + '/auth/refresh', timeout=60).status_code == 403
    csrf = session.cookies.get('csrf_token')
    refreshed = session.post(API + '/auth/refresh', headers={'X-CSRF-Token': csrf}, timeout=60)
    assert refreshed.status_code == 200 and refreshed.json()['token'] != r.json()['token']
    csrf = session.cookies.get('csrf_token')
    logout = session.post(API + '/auth/logout', headers={'X-CSRF-Token': csrf}, timeout=60)
    assert logout.status_code == 200 and logout.json()['ok'] is True
    assert call('GET', '/auth/me', refreshed.json()['token']).status_code == 401


def test_04_abstract_upload_and_private_access(state):
    s = state
    for name, data in [('fake.pdf', b'fake'), ('large.pdf', b'%PDF-' + b'A' * (3 * 1024 * 1024))]:
        r = call('POST', '/applications/abstract', s['leader'], data={'topic_id': s['topic']}, files={'file': (name, data, 'application/pdf')})
        assert r.status_code == 400 and 'detail' in r.json()
    r = call('POST', '/applications/abstract', s['leader'], data={'topic_id': s['topic']}, files={'file': ('TEST_abstract.pdf', PDF, 'application/pdf')})
    assert r.status_code == 200, r.text
    s['application'] = r.json()['application_id']; s['abstract_file'] = r.json()['file']['file_id']
    record = s['db'].files.find_one({'file_id': s['abstract_file']})
    assert record['team_id'] == s['team'] and record['topic_id'] == s['topic']
    assert record['topic_title'] == s['db'].topics.find_one({'topic_id': s['topic']})['title']
    assert record['filename'] == 'TEST_abstract.pdf' and record['uploaded_at']
    gridfs_id = ObjectId(record['gridfs_id'])
    with GridFSBucket(s['db']).open_download_stream(gridfs_id) as stored:
        assert stored.read() == PDF
    assert s['db'].fs.files.find_one({'_id': gridfs_id})['metadata']['topic_id'] == s['topic']
    persisted = call('GET', '/applications/me', s['member']).json()['application']
    assert persisted['application_id'] == s['application'] and persisted['status'] == 'pending'
    for token, expected in [(s['member'], 403), (s['judge'], 403), (None, 401)]:
        file = call('GET', '/files/' + s['abstract_file'], token)
        assert file.status_code == expected
    admin_file = call('GET', '/files/' + s['abstract_file'], s['admin'])
    assert admin_file.status_code == 200 and admin_file.content == PDF
    assert 'no-store' in admin_file.headers['cache-control']
    assert call('GET', '/payments/me', s['leader']).json()['settings'] is None
    assert call('PUT', '/projects/me', s['leader'], json=project_payload()).status_code == 403


def test_05_manual_record_and_application_review(state):
    s = state
    manual = call('POST', '/admin/applications/manual', s['admin'], json={'team_name': 'TEST_manual_' + s['suffix'],
        'college': 'TEST College', 'leader_name': 'TEST Manual', 'contact_email': s['email'], 'topic_id': s['topic'],
        'submission_date': '2026-11-01T10:00:00+05:30', 'notes': 'TEST received email'})
    assert manual.status_code == 200 and manual.json()['method'] == 'email'
    s['manual_ids'].append(manual.json()['application_id'])
    assert any(x['application_id'] == s['manual_ids'][0] for x in call('GET', '/admin/applications', s['admin']).json())
    for status in ['under_review', 'rejected', 'selected']:
        r = call('PATCH', '/admin/applications/' + s['application'], s['admin'], json={'status': status, 'admin_notes': 'TEST review'})
        assert r.status_code == 200 and r.json()['application']['status'] == status
        assert call('GET', '/applications/me', s['leader']).json()['application']['status'] == status
    dashboard = call('GET', '/participant/dashboard', s['member']).json()
    assert all(x['status'] == 'active' for x in dashboard['memberships'])


def test_06_payment_correction_approve_and_explicit_confirmation(state):
    s = state
    settings = call('PUT', '/admin/payment-settings', s['admin'], json={'amount': 600, 'upi_id': 'TEST@upi', 'bank_details': 'TEST only', 'instructions': 'TEST only', 'deadline': '2026-11-25T23:59:00+05:30'})
    assert settings.status_code == 200
    assert call('GET', '/payments/me', s['leader']).json()['settings']['amount'] == 600
    proof_data = {'transaction_ref': 'TEST_' + s['suffix'], 'payment_date': '2026-11-01', 'amount_paid': 600}
    for action in ['request_correction', 'reject', 'approve']:
        proof = call('POST', '/payments/proof', s['leader'], data=proof_data, files={'file': ('TEST_proof.png', PNG, 'image/png')})
        assert proof.status_code == 200 and proof.json()['status'] == 'payment_under_verification'
        s['payment'] = proof.json()['payment_id']
        assert call('POST', '/admin/payments/' + s['payment'] + '/confirm-registration', s['admin']).status_code == 400
        decision = call('PATCH', '/admin/payments/' + s['payment'], s['admin'], json={'action': action, 'reason': 'TEST review'})
        assert decision.status_code == 200, decision.text
        expected = 'payment_verified' if action == 'approve' else 'correction_required'
        assert call('GET', '/payments/me', s['leader']).json()['payment']['status'] == expected
    assert call('GET', '/projects/me', s['leader']).json()['eligible'] is False
    confirmation = call('POST', '/admin/payments/' + s['payment'] + '/confirm-registration', s['admin'])
    assert confirmation.status_code == 200 and confirmation.json()['ok'] is True
    assert call('GET', '/participant/dashboard', s['leader']).json()['team']['registration_status'] == 'registration_confirmed'


def project_payload():
    return {'title': 'TEST Review Project', 'description': 'TEST isolated project submission for security workflow verification.',
            'github_url': 'https://github.com/example/test', 'demo_url': 'https://example.com/test', 'video_url': 'https://youtu.be/dQw4w9WgXcQ'}


def test_07_project_deadline_draft_resources_and_final_lock(state):
    s = state; timeline = call('GET', '/admin/timeline', s['admin']).json()
    timeline.update(project_override='auto', project_open='2020-01-01T00:00:00+05:30', project_close='2020-01-02T00:00:00+05:30')
    assert call('PUT', '/admin/timeline', s['admin'], json=timeline).status_code == 200
    assert call('PUT', '/projects/me', s['leader'], json=project_payload()).status_code == 400
    timeline['project_override'] = 'open'
    assert call('PUT', '/admin/timeline', s['admin'], json=timeline).status_code == 200
    r = call('PUT', '/projects/me', s['leader'], json=project_payload())
    assert r.status_code == 200 and r.json()['status'] == 'draft'
    assert call('GET', '/projects/me', s['member']).json()['submission']['title'] == 'TEST Review Project'
    assert call('POST', '/projects/me/submit', s['leader']).status_code == 400
    document = call('POST', '/projects/me/presentation', s['leader'], files={'file': ('TEST_document.pdf', PDF, 'application/pdf')})
    assert document.status_code == 200
    s['project_file'] = document.json()['file_id']
    resource = call('POST', '/projects/me/resources/link', s['leader'], json={'title': 'TEST link', 'resource_type': 'external_link', 'url': 'https://example.com/resource'})
    assert resource.status_code == 200
    rid = resource.json()['resource_id']
    assert call('DELETE', '/projects/me/resources/' + rid, s['leader']).json()['ok'] is True
    assert not any(x['resource_id'] == rid for x in call('GET', '/projects/me', s['leader']).json()['submission']['resources'])
    resource = call('POST', '/projects/me/resources/file', s['leader'], data={'title': 'TEST supporting document', 'resource_type': 'project_document'}, files={'file': ('TEST_extra.pdf', PDF, 'application/pdf')})
    assert resource.status_code == 200
    final = call('POST', '/projects/me/submit', s['leader'])
    assert final.status_code == 200 and final.json()['status'] == 'submitted'
    assert call('PUT', '/projects/me', s['leader'], json=project_payload()).status_code == 400


def test_08_judge_assignment_criteria_windows_and_separate_records(state):
    s = state
    assigned = call('POST', '/admin/judge-assignments', s['admin'], json={'judge_id': s['judge_id'], 'team_id': s['team'], 'phases': ['phase1', 'phase2']})
    assert assigned.status_code == 200 and assigned.json()['team_id'] == s['team']
    assert call('GET', '/files/' + s['project_file'], s['judge']).content == PDF
    for phase in ['phase1', 'phase2']:
        criteria = call('GET', '/judge/criteria/' + phase, s['judge']).json()
        if not criteria:
            created = call('POST', '/admin/judging/criteria', s['admin'], json={'phase': phase, 'title': 'TEST review criterion', 'description': 'TEST_' + s['suffix'], 'max_marks': 10, 'weight': 1})
            assert created.status_code == 200
            criteria = [created.json()]
        s[phase + '_criteria'] = criteria
        windows = {'phase1_open': False, 'phase2_open': False}
        assert call('PUT', '/admin/judging/windows', s['admin'], json=windows).status_code == 200
        payload = {'phase': phase, 'scores': [{'criterion_id': c['criterion_id'], 'marks': c['max_marks'] * .8} for c in criteria], 'action': 'save'}
        assert call('PUT', '/judge/evaluations/' + s['team'], s['judge'], json=payload).status_code == 400
        windows[phase + '_open'] = True
        assert call('PUT', '/admin/judging/windows', s['admin'], json=windows).status_code == 200
        assert call('PUT', '/judge/evaluations/' + s['team'], s['judge'], json={**payload, 'scores': []}).status_code == 400
        r = call('PUT', '/judge/evaluations/' + s['team'], s['judge'], json=payload)
        assert r.status_code == 200 and r.json()['status'] == 'draft'
        payload['action'] = 'submit'
        r = call('PUT', '/judge/evaluations/' + s['team'], s['judge'], json=payload)
        assert r.status_code == 200 and r.json()['normalized_total'] == 80
        assert call('PUT', '/judge/evaluations/' + s['team'], s['judge'], json=payload).status_code == 400
    results = call('GET', '/admin/results', s['admin']).json()
    assert all(any(x['team_id'] == s['team'] for x in results['phases'][p]) for p in ['phase1', 'phase2'])


def test_09_no_consolidation_until_formula_and_formula_results(state):
    s = state; s['db'].settings.delete_many({'key': 'judging_formula'})
    assert call('GET', '/admin/results', s['admin']).json()['consolidated'] == {'configured': False, 'rows': []}
    assert call('PUT', '/admin/judging/formula', s['admin'], json={'phase1_weight': 0, 'phase2_weight': 0}).status_code == 400
    assert call('PUT', '/admin/judging/formula', s['admin'], json={'phase1_weight': 30, 'phase2_weight': 70}).status_code == 200
    rows = call('GET', '/admin/results', s['admin']).json()['consolidated']['rows']
    row = next(x for x in rows if x['team_id'] == s['team'])
    assert row['score'] == 80 and row['phase1'] == 80 and row['phase2'] == 80


def test_10_rbac_cross_team_files_and_read_only_arena(state):
    s = state
    for endpoint in ['/admin/overview', '/admin/participants', '/admin/payments', '/admin/judging', '/admin/audit-log']:
        assert call('GET', endpoint, s['member']).status_code == 403
    assert call('PUT', '/judge/evaluations/' + str(ObjectId()), s['judge'], json={'phase': 'phase2', 'scores': [], 'action': 'save'}).status_code == 403
    text = Path('/app/memory/test_credentials.md').read_text()
    email, password = re.search(r'## Phase 1 Team Leader\n- Email: (.+)\n- Password: (.+)', text).groups()
    other = login(email, password)
    assert call('GET', '/files/' + s['abstract_file'], other).status_code == 403
    public = call('GET', '/arena/questions')
    assert public.status_code == 200 and all('answer_index' not in x for x in public.json())
    assert call('GET', '/arena/admin/questions', s['member']).status_code == 403
    assert call('GET', '/arena/admin/questions', s['admin']).status_code == 200


def test_11_admin_topics_crud_and_audit_persistence(state):
    s = state
    payload = {'title': 'TEST temporary review topic', 'description': 'TEST temporary review description', 'short': 'TEST', 'enabled': False}
    r = call('POST', '/admin/topics', s['admin'], json=payload)
    assert r.status_code == 200
    tid = r.json()['topic_id']; s['topic_ids'].append(tid)
    payload['title'] += ' updated'
    assert call('PUT', '/admin/topics/' + tid, s['admin'], json=payload).status_code == 200
    row = next(x for x in call('GET', '/admin/topics', s['admin']).json() if x['topic_id'] == tid)
    assert row['title'] == payload['title']
    assert call('DELETE', '/admin/topics/' + tid, s['admin']).json()['ok'] is True
    assert not any(x['topic_id'] == tid for x in call('GET', '/admin/topics', s['admin']).json())
    logs = call('GET', '/admin/audit-log', s['admin']).json()
    assert any(x['target_id'] == tid and x['action'] == 'topic.deleted' for x in logs)


def test_12_password_change_reset_and_session_invalidation(state):
    s = state; new_password = 'TEST_Changed!2026Leader'
    changed = call('POST', '/auth/change-password', s['leader'], json={'current_password': s['password'], 'new_password': new_password})
    assert changed.status_code == 200 and changed.json()['user']['must_change_password'] is False
    assert call('GET', '/auth/me', s['leader']).status_code == 401
    token = changed.json()['token']
    assert call('POST', '/auth/forgot-password', json={'email': s['email']}).json()['ok'] is True
    raw = secrets.token_urlsafe(32)
    s['db'].password_reset_tokens.update_one({'user_id': s['team'], 'used_at': None}, {'$set': {'token_hash': hashlib.sha256(raw.encode()).hexdigest()}})
    reset = call('POST', '/auth/reset-password', json={'token': raw, 'password': s['password']})
    assert reset.status_code == 200 and reset.json()['ok'] is True
    assert call('GET', '/auth/me', token).status_code == 401
    assert call('POST', '/auth/reset-password', json={'token': raw, 'password': s['password']}).status_code == 400
    s['leader'] = login(s['email'], s['password'])


def test_13_lockout_after_five_failures(state):
    email = 'test_lock_' + state['suffix'] + '@example.com'
    codes = [call('POST', '/auth/login', json={'email': email, 'password': 'TEST_Invalid!2026'}).status_code for _ in range(6)]
    assert codes == [401, 401, 401, 401, 401, 429], codes


def test_14_document_security_headers():
    r = requests.get(BASE, timeout=60)
    assert r.status_code == 200
    for header in ['content-security-policy', 'x-content-type-options', 'strict-transport-security']:
        assert r.headers.get(header), f'Missing {header} on HTML document'


def test_15_long_passwords_are_not_silently_truncated(state):
    s = state; prefix = 'Aa1!' + 'x' * 68
    long_password = prefix + 'correct-suffix'
    changed = call('POST', '/auth/change-password', s['leader'], json={'current_password': s['password'], 'new_password': long_password})
    try:
        if changed.status_code == 422:
            return
        assert changed.status_code == 200, changed.text
        wrong = call('POST', '/auth/login', json={'email': s['email'], 'password': prefix + 'wrong-suffix'})
        assert wrong.status_code == 401, 'A different password suffix after byte 72 authenticated successfully'
    finally:
        if changed.status_code == 200:
            restored = call('POST', '/auth/change-password', changed.json()['token'], json={'current_password': long_password, 'new_password': s['password']})
            assert restored.status_code == 200
            s['leader'] = restored.json()['token']


def test_16_forced_password_change_protects_private_files(state):
    s = state; uid = ObjectId(); email = f'test_forced_{s["suffix"]}@example.com'; password = 'TEST_Forced!2026Admin'
    s['user_ids'].append(str(uid))
    s['db'].users.insert_one({'_id': uid, 'email': email, 'name': 'TEST forced admin', 'role': 'admin',
        'password_hash': bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode(), 'is_active': True,
        'email_verified': True, 'must_change_password': True, 'session_version': 0})
    token = login(email, password)
    assert call('GET', '/admin/overview', token).status_code == 403
    r = call('GET', '/files/' + s['abstract_file'], token)
    assert r.status_code == 403, f'Forced-change admin downloaded a private file: {r.status_code}'


def test_17_judge_cannot_download_payment_proofs(state):
    s = state; payment = call('GET', '/payments/me', s['leader']).json()['payment']
    r = call('GET', '/files/' + payment['proof']['file_id'], s['judge'])
    assert r.status_code == 403, 'Assigned judge can access confidential payment receipts unrelated to judging'


def test_18_duplicate_criterion_scores_rejected(state):
    s = state; existing = s['db'].evaluations.find_one({'team_id': s['team'], 'judge_id': s['judge_id'], 'phase': 'phase2'})
    s['db'].evaluations.update_one({'_id': existing['_id']}, {'$set': {'status': 'draft'}})
    try:
        call('PUT', '/admin/judging/windows', s['admin'], json={'phase1_open': True, 'phase2_open': True})
        criteria = s['phase2_criteria']
        scores = [{'criterion_id': c['criterion_id'], 'marks': c['max_marks'] * .5} for c in criteria]
        scores.append({'criterion_id': criteria[0]['criterion_id'], 'marks': criteria[0]['max_marks']})
        r = call('PUT', '/judge/evaluations/' + s['team'], s['judge'], json={'phase': 'phase2', 'scores': scores, 'action': 'save'})
        assert r.status_code in [400, 422], f'Duplicate criterion accepted and reweighted score: {r.text}'
    finally:
        s['db'].evaluations.replace_one({'_id': existing['_id']}, existing)


def test_19_payment_deadline_enforced(state):
    s = state; existing = s['db'].payments.find_one({'team_id': s['team']})
    s['db'].payments.update_one({'_id': existing['_id']}, {'$set': {'status': 'correction_required'}})
    call('PUT', '/admin/payment-settings', s['admin'], json={'amount': 600, 'deadline': '2020-01-01T00:00:00+05:30'})
    try:
        r = call('POST', '/payments/proof', s['leader'], data={'transaction_ref': 'TEST_DEADLINE', 'payment_date': '2026-11-01', 'amount_paid': 600}, files={'file': ('TEST_late.pdf', PDF, 'application/pdf')})
        assert r.status_code == 400, f'Payment proof accepted after configured deadline: {r.status_code}'
    finally:
        s['db'].payments.replace_one({'_id': existing['_id']}, existing)


def test_20_logout_revokes_refresh_without_access_cookie(state):
    s = state; session = requests.Session()
    logged = session.post(API + '/auth/login', json={'email': s['email'], 'password': s['password']}, timeout=60)
    assert logged.status_code == 200
    refresh = session.cookies.get('refresh_token')
    csrf = session.cookies.get('csrf_token')
    for cookie in list(session.cookies):
        if cookie.name == 'access_token':
            session.cookies.clear(cookie.domain, cookie.path, cookie.name)
    logout = session.post(API + '/auth/logout', headers={'X-CSRF-Token': csrf}, timeout=60)
    assert logout.status_code == 200 and logout.json()['ok'] is True
    replay = requests.post(API + '/auth/refresh', cookies={'refresh_token': refresh, 'csrf_token': csrf},
                           headers={'X-CSRF-Token': csrf}, timeout=60)
    assert replay.status_code == 401, 'Refresh session remains usable after logout when access cookie has expired'