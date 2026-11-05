import re

with open('backend/server.py') as f:
    c = f.read()

checks = [
    ('register has Response param', r'async def register.*response: Response'),
    ('leader is_active True', r'"is_active": True'),
    ('team status registered (not email_verification_pending)', r'"registration_status": "registered"'),
    ('auto-login after register', r'issue_session\(response, leader_user, request\)'),
    ('welcome notification', r'registration_success'),
    ('seed_user must_change_password False', r'must_change_password=False'),
    ('auto-activate legacy accounts on login', r'Auto-activate accounts'),
]

req_block = c.split('def require(')[1].split('return dependency')[0] if 'def require(' in c else ''
checks.append(('require() has no must_change_password', 'must_change_password' not in req_block))

for label, pattern in checks[:-1]:
    ok = bool(re.search(pattern, c))
    print(('OK  ' if ok else 'FAIL') + '  ' + label)

label, ok = checks[-1]
print(('OK  ' if ok else 'FAIL') + '  ' + label)

with open('backend/phase1.py') as f:
    p1 = f.read()

p1_checks = [
    ('TeamSelectionIn class exists', r'class TeamSelectionIn'),
    ('admin/teams/{team_id}/selection endpoint', r'/admin/teams/\{team_id\}/selection'),
    ('selection notification', r'team_selected'),
]
print()
print('--- phase1.py ---')
for label, pattern in p1_checks:
    ok = bool(re.search(pattern, p1))
    print(('OK  ' if ok else 'FAIL') + '  ' + label)

print()
print('--- Frontend ---')
import os
files = {
    'AuthContext.jsx': 'frontend/src/context/AuthContext.jsx',
    'App.js': 'frontend/src/App.js',
    'AuthPage.jsx': 'frontend/src/pages/AuthPage.jsx',
    'AdminDashboard.jsx': 'frontend/src/pages/AdminDashboard.jsx',
    'PeoplePanels.jsx': 'frontend/src/pages/admin/PeoplePanels.jsx',
}
fe_checks = {
    'AuthContext.jsx': [('register auto-logs in (accept call)', r'register.*accept')],
    'App.js': [('must_change_password redirect removed', r'must_change_password')],
    'AuthPage.jsx': [('register redirects to dashboard', r'homeFor\(u\.role\)')],
    'AdminDashboard.jsx': [
        ('Activity/Security tab removed from TABS', lambda c: 'ShieldAlert' not in c and 'security' not in c.split('const TABS')[1].split(';')[0]),
        ('SecurityPanel tab content removed', lambda c: '<SecurityPanel' not in c),
        ('audit-log fetch removed', lambda c: 'audit-log' not in c),
    ],
    'PeoplePanels.jsx': [
        ('YES/NO selection control present', r'selection|Select'),
        ('abstract column present', r'abstract|Abstract'),
    ],
}
for fname, path in files.items():
    with open(path) as f:
        fc = f.read()
    for label, pattern in fe_checks.get(fname, []):
        if callable(pattern):
            ok = pattern(fc)
        else:
            ok = bool(re.search(pattern, fc, re.IGNORECASE))
        # For App.js must_change_password check, absence is good
        if fname == 'App.js' and 'must_change_password' in label:
            ok = not ok
        print(('OK  ' if ok else 'FAIL') + '  ' + fname + ': ' + label)
