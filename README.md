# SANKALP 2026

SANKALP 2026 is a web-based event and hackathon management platform. It
supports team registration, challenge-topic selection, abstract
submission, administrative review, judging, and event updates.

## Project Architecture

The application is split into three main parts:

  -----------------------------------------------------------------------
  Layer                   Technology              Responsibility
  ----------------------- ----------------------- -----------------------
  Frontend                React                   Public landing page,
                                                  team/member dashboards,
                                                  judge dashboard and
                                                  admin control center

  Backend                 Python, FastAPI         Authentication,
                                                  registration,
                                                  application workflows,
                                                  administration and file
                                                  APIs

  Database                MongoDB Atlas           Users, teams,
                                                  registrations,
                                                  applications and
                                                  related records

  File storage            MongoDB GridFS          Stores abstract PDF
                                                  files in the existing
                                                  MongoDB database

  Frontend hosting        Vercel                  Hosts the React
                                                  application

  Backend hosting         Render                  Hosts the FastAPI API
  -----------------------------------------------------------------------

The frontend communicates with the FastAPI backend through the
configured API base URL. The backend connects to MongoDB Atlas using
environment variables.

## Main Features

### Team and participant features

-   Team registration and login.
-   Team leader and participant account handling.
-   Challenge-topic selection.
-   Abstract PDF submission.
-   Team dashboard and activity history.
-   Account activation and password recovery.

### Admin features

-   Overview of teams, participants, applications and event activity.
-   People management, including registration confirmation and account
    status.
-   Challenge-topic management.
-   Abstract review with Pending, Under Review, Selected and Rejected
    states.
-   Administrative activity updates visible to relevant team leaders.
-   Protected abstract PDF downloads.
-   Team and participant management.

### Judge features

-   Judge dashboard and assigned judging workflows.
-   Access controlled by backend authorization.

### Abstract file storage

-   Abstract PDFs are stored in MongoDB Atlas using GridFS.
-   MongoDB records retain file metadata and the associated GridFS file
    ID.
-   Abstract downloads are served through a protected backend endpoint.
-   Abstract files are not intended to be publicly accessible.

## Repository Structure

The repository contains separate frontend and backend directories. The
exact structure may evolve as the project is updated.

``` text
sankalp26-main/
├── backend/
│   ├── server.py
│   ├── phase1.py
│   ├── core_utils.py
│   ├── arena.py
│   └── ...
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   └── pages/
│   ├── package.json
│   └── ...
├── .gitignore
└── README.md
```

## Prerequisites

Install the following before running the project locally:

-   Python 3.11 (or a compatible version supported by the backend
    dependencies).
-   Node.js and npm.
-   A MongoDB Atlas cluster and database.
-   Git.

## Local Setup

### 1. Clone the repository

``` bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd sankalp26-main
```

### 2. Configure the backend

Create or update the backend environment file using the project's
expected environment-variable names. Do not commit real credentials.

At minimum, the backend deployment requires the MongoDB connection
settings:

``` env
MONGO_URL=<YOUR_MONGODB_ATLAS_CONNECTION_STRING>
DB_NAME=<YOUR_DATABASE_NAME>
```

The email integration may also require the existing email-related
environment variables and `INTEGRATION_PROXY_URL`, depending on the
current `emailer.py` implementation.

Set the frontend URL used when generating account activation or
password-reset links:

``` env
FRONTEND_URL=http://localhost:3000
```

Use the actual local frontend origin and the production frontend URL in
their respective environments. Check `backend/.env.example` for the
complete, current list of required variables.

**Secrets must remain server-side.** Never put MongoDB credentials,
email secrets or other private keys in React environment variables or
commit them to Git.

### 3. Install backend dependencies

From the repository root, create and activate a virtual environment:

**Windows PowerShell**

``` powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the backend requirements:

``` powershell
pip install -r backend/requirements.txt
```

If the requirements file is located elsewhere in your checkout, use the
path shown by the repository.

### 4. Run the backend

From the repository root:

``` powershell
python -m uvicorn backend.server:app --reload --host 127.0.0.1 --port 8000
```

The API should be available at:

-   API: `http://127.0.0.1:8000`
-   Interactive API documentation, if enabled:
    `http://127.0.0.1:8000/docs`

If startup fails, inspect the traceback and verify that all required
environment variables and Python dependencies are configured.

### 5. Configure and run the frontend

Open a second terminal:

``` bash
cd frontend
npm install
```

Set the frontend API base URL using the environment-variable name
expected by the existing frontend code. Point it to the local FastAPI
server during local development:

``` text
http://127.0.0.1:8000
```

Then run the script defined in `frontend/package.json`. For example, if
the project defines a `start` script:

``` bash
npm start
```

If it defines a `dev` script instead:

``` bash
npm run dev
```

Use the script actually present in `package.json`.

## Deployment

### Frontend --- Vercel

1.  Import the frontend project/repository into Vercel.
2.  Configure the frontend's production API base URL to point to the
    deployed Render backend.
3.  Add only frontend-safe environment variables.
4.  Deploy and verify the production build.

### Backend --- Render

1.  Create or select the FastAPI web service.
2.  Configure the build and start commands to match the repository
    layout.
3.  Add the required backend environment variables, including
    `MONGO_URL`, `DB_NAME`, the production `FRONTEND_URL`, and required
    email configuration.
4.  Ensure the backend CORS configuration allows the production Vercel
    origin.
5.  Deploy and check the service logs.

### Database and files --- MongoDB Atlas

-   Configure Atlas network access to permit connections from the
    deployed backend.
-   Use a database user with only the permissions the application needs.
-   Keep the connection string private.
-   Abstract PDF binaries are stored through GridFS in the configured
    database.
-   Back up the database and understand the retention requirements
    before deleting production records.

## Security Notes

-   Keep secrets in local environment files and hosting-provider
    environment settings.
-   Do not commit `.env` files.
-   Keep abstract PDFs private; serve them only through authenticated
    and authorized backend routes.
-   Enforce role checks in the backend, not only by hiding frontend
    controls.
-   Use secure, single-use, time-limited password-reset tokens.
-   Validate uploaded file types and sizes on the backend.
-   Confirm the target team and associated records before performing
    destructive admin actions.

## Testing Checklist

Before opening the platform to participants, test the deployed
application end to end:

-   [ ] Team registration and login.
-   [ ] Account activation and password reset using a real email
    mailbox.
-   [ ] Challenge-topic selection.
-   [ ] Abstract PDF upload to MongoDB GridFS.
-   [ ] Abstract metadata association with the correct team and topic.
-   [ ] Admin abstract download and unauthorized-download rejection.
-   [ ] Abstract replacement and cleanup of the previous GridFS file.
-   [ ] Registration confirmation and participant account
    activation/deactivation.
-   [ ] Abstract review status changes and team leader activity updates.
-   [ ] Judge access and role permissions.
-   [ ] Mobile layout and workflows in a real mobile browser.

## Troubleshooting

### Backend cannot import a module

Check the traceback, confirm the module exists, and use an import path
consistent with the Python package structure. Run Uvicorn from the
repository root when using `backend.server:app`.

### MongoDB connection fails

Verify `MONGO_URL`, `DB_NAME`, Atlas database-user credentials, and
Atlas network access settings.

### Frontend cannot reach the API

Verify that the frontend API base URL points to the correct backend. On
a deployed site, do not use `localhost` as the backend URL. Check Render
logs and backend CORS settings.

### Abstract upload or download fails

Check the backend logs, MongoDB connectivity, GridFS operations,
file-size/type validation, and the authenticated user's role. Do not
treat a frontend success message as proof that the file was saved.

## Maintenance

-   Keep dependencies updated deliberately and test before deploying.
-   Review Render logs after deployments.
-   Monitor MongoDB Atlas storage and backup health.
-   Test critical registration, upload, download and password-recovery
    workflows after changes.
-   Avoid committing credentials, uploaded PDFs or local build
    artifacts.

------------------------------------------------------------------------

**Note:** This README describes the architecture and workflows
established during project development. Confirm environment-variable
names, package scripts, deployment commands and optional integrations
against the current repository before using it as the sole deployment
guide.
