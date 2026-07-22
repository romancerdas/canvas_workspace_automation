# Overview

The software is a Canvas Workspace Automation web application that connects to the Canvas Learning Management System using a Personal Access Token. The application allows a user to select one of their Canvas courses, retrieve assignments and module information, generate a local folder structure for the course, and synchronize new or updated course information. The application also maintains a local JSON state to track synchronization history and avoid processing duplicate information.

The purpose of this software was to improve my understanding of REST APIs, bearer token authentication, web application development with Flask, JSON data persistence, scheduled synchronization, and working with external web services. It also provided experience designing a project that combines frontend and backend development into a single application.

[Software Demo Video](http://youtube.link.goes.here)

# Development Environment

The software was developed using Visual Studio Code on Windows. Development and testing were completed using Python's virtual environment, Git for version control, and Flask's built-in development server. The application communicates with the Canvas REST API over HTTPS and stores application configuration and synchronization data locally in JSON files.

The project was written in Python using the following libraries:

- Flask
- Requests
- APScheduler
- JSON (built-in)
- pathlib (built-in)
- os (built-in)
- datetime (built-in)

# Useful Websites

- [Canvas LMS REST API Documentation](https://canvas.instructure.com/doc/api/)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [Python Requests Documentation](https://requests.readthedocs.io/)
- [APScheduler Documentation](https://apscheduler.readthedocs.io/)
- [Python Official Documentation](https://docs.python.org/3/)

# Future Work

- Improve support for downloading course files and attachments when Canvas permissions allow access.
- Add OAuth authentication as an alternative to Personal Access Tokens.
- Improve synchronization by detecting changes to modules, pages, announcements, and course files while providing more detailed progress reporting.