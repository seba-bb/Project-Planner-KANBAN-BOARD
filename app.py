from __future__ import annotations

import json
from html import escape

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
    page_title="Engineering Workflow Manager",
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
        .metric-row [data-testid="stMetric"] {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 12px 14px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


def initialize_state() -> None:
    if "statuses" not in st.session_state:
        st.session_state.statuses = DEFAULT_STATUSES.copy()
    if "people" not in st.session_state:
        st.session_state.people = DEFAULT_PEOPLE.copy()
    if "project_ids" not in st.session_state:
        st.session_state.project_ids = DEFAULT_PROJECT_IDS.copy()
    if "tasks" not in st.session_state:
        st.session_state.tasks = [task.copy() for task in DEFAULT_TASKS]


def normalize_name(name: str) -> str:
    return " ".join(name.strip().split())


def rename_values(
    state_key: str,
    task_field: str,
    new_names: list[str],
    item_label: str,
) -> tuple[bool, str]:
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


def remove_people(people_to_remove: list[str]) -> tuple[bool, str]:
    if not people_to_remove:
        return False, "Select at least one row to remove."

    remaining_people = [person for person in st.session_state.people if person not in people_to_remove]
    if not remaining_people:
        return False, "At least one responsible row must remain."

    st.session_state.people = remaining_people
    return True, "Responsible rows removed. Tasks assigned to removed rows are hidden until the row is added again."


def build_board_html(statuses: list[str], people: list[str], tasks: list[dict[str, str]]) -> str:
    board_data = {
        "statuses": statuses,
        "people": people,
        "tasks": tasks,
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
        overflow-x: auto;
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
        z-index: 2;
        background: #ffffff;
    }}
    .header, .person, .column-header {{
        border-bottom: 1px solid #dbe3ef;
        color: #475569;
        font-size: 12px;
        font-weight: 800;
        letter-spacing: 0;
        min-height: 36px;
        padding: 10px 8px 7px;
        text-transform: uppercase;
    }}
    .person {{
        align-items: start;
        color: #111827;
        display: flex;
        font-size: 14px;
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
    .task-title {{
        color: #0f172a;
        font-size: 14px;
        font-weight: 800;
        line-height: 1.25;
        margin-bottom: 8px;
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
</style>
</head>
<body>
<p class="hint">Hold a task card and drop it into another column or another responsible row. Open Details for stage, status, owner, and description.</p>
<div class="board-wrap">
    <div id="board" class="board"></div>
</div>
<script>
const data = {payload};
const board = document.getElementById("board");
let draggedId = null;

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

function addCell(tag, className, content) {{
    const cell = document.createElement(tag);
    cell.className = className;
    cell.textContent = content;
    board.appendChild(cell);
    return cell;
}}

function createTaskCard(task) {{
    const card = document.createElement("div");
    card.className = cardClass(task.status);
    card.draggable = true;
    card.id = task.id;
    card.dataset.owner = task.owner;
    card.dataset.status = task.status;

    card.innerHTML = `
        <div class="task-title"></div>
        <div class="task-summary">
            <strong>Project:</strong> <span class="project"></span><br>
            <strong>Due:</strong> <span class="due"></span>
        </div>
        <details>
            <summary>Details</summary>
            <div class="task-details">
                <strong>Project ID:</strong> <span class="project-id"></span><br>
                <strong>Owner:</strong> <span class="owner"></span><br>
                <strong>Status:</strong> <span class="status"></span><br>
                <strong>Stage:</strong> <span class="stage"></span><br>
                <strong>Description:</strong> <span class="description"></span>
            </div>
        </details>
    `;

    card.querySelector(".task-title").textContent = text(task.title);
    card.querySelector(".project").textContent = text(task.project);
    card.querySelector(".due").textContent = text(task.due);
    card.querySelector(".project-id").textContent = text(task.project_id);
    card.querySelector(".owner").textContent = text(task.owner);
    card.querySelector(".status").textContent = text(task.status);
    card.querySelector(".stage").textContent = text(task.stage);
    card.querySelector(".description").textContent = text(task.description);

    card.addEventListener("dragstart", event => {{
        draggedId = card.id;
        event.dataTransfer.effectAllowed = "move";
        event.dataTransfer.setData("text/plain", card.id);
    }});

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

        card.dataset.owner = person;
        card.dataset.status = status;
        card.className = cardClass(status);
        card.querySelector(".owner").textContent = person;
        card.querySelector(".status").textContent = status;
        zone.appendChild(card);
    }});

    return zone;
}}

function renderBoard() {{
    board.style.setProperty("--column-count", data.statuses.length);
    addCell("div", "header", "Responsible");
    data.statuses.forEach(status => addCell("div", "column-header", status));

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
    return max(520, 92 + people_count * 230)


initialize_state()

st.title("Engineering Workflow Manager")
st.caption("Dashboard board view grouped by responsible people")

statuses = st.session_state.statuses
people = st.session_state.people
project_ids = st.session_state.project_ids

with st.sidebar:
    st.header("Filters")
    selected_project_ids = st.multiselect("Project ID", project_ids, default=project_ids)
    selected_people = st.multiselect("Responsible rows", people, default=people)
    selected_statuses = st.multiselect("Status columns", statuses, default=statuses)

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

filtered_tasks = [
    task | {"id": f"task-{index}"}
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

st.markdown('<div class="metric-row">', unsafe_allow_html=True)
metric_cols = st.columns(4)
metric_cols[0].metric("All tasks", len(filtered_tasks))
metric_cols[1].metric("Projects", len({task["project_id"] for task in filtered_tasks}))
metric_cols[2].metric("Quality To Do", len(quality_todo_tasks))
metric_cols[3].metric("Visible columns", len(selected_statuses))
st.markdown('</div>', unsafe_allow_html=True)

st.subheader("Shared Project Board")
st.caption(
    "Task cards show title, project, and due date. Open Details for the rest. Drag cards between columns and responsible rows."
)

visible_statuses = [status for status in statuses if status in selected_statuses]
visible_people = [person for person in people if person in selected_people]
board_html = build_board_html(visible_statuses, visible_people, filtered_tasks)
components.html(board_html, height=board_height(len(visible_people)), scrolling=True)
