from __future__ import annotations

import base64
import json
import mimetypes
from pathlib import Path
from html import escape
from urllib.parse import quote

import streamlit as st
import streamlit.components.v1 as components


DEFAULT_STATUSES = ["Backlog / To Do", "In Progress", "Completed", "Rejected"]
DEFAULT_PEOPLE = [
    "Project Manager",
    "Manufacturing Engineer",
    "Quality Engineer",
    "Purchasing",
    "Logistics",
    "Technical Director",
]
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
ATTACHMENTS_DIR = Path(__file__).parent / "attachments"

# Demo seed data used when the Streamlit session starts for the first time.
# The app currently keeps data in memory, so these values reset for a new session.
DEFAULT_TASKS = [
    {
        "title": "Create project record",
        "owner": "Project Manager",
        "status": "Completed",
        "due": "2026-08-02",
        "stage": "Project Setup",
        "project_id": "PRJ-001",
        "project": "NPI - Stamping Bracket",
        "description": "Create the initial project record and confirm the project manager.",
    },
    {
        "title": "Upload Purchase Order",
        "owner": "Project Manager",
        "status": "Backlog / To Do",
        "due": "2026-08-04",
        "stage": "Project Setup",
        "project_id": "PRJ-001",
        "project": "NPI - Stamping Bracket",
        "description": "Attach the customer purchase order and verify the commercial reference.",
    },
    {
        "title": "Manufacturing feasibility checklist",
        "owner": "Manufacturing Engineer",
        "status": "In Progress",
        "due": "2026-08-08",
        "stage": "Feasibility Review",
        "project_id": "PRJ-001",
        "project": "NPI - Stamping Bracket",
        "description": "Review process feasibility, press capacity, tooling assumptions, and cycle time risk.",
    },
    {
        "title": "Review drawing revision",
        "owner": "Quality Engineer",
        "status": "Backlog / To Do",
        "due": "2026-08-05",
        "stage": "Feasibility Review",
        "project_id": "PRJ-001",
        "project": "NPI - Stamping Bracket",
        "description": "Check the latest customer drawing revision and confirm special characteristics.",
    },
    {
        "title": "Create quality feasibility checklist",
        "owner": "Quality Engineer",
        "status": "Backlog / To Do",
        "due": "2026-08-06",
        "stage": "Feasibility Review",
        "project_id": "PRJ-001",
        "project": "NPI - Stamping Bracket",
        "description": "Prepare the quality checklist for feasibility gate review.",
    },
    {
        "title": "Prepare Control Plan draft",
        "owner": "Quality Engineer",
        "status": "Backlog / To Do",
        "due": "2026-08-09",
        "stage": "Documentation Preparation",
        "project_id": "PRJ-001",
        "project": "NPI - Stamping Bracket",
        "description": "Create the initial Control Plan with process steps and inspection points.",
    },
    {
        "title": "Prepare CMM measurement program",
        "owner": "Quality Engineer",
        "status": "Backlog / To Do",
        "due": "2026-08-11",
        "stage": "Documentation Preparation",
        "project_id": "PRJ-001",
        "project": "NPI - Stamping Bracket",
        "description": "Prepare the first CMM measurement program for dimensional validation.",
    },
    {
        "title": "Confirm PPAP documentation list",
        "owner": "Quality Engineer",
        "status": "Backlog / To Do",
        "due": "2026-08-13",
        "stage": "Documentation Preparation",
        "project_id": "PRJ-002",
        "project": "Engineering Change - Seat Rail Clip",
        "description": "Confirm required PPAP documents and evidence for customer submission.",
    },
    {
        "title": "Packaging concept review",
        "owner": "Logistics",
        "status": "Backlog / To Do",
        "due": "2026-08-12",
        "stage": "Documentation Preparation",
        "project_id": "PRJ-002",
        "project": "Engineering Change - Seat Rail Clip",
        "description": "Review packaging concept, handling method, and available container options.",
    },
    {
        "title": "Supplier cost confirmation",
        "owner": "Purchasing",
        "status": "In Progress",
        "due": "2026-08-11",
        "stage": "Purchasing and Logistics",
        "project_id": "PRJ-002",
        "project": "Engineering Change - Seat Rail Clip",
        "description": "Confirm supplier cost impact and timing for purchased components.",
    },
    {
        "title": "Approve technical feasibility",
        "owner": "Technical Director",
        "status": "Backlog / To Do",
        "due": "2026-08-10",
        "stage": "Feasibility Review",
        "project_id": "PRJ-003",
        "project": "Tool Transfer - Door Reinforcement",
        "description": "Approve the technical feasibility gate before downstream work starts.",
    },
    {
        "title": "Old container concept",
        "owner": "Logistics",
        "status": "Rejected",
        "due": "2026-08-06",
        "stage": "Purchasing and Logistics",
        "project_id": "PRJ-003",
        "project": "Tool Transfer - Door Reinforcement",
        "description": "Rejected because the container footprint does not match the new logistics flow.",
    },
]


st.set_page_config(
    page_title="Project Planner",
    page_icon="EWM",
    layout="wide",
)

st.markdown(
    """
    <style>
        .block-container {
            padding-top: 1.6rem;
            padding-bottom: 2rem;
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
        st.session_state.statuses = DEFAULT_STATUSES.copy()
    if "people" not in st.session_state:
        st.session_state.people = DEFAULT_PEOPLE.copy()
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
        st.session_state.tasks = [task.copy() for task in DEFAULT_TASKS]

    for task in st.session_state.tasks:
        # Older/default tasks may not include fields added by newer UI features.
        task.setdefault("responsible_email", st.session_state.users[0])
        task.setdefault("attachments", [])
        task.setdefault("email_notification", False)


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


def attachment_link_items(attachments: list[str]) -> list[dict[str, str]]:
    items = []
    app_folder = Path(__file__).parent.resolve()

    for attachment in attachments:
        name = Path(attachment).name or attachment
        href = ""

        if attachment.startswith(("http://", "https://", "mailto:")):
            href = attachment
        else:
            attachment_path = Path(attachment)
            if not attachment_path.is_absolute():
                attachment_path = app_folder / attachment_path
            attachment_path = attachment_path.resolve()

            try:
                attachment_path.relative_to(app_folder)
            except ValueError:
                attachment_path = None

            if attachment_path and not attachment_path.is_file() and ATTACHMENTS_DIR.exists():
                safe_name = safe_storage_name(name)
                attachment_path = next(
                    (
                        saved_path
                        for saved_path in ATTACHMENTS_DIR.rglob("*")
                        if saved_path.is_file() and saved_path.name in {name, safe_name}
                    ),
                    None,
                )

            if attachment_path and attachment_path.is_file():
                mime_type = mimetypes.guess_type(attachment_path.name)[0] or "application/octet-stream"
                encoded_file = base64.b64encode(attachment_path.read_bytes()).decode("ascii")
                href = f"data:{mime_type};base64,{encoded_file}"

        items.append({"name": name, "href": href})

    return items

def rename_values(
    state_key: str,
    task_field: str,
    new_names: list[str],
    item_label: str,
) -> tuple[bool, str]:
    # Rename list entries and update existing tasks that reference the old names.
    # This keeps the board from losing tasks when a column, project ID, or owner row is renamed.
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

    return True, f"{item_label} names updated."


def add_value(state_key: str, value: str, item_label: str) -> tuple[bool, str]:
    cleaned_value = normalize_name(value)

    if not cleaned_value:
        return False, f"Enter a {item_label.lower()} first."

    if cleaned_value in st.session_state[state_key]:
        return False, f"This {item_label.lower()} already exists."

    st.session_state[state_key].append(cleaned_value)
    return True, f"Added {item_label.lower()}: {cleaned_value}."


def add_attachments_to_task(
    task_index: int,
    uploaded_files: list[object],
    typed_attachment_names: str,
) -> tuple[bool, str]:
    if task_index < 0 or task_index >= len(st.session_state.tasks):
        return False, "Select an existing task."

    uploaded_files = uploaded_files or []
    task = st.session_state.tasks[task_index]
    typed_names = [name.strip() for name in typed_attachment_names.splitlines() if name.strip()]

    if not uploaded_files and not typed_names:
        return False, "Choose at least one file or enter one file link."

    task_folder = ATTACHMENTS_DIR / safe_storage_name(
        f"{task_index + 1}_{task['project_id']}_{task['title']}"
    )
    task_folder.mkdir(parents=True, exist_ok=True)

    saved_file_names = []
    for uploaded_file in uploaded_files:
        target_path = unique_file_path(task_folder, uploaded_file.name)
        target_path.write_bytes(uploaded_file.getbuffer())
        saved_file_names.append(str(target_path.relative_to(Path(__file__).parent)))

    candidate_names = saved_file_names + typed_names
    existing_names = task.setdefault("attachments", [])
    added_names = []

    for name in candidate_names:
        if name not in existing_names:
            existing_names.append(name)
            added_names.append(name)

    if not added_names:
        return False, "These files are already attached to the selected task."

    return True, f"Added {len(added_names)} file(s) to: {task['title']}."


def task_option_label(task: dict[str, object]) -> str:
    return f"{task['project_id']} | {task['title']} ({task['owner']})"

def add_task(
    title: str,
    project_id: str,
    project: str,
    owner: str,
    responsible_email: str,
    status: str,
    due: str,
    stage: str,
    description: str,
    attachments: list[str],
    send_email: bool,
) -> tuple[bool, str]:
    # Normalize user input at the boundary so downstream rendering can assume
    # required fields are present and human-readable.
    cleaned_title = normalize_name(title)
    cleaned_project = normalize_name(project)
    cleaned_stage = normalize_name(stage)
    cleaned_description = description.strip()

    if not cleaned_title:
        return False, "Task title is required."

    if not cleaned_project:
        return False, "Project name is required."

    task = {
        "title": cleaned_title,
        "owner": owner,
        "responsible_email": responsible_email,
        "status": status,
        "due": due,
        "stage": cleaned_stage or "Not assigned",
        "project_id": project_id,
        "project": cleaned_project,
        "description": cleaned_description or "No additional details provided.",
        "attachments": attachments,
        "email_notification": send_email,
    }
    st.session_state.tasks.append(task)
    st.session_state.last_added_task = task.copy()
    return True, f"Added task: {cleaned_title}."


@st.dialog("Add task")
def add_task_dialog(project_ids: list[str], people: list[str], statuses: list[str], users: list[str]) -> None:
    with st.form("add_task_dialog_form"):
        task_title = st.text_input("Task title", placeholder="Prepare inspection report")
        task_project_id = st.selectbox("Project ID", project_ids)
        task_project = st.text_input("Project name", placeholder="NPI - Stamping Bracket")
        task_owner = st.selectbox("Responsible row", people)
        responsible_email = st.selectbox("Responsible", users)
        task_status = st.selectbox("Column/status", statuses)
        task_due = st.date_input("Due date")
        task_stage = st.text_input("Workflow stage", placeholder="Documentation Preparation")
        task_description = st.text_area("Details", placeholder="Additional task information")
        uploaded_files = st.file_uploader("Attach files", accept_multiple_files=True)
        send_email = st.checkbox("Send email to responsible person")
        submitted = st.form_submit_button("Add task")

    if submitted:
        success, message = add_task(
            task_title,
            task_project_id,
            task_project,
            task_owner,
            responsible_email,
            task_status,
            task_due.isoformat(),
            task_stage,
            task_description,
            [file.name for file in uploaded_files],
            send_email,
        )
        if success:
            st.session_state.show_added_task_dialog = True
            st.rerun()
        st.error(message)


@st.dialog("Attach files to task")
def attach_files_dialog() -> None:
    selected_task_index = st.selectbox(
        "Existing task",
        range(len(st.session_state.tasks)),
        format_func=lambda index: task_option_label(st.session_state.tasks[index]),
    )
    current_attachments = st.session_state.tasks[selected_task_index].get("attachments", [])
    current_attachment_text = ", ".join(current_attachments) or "No files attached"
    st.caption(f"Current files: {current_attachment_text}")
    uploaded_files = st.file_uploader(
        "Add files",
        accept_multiple_files=True,
        key="dialog_existing_task_files",
    )
    typed_attachment_names = st.text_area(
        "File paths or links",
        placeholder="Paste one file path or SharePoint link per line",
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

@st.dialog("Task added")
def task_added_dialog() -> None:
    task = st.session_state.get("last_added_task")
    if not task:
        st.write("Task was added.")
    else:
        st.write("The task was added to the board.")
        st.markdown(f"**Task title:** {escape(task['title'])}")
        st.markdown(f"**Project ID:** {escape(task['project_id'])}")
        st.markdown(f"**Project name:** {escape(task['project'])}")
        st.markdown(f"**Responsible row:** {escape(task['owner'])}")
        st.markdown(f"**Responsible:** {escape(task['responsible_email'])}")
        st.markdown(f"**Column/status:** {escape(task['status'])}")
        st.markdown(f"**Due date:** {escape(task['due'])}")
        st.markdown(f"**Workflow stage:** {escape(task['stage'])}")
        attachment_names = ", ".join(task.get("attachments", [])) or "No files attached"
        st.markdown(f"**Details:** {escape(task['description'])}")
        st.markdown(f"**Attachments:** {escape(attachment_names)}")
        if task.get("email_notification"):
            subject = quote(f"New task assigned: {task['title']}")
            body = quote(
                f"Task: {task['title']}\n"
                f"Project ID: {task['project_id']}\n"
                f"Project: {task['project']}\n"
                f"Due date: {task['due']}\n"
                f"Workflow stage: {task['stage']}\n\n"
                f"Details: {task['description']}"
            )
            st.markdown(f"[Open email draft](mailto:{task['responsible_email']}?subject={subject}&body={body})")

    if st.button("Close", key="close_added_task_dialog"):
        st.session_state.show_added_task_dialog = False
        st.rerun()


def remove_people(people_to_remove: list[str]) -> tuple[bool, str]:
    if not people_to_remove:
        return False, "Select at least one row to remove."

    remaining_people = [person for person in st.session_state.people if person not in people_to_remove]
    if not remaining_people:
        return False, "At least one responsible row must remain."

    st.session_state.people = remaining_people
    return True, "Responsible rows removed. Tasks assigned to removed rows are hidden until the row is added again."


def build_board_html(statuses: list[str], people: list[str], tasks: list[dict[str, str]]) -> str:
    # Streamlit does not provide a native Planner-style drag-and-drop board, so
    # this function embeds a small self-contained HTML/CSS/JS app.
    board_tasks = [
        task | {"attachment_links": attachment_link_items(task.get("attachments", []))}
        for task in tasks
    ]
    board_data = {
        "statuses": statuses,
        "people": people,
        "users": st.session_state.users,
        "project_colors": project_color_payload(),
        "tasks": board_tasks,
    }
    payload = json.dumps(board_data)

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
        grid-template-columns: 190px repeat(var(--column-count), minmax(215px, 1fr));
        gap: 10px;
        min-width: calc(190px + var(--column-count) * 215px);
    }}
    .header, .person {{
        position: sticky;
        left: 0;
        z-index: 4;
        background: #ffffff;
    }}
    .header, .column-header {{
        position: sticky;
        top: 0;
        z-index: 5;
    }}
    .header {{
        align-items: center;
        background: #f8fafc;
        border: 1px solid #dbe3ef;
        border-radius: 8px;
        color: #334155;
        display: flex;
        font-size: 11px;
        font-weight: 900;
        letter-spacing: 0;
        min-height: 42px;
        padding: 10px;
        text-transform: uppercase;
    }}
    .column-header {{
        align-items: center;
        background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
        border: 1px solid #dbe3ef;
        border-radius: 8px;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
        color: #0f172a;
        display: grid;
        gap: 6px;
        grid-template-columns: 1fr auto;
        min-height: 42px;
        overflow: hidden;
        padding: 9px 10px 8px;
    }}
    .column-header::before {{
        background: var(--status-accent, #64748b);
        content: "";
        height: 3px;
        inset: 0 0 auto;
        position: absolute;
    }}
    .column-title {{
        font-size: 12px;
        font-weight: 900;
        line-height: 1.15;
        overflow-wrap: anywhere;
        text-transform: uppercase;
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
    .person {{
        align-items: start;
        border-bottom: 1px solid #dbe3ef;
        color: #111827;
        display: flex;
        font-size: 14px;
        font-weight: 800;
        min-height: 36px;
        padding: 10px 8px 7px;
        text-transform: none;
    }}
    .dropzone {{
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
    .task-project-id-badge {{
        background: var(--project-bg, #eff6ff);
        border: 1px solid var(--project-border, #bfdbfe);
        border-radius: 999px;
        color: var(--project-text, #1d4ed8);
        flex: 0 0 auto;
        font-size: 11px;
        font-weight: 900;
        line-height: 1;
        max-width: 84px;
        overflow: hidden;
        padding: 5px 7px;
        text-overflow: ellipsis;
        white-space: nowrap;
    }}
    .task-summary {{
        color: #475569;
        font-size: 12px;
        line-height: 1.45;
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
    .form-grid label {{
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
<p class="hint">Hold a task card and drop it into another column or another responsible row. Double-click a task to edit it in a small window.</p>
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
                    <label>Project ID<input id="edit-project-id" type="text"></label>
                    <label>Project name<input id="edit-project" type="text"></label>
                    <label>Responsible row<select id="edit-owner"></select></label>
                    <label>Responsible<select id="edit-responsible-email"></select></label>
                    <label>Column/status<select id="edit-status"></select></label>
                    <label>Due date<input id="edit-due" type="date"></label>
                    <label>Workflow stage<input id="edit-stage" type="text"></label>
                    <label>Details<textarea id="edit-description"></textarea></label>
                    <label>Attached files<textarea id="edit-attachments" placeholder="One file name or link per line"></textarea></label>
                    <div id="edit-attachment-links" class="attachment-list"></div>
                    <div class="modal-note">Saved files and links can be opened from this list.</div>
                    <label>Upload files<input id="edit-uploaded-files" type="file" multiple></label>
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

const projectColors = [
    {{ bg: "#eff6ff", border: "#bfdbfe", text: "#1d4ed8" }},
    {{ bg: "#f0fdf4", border: "#bbf7d0", text: "#15803d" }},
    {{ bg: "#fff7ed", border: "#fed7aa", text: "#c2410c" }},
    {{ bg: "#f5f3ff", border: "#ddd6fe", text: "#6d28d9" }},
    {{ bg: "#ecfeff", border: "#a5f3fc", text: "#0e7490" }},
    {{ bg: "#fdf2f8", border: "#fbcfe8", text: "#be185d" }},
    {{ bg: "#fefce8", border: "#fde68a", text: "#a16207" }},
    {{ bg: "#f1f5f9", border: "#cbd5e1", text: "#334155" }},
];

function projectColor(projectId) {{
    const value = text(projectId);
    if (data.project_colors && data.project_colors[value]) return data.project_colors[value];

    let hash = 0;
    for (let index = 0; index < value.length; index += 1) {{
        hash = (hash + value.charCodeAt(index) * (index + 1)) % projectColors.length;
    }}
    return projectColors[hash];
}}

function applyProjectBadgeColor(badge, projectId) {{
    const color = projectColor(projectId);
    badge.style.setProperty("--project-bg", color.bg);
    badge.style.setProperty("--project-border", color.border);
    badge.style.setProperty("--project-text", color.text);
}}

function findTask(taskId) {{
    return data.tasks.find(task => task.id === taskId);
}}

function fillSelect(select, options, selectedValue) {{
    select.innerHTML = "";
    options.forEach(optionValue => {{
        const option = document.createElement("option");
        option.value = optionValue;
        option.textContent = optionValue;
        option.selected = optionValue === selectedValue;
        select.appendChild(option);
    }});
}}

function addCell(tag, className, content) {{
    const cell = document.createElement(tag);
    cell.className = className;
    cell.textContent = content;
    board.appendChild(cell);
    return cell;
}}

function statusAccent(status) {{
    const lowered = status.toLowerCase();
    if (lowered.includes("completed") || lowered.includes("done")) return "#16a34a";
    if (lowered.includes("rejected") || lowered.includes("cancel")) return "#dc2626";
    if (lowered.includes("progress") || lowered.includes("active")) return "#f59e0b";
    if (lowered.includes("backlog") || lowered.includes("todo") || lowered.includes("to do")) return "#2563eb";
    return "#64748b";
}}

function createColumnHeader(status) {{
    const header = document.createElement("div");
    const taskCount = data.tasks.filter(task => task.status === status).length;
    header.className = "column-header";
    header.style.setProperty("--status-accent", statusAccent(status));

    const title = document.createElement("span");
    title.className = "column-title";
    title.textContent = status;

    const count = document.createElement("span");
    count.className = "column-count";
    count.textContent = taskCount;

    header.appendChild(title);
    header.appendChild(count);
    board.appendChild(header);
    return header;
}}

function renderAttachmentLinks(container, task) {{
    container.innerHTML = "";
    const links = task.attachment_links || [];
    if (!links.length) {{
        const empty = document.createElement("span");
        empty.textContent = "No files attached";
        container.appendChild(empty);
        return;
    }}

    links.forEach(item => {{
        if (item.href) {{
            const link = document.createElement("a");
            link.href = item.href;
            link.textContent = item.name;
            link.target = "_blank";
            link.rel = "noopener";
            if (item.href.startsWith("data:")) link.download = item.name;
            container.appendChild(link);
        }} else {{
            const name = document.createElement("span");
            name.textContent = item.name;
            container.appendChild(name);
        }}
    }});
}}

function updateTaskAttachmentLinks(task) {{
    task.attachment_links = (task.attachments || []).map(name => ({{ name, href: "" }}));
}}

function taskStoreKey(task) {{
    return `ewm-task-meta:${{task.storage_key || task.id}}`;
}}

function taskMeta(task) {{
    if (task._meta) return task._meta;
    const fallback = {{ checklist: [], comments: [], activity: [] }};
    try {{
        task._meta = {{ ...fallback, ...JSON.parse(localStorage.getItem(taskStoreKey(task)) || "{{}}") }};
    }} catch (error) {{
        task._meta = fallback;
    }}
    task._meta.checklist = Array.isArray(task._meta.checklist) ? task._meta.checklist : [];
    task._meta.comments = Array.isArray(task._meta.comments) ? task._meta.comments : [];
    task._meta.activity = Array.isArray(task._meta.activity) ? task._meta.activity : [];
    return task._meta;
}}

function saveTaskMeta(task) {{
    localStorage.setItem(taskStoreKey(task), JSON.stringify(taskMeta(task)));
}}

function nowLabel() {{
    return new Date().toLocaleString([], {{ year: "numeric", month: "short", day: "2-digit", hour: "2-digit", minute: "2-digit" }});
}}

function currentUserLabel() {{
    const user = text(document.getElementById("edit-responsible-email").value || data.users[0] || "User");
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

function updateCardFromTask(card, task) {{
    card.className = cardClass(task.status);
    card.dataset.owner = task.owner;
    card.dataset.status = task.status;
    card.querySelector(".task-title").textContent = text(task.title);
    card.querySelector(".project").textContent = text(task.project);
    card.querySelector(".due").textContent = text(task.due);
    const projectBadge = card.querySelector(".task-project-id-badge");
    if (projectBadge) {{
        projectBadge.textContent = text(task.project_id);
        applyProjectBadgeColor(projectBadge, task.project_id);
    }}
    card.querySelector(".project-id-detail").textContent = text(task.project_id);
    card.querySelector(".owner").textContent = text(task.owner);
    card.querySelector(".responsible-email").textContent = text(task.responsible_email);
    card.querySelector(".status").textContent = text(task.status);
    card.querySelector(".stage").textContent = text(task.stage);
    card.querySelector(".description").textContent = text(task.description);
    card.querySelector(".attachments").textContent = task.attachments && task.attachments.length ? task.attachments.join(", ") : "No files attached";
}}

function createTaskCard(task) {{
    const card = document.createElement("div");
    card.draggable = true;
    card.id = task.id;
    card.dataset.owner = task.owner;
    card.dataset.status = task.status;

    card.innerHTML = `
        <div class="task-card-header">
            <div class="task-title"></div>
            <span class="task-project-id-badge"></span>
        </div>
        <div class="task-summary">
            <strong>Project:</strong> <span class="project"></span><br>
            <strong>Due:</strong> <span class="due"></span>
        </div>
        <details>
            <summary>Details</summary>
            <div class="task-details">
                <strong>Project ID:</strong> <span class="project-id-detail"></span><br>
                <strong>Owner:</strong> <span class="owner"></span><br>
                <strong>Responsible:</strong> <span class="responsible-email"></span><br>
                <strong>Status:</strong> <span class="status"></span><br>
                <strong>Stage:</strong> <span class="stage"></span><br>
                <strong>Description:</strong> <span class="description"></span><br>
                <strong>Attachments:</strong> <span class="attachments attachment-list"></span>
            </div>
        </details>
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

function createDropzone(person, status) {{
    const zone = document.createElement("div");
    zone.className = "dropzone";
    zone.dataset.owner = person;
    zone.dataset.status = status;

    zone.addEventListener("dragover", event => {{
        event.preventDefault();
        zone.classList.add("drag-over");
    }});
    zone.addEventListener("dragleave", () => zone.classList.remove("drag-over"));
    zone.addEventListener("drop", event => {{
        event.preventDefault();
        zone.classList.remove("drag-over");
        const cardId = event.dataTransfer.getData("text/plain") || draggedId;
        const card = document.getElementById(cardId);
        if (!card) return;

        const task = findTask(cardId);
        if (task) {{
            task.owner = person;
            task.status = status;
            updateCardFromTask(card, task);
        }} else {{
            card.dataset.owner = person;
            card.dataset.status = status;
            card.className = cardClass(status);
            card.querySelector(".owner").textContent = person;
            card.querySelector(".status").textContent = status;
        }}
        zone.appendChild(card);
    }});

    return zone;
}}

function openEditModal(taskId) {{
    const task = findTask(taskId);
    if (!task) return;
    editingTaskId = taskId;

    document.getElementById("edit-title").value = text(task.title);
    document.getElementById("edit-project-id").value = text(task.project_id);
    document.getElementById("edit-project").value = text(task.project);
    fillSelect(document.getElementById("edit-owner"), data.people, task.owner);
    fillSelect(document.getElementById("edit-responsible-email"), data.users, task.responsible_email);
    fillSelect(document.getElementById("edit-status"), data.statuses, task.status);
    document.getElementById("edit-due").value = text(task.due);
    document.getElementById("edit-stage").value = text(task.stage);
    document.getElementById("edit-description").value = text(task.description);
    document.getElementById("edit-attachments").value = task.attachments && task.attachments.length ? task.attachments.join("\\n") : "";
    renderAttachmentLinks(document.getElementById("edit-attachment-links"), task);
    document.getElementById("edit-uploaded-files").value = "";
    document.getElementById("checklist-new-item").value = "";
    document.getElementById("comment-input").value = "";
    renderChecklist(task);
    renderActivity(task);
    modal.classList.add("open");
    modal.setAttribute("aria-hidden", "false");
}}

function closeEditModal() {{
    editingTaskId = null;
    modal.classList.remove("open");
    modal.setAttribute("aria-hidden", "true");
}}

function saveEditedTask() {{
    const task = findTask(editingTaskId);
    if (!task) return;

    task.title = document.getElementById("edit-title").value.trim() || task.title;
    task.project_id = document.getElementById("edit-project-id").value.trim() || task.project_id;
    task.project = document.getElementById("edit-project").value.trim() || task.project;
    task.owner = document.getElementById("edit-owner").value;
    task.responsible_email = document.getElementById("edit-responsible-email").value;
    task.status = document.getElementById("edit-status").value;
    task.due = document.getElementById("edit-due").value || task.due;
    task.stage = document.getElementById("edit-stage").value.trim() || "Not assigned";
    task.description = document.getElementById("edit-description").value.trim() || "No additional details provided.";
    const typedAttachments = document.getElementById("edit-attachments").value
        .split("\\n")
        .map(value => value.trim())
        .filter(Boolean);
    const uploadedAttachmentNames = Array.from(document.getElementById("edit-uploaded-files").files)
        .map(file => file.name);
    task.attachments = Array.from(new Set([...typedAttachments, ...uploadedAttachmentNames]));
    updateTaskAttachmentLinks(task);
    renderAttachmentLinks(document.getElementById("edit-attachment-links"), task);
    addActivity(task, "updated this task");

    const card = document.getElementById(task.id);
    if (card) {{
        const targetZone = document.querySelector(`.dropzone[data-owner="${{CSS.escape(task.owner)}}"][data-status="${{CSS.escape(task.status)}}"]`);
        updateCardFromTask(card, task);
        if (targetZone) targetZone.appendChild(card);
    }}
    closeEditModal();
}}

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
    board.style.setProperty("--column-count", data.statuses.length);
    addCell("div", "header", "Responsible");
    data.statuses.forEach(status => createColumnHeader(status));

    data.people.forEach(person => {{
        addCell("div", "person", person);
        data.statuses.forEach(status => {{
            const zone = createDropzone(person, status);
            data.tasks
                .filter(task => task.owner === person && task.status === status)
                .forEach(task => zone.appendChild(createTaskCard(task)));
            board.appendChild(zone);
        }});
    }});
}}

renderBoard();
</script>
</body>
</html>
"""


def board_height(people_count: int) -> int:
    # Fixed height keeps the embedded board predictable while its own container scrolls.
    return 760


initialize_state()

st.title("Project Planner")
st.caption("Dashboard board view grouped by responsible people")

statuses = st.session_state.statuses
people = st.session_state.people
project_ids = st.session_state.project_ids
if "project_colors" not in st.session_state:
    st.session_state.project_colors = {
        project_id: default_project_color(project_id)
        for project_id in project_ids
    }
for project_id in project_ids:
    st.session_state.project_colors.setdefault(project_id, default_project_color(project_id))
users = st.session_state.users

with st.sidebar:
    st.header("Filters")
    selected_project_ids = st.multiselect("Project ID", project_ids, default=project_ids)
    selected_people = st.multiselect("Responsible rows", people, default=people)
    selected_statuses = st.multiselect("Status columns", statuses, default=statuses)

    st.divider()
    st.header("Project ID colors")
    with st.form("project_id_colors_form"):
        proposed_project_colors = {}
        for project_id in project_ids:
            current_color = st.session_state.project_colors.get(project_id, default_project_color(project_id))
            proposed_project_colors[project_id] = st.color_picker(
                project_id,
                value=normalize_hex_color(current_color),
                key=f"project_color_{project_id}",
            )

        project_colors_submitted = st.form_submit_button("Apply project colors")

    if project_colors_submitted:
        st.session_state.project_colors.update(
            {
                project_id: normalize_hex_color(color)
                for project_id, color in proposed_project_colors.items()
            }
        )
        st.success("Project ID colors updated.")
        st.rerun()


    st.divider()
    st.header("Board columns")

    with st.form("rename_columns_form"):
        proposed_status_names = []
        for index, status in enumerate(statuses):
            proposed_status_names.append(
                st.text_input(f"Column {index + 1}", value=status, key=f"column_name_{index}")
            )

        rename_columns_submitted = st.form_submit_button("Apply column names")

    if rename_columns_submitted:
        success, message = rename_values("statuses", "status", proposed_status_names, "Column")
        if success:
            st.success(message)
            st.rerun()
        st.error(message)

    with st.form("add_column_form"):
        new_column_name = st.text_input("New column name", placeholder="Waiting for approval")
        add_column_submitted = st.form_submit_button("Add column")

    if add_column_submitted:
        success, message = add_value("statuses", new_column_name, "Column")
        if success:
            st.success(message)
            st.rerun()
        st.error(message)

    st.divider()
    st.header("Project IDs")

    with st.form("rename_project_ids_form"):
        proposed_project_ids = []
        for index, project_id in enumerate(project_ids):
            proposed_project_ids.append(
                st.text_input(f"Project ID {index + 1}", value=project_id, key=f"project_id_{index}")
            )

        rename_projects_submitted = st.form_submit_button("Apply project IDs")

    if rename_projects_submitted:
        success, message = rename_values("project_ids", "project_id", proposed_project_ids, "Project ID")
        if success:
            st.success(message)
            st.rerun()
        st.error(message)

    with st.form("add_project_id_form"):
        new_project_id = st.text_input("New project ID", placeholder="PRJ-004")
        add_project_submitted = st.form_submit_button("Add project ID")

    if add_project_submitted:
        success, message = add_value("project_ids", new_project_id, "Project ID")
        if success:
            st.success(message)
            st.rerun()
        st.error(message)


    st.divider()
    st.header("Responsible rows")

    with st.form("rename_people_form"):
        proposed_people_names = []
        for index, person in enumerate(people):
            proposed_people_names.append(
                st.text_input(f"Row {index + 1}", value=person, key=f"person_name_{index}")
            )

        rename_people_submitted = st.form_submit_button("Apply row names")

    if rename_people_submitted:
        success, message = rename_values("people", "owner", proposed_people_names, "Responsible row")
        if success:
            st.success(message)
            st.rerun()
        st.error(message)

    with st.form("add_person_form"):
        new_person = st.text_input("New responsible row", placeholder="Process Engineer")
        add_person_submitted = st.form_submit_button("Add row")

    if add_person_submitted:
        success, message = add_value("people", new_person, "Responsible row")
        if success:
            st.success(message)
            st.rerun()
        st.error(message)

    with st.form("remove_people_form"):
        rows_to_remove = st.multiselect("Rows to remove", people)
        remove_people_submitted = st.form_submit_button("Remove selected rows")

    if remove_people_submitted:
        success, message = remove_people(rows_to_remove)
        if success:
            st.success(message)
            st.rerun()
        st.error(message)

    st.divider()
    st.header("Task files")

    selected_task_index = st.selectbox(
        "Existing task",
        range(len(st.session_state.tasks)),
        format_func=lambda index: task_option_label(st.session_state.tasks[index]),
    )
    current_attachments = st.session_state.tasks[selected_task_index].get("attachments", [])
    current_attachment_text = ", ".join(current_attachments) or "No files attached"
    st.caption(f"Current files: {current_attachment_text}")
    existing_task_files = st.file_uploader(
        "Add files",
        accept_multiple_files=True,
        key="existing_task_files",
    )
    typed_attachment_names = st.text_area(
        "File paths or links",
        placeholder="Paste one file path or SharePoint link per line",
    )

    if st.button("Attach to task", key="attach_existing_task_files"):
        success, message = add_attachments_to_task(
            selected_task_index,
            existing_task_files,
            typed_attachment_names,
        )
        if success:
            st.success(message)
            st.rerun()
        st.error(message)

filtered_tasks = [
    # Add a stable DOM id for the embedded board. The id is based on the current
    # filtered order and is used only inside the browser component.
    task | {"id": f"task-{index}", "storage_key": f"task-{index}"}
    for index, task in enumerate(st.session_state.tasks)
    if task["project_id"] in selected_project_ids
    and task["owner"] in selected_people
    and task["status"] in selected_statuses
]

quality_todo_tasks = [
    task
    for task in filtered_tasks
    if task["owner"] == "Quality Engineer" and task["status"] == "Backlog / To Do"
]

project_count = len({task["project_id"] for task in filtered_tasks})
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
            <div class="dashboard-label">Quality To Do</div>
            <div class="dashboard-value">{len(quality_todo_tasks)}</div>
        </div>
        <div class="dashboard-tile">
            <div class="dashboard-label">Visible columns</div>
            <div class="dashboard-value">{len(selected_statuses)}</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.subheader("Shared Project Board")
st.caption(
    "Task cards show title, project, and due date. Open Details for the rest. Drag cards between columns and responsible rows."
)

board_action_cols = st.columns([1, 1, 4])
if board_action_cols[0].button("Add task", type="primary"):
    add_task_dialog(project_ids, people, statuses, users)
if board_action_cols[1].button("Attach files"):
    attach_files_dialog()

if st.session_state.get("show_added_task_dialog"):
    task_added_dialog()

visible_statuses = [status for status in statuses if status in selected_statuses]
visible_people = [person for person in people if person in selected_people]
board_html = build_board_html(visible_statuses, visible_people, filtered_tasks)
components.html(board_html, height=board_height(len(visible_people)), scrolling=True)








