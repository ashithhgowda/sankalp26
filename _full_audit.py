"""
Full audit of all original requirements vs current implementation.
"""
import re, os

def read(path):
    try:
        with open(path, encoding='utf-8', errors='replace') as f:
            return f.read()
    except FileNotFoundError:
        return ""

server   = read("backend/server.py")
phase1   = read("backend/phase1.py")
auth_ctx = read("frontend/src/context/AuthContext.jsx")
app_js   = read("frontend/src/App.js")
auth_pg  = read("frontend/src/pages/AuthPage.jsx")
admin_db = read("frontend/src/pages/AdminDashboard.jsx")
team_db  = read("frontend/src/pages/TeamDashboard.jsx")
people   = read("frontend/src/pages/admin/PeoplePanels.jsx")
payments_panel = read("frontend/src/pages/admin/PaymentsPanel.jsx")
payment_panel  = read("frontend/src/components/dashboard/PaymentPanel.jsx")
abstract_panel = read("frontend/src/components/dashboard/AbstractPanel.jsx")
notif_panel    = read("frontend/src/components/dashboard/NotificationsPanel.jsx")
story    = read("frontend/src/components/landing/Story.jsx")
navbar   = read("frontend/src/components/Navbar.jsx")
hero     = read("frontend/src/components/landing/Hero.jsx")
tracks   = read("frontend/src/components/landing/Tracks.jsx")
dash_shell = read("frontend/src/components/DashShell.jsx")
index_css  = read("frontend/src/index.css")

results = []

def chk(label, condition, critical=False):
    status = "OK  " if condition else ("FAIL" if critical else "WARN")
    results.append((status, label))

# ── Registration & Auth ────────────────────────────────────────────────────
chk("REG: register endpoint has Response param", 'async def register(body: RegisterIn, request: Request, response: Response)' in server, True)
chk("REG: leader is_active=True on register", '"is_active": True, "email_verified": True' in server, True)
chk("REG: team status=registered on register", '"registration_status": "registered"' in server, True)
chk("REG: auto-login after register (issue_session)", 'issue_session(response, leader_user, request)' in server, True)
chk("REG: welcome notification sent", 'registration_success' in server, True)
chk("AUTH: require() has no must_change_password block", 'must_change_password' not in server.split('def require(')[1].split('return dependency')[0])
chk("AUTH: seed_user must_change_password=False", 'must_change_password=False' in server, True)
chk("AUTH: login auto-activates legacy pending accounts", 'Auto-activate accounts' in server, True)
chk("AUTH: frontend register calls accept() (auto-login)", 'register.*accept' in auth_ctx)
chk("AUTH: App.js no must_change_password redirect", 'must_change_password' not in app_js)
chk("AUTH: AuthPage register redirects to dashboard", 'homeFor(u.role)' in auth_pg)
chk("AUTH: AuthPage member description updated", 'activation link' not in auth_pg)

# ── Admin ──────────────────────────────────────────────────────────────────
chk("ADMIN: Activity/security tab removed from TABS", 'ShieldAlert' not in admin_db and '"security"' not in admin_db.split('const TABS')[1].split(';')[0], True)
chk("ADMIN: SecurityPanel TabsContent removed", '<SecurityPanel' not in admin_db, True)
chk("ADMIN: audit-log fetch removed", 'audit-log' not in admin_db, True)
chk("ADMIN: People panel has YES/NO selection", 'SelectionToggle' in people or 'selected: select' in people, True)
chk("ADMIN: People panel has abstract column", 'AbstractBadge' in people or 'abstract' in people.lower(), True)
chk("ADMIN: People panel passes onReload to TeamsPanel", 'onReload={load}' in admin_db and 'TeamsPanel' in admin_db, True)

# ── Phase1 backend ─────────────────────────────────────────────────────────
chk("PHASE1: TeamSelectionIn class", 'class TeamSelectionIn' in phase1, True)
chk("PHASE1: /admin/teams/{team_id}/selection endpoint", '/admin/teams/{team_id}/selection' in phase1, True)
chk("PHASE1: selection notification to leader", 'team_selected' in phase1, True)
chk("PHASE1: admin-selection upserts application (not insert_one)", 'upsert=True' in phase1.split('set_team_selection')[1].split('return router')[0], True)
chk("PHASE1: participant_dashboard checks reg_status for payment", 'selected_awaiting_payment' in phase1, True)
chk("PHASE1: setup_phase1 migrates email_verification_pending", 'email_verification_pending' in phase1, True)
chk("PHASE1: setup_phase1 activates legacy is_active=False users", 'is_active.*False' in phase1)

# ── PaymentPanel (team dashboard) ──────────────────────────────────────────
chk("PAYMENT: PaymentPanel receives team prop", 'team={data.team}' in team_db, True)
chk("PAYMENT: isPaymentEligible checks team.registration_status", 'isPaymentEligible' in payment_panel, True)
chk("PAYMENT: Congratulations banner shown on selection", 'Congratulations' in payment_panel, True)
chk("PAYMENT: QR image/download rendered", 'PrivateImage' in payment_panel, True)
chk("PAYMENT: proof upload form present", 'payment-proof-form' in payment_panel, True)

# ── Admin Payments Panel ───────────────────────────────────────────────────
chk("ADMIN_PAY: approve/reject actions present", 'approve' in payments_panel and 'reject' in payments_panel, True)
chk("ADMIN_PAY: payment proof download", 'downloadFile' in payments_panel or 'Secure proof' in payments_panel, True)
chk("ADMIN_PAY: QR upload present", 'uploadQr' in payments_panel or 'Upload QR' in payments_panel, True)
chk("ADMIN_PAY: team name displayed", 'team?.name' in payments_panel or 'payment.team' in payments_panel, True)

# ── Notifications ─────────────────────────────────────────────────────────
chk("NOTIF: NotificationsPanel renders notifications list", 'notifications-panel' in notif_panel, True)
chk("NOTIF: mark-read button present", 'Mark read' in notif_panel, True)
chk("NOTIF: selection notification in phase1", 'team_selected' in phase1, True)
chk("NOTIF: payment-approved notification in phase1", 'payment_verified' in phase1 or 'Payment verified' in phase1, True)
chk("NOTIF: registration-success notification in server.py", 'registration_success' in server, True)

# ── Mobile responsiveness ─────────────────────────────────────────────────
chk("MOBILE: Story has mobile layout (lg:hidden)", 'lg:hidden' in story, True)
chk("MOBILE: Story desktop hidden on mobile (lg:grid)", 'lg:grid' in story, True)
chk("MOBILE: Navbar hamburger menu present", 'nav-mobile-toggle' in navbar, True)
chk("MOBILE: Navbar mobile drawer with auth CTAs", 'nav-mobile-menu' in navbar and 'Register team' in navbar, True)
chk("MOBILE: DashShell nav wraps on mobile", 'order-3' in dash_shell or 'flex-wrap' in dash_shell, True)
chk("MOBILE: overflow-x hidden in global CSS", 'overflow-x: hidden' in index_css, True)
chk("MOBILE: Select dropdown z-index fix", 'z-index: 9999' in auth_pg or 'zIndex: 9999' in auth_pg, True)
chk("MOBILE: Hero reduced padding on mobile", 'pt-24' in hero or 'pt-20' in hero, True)
chk("MOBILE: Tracks grid mobile-first", 'grid-cols-1' in tracks, True)

# ── CSP & API ─────────────────────────────────────────────────────────────
chk("CSP: localhost connect-src added for dev", 'localhost:*' in server, True)
chk("API: /public/meta endpoint exists", 'async def meta' in phase1 or 'public_meta' in phase1, True)
chk("API: CORS_ORIGINS env var used", 'CORS_ORIGINS' in server, True)

# ── Abstract upload ────────────────────────────────────────────────────────
chk("ABSTRACT: submit_abstract endpoint in phase1", 'async def submit_abstract' in phase1, True)
chk("ABSTRACT: AbstractPanel upload form present", 'abstract-submit-button' in abstract_panel, True)
chk("ABSTRACT: AdminPanel shows abstract download", 'Download PDF' in read("frontend/src/pages/admin/ApplicationsPanel.jsx"), True)

print("\n=== AUDIT RESULTS ===\n")
fails = [r for r in results if r[0] == "FAIL"]
warns = [r for r in results if r[0] == "WARN"]
oks   = [r for r in results if r[0] == "OK  "]

for status, label in results:
    print(f"  {status}  {label}")

print(f"\n  Total: {len(oks)} OK, {len(warns)} WARN, {len(fails)} FAIL")
