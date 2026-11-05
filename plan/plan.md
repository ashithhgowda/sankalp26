# SANKALP'26 Phase 1 — Secure Core Hackathon Platform

Complete the existing SANKALP'26 website as a secure, reliable system for registration, selection, payment verification, project submission, and judging.
Preserve the established event identity and content while leaving the existing Arena unchanged until a separately approved Phase 2.

## Who it's for

- Public visitors learning about SANKALP'26 and its six official challenge topics.
- Team leaders registering teams and managing official team submissions.
- Invited team members activating individual accounts, following team progress, and collaborating on project submissions.
- Administrators managing participants, teams, applications, payments, timelines, submissions, judges, and security-relevant activity.
- Assigned judges completing separate intermediate and final evaluations.

## Core features and experience

### Official event experience
- Preserve the title “NATIONAL-LEVEL 24-HOUR HACKATHON (3rd Edition),” IEEE AJIET Student Branch and ECE Department attribution, AJIET Mangaluru venue, 27–28 November 2026 dates, logos, assets, and existing event sections.
- Preserve the six existing challenge topics and manage their titles, descriptions, order, and availability centrally.
- Display organizer-managed dates and portal states in India Standard Time.

### Secure individual accounts
- Provide email/password registration, login, logout, session renewal, password change, forgot-password, secure reset, and account activation.
- Require secure, single-use, time-limited activation and reset links.
- Require the existing seeded administrator to replace the initial password before accessing administrator tools.
- Keep participant, team leader, administrator, and judge permissions distinct and enforced for protected actions and private records.

### Team registration and invitations
- The team leader creates the team and their own individual account.
- The leader enters each member’s name, USN, email, and optional college.
- Each member receives an individual invitation, verifies their email, creates their own password, and signs in independently.
- Prevent duplicate emails, duplicate USNs, duplicate memberships, and unauthorized team changes.
- Show activation and invitation status to the leader and administrator, with secure resend and revocation controls.

### Abstract applications
- Allow the team leader to select one official topic and upload a PDF of up to 3 MB.
- Show a unique submission ID, timestamp, status, and history.
- Display `hackathon@ajiet.edu.in` as the manual email-submission option without reading the inbox automatically.
- Let administrators manually record email-based applications, review all applications, add notes, download private PDFs, and set Pending, Under Review, Selected, or Rejected status.
- Send selection or rejection email only when delivery succeeds and always keep the corresponding dashboard notification and delivery status.

### Selection, payment, and confirmation
- Use manual UPI or bank transfer only; no payment gateway is added.
- After selection, notify the team leader and reveal only organizer-configured payment instructions.
- Keep the QR code, UPI ID, bank details, amount, deadline, and instructions unset until an administrator provides them.
- Allow only the team leader to upload a receipt or screenshot, transaction reference, payment date, amount, and optional remarks.
- Keep payment-proof submission, administrator verification, and final registration approval as separate states and actions.
- Allow administrators to approve, reject, or request corrected proof, with reasons and history.
- Mark the team Registration Confirmed only after payment verification and an additional explicit administrator approval.
- Show the confirmed team status to every activated team member while sending payment and final-confirmation emails to the leader by default.

### Project submission
- Restrict the project portal to eligible, confirmed teams and enforce organizer-controlled opening and closing dates on the server.
- Collect project title, description, GitHub repository, demonstration link, presentation or documentation, and an optional video link.
- Provide an “Additional Deliverables (Optional)” area for multiple files or external resources with custom titles and descriptions.
- Let every activated team member collaborate on the project draft and its files.
- Lock the project after final submission.
- Allow an authorized administrator to reopen a finalized team submission, with the unlock and subsequent changes recorded in the activity history.
- Keep each team’s project and files private from other teams.

### Administration
- Provide one centralized workspace for participants, teams, topics, abstract applications, notifications, manual payments, event timeline, projects, judging, and activity history.
- Record important administrative actions, status changes, payment decisions, timeline edits, topic edits, judging changes, and project unlocks.
- Keep private payment instructions and uploaded files unavailable through public or unauthorized routes.

### Two-phase judging
- Keep Phase 1 Intermediate/Midnight Evaluation and Phase 2 Final Evaluation as independent records.
- Let administrators configure criteria, maximum marks, weightage, phase availability, judge assignments, evaluation locking, and authorized reopening.
- Restrict judges to assigned teams and assigned phases.
- Allow Phase 1 evaluation while an eligible team is still working on its project draft; require a finalized project for Phase 2.
- Preserve individual judge scores and prior submitted evaluations.
- Show separate phase results before a scoring formula exists.
- Do not calculate or display a consolidated score until an administrator saves the organizer-approved formula.

### Security baseline
- Keep secrets out of browser code, repositories, logs, and public responses.
- Use secure password hashing, short-lived sessions, refresh rotation, session revocation, brute-force protection, and generic recovery responses.
- Validate and constrain all server inputs, reject dangerous URLs, and avoid rendering untrusted HTML.
- Enforce ownership and role checks for every private team, payment, file, submission, and evaluation operation.
- Validate actual file contents, enforce size and type limits, generate safe storage paths, and authorize every download.
- Apply approved-origin CORS, CSRF protection where browser cookies are used, security headers, safe production errors, disabled public diagnostics, and no production source maps.
- Maintain a clear distinction between reviewed safeguards and anything that would require an external penetration test or production infrastructure verification.

## User flow

1. A visitor reviews the official event information, timeline, and six challenge topics.
2. A team leader registers an individual account and team, then enters the invited members.
3. The leader verifies their email; each member separately activates their invitation and creates a private password.
4. The leader submits the team’s abstract PDF or sends it manually to the official email address for administrator entry.
5. An administrator reviews the application and records a selection or rejection decision.
6. A selected team leader receives a dashboard notification and, when available, an email directing them to payment instructions.
7. The leader pays manually and uploads proof; an administrator independently verifies it, then separately confirms registration.
8. All activated members see the confirmed team status and may collaborate on the project draft while the portal is open.
9. The team finalizes the project; an administrator may reopen it only through an audited unlock action.
10. Assigned judges complete the open evaluation phases without accessing unassigned teams.
11. Administrators review separate phase results and may enable consolidated results only after saving the approved scoring formula.

## UI/UX feel

- Preserve the existing premium futuristic identity, dark glassmorphism, neon cyan and magenta accents, typography, imagery, and meaningful motion.
- Prioritize clear status language, readable forms, responsive layouts, keyboard access, validation, loading feedback, success confirmation, and actionable error messages.
- Keep major workflows separated into focused dashboard sections rather than crowding them into one view.
- Ensure every visible command performs a real action and every unavailable feature clearly explains its current state.
- Keep Arena visually and functionally unchanged during Phase 1.

## Implementation phases

### Phase 1 — Core website MVP (built now)
- Official public event experience and six managed topics.
- Secure individual authentication, activation, recovery, and role protection.
- Team registration, member invitations, and independent accounts.
- Abstract upload, manual email records, review, selection, rejection, and notifications.
- Manual payment instructions, proof, verification, correction, and explicit registration confirmation.
- Organizer-managed timeline and portal availability.
- Collaborative project drafts, optional deliverables, final lock, and audited administrator reopening.
- Central administrator controls, private files, audit history, and two-phase assigned judging.
- Security hardening across accounts, APIs, browser behavior, private data, uploads, dependencies, and production-facing responses.

### Phase 2 — Arena (not built now)
- Review the preserved existing quiz-based Arena only after explicit approval.
- Any future game, XP, leaderboard, or Arena redesign requires a separate scope and approval.

### Phase 3 — Post-event operations (not built now)
- Organizer-approved result publication, certificates, archival exports, retention policies, and post-event reporting.
- Any additions remain separate from Phase 1 acceptance.

## Assumptions

- The existing official team-size limit remains unchanged; the current maximum is three people including the leader.
- Only the leader controls team registration, abstract submission, and payment-proof submission.
- Every activated member may edit the team’s project draft and additional deliverables.
- A finalized project is immutable unless an administrator performs an audited unlock.
- Selection and payment emails go to the team leader by default; other members rely on their dashboards unless organizers later enable wider email distribution.
- Manual email submissions are entered by administrators and are never fetched from Gmail or another inbox.
- No payment amount, UPI ID, QR code, bank details, or payment instructions are invented or prefilled.
- Payment evidence never causes automatic approval or registration confirmation.
- Official hackathon dates remain 27–28 November 2026; other editable deadlines use existing values until an administrator changes them.
- Phase weights, averaging rules, number of judges, and final score calculations remain unconfigured until organizers approve them.
- Multi-factor authentication is not added unless the current account system already supports it without a new paid service.
- The existing managed email and private-file services remain the approved integrations; failed email delivery is recorded honestly and dashboard notifications remain available.
- Phase 1 does not include Arena enhancements, automatic inbox reading, a payment gateway, or invented judging policy.