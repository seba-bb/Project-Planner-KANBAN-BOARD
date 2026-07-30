# Engineering Workflow Manager - Action Plan

## Objective

Build an MVP application that helps manage new product introductions, engineering changes, and tooling transfers through structured workflows, task ownership, deadlines, document tracking, notifications, dashboards, and PDF reporting.

## Phase 1: Product Definition

### 1. Define the Complete Workflow

- Map the full workflow for each project type:
  - New Product Introduction
  - Engineering Change
  - Tool Transfer
- Define all stages, gates, approvals, and dependencies.
- Identify which tasks can run in parallel.
- Define what unlocks each next stage.
- Document required inputs and outputs for every stage.

### 2. Define User Roles and Responsibilities

- Confirm responsibilities for each role:
  - Project Manager
  - Manufacturing Engineer
  - Quality Engineer
  - Purchasing
  - Logistics
  - Technical Director
- Assign task ownership rules.
- Define approval authority for each workflow stage.
- Identify which users only need dashboard visibility.

### 3. Prepare Product Backlog

- Convert MVP features into user stories.
- Prioritize stories by business value and technical dependency.
- Mark must-have, should-have, and future features.
- Define acceptance criteria for each user story.

## Phase 2: UX and Data Design

### 4. Create UI Wireframes

- Design the main project dashboard.
- Design the project creation screen.
- Design the project detail view.
- Design task and checklist views.
- Design file attachment and document link sections.
- Design PDF export flow.

### 5. Design the Database

- Define database tables for:
  - Users
  - Roles
  - Projects
  - Project types
  - Workflow stages
  - Tasks
  - Checklists
  - Approvals
  - Attachments
  - Notifications
  - Activity history
- Define relationships between projects, tasks, owners, files, and approvals.
- Choose SQLite schema for MVP with a migration path to PostgreSQL.

## Phase 3: MVP Foundation

### 6. Set Up the Application Structure

- Create the Python project structure.
- Add Streamlit frontend entry point.
- Add database initialization logic.
- Add configuration handling.
- Add local file storage directory.
- Add basic logging.

### 7. Implement Project Creation

- Build the create project form.
- Allow project type selection.
- Capture required project metadata.
- Store project data in SQLite.
- Generate the initial workflow based on selected project type.

### 8. Implement Schedule and File Uploads

- Add upload support for project schedules.
- Add upload support for Purchase Orders and other attachments.
- Store files locally for MVP.
- Save file metadata in the database.
- Display linked documents in the project detail view.

## Phase 4: Workflow Engine

### 9. Implement Dynamic Workflow Logic

- Create workflow templates per project type.
- Generate project-specific stages and tasks from templates.
- Support task dependencies.
- Unlock next tasks when prerequisites are complete.
- Support parallel task execution where required.

### 10. Implement Task Management

- Add task owner, due date, status, and comments.
- Support task status changes:
  - Not started
  - In progress
  - Blocked
  - Completed
- Track blocked reason.
- Track task completion date.
- Maintain activity history.

### 11. Implement Checklists and Approvals

- Create checklist templates for feasibility and documentation tasks.
- Allow checklist completion by assigned roles.
- Add approval actions for Quality Manager and Technical Director.
- Prevent gated stages from progressing before approval.

## Phase 5: Communication and Reporting

### 12. Implement Email Notifications

- Configure SMTP settings.
- Send notification when a task is assigned.
- Send notification when a dependent task is unlocked.
- Send reminder for upcoming due dates.
- Send alert for delayed or blocked tasks.

### 13. Build the Management Dashboard

- Display all projects.
- Show project status and completion percentage.
- Highlight delayed projects.
- Highlight blocked projects and reasons.
- Show upcoming deadlines.
- Add filters by project type, owner, status, and due date.

### 14. Implement PDF Export

- Generate a project summary report.
- Include project metadata, task status, checklist results, approvals, blockers, and attachments.
- Add production readiness notification status.
- Save or download the generated PDF.

## Phase 6: Validation and Release

### 15. Test the MVP Workflow

- Test project creation for all project types.
- Test workflow generation and task unlocking.
- Test checklist and approval gates.
- Test file uploads.
- Test dashboard calculations.
- Test PDF export.
- Test email notification behavior.

### 16. Prepare MVP Release

- Add setup instructions to the README.
- Add sample data for demo/testing.
- Review known limitations.
- Prepare a short user guide.
- Run final acceptance testing with representative users.

## Suggested MVP Milestones

### Milestone 1: Workflow Design Complete

- Workflow diagrams completed.
- Roles and task ownership confirmed.
- Product backlog approved.

### Milestone 2: Application Skeleton Ready

- Streamlit app runs locally.
- SQLite database initialized.
- Basic project creation works.

### Milestone 3: Core Workflow Working

- Project workflow is generated dynamically.
- Tasks, dependencies, statuses, and blockers work.
- Checklists and approvals are available.

### Milestone 4: Management Visibility Ready

- Dashboard displays project progress.
- Delayed and blocked projects are visible.
- Upcoming deadlines are shown.

### Milestone 5: MVP Release Candidate

- File uploads work.
- Email notifications work.
- PDF export works.
- End-to-end test workflow passes.

## Immediate Next Actions

1. Confirm the final list of project types and workflow stages.
2. Create user stories for the MVP backlog.
3. Sketch the dashboard and project detail screens.
4. Draft the first SQLite database schema.
5. Start the Streamlit application skeleton.
