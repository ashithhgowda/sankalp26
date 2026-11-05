# Authentication verification playbook

## Database checks
- Confirm `users.email` and `users.usn` uniqueness where values exist.
- Confirm bcrypt hashes start with `$2b$` and plaintext passwords are never stored.
- Confirm TTL indexes exist for password-reset, invitation, session, and rate-limit expiry fields.
- Confirm seeded accounts are not overwritten during application restart.

## API checks
- Register a leader, verify their email, and confirm their protected access.
- Activate invited members through single-use, time-limited links and create separate passwords.
- Verify login returns HttpOnly access and refresh cookies plus a CSRF token.
- Verify `/api/auth/me`, refresh, logout, password change, forgot-password, and reset-password.
- Verify repeated failed login attempts return 429 without revealing whether an email exists.
- Verify password changes and resets revoke earlier sessions.
- Verify inactive users, participants, judges, and administrators cannot cross role boundaries.

## Browser checks
- Verify loading, validation, success, expired-token, and invalid-token states.
- Verify the forced initial password-change screen blocks administrator tools until completion.
- Verify the browser uses HttpOnly cookies rather than persisting access tokens in local storage.