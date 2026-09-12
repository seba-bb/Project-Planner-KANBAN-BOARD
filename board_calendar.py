"""Monthly task calendar using the board's saved due dates."""
import calendar
from datetime import date
from html import escape


def due_date(task):
    try:
        return date.fromisoformat(str(task.get("due", "")))
    except ValueError:
        return None


def shift_month(month, offset):
    year, index = divmod(month.year * 12 + month.month - 1 + offset, 12)
    return date(year, index + 1, 1)


def calendar_tasks(tasks):
    grouped, undated = {}, []
    for task in tasks:
        if task.get("archived", False):
            continue
        due = due_date(task)
        if due is None:
            undated.append(task)
        else:
            grouped.setdefault(due, []).append(task)
    return grouped, undated


def build_calendar_html(tasks, month, today=None):
    today = today or date.today()
    grouped, _ = calendar_tasks(tasks)
    parts = ['''<style>
    .planner-calendar { overflow-x: auto; color: #244522; font-family: "Segoe UI", Arial, sans-serif; }
    .planner-calendar table { width: 100%; min-width: 840px; table-layout: fixed; border-collapse: separate; border-spacing: 4px; }
    .planner-calendar caption { text-align: left; font-size: 1.4rem; font-weight: 700; padding: 12px 4px; }
    .planner-calendar th { background: #c1feac; border-radius: 7px; padding: 9px; text-align: center; }
    .planner-calendar td { vertical-align: top; background: #fff; border: 1px solid #dbe8d3; border-radius: 8px; padding: 7px; height: 140px; }
    .planner-calendar td.outside-month { background: #edf3e9; }
    .planner-calendar td.today { border: 2px solid #4b8c37; }
    .planner-calendar .day-number { display: block; font-weight: 600; font-size: .85rem; margin-bottom: 8px; }
    .planner-calendar .outside-month .day-number { color: #65745f; }
    .planner-calendar .calendar-task { border: 1px solid #b8dca8; border-left: 4px solid #80c767; border-radius: 6px; background: #f0faeb; margin-bottom: 7px; font-size: .82rem; overflow-wrap: anywhere; }
    .planner-calendar .calendar-task.overdue { border-color: #ef9999; border-left-color: #dc2626; background: #fff0f0; }
    .planner-calendar .calendar-task.due-soon { border-color: #e6cf70; border-left-color: #d4a900; background: #fff8d6; }
    .planner-calendar summary { padding: 7px; cursor: pointer; }
    .planner-calendar .task-title { font-weight: 600; }
    .planner-calendar .due-label { display: block; font-size: .72rem; margin-top: 4px; }
    .planner-calendar .overdue .due-label { color: #b91c1c; font-weight: 700; }
    .planner-calendar .calendar-task-body { border-top: 1px solid #dbe8d3; padding: 7px; }
    .planner-calendar .calendar-description { white-space: pre-wrap; margin-top: 6px; }
    </style><div class="planner-calendar"><table>''']
    parts.append(f'<caption>{escape(month.strftime("%B %Y"))}</caption><thead><tr>')
    parts.extend(f'<th scope="col">{day}</th>' for day in ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'])
    parts.append('</tr></thead><tbody>')
    for week in calendar.Calendar(firstweekday=0).monthdatescalendar(month.year, month.month):
        parts.append('<tr>')
        for day in week:
            classes = ('outside-month ' if day.month != month.month else '') + ('today' if day == today else '')
            current = ' aria-current="date"' if day == today else ''
            parts.append(f'<td class="{classes}" data-date="{day.isoformat()}"><time class="day-number" datetime="{day.isoformat()}"{current}>{day.day}{" · Today" if day == today else ""}</time>')
            for task in grouped.get(day, []):
                days = (day - today).days
                urgency = 'overdue' if days < 0 else 'due-soon' if days <= 5 else ''
                label = f'Overdue · {-days} day(s)' if days < 0 else 'Due today' if days == 0 else f'Due in {days} day(s)'
                members = task.get('responsible_emails', task.get('responsible_email', []))
                if isinstance(members, list):
                    members = ', '.join(members)
                parts.append(
                    f'<details class="calendar-task {urgency}" data-task-id="{escape(str(task.get("id", "")), quote=True)}">'
                    f'<summary><span class="task-title">{escape(task["title"])}</span>'
                    f'<span class="due-label">{label}</span></summary><div class="calendar-task-body">'
                    f'<strong>Due:</strong> {day.isoformat()}<br><strong>Column:</strong> {escape(task["status"])}<br>'
                    f'<strong>Responsible:</strong> {escape(members or "Unassigned")}'
                    f'<div class="calendar-description">{escape(task.get("description", ""))}</div></div></details>'
                )
            parts.append('</td>')
        parts.append('</tr>')
    parts.append('</tbody></table></div>')
    return ''.join(parts)


def render_calendar(tasks):
    import streamlit as st

    today = date.today()
    st.session_state.setdefault('calendar_month', today.replace(day=1))

    def select_month(month):
        st.session_state.calendar_month = month.replace(day=1)
        st.session_state.calendar_jump = month.replace(day=1)

    def jump_to_month():
        select_month(st.session_state.calendar_jump or st.session_state.calendar_month)

    month = st.session_state.calendar_month
    st.session_state.setdefault('calendar_jump', month)
    st.subheader('Task calendar')
    st.caption('Tasks appear on their required completion date and follow the board filters. Archived items are excluded. Filter to unfinished columns to focus on outstanding work.')
    previous, current, following, picker = st.columns([1, 1, 1, 3])
    previous.button('Previous month', key='calendar_previous', on_click=select_month, args=(shift_month(month, -1),), disabled=month == date(2, 1, 1), width='stretch')
    current.button('Today', key='calendar_today', on_click=select_month, args=(today,), width='stretch')
    following.button('Next month', key='calendar_next', on_click=select_month, args=(shift_month(month, 1),), disabled=month == date(9998, 12, 1), width='stretch')
    picker.date_input('Go to month', value=None, min_value=date(2, 1, 1), max_value=date(9998, 12, 31),
                      key='calendar_jump', on_change=jump_to_month, label_visibility='collapsed', help='Choose any date in the month you want to view.')
    grouped, undated = calendar_tasks(tasks)
    overdue = [task for due in sorted(grouped) if due < today for task in grouped[due]]
    if overdue:
        st.error(f'{len(overdue)} task(s) have a past due date in the selected columns. The overdue list below includes other months.')
    st.caption('Red: overdue · Yellow: due today or within 5 days · Green: due later. Click a task to see its details.')
    if not tasks:
        st.info('No tasks match these filters. Change or clear the filters to see calendar tasks.')
    st.html(build_calendar_html(tasks, month, today))
    if overdue:
        with st.expander(f'Overdue tasks ({len(overdue)})'):
            st.dataframe([{'Task': task['title'], 'Due': task['due'], 'Column': task['status'],
                           'Days overdue': (today - due_date(task)).days} for task in overdue], hide_index=True, width='stretch')
    if undated:
        with st.expander(f'Tasks without a valid due date ({len(undated)})'):
            st.caption('Set a due date in the task details on the board to place these tasks on the calendar.')
            st.dataframe([{'Task': task['title'], 'Column': task['status']} for task in undated], hide_index=True, width='stretch')
