<<<<<<< HEAD
ď»ż# Project Planner
=======
ď»ż# Engineering Project Planner
>>>>>>> origin/master

Project Planner is an application for managing new product introductions, engineering changes, and tooling transfers in a manufacturing company specializing in metal stamping.

## Project Goal

The application supports complete project workflow management by helping teams:

- Guide users through standardized engineering and manufacturing workflows.
- Track project status, ownership, deadlines, and blockers.
- Centralize schedules, files, checklists, and document links.
- Automate notifications when new tasks become available.
- Maintain a complete project history.
- Generate project summary reports.

## Problem Statement

Many project activities are currently handled manually. Information is scattered across files, emails, and disconnected sources, making it difficult to track progress, identify delays, and understand project readiness.

This application aims to make the full workflow visible, repeatable, and easier to control.

## Minimum Viable Product

### Project Types

- New Product Introduction
- Engineering Change
- Tool Transfer

### User Roles

- Project Manager
- Manufacturing Engineer
- Quality Engineer
- Purchasing
- Logistics
- Technical Director

### Core Features

1. Create a new project.
2. Upload a project schedule as a file or image.
3. Select the project type.
4. Generate a dynamic workflow based on the project type.
5. Manage tasks with owner, due date, and status.
6. Complete role-based checklists.
7. Attach files or document links.
8. Send email notifications when subsequent tasks are unlocked.
9. Provide role-based task visibility.
10. Display a management dashboard.
11. Export the project summary to PDF.

### Task Visibility

Each role should have clear visibility of its own assigned tasks, deadlines, statuses, and blockers.

All roles should also be able to see the tasks assigned to other roles in a shared project board, similar to Microsoft Teams Planner or Trello. This shared view should make ownership, dependencies, progress, and blocked work transparent across the full project team.

## Example Workflow

### Stage 1: Project Setup

- Create project.
- Upload Purchase Order.
- Upload project schedule.

### Stage 2: Feasibility Review

- Manufacturing Engineer checklist.
- Quality Manager approval.
- Technical Director approval.

### Stage 3: Documentation Preparation

These activities can run in parallel:

- Prepare manufacturing process documentation.
- Prepare packaging documentation.
- Prepare quality documentation.
- Create Control Plan.
- Prepare CMM measurement program.

### Stage 4: Purchasing and Logistics

After project schedule approval:

- Complete purchasing activities.
- Complete logistics activities.
- Verify packaging and containers.
- Plan delivery.

### Stage 5: Project Closure

- Close the project.
- Generate PDF report.
- Notify stakeholders that production is ready to start.

## Dashboard

The dashboard should display:

- All projects.
- Status of each project.
- Project completion percentage.
- Shared task board with tasks grouped by workflow column/status, owner, or role.
- My Tasks view for the currently selected role or user.
- Delayed projects.
- Blocked projects.
- Reason for blockage.
- Upcoming deadlines.

## Proposed Architecture

### Frontend

- Streamlit

### Backend

- Python

### Database

The application should use PostgreSQL as the persistent project database when deployed on local company servers. SQLite can still be useful for early prototypes, but PostgreSQL is the preferred MVP/production database because the planner is shared by multiple users and needs centralized task history, comments, checklist state, due date changes, and reporting data.

Recommended local-server setup:

```text
User browser
  -> Streamlit Project Planner app
  -> Local PostgreSQL server
  -> Shared local file storage for attachments
```

Recommended PostgreSQL objects:

- `projects`: project ID, project name, project type, status, customer, start date, target date, blockage reason, project color.
- `workflow_columns`: configurable board columns such as Open RFQ, Review RFQ, Offer Calculation, In Progress, Completed, or Rejected.
- `tasks`: title, project reference, responsible row/role, workflow column/status, due date, description, created date, completed date.
- `task_responsibles`: one task linked to one or more responsible email addresses.
- `people`: available responsible people and email addresses.
- `checklist_items`: task checklist text, completion state, completed by, completed date.
- `comments`: task comments with author and timestamp.
- `activity_log`: full task/project history such as due date changes, column moves, checklist updates, and file attachments.
- `attachments`: file metadata and document links connected to projects or tasks.

Example environment variables:

```text
DB_HOST=local-server-name
DB_PORT=5432
DB_NAME=project_planner
DB_USER=project_planner_app
DB_PASSWORD=secure_password
```

The database should store attachment metadata, not large uploaded files. Uploaded files should be stored in a controlled local/shared folder and referenced from PostgreSQL.

### File Storage

- Local or shared server folder for MVP, for example `\\server\ProjectPlannerAttachments`.
- PostgreSQL stores file names, paths, task/project references, uploader, and upload date.
- SharePoint or Azure Blob Storage can be added in the future.

### Notifications

- SMTP email.

## Roadmap

### Version 1

- Core workflow.
- Dashboard.
- PDF export.
- Email notifications.

### Version 2

- User authentication.
- Roles and permissions.
- ERP integration.

### Version 3

- KPI dashboards.
- AI-powered risk analysis.
- Automatic schedule recommendations.
- Outlook and Microsoft Teams integration.

## Next Steps

1. Design the complete workflow.
2. Create UI wireframes.
3. Design the database.
4. Build the product backlog and user stories.
5. Implement the solution using Python and Streamlit.

