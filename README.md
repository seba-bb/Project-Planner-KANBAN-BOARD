# Project Planner KANBAN BOARD

Project Planner KANBAN BOARD is a visual task management application built with Python and Streamlit. It helps teams organize project tasks on a shared Kanban board, assign responsibility, track deadlines, and see progress at a glance.

The board supports projects such as new product introductions, engineering changes, and tool transfers. Teams can adapt its status columns and task ownership to their own project needs.

## Project Goal

- Keep project tasks and their status visible in one place.
- Make ownership and due dates clear for every task.
- Help teams identify pending work and coordinate priorities.
- Keep task details, files, and document links close to the work.
- Provide a shared view across projects and responsible teams.

## Kanban Solution

Each task appears as a card. Columns represent task status. Drag a card between columns to change its status. Small circles below the due date show the initials of each assigned person; hover over a circle to see their email address.

### Default Board Columns

| Column | Purpose |
| --- | --- |
| Backlog / To Do | Tasks waiting to be started. |
| In Progress | Tasks currently being worked on. |
| Completed | Tasks that have been finished. |
| Rejected | Tasks that have been declined or will not be continued. |

Click a column title to rename it directly in the header. Press **Enter** or click outside to save; **Escape** cancels. Empty and duplicate names are rejected. Column names and order are saved in `board_columns.json`, including empty columns, and existing tickets keep their assignments. Drag a column header to change its position; the header lifts and highlights while dragging. Click the shaded **+ Add column** header on the right to create a column in place. Column order is saved alongside column names.

### Task Ownership

The default owner roles are Project Manager, Manufacturing Engineer, Quality Engineer, Purchasing, Logistics, and Technical Director. Teams can customize owner roles and assign responsible people to individual tasks using email addresses. Edit a task to change its owner or assignees.

### Task Cards

Cards show the task title, project, due date, and assignee initials. Open the task details or double-click a card to view or edit additional information, including:

- Project ID and project name.
- Owner role and responsible people.
- Status and due date.
- Description.
- Attached files, file paths, and document links.

### Using the Board

1. Click **+** in a column header or **+ Add task** at the bottom of a column. Fill in the project, owner, and due date; the column status is selected automatically.
2. Place planned work in Backlog / To Do.
3. Move a card to In Progress when work starts.
4. Update task details and attach supporting documents as needed.
5. Move finished tasks to Completed, or declined tasks to Rejected.
6. Open **Filter** above the board to focus on relevant tasks; filters across categories are combined.

## Current Features

- Shared Kanban board with drag-and-drop task cards.
- Task creation and editing.
- Due dates highlighted yellow from today through the next five days, and red when overdue, using the viewer’s local date.
- Configurable status columns and owner roles.
- Multiple project IDs with customizable colors.
- Assignment of multiple responsible people to a task, with new email addresses added directly in the responsible-person selector.
- Task attachments and document links.
- A top **Filter** button opens keyword, member, status, due-date, project, and owner-role filters. **Clear filters** restores the full board. Due-date filters use the application server’s calendar date.
- Statistics below the board for visible tasks, projects, Quality To Do tasks, and columns.
- Local CSV task storage and actions CSV download.

## Technology and Storage

- **Application:** Python and Streamlit, with an embedded HTML/CSS/JavaScript board.
- **Task storage:** `project_planner_actions.csv` in the application directory.
- **Column configuration:** `board_columns.json` in the application directory; include this file alongside the CSV when backing up the board.
- **Attachments:** Local files and references to file paths or document links.

The application starts with sample tasks when no CSV task database exists. Saving a ticket writes its assignments and edited fields to the CSV; dragging a card saves its status. Saved changes survive page reloads. Existing CSV files receive stable ticket IDs automatically.

## Configuration Inventory

[CMDB — configuration items, dependencies, storage, and recovery notes](CMDB.md) (Polish). Machine-readable registers are available in [docs/cmdb](docs/cmdb).

## Run Locally

Run the application from the repository directory using the project virtual environment:

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

If setting up a new checkout without an existing virtual environment, create one first with `python3 -m venv .venv`.

## Planned Improvements

- Centralized PostgreSQL storage for shared multi-user use.
- Persistent task history, comments, and checklists.
- Dedicated views for personal tasks, overdue work, and blocked tasks.
- User authentication and permissions.
- Email notifications and project reports.
- Kanban metrics such as work in progress, throughput, and cycle time.
- ERP, Outlook, and Microsoft Teams integration.
