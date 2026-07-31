# Project Planner

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
- Shared task board with tasks grouped by status, owner, role, or workflow stage.
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

- SQLite for MVP.
- PostgreSQL for production.

### File Storage

- Local storage for MVP.
- SharePoint or Azure Blob Storage in the future.

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

