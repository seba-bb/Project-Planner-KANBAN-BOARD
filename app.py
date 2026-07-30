from __future__ import annotations

from html import escape

import streamlit as st


DEFAULT_STATUSES = ["Backlog / To Do", "In Progress", "Completed", "Rejected"]
PEOPLE = [
    "Project Manager",
    "Manufacturing Engineer",
    "Quality Engineer",
    "Purchasing",
    "Logistics",
    "Technical Director",
]

DEFAULT_TASKS = [
    {
        "title": "Create project record",
        "owner": "Project Manager",
        "status": "Completed",
        "due": "2026-08-02",
        "stage": "Project Setup",
        "project_id": "PRJ-001",
        "project": "NPI - Stamping Bracket",
    },
    {
        "title": "Upload Purchase Order",
        "owner": "Project Manager",
        "status": "Backlog / To Do",
        "due": "2026-08-04",
        "stage": "Project Setup",
        "project_id": "PRJ-001",
        "project": "NPI - Stamping Bracket",
    },
    {
        "title": "Manufacturing feasibility checklist",
        "owner": "Manufacturing Engineer",
        "status": "In Progress",
        "due": "2026-08-08",
        "stage": "Feasibility Review",
        "project_id": "PRJ-001",
        "project": "NPI - Stamping Bracket",
    },
    {
        "title": "Quality approval",
        "owner": "Quality Engineer",
        "status": "Backlog / To Do",
        "due": "2026-08-09",
        "stage": "Feasibility Review",
        "project_id": "PRJ-001",
        "project": "NPI - Stamping Bracket",
    },
    {
        "title": "Packaging concept review",
        "owner": "Logistics",
        "status": "Backlog / To Do",
        "due": "2026-08-12",
        "stage": "Documentation Preparation",
        "project_id": "PRJ-002",
        "project": "Engineering Change - Seat Rail Clip",
    },
    {
        "title": "Supplier cost confirmation",
        "owner": "Purchasing",
        "status": "In Progress",
        "due": "2026-08-11",
        "stage": "Purchasing and Logistics",
        "project_id": "PRJ-002",
        "project": "Engineering Change - Seat Rail Clip",
    },
    {
        "title": "Approve technical feasibility",
        "owner": "Technical Director",
        "status": "Backlog / To Do",
        "due": "2026-08-10",
        "stage": "Feasibility Review",
        "project_id": "PRJ-003",
        "project": "Tool Transfer - Door Reinforcement",
    },
    {
        "title": "Old container concept",
        "owner": "Logistics",
        "status": "Rejected",
        "due": "2026-08-06",
        "stage": "Purchasing and Logistics",
        "project_id": "PRJ-003",
        "project": "Tool Transfer - Door Reinforcement",
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
        .swimlane-title {
            font-weight: 700;
            font-size: 0.95rem;
            padding: 10px 0 2px;
            color: #111827;
        }
        .column-title {
            font-size: 0.78rem;
            font-weight: 700;
            text-transform: uppercase;
            color: #475569;
            border-bottom: 1px solid #e2e8f0;
            padding-bottom: 8px;
            margin-bottom: 8px;
            min-height: 38px;
        }
        .task-card {
            border: 1px solid #dbe3ef;
            border-left: 4px solid #2563eb;
            border-radius: 8px;
            padding: 10px 11px;
            margin-bottom: 9px;
            background: white;
            min-height: 148px;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.05);
        }
        .task-card.completed { border-left-color: #16a34a; }
        .task-card.rejected { border-left-color: #dc2626; }
        .task-card.progress { border-left-color: #f59e0b; }
        .task-title {
            font-weight: 700;
            color: #0f172a;
            line-height: 1.25;
            margin-bottom: 8px;
        }
        .task-meta {
            font-size: 0.78rem;
            color: #475569;
            line-height: 1.45;
        }
        .empty-cell {
            border: 1px dashed #cbd5e1;
            border-radius: 8px;
            min-height: 148px;
            background: #f8fafc;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


def initialize_state() -> None:
    if "statuses" not in st.session_state:
        st.session_state.statuses = DEFAULT_STATUSES.copy()
    if "tasks" not in st.session_state:
        st.session_state.tasks = [task.copy() for task in DEFAULT_TASKS]


def normalize_column_name(name: str) -> str:
    return " ".join(name.strip().split())


def rename_columns(new_names: list[str]) -> tuple[bool, str]:
    cleaned_names = [normalize_column_name(name) for name in new_names]

    if any(not name for name in cleaned_names):
        return False, "Column names cannot be empty."

    if len(set(cleaned_names)) != len(cleaned_names):
        return False, "Column names must be unique."

    old_names = st.session_state.statuses.copy()
    rename_map = dict(zip(old_names, cleaned_names, strict=True))
    st.session_state.statuses = cleaned_names

    for task in st.session_state.tasks:
        task["status"] = rename_map.get(task["status"], task["status"])

    return True, "Column names updated."


def add_column(column_name: str) -> tuple[bool, str]:
    cleaned_name = normalize_column_name(column_name)

    if not cleaned_name:
        return False, "Enter a column name first."

    if cleaned_name in st.session_state.statuses:
        return False, "This column already exists."

    st.session_state.statuses.append(cleaned_name)
    return True, f"Added column: {cleaned_name}."


def card_class(status: str) -> str:
    lowered = status.lower()
    if "completed" in lowered or "done" in lowered:
        return "task-card completed"
    if "rejected" in lowered or "cancel" in lowered:
        return "task-card rejected"
    if "progress" in lowered or "active" in lowered:
        return "task-card progress"
    return "task-card"


def render_task_card(task: dict[str, str]) -> None:
    st.markdown(
        f"""
        <div class=\"{card_class(task['status'])}\">
            <div class=\"task-title\">{escape(task['title'])}</div>
            <div class=\"task-meta\">
                <strong>Project ID:</strong> {escape(task['project_id'])}<br>
                <strong>Project:</strong> {escape(task['project'])}<br>
                <strong>Stage:</strong> {escape(task['stage'])}<br>
                <strong>Due:</strong> {escape(task['due'])}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


initialize_state()

st.title("Engineering Workflow Manager")
st.caption("Dashboard board view grouped by responsible people")

statuses = st.session_state.statuses
project_ids = sorted({task["project_id"] for task in st.session_state.tasks})

with st.sidebar:
    st.header("Filters")
    selected_project_ids = st.multiselect("Project ID", project_ids, default=project_ids)
    selected_people = st.multiselect("Responsible people", PEOPLE, default=PEOPLE)
    selected_statuses = st.multiselect("Status columns", statuses, default=statuses)

    st.divider()
    st.header("Board columns")

    with st.form("rename_columns_form"):
        proposed_names = []
        for index, status in enumerate(statuses):
            proposed_names.append(st.text_input(f"Column {index + 1}", value=status, key=f"column_name_{index}"))

        rename_submitted = st.form_submit_button("Apply column names")

    if rename_submitted:
        success, message = rename_columns(proposed_names)
        if success:
            st.success(message)
            st.rerun()
        st.error(message)

    with st.form("add_column_form"):
        new_column_name = st.text_input("New column name", placeholder="Waiting for approval")
        add_submitted = st.form_submit_button("Add column")

    if add_submitted:
        success, message = add_column(new_column_name)
        if success:
            st.success(message)
            st.rerun()
        st.error(message)

filtered_tasks = [
    task
    for task in st.session_state.tasks
    if task["project_id"] in selected_project_ids
    and task["owner"] in selected_people
    and task["status"] in selected_statuses
]

st.markdown('<div class="metric-row">', unsafe_allow_html=True)
metric_cols = st.columns(4)
metric_cols[0].metric("All tasks", len(filtered_tasks))
metric_cols[1].metric(
    "Backlog / To Do",
    sum(task["status"] == "Backlog / To Do" for task in filtered_tasks),
)
metric_cols[2].metric(
    "In Progress",
    sum(task["status"] == "In Progress" for task in filtered_tasks),
)
metric_cols[3].metric("Projects", len({task["project_id"] for task in filtered_tasks}))
st.markdown('</div>', unsafe_allow_html=True)

st.subheader("Shared Project Board")
st.caption(
    "Columns show configurable task statuses. Rows are swimlanes for the responsible people."
)

visible_statuses = [status for status in statuses if status in selected_statuses]
column_weights = [1.25] + [1] * len(visible_statuses)

header_cols = st.columns(column_weights, gap="small")
header_cols[0].markdown("<div class='column-title'>Responsible</div>", unsafe_allow_html=True)
for index, status in enumerate(visible_statuses, start=1):
    header_cols[index].markdown(
        f"<div class='column-title'>{escape(status)}</div>",
        unsafe_allow_html=True,
    )

for person in PEOPLE:
    if person not in selected_people:
        continue

    row_cols = st.columns(column_weights, gap="small")
    row_cols[0].markdown(f"<div class='swimlane-title'>{escape(person)}</div>", unsafe_allow_html=True)

    for index, status in enumerate(visible_statuses, start=1):
        tasks_for_cell = [
            task
            for task in filtered_tasks
            if task["owner"] == person and task["status"] == status
        ]

        with row_cols[index]:
            if tasks_for_cell:
                for task in tasks_for_cell:
                    render_task_card(task)
            else:
                st.markdown("<div class='empty-cell'></div>", unsafe_allow_html=True)
