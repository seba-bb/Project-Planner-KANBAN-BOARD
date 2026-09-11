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

Assign responsible people to individual tasks using email addresses. Edit a task to change its assignees or add a new email address directly in the selector.

### Task Cards

Cards show the task title, labels directly underneath, and then Details. Project names, due dates, and assignee initials remain visible; Project ID badges are removed. Open the task details or double-click a card to view or edit additional information, including:

- Colored labels.
- Responsible people.
- Status and due date.
- Description.
- Uploaded files, local/shared folder paths, and document links.

### Task Labels

Open a task and click **Labels** below its title; the Details field follows the labels. Search the shared label list and check one or more labels, or choose **Create a new label**, enter a name, select a color, and click **Apply label**. Use the pencil beside a label to edit its name or color. **Add task** (for a new ticket) or **Save changes** (when editing) saves the ticket’s selections and label edits; **Cancel** discards them. Editing a shared label updates its appearance on every ticket using it.

Selected labels appear directly below the title and above Details on cards. Uncheck a label to remove it from a ticket; it stays available for other tickets. Project assignments remain stored, but Project ID badges and project fields are not shown in task details.

### Files, Links, and Folders

Inside a task, use **Add link** for an HTTP/HTTPS address or an absolute folder path such as `C:\Program Files`, `\\server\share`, or `/srv/shared`. Use **Upload file** to select files from your computer (up to 50 files and 20 MB total per save). Click **Add task** or **Save changes** to persist additions or removals. Both use the same attachment controls and save actual uploaded file contents.

The single list shows clickable web links and file downloads. PDFs, supported images, and text files also have an **Open** preview link. Local folders have a folder link and **Copy path**: browsers may block `file://` navigation from a web page, so paste the copied path into your file manager when needed. Folder paths refer to the viewer’s computer or network; they do not upload a folder to the server.

Old entries that contain only a filename without a saved file are marked unavailable and need to be uploaded again. Removing an attachment from a ticket removes its reference; the stored file is retained on disk.

### Using the Board

1. Click **+** in a column header or **+ Add task** at the bottom of a column. Add task and Edit task use the same form: **Task title → Labels → Details → Responsible people → Column/status → Due date → Files and links**. The clicked column is selected automatically. Project ID and Project Name are not requested; older project assignments remain stored.
2. Place planned work in Backlog / To Do.
3. Move a card to In Progress when work starts.
4. Update task details and attach supporting documents as needed.
5. Move finished tasks to Completed, or declined tasks to Rejected.
6. Open **Filter** above the board to focus on relevant tasks; filters across categories are combined. **Labels** matches any selected label, and **No labels** finds unlabelled tickets.

## Current Features

- Shared Kanban board with drag-and-drop task cards.
- Task creation and editing through the same form, including label creation and file uploads.
- Shared colored labels with search, multiple selections, and inline creation and editing.
- Due dates highlighted yellow from today through the next five days, and red when overdue, using the viewer’s local date.
- Configurable status columns.
- Assignment of multiple responsible people to a task, with new email addresses added directly in the responsible-person selector.
- A single clickable file/link list with **Add link**, **Upload file**, and removal controls inside each ticket.
- A top **Filter** button opens keyword, member, status, due-date, and label filters. **Clear filters** restores the full board. Due-date filters use the application server’s calendar date.
- Statistics below the board for visible tasks, projects, To Do tasks, and columns.
- Local CSV task storage.
- Full-width board without a left sidebar; column controls are available directly in the board headers.

## Technology and Storage

- **Application:** Python and Streamlit, with an embedded HTML/CSS/JavaScript board.
- **Task storage:** `project_planner_actions.csv` in the application directory.
- **Column configuration:** `board_columns.json` in the application directory; include this file alongside the CSV when backing up the board.
- **Labels:** `board_labels.json` stores shared label names and colors; the task CSV stores selected label IDs. Include both files in backups.
- **Attachments:** File contents are stored in `attachments/<ticket-id>/`; the CSV stores their relative paths alongside web links and folder references. Include the attachments directory in backups.

The application starts with sample tasks when no CSV task database exists. Saving a ticket writes its assignments and edited fields to the CSV; dragging a card saves its status. Saved changes survive page reloads. Existing CSV files receive stable ticket IDs automatically.

## Email Notifications

New tasks automatically notify all responsible email addresses after the ticket is saved. A notice above the board reports whether the SMTP server accepted the message, rejected recipients, or could not send it. Mail-server acceptance does not guarantee inbox delivery. Task creation still succeeds if sending fails; notifications are not automatically retried on reload. The CSV records the notification status.

Copy [the SMTP example](.streamlit/secrets.toml.example) to `.streamlit/secrets.toml`, then enter your SMTP host, port, sender address, encryption mode, and credentials if your server requires login. The real secrets file is ignored by Git. `starttls` is the default; `ssl` and an explicitly configured `none` mode for a trusted relay are also supported. `app_url` adds a link to your board in the notification.

Alternatively, configure `PP_SMTP_HOST`, `PP_SMTP_PORT`, `PP_SMTP_FROM_EMAIL`, `PP_SMTP_SECURITY`, `PP_SMTP_USERNAME`, `PP_SMTP_PASSWORD`, and `PP_SMTP_APP_URL` in the server environment. Environment variables override the secrets file. Without a configured host and sender, the app saves the ticket and displays that email was not sent.

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
- Project reports and notification retry management.
- Kanban metrics such as work in progress, throughput, and cycle time.
- ERP, Outlook, and Microsoft Teams integration.
