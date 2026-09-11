from __future__ import annotations

import base64
import csv
import json
import mimetypes
import os
import re
import tempfile
from uuid import uuid4
from datetime import date
from pathlib import Path
from html import escape
from io import StringIO
from urllib.parse import quote, urlsplit

from notifications import send_new_task_notification

import streamlit as st
import streamlit.components.v1 as components


DEFAULT_STATUSES = ["Backlog / To Do", "In Progress", "Completed", "Rejected"]
DEFAULT_PROJECT_IDS = ["PRJ-001", "PRJ-002", "PRJ-003"]
DEFAULT_PROJECT_COLORS = [
    "#2563eb",
    "#16a34a",
    "#f97316",
    "#7c3aed",
    "#0891b2",
    "#db2777",
    "#ca8a04",
    "#475569",
]
DEFAULT_USERS = ["sebastian.stasica@die-tech.biz"]
APP_ICON_PATH = Path(__file__).parent / "assets" / "project_planner_icon.png"
ATTACHMENTS_DIR = Path(__file__).parent / "attachments"
MAX_ATTACHMENT_BYTES = 20 * 1024 * 1024
TASK_DATABASE_CSV = Path(__file__).parent / "project_planner_actions.csv"
BOARD_COLUMNS_JSON = Path(__file__).parent / "board_columns.json"
BOARD_LABELS_JSON = Path(__file__).parent / "board_labels.json"
TASK_CSV_FIELDS = [
    "id",
    "title",
    "owner",
    "responsible_emails",
    "status",
    "due",
    "project_id",
    "project",
    "description",
    "attachments",
    "email_notification",
    "email_notification_status",
    "labels",
]

# Demo seed data used when no CSV task database exists yet.
DEFAULT_TASKS = [
    {
        "title": "Create project record",
        "owner": "Project Manager",
        "status": "Completed",
        "due": "2026-08-02",
        "project_id": "PRJ-001",
        "project": "NPI - Stamping Bracket",
        "description": "Create the initial project record and confirm the project manager.",
    },
    {
        "title": "Upload Purchase Order",
        "owner": "Project Manager",
        "status": "Backlog / To Do",
        "due": "2026-08-04",
        "project_id": "PRJ-001",
        "project": "NPI - Stamping Bracket",
        "description": "Attach the customer purchase order and verify the commercial reference.",
    },
    {
        "title": "Manufacturing feasibility checklist",
        "owner": "Manufacturing Engineer",
        "status": "In Progress",
        "due": "2026-08-08",
        "project_id": "PRJ-001",
        "project": "NPI - Stamping Bracket",
        "description": "Review process feasibility, press capacity, tooling assumptions, and cycle time risk.",
    },
    {
        "title": "Review drawing revision",
        "owner": "Quality Engineer",
        "status": "Backlog / To Do",
        "due": "2026-08-05",
        "project_id": "PRJ-001",
        "project": "NPI - Stamping Bracket",
        "description": "Check the latest customer drawing revision and confirm special characteristics.",
    },
    {
        "title": "Create quality feasibility checklist",
        "owner": "Quality Engineer",
        "status": "Backlog / To Do",
        "due": "2026-08-06",
        "project_id": "PRJ-001",
        "project": "NPI - Stamping Bracket",
        "description": "Prepare the quality checklist for feasibility gate review.",
    },
    {
        "title": "Prepare Control Plan draft",
        "owner": "Quality Engineer",
        "status": "Backlog / To Do",
        "due": "2026-08-09",
        "project_id": "PRJ-001",
        "project": "NPI - Stamping Bracket",
        "description": "Create the initial Control Plan with process steps and inspection points.",
    },
    {
        "title": "Prepare CMM measurement program",
        "owner": "Quality Engineer",
        "status": "Backlog / To Do",
        "due": "2026-08-11",
        "project_id": "PRJ-001",
        "project": "NPI - Stamping Bracket",
        "description": "Prepare the first CMM measurement program for dimensional validation.",
    },
    {
        "title": "Confirm PPAP documentation list",
        "owner": "Quality Engineer",
        "status": "Backlog / To Do",
        "due": "2026-08-13",
        "project_id": "PRJ-002",
        "project": "Engineering Change - Seat Rail Clip",
        "description": "Confirm required PPAP documents and evidence for customer submission.",
    },
    {
        "title": "Packaging concept review",
        "owner": "Logistics",
        "status": "Backlog / To Do",
        "due": "2026-08-12",
        "project_id": "PRJ-002",
        "project": "Engineering Change - Seat Rail Clip",
        "description": "Review packaging concept, handling method, and available container options.",
    },
    {
        "title": "Supplier cost confirmation",
        "owner": "Purchasing",
        "status": "In Progress",
        "due": "2026-08-11",
        "project_id": "PRJ-002",
        "project": "Engineering Change - Seat Rail Clip",
        "description": "Confirm supplier cost impact and timing for purchased components.",
    },
    {
        "title": "Approve technical feasibility",
        "owner": "Technical Director",
        "status": "Backlog / To Do",
        "due": "2026-08-10",
        "project_id": "PRJ-003",
        "project": "Tool Transfer - Door Reinforcement",
        "description": "Approve the technical feasibility gate before downstream work starts.",
    },
    {
        "title": "Old container concept",
        "owner": "Logistics",
        "status": "Rejected",
        "due": "2026-08-06",
        "project_id": "PRJ-003",
        "project": "Tool Transfer - Door Reinforcement",
        "description": "Rejected because the container footprint does not match the new logistics flow.",
    },
]



def task_from_csv_row(row: dict[str, str]) -> dict[str, object]:
    responsible_emails = csv_json_list(row.get("responsible_emails", ""))
    attachments = csv_json_list(row.get("attachments", ""))
    task = {
        "id": row.get("id") or uuid4().hex,
        "title": row.get("title", "Untitled task"),
        "owner": row.get("owner", ""),
        "responsible_emails": responsible_emails,
        "responsible_email": ", ".join(responsible_emails),
        "status": row.get("status", DEFAULT_STATUSES[0]),
        "due": row.get("due", ""),
        "project_id": row.get("project_id", DEFAULT_PROJECT_IDS[0]),
        "project": row.get("project", "Unassigned project"),
        "description": row.get("description", "No additional details provided."),
        "attachments": attachments,
        "labels": csv_json_list(row.get("labels", "")),
        "email_notification_status": row.get("email_notification_status", ""),
        "email_notification": row.get("email_notification", "").strip().lower() in {"1", "true", "yes"},
    }
    return task


def csv_json_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if item]
    if not value:
        return []
    try:
        parsed = json.loads(str(value))
    except json.JSONDecodeError:
        parsed = [part.strip() for part in str(value).split(";")]
    if isinstance(parsed, str):
        parsed = [parsed]
    return [str(item) for item in parsed if item]


def task_to_csv_row(task: dict[str, object]) -> dict[str, str]:
    responsible_emails = responsible_emails_list(task)
    return {
        "id": str(task["id"]),
        "title": str(task.get("title", "")),
        "owner": str(task.get("owner", "")),
        "responsible_emails": json.dumps(responsible_emails, ensure_ascii=False),
        "status": str(task.get("status", "")),
        "due": str(task.get("due", "")),
        "project_id": str(task.get("project_id", "")),
        "project": str(task.get("project", "")),
        "description": str(task.get("description", "")),
        "attachments": json.dumps(task.get("attachments", []), ensure_ascii=False),
        "labels": json.dumps(task.get("labels", []), ensure_ascii=False),
        "email_notification": "true" if task.get("email_notification") else "false",
        "email_notification_status": str(task.get("email_notification_status", "")),
    }


def load_tasks_from_csv() -> list[dict[str, object]]:
    if not TASK_DATABASE_CSV.exists():
        return [task.copy() for task in DEFAULT_TASKS]

    with TASK_DATABASE_CSV.open("r", newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)
        needs_ids = "id" not in (reader.fieldnames or [])
        rows = list(reader)
        needs_ids = needs_ids or any(not row.get("id") for row in rows)
        tasks = [task_from_csv_row(row) for row in rows]
    if needs_ids:
        write_tasks_to_csv(tasks)
    return tasks


def write_tasks_to_csv(tasks: list[dict[str, object]]) -> None:
    TASK_DATABASE_CSV.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", newline="", encoding="utf-8-sig",
            dir=TASK_DATABASE_CSV.parent, delete=False,
        ) as csv_file:
            temporary_path = Path(csv_file.name)
            writer = csv.DictWriter(csv_file, fieldnames=TASK_CSV_FIELDS)
            writer.writeheader()
            writer.writerows(task_to_csv_row(task) for task in tasks)
        os.replace(temporary_path, TASK_DATABASE_CSV)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def save_tasks_to_csv() -> None:
    write_tasks_to_csv(st.session_state.tasks)


def apply_board_edit(event: object) -> None:
    if not isinstance(event, dict) or not isinstance(event.get("event_id"), str):
        return
    event_id = event["event_id"]
    if st.session_state.get("board_save_result", {}).get("event_id") == event_id:
        return
    try:
        updates = event.get("updates")
        if not isinstance(updates, dict) or not updates:
            raise ValueError("No ticket changes were received.")
        allowed = {"title", "project_id", "project", "responsible_emails", "status", "due", "description", "attachments", "labels"}
        if set(updates) - allowed:
            raise ValueError("The ticket contains unsupported changes.")
        for field, value in updates.items():
            if field in {"responsible_emails", "attachments", "labels"}:
                if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
                    raise ValueError(f"Invalid {field} value.")
            elif not isinstance(value, str):
                raise ValueError(f"Invalid {field} value.")
        # Read the latest file so an edit does not overwrite other saved tickets.
        tasks = load_tasks_from_csv()
        task = next((task for task in tasks if task.get("id") == event.get("task_id")), None)
        if task is None:
            raise ValueError("This ticket no longer exists. Reload the board.")
        if "attachments" in updates:
            old_attachments = task.get("attachments", [])
            updates = updates | {"attachments": list(dict.fromkeys(
                reference if reference in old_attachments else clean_attachment_link(reference)
                for reference in updates["attachments"]
            ))}
        task.update(updates)
        if not task["title"].strip():
            raise ValueError("Task title is required.")
        task["responsible_emails"] = clean_responsible_emails(task["responsible_emails"])
        task["responsible_email"] = ", ".join(task["responsible_emails"])
        previous_labels = load_board_labels()
        label_changes = event.get("label_changes", [])
        labels = merge_board_labels(previous_labels, label_changes)
        if "labels" in updates:
            task["labels"] = list(dict.fromkeys(task["labels"]))
            if set(task["labels"]) - {label["id"] for label in labels}:
                raise ValueError("A selected label no longer exists. Reload the board.")
        saved_files = save_uploaded_files(task["id"], event.get("uploaded_files", []))
        task["attachments"] = list(dict.fromkeys(task.get("attachments", []) + saved_files))
        labels_changed = labels != previous_labels
        labels_written = False
        try:
            if labels_changed:
                write_board_labels(labels)
                labels_written = True
            write_tasks_to_csv(tasks)
        except OSError:
            cleanup_uploaded_files(saved_files)
            if labels_written:
                write_board_labels(previous_labels)
            raise
        st.session_state.tasks = tasks
        st.session_state.board_save_result = {"event_id": event_id, "ok": True}
    except (OSError, ValueError) as error:
        st.session_state.board_save_result = {
            "event_id": event_id, "ok": False,
            "error": f"Ticket was not saved: {error}",
        }


def merge_board_labels(existing: list[dict], changes: object) -> list[dict]:
    if not isinstance(changes, list):
        raise ValueError("Invalid label changes.")
    merged = {label["id"]: label.copy() for label in existing}
    for label in changes:
        if not isinstance(label, dict) or set(label) != {"id", "name", "color"}:
            raise ValueError("Invalid label definition.")
        if any(not isinstance(label[key], str) for key in ("id", "name", "color")):
            raise ValueError("Invalid label definition.")
        name = normalize_name(label["name"])
        if not re.fullmatch(r"[a-zA-Z0-9_-]{1,80}", label["id"]):
            raise ValueError("Invalid label ID.")
        if not name or len(name) > 80:
            raise ValueError("Label names must contain 1 to 80 characters.")
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", label["color"]):
            raise ValueError("Choose a valid label color.")
        merged[label["id"]] = {"id": label["id"], "name": name, "color": label["color"].lower()}
    names = [label["name"].casefold() for label in merged.values()]
    if len(names) != len(set(names)):
        raise ValueError("Label names must be unique.")
    return list(merged.values())


def load_board_labels() -> list[dict]:
    if not BOARD_LABELS_JSON.exists():
        return []
    return merge_board_labels([], json.loads(BOARD_LABELS_JSON.read_text(encoding="utf-8")))


def write_board_labels(labels: list[dict]) -> None:
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=BOARD_LABELS_JSON.parent, delete=False,
        ) as file:
            temporary_path = Path(file.name)
            json.dump(labels, file, ensure_ascii=False, indent=2)
            file.write("\n")
        os.replace(temporary_path, BOARD_LABELS_JSON)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def load_board_columns() -> list[str]:
    if not BOARD_COLUMNS_JSON.exists():
        return DEFAULT_STATUSES.copy()
    columns = json.loads(BOARD_COLUMNS_JSON.read_text(encoding="utf-8"))
    if (not isinstance(columns, list) or not columns
            or any(not isinstance(name, str) or not name.strip() for name in columns)
            or len(set(columns)) != len(columns)):
        raise ValueError("The saved board columns are invalid.")
    return columns


def write_board_columns(columns: list[str]) -> None:
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=BOARD_COLUMNS_JSON.parent, delete=False,
        ) as file:
            temporary_path = Path(file.name)
            json.dump(columns, file, ensure_ascii=False, indent=2)
            file.write("\n")
        os.replace(temporary_path, BOARD_COLUMNS_JSON)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def rename_board_columns(new_names: list[str]) -> tuple[bool, str]:
    old_names = st.session_state.statuses.copy()
    names = [normalize_name(name) for name in new_names]
    if len(names) != len(old_names) or any(not name for name in names):
        return False, "Column names cannot be empty."
    if len(set(names)) != len(names):
        return False, "Column names must be unique."
    if names == old_names:
        return True, "Column names unchanged."
    rename_map = dict(zip(old_names, names, strict=True))
    wrote_tasks = False
    try:
        original_tasks = load_tasks_from_csv()
        tasks = [task | {"status": rename_map.get(task["status"], task["status"])} for task in original_tasks]
        if tasks != original_tasks:
            write_tasks_to_csv(tasks)
            wrote_tasks = True
        try:
            write_board_columns(names)
        except OSError:
            # Keep the old ticket statuses if saving the column configuration fails.
            if wrote_tasks:
                write_tasks_to_csv(original_tasks)
            raise
    except (OSError, ValueError) as error:
        return False, f"Column names were not saved: {error}"
    st.session_state.statuses = names
    st.session_state.tasks = tasks
    if "status_filter" in st.session_state:
        st.session_state.updated_status_filter = [
            rename_map.get(name, name) for name in st.session_state.status_filter
        ]
    return True, "Column names updated."


def apply_column_rename(event: dict[str, object]) -> None:
    event_id = event.get("event_id")
    if not isinstance(event_id, str):
        return
    if st.session_state.get("board_save_result", {}).get("event_id") == event_id:
        return
    old_name, new_name = event.get("status"), event.get("name")
    if old_name not in st.session_state.statuses or not isinstance(new_name, str):
        success, message = False, "This column no longer exists. Reload the board."
    else:
        names = [new_name if name == old_name else name for name in st.session_state.statuses]
        success, message = rename_board_columns(names)
    st.session_state.board_save_result = {"event_id": event_id, "ok": success, "error": "" if success else message}


def move_board_column(status: str, target: str, position: str) -> tuple[bool, str]:
    columns = st.session_state.statuses.copy()
    if (not all(isinstance(value, str) for value in (status, target, position))
            or status not in columns or target not in columns or position not in {"before", "after"}):
        return False, "The column order changed. Reload the board and try again."
    if status == target:
        return True, "Column order unchanged."
    columns.remove(status)
    columns.insert(columns.index(target) + (position == "after"), status)
    try:
        write_board_columns(columns)
    except OSError as error:
        return False, f"Column order was not saved: {error}"
    st.session_state.statuses = columns
    return True, "Column order updated."


def apply_column_action(event: dict[str, object]) -> None:
    event_id = event.get("event_id")
    if not isinstance(event_id, str):
        return
    if st.session_state.get("board_save_result", {}).get("event_id") == event_id:
        return
    if event.get("action") == "add_column" and isinstance(event.get("name"), str):
        success, message = add_value("statuses", event["name"], "Column")
    elif event.get("action") == "move_column":
        success, message = move_board_column(event.get("status"), event.get("target"), event.get("position"))
    else:
        success, message = False, "Invalid column change."
    st.session_state.board_save_result = {"event_id": event_id, "ok": success, "error": "" if success else message}


def reset_board_filters() -> None:
    st.session_state.filter_keyword = ""
    st.session_state.filter_members = []
    st.session_state.filter_due = "Any date"
    st.session_state.filter_labels = []
    st.session_state.status_filter = st.session_state.statuses.copy()


def task_matches_filters(
    task: dict[str, object], keyword: str = "", members: list[str] | None = None,
    due_filter: str = "Any date", today: date | None = None, labels: list[str] | None = None,
) -> bool:
    task_labels = task.get("labels", [])
    if labels and not (set(task_labels).intersection(labels) or ("__no_labels__" in labels and not task_labels)):
        return False
    emails = responsible_emails_list(task)
    searchable = " ".join(str(task.get(field, "")) for field in (
        "title", "description", "project", "project_id", "status", "due",
    )) + " " + " ".join(emails)
    if any(word not in searchable.casefold() for word in keyword.casefold().split()):
        return False
    if members and not (set(emails).intersection(members) or ("No members" in members and not emails)):
        return False
    if due_filter == "Any date":
        return True
    due_text = str(task.get("due") or "").strip()
    if due_filter == "No date":
        return not due_text
    try:
        days_left = (date.fromisoformat(due_text) - (today or date.today())).days
    except ValueError:
        return False
    if due_filter == "Overdue":
        return days_left < 0
    if due_filter == "Due today":
        return days_left == 0
    limits = {"Due in the next day": 1, "Due in the next week": 7, "Due in the next month": 30}
    return due_filter in limits and 0 <= days_left <= limits[due_filter]


def on_board_change() -> None:
    event = st.session_state.get("kanban_board")
    if isinstance(event, dict) and event.get("action") in {"add_column", "move_column"}:
        apply_column_action(event)
        return
    if isinstance(event, dict) and event.get("action") == "rename_column":
        apply_column_rename(event)
        return
    if isinstance(event, dict) and event.get("action") == "create_task":
        apply_new_task(event)
        return
    apply_board_edit(event)


def task_database_csv_bytes() -> bytes:
    rows = [task_to_csv_row(task) for task in st.session_state.tasks]

    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=TASK_CSV_FIELDS)
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8-sig")


def render_app_header() -> None:
    st.markdown(
        """
        <div class="app-brand-header" aria-label="Project Planner">
            <div class="app-brand-monogram" aria-hidden="true">
                <span class="app-brand-monogram-blue">P</span><span class="app-brand-monogram-green">P</span>
            </div>
            <div class="app-brand-wordmark">
                <span class="app-brand-project">Project</span>
                <span class="app-brand-planner">Planner</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
st.set_page_config(
    page_title="Project Planner",
    page_icon=str(APP_ICON_PATH),
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
        [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] {
            display: none;
        }
        .block-container {
            padding-top: 1.6rem;
            padding-bottom: 2rem;
        }
        .app-brand-header {
            display: flex;
            align-items: center;
            gap: 16px;
            margin: 0 0 2px;
        }
        .app-brand-monogram {
            display: flex;
            align-items: baseline;
            gap: 0;
            flex: 0 0 auto;
            font-family: Inter, "Segoe UI", Arial, sans-serif;
            font-size: 3rem;
            font-weight: 900;
            line-height: 1;
            letter-spacing: 0;
        }
        .app-brand-monogram-blue {
            color: #0058c9;
        }
        .app-brand-monogram-green {
            color: #168b00;
            margin-left: -0.08em;
        }
        .app-brand-wordmark {
            display: flex;
            align-items: baseline;
            gap: 22px;
            font-family: Inter, "Segoe UI", Arial, sans-serif;
            font-size: 2.35rem;
            font-weight: 800;
            line-height: 1;
            letter-spacing: 0;
        }
        .app-brand-project {
            color: #0058c9;
        }
        .app-brand-planner {
            color: #168b00;
        }
        .dashboard-strip {
            display: grid;
            grid-template-columns: repeat(4, minmax(120px, 1fr));
            gap: 8px;
            margin: 8px 0 14px;
        }
        .dashboard-tile {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 8px 10px;
        }
        .dashboard-label {
            color: #64748b;
            font-size: 0.72rem;
            font-weight: 700;
            line-height: 1.1;
            margin-bottom: 3px;
        }
        .dashboard-value {
            color: #0f172a;
            font-size: 1.25rem;
            font-weight: 800;
            line-height: 1;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


def initialize_state() -> None:
    # Streamlit reruns the script after most interactions. Session state preserves
    # user-edited lists and tasks across those reruns inside the current browser session.
    if "statuses" not in st.session_state:
        st.session_state.statuses = load_board_columns()
    if "updated_status_filter" in st.session_state:
        st.session_state.status_filter = st.session_state.pop("updated_status_filter")
    if "project_ids" not in st.session_state:
        st.session_state.project_ids = DEFAULT_PROJECT_IDS.copy()
    if "project_colors" not in st.session_state:
        st.session_state.project_colors = {
            project_id: default_project_color(project_id)
            for project_id in st.session_state.project_ids
        }
    if "users" not in st.session_state:
        st.session_state.users = DEFAULT_USERS.copy()
    if "tasks" not in st.session_state:
        st.session_state.tasks = load_tasks_from_csv()

    for task in st.session_state.tasks:
        task.setdefault("id", uuid4().hex)
        # Older/default tasks may not include fields added by newer UI features.
        existing_responsible = task.get("responsible_emails", task.get("responsible_email", st.session_state.users[0]))
        if isinstance(existing_responsible, str):
            existing_responsible = [existing_responsible]
        task["responsible_emails"] = [email for email in existing_responsible if email] or [st.session_state.users[0]]
        task["responsible_email"] = ", ".join(task["responsible_emails"])
        task.setdefault("attachments", [])
        task.setdefault("email_notification", False)
        if task.get("status") and task["status"] not in st.session_state.statuses:
            st.session_state.statuses.append(task["status"])
        if task.get("project_id") and task["project_id"] not in st.session_state.project_ids:
            st.session_state.project_ids.append(task["project_id"])
        for email in task["responsible_emails"]:
            if email not in st.session_state.users:
                st.session_state.users.append(email)


def normalize_name(name: str) -> str:
    return " ".join(name.strip().split())


def default_project_color(project_id: str) -> str:
    hash_value = sum((index + 1) * ord(character) for index, character in enumerate(project_id))
    return DEFAULT_PROJECT_COLORS[hash_value % len(DEFAULT_PROJECT_COLORS)]


def normalize_hex_color(value: str) -> str:
    value = value.strip()
    if len(value) == 7 and value.startswith("#"):
        try:
            int(value[1:], 16)
        except ValueError:
            return "#2563eb"
        return value.lower()
    return "#2563eb"


def readable_text_color(background_color: str) -> str:
    color = normalize_hex_color(background_color).lstrip("#")
    red = int(color[0:2], 16)
    green = int(color[2:4], 16)
    blue = int(color[4:6], 16)
    luminance = (0.299 * red + 0.587 * green + 0.114 * blue) / 255
    return "#0f172a" if luminance > 0.62 else "#ffffff"


def project_color_payload() -> dict[str, dict[str, str]]:
    for project_id in st.session_state.project_ids:
        st.session_state.project_colors.setdefault(project_id, default_project_color(project_id))

    return {
        project_id: {
            "bg": normalize_hex_color(st.session_state.project_colors[project_id]),
            "border": normalize_hex_color(st.session_state.project_colors[project_id]),
            "text": readable_text_color(st.session_state.project_colors[project_id]),
        }
        for project_id in st.session_state.project_ids
    }

def safe_storage_name(value: str) -> str:
    cleaned = "".join(character if character.isalnum() or character in ".-_" else "_" for character in value)
    return cleaned.strip("._") or "attachment"


def unique_file_path(folder: Path, file_name: str) -> Path:
    target_path = folder / safe_storage_name(file_name)
    if not target_path.exists():
        return target_path

    stem = target_path.stem
    suffix = target_path.suffix
    counter = 2
    while True:
        candidate_path = folder / f"{stem}_{counter}{suffix}"
        if not candidate_path.exists():
            return candidate_path
        counter += 1


def local_folder_uri(value: str) -> str | None:
    path = value.strip()
    if re.match(r"^[A-Za-z]:[\\/]", path):
        return "file:///" + quote(path.replace("\\", "/"), safe="/:")
    if path.startswith("\\\\"):
        return "file://" + quote(path[2:].replace("\\", "/"), safe="/")
    if path.startswith("/"):
        return "file://" + quote(path, safe="/")
    if path.lower().startswith("file://") and urlsplit(path).path:
        return "file:" + path[5:]
    return None


def clean_attachment_link(value: str) -> str:
    link = value.strip()
    if local_folder_uri(link):
        return link
    parsed = urlsplit(link)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname or any(char.isspace() for char in link):
        raise ValueError("Enter a web link or an absolute local/shared folder path.")
    return link


def upload_payload(files: list[object]) -> list[dict[str, str]]:
    return [{"name": file.name, "data": base64.b64encode(file.getvalue()).decode("ascii")} for file in files or []]


def cleanup_uploaded_files(references: list[str]) -> None:
    root = ATTACHMENTS_DIR.resolve()
    for reference in references:
        path = (ATTACHMENTS_DIR.parent / reference).resolve()
        if path.is_relative_to(root):
            path.unlink(missing_ok=True)


def save_uploaded_files(task_id: str, uploads: object) -> list[str]:
    if not isinstance(uploads, list) or len(uploads) > 50:
        raise ValueError("Choose up to 50 files per save (20 MB total).")
    decoded = []
    total = 0
    for upload in uploads:
        if not isinstance(upload, dict) or not isinstance(upload.get("name"), str) or not isinstance(upload.get("data"), str):
            raise ValueError("Invalid uploaded file.")
        if not upload["name"].strip() or len(upload["name"]) > 255:
            raise ValueError("Invalid file name.")
        if len(upload["data"]) > ((MAX_ATTACHMENT_BYTES + 2) // 3) * 4:
            raise ValueError("Uploads must total 20 MB or less per save.")
        try:
            contents = base64.b64decode(upload["data"], validate=True)
        except (ValueError, base64.binascii.Error) as error:
            raise ValueError("The uploaded file could not be read. Select it again.") from error
        total += len(contents)
        if total > MAX_ATTACHMENT_BYTES:
            raise ValueError("Uploads must total 20 MB or less per save.")
        decoded.append((upload["name"], contents))
    saved = []
    try:
        if decoded:
            folder = ATTACHMENTS_DIR / safe_storage_name(task_id)
            folder.mkdir(parents=True, exist_ok=True)
            for name, contents in decoded:
                path = unique_file_path(folder, name)
                # Never overwrite an existing attachment, including same-name uploads.
                with path.open("xb") as file:
                    saved.append(str(path.relative_to(ATTACHMENTS_DIR.parent)))
                    file.write(contents)
    except OSError:
        cleanup_uploaded_files(saved)
        raise
    return saved


def attachment_link_items(attachments: list[str]) -> list[dict[str, str]]:
    items = []
    root = ATTACHMENTS_DIR.resolve()
    for attachment in attachments:
        item = {"reference": attachment, "name": Path(attachment).name or attachment, "href": ""}
        if attachment.lower().startswith(("http://", "https://")):
            try:
                item.update(name=attachment, href=clean_attachment_link(attachment), kind="link")
            except ValueError:
                pass
        else:
            path = (ATTACHMENTS_DIR.parent / attachment).resolve()
            # Only expose uploaded files, never arbitrary application/server files.
            if path.is_relative_to(root) and path.is_file():
                mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
                safe_preview = mime in {"application/pdf", "text/plain", "image/png", "image/jpeg", "image/gif", "image/webp"}
                if not safe_preview:
                    mime = "application/octet-stream"
                try:
                    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
                    item.update(href=f"data:{mime};base64,{encoded}", kind="file", preview=safe_preview)
                except OSError:
                    pass
        if not item["href"] and (folder_uri := local_folder_uri(attachment)):
            item.update(name=attachment, href=folder_uri, kind="folder", reference=attachment)
        items.append(item)
    return items


def rename_values(
    state_key: str,
    task_field: str,
    new_names: list[str],
    item_label: str,
) -> tuple[bool, str]:
    if state_key == "statuses":
        return rename_board_columns(new_names)
    # Rename list entries and update existing tasks that reference the old names.
    # This keeps the board from losing tasks when a column or project ID is renamed.
    cleaned_names = [normalize_name(name) for name in new_names]

    if any(not name for name in cleaned_names):
        return False, f"{item_label} names cannot be empty."

    if len(set(cleaned_names)) != len(cleaned_names):
        return False, f"{item_label} names must be unique."

    old_names = st.session_state[state_key].copy()
    rename_map = dict(zip(old_names, cleaned_names, strict=True))
    st.session_state[state_key] = cleaned_names

    for task in st.session_state.tasks:
        task[task_field] = rename_map.get(task[task_field], task[task_field])

    save_tasks_to_csv()
    return True, f"{item_label} names updated."


def add_value(state_key: str, value: str, item_label: str) -> tuple[bool, str]:
    cleaned_value = normalize_name(value)

    if not cleaned_value:
        return False, f"Enter a {item_label.lower()} first."

    if cleaned_value in st.session_state[state_key]:
        return False, f"This {item_label.lower()} already exists."

    if state_key == "statuses":
        try:
            write_board_columns([*st.session_state.statuses, cleaned_value])
        except OSError as error:
            return False, f"Column was not saved: {error}"
        if "status_filter" in st.session_state:
            st.session_state.updated_status_filter = [*st.session_state.status_filter, cleaned_value]
    st.session_state[state_key].append(cleaned_value)
    return True, f"Added {item_label.lower()}: {cleaned_value}."


def normalize_email(email: str) -> str:
    return email.strip().lower()


def clean_responsible_emails(emails: list[str]) -> list[str]:
    cleaned = list(dict.fromkeys(normalize_email(email) for email in emails))
    if not cleaned:
        raise ValueError("Select at least one responsible person.")
    for email in cleaned:
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            raise ValueError(f"Invalid email address: {email}.")
    return cleaned


def add_user_emails(raw_emails: str) -> tuple[bool, str]:
    candidates = [normalize_email(email) for email in raw_emails.replace(",", "\n").splitlines()]
    candidates = [email for email in candidates if email]

    if not candidates:
        return False, "Enter at least one email address."

    invalid_emails = [email for email in candidates if "@" not in email or "." not in email.split("@")[-1]]
    if invalid_emails:
        return False, f"Invalid email address: {invalid_emails[0]}."

    added_emails = []
    for email in candidates:
        if email not in st.session_state.users:
            st.session_state.users.append(email)
            added_emails.append(email)

    if not added_emails:
        return False, "These email addresses are already on the list."

    return True, f"Added {len(added_emails)} email address(es)."


def remove_user_emails(emails_to_remove: list[str]) -> tuple[bool, str]:
    if not emails_to_remove:
        return False, "Select at least one email address to remove."

    remaining_users = [email for email in st.session_state.users if email not in emails_to_remove]
    if not remaining_users:
        return False, "At least one email address must remain."

    st.session_state.users = remaining_users
    for task in st.session_state.tasks:
        task_emails = [email for email in task.get("responsible_emails", []) if email in remaining_users]
        task["responsible_emails"] = task_emails or [remaining_users[0]]
        task["responsible_email"] = ", ".join(task["responsible_emails"])

    save_tasks_to_csv()
    return True, "Email list updated."


def responsible_emails_list(task: dict[str, object]) -> list[str]:
    emails = task.get("responsible_emails", task.get("responsible_email", []))
    if isinstance(emails, str):
        emails = [email.strip() for email in emails.split(",")]
    return [str(email) for email in emails if email]


def responsible_emails_text(task: dict[str, object]) -> str:
    return ", ".join(responsible_emails_list(task))


def add_attachments_to_task(
    task_index: int,
    uploaded_files: list[object],
    typed_attachment_names: str,
) -> tuple[bool, str]:
    if task_index < 0 or task_index >= len(st.session_state.tasks):
        return False, "Select an existing task."

    task = st.session_state.tasks[task_index]
    links = [line.strip() for line in typed_attachment_names.splitlines() if line.strip()]
    if not uploaded_files and not links:
        return False, "Choose a file or enter a link."
    apply_board_edit({
        "event_id": uuid4().hex, "task_id": task["id"],
        "updates": {"attachments": task.get("attachments", []) + links},
        "uploaded_files": upload_payload(uploaded_files),
    })
    result = st.session_state.board_save_result
    return result["ok"], "Files and links added." if result["ok"] else result["error"]


def task_option_label(task: dict[str, object]) -> str:
    return f"{task['project_id']} | {task['title']}"

def add_task(
    title: str,
    project_id: str,
    project: str,
    responsible_emails: list[str],
    status: str,
    due: str,
    description: str,
    attachments: list[str],
    uploaded_files: list[dict] | None = None,
    label_ids: list[str] | None = None, label_changes: list[dict] | None = None,
) -> tuple[bool, str]:
    # Normalize user input at the boundary so downstream rendering can assume
    # required fields are present and human-readable.
    cleaned_title = normalize_name(title)
    cleaned_project = normalize_name(project)
    cleaned_description = description.strip()

    if not cleaned_title:
        return False, "Task title is required."

    try:
        responsible_emails = clean_responsible_emails(responsible_emails)
    except ValueError as error:
        return False, str(error)

    task = {
        "id": uuid4().hex,
        "title": cleaned_title,
        "owner": "",  # Retain the legacy CSV field without assigning a role.
        "responsible_emails": responsible_emails,
        "responsible_email": ", ".join(responsible_emails),
        "status": status,
        "due": due,
        "project_id": project_id,
        "project": cleaned_project,
        "description": cleaned_description or "No additional details provided.",
        "attachments": attachments,
        "email_notification": False,
        "email_notification_status": "pending",
    }
    saved_files = []
    labels_written = False
    try:
        previous_labels = load_board_labels()
        catalog = merge_board_labels(previous_labels, label_changes or [])
        task["labels"] = list(dict.fromkeys(label_ids or []))
        if set(task["labels"]) - {label["id"] for label in catalog}:
            raise ValueError("A selected label no longer exists. Reload the board.")
        task["attachments"] = [clean_attachment_link(link) for link in attachments]
        saved_files = save_uploaded_files(task["id"], uploaded_files or [])
        task["attachments"].extend(saved_files)
        tasks = [*load_tasks_from_csv(), task]
        if catalog != previous_labels:
            write_board_labels(catalog)
            labels_written = True
        write_tasks_to_csv(tasks)
    except (OSError, ValueError) as error:
        cleanup_uploaded_files(saved_files)
        if labels_written:
            write_board_labels(previous_labels)
        return False, f"Task was not saved: {error}"
    st.session_state.tasks = tasks
    notification = send_new_task_notification(task)
    task["email_notification"] = notification["status"] == "sent"
    task["email_notification_status"] = notification["status"]
    try:
        latest_tasks = load_tasks_from_csv()
        saved_task = next(item for item in latest_tasks if item["id"] == task["id"])
        saved_task.update(email_notification=task["email_notification"], email_notification_status=task["email_notification_status"])
        write_tasks_to_csv(latest_tasks)
        st.session_state.tasks = latest_tasks
    except (OSError, StopIteration):
        notification = notification | {"message": notification["message"] + " The notification status could not be saved."}
    st.session_state.last_notification_result = notification
    st.session_state.last_added_task = task.copy()
    return True, f"Added task: {cleaned_title}."


def apply_new_task(event: dict) -> None:
    event_id = event.get("event_id")
    if not isinstance(event_id, str) or st.session_state.get("board_save_result", {}).get("event_id") == event_id:
        return
    try:
        updates = event.get("updates")
        allowed = {"title", "responsible_emails", "status", "due", "description", "attachments", "labels"}
        if not isinstance(updates, dict) or set(updates) != allowed:
            raise ValueError("The new task contains invalid fields.")
        for field, value in updates.items():
            if field in {"responsible_emails", "attachments", "labels"}:
                if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
                    raise ValueError(f"Invalid {field} value.")
            elif not isinstance(value, str):
                raise ValueError(f"Invalid {field} value.")
        if updates["status"] not in st.session_state.statuses:
            raise ValueError("Choose an existing column.")
        if updates["due"]:
            date.fromisoformat(updates["due"])
        changes = event.get("label_changes", [])
        if not isinstance(changes, list):
            raise ValueError("Invalid label changes.")
        success, message = add_task(
            updates["title"], "", "", updates["responsible_emails"], updates["status"],
            updates["due"], updates["description"], updates["attachments"],
            uploaded_files=event.get("uploaded_files", []), label_ids=updates["labels"], label_changes=changes,
        )
        st.session_state.board_save_result = {"event_id": event_id, "ok": success, "error": "" if success else message}
        if success:
            st.session_state.show_task_created_notice = True
    except (ValueError, OSError) as error:
        st.session_state.board_save_result = {"event_id": event_id, "ok": False, "error": f"Task was not saved: {error}"}


@st.dialog("Attach files to task")
def attach_files_dialog() -> None:
    selected_task_index = st.selectbox(
        "Existing task",
        range(len(st.session_state.tasks)),
        format_func=lambda index: task_option_label(st.session_state.tasks[index]),
    )
    current_attachments = st.session_state.tasks[selected_task_index].get("attachments", [])
    for index, item in enumerate(attachment_link_items(current_attachments)):
        if item.get("kind") == "link":
            st.link_button(item["name"], item["href"])
        elif item["href"]:
            mime, encoded = item["href"].split(";base64,", 1)
            st.download_button(item["name"], base64.b64decode(encoded), file_name=item["name"], mime=mime[5:], key=f"attachment_download_{selected_task_index}_{index}")
        else:
            st.caption(f"{item['name']} — file unavailable; upload it again.")
    uploaded_files = st.file_uploader(
        "Upload file",
        accept_multiple_files=True,
        key="dialog_existing_task_files",
    )
    typed_attachment_names = st.text_area(
        "Add link",
        placeholder="One https:// link per line",
        key="dialog_attachment_links",
    )

    if st.button("Attach files", type="primary", key="dialog_attach_existing_task_files"):
        success, message = add_attachments_to_task(
            selected_task_index,
            uploaded_files,
            typed_attachment_names,
        )
        if success:
            st.success(message)
            st.rerun()
        st.error(message)


@st.dialog("Manage people emails")
def manage_people_emails_dialog() -> None:
    st.caption("These emails are available when assigning responsible people to a task.")
    current_users = st.session_state.users
    st.write("Current emails")
    for email in current_users:
        st.markdown(f"- {escape(email)}")

    with st.form("add_people_emails_form"):
        raw_emails = st.text_area(
            "Add emails",
            placeholder="one.person@company.com, another.person@company.com",
        )
        add_emails_submitted = st.form_submit_button("Add emails")

    if add_emails_submitted:
        success, message = add_user_emails(raw_emails)
        if success:
            st.success(message)
            st.rerun()
        st.error(message)

    with st.form("remove_people_emails_form"):
        emails_to_remove = st.multiselect("Emails to remove", current_users)
        remove_emails_submitted = st.form_submit_button("Remove selected emails")

    if remove_emails_submitted:
        success, message = remove_user_emails(emails_to_remove)
        if success:
            st.success(message)
            st.rerun()
        st.error(message)

def build_board_html(statuses: list[str], tasks: list[dict[str, str]]) -> str:
    # Streamlit does not provide a native Planner-style drag-and-drop board, so
    # this function embeds a small self-contained HTML/CSS/JS app.
    board_tasks = [
        task | {"attachment_links": attachment_link_items(task.get("attachments", []))}
        for task in tasks
    ]
    board_data = {
        "statuses": statuses,
        "labels": load_board_labels(),
        "users": st.session_state.users,
        "tasks": board_tasks,
    }
    payload = json.dumps(board_data).replace("<", "\\u003c")

    return f"""
<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<style>
    :root {{
        color-scheme: light;
        font-family: Inter, "Segoe UI", Arial, sans-serif;
    }}
    body {{
        margin: 0;
        background: #ffffff;
        color: #0f172a;
    }}
    .board-wrap {{
        height: calc(100vh - 56px);
        min-height: 620px;
        overflow: auto;
        padding-bottom: 8px;
    }}
    .board {{
        display: grid;
        grid-template-columns: repeat(var(--column-count), minmax(215px, 1fr));
        grid-template-rows: auto 1fr;
        gap: 10px;
        min-width: calc(var(--column-count) * 225px - 10px);
    }}
    .column-header {{
        position: sticky;
        top: 0;
        z-index: 5;
        align-items: center;
        background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
        border: 1px solid #dbe3ef;
        border-radius: 8px;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
        color: #0f172a;
        display: grid;
        gap: 6px;
        grid-template-columns: 1fr auto auto;
        min-height: 42px;
        overflow: hidden;
        padding: 9px 10px 8px;
    }}
    .column-header {{ cursor: grab; }}
    .column-header:active {{
        cursor: grabbing;
        background: #e0e7ff;
        box-shadow: 0 6px 14px rgba(37, 99, 235, 0.18);
    }}
    .column-header.column-dragging {{
        background: #e0e7ff;
        box-shadow: 0 8px 18px rgba(37, 99, 235, 0.25);
        transform: translateY(-3px);
        opacity: 0.7;
    }}
    .dropzone.column-dragging {{ opacity: 0.45; }}
    .column-drop-before {{ border-left: 4px solid #2563eb; }}
    .column-drop-after {{ border-right: 4px solid #2563eb; }}
    .add-column-header {{
        align-self: start;
        background: #e2e8f0;
        border: 1px dashed #94a3b8;
        border-radius: 8px;
        box-shadow: inset 0 1px 3px rgba(15, 23, 42, 0.08);
        padding: 10px;
        position: sticky;
        top: 0;
        z-index: 5;
    }}
    .add-column-button {{
        background: transparent;
        border: 0;
        color: #475569;
        cursor: pointer;
        font: inherit;
        font-size: 13px;
        font-weight: 700;
        min-height: 40px;
        text-align: left;
        width: 100%;
    }}
    .add-column-actions {{ display: flex; gap: 6px; margin-top: 8px; }}
    .add-column-actions button {{
        border: 1px solid #cbd5e1;
        border-radius: 5px;
        background: #ffffff;
        cursor: pointer;
        padding: 7px 10px;
    }}
    .add-column-actions .primary {{ background: #2563eb; color: #ffffff; }}
    .column-header::before {{
        background: var(--status-accent, #64748b);
        content: "";
        height: 3px;
        inset: 0 0 auto;
        position: absolute;
    }}
    .column-title-wrap {{
        min-width: 0;
    }}
    .column-title {{
        background: transparent;
        border: 0;
        border-radius: 4px;
        color: inherit;
        cursor: text;
        font-family: inherit;
        padding: 3px 0;
        text-align: left;
        width: 100%;
        font-size: 12px;
        font-weight: 900;
        line-height: 1.15;
        overflow-wrap: anywhere;
        text-transform: uppercase;
    }}
    .column-title:hover {{
        background: #eff6ff;
    }}
    .column-title:focus-visible {{
        outline: 2px solid #2563eb;
        outline-offset: 2px;
    }}
    .column-title-input {{
        background: #ffffff;
        border: 1px solid #2563eb;
        border-radius: 4px;
        box-sizing: border-box;
        color: #0f172a;
        font: inherit;
        font-size: 12px;
        min-width: 0;
        padding: 6px;
        width: 100%;
    }}
    .column-title-error {{
        color: #b91c1c;
        font-size: 11px;
        overflow-wrap: anywhere;
    }}
    .column-count {{
        align-items: center;
        background: #f1f5f9;
        border: 1px solid #dbe3ef;
        border-radius: 999px;
        color: #475569;
        display: inline-flex;
        font-size: 11px;
        font-weight: 900;
        height: 22px;
        justify-content: center;
        min-width: 24px;
        padding: 0 7px;
    }}
    .header-add-task, .column-add-task {{
        align-items: center;
        background: transparent;
        border: 1px solid transparent;
        border-radius: 6px;
        color: #2563eb;
        cursor: pointer;
        display: inline-flex;
        font-family: inherit;
        font-weight: 700;
        justify-content: center;
    }}
    .header-add-task {{
        font-size: 23px;
        height: 30px;
        line-height: 1;
        width: 30px;
    }}
    .column-add-task {{
        flex-shrink: 0;
        font-size: 12px;
        gap: 6px;
        margin-top: auto;
        min-height: 38px;
        padding: 8px;
        width: 100%;
    }}
    .header-add-task:hover, .column-add-task:hover {{
        background: #eff6ff;
        border-color: #bfdbfe;
    }}
    .header-add-task:focus-visible, .column-add-task:focus-visible {{
        outline: 2px solid #2563eb;
        outline-offset: 2px;
    }}
    .dropzone {{
        display: flex;
        flex-direction: column;
        background: #f8fafc;
        border: 1px dashed #cbd5e1;
        border-radius: 8px;
        min-height: 168px;
        padding: 8px;
        transition: background 120ms ease, border-color 120ms ease;
    }}
    .dropzone.drag-over {{
        background: #eef6ff;
        border-color: #2563eb;
    }}
    .task-card {{
        flex-shrink: 0;
        background: #ffffff;
        border: 1px solid #dbe3ef;
        border-left: 4px solid #2563eb;
        border-radius: 8px;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.06);
        cursor: grab;
        margin-bottom: 9px;
        padding: 10px;
        user-select: none;
    }}
    .task-card:active {{
        cursor: grabbing;
    }}
    .task-card.completed {{ border-left-color: #16a34a; }}
    .task-card.rejected {{ border-left-color: #dc2626; }}
    .task-card.progress {{ border-left-color: #f59e0b; }}
    .task-card-header {{
        align-items: flex-start;
        display: flex;
        gap: 8px;
        justify-content: space-between;
        margin-bottom: 8px;
    }}
    .task-title {{
        color: #0f172a;
        flex: 1 1 auto;
        font-size: 14px;
        font-weight: 800;
        line-height: 1.25;
        min-width: 0;
        overflow-wrap: anywhere;
    }}
    .task-summary {{
        color: #475569;
        font-size: 12px;
        line-height: 1.45;
    }}
    .task-assignees {{
        display: flex;
        flex-wrap: wrap;
        gap: 5px;
        margin-top: 8px;
    }}
    .assignee-avatar {{
        align-items: center;
        background: #eff6ff;
        border: 1px solid #bfdbfe;
        border-radius: 50%;
        color: #1d4ed8;
        display: inline-flex;
        flex: 0 0 26px;
        font-size: 10px;
        font-weight: 800;
        height: 26px;
        justify-content: center;
        box-sizing: border-box;
        width: 26px;
    }}
    .due-stack {{
        align-items: center;
        display: inline-flex;
        flex-wrap: wrap;
        gap: 4px;
        margin-top: 2px;
        vertical-align: top;
    }}
    .due-history {{
        color: #94a3b8;
        display: inline-flex;
        flex-wrap: wrap;
        gap: 4px;
    }}
    .due-history span {{
        text-decoration: line-through;
    }}
    .due-history span::after {{
        color: #94a3b8;
        content: "->";
        display: inline-block;
        margin-left: 4px;
        text-decoration: none;
    }}
    .due-current {{
        border-radius: 4px;
        color: #334155;
        font-weight: 800;
        padding: 2px 5px;
    }}
    .due-current.due-soon {{
        background: #fef08a;
        color: #713f12;
    }}
    .due-current.due-overdue {{
        background: #fecaca;
        color: #991b1b;
    }}
    details {{
        border-top: 1px solid #e2e8f0;
        margin-top: 8px;
        padding-top: 7px;
    }}
    summary {{
        color: #2563eb;
        cursor: pointer;
        font-size: 12px;
        font-weight: 700;
    }}
    .task-details {{
        color: #475569;
        font-size: 12px;
        line-height: 1.45;
        margin-top: 6px;
    }}
    .hint {{
        color: #64748b;
        font-size: 12px;
        margin: 0 0 10px;
    }}
    .attachment-actions {{ display: flex; gap: 8px; margin: 6px 0; }}
    .attachment-actions button, #attachment-link-apply {{ border: 1px solid #cbd5e1; border-radius: 4px; background: #f8fafc; color: #334155; padding: 6px 10px; cursor: pointer; }}
    .attachment-row {{ display: flex; align-items: center; gap: 10px; padding: 5px 0; }}
    .attachment-row > :first-child {{ flex: 1; min-width: 0; }}
    .attachment-remove {{ border: 0; background: none; color: #64748b; cursor: pointer; }}
    #attachment-error {{ color: #b91c1c; font-size: 12px; }}
    .attachment-list {{
        display: grid;
        gap: 3px;
        margin-top: 4px;
    }}
    .attachment-list a {{
        color: #2563eb;
        font-weight: 700;
        overflow-wrap: anywhere;
    }}
    .attachment-list span {{
        color: #475569;
        overflow-wrap: anywhere;
    }}
    .modal-note {{
        color: #64748b;
        font-size: 12px;
        line-height: 1.35;
        margin-top: 4px;
    }}    .modal-backdrop {{
        align-items: flex-start;
        background: rgba(15, 23, 42, 0.38);
        display: none;
        inset: 0;
        justify-content: center;
        overflow-y: auto;
        padding: 20px 16px;
        position: fixed;
        z-index: 1000;
    }}
    .modal-backdrop.open {{
        display: flex;
    }}
    .task-modal {{
        background: #ffffff;
        border-radius: 8px;
        box-shadow: 0 22px 50px rgba(15, 23, 42, 0.22);
        max-height: calc(100vh - 40px);
        overflow-y: auto;
        padding: 18px;
        width: min(1100px, calc(100vw - 32px));
    }}
    .task-modal h3 {{
        font-size: 18px;
        line-height: 1.2;
        margin: 0 0 14px;
    }}

    .task-label-section {{ position: relative; }}
    .label-chips:empty {{ display: none; }}
    .label-chips {{ display: flex; flex-wrap: wrap; gap: 5px; margin: 6px 0; }}
    .label-chip {{ display: inline-block; padding: 5px 10px; border-radius: 4px; font-size: 12px; font-weight: 700; overflow-wrap: anywhere; }}
    .labels-button, .labels-wide-button, .label-editor-actions button {{ background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 4px; padding: 6px 10px; color: #334155; cursor: pointer; }}
    .labels-button:hover, .labels-wide-button:hover {{ background: #e2e8f0; }}
    .labels-popover {{ position: absolute; z-index: 30; top: 100%; left: 0; width: min(310px, 100%); box-sizing: border-box; padding: 12px; border: 1px solid #e2e8f0; border-radius: 8px; background: #fff; box-shadow: 0 8px 24px #0f172a33; }}
    .labels-heading {{ display: flex; justify-content: space-between; align-items: center; color: #475569; margin-bottom: 8px; }}
    .labels-heading button, .label-edit {{ cursor: pointer; background: none; border: 0; font-size: 18px; color: #475569; padding: 4px; }}
    #labels-options {{ max-height: 200px; overflow-y: auto; margin: 8px 0; }}
    .label-option {{ display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }}
    .label-option label {{ display: flex; align-items: center; gap: 8px; flex: 1; cursor: pointer; min-width: 0; }}
    .form-grid .label-option input {{ width: 16px; height: 16px; margin: 0; flex-shrink: 0; }}
    .label-option .label-chip {{ flex: 1; }}
    .labels-wide-button {{ width: 100%; margin-top: 8px; }}
    .label-colors {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 6px; margin: 8px 0; }}
    .label-colors button {{ min-height: 30px; border: 2px solid transparent; border-radius: 4px; cursor: pointer; }}
    .label-colors button[aria-pressed="true"] {{ border-color: #172b4d; outline: 2px solid #fff; outline-offset: -4px; }}
    .label-color-title {{ margin-top: 10px; color: #334155; font-size: 12px; font-weight: 800; }}
    .label-editor-actions {{ display: flex; gap: 8px; margin-top: 10px; }}
    #label-error {{ color: #b91c1c; font-size: 12px; margin-top: 6px; }}
    .creating-task .task-list-section, .creating-task .activity-panel {{ display: none; }}
    .creating-task .modal-layout {{ grid-template-columns: minmax(0, 1fr); }}
    .modal-layout {{
        display: grid;
        gap: 18px;
        grid-template-columns: minmax(0, 1fr) 340px;
    }}
    .modal-main {{
        min-width: 0;
    }}
    .form-grid {{
        display: grid;
        gap: 10px;
    }}
    .form-grid label,
    .field-label {{
        color: #334155;
        font-size: 12px;
        font-weight: 800;
    }}
    .form-grid input,
    .form-grid select,
    .form-grid textarea {{
        border: 1px solid #cbd5e1;
        border-radius: 6px;
        box-sizing: border-box;
        color: #0f172a;
        font: inherit;
        margin-top: 4px;
        padding: 8px;
        width: 100%;
    }}
    .form-grid textarea {{
        min-height: 82px;
        resize: vertical;
    }}
    .responsible-multiselect {{
        margin-top: 4px;
        position: relative;
    }}
    .responsible-control {{
        align-items: center;
        background: #f1f5f9;
        border: 1px solid #e2e8f0;
        border-radius: 6px;
        box-sizing: border-box;
        cursor: pointer;
        display: grid;
        gap: 8px;
        grid-template-columns: 1fr auto auto;
        min-height: 40px;
        padding: 6px 8px;
        width: 100%;
    }}
    .responsible-control.open {{
        border-color: #94a3b8;
        box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.10);
    }}
    .responsible-tags {{
        align-items: center;
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        min-width: 0;
    }}
    .responsible-placeholder {{
        color: #64748b;
        font-size: 13px;
        font-weight: 600;
    }}
    .responsible-chip {{
        align-items: center;
        background: #ff4b4b;
        border-radius: 6px;
        color: #ffffff;
        display: inline-flex;
        font-size: 12px;
        font-weight: 800;
        gap: 6px;
        max-width: 210px;
        min-height: 28px;
        padding: 4px 7px;
    }}
    .responsible-chip span {{
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }}
    .responsible-chip button,
    .responsible-clear {{
        align-items: center;
        background: rgba(255, 255, 255, 0.22);
        border: 0;
        border-radius: 999px;
        color: inherit;
        cursor: pointer;
        display: inline-flex;
        font-size: 12px;
        font-weight: 900;
        height: 18px;
        justify-content: center;
        line-height: 1;
        padding: 0;
        width: 18px;
    }}
    .responsible-clear {{
        background: #94a3b8;
        color: #ffffff;
    }}
    .responsible-caret {{
        color: #475569;
        font-size: 12px;
        font-weight: 900;
    }}
    .responsible-menu {{
        background: #ffffff;
        border: 1px solid #cbd5e1;
        border-radius: 6px;
        box-shadow: 0 12px 24px rgba(15, 23, 42, 0.14);
        display: none;
        left: 0;
        margin-top: 4px;
        max-height: 190px;
        overflow-y: auto;
        padding: 6px;
        position: absolute;
        right: 0;
        z-index: 20;
    }}
    .responsible-menu.open {{
        display: grid;
        gap: 4px;
    }}
    .responsible-add {{
        background: #ffffff;
        border-top: 1px solid #e2e8f0;
        bottom: -6px;
        display: flex;
        gap: 6px;
        padding: 8px 0 4px;
        position: sticky;
    }}
    .responsible-add input {{
        margin: 0;
        min-width: 0;
        flex: 1;
    }}
    .responsible-add button {{
        background: #eff6ff;
        border: 1px solid #bfdbfe;
        border-radius: 6px;
        color: #1d4ed8;
        cursor: pointer;
        font: inherit;
        padding: 6px 10px;
        white-space: nowrap;
    }}
    #responsible-email-error {{
        color: #b91c1c;
        font-size: 12px;
    }}
    .responsible-option {{
        align-items: center;
        border-radius: 5px;
        color: #334155;
        cursor: pointer;
        display: grid;
        font-size: 13px;
        font-weight: 700;
        gap: 8px;
        grid-template-columns: 16px 1fr;
        padding: 7px 8px;
    }}
    .responsible-option:hover {{
        background: #f1f5f9;
    }}
    .responsible-option input {{
        height: 14px;
        margin: 0;
        width: 14px;
    }}
    .responsible-option span {{
        overflow-wrap: anywhere;
    }}
    .task-list-section,
    .activity-panel {{
        border-top: 1px solid #e2e8f0;
        margin-top: 14px;
        padding-top: 12px;
    }}
    .activity-panel {{
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        margin-top: 0;
        padding: 12px;
    }}
    .section-title {{
        align-items: center;
        color: #0f172a;
        display: flex;
        font-size: 13px;
        font-weight: 900;
        gap: 8px;
        margin-bottom: 10px;
    }}
    .checklist-progress {{
        color: #64748b;
        font-size: 12px;
        font-weight: 800;
        margin-bottom: 6px;
    }}
    .checklist-bar {{
        background: #e2e8f0;
        border-radius: 999px;
        height: 7px;
        margin-bottom: 10px;
        overflow: hidden;
    }}
    .checklist-bar-fill {{
        background: #2563eb;
        height: 100%;
        width: 0%;
    }}
    .checklist-items {{
        display: grid;
        gap: 7px;
    }}
    .checklist-item {{
        align-items: flex-start;
        display: grid;
        gap: 8px;
        grid-template-columns: 18px 1fr auto;
    }}
    .checklist-item input {{
        height: 16px;
        margin-top: 2px;
        width: 16px;
    }}
    .checklist-item span {{
        color: #334155;
        font-size: 13px;
        line-height: 1.35;
        overflow-wrap: anywhere;
    }}
    .checklist-item.done span {{
        color: #64748b;
        text-decoration: line-through;
    }}
    .icon-button {{
        align-items: center;
        background: #ffffff;
        border: 1px solid #cbd5e1;
        border-radius: 6px;
        color: #475569;
        cursor: pointer;
        display: inline-flex;
        font-weight: 900;
        height: 26px;
        justify-content: center;
        line-height: 1;
        width: 26px;
    }}
    .inline-add {{
        display: grid;
        gap: 8px;
        grid-template-columns: 1fr auto;
        margin-top: 10px;
    }}
    .inline-add input,
    .comment-box textarea {{
        border: 1px solid #cbd5e1;
        border-radius: 6px;
        box-sizing: border-box;
        color: #0f172a;
        font: inherit;
        padding: 8px;
        width: 100%;
    }}
    .inline-add button,
    .comment-box button {{
        background: #2563eb;
        border: 1px solid #2563eb;
        border-radius: 6px;
        color: #ffffff;
        cursor: pointer;
        font-weight: 800;
        padding: 8px 10px;
    }}
    .comment-box textarea {{
        min-height: 74px;
        resize: vertical;
    }}
    .comment-box button {{
        margin-top: 8px;
        width: 100%;
    }}
    .activity-list {{
        display: grid;
        gap: 10px;
        margin-top: 12px;
    }}
    .activity-item {{
        display: grid;
        gap: 8px;
        grid-template-columns: 30px 1fr;
    }}
    .activity-avatar {{
        align-items: center;
        background: #4f46e5;
        border-radius: 999px;
        color: #ffffff;
        display: inline-flex;
        font-size: 13px;
        font-weight: 900;
        height: 30px;
        justify-content: center;
        width: 30px;
    }}
    .activity-text {{
        color: #334155;
        font-size: 13px;
        line-height: 1.35;
        overflow-wrap: anywhere;
    }}
    .activity-time {{
        color: #2563eb;
        font-size: 12px;
        margin-top: 2px;
    }}
    @media (max-width: 820px) {{
        .modal-layout {{
            grid-template-columns: 1fr;
        }}
    }}
    .modal-actions {{
        display: flex;
        gap: 8px;
        justify-content: flex-end;
        margin-top: 14px;
    }}
    .modal-actions button {{
        border: 1px solid #cbd5e1;
        border-radius: 6px;
        cursor: pointer;
        font-weight: 800;
        padding: 8px 12px;
    }}
    .modal-actions .primary {{
        background: #2563eb;
        border-color: #2563eb;
        color: #ffffff;
    }}
</style>
</head>
<body>
<p class="hint">Drag cards to change status. Drag column headers to reorder them, or click a title to rename it. Double-click a task to edit it.</p>
<p id="save-error" role="alert" style="color: #b91c1c;"></p>
<div class="board-wrap">
    <div id="board" class="board"></div>
</div>
<div id="edit-modal" class="modal-backdrop" aria-hidden="true">
    <div class="task-modal" role="dialog" aria-modal="true" aria-labelledby="edit-modal-title">
        <h3 id="edit-modal-title">Edit task</h3>
        <div class="modal-layout">
            <div class="modal-main">
                <div class="form-grid">
                    <label>Task title<input id="edit-title" type="text"></label>
                    <div class="task-label-section" id="task-label-section">
                        <div id="selected-labels" class="label-chips" aria-label="Selected labels"></div>
                        <button type="button" id="labels-toggle" class="labels-button" aria-expanded="false" aria-controls="labels-popover">◇ Labels</button>
                        <section id="labels-popover" class="labels-popover" hidden aria-label="Labels">
                            <div class="labels-heading"><strong>Labels</strong><button type="button" id="labels-close" aria-label="Close labels">×</button></div>
                            <div id="labels-list-view">
                                <input id="labels-search" type="search" placeholder="Search labels…" aria-label="Search labels">
                                <div id="labels-options"></div>
                                <button type="button" id="label-create" class="labels-wide-button">Create a new label</button>
                            </div>
                            <div id="label-editor" hidden>
                                <label>Label name<input id="label-name" type="text" maxlength="80"></label>
                                <div class="label-color-title">Color</div>
                                <div id="label-colors" class="label-colors" role="group" aria-label="Label color"></div>
                                <div id="label-preview" class="label-chip"></div>
                                <div class="label-editor-actions"><button type="button" id="label-apply">Apply label</button><button type="button" id="label-back">Back</button></div>
                                <div id="label-error" role="alert"></div>
                            </div>
                            <p class="modal-note">Labels and selections are saved with the task. Editing a label updates it across the board.</p>
                        </section>
                    </div>
                    <label>Details<textarea id="edit-description"></textarea></label>
                    <div class="field-label">Responsible people
                        <div class="responsible-multiselect" id="edit-responsible-people">
                            <div id="responsible-control" class="responsible-control" tabindex="0" role="button" aria-expanded="false">
                                <div id="responsible-tags" class="responsible-tags"></div>
                                <button type="button" id="responsible-clear" class="responsible-clear" title="Clear selected people">x</button>
                                <span class="responsible-caret">v</span>
                            </div>
                            <div id="responsible-menu" class="responsible-menu">
                                <div id="responsible-options"></div>
                                <div class="responsible-add">
                                    <input id="responsible-new-email" type="email" aria-label="New responsible email" placeholder="name@company.com">
                                    <button id="responsible-add-email" type="button">Add email</button>
                                </div>
                                <div id="responsible-email-error" role="alert"></div>
                            </div>
                        </div>
                    </div>
                    <label>Column/status<select id="edit-status"></select></label>
                    <label>Due date<input id="edit-due" type="date"></label>
                    <div class="attachment-section">
                        <div class="field-label">Files and links</div>
                        <div class="attachment-actions">
                            <button id="attachment-add-link" type="button">Add link</button>
                            <button id="attachment-upload" type="button">Upload file</button>
                            <input id="edit-uploaded-files" type="file" multiple hidden aria-label="Upload file">
                        </div>
                        <div id="attachment-link-form" hidden>
                            <label>Link or folder path<input id="attachment-link-input" type="text" placeholder="https://… or C:\\Program Files"></label>
                            <button id="attachment-link-apply" type="button">Add</button>
                        </div>
                        <div id="attachment-error" role="alert"></div>
                        <div id="edit-attachment-links" class="attachment-list"></div>
                        <div class="modal-note">Added links and files are saved with the task. Local folders: use Copy path if your browser blocks opening. Uploads: 20 MB total per save.</div>
                    </div>
                </div>
                <section class="task-list-section" aria-label="Task list">
                    <div class="section-title">Task list</div>
                    <div id="checklist-progress" class="checklist-progress">0%</div>
                    <div class="checklist-bar"><div id="checklist-bar-fill" class="checklist-bar-fill"></div></div>
                    <div id="checklist-items" class="checklist-items"></div>
                    <div class="inline-add">
                        <input id="checklist-new-item" type="text" placeholder="Add checklist item">
                        <button type="button" id="checklist-add">Add</button>
                    </div>
                </section>
            </div>
            <aside class="activity-panel" aria-label="Comments and activity">
                <div class="section-title">Comments and activity</div>
                <div class="comment-box">
                    <textarea id="comment-input" placeholder="Write a comment..."></textarea>
                    <button type="button" id="comment-add">Add comment</button>
                </div>
                <div id="activity-list" class="activity-list"></div>
            </aside>
        </div>
        <div class="modal-actions">
            <button type="button" id="edit-cancel">Cancel</button>
            <span id="edit-save-error" role="alert" style="color: #b91c1c;"></span>
            <button type="button" id="edit-save" class="primary">Save changes</button>
        </div>
    </div>
</div>
<script>
const data = {payload};
const board = document.getElementById("board");
const modal = document.getElementById("edit-modal");
let draggedId = null;
let editingTaskId = null;
let newTaskDraft = null;
let editingResponsibleEmails = [];
let pendingSaveId = null;
let pendingColumnRename = null;
let draggedColumn = null;
let suppressColumnClickUntil = 0;
let pendingColumnAdd = null;


let editingLabelIds = [];
let editingLabelCatalog = [];
let editingLabelChanges = {{}};
let editingLabelId = null;
let chosenLabelColor = "#4bce97";
const labelPalette = [
    ["Green", "#4bce97"], ["Yellow", "#f5cd47"], ["Orange", "#fea362"],
    ["Red", "#f87168"], ["Purple", "#9f8fef"], ["Blue", "#579dff"],
    ["Sky", "#6cc3e0"], ["Lime", "#94c748"], ["Pink", "#e774bb"], ["Gray", "#b6c2cf"],
];
function labelChip(label) {{
    const chip = document.createElement("span");
    chip.className = "label-chip";
    chip.textContent = label.name;
    chip.style.backgroundColor = label.color;
    // Use a contrasting text color even for labels imported with a custom color.
    const rgb = label.color.slice(1).match(/../g).map(value => parseInt(value, 16) / 255);
    const linear = rgb.map(value => value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4);
    chip.style.color = 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2] > 0.179 ? "#000000" : "#ffffff";
    return chip;
}}
function renderTaskLabels(container, ids, catalog = data.labels) {{
    container.replaceChildren();
    (ids || []).forEach(id => {{
        const label = catalog.find(value => value.id === id);
        if (label) container.appendChild(labelChip(label));
    }});
}}
function setLabelsOpen(open) {{
    document.getElementById("labels-popover").hidden = !open;
    document.getElementById("labels-toggle").setAttribute("aria-expanded", String(open));
    if (open) {{
        document.getElementById("label-editor").hidden = true;
        document.getElementById("labels-list-view").hidden = false;
        document.getElementById("labels-search").focus();
        renderLabelOptions();
    }}
}}
function renderLabelOptions() {{
    renderTaskLabels(document.getElementById("selected-labels"), editingLabelIds, editingLabelCatalog);
    const options = document.getElementById("labels-options");
    options.replaceChildren();
    const query = document.getElementById("labels-search").value.trim().toLocaleLowerCase();
    editingLabelCatalog.filter(label => label.name.toLocaleLowerCase().includes(query)).forEach(label => {{
        const row = document.createElement("div");
        row.className = "label-option";
        const choice = document.createElement("label");
        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.checked = editingLabelIds.includes(label.id);
        checkbox.addEventListener("change", () => {{
            editingLabelIds = checkbox.checked ? uniqueValues([...editingLabelIds, label.id]) : editingLabelIds.filter(id => id !== label.id);
            renderTaskLabels(document.getElementById("selected-labels"), editingLabelIds, editingLabelCatalog);
        }});
        choice.append(checkbox, labelChip(label));
        const edit = document.createElement("button");
        edit.type = "button";
        edit.className = "label-edit";
        edit.textContent = "✎";
        edit.setAttribute("aria-label", `Edit label ${{label.name}}`);
        edit.addEventListener("click", () => openLabelEditor(label));
        row.append(choice, edit);
        options.appendChild(row);
    }});
    if (!options.childElementCount) {{
        const empty = document.createElement("p");
        empty.className = "modal-note";
        empty.textContent = query ? "No matching labels." : "No labels yet. Create your first label.";
        options.appendChild(empty);
    }}
}}
function updateLabelPreview() {{
    const preview = document.getElementById("label-preview");
    preview.replaceChildren(labelChip({{name: document.getElementById("label-name").value.trim() || "Label preview", color: chosenLabelColor}}));
}}
function openLabelEditor(label = null) {{
    editingLabelId = label?.id || null;
    chosenLabelColor = label?.color || labelPalette[0][1];
    document.getElementById("labels-list-view").hidden = true;
    document.getElementById("label-editor").hidden = false;
    document.getElementById("label-error").textContent = "";
    document.getElementById("label-name").value = label?.name || "";
    const colors = document.getElementById("label-colors");
    colors.replaceChildren();
    labelPalette.forEach(([name, color]) => {{
        const button = document.createElement("button");
        button.type = "button";
        button.style.backgroundColor = color;
        button.setAttribute("aria-label", name);
        button.setAttribute("aria-pressed", String(color === chosenLabelColor));
        button.addEventListener("click", () => {{
            chosenLabelColor = color;
            colors.querySelectorAll("button").forEach(item => item.setAttribute("aria-pressed", String(item === button)));
            updateLabelPreview();
        }});
        colors.appendChild(button);
    }});
    updateLabelPreview();
    document.getElementById("label-name").focus();
}}
function applyLabelEditor() {{
    const name = document.getElementById("label-name").value.trim().replace(/\\s+/g, " ");
    const error = document.getElementById("label-error");
    if (!name || name.length > 80) {{ error.textContent = "Enter a label name (1–80 characters)."; return; }}
    if (editingLabelCatalog.some(label => label.id !== editingLabelId && label.name.toLocaleLowerCase() === name.toLocaleLowerCase())) {{
        error.textContent = "A label with this name already exists."; return;
    }}
    const id = editingLabelId || globalThis.crypto?.randomUUID?.() || `label-${{Date.now()}}-${{Math.random().toString(36).slice(2)}}`;
    const label = {{id, name, color: chosenLabelColor}};
    editingLabelCatalog = [...editingLabelCatalog.filter(item => item.id !== id), label];
    editingLabelChanges[id] = label;
    if (!editingLabelId) editingLabelIds = uniqueValues([...editingLabelIds, id]);
    document.getElementById("labels-search").value = "";
    setLabelsOpen(true);
}}
document.getElementById("labels-toggle").addEventListener("click", () => setLabelsOpen(document.getElementById("labels-popover").hidden));
document.getElementById("labels-close").addEventListener("click", () => {{ setLabelsOpen(false); document.getElementById("labels-toggle").focus(); }});
document.getElementById("labels-search").addEventListener("input", renderLabelOptions);
document.getElementById("label-create").addEventListener("click", () => openLabelEditor());
document.getElementById("label-apply").addEventListener("click", applyLabelEditor);
document.getElementById("label-back").addEventListener("click", () => setLabelsOpen(true));
document.getElementById("label-name").addEventListener("input", updateLabelPreview);
document.getElementById("label-name").addEventListener("keydown", event => {{
    if (event.key === "Enter") {{ event.preventDefault(); applyLabelEditor(); }}
}});
document.getElementById("labels-popover").addEventListener("keydown", event => {{
    if (event.key === "Escape") {{ event.stopPropagation(); setLabelsOpen(false); document.getElementById("labels-toggle").focus(); }}
}});
document.addEventListener("click", event => {{
    if (!document.getElementById("task-label-section").contains(event.target)) setLabelsOpen(false);
}});

function persistTask(task, updates, labelChanges = [], uploadedFiles = []) {{
    if (pendingSaveId) return;
    pendingSaveId = globalThis.crypto?.randomUUID?.() || `${{Date.now()}}-${{Math.random().toString(36).slice(2)}}`;
    document.getElementById("save-error").textContent = "";
    document.getElementById("edit-save-error").textContent = "";
    document.getElementById("edit-save").disabled = true;
    document.getElementById("edit-save").textContent = "Saving…";
    board.style.pointerEvents = "none";
    window.parent.postMessage({{
        type: "planner:save", value: {{event_id: pendingSaveId, action: newTaskDraft ? "create_task" : "edit_task", task_id: task.id, updates, label_changes: labelChanges, uploaded_files: uploadedFiles}},
    }}, "*");
}}

window.addEventListener("message", event => {{
    if (event.source !== window.parent) return;
    if (event.data?.type === "planner:reveal-column-creator") {{
        const wrap = document.querySelector(".board-wrap");
        wrap.scrollLeft = wrap.scrollWidth;
        document.querySelector(".add-column-button").click();
        return;
    }}
    if (event.data?.type !== "planner:save-result") return;
    const result = event.data.result;
    if (!result || result.event_id !== pendingSaveId) return;
    pendingSaveId = null;
    board.style.pointerEvents = "";
    if (pendingColumnRename || pendingColumnAdd) {{
        const editor = pendingColumnRename || pendingColumnAdd;
        pendingColumnRename = null;
        pendingColumnAdd = null;
        editor.input.disabled = false;
        if (result.ok) {{
            if (editor.close) editor.close();
            else {{
                editor.input.hidden = true;
                editor.title.hidden = false;
            }}
        }} else {{
            editor.error.textContent = result.error;
            editor.input.setAttribute("aria-invalid", "true");
            editor.input.focus();
        }}
        return;
    }}
    document.getElementById("edit-save").disabled = false;
    document.getElementById("edit-save").textContent = newTaskDraft ? "Add task" : "Save changes";
    if (result.ok) {{
        closeEditModal();
    }} else {{
        document.getElementById("save-error").textContent = result.error;
        document.getElementById("edit-save-error").textContent = result.error;
    }}
}});

function cardClass(status) {{
    const lowered = status.toLowerCase();
    if (lowered.includes("completed") || lowered.includes("done")) return "task-card completed";
    if (lowered.includes("rejected") || lowered.includes("cancel")) return "task-card rejected";
    if (lowered.includes("progress") || lowered.includes("active")) return "task-card progress";
    return "task-card";
}}

function text(value) {{
    return String(value ?? "");
}}

function findTask(taskId) {{
    return data.tasks.find(task => task.id === taskId);
}}

function fillSelect(select, options, selectedValue) {{
    select.innerHTML = "";
    const selectedValues = Array.isArray(selectedValue) ? selectedValue : [selectedValue];
    options.forEach(optionValue => {{
        const option = document.createElement("option");
        option.value = optionValue;
        option.textContent = optionValue;
        option.selected = selectedValues.includes(optionValue);
        select.appendChild(option);
    }});
}}

function selectedOptions(select) {{
    return Array.from(select.selectedOptions).map(option => option.value).filter(Boolean);
}}

function uniqueValues(values) {{
    return Array.from(new Set(values.filter(Boolean)));
}}

function setResponsibleMenuOpen(isOpen) {{
    const control = document.getElementById("responsible-control");
    const menu = document.getElementById("responsible-menu");
    control.classList.toggle("open", isOpen);
    control.setAttribute("aria-expanded", String(isOpen));
    menu.classList.toggle("open", isOpen);
}}

function syncResponsiblePicker() {{
    const tags = document.getElementById("responsible-tags");
    const menu = document.getElementById("responsible-options");
    tags.innerHTML = "";
    menu.innerHTML = "";

    if (!editingResponsibleEmails.length) {{
        const placeholder = document.createElement("span");
        placeholder.className = "responsible-placeholder";
        placeholder.textContent = "Choose responsible people";
        tags.appendChild(placeholder);
    }}

    editingResponsibleEmails.forEach(email => {{
        const chip = document.createElement("span");
        chip.className = "responsible-chip";
        const label = document.createElement("span");
        label.textContent = email;
        const remove = document.createElement("button");
        remove.type = "button";
        remove.title = `Remove ${{email}}`;
        remove.textContent = "x";
        remove.addEventListener("click", event => {{
            event.stopPropagation();
            editingResponsibleEmails = editingResponsibleEmails.filter(value => value !== email);
            syncResponsiblePicker();
        }});
        chip.appendChild(label);
        chip.appendChild(remove);
        tags.appendChild(chip);
    }});

    data.users.forEach(email => {{
        const row = document.createElement("label");
        row.className = "responsible-option";
        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.value = email;
        checkbox.checked = editingResponsibleEmails.includes(email);
        checkbox.addEventListener("change", () => {{
            if (checkbox.checked) {{
                editingResponsibleEmails = uniqueValues([...editingResponsibleEmails, email]);
            }} else {{
                editingResponsibleEmails = editingResponsibleEmails.filter(value => value !== email);
            }}
            syncResponsiblePicker();
        }});
        const label = document.createElement("span");
        label.textContent = email;
        row.appendChild(checkbox);
        row.appendChild(label);
        menu.appendChild(row);
    }});
}}

function addResponsibleEmail() {{
    const input = document.getElementById("responsible-new-email");
    const email = input.value.trim().toLowerCase();
    const error = document.getElementById("responsible-email-error");
    if (!/^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$/u.test(email)) {{
        error.textContent = "Enter a valid email address, for example name@company.com.";
        input.focus();
        return;
    }}
    error.textContent = "";
    data.users = uniqueValues([...data.users, email]);
    editingResponsibleEmails = uniqueValues([...editingResponsibleEmails, email]);
    input.value = "";
    syncResponsiblePicker();
    input.focus();
}}

document.getElementById("responsible-add-email").addEventListener("click", addResponsibleEmail);
document.getElementById("responsible-new-email").addEventListener("keydown", event => {{
    if (event.key === "Enter") {{
        event.preventDefault();
        addResponsibleEmail();
    }}
}});

function renderResponsiblePicker(selectedValues) {{
    document.getElementById("responsible-new-email").value = "";
    document.getElementById("responsible-email-error").textContent = "";
    const selected = Array.isArray(selectedValues) ? selectedValues : [selectedValues];
    editingResponsibleEmails = uniqueValues(selected);
    syncResponsiblePicker();
    setResponsibleMenuOpen(false);
}}

function selectedResponsibleEmails() {{
    return editingResponsibleEmails.slice();
}}

function taskResponsibleEmails(task) {{
    if (Array.isArray(task.responsible_emails)) return task.responsible_emails;
    const legacyEmail = text(task.responsible_email);
    return legacyEmail ? legacyEmail.split(",").map(value => value.trim()).filter(Boolean) : [];
}}

function responsibleEmailsText(task) {{
    return taskResponsibleEmails(task).join(", ");
}}

function assigneeInitials(email) {{
    const name = text(email).split("@")[0].trim();
    const parts = name.split(/[\\s._+-]+/u).filter(Boolean);
    if (!parts.length) return "?";
    return (parts.length > 1
        ? Array.from(parts[0])[0] + Array.from(parts[parts.length - 1])[0]
        : Array.from(parts[0]).slice(0, 2).join("")).toUpperCase();
}}

function renderAssignees(container, task) {{
    container.replaceChildren();
    const emails = [...new Set(taskResponsibleEmails(task).map(email => text(email).trim()).filter(Boolean))];
    emails.forEach(email => {{
        const avatar = document.createElement("span");
        avatar.className = "assignee-avatar";
        avatar.textContent = assigneeInitials(email);
        avatar.title = email;
        avatar.setAttribute("role", "img");
        avatar.setAttribute("aria-label", email);
        container.appendChild(avatar);
    }});
}}

function updateColumnCounts() {{
    board.querySelectorAll(".column-header").forEach(header => {{
        header.querySelector(".column-count").textContent = data.tasks.filter(task => task.status === header.dataset.status).length;
    }});
}}

function statusAccent(status) {{
    const lowered = status.toLowerCase();
    if (lowered.includes("completed") || lowered.includes("done")) return "#16a34a";
    if (lowered.includes("rejected") || lowered.includes("cancel")) return "#dc2626";
    if (lowered.includes("progress") || lowered.includes("active")) return "#f59e0b";
    if (lowered.includes("backlog") || lowered.includes("todo") || lowered.includes("to do")) return "#2563eb";
    return "#64748b";
}}

function createAddTaskButton(status, inHeader = false) {{
    const button = document.createElement("button");
    button.type = "button";
    button.className = inHeader ? "header-add-task" : "column-add-task";
    button.textContent = inHeader ? "+" : "+ Add task";
    button.title = `Add task to ${{status}}`;
    button.setAttribute("aria-label", `Add task to ${{status}}`);
    button.addEventListener("click", () => {{
        if (pendingSaveId) return;
        openNewTask(status);
    }});
    return button;
}}

function createColumnTitle(status) {{
    const wrapper = document.createElement("div");
    wrapper.className = "column-title-wrap";
    const title = document.createElement("button");
    title.type = "button";
    title.className = "column-title";
    title.draggable = true;
    title.textContent = status;
    title.title = "Click to rename column";
    title.setAttribute("aria-label", `Rename column ${{status}}`);
    const input = document.createElement("input");
    input.type = "text";
    input.className = "column-title-input";
    input.setAttribute("aria-label", `Column name for ${{status}}`);
    input.hidden = true;
    const error = document.createElement("div");
    error.className = "column-title-error";
    error.setAttribute("role", "alert");

    function cancel() {{
        input.hidden = true;
        title.hidden = false;
        error.textContent = "";
        input.removeAttribute("aria-invalid");
    }}
    function save() {{
        if (input.hidden || pendingSaveId) return;
        const name = input.value.trim().replace(/\\s+/g, " ");
        error.textContent = "";
        input.removeAttribute("aria-invalid");
        if (name === status) {{ cancel(); return; }}
        if (!name || data.statuses.includes(name)) {{
            error.textContent = name ? "Column names must be unique." : "Enter a column name.";
            input.setAttribute("aria-invalid", "true");
            return;
        }}
        pendingSaveId = globalThis.crypto?.randomUUID?.() || `${{Date.now()}}-${{Math.random().toString(36).slice(2)}}`;
        pendingColumnRename = {{input, title, error}};
        input.disabled = true;
        board.style.pointerEvents = "none";
        window.parent.postMessage({{
            type: "planner:rename-column",
            value: {{action: "rename_column", status, name, event_id: pendingSaveId}},
        }}, "*");
    }}
    title.addEventListener("click", () => {{
        if (pendingSaveId || Date.now() < suppressColumnClickUntil) return;
        title.hidden = true;
        input.hidden = false;
        input.value = status;
        input.focus();
        input.select();
    }});
    input.addEventListener("keydown", event => {{
        if (event.key === "Enter") {{ event.preventDefault(); save(); }}
        if (event.key === "Escape") {{
            event.preventDefault();
            event.stopPropagation();
            cancel();
            title.focus();
        }}
    }});
    input.addEventListener("blur", save);
    wrapper.append(title, input, error);
    return wrapper;
}}

function clearColumnDrag() {{
    board.querySelectorAll(".column-dragging, .column-drop-before, .column-drop-after").forEach(element => {{
        element.classList.remove("column-dragging", "column-drop-before", "column-drop-after");
    }});
    draggedColumn = null;
}}

function enableColumnDrop(element, status) {{
    element.addEventListener("dragover", event => {{
        if (!draggedColumn || draggedColumn === status || pendingSaveId) return;
        event.preventDefault();
        event.dataTransfer.dropEffect = "move";
        const rect = element.getBoundingClientRect();
        const after = event.clientX > rect.left + rect.width / 2;
        element.classList.toggle("column-drop-before", !after);
        element.classList.toggle("column-drop-after", after);
    }});
    element.addEventListener("dragleave", () => {{
        element.classList.remove("column-drop-before", "column-drop-after");
    }});
    element.addEventListener("drop", event => {{
        if (!draggedColumn || pendingSaveId) return;
        event.preventDefault();
        event.stopPropagation();
        const moving = draggedColumn;
        const rect = element.getBoundingClientRect();
        const position = event.clientX > rect.left + rect.width / 2 ? "after" : "before";
        clearColumnDrag();
        if (moving === status) return;
        pendingSaveId = globalThis.crypto?.randomUUID?.() || `${{Date.now()}}-${{Math.random().toString(36).slice(2)}}`;
        board.style.pointerEvents = "none";
        document.getElementById("save-error").textContent = "";
        window.parent.postMessage({{
            type: "planner:column-action",
            value: {{action: "move_column", status: moving, target: status, position, event_id: pendingSaveId}},
        }}, "*");
    }});
}}

function createAddColumnHeader() {{
    const header = document.createElement("div");
    header.className = "add-column-header";
    const title = document.createElement("button");
    title.type = "button";
    title.className = "add-column-button";
    title.textContent = "+ Add column";
    const form = document.createElement("div");
    form.className = "add-column-form";
    form.hidden = true;
    const input = document.createElement("input");
    input.className = "column-title-input";
    input.placeholder = "Column name";
    input.setAttribute("aria-label", "New column name");
    const error = document.createElement("div");
    error.className = "column-title-error";
    error.setAttribute("role", "alert");
    const actions = document.createElement("div");
    actions.className = "add-column-actions";
    const save = document.createElement("button");
    save.type = "button";
    save.className = "primary";
    save.textContent = "Add column";
    const cancel = document.createElement("button");
    cancel.type = "button";
    cancel.textContent = "Cancel";
    function close() {{
        if (pendingSaveId) return;
        form.hidden = true;
        title.hidden = false;
        input.hidden = false;
        input.disabled = false;
        error.textContent = "";
        input.value = "";
    }}
    function submit() {{
        if (pendingSaveId) return;
        const name = input.value.trim().replace(/\\s+/g, " ");
        if (!name || data.statuses.includes(name)) {{
            error.textContent = name ? "This column already exists." : "Enter a column name.";
            return;
        }}
        pendingSaveId = globalThis.crypto?.randomUUID?.() || `${{Date.now()}}-${{Math.random().toString(36).slice(2)}}`;
        pendingColumnAdd = {{input, title, error, close}};
        input.disabled = true;
        board.style.pointerEvents = "none";
        window.parent.postMessage({{
            type: "planner:column-action",
            value: {{action: "add_column", name, event_id: pendingSaveId}},
        }}, "*");
    }}
    title.addEventListener("click", () => {{
        if (pendingSaveId) return;
        title.hidden = true;
        form.hidden = false;
        input.hidden = false;
        input.focus();
    }});
    save.addEventListener("click", submit);
    cancel.addEventListener("click", close);
    input.addEventListener("keydown", event => {{
        if (event.key === "Enter") {{ event.preventDefault(); submit(); }}
        if (event.key === "Escape") {{ event.preventDefault(); close(); title.focus(); }}
    }});
    actions.append(save, cancel);
    form.append(input, error, actions);
    header.append(title, form);
    board.appendChild(header);
}}

function createColumnHeader(status) {{
    const header = document.createElement("div");
    const taskCount = data.tasks.filter(task => task.status === status).length;
    header.className = "column-header";
    header.dataset.status = status;
    header.draggable = true;
    header.title = "Drag to move this column; click its title to rename";
    header.addEventListener("dragstart", event => {{
        if (pendingSaveId || !header.querySelector(".column-title-input").hidden
                || event.target.closest("input, .header-add-task")) {{
            event.preventDefault();
            return;
        }}
        draggedColumn = status;
        draggedId = null;
        suppressColumnClickUntil = Date.now() + 500;
        event.dataTransfer.effectAllowed = "move";
        event.dataTransfer.setData("application/x-kanban-column", status);
        header.classList.add("column-dragging");
        board.querySelectorAll(".dropzone").forEach(zone => {{
            if (zone.dataset.status === status) zone.classList.add("column-dragging");
        }});
    }});
    header.addEventListener("dragend", () => {{
        suppressColumnClickUntil = Date.now() + 200;
        clearColumnDrag();
    }});
    enableColumnDrop(header, status);
    header.style.setProperty("--status-accent", statusAccent(status));

    const title = createColumnTitle(status);

    const count = document.createElement("span");
    count.className = "column-count";
    count.textContent = taskCount;

    header.appendChild(title);
    header.appendChild(count);
    header.appendChild(createAddTaskButton(status, true));
    board.appendChild(header);
    return header;
}}

let editingAttachments = [];
let editingUploads = [];
let attachmentReadPending = false;
let attachmentSession = 0;

function renderAttachmentLinks(container, task, removeItem = null) {{
    (container.attachmentUrls || []).forEach(url => URL.revokeObjectURL(url));
    container.attachmentUrls = [];
    container.replaceChildren();
    const links = task.attachment_links || [];
    if (!links.length) {{
        const empty = document.createElement("span");
        empty.textContent = "No files or links attached";
        container.appendChild(empty);
        return;
    }}
    links.forEach((item, index) => {{
        const row = document.createElement("div");
        row.className = "attachment-row";
        let href = item.href || "";
        const file = href.startsWith("data:");
        if (file) {{
            const [header, encoded] = href.split(",", 2);
            const mime = header.slice(5).split(";")[0];
            const bytes = Uint8Array.from(atob(encoded), char => char.charCodeAt(0));
            href = URL.createObjectURL(new Blob([bytes], {{type: mime}}));
            container.attachmentUrls.push(href);
        }}
        if (href && (file || item.kind === "folder" || /^https?:\\/\\//i.test(href))) {{
            const link = document.createElement("a");
            link.href = href;
            link.textContent = item.name;
            link.target = "_blank";
            link.rel = "noopener noreferrer";
            if (file) {{
                link.download = item.name;
                link.title = `Download ${{item.name}}`;
            }}
            row.appendChild(link);
            if (item.kind === "folder") {{
                link.title = "Open folder (your browser may block local links)";
                const copy = document.createElement("button");
                copy.type = "button";
                copy.className = "attachment-remove";
                copy.textContent = "Copy path";
                copy.addEventListener("click", async () => {{
                    try {{
                        const path = item.reference || item.name;
                        if (navigator.clipboard?.writeText) await navigator.clipboard.writeText(path);
                        else {{
                            const input = document.createElement("textarea");
                            input.value = path;
                            row.appendChild(input);
                            input.select();
                            const copied = document.execCommand("copy");
                            input.remove();
                            if (!copied) throw new Error();
                        }}
                        copy.textContent = "Copied";
                    }} catch (_) {{
                        copy.textContent = "Select and copy the path";
                    }}
                }});
                row.appendChild(copy);
            }}
            if (file && item.preview) {{
                const open = document.createElement("a");
                open.href = href;
                open.textContent = "Open";
                open.target = "_blank";
                open.rel = "noopener noreferrer";
                open.setAttribute("aria-label", `Open ${{item.name}}`);
                row.appendChild(open);
            }}
        }} else {{
            const name = document.createElement("span");
            name.textContent = `${{item.name}} — unavailable; upload the file again`;
            row.appendChild(name);
        }}
        if (removeItem) {{
            const remove = document.createElement("button");
            remove.type = "button";
            remove.className = "attachment-remove";
            remove.textContent = "×";
            remove.setAttribute("aria-label", `Remove ${{item.name}}`);
            remove.addEventListener("click", () => removeItem(index));
            row.appendChild(remove);
        }}
        // Attachment interactions must not drag the card or open the task editor.
        row.addEventListener("dblclick", event => event.stopPropagation());
        row.addEventListener("dragstart", event => {{ event.preventDefault(); event.stopPropagation(); }});
        container.appendChild(row);
    }});
}}
function renderEditingAttachments() {{
    const all = [...editingAttachments, ...editingUploads];
    renderAttachmentLinks(document.getElementById("edit-attachment-links"), {{attachment_links: all}}, index => {{
        if (index < editingAttachments.length) editingAttachments.splice(index, 1);
        else editingUploads.splice(index - editingAttachments.length, 1);
        renderEditingAttachments();
    }});
}}
function folderUri(value) {{
    if (/^[a-z]:[\\\\/]/i.test(value)) return "file:///" + encodeURI(value.replace(/\\\\/g, "/")).replace(/#/g, "%23").replace(/\\?/g, "%3F");
    if (value.startsWith("\\\\\\\\")) return "file://" + encodeURI(value.slice(2).replace(/\\\\/g, "/")).replace(/#/g, "%23").replace(/\\?/g, "%3F");
    if (value.startsWith("/")) return "file://" + encodeURI(value).replace(/#/g, "%23").replace(/\\?/g, "%3F");
    if (/^file:\\/\\//i.test(value)) return value;
    return null;
}}
function addAttachmentLink() {{
    const input = document.getElementById("attachment-link-input");
    const value = input.value.trim();
    const error = document.getElementById("attachment-error");
    const folder = folderUri(value);
    try {{
        if (!folder) {{
            const parsed = new URL(value);
            if (!["http:", "https:"].includes(parsed.protocol) || !parsed.hostname || /\\s/.test(value)) throw new Error();
        }}
    }} catch (_) {{
        error.textContent = "Enter a web link or an absolute local/shared folder path.";
        return false;
    }}
    if (!editingAttachments.some(item => item.reference === value)) editingAttachments.push({{reference: value, name: value, href: folder || value, kind: folder ? "folder" : "link"}});
    error.textContent = "";
    input.value = "";
    document.getElementById("attachment-link-form").hidden = true;
    renderEditingAttachments();
    return true;
}}
function readUpload(file) {{
    return new Promise((resolve, reject) => {{
        const reader = new FileReader();
        reader.onerror = () => reject(new Error(`Could not read ${{file.name}}. Select it again.`));
        reader.onabort = () => reject(new Error("File reading was cancelled."));
        reader.onload = () => {{
            const data = reader.result.split(",", 2)[1];
            const preview = ["application/pdf", "text/plain", "image/png", "image/jpeg", "image/gif", "image/webp"].includes(file.type);
            const mime = preview ? file.type : "application/octet-stream";
            resolve({{name: file.name, data, size: file.size, preview, href: `data:${{mime}};base64,${{data}}`, kind: "file"}});
        }};
        reader.readAsDataURL(file);
    }});
}}
document.getElementById("attachment-add-link").addEventListener("click", () => {{
    document.getElementById("attachment-link-form").hidden = false;
    document.getElementById("attachment-link-input").focus();
}});
document.getElementById("attachment-link-apply").addEventListener("click", addAttachmentLink);
document.getElementById("attachment-link-input").addEventListener("keydown", event => {{
    if (event.key === "Enter") {{ event.preventDefault(); addAttachmentLink(); }}
}});
document.getElementById("attachment-upload").addEventListener("click", () => document.getElementById("edit-uploaded-files").click());
document.getElementById("edit-uploaded-files").addEventListener("change", async event => {{
    const files = Array.from(event.target.files);
    const session = attachmentSession;
    const error = document.getElementById("attachment-error");
    error.textContent = "";
    if (files.length + editingUploads.length > 50 || [...files, ...editingUploads].reduce((sum, file) => sum + file.size, 0) > 20 * 1024 * 1024) {{
        error.textContent = "Choose up to 50 files, totaling 20 MB or less per save.";
        event.target.value = "";
        return;
    }}
    attachmentReadPending = true;
    document.getElementById("edit-save").disabled = true;
    document.getElementById("attachment-upload").disabled = true;
    error.textContent = "Reading files…";
    try {{
        const uploads = await Promise.all(files.map(readUpload));
        if (session !== attachmentSession) return;
        editingUploads.push(...uploads);
        error.textContent = "";
        renderEditingAttachments();
    }} catch (failure) {{
        if (session === attachmentSession) error.textContent = failure.message;
    }} finally {{
        if (session === attachmentSession) {{
            attachmentReadPending = false;
            document.getElementById("edit-save").disabled = Boolean(pendingSaveId);
            document.getElementById("attachment-upload").disabled = false;
            event.target.value = "";
        }}
    }}
}});

function taskStoreKey(task) {{
    return `ewm-task-meta:${{task.storage_key || task.id}}`;
}}

function taskMeta(task) {{
    if (task._meta) return task._meta;
    const fallback = {{ checklist: [], comments: [], activity: [], due_history: [] }};
    try {{
        task._meta = {{ ...fallback, ...JSON.parse(localStorage.getItem(taskStoreKey(task)) || "{{}}") }};
    }} catch (error) {{
        task._meta = fallback;
    }}
    task._meta.checklist = Array.isArray(task._meta.checklist) ? task._meta.checklist : [];
    task._meta.comments = Array.isArray(task._meta.comments) ? task._meta.comments : [];
    task._meta.activity = Array.isArray(task._meta.activity) ? task._meta.activity : [];
    task._meta.due_history = Array.isArray(task._meta.due_history) ? task._meta.due_history : [];
    return task._meta;
}}

function saveTaskMeta(task) {{
    try {{
        localStorage.setItem(taskStoreKey(task), JSON.stringify(taskMeta(task)));
    }} catch (error) {{
        // Browser metadata is optional; it must not prevent saving the ticket.
    }}
}}

function nowLabel() {{
    return new Date().toLocaleString([], {{ year: "numeric", month: "short", day: "2-digit", hour: "2-digit", minute: "2-digit" }});
}}

function currentUserLabel() {{
    const selectedUsers = selectedResponsibleEmails();
    const user = text(selectedUsers[0] || data.users[0] || "User");
    return user.includes("@") ? user.split("@")[0] : user;
}}

function addActivity(task, message) {{
    const meta = taskMeta(task);
    meta.activity.unshift({{ author: currentUserLabel(), message, time: nowLabel() }});
    meta.activity = meta.activity.slice(0, 30);
    saveTaskMeta(task);
    renderActivity(task);
}}

function renderChecklist(task) {{
    const meta = taskMeta(task);
    const container = document.getElementById("checklist-items");
    container.innerHTML = "";
    const completed = meta.checklist.filter(item => item.done).length;
    const total = meta.checklist.length;
    const percent = total ? Math.round((completed / total) * 100) : 0;
    document.getElementById("checklist-progress").textContent = `${{percent}}% complete`;
    document.getElementById("checklist-bar-fill").style.width = `${{percent}}%`;

    if (!total) {{
        const empty = document.createElement("div");
        empty.className = "modal-note";
        empty.textContent = "No checklist items yet.";
        container.appendChild(empty);
        return;
    }}

    meta.checklist.forEach((item, index) => {{
        const row = document.createElement("div");
        row.className = item.done ? "checklist-item done" : "checklist-item";

        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.checked = Boolean(item.done);
        checkbox.addEventListener("change", () => {{
            item.done = checkbox.checked;
            saveTaskMeta(task);
            addActivity(task, `${{checkbox.checked ? "completed" : "reopened"}} checklist item: ${{item.text}}`);
            renderChecklist(task);
        }});

        const label = document.createElement("span");
        label.textContent = item.text;

        const remove = document.createElement("button");
        remove.type = "button";
        remove.className = "icon-button";
        remove.title = "Delete checklist item";
        remove.textContent = "x";
        remove.addEventListener("click", () => {{
            const removed = meta.checklist.splice(index, 1)[0];
            saveTaskMeta(task);
            addActivity(task, `deleted checklist item: ${{removed.text}}`);
            renderChecklist(task);
        }});

        row.appendChild(checkbox);
        row.appendChild(label);
        row.appendChild(remove);
        container.appendChild(row);
    }});
}}

function renderActivity(task) {{
    const meta = taskMeta(task);
    const container = document.getElementById("activity-list");
    container.innerHTML = "";
    const items = [
        ...meta.comments.map(comment => ({{ ...comment, message: `commented: ${{comment.message}}` }})),
        ...meta.activity,
    ];

    if (!items.length) {{
        const empty = document.createElement("div");
        empty.className = "modal-note";
        empty.textContent = "No comments or activity yet.";
        container.appendChild(empty);
        return;
    }}

    items.forEach(item => {{
        const row = document.createElement("div");
        row.className = "activity-item";
        const avatar = document.createElement("div");
        avatar.className = "activity-avatar";
        avatar.textContent = text(item.author || "U").slice(0, 1).toUpperCase();
        const body = document.createElement("div");
        const content = document.createElement("div");
        content.className = "activity-text";
        content.textContent = `${{item.author || "User"}} ${{item.message}}`;
        const time = document.createElement("div");
        time.className = "activity-time";
        time.textContent = item.time || "";
        body.appendChild(content);
        body.appendChild(time);
        row.appendChild(avatar);
        row.appendChild(body);
        container.appendChild(row);
    }});
}}

function renderDueDate(element, value, today = new Date()) {{
    const dateText = text(value);
    element.textContent = dateText;
    element.classList.remove("due-soon", "due-overdue");
    element.removeAttribute("title");
    element.removeAttribute("aria-label");
    if (!/^\\d{{4}}-\\d{{2}}-\\d{{2}}$/.test(dateText)) return;
    const due = new Date(`${{dateText}}T00:00:00Z`);
    if (!Number.isFinite(due.getTime()) || due.toISOString().slice(0, 10) !== dateText) return;
    // Compare calendar dates in the user's timezone, without DST-length days.
    const todayDate = Date.UTC(today.getFullYear(), today.getMonth(), today.getDate());
    const daysLeft = Math.round((due.getTime() - todayDate) / 86400000);
    let description;
    if (daysLeft < 0) {{
        element.classList.add("due-overdue");
        description = `Overdue by ${{-daysLeft}} ${{daysLeft === -1 ? "day" : "days"}}`;
    }} else {{
        if (daysLeft <= 5) element.classList.add("due-soon");
        description = daysLeft === 0 ? "Due today" : `Due in ${{daysLeft}} ${{daysLeft === 1 ? "day" : "days"}}`;
    }}
    element.title = description;
    element.setAttribute("aria-label", `${{dateText}}: ${{description}}`);
}}

function refreshDueDates() {{
    const today = new Date();
    data.tasks.forEach(task => {{
        const element = document.getElementById(task.id)?.querySelector(".due-current");
        if (element) renderDueDate(element, task.due, today);
    }});
}}

function updateCardFromTask(card, task) {{
    card.className = cardClass(task.status);
    card.dataset.status = task.status;
    card.querySelector(".task-title").textContent = text(task.title);
    card.querySelector(".project").textContent = text(task.project);
    card.querySelector(".task-project-line").hidden = !task.project;
    const dueHistory = card.querySelector(".due-history");
    if (dueHistory) {{
        dueHistory.innerHTML = "";
        taskMeta(task).due_history.forEach(oldDate => {{
            const oldDateNode = document.createElement("span");
            oldDateNode.textContent = text(oldDate);
            dueHistory.appendChild(oldDateNode);
        }});
    }}
    renderDueDate(card.querySelector(".due-current"), task.due);
    renderAssignees(card.querySelector(".task-assignees"), task);
    renderTaskLabels(card.querySelector(".task-labels"), task.labels);
    card.querySelector(".responsible-email").textContent = responsibleEmailsText(task) || "No responsible person selected";
    card.querySelector(".status").textContent = text(task.status);
    card.querySelector(".description").textContent = text(task.description);
    renderAttachmentLinks(card.querySelector(".attachments"), task);
}}

function createTaskCard(task) {{
    const card = document.createElement("div");
    card.draggable = true;
    card.id = task.id;
    card.dataset.status = task.status;

    card.innerHTML = `
        <div class="task-card-header">
            <div class="task-title"></div>
        </div>
        <div class="task-labels label-chips" aria-label="Task labels"></div>
        <details>
            <summary>Details</summary>
            <div class="task-details">
                <strong>Responsible:</strong> <span class="responsible-email"></span><br>
                <strong>Status:</strong> <span class="status"></span><br>
                <strong>Description:</strong> <span class="description"></span><br>
                <strong>Files and links:</strong> <div class="attachments attachment-list"></div>
            </div>
        </details>
        <div class="task-summary">
            <div class="task-project-line"><strong>Project:</strong> <span class="project"></span></div>
            <strong>Due:</strong> <span class="due-stack"><span class="due-history"></span><span class="due-current"></span></span>
        </div>
        <div class="task-assignees" role="group" aria-label="Responsible people"></div>
    `;
    updateCardFromTask(card, task);

    card.addEventListener("dragstart", event => {{
        draggedId = card.id;
        event.dataTransfer.effectAllowed = "move";
        event.dataTransfer.setData("text/plain", card.id);
    }});
    card.addEventListener("dblclick", () => openEditModal(card.id));

    return card;
}}

function createDropzone(status) {{
    const zone = document.createElement("div");
    zone.className = "dropzone";
    zone.dataset.status = status;

    zone.addEventListener("dragover", event => {{
        if (draggedColumn) return;
        event.preventDefault();
        zone.classList.add("drag-over");
    }});
    zone.addEventListener("dragleave", () => zone.classList.remove("drag-over"));
    zone.addEventListener("drop", event => {{
        if (draggedColumn) return;
        event.preventDefault();
        zone.classList.remove("drag-over");
        const cardId = event.dataTransfer.getData("text/plain") || draggedId;
        const card = document.getElementById(cardId);
        if (!card) return;

        const task = findTask(cardId);
        if (!task) return;
        persistTask(task, {{status}});
    }});

    enableColumnDrop(zone, status);
    return zone;
}}

function openNewTask(status) {{
    if (pendingSaveId) return;
    const today = new Date();
    const due = `${{today.getFullYear()}}-${{String(today.getMonth() + 1).padStart(2, "0")}}-${{String(today.getDate()).padStart(2, "0")}}`;
    openEditModal(null, {{id: null, title: "", status, due, description: "", responsible_emails: data.users.slice(0, 1), labels: [], attachments: [], attachment_links: []}});
}}

function openEditModal(taskId, draft = null) {{
    const task = draft || findTask(taskId);
    if (!task) return;
    newTaskDraft = draft;
    editingTaskId = taskId;
    document.getElementById("edit-modal-title").textContent = draft ? "Add task" : "Edit task";
    document.getElementById("edit-save").textContent = draft ? "Add task" : "Save changes";
    modal.classList.toggle("creating-task", Boolean(draft));
    editingLabelIds = [...(task.labels || [])];
    editingLabelCatalog = (data.labels || []).map(label => ({{...label}}));
    editingLabelChanges = {{}};
    document.getElementById("labels-search").value = "";
    setLabelsOpen(false);
    renderLabelOptions();
    document.getElementById("edit-save-error").textContent = "";

    document.getElementById("edit-title").value = text(task.title);
    renderResponsiblePicker(taskResponsibleEmails(task));
    fillSelect(document.getElementById("edit-status"), data.statuses, task.status);
    document.getElementById("edit-due").value = text(task.due);
    document.getElementById("edit-description").value = text(task.description);
    attachmentSession += 1;
    attachmentReadPending = false;
    editingAttachments = (task.attachment_links || []).map(item => ({{...item}}));
    editingUploads = [];
    document.getElementById("edit-save").disabled = Boolean(pendingSaveId);
    document.getElementById("attachment-upload").disabled = false;
    document.getElementById("attachment-link-input").value = "";
    document.getElementById("attachment-link-form").hidden = true;
    document.getElementById("attachment-error").textContent = "";
    renderEditingAttachments();
    document.getElementById("edit-uploaded-files").value = "";
    document.getElementById("checklist-new-item").value = "";
    document.getElementById("comment-input").value = "";
    if (!draft) {{
        renderChecklist(task);
        renderActivity(task);
    }}
    modal.classList.add("open");
    modal.setAttribute("aria-hidden", "false");
}}

function closeEditModal() {{
    attachmentSession += 1;
    editingTaskId = null;
    newTaskDraft = null;
    setLabelsOpen(false);
    modal.classList.remove("open");
    modal.setAttribute("aria-hidden", "true");
}}

function saveEditedTask() {{
    const task = newTaskDraft || findTask(editingTaskId);
    if (!task || pendingSaveId || attachmentReadPending) return;
    if (document.getElementById("attachment-link-input").value.trim() && !addAttachmentLink()) return;
    if (!selectedResponsibleEmails().length) {{
        document.getElementById("edit-save-error").textContent = "Select at least one responsible person.";
        return;
    }}

    const title = document.getElementById("edit-title").value.trim();
    if (!title) {{
        document.getElementById("edit-save-error").textContent = "Task title is required.";
        return;
    }}
    task.title = title;
    task.responsible_emails = selectedResponsibleEmails();
    task.responsible_email = task.responsible_emails.join(", ");
    task.status = document.getElementById("edit-status").value;
    const previousDue = text(task.due);
    const nextDue = document.getElementById("edit-due").value || task.due;
    if (!newTaskDraft && nextDue !== previousDue) {{
        const meta = taskMeta(task);
        meta.due_history.unshift(previousDue);
        meta.due_history = Array.from(new Set(meta.due_history.filter(Boolean))).slice(0, 5);
        task.due = nextDue;
        saveTaskMeta(task);
        addActivity(task, `changed due date from ${{previousDue}} to ${{nextDue}}`);
    }} else {{
        task.due = nextDue;
    }}
    task.description = document.getElementById("edit-description").value.trim() || "No additional details provided.";
    if (!newTaskDraft) addActivity(task, "updated this task");

    const card = document.getElementById(task.id);
    if (card) {{
        const targetZone = document.querySelector(`.dropzone[data-status="${{CSS.escape(task.status)}}"]`);
        updateCardFromTask(card, task);
        if (targetZone) targetZone.insertBefore(card, targetZone.querySelector(".column-add-task"));
    }}
    updateColumnCounts();
    const fields = ["title", "responsible_emails", "status", "due", "description", "attachments", "labels"];
    persistTask(task, Object.fromEntries(fields.map(field => [field, field === "labels" ? [...editingLabelIds] : field === "attachments" ? editingAttachments.map(item => item.reference) : task[field]])), Object.values(editingLabelChanges), editingUploads.map(file => ({{name: file.name, data: file.data}})));
}}

document.getElementById("responsible-control").addEventListener("click", () => {{
    const isOpen = document.getElementById("responsible-menu").classList.contains("open");
    setResponsibleMenuOpen(!isOpen);
}});
document.getElementById("responsible-control").addEventListener("keydown", event => {{
    if (event.key === "Enter" || event.key === " ") {{
        event.preventDefault();
        const isOpen = document.getElementById("responsible-menu").classList.contains("open");
        setResponsibleMenuOpen(!isOpen);
    }}
}});
document.getElementById("responsible-clear").addEventListener("click", event => {{
    event.stopPropagation();
    editingResponsibleEmails = [];
    syncResponsiblePicker();
}});
document.addEventListener("click", event => {{
    if (!document.getElementById("edit-responsible-people").contains(event.target)) {{
        setResponsibleMenuOpen(false);
    }}
}});

document.getElementById("checklist-add").addEventListener("click", () => {{
    const task = findTask(editingTaskId);
    const input = document.getElementById("checklist-new-item");
    const value = input.value.trim();
    if (!task || !value) return;
    taskMeta(task).checklist.push({{ text: value, done: false }});
    input.value = "";
    saveTaskMeta(task);
    addActivity(task, `added checklist item: ${{value}}`);
    renderChecklist(task);
}});
document.getElementById("checklist-new-item").addEventListener("keydown", event => {{
    if (event.key === "Enter") {{
        event.preventDefault();
        document.getElementById("checklist-add").click();
    }}
}});
document.getElementById("comment-add").addEventListener("click", () => {{
    const task = findTask(editingTaskId);
    const input = document.getElementById("comment-input");
    const value = input.value.trim();
    if (!task || !value) return;
    taskMeta(task).comments.unshift({{ author: currentUserLabel(), message: value, time: nowLabel() }});
    input.value = "";
    saveTaskMeta(task);
    renderActivity(task);
}});
document.getElementById("edit-cancel").addEventListener("click", closeEditModal);
document.getElementById("edit-save").addEventListener("click", saveEditedTask);
modal.addEventListener("click", event => {{
    if (event.target === modal) closeEditModal();
}});
document.addEventListener("keydown", event => {{
    if (event.key === "Escape") closeEditModal();
}});

function renderBoard() {{
    board.replaceChildren();
    board.style.setProperty("--column-count", data.statuses.length + 1);
    data.statuses.forEach(status => createColumnHeader(status));
    createAddColumnHeader();
    data.statuses.forEach(status => {{
        const zone = createDropzone(status);
        data.tasks
            .filter(task => task.status === status)
            .forEach(task => zone.appendChild(createTaskCard(task)));
        zone.appendChild(createAddTaskButton(status));
        board.appendChild(zone);
    }});
    const spacer = document.createElement("div");
    spacer.className = "add-column-space";
    board.appendChild(spacer);
}}

renderBoard();
// Refresh an open board when the date changes or the user returns to the tab.
setInterval(refreshDueDates, 60000);
document.addEventListener("visibilitychange", () => {{
    if (!document.hidden) refreshDueDates();
}});
</script>
</body>
</html>
"""


def board_height() -> int:
    # Fixed height keeps the embedded board predictable while its own container scrolls.
    return 760


initialize_state()
if not TASK_DATABASE_CSV.exists():
    save_tasks_to_csv()

render_app_header()
if st.session_state.pop("show_task_created_notice", False):
    st.success(f"Added task: {st.session_state.last_added_task['title']}")
    notification = st.session_state.get("last_notification_result", {})
    if notification.get("status") == "sent":
        st.success(notification["message"])
    elif notification:
        st.warning(notification["message"])

statuses = st.session_state.statuses
project_ids = st.session_state.project_ids
if "project_colors" not in st.session_state:
    st.session_state.project_colors = {
        project_id: default_project_color(project_id)
        for project_id in project_ids
    }
for project_id in project_ids:
    st.session_state.project_colors.setdefault(project_id, default_project_color(project_id))
users = st.session_state.users

toolbar_actions, toolbar_filters = st.columns([6, 1])
with toolbar_filters:
    with st.popover("Filter", icon=":material/filter_list:", width="stretch"):
        st.markdown("**Filter**")
        filter_keyword = st.text_input("Keyword", placeholder="Enter a keyword…", key="filter_keyword")
        filter_members = st.multiselect("Members", ["No members", *users], key="filter_members", placeholder="Any member")
        selected_statuses = st.multiselect("Card status", statuses, default=statuses, key="status_filter")
        filter_due = st.selectbox("Due date", [
            "Any date", "No date", "Overdue", "Due today", "Due in the next day",
            "Due in the next week", "Due in the next month",
        ], key="filter_due")
        label_names = {label["id"]: label["name"] for label in load_board_labels()}
        selected_labels = st.multiselect(
            "Labels", ["__no_labels__", *label_names], key="filter_labels",
            format_func=lambda label_id: "No labels" if label_id == "__no_labels__" else label_names[label_id],
            placeholder="Any label",
        )
        st.button("Clear filters", on_click=reset_board_filters, width="stretch")

filtered_tasks = [
    task | {"storage_key": task["id"]}
    for task in st.session_state.tasks
    if task["status"] in selected_statuses
    and task_matches_filters(task, filter_keyword, filter_members, filter_due, labels=selected_labels)
]

todo_tasks = [
    task
    for task in filtered_tasks
    if task["status"] == "Backlog / To Do"
]


visible_statuses = [status for status in statuses if status in selected_statuses]
board_html = build_board_html(visible_statuses, filtered_tasks)
kanban_component = components.declare_component(
    "kanban_board", path=str(Path(__file__).parent / "assets" / "kanban_component"),
)
kanban_component(
    html=board_html, height=board_height(),
    save_result=st.session_state.get("board_save_result"),
    key="kanban_board", default=None, on_change=on_board_change,
)

project_count = len({task["project_id"] for task in filtered_tasks if task.get("project_id")})
st.markdown(
    f"""
    <div class="dashboard-strip">
        <div class="dashboard-tile">
            <div class="dashboard-label">All tasks</div>
            <div class="dashboard-value">{len(filtered_tasks)}</div>
        </div>
        <div class="dashboard-tile">
            <div class="dashboard-label">Projects</div>
            <div class="dashboard-value">{project_count}</div>
        </div>
        <div class="dashboard-tile">
            <div class="dashboard-label">To Do</div>
            <div class="dashboard-value">{len(todo_tasks)}</div>
        </div>
        <div class="dashboard-tile">
            <div class="dashboard-label">Visible columns</div>
            <div class="dashboard-value">{len(selected_statuses)}</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)
