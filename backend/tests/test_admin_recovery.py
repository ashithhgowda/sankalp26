"""Non-destructive recovery checks; never replace the protected one-time password."""
import hashlib
import json
import os
from pathlib import Path
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
import pytest
import requests
from dotenv import dotenv_values
from pymongo import MongoClient


def check(condition, message):
    if not condition:
        pytest.fail(message, pytrace=False)


@pytest.fixture(scope='module')
def recovery():
    # Read credential guidance, but authenticate only from the protected environment.
    guidance = Path('/app/memory/test_credentials.md')
    check(guidance.exists() and bool(guidance.read_text().strip()), 'Credential guidance missing')
    env = dotenv_values('/app/backend/.env')
    front = dotenv_values('/app/frontend/.env')
    os.environ['REACT_APP_BACKEND_URL'] = front['REACT_APP_BACKEND_URL']
    client = MongoClient(env['MONGO_URL'])
    db = client[env['DB_NAME']]
    email = env['ADMIN_EMAIL'].strip().lower()
    user = db.users.find_one({'email': email})
    check(user is not None, 'Administrator missing')
    before = (user['password_hash'], user.get('session_version'), user.get('must_change_password'))
    session = requests.Session()
    state = {'env': env, 'base': os.environ['REACT_APP_BACKEND_URL'].rstrip('/'), 'db': db,
             'user': user, 'email': email, 'session': session}
    yield state
    csrf = session.cookies.get('csrf_token')
    if session.cookies.get('access_token'):
        result = session.post(state['base'] + '/api/auth/logout', headers={'X-CSRF-Token': csrf or ''}, timeout=30)
        check(result.status_code == 200 and result.json().get('ok') is True, 'Cleanup logout failed')
    after = db.users.find_one({'_id': user['_id']})
    check(before == (after['password_hash'], after.get('session_version'), after.get('must_change_password')), 'Recovery state changed during testing')
    check(db.sessions.count_documents({'user_id': str(user['_id']), 'revoked_at': None}) == 0, 'Authenticated session remains')
    session.close()
    client.close()


def test_01_single_active_admin(recovery):
    r = recovery
    check(r['db'].users.count_documents({'email': r['email']}) == 1, 'Duplicate matching administrator')
    check(r['user']['role'] == 'admin' and r['user']['is_active'] is True and r['user']['email_verified'] is True, 'Administrator role/status incorrect')
    check(r['user']['must_change_password'] is True, 'Forced replacement is not enabled')


def test_02_protected_password_hash(recovery):
    r = recovery
    check(r['user']['password_hash'].startswith('$2b$'), 'Unexpected bcrypt format')
    check(bcrypt.checkpw(r['env']['ADMIN_PASSWORD'].encode(), r['user']['password_hash'].encode()), 'Protected one-time password does not match')


def test_03_sessions_and_lock_bucket(recovery):
    r = recovery
    check(r['db'].sessions.count_documents({'user_id': str(r['user']['_id']), 'revoked_at': None}) == 0, 'Prior active session remains')
    key = 'login-fail:' + hashlib.sha256(r['email'].encode()).hexdigest()
    check(r['db'].rate_limits.count_documents({'key': key}) == 0, 'Failed-login lock bucket remains')
    check(r['db'].login_attempts.count_documents({'identifier': r['email']}) == 0, 'Legacy login attempt remains')


def test_04_recovery_audits(recovery):
    r = recovery
    for action in ('admin.recovery_initiated', 'admin.recovery_flow_verified'):
        event = r['db'].audit_logs.find_one({'action': action, 'target_id': str(r['user']['_id'])}, sort=[('created_at', -1)])
        check(event is not None, 'Required recovery audit missing: ' + action)
        details = event.get('details', {})
        check(not any(any(word in key.lower() for word in ('password', 'hash', 'token', 'cookie', 'secret')) and not isinstance(value, bool) for key, value in details.items()), 'Secret-like recovery audit detail')
        if action.endswith('initiated'):
            check(details.get('sessions_revoked', 0) >= 64 and details.get('forced_password_change') is True, 'Recovery initiation flags incomplete')
        else:
            check(all(details.get(key) is True for key in ('login_verified', 'forced_change_verified', 'dashboard_access_verified', 'temporary_status_restored')), 'Recovery verification flags incomplete')


def test_05_prior_session_rejected(recovery):
    # Signed replay probes use revoked session IDs without revealing or storing tokens.
    r = recovery
    prior = r['db'].sessions.find_one({'user_id': str(r['user']['_id']), 'revoked_at': {'$ne': None}})
    check(prior is not None, 'No revoked session available to verify')
    now = datetime.now(timezone.utc)
    payload = {'sub': str(r['user']['_id']), 'sid': prior['sid'], 'type': 'access', 'sv': r['user'].get('session_version', 0), 'iat': now, 'exp': now + timedelta(minutes=2)}
    token = jwt.encode(payload, r['env']['JWT_SECRET'], algorithm='HS256')
    response = requests.get(r['base'] + '/api/auth/me', headers={'Authorization': 'Bearer ' + token}, timeout=30)
    check(response.status_code == 401 and response.json().get('detail') == 'Session is no longer active', 'Revoked session accepted')
    payload['sv'] -= 1
    token = jwt.encode(payload, r['env']['JWT_SECRET'], algorithm='HS256')
    response = requests.get(r['base'] + '/api/admin/overview', headers={'Authorization': 'Bearer ' + token}, timeout=30)
    check(response.status_code == 401 and response.json().get('detail') == 'Session is no longer active', 'Old session version accepted')


def test_06_login_and_httponly(recovery):
    r = recovery
    response = r['session'].post(r['base'] + '/api/auth/login', json={'email': r['email'], 'password': r['env']['ADMIN_PASSWORD']}, timeout=30)
    check(response.status_code == 200, 'One-time API login failed')
    data = response.json().get('user', {})
    check(data.get('email') == r['email'] and data.get('role') == 'admin' and data.get('must_change_password') is True, 'Login returned wrong account/state')
    check('password_hash' not in data, 'Password hash leaked in user response')
    for name in ('access_token', 'refresh_token'):
        cookie = next((c for c in response.cookies if c.name == name), None)
        check(cookie is not None and cookie.secure and cookie.has_nonstandard_attr('HttpOnly'), 'Authentication cookie missing secure/HttpOnly flag')


def test_07_forced_change_api_guards(recovery):
    r = recovery
    check(bool(r['session'].cookies.get('access_token')), 'No test session available')
    for path in ('/api/admin/overview', '/api/admin/teams', '/api/admin/topics', '/api/admin/audit-log', '/api/admin/projects', '/api/arena/admin/questions'):
        response = r['session'].get(r['base'] + path, timeout=30)
        check(response.status_code == 403 and response.json().get('detail') == 'Password change required before accessing this area', 'Forced-change guard failed: ' + path)
    response = r['session'].get(r['base'] + '/api/auth/me', timeout=30)
    check(response.status_code == 200 and response.json().get('must_change_password') is True, 'Security screen cannot read forced-change status')


def test_08_explicit_credentialed_cors(recovery):
    r = recovery
    response = requests.options(r['base'] + '/api/auth/login', headers={'Origin': r['base'], 'Access-Control-Request-Method': 'POST', 'Access-Control-Request-Headers': 'Content-Type'}, timeout=30)
    check(response.status_code == 200, 'Public-origin CORS preflight failed')
    check(response.headers.get('Access-Control-Allow-Origin') == r['base'] and response.headers.get('Access-Control-Allow-Credentials') == 'true', 'Explicit credentialed CORS is not configured')


def test_09_logout_and_state_preservation(recovery):
    r = recovery
    response = r['session'].post(r['base'] + '/api/auth/logout', headers={'X-CSRF-Token': r['session'].cookies.get('csrf_token', '')}, timeout=30)
    check(response.status_code == 200 and response.json().get('ok') is True, 'Logout failed')
    response = r['session'].get(r['base'] + '/api/auth/me', timeout=30)
    check(response.status_code == 401 and response.json().get('detail') == 'Not authenticated', 'Logout still authenticated')


def test_10_existing_login_ui(recovery):
    # Local Playwright keeps protected credentials out of remote tool arguments/logs.
    from playwright.sync_api import sync_playwright
    r = recovery
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path='/root/bin/chromium', headless=True, args=['--no-sandbox'])
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()
        page_errors = []
        page.on('pageerror', lambda error: page_errors.append(True))
        try:
            page.goto(r['base'] + '/auth?mode=login', wait_until='domcontentloaded')
            page.get_by_test_id('login-form').wait_for(state='visible', timeout=30000)
            page.get_by_test_id('login-email-input').fill(r['email'])
            page.get_by_test_id('login-password-input').fill(r['env']['ADMIN_PASSWORD'])
            page.get_by_test_id('login-submit-button').click(force=True)
            page.wait_for_url('**/account/security', timeout=30000)
            page.get_by_test_id('account-security-page').wait_for(state='visible')
            check(page.get_by_test_id('current-password-input').is_editable() and page.get_by_test_id('new-password-input').is_editable(), 'Forced-change inputs unusable')
            check(page.get_by_test_id('admin-dashboard').count() == 0, 'Admin tools shown before replacement')
            print('PASS: protected one-time login redirects to forced-change screen')
            page.goto(r['base'] + '/admin', wait_until='domcontentloaded')
            page.wait_for_url('**/account/security', timeout=30000)
            page.get_by_test_id('account-security-page').wait_for(state='visible')
            print('PASS: direct admin dashboard navigation blocked')
            page.set_viewport_size({'width': 390, 'height': 844})
            check(page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), 'Security screen overflows on mobile')
            page.screenshot(path='/app/test_reports/recovery_security_mobile.jpeg', quality=40, full_page=False)
            errors = page.evaluate("""() => { const errorElements = Array.from(document.querySelectorAll('.error, [class*="error"], [id*="error"]')); return errorElements.map(el => el.textContent).join(', '); }""")
            check(not errors and not page_errors, 'Recovery screen has error messages/page exceptions')
            check(not page.evaluate("localStorage.getItem('sk_token')"), 'Access token persisted in local storage')
            print('PASS: mobile security screen and browser secret-storage checks')
        except Exception:
            pytest.fail('Recovery UI flow failed; details suppressed to protect credentials', pytrace=False)
        finally:
            cookies = context.cookies()
            csrf = next((c['value'] for c in cookies if c['name'] == 'csrf_token'), '')
            if any(c['name'] == 'access_token' for c in cookies):
                result = context.request.post(r['base'] + '/api/auth/logout', headers={'X-CSRF-Token': csrf})
                check(result.status == 200 and result.json().get('ok') is True, 'Browser cleanup logout failed')
                result = context.request.get(r['base'] + '/api/auth/me')
                check(result.status == 401, 'Browser session survived logout')
                print('PASS: browser test session logged out')
            context.clear_cookies()
            context.close()
            browser.close()