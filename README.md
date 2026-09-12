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

Click a column title to rename it directly in the header. Press **Enter** or click outside to save; **Escape** cancels. Empty and duplicate names are rejected. Column names and order are saved in `board_columns.json`, including empty columns, and existing tickets keep their assignments. Drag a column header to change its position; the header lifts and highlights while dragging. Click the shaded **+ Add column** header on the right to create a column in place. Column order is saved alongside column names. Changes use the latest saved column list so an older browser session retains columns added by another session. After adding a column, the board scrolls to the Add column header and opens a fresh name field so you can keep adding columns.

### Column Actions and Archives

Click **⋯** in a column header to open **Column actions**. Sort its tickets by **Due date** (earliest first), **Responsible** (email A–Z), or **Label** (name A–Z). Multiple assignees or labels are compared alphabetically, and missing values sort last. **Default order** restores the saved task order. Each column’s sort preference survives reloads and applies to new or edited tickets.

While dragging a ticket, a small green gap shows its insertion position between cards, at the top, or at the bottom of a column. Drop to save that position, including moves within the same column. Manually placing a ticket in a sorted column switches that destination column to **Default order**, keeping its other tickets in their displayed order. The position survives reloads.

**Archive column** hides the column and its tickets without deleting them or changing their assignments. Open **Archived items → Columns** below the board to restore it in its saved position, with its sorting preference intact. You can also open a ticket and choose **Archive ticket**. Restore individually archived tickets through **Archived items → Tickets**; restore their column first if it is archived too. Ticket IDs, labels, file references, and stored contents are retained. Archiving is available for existing tickets, after creation.

### Board Statistics

Click **Statistics**, immediately left of **Filter**, to open the statistics view. **Back to board** returns to the Kanban board. Both views share the same filters and exclude archived tickets and columns.

- **Tasks by column:** task distribution across the selected columns, including empty columns.
- **Due-date overview:** overdue, due today, due in 1–5 days, later, and missing or invalid dates. All selected columns are included; filter to unfinished columns when reviewing outstanding deadlines.
- **Workload by responsible person:** each shared ticket counts once for each responsible person; unassigned tickets appear separately.
- **Tasks by label:** each ticket counts once for each selected label, with unlabelled tickets grouped separately.

Charts include hover details and expandable data tables. Summary cards show task count, selected columns, assigned tasks, and tasks with labels. These are current snapshots; historical flow, throughput, and cycle-time charts require dated status history, which is not currently stored centrally.

### Task Ownership

Assign responsible people to individual tasks using email addresses. Edit a task to change its assignees or add a new email address directly in the selector.

### Task Cards

Cards show the task title, labels directly underneath, and then Details. Due dates and assignee initials remain visible; Project ID and project name are not shown on cards. Open the task details or double-click a card to view or edit additional information, including:

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
6. Open **Filter** above the board to focus on relevant tasks; filters across categories are combined. **Labels** matches any selected label, and **No labels** finds unlabelled tickets. Filters narrow the tickets while every active column remains visible, including empty columns. Archived columns stay hidden until restored.

## Current Features

- Green Kanban board using `#C1FEAC`, with white cards, compact headers, and drag-and-drop task cards.
- Task creation and editing through the same form, including label creation and file uploads.
- Shared colored labels with search, multiple selections, and inline creation and editing.
- Due dates highlighted yellow from today through the next five days, and red when overdue, using the viewer’s local date.
- Configurable status columns with a **⋯ Column actions** menu for saved sorting and archiving.
- Recoverable column and ticket archives, available from **Archived items** below the board.
- Assignment of multiple responsible people to a task, with new email addresses added directly in the responsible-person selector.
- A single clickable file/link list with **Add link**, **Upload file**, and removal controls inside each ticket.
- A top **Filter** button opens keyword, member, status, due-date, and label filters. **Clear filters** restores the full board. Due-date filters use the application server’s calendar date.
- Local CSV task storage.
- Full-width board without a left sidebar; column controls are available directly in the board headers.

## Technology and Storage

- **Application:** Python and Streamlit, with an embedded HTML/CSS/JavaScript board.
- **Task storage:** `project_planner_actions.csv` in the application directory, including each ticket’s archive flag. Archiving retains its row.
- **Column configuration:** `board_columns.json` retains all column names and order. `board_column_settings.json` stores each column’s sorting preference and archive flag. Include both files alongside the CSV in backups.
- **Labels:** `board_labels.json` stores shared label names and colors; the task CSV stores selected label IDs. Include both files in backups.
- **Attachments:** File contents are stored in `attachments/<ticket-id>/`; the CSV stores their relative paths alongside web links and folder references. Include the attachments directory in backups.

The application starts with sample tasks when no CSV task database exists. Saving a ticket writes its assignments and edited fields to the CSV; dragging a card saves its status and position using CSV row order. Saved changes survive page reloads. Existing CSV files receive stable ticket IDs automatically.

## Email Notifications

New tasks automatically notify all responsible email addresses after the ticket is saved. A notice above the board reports whether the SMTP server accepted the message, rejected recipients, or could not send it. Mail-server acceptance does not guarantee inbox delivery. Task creation still succeeds if sending fails; notifications are not automatically retried on reload. The CSV records the notification status.

Copy [the SMTP example](.streamlit/secrets.toml.example) to `.streamlit/secrets.toml`, then enter your SMTP host, port, sender address, encryption mode, and credentials if your server requires login. The real secrets file is ignored by Git. `starttls` is the default; `ssl` and an explicitly configured `none` mode for a trusted relay are also supported. `app_url` adds a link to your board in the notification.

Alternatively, configure `PP_SMTP_HOST`, `PP_SMTP_PORT`, `PP_SMTP_FROM_EMAIL`, `PP_SMTP_SECURITY`, `PP_SMTP_USERNAME`, `PP_SMTP_PASSWORD`, and `PP_SMTP_APP_URL` in the server environment. Environment variables override the secrets file. Without a configured host and sender, the app saves the ticket and displays that email was not sent.

Notifications for assignment changes on existing tasks and new comments are planned below; they are not implemented yet.

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

### Backup and Recovery Tasks

- [ ] Add automatic snapshots before board changes, scheduled backups, and a manual **Back up now** option.
- [ ] Back up the task CSV, column names/order/settings, labels, and uploaded attachments together. Include comments, checklists, and activity once they are stored centrally; browser-only data is not currently part of server backups.
- [ ] Add recovery of an individual ticket or the whole board from a selected snapshot, with a preview of the changes. Explain that restoring the whole board rolls back later changes by all users.
- [ ] Add configurable backup retention and protected backup storage. Keep everyday board access open while restricting backup deletion and snapshot recovery to an administrator.

### Email Notification Tasks

- [ ] Notify each newly assigned responsible person after an assignment is saved, including assignments added to existing tickets. Retain the existing new-task notification behavior without sending duplicates.
- [ ] Notify all currently assigned responsible people when a new comment is successfully saved. Include the task title, comment text, and a ticket link when configured. Store comments centrally first so notifications and shared comment history refer to the same saved comment.
- [ ] Record notification attempts and failures, and support retries without duplicate messages or loss of the saved assignment/comment.

### Other Improvements

- Centralized PostgreSQL storage for shared multi-user use.
- Persistent task history, comments, and checklists.
- Dedicated views for personal tasks, overdue work, and blocked tasks.
- User authentication and permissions.
- Project reports.
- Kanban metrics such as work in progress, throughput, and cycle time.
- ERP, Outlook, and Microsoft Teams integration.

## Tests

```bash
.venv/bin/python -m unittest discover -s tests
npm ci --prefix tests/ui
npm test --prefix tests/ui
```

The UI regression tests use jsdom and the project VENV to render an isolated board. They cover repeated column creation, iframe refreshes, column actions, ticket archiving, and failed-save retries without opening or modifying the live CSV. Python integration tests also exercise multiple Streamlit sessions, status-filter changes, and archive/restore operations against temporary storage.
