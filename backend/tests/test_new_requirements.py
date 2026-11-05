# New Phase 1 requirements: shared edits/files, audited reopen, topic order, delivery management and Arena preservation.
import concurrent.futures
import time

import pytest
import requests
from bson import ObjectId
from pymongo import MongoClient
import os

from new_requirements_fixture import BASE, PDF, cleanup, credentials, setup


def call(method, path, token=None, **kwargs):
    headers = kwargs.pop('headers', {})
    if token:
        headers['Authorization'] = 'Bearer ' + token
    return requests.request(method, BASE + '/api' + path, headers=headers, timeout=120, **kwargs)


def payload(title='TEST Collaborative Project'):
    return {'title': title, 'description': 'TEST activated members collaborate on the same eligible project draft.',
            'github_url': 'https://github.com/example/test', 'demo_url': 'https://example.com/demo',
            'video_url': 'https://example.com/video'}


@pytest.fixture(scope='module')
def state():
    s = setup()
    try:
        for key in ['team', 'member', 'admin', 'judge']:
            email, password = (s[key + '_email'], s[key + '_password']) if key in ['team', 'member'] else credentials(key.title())
            response = call('POST', '/auth/login', json={'email': email, 'password': password})
            if response.status_code != 200:
                pytest.skip('Fixture authentication failed: ' + response.text)
            s[key] = response.json()['token']
            s[key + '_uid'] = response.json()['user']['id']
        yield s
    finally:
        cleanup(s)


def project(s, role='member'):
    r = call('GET', '/projects/me', s[role])
    assert r.status_code == 200, r.text
    return r.json()['submission']


def test_01_auth_cookies_cors_and_hash(state):
    s = state
    r = call('POST', '/auth/login', json={'email': s['member_email'], 'password': s['member_password']})
    assert r.status_code == 200 and r.json()['user']['role'] == 'member'
    cookies = r.headers['set-cookie']
    assert 'access_token=' in cookies and 'refresh_token=' in cookies
    for cookie in r.raw.headers.getlist('Set-Cookie'):
        if cookie.startswith(('access_token=', 'refresh_token=')):
            assert 'HttpOnly' in cookie and 'Secure' in cookie
    cors = call('OPTIONS', '/auth/login', headers={'Origin': BASE, 'Access-Control-Request-Method': 'POST'})
    assert cors.headers.get('access-control-allow-origin') == BASE and cors.headers.get('access-control-allow-credentials') == 'true'
    client = MongoClient(os.environ['MONGO_URL'])
    assert client[os.environ['DB_NAME']].users.find_one({'_id': ObjectId(s['member_id'])})['password_hash'].startswith('$2b$')
    client.close()


def test_02_leader_member_shared_draft(state):
    s = state
    r = call('PUT', '/projects/me', s['team'], json=payload())
    assert r.status_code == 200 and r.json()['status'] == 'draft', r.text
    s['sid'] = r.json()['submission_id']
    assert project(s)['title'] == payload()['title']
    r = call('PUT', '/projects/me', s['member'], json=payload('TEST Member edit'))
    assert r.status_code == 200 and r.json()['submission_id'] == s['sid'], r.text
    assert project(s, 'team')['title'] == 'TEST Member edit'


def test_03_member_presentation_and_file_link_deliverables(state):
    s = state
    p = call('POST', '/projects/me/presentation', s['member'], files={'file': ('TEST_presentation.pdf', PDF, 'application/pdf')})
    assert p.status_code == 200, p.text
    s['presentation'] = p.json()['file_id']
    assert project(s, 'team')['presentation_file']['file_id'] == s['presentation']
    r = call('POST', '/projects/me/resources/file', s['member'], data={'title': 'TEST custom file title', 'description': 'TEST custom file description', 'resource_type': 'project_document'}, files={'file': ('TEST_resource.pdf', PDF, 'application/pdf')})
    assert r.status_code == 200, r.text
    s['file_resource'] = r.json()
    r = call('POST', '/projects/me/resources/link', s['member'], json={'title': 'TEST custom link title', 'description': 'TEST custom link description', 'resource_type': 'external_link', 'url': 'https://example.com/resource'})
    assert r.status_code == 200, r.text
    s['link_resource'] = r.json()
    resources = project(s, 'team')['resources']
    assert any(x['description'] == 'TEST custom file description' and x['title'] == 'TEST custom file title' for x in resources)
    assert any(x['description'] == 'TEST custom link description' and x['title'] == 'TEST custom link title' for x in resources)


def test_04_member_remove_file_and_link(state):
    s = state
    for kind in ['file_resource', 'link_resource']:
        old = s[kind]
        deleted = call('DELETE', '/projects/me/resources/' + old['resource_id'], s['member'])
        assert deleted.status_code == 200 and deleted.json()['ok'] is True
        assert not any(x['resource_id'] == old['resource_id'] for x in project(s, 'team')['resources'])
    r = call('GET', '/files/' + s['file_resource']['file']['file_id'], s['member'])
    assert r.status_code == 404 and 'detail' in r.json()
    # Keep authorized resources for final-lock and reviewer coverage.
    test_03_member_presentation_and_file_link_deliverables(s)


def test_05_finalize_blocks_all_team_mutations(state):
    s = state
    r = call('POST', '/projects/me/submit', s['member'])
    assert r.status_code == 200 and r.json()['status'] == 'submitted', r.text
    before = project(s)
    for role in ['team', 'member']:
        operations = [
            ('PUT', '/projects/me', {'json': payload('TEST forbidden edit')}),
            ('POST', '/projects/me/presentation', {'files': {'file': ('TEST_locked.pdf', PDF, 'application/pdf')}}),
            ('POST', '/projects/me/resources/file', {'data': {'title': 'TEST blocked', 'resource_type': 'project_document'}, 'files': {'file': ('TEST_locked.pdf', PDF, 'application/pdf')}}),
            ('POST', '/projects/me/resources/link', {'json': {'title': 'TEST blocked', 'resource_type': 'external_link', 'url': 'https://example.com'}}),
            ('DELETE', '/projects/me/resources/' + s['link_resource']['resource_id'], {}),
        ]
        for method, path, kwargs in operations:
            blocked = call(method, path, s[role], **kwargs)
            assert blocked.status_code in [400, 404] and 'detail' in blocked.json(), blocked.text
    assert project(s) == before


def test_06_admin_only_reopen_history_and_audit(state):
    s = state
    for role in ['team', 'member', 'judge']:
        r = call('POST', f'/admin/projects/{s["sid"]}/reopen', s[role])
        assert r.status_code == 403 and r.json()['detail'] == 'Forbidden'
    r = call('POST', f'/admin/projects/{s["sid"]}/reopen', s['admin'])
    assert r.status_code == 200 and r.json()['status'] == 'draft', r.text
    assert project(s)['reopened_by'] == s['admin_uid']
    row = next(x for x in call('GET', '/admin/projects', s['admin']).json() if x['submission_id'] == s['sid'])
    assert any(x['action'] == 'reopened_by_admin' and x['by'] == s['admin_uid'] for x in row['history'])
    logs = call('GET', '/admin/audit-log', s['admin']).json()
    assert any(x['action'] == 'project.reopened' and x['target_id'] == s['sid'] for x in logs)


def test_07_member_edit_and_refinalize(state):
    s = state
    r = call('PUT', '/projects/me', s['member'], json=payload('TEST reopened member edit'))
    assert r.status_code == 200 and r.json()['status'] == 'draft'
    assert project(s, 'team')['title'] == 'TEST reopened member edit'
    r = call('POST', '/projects/me/submit', s['team'])
    assert r.status_code == 200 and r.json()['status'] == 'submitted'
    assert project(s)['status'] == 'submitted'


def test_08_admin_judge_authorized_deliverables(state):
    s = state
    for role, path in [('admin', '/admin/projects'), ('judge', '/judge/submissions')]:
        r = call('GET', path, s[role])
        assert r.status_code == 200
        row = next(x for x in r.json() if x['submission_id'] == s['sid'])
        assert row['video_url'] == payload()['video_url'] and len(row['resources']) == 2
        for fid in [s['presentation'], s['file_resource']['file']['file_id']]:
            f = call('GET', '/files/' + fid, s[role])
            assert f.status_code == 200 and f.content == PDF
    assert call('GET', '/files/' + s['presentation']).status_code == 401
    r = call('POST', '/auth/login', json={'email': s['outsider_email'], 'password': s['outsider_password']})
    assert call('GET', '/files/' + s['presentation'], r.json()['token']).status_code == 403


def test_09_topic_reorder_preserves_six_records(state):
    s = state
    original = call('GET', '/admin/topics', s['admin']).json()
    assert len(original) == 6
    ids = [x['topic_id'] for x in original]
    try:
        r = call('PUT', '/admin/topics/order', s['admin'], json={'topic_ids': ids[::-1]})
        assert r.status_code == 200 and [x['topic_id'] for x in r.json()] == ids[::-1]
        public = call('GET', '/public/meta').json()['topics']
        assert [x['topic_id'] for x in public] == ids[::-1]
        assert {x['topic_id']: (x['title'], x['description'], x['enabled']) for x in public} == {x['topic_id']: (x['title'], x['description'], x['enabled']) for x in original}
        for invalid in [ids[:-1], ids[:-1] + [ids[0]], ids + ['unknown']]:
            r = call('PUT', '/admin/topics/order', s['admin'], json={'topic_ids': invalid})
            assert r.status_code == 400 and 'detail' in r.json()
        assert call('PUT', '/admin/topics/order', s['member'], json={'topic_ids': ids}).status_code == 403
    finally:
        assert call('PUT', '/admin/topics/order', s['admin'], json={'topic_ids': ids}).status_code == 200


def test_10_notice_recipient_dashboard_status_retry_and_audit(state):
    s = state
    r = call('GET', '/admin/notifications', s['admin'])
    assert r.status_code == 200
    notice = next(x for x in r.json() if x['notification_id'] == s['registration_confirmed_notice'])
    assert notice['recipient']['email'] == s['team_email'] and notice['email_status'] == 'failed'
    dashboard = call('GET', '/participant/dashboard', s['team']).json()
    assert any(x['notification_id'] == notice['notification_id'] for x in dashboard['notifications'])
    retry = call('POST', f'/admin/notifications/{notice["notification_id"]}/retry', s['admin'])
    assert retry.status_code == 200 and retry.json()['email_status'] in ['failed', 'sent'], retry.text
    after = next(x for x in call('GET', '/admin/notifications', s['admin']).json() if x['notification_id'] == notice['notification_id'])
    assert after['email_status'] == retry.json()['email_status'] and after['email_updated_at']
    assert any(x['action'] == 'notification.email_retried' and x['target_id'] == notice['notification_id'] for x in call('GET', '/admin/audit-log', s['admin']).json())


def test_11_retry_security_and_role_guards(state):
    s = state
    r = call('POST', f'/admin/notifications/{s["member_activation_notice"]}/retry', s['admin'])
    assert r.status_code == 400 and 'newly generated token' in r.json()['detail']
    for role in ['member', 'judge']:
        r = call('GET', '/admin/notifications', s[role])
        assert r.status_code == 403 and r.json()['detail'] == 'Forbidden'
        r = call('POST', f'/admin/notifications/{s["registration_confirmed_notice"]}/retry', s[role])
        assert r.status_code == 403


def test_12_unset_payment_details(state):
    s = state
    payment = call('GET', '/admin/payment-settings', s['admin']).json()
    assert not payment.get('upi_id') and not payment.get('bank_details') and payment.get('amount') is None


def test_13_formula_and_arena_preservation(state):
    s = state
    result = call('GET', '/admin/results', s['admin']).json()['consolidated']
    assert result == {'configured': False, 'rows': []}
    arena = call('GET', '/arena/questions')
    assert arena.status_code == 200 and isinstance(arena.json(), list) and all('answer_index' not in x for x in arena.json())
    r = call('GET', '/arena/admin/questions', s['member'])
    assert r.status_code == 403 and 'detail' in r.json()
    assert call('GET', '/arena/admin/questions').status_code == 401
    assert isinstance(call('GET', '/arena/admin/questions', s['admin']).json(), list)


def test_14_upload_finalize_concurrency_immutability(state):
    s = state
    assert call('POST', f'/admin/projects/{s["sid"]}/reopen', s['admin']).status_code == 200
    before = project(s)
    # Real storage IO creates overlap: an upload accepted as draft must not update a finalized record.
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        upload = pool.submit(call, 'POST', '/projects/me/presentation', s['member'], files={'file': ('TEST_concurrent.pdf', PDF, 'application/pdf')})
        time.sleep(0.06)
        final = call('POST', '/projects/me/submit', s['team'])
        uploaded = upload.result()
    assert final.status_code == 200 and final.json()['status'] == 'submitted'
    current = project(s)
    print('Concurrent upload status:', uploaded.status_code, 'final document:', final.json()['presentation_file']['file_id'], 'current document:', current['presentation_file']['file_id'])
    assert current['status'] == 'submitted'
    if uploaded.status_code == 200 and final.json()['presentation_file']['file_id'] == before['presentation_file']['file_id']:
        assert current['presentation_file']['file_id'] == final.json()['presentation_file']['file_id'], 'Presentation changed after successful finalization: draft precheck + unconditional update race'
    else:
        assert uploaded.status_code in [200, 400], uploaded.text