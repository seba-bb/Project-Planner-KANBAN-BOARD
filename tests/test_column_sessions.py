"""Exercise actual Streamlit callbacks and filters using a test component bridge."""
import json
from pathlib import Path
import re
import shutil
import tempfile
import unittest

from streamlit.testing.v1 import AppTest


class ColumnSessionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.target = Path(self.directory.name)
        root = Path(__file__).resolve().parents[1]
        shutil.copy2(root / 'notifications.py', self.target / 'notifications.py')
        shutil.copy2(root / 'board_statistics.py', self.target / 'board_statistics.py')
        shutil.copytree(root / 'assets', self.target / 'assets')
        source = (root / 'app.py').read_text(encoding='utf-8-sig')
        # AppTest cannot drive custom iframe widgets. Adapt only that transport to
        # a text widget, retaining the production callback and all filter widgets.
        shim = '''
def declare_test_component(*args, **kwargs):
    def render(**options):
        def receive():
            st.session_state.kanban_board = json.loads(st.session_state.test_board_event)
            options["on_change"]()
        st.text_input("Board event", key="test_board_event", on_change=receive)
        st.session_state.test_board_html = options["html"]
    return render

'''
        source = source.replace('initialize_state()\nif not TASK_DATABASE_CSV.exists():', shim + 'initialize_state()\nif not TASK_DATABASE_CSV.exists():')
        source = source.replace('kanban_component = components.declare_component(', 'kanban_component = declare_test_component(')
        self.app_path = self.target / 'app.py'
        self.app_path.write_text(source, encoding='utf-8-sig')

    def session(self):
        app = AppTest.from_file(str(self.app_path)).run(timeout=15)
        self.assertFalse(app.exception)
        return app

    def event(self, app, **event):
        app.text_input(key='test_board_event').set_value(json.dumps(event)).run(timeout=15)
        self.assertFalse(app.exception)
        self.assertTrue(app.session_state.board_save_result['ok'])

    def board(self, app):
        return json.loads(re.search(r'const data = (.*);\n', app.session_state.test_board_html)[1])

    def test_status_filter_does_not_hide_previously_added_columns(self):
        app = self.session()
        original = app.session_state.statuses.copy()
        self.event(app, event_id='first', action='add_column', name='First new')
        # Simulate a browser still posting its earlier status-filter selection.
        app.multiselect(key='status_filter').set_value(original)
        self.event(app, event_id='second', action='add_column', name='Second new')
        expected = original + ['First new', 'Second new']
        self.assertEqual(self.board(app)['statuses'], expected)
        self.assertEqual(json.loads((self.target / 'board_columns.json').read_text()), expected)
        app.multiselect(key='status_filter').set_value(['Completed']).run(timeout=15)
        self.assertEqual(self.board(app)['statuses'], expected)
        self.assertTrue(all(task['status'] == 'Completed' for task in self.board(app)['tasks']))

    def test_two_sessions_keep_both_additions_and_reload_renamed_statuses(self):
        first, second = self.session(), self.session()
        original = first.session_state.statuses.copy()
        self.event(first, event_id='first', action='add_column', name='First new')
        self.event(second, event_id='second', action='add_column', name='Second new')
        expected = original + ['First new', 'Second new']
        self.assertEqual(self.board(second)['statuses'], expected)
        self.event(first, event_id='rename', action='rename_column', status=original[0], name='Ready')
        second.text_input(key='filter_keyword').set_value('parts').run(timeout=15)
        self.assertFalse(second.exception)
        self.assertEqual(self.board(second)['statuses'], ['Ready', *expected[1:]])
        self.assertNotIn(original[0], {task['status'] for task in second.session_state.tasks})
        self.assertEqual(self.board(self.session())['statuses'], ['Ready', *expected[1:]])

    def test_column_archive_hides_then_restores_saved_tickets_after_reload(self):
        app = self.session()
        status = app.session_state.statuses[0]
        original_csv = (self.target / 'project_planner_actions.csv').read_bytes()
        self.event(app, event_id='sort', action='sort_column', status=status, sort_by='due')
        self.event(app, event_id='archive', action='archive_column', status=status)
        self.assertNotIn(status, self.board(app)['statuses'])
        self.assertFalse(any(task['status'] == status for task in self.board(app)['tasks']))
        self.assertEqual((self.target / 'project_planner_actions.csv').read_bytes(), original_csv)
        app = self.session()
        self.assertNotIn(status, self.board(app)['statuses'])
        app.button(key=f'restore_column_{status}').click().run(timeout=15)
        self.assertFalse(app.exception)
        self.assertIn(status, self.board(app)['statuses'])
        tasks = [task for task in self.board(app)['tasks'] if task['status'] == status]
        self.assertTrue(tasks)
        self.assertEqual([task['due'] for task in tasks], sorted(task['due'] for task in tasks))
        self.assertEqual(self.board(app)['column_settings'][status]['sort'], 'due')

    def test_ticket_archive_hides_then_restores_from_archive_control(self):
        app = self.session()
        task_id = self.board(app)['tasks'][0]['id']
        self.event(app, event_id='archive-ticket', action='archive_task', task_id=task_id)
        self.assertNotIn(task_id, [task['id'] for task in self.board(app)['tasks']])
        app = self.session()
        self.assertNotIn(task_id, [task['id'] for task in self.board(app)['tasks']])
        app.button(key=f'restore_ticket_{task_id}').click().run(timeout=15)
        self.assertFalse(app.exception)
        self.assertIn(task_id, [task['id'] for task in self.board(app)['tasks']])
        self.assertFalse(any('dashboard-strip' in element.value for element in app.markdown))

    def test_drag_position_survives_component_rerender_and_fresh_session(self):
        app = self.session()
        status = 'In Progress'
        self.event(app, event_id='sort', action='sort_column', status=status, sort_by='due')
        board = self.board(app)
        moving = next(task for task in board['tasks'] if task['status'] != status)
        neighbors = [task['id'] for task in board['tasks'] if task['status'] == status]
        self.assertGreaterEqual(len(neighbors), 2)
        self.event(app, event_id='drop', action='edit_task', task_id=moving['id'],
                   updates={'status': status}, before_task_id=neighbors[1])
        expected = [neighbors[0], moving['id'], *neighbors[1:]]
        for session in (app, self.session()):
            saved = self.board(session)
            self.assertEqual([task['id'] for task in saved['tasks'] if task['status'] == status], expected)
            self.assertEqual(saved['column_settings'][status]['sort'], 'default')

    def test_statistics_navigation_filters_and_archive_control_position(self):
        app = self.session()
        # The archive control is rendered after the board's component transport.
        elements = list(app.main)
        board_index = next(i for i, element in enumerate(elements) if getattr(element, 'key', None) == 'test_board_event')
        archive_index = next(i for i, element in enumerate(elements) if element.type == 'popover' and element.proto.popover.label == 'Archived items')
        self.assertGreater(archive_index, board_index)
        original_csv = (self.target / 'project_planner_actions.csv').read_bytes()
        app.multiselect(key='status_filter').set_value(['In Progress']).run(timeout=15)
        expected = len(self.board(app)['tasks'])
        app.button(key='toggle_statistics').click().run(timeout=15)
        self.assertFalse(app.exception)
        self.assertEqual(app.button(key='toggle_statistics').label, 'Back to board')
        self.assertEqual(app.metric[0].value, str(expected))
        self.assertEqual(len(app.get('vega_lite_chart')), 4)
        self.assertEqual(len(app.text_input(key='filter_keyword').value), 0)
        self.assertFalse(any(element.key == 'test_board_event' for element in app.text_input))
        app.text_input(key='filter_keyword').set_value('no matching ticket xyz').run(timeout=15)
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, '0')
        self.assertEqual(len(app.get('vega_lite_chart')), 0)
        self.assertTrue(any('No tasks match' in info.value for info in app.info))
        app.button(key='toggle_statistics').click().run(timeout=15)
        self.assertFalse(app.exception)
        self.assertEqual(app.multiselect(key='status_filter').value, ['In Progress'])
        self.assertEqual(app.text_input(key='filter_keyword').value, 'no matching ticket xyz')
        self.assertEqual(self.board(app)['tasks'], [])
        self.assertEqual((self.target / 'project_planner_actions.csv').read_bytes(), original_csv)

    def test_archiving_all_columns_does_not_lose_them_or_prevent_adding_a_new_one(self):
        app = self.session()
        original = app.session_state.statuses.copy()
        for index, status in enumerate(original):
            self.event(app, event_id=f'archive-{index}', action='archive_column', status=status)
        self.assertEqual(self.board(app)['statuses'], [])
        self.assertEqual(self.board(app)['tasks'], [])
        self.event(app, event_id='new-column', action='add_column', name='New active column')
        self.assertEqual(self.board(app)['statuses'], ['New active column'])
        self.assertEqual(app.session_state.statuses, original + ['New active column'])


if __name__ == '__main__':
    unittest.main()
