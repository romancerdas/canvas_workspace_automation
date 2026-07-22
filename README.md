# Canvas Workspace Automation

A CSE 310 Module 6 “Choose Your Own Adventure” project that connects to Canvas with a manually generated API token, lists active courses, synchronizes one selected course, mirrors course resources into a local folder structure, and records sync state in JSON.

## Features

- Canvas REST API integration with bearer-token authentication
- Active-course listing and course selection in a Flask web interface
- Module and assignment retrieval
- Local folder generation for courses, modules, files, and assignments
- `assignment.md` generation with due date, points, URL, and description
- Downloads every accessible file from the Canvas **Files** area while preserving its folder hierarchy
- Downloads assignment attachments and files linked in assignment descriptions
- Downloads module file items that are not already present in the course Files area
- Duplicate/update detection using Canvas file IDs and remote update metadata
- JSON persistence for settings, selected course, last sync, and download history
- Manual “Run Weekly Sync Now” workflow
- Optional background weekly schedule through APScheduler
- Dashboard summary of new assignments, changed assignments, downloaded files, unchanged files, and warnings
- Error handling for invalid tokens, denied access, network failures, missing URLs, and file-system errors
- Automated tests using a fake Canvas client

## Technology

- Python 3.11+
- Flask
- Requests
- APScheduler
- Pytest

## Setup

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

Open `http://127.0.0.1:5000`.

## Canvas token

In Canvas, create a personal access token from **Account → Settings → Approved Integrations → New Access Token**. The exact menu can vary by institution. Enter the institution Canvas base URL and token on the Settings page.

The token is saved locally in `data/config.json`. That file is excluded from Git. Never commit or share the token.

## Use

1. Open **Settings** and save the Canvas URL, token, local download directory, weekday, and hour.
2. Open **Courses**, load active courses, and select one.
3. Return to **Dashboard** and choose **Run Weekly Sync Now**.
4. Inspect the selected download directory and the dashboard summary.

Generated structure:

```text
workspace/
└── Course Name/
    ├── README.md
    ├── Assignments/
    │   └── Assignment Name/
    │       └── assignment.md
    ├── Course Files/
    │   └── Canvas Folder/
    │       └── downloaded-resource.pdf
    ├── Assignments/
    │   └── Assignment Name/
    │       ├── assignment.md
    │       └── Attachments/
    │           └── assignment-resource.zip
    └── Modules/
        └── Module Name/
            └── module-only-resource.pdf
```

## JSON files

- `data/config.json`: Canvas URL, token, selected course, download directory, schedule
- `data/sync_state.json`: assignment snapshots, file IDs/versions, paths, last sync
- `data/last_summary.json`: latest dashboard summary

## Tests

```bash
pytest -q
```

## Scope and limitations

The project intentionally supports one selected course. It downloads files exposed by the Canvas Files API, module file items, and Canvas file links found in assignment descriptions. It does not scrape arbitrary external websites, implement OAuth, upload submissions, or send notifications. Those items were excluded to keep the minimum viable project aligned with the approved plan.

The scheduler reads its weekday and hour when the process starts. Restart the app after changing schedule settings. For reliable unattended scheduling, run the app on a machine or server that stays on.

## Learning outcomes

This project demonstrates REST API calls, bearer-token authentication, pagination, filesystem automation, safe filenames, JSON persistence, scheduled jobs, web routing/templates, change detection, defensive error handling, and automated testing.

## Suggested 4–5 minute demo outline

1. Explain the problem and approved scope.
2. Show Settings without revealing the token.
3. Load and select a Canvas course.
4. Run a sync and explain the dashboard counts.
5. Open generated assignment and module folders.
6. Run the sync again to demonstrate duplicate skipping.
7. Show `sync_state.json`, tests, and key learning outcomes.
