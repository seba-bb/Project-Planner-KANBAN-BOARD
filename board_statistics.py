"""Current Kanban statistics, calculated without changing board data."""
from collections import Counter
from datetime import date


DUE_COLORS = {
    "Overdue": "#dc2626",
    "Due today": "#f59e0b",
    "Due in 1–5 days": "#e6c644",
    "Due later": "#80c767",
    "No valid date": "#94a3b8",
}


def calculate_statistics(tasks, statuses, labels, today=None):
    today = today or date.today()
    # Callers supply active columns, so archived columns and tickets stay excluded.
    tasks = [task for task in tasks if not task.get("archived", False) and task["status"] in statuses]
    status_counts = Counter(task["status"] for task in tasks)
    due_counts = Counter({name: 0 for name in DUE_COLORS})
    member_counts = Counter()
    label_counts = Counter()
    label_catalog = {label["id"]: label for label in labels}
    assigned = labelled = 0
    for task in tasks:
        try:
            days = (date.fromisoformat(str(task.get("due", ""))) - today).days
            bucket = "Overdue" if days < 0 else "Due today" if days == 0 else "Due in 1–5 days" if days <= 5 else "Due later"
        except ValueError:
            bucket = "No valid date"
        due_counts[bucket] += 1
        members = task.get("responsible_emails", task.get("responsible_email", []))
        if isinstance(members, str):
            members = members.split(",")
        members = {email.strip().lower() for email in members if email.strip()}
        assigned += bool(members)
        member_counts.update(members or {"Unassigned"})
        selected = set(task.get("labels", [])) & label_catalog.keys()
        labelled += bool(selected)
        label_counts.update(selected or {None})
    return {
        "total": len(tasks), "assigned": assigned, "labelled": labelled,
        "columns": [{"name": status, "tasks": status_counts[status]} for status in statuses],
        "due": [{"name": name, "tasks": due_counts[name], "color": color} for name, color in DUE_COLORS.items()],
        "members": [{"name": name, "tasks": count} for name, count in sorted(member_counts.items(), key=lambda item: (-item[1], item[0]))],
        "labels": [
            {"name": label_catalog[label_id]["name"] if label_id else "No labels", "tasks": count,
             "color": label_catalog[label_id]["color"] if label_id else "#94a3b8"}
            for label_id, count in sorted(label_counts.items(), key=lambda item: (-item[1], str(item[0])))
        ],
    }


def chart_spec(rows, *, donut=False):
    """Vega-Lite charts provide hover details and responsive sizing."""
    names = [row["name"] for row in rows]
    spec = {
        "data": {"values": rows},
        "height": 280 if donut else max(180, 32 * len(rows)),
        "mark": {"type": "arc", "innerRadius": 65} if donut else {"type": "bar", "cornerRadiusEnd": 4, "color": "#80c767"},
        "encoding": {
            "tooltip": [{"field": "name", "type": "nominal", "title": "Category"},
                        {"field": "tasks", "type": "quantitative", "title": "Tasks", "format": ",d"}],
        },
        "config": {"background": "transparent", "view": {"stroke": None}, "font": "Segoe UI",
                   "axis": {"labelColor": "#285b32", "titleColor": "#285b32", "gridColor": "#e5efdf"}},
    }
    if donut:
        spec["encoding"]["theta"] = {"field": "tasks", "type": "quantitative"}
    else:
        spec["encoding"].update({
            "x": {"field": "tasks", "type": "quantitative", "title": "Tasks", "axis": {"tickMinStep": 1, "format": "d"}},
            "y": {"field": "name", "type": "nominal", "title": None, "sort": names, "axis": {"labelLimit": 300}},
        })
    if rows and "color" in rows[0]:
        spec["encoding"]["color"] = {
            "field": "name", "type": "nominal", "title": None,
            "scale": {"domain": names, "range": [row["color"] for row in rows]},
            "legend": {"orient": "bottom", "columns": 2} if donut else None,
        }
    return spec


def render_statistics(tasks, statuses, labels):
    import streamlit as st

    stats = calculate_statistics(tasks, statuses, labels)
    st.subheader("Board statistics")
    st.caption("Current tasks matching the board filters. Archived tickets and columns are excluded.")
    for column, label, value in zip(st.columns(4),
                                    ["Tasks", "Selected columns", "Assigned tasks", "Tasks with labels"],
                                    [stats["total"], len(statuses), stats["assigned"], stats["labelled"]]):
        column.metric(label, value, border=True)
    if not stats["total"]:
        st.info("No tasks match these filters. Change or clear the filters to see statistics.")
        return

    def chart(title, caption, rows, key, donut=False):
        with st.container(border=True):
            st.markdown(f"**{title}**")
            st.caption(caption)
            st.vega_lite_chart(spec=chart_spec(rows, donut=donut), width="stretch", theme=None, key=key)
            with st.expander("View chart data"):
                st.dataframe([{"Category": row["name"], "Tasks": row["tasks"]} for row in rows], hide_index=True, width="stretch")

    left, right = st.columns(2)
    with left:
        chart("Tasks by column", "See where tasks are concentrated across the board.", stats["columns"], "stats_columns")
    with right:
        chart("Due-date overview", "Includes all selected columns. Filter to unfinished columns to review outstanding deadlines.", stats["due"], "stats_due", donut=True)
    left, right = st.columns(2)
    with left:
        chart("Workload by responsible person", "Shared tickets count once for each responsible person; totals can exceed the number of tasks.", stats["members"], "stats_members")
    with right:
        chart("Tasks by label", "Tickets with several labels count once under each label.", stats["labels"], "stats_labels")
