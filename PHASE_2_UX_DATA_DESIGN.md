# Phase 2 - UX and Data Design

## Goal

Design the first usable structure of the Engineering Workflow Manager before starting implementation. This phase focuses on the main screens, task board behavior, role visibility, and the MVP database schema.

## UX Scope

### 1. Main Dashboard

Purpose: give management and project teams a fast overview of all active projects.

The dashboard should show:

- Project ID.
- Project name.
- Project type.
- Current workflow stage.
- Overall status.
- Completion percentage.
- Delayed tasks count.
- Blocked tasks count.
- Next deadline.
- Project Manager.

Useful filters:

- Project ID.
- Project type.
- Project status.
- Project Manager.
- Delayed projects.
- Blocked projects.

### 2. Project Detail View

Purpose: show one project from setup through closure.

The project detail view should include:

- Project summary.
- Uploaded schedule.
- Purchase Order and attachments.
- Workflow stages.
- Tasks grouped by stage.
- Approvals.
- Blockers.
- Activity history.
- PDF export action.

### 3. Shared Task Board

Purpose: provide a Teams Planner or Trello-style view for the full project team.

All roles should be able to see tasks assigned to every role. This makes ownership, progress, delays, and blockers transparent across the project.

Suggested board columns:

- Backlog / To Do.
- In Progress.
- Completed.
- Rejected.

Board columns should be configurable in the MVP prototype:

- Existing column names can be changed.
- New columns can be added.
- Renaming a column should keep existing tasks in the renamed column.

Project IDs should be configurable in the MVP prototype:

- Existing project IDs can be changed.
- New project IDs can be added.
- Renaming a project ID should keep existing tasks connected to the renamed project ID.

Suggested board rows:

- One swimlane per responsible person or role.
- Each swimlane should show that person's tasks across all status columns.
- Existing swimlane names can be changed.
- New swimlanes can be added.
- Existing swimlanes can be removed from the board.
- Renaming a swimlane should keep existing tasks connected to the renamed responsible person or role.
- The layout should make it easy to compare workload and progress between responsible people.

Each task card should show directly on the card:

- Task title.
- Project name.
- Due date.

Further task information should be visible only after the task card is opened:

- Project ID.
- Owner.
- Role.
- Status.
- Workflow stage.
- Description.
- Blocked reason, if blocked.
- Attachment or checklist indicator, if relevant.

Task cards should support drag and drop:

- Move a task between status columns.
- Move a task between responsible rows or roles.
- Keep the static prototype interaction in the browser until database persistence is added.

The static prototype should also include an Add task button at the top of the board:

- The button should open a smaller task creation window.
- The form should include task title, project ID, project name, responsible row or role, responsible email, column/status, due date, workflow stage, details, file attachments, and an email notification option.
- After a task is added, a smaller confirmation window should show the information that was added.
- Double-clicking an existing task card should open a similar small edit window.
- The edit window should allow changing task title, project ID, project name, responsible row or role, responsible email, column/status, due date, workflow stage, details, and attached file names.
- The edit window should stay visible within the current board viewport without requiring page scrolling.
- The user list should include `sebastian.stasica@die-tech.biz` for the prototype.
- Email notification in the static prototype should prepare an email draft for the responsible person; SMTP sending can be added in the backend phase.

Board filters:

- Project ID.
- Responsible person or row.
- Role.
- Workflow stage.
- Status.
- Due date.

### 4. My Tasks View

Purpose: let each role quickly focus on its own responsibilities.

The My Tasks view should show only tasks assigned to the selected user or role, while keeping the shared board available for full project visibility.

The view should include:

- Tasks assigned to me.
- Upcoming deadlines.
- Blocked tasks requiring action.
- Newly unlocked tasks.
- Completed tasks.

### 5. Project Creation Screen

Purpose: create a project and generate the correct workflow.

Required fields:

- Project name.
- Project type.
- Customer.
- Part number or product reference.
- Project Manager.
- Planned start date.
- Planned production start date.
- Initial schedule upload.
- Purchase Order upload, if available.

## Data Model Draft

### users

- id
- name
- email
- role_id
- is_active

### roles

- id
- name
- description

### projects

- id
- name
- project_type_id
- customer
- part_number
- project_manager_id
- status
- planned_start_date
- planned_production_start_date
- created_at
- updated_at

### project_types

- id
- name
- description

### workflow_stages

- id
- project_id
- name
- sequence_number
- status
- unlocked_at
- completed_at

### tasks

- id
- project_id
- workflow_stage_id
- name
- description
- owner_user_id
- owner_role_id
- status
- due_date
- blocked_reason
- unlocked_at
- completed_at
- created_at
- updated_at

### task_dependencies

- id
- task_id
- depends_on_task_id

### checklists

- id
- task_id
- name
- created_at

### checklist_items

- id
- checklist_id
- description
- is_completed
- completed_by_user_id
- completed_at

### approvals

- id
- project_id
- workflow_stage_id
- task_id
- approver_role_id
- approver_user_id
- status
- approved_at
- comments

### attachments

- id
- project_id
- task_id
- file_name
- file_path
- document_url
- attachment_type
- uploaded_by_user_id
- uploaded_at

### notifications

- id
- project_id
- task_id
- recipient_user_id
- notification_type
- status
- sent_at

### activity_history

- id
- project_id
- task_id
- user_id
- action
- details
- created_at

## Visibility Rules

- A task always has a project ID.
- A task always has an owner role and may also have a specific owner user.
- My Tasks filters tasks by the selected role or user.
- Shared Board shows tasks for all roles on the project.
- Edit permissions can be restricted later, but MVP visibility should remain transparent for all project roles.
- Blocked reasons should be visible to all roles.

## Phase 2 Deliverables

1. Dashboard wireframe.
2. Project detail wireframe.
3. Shared board wireframe.
4. My Tasks wireframe.
5. Project creation wireframe.
6. First SQLite schema draft.
7. Review notes before implementation starts.









