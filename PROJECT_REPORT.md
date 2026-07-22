# Project Report

## Purpose

The application reduces repetitive Canvas checking by creating a local workspace for one course and reporting what changed since the previous synchronization.

## Requirements fulfilled

1. The user can provide a Canvas instance URL and manually generated access token.
2. The application authenticates through the Canvas REST API.
3. Active courses are listed in the web interface.
4. One course can be selected and persisted.
5. Course modules and assignments are retrieved.
6. A local course/module/assignment folder structure is generated.
7. Files attached as Canvas module file items are downloaded.
8. Canvas file IDs and update metadata prevent redundant downloads.
9. Configuration, selected course, last sync, and download history are stored in JSON.
10. A manual weekly-sync workflow and background weekly scheduler are included.
11. The dashboard reports new assignments, updated assignments, downloaded files, skipped files, and errors.
12. Invalid tokens, network failures, permissions, missing URLs, and unsafe filenames are handled.

## Stretch challenge

The change-detection layer is the stretch challenge. It compares stored assignment snapshots and file versions against the current Canvas response, then generates a categorized summary rather than blindly replacing all local content.

## Design

The Flask routes handle user interaction. `CanvasClient` isolates API calls and pagination. `SyncService` owns synchronization and filesystem behavior. `JsonStore` provides atomic local persistence. APScheduler invokes the same synchronization function used by the manual workflow.

## Security note

The token is local-only and excluded through `.gitignore`, but JSON is not encrypted. A production version should use environment variables, an OS credential store, or encrypted secret storage.
