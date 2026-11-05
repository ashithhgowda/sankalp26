# SANKALP'26 — PRD

## Original problem
Premium cinematic hackathon website for SANKALP'26 (IEEE AJIET SB, national-level 24-hour hackathon, 27–28 Nov 2026, ₹75,000 prize pool, AJIET Mangaluru). Landing/branding, team auth, submission portal (GitHub, demo, video pitch), judge evaluation, real-time leaderboard, admin dashboard. iOS-style glassmorphism, crazy cinematic tech theme, neon girl as the story of the theme, palette Jet Black #0A0A0A / Cerulean #007BA7 / Neon Rose #FF2D95. Full-screen logo reveal then neon-girl hero.

## User choices
JWT email+password auth · seeded admin + admin-created judges · submission fields: title, tagline, description, GitHub, demo, video, tech stack, category · all content sections · cinematic intro.

## Architecture
- FastAPI + Motor (server.py): auth (bcrypt, JWT cookie + Bearer, lockout via X-Forwarded-For), submissions, evaluations (4 criteria x 10), leaderboard (avg across judges, ties share rank), admin (overview, teams, judges CRUD, settings: phase + leaderboard_public)
- React + framer-motion + shadcn: Landing (Intro, Hero, Story scroll chapters, Tracks bento, Timeline, Prizes, Organisers, FAQ, Footer), /auth, /dashboard (team), /judge, /admin, /leaderboard (5s polling)
- Phases: registration → hackathon → evaluation (submissions lock) → results

## Implemented (Jun 2026)
- All of the above; tested by testing agent iteration_1 (backend 17/18 → lockout fixed; frontend 100%)

## Backlog
- P1: Abstract file upload (PDF/DOC ≤3MB) via object storage; email notifications (shortlist/accept)
- P1: Real prize split amounts (currently "Share of ₹75,000 pool")
- P2: Judge assignment per track, CSV export, certificates, password reset
