# REMAINING WORK (checked against original prompt)

## DONE
- [x] Registration: auto-activate, auto-login, no email verification required
- [x] Login: auto-activate legacy pending accounts
- [x] Admin: no forced password change (seed_user + require() fixed)
- [x] Admin Dashboard: Activity/Security section removed
- [x] Admin People: YES/NO selection controls with notifications
- [x] Admin People: Abstract column showing file status
- [x] Mobile: Story section - alternating mobile layout, desktop unchanged
- [x] Mobile: Navbar - hamburger, outside-click close, full CTAs in drawer
- [x] Mobile: Hero - responsive font sizes, proper spacing
- [x] Mobile: global CSS - overflow-x fix, z-index fixes, Select dropdown z-index, tap targets, 16px font on inputs
- [x] Mobile: DashShell - nav wraps cleanly on 320px

## REMAINING

### Phase 4: Auth page mobile (registration form)
- [ ] Register form: overflow-visible on card so Select portal is not clipped on WebKit
- [ ] Member description text: remove "each member receives activation link" (no longer true) 
- [ ] Register form overall: verify responsive on 320px/375px (grid, spacing)

### Phase 5: Team Dashboard - complete notification for selection
- [ ] Verify dashboard shows selection status and payment tab activates when selected
- [ ] NotificationsPanel: confirm persistent, linked to user_id

### Phase 6: Admin Teams endpoint - return abstract in team data  
- [ ] /admin/teams already fetches `application` per team - verify abstract file info is included
- [ ] Test that PeoplePanels AbstractBadge gets the file_id from team.application.file

### Phase 7: Payment workflow verification
- [ ] Verify QR code file is served via /files/{file_id} correctly
- [ ] PaymentPanel: QR image visible when settings.qr_file exists
- [ ] Payment settings endpoint: returns qr_file correctly

### Phase 8: Mobile responsiveness - remaining components
- [ ] Tracks section: cards on 320px
- [ ] Registration form: member sections on mobile
- [ ] Admin dashboard tabs: scrollable on 320px
- [ ] TeamDashboard tabs: scrollable on 320px
- [ ] PaymentPanel: responsive on mobile
- [ ] AbstractPanel: responsive on mobile

### Phase 9: API/CSP fixes
- [ ] Content-Security-Policy: connect-src must allow localhost for dev
- [ ] Verify /public/meta returns topics (6 challenge cards load)
- [ ] CORS origins matches frontend URL

### Phase 10: Database
- [ ] Ensure topics are seeded (6 challenges must exist)
- [ ] Admin endpoint: topics seed check in setup_phase1
