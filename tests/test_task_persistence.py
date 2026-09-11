"""Exercise the app's CSV save boundary without starting its Streamlit UI."""
import ast
import copy
import csv
import json
import os
import re
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import uuid4
from datetime import date


class State(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__


class TaskPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.state = State()
        self.namespace = dict(
            csv=csv, json=json, os=os, re=re, tempfile=tempfile, Path=Path, uuid4=uuid4, date=date,
            st=SimpleNamespace(session_state=self.state),
            TASK_DATABASE_CSV=Path(self.directory.name) / 'tasks.csv',
            BOARD_COLUMNS_JSON=Path(self.directory.name) / 'columns.json',
        )
        source = Path(__file__).resolve().parents[1] / 'app.py'
        tree = ast.parse(source.read_text(encoding='utf-8-sig'))
        functions = {
            'csv_json_list', 'task_from_csv_row', 'task_to_csv_row',
            'responsible_emails_list', 'load_tasks_from_csv',
            'write_tasks_to_csv', 'save_tasks_to_csv', 'apply_board_edit',
            'normalize_email', 'clean_responsible_emails', 'normalize_name',
            'load_board_columns', 'write_board_columns', 'rename_board_columns',
            'apply_column_rename', 'rename_values', 'add_value',
            'move_board_column', 'apply_column_action', 'task_matches_filters', 'reset_board_filters',
        }
        constants = {'TASK_CSV_FIELDS', 'DEFAULT_STATUSES', 'DEFAULT_PROJECT_IDS'}
        nodes = [node for node in tree.body if
                 (isinstance(node, ast.FunctionDef) and node.name in functions) or
                 (isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in constants for t in node.targets))]
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), 'exec'), self.namespace)
        self.state.tasks = [dict(
            id='ticket-a', title='Inspect parts', project='Demo', project_id='PRJ-001',
            owner='Quality Engineer', responsible_emails=['first@example.com'],
            status='Backlog / To Do', due='2026-10-01', description='Details',
            attachments=[], email_notification=False,
        )]
        self.namespace['save_tasks_to_csv']()
        self.state.statuses = self.namespace['DEFAULT_STATUSES'].copy()

    def edit(self, updates, task_id='ticket-a', event_id=None):
        self.namespace['apply_board_edit'](dict(
            task_id=task_id, event_id=event_id or uuid4().hex, updates=updates,
        ))

    def load(self):
        return self.namespace['load_tasks_from_csv']()

    def test_assignees_survive_fresh_load_and_status_move(self):
        emails = ['first@example.com', 'anna.nowak@example.com']
        self.edit({'responsible_emails': emails})
        self.assertTrue(self.state.board_save_result['ok'])
        self.state.tasks = self.load()
        self.assertEqual(self.state.tasks[0]['responsible_emails'], emails)
        self.edit({'status': 'Completed'})
        saved = self.load()[0]
        self.assertEqual(saved['responsible_emails'], emails)
        self.assertEqual(saved['owner'], 'Quality Engineer')
        self.assertEqual(saved['status'], 'Completed')

    def test_edit_uses_id_and_preserves_another_ticket_saved_on_disk(self):
        second = self.state.tasks[0] | {'id': 'ticket-b', 'title': 'Another ticket'}
        self.namespace['write_tasks_to_csv']([second, self.state.tasks[0]])
        self.edit({'responsible_emails': ['new@example.com']})
        saved = self.load()
        self.assertEqual(saved[0]['title'], 'Another ticket')
        self.assertEqual(saved[0]['responsible_emails'], ['first@example.com'])
        self.assertEqual(saved[1]['responsible_emails'], ['new@example.com'])

    def test_new_email_is_normalized_and_not_duplicated(self):
        self.edit({'responsible_emails': [' Anna.Nowak@example.com ', 'anna.nowak@example.com']})
        self.assertTrue(self.state.board_save_result['ok'])
        self.assertEqual(self.load()[0]['responsible_emails'], ['anna.nowak@example.com'])

    def test_legacy_csv_gets_persistent_ids(self):
        path = self.namespace['TASK_DATABASE_CSV']
        with path.open(newline='', encoding='utf-8-sig') as stream:
            row = next(csv.DictReader(stream))
        row.pop('id')
        with path.open('w', newline='', encoding='utf-8-sig') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(row))
            writer.writeheader()
            writer.writerow(row)
        migrated = self.load()[0]
        self.assertTrue(migrated['id'])
        self.assertEqual(self.load()[0]['id'], migrated['id'])
        self.edit({'responsible_emails': ['new@example.com']}, task_id=migrated['id'])
        self.assertEqual(self.load()[0]['responsible_emails'], ['new@example.com'])

    def test_invalid_edits_do_not_change_saved_or_session_tasks(self):
        original = copy.deepcopy(self.state.tasks)
        for updates in ({'responsible_emails': []}, {'responsible_emails': 'bad'}, {'responsible_emails': ['invalid-email']}, {'id': 'changed'}):
            self.edit(updates)
            self.assertFalse(self.state.board_save_result['ok'])
            self.assertEqual(self.state.tasks, original)
            self.assertEqual(self.load()[0]['responsible_emails'], ['first@example.com'])
        self.edit({'status': 'Completed'}, task_id='missing')
        self.assertFalse(self.state.board_save_result['ok'])

    def test_failed_write_preserves_csv_and_reports_error(self):
        original = self.namespace['TASK_DATABASE_CSV'].read_bytes()
        with patch.object(os, 'replace', side_effect=OSError('disk unavailable')):
            self.edit({'responsible_emails': ['new@example.com']})
        self.assertFalse(self.state.board_save_result['ok'])
        self.assertIn('disk unavailable', self.state.board_save_result['error'])
        self.assertEqual(self.namespace['TASK_DATABASE_CSV'].read_bytes(), original)
        self.assertEqual(self.state.tasks[0]['responsible_emails'], ['first@example.com'])
        self.assertEqual(len(list(Path(self.directory.name).iterdir())), 1)

    def test_replayed_component_event_does_not_overwrite_newer_data(self):
        self.edit({'status': 'Completed'}, event_id='one-event')
        tasks = self.load()
        tasks[0]['status'] = 'In Progress'
        self.namespace['write_tasks_to_csv'](tasks)
        self.edit({'status': 'Completed'}, event_id='one-event')
        self.assertEqual(self.load()[0]['status'], 'In Progress')

    def test_renaming_column_preserves_tasks_and_selected_filter(self):
        self.state.status_filter = ['Backlog / To Do', 'Completed']
        self.namespace['apply_column_rename']({
            'event_id': 'rename-1', 'status': 'Backlog / To Do', 'name': ' Ready   to start ',
        })
        self.assertTrue(self.state.board_save_result['ok'])
        self.assertEqual(self.load()[0]['status'], 'Ready to start')
        self.assertEqual(self.load()[0]['id'], 'ticket-a')
        self.assertEqual(self.load()[0]['responsible_emails'], ['first@example.com'])
        self.assertEqual(self.namespace['load_board_columns']()[0], 'Ready to start')
        self.assertNotIn('Backlog / To Do', self.namespace['load_board_columns']())
        self.assertEqual(self.state.updated_status_filter, ['Ready to start', 'Completed'])

    def test_renaming_empty_column_survives_fresh_load(self):
        original = self.namespace['TASK_DATABASE_CSV'].read_bytes()
        self.namespace['apply_column_rename']({
            'event_id': 'rename-empty', 'status': 'Rejected', 'name': 'Archived',
        })
        self.assertTrue(self.state.board_save_result['ok'])
        self.assertEqual(self.namespace['load_board_columns'](),
                         ['Backlog / To Do', 'In Progress', 'Completed', 'Archived'])
        self.assertEqual(self.namespace['TASK_DATABASE_CSV'].read_bytes(), original)

    def test_invalid_column_rename_does_not_modify_data(self):
        original = self.namespace['TASK_DATABASE_CSV'].read_bytes()
        for name in ['', '   ', 'In Progress']:
            self.namespace['apply_column_rename']({
                'event_id': uuid4().hex, 'status': 'Backlog / To Do', 'name': name,
            })
            self.assertFalse(self.state.board_save_result['ok'])
            self.assertEqual(self.namespace['TASK_DATABASE_CSV'].read_bytes(), original)
            self.assertFalse(self.namespace['BOARD_COLUMNS_JSON'].exists())

    def test_column_config_failure_restores_ticket_statuses(self):
        original = self.namespace['TASK_DATABASE_CSV'].read_bytes()
        def unavailable(columns):
            raise OSError('configuration directory unavailable')
        with patch.dict(self.namespace, write_board_columns=unavailable):
            self.namespace['apply_column_rename']({
                'event_id': 'failed-rename', 'status': 'Backlog / To Do', 'name': 'Ready',
            })
        self.assertFalse(self.state.board_save_result['ok'])
        self.assertEqual(self.namespace['TASK_DATABASE_CSV'].read_bytes(), original)
        self.assertEqual(self.state.tasks[0]['status'], 'Backlog / To Do')
        self.assertEqual(self.state.statuses[0], 'Backlog / To Do')

    def test_added_and_sidebar_renamed_columns_use_same_configuration(self):
        success, _ = self.namespace['add_value']('statuses', 'Review', 'Column')
        self.assertTrue(success)
        self.assertEqual(self.namespace['load_board_columns']()[-1], 'Review')
        names = self.state.statuses[:-1] + ['Review complete']
        success, _ = self.namespace['rename_values']('statuses', 'status', names, 'Column')
        self.assertTrue(success)
        self.assertEqual(self.namespace['load_board_columns']()[-1], 'Review complete')

    def test_column_reordering_preserves_ticket_status_and_saves_order(self):
        original = self.namespace['TASK_DATABASE_CSV'].read_bytes()
        success, _ = self.namespace['move_board_column']('Completed', 'Backlog / To Do', 'before')
        self.assertTrue(success)
        self.assertEqual(self.namespace['load_board_columns'](),
                         ['Completed', 'Backlog / To Do', 'In Progress', 'Rejected'])
        self.assertEqual(self.namespace['TASK_DATABASE_CSV'].read_bytes(), original)
        success, _ = self.namespace['move_board_column']('Completed', 'Rejected', 'after')
        self.assertTrue(success)
        self.assertEqual(self.namespace['load_board_columns']()[-1], 'Completed')
        self.assertEqual(self.namespace['TASK_DATABASE_CSV'].read_bytes(), original)

    def test_failed_reorder_keeps_existing_order(self):
        old = self.state.statuses.copy()
        with patch.object(os, 'replace', side_effect=OSError('disk unavailable')):
            success, _ = self.namespace['move_board_column']('Completed', 'Backlog / To Do', 'before')
        self.assertFalse(success)
        self.assertEqual(self.state.statuses, old)
        self.assertFalse(self.namespace['BOARD_COLUMNS_JSON'].exists())

    def test_add_column_event_persists_and_selects_new_column(self):
        self.state.status_filter = ['Completed']
        self.namespace['apply_column_action']({
            'event_id': 'add-review', 'action': 'add_column', 'name': 'Review',
        })
        self.assertTrue(self.state.board_save_result['ok'])
        self.assertEqual(self.namespace['load_board_columns']()[-1], 'Review')
        self.assertEqual(self.state.updated_status_filter, ['Completed', 'Review'])
        self.namespace['apply_column_action']({
            'event_id': 'duplicate-review', 'action': 'add_column', 'name': 'Review',
        })
        self.assertFalse(self.state.board_save_result['ok'])
        self.assertEqual(self.namespace['load_board_columns']().count('Review'), 1)

    def test_keyword_members_and_due_filters(self):
        matches = self.namespace['task_matches_filters']
        task = self.state.tasks[0]
        today = date(2026, 9, 30)
        self.assertTrue(matches(task, 'PARTS demo', ['first@example.com'], 'Due in the next day', today))
        self.assertFalse(matches(task, 'missing', today=today))
        self.assertFalse(matches(task, members=['other@example.com'], today=today))
        self.assertFalse(matches(task, due_filter='Overdue', today=today))
        self.assertTrue(matches(task, due_filter='Overdue', today=date(2026, 10, 2)))
        self.assertTrue(matches(task, due_filter='Due today', today=date(2026, 10, 1)))
        self.assertTrue(matches(task, due_filter='Due in the next week', today=date(2026, 9, 24)))
        self.assertFalse(matches(task, due_filter='Due in the next week', today=date(2026, 9, 23)))
        empty = task | {'due': '', 'responsible_emails': []}
        self.assertTrue(matches(empty, members=['No members'], due_filter='No date', today=today))
        self.assertFalse(matches(task | {'due': 'invalid'}, due_filter='Overdue', today=today))

    def test_clear_filters_restores_all_categories(self):
        self.state.project_ids = ['PRJ-001']
        self.state.filter_keyword = 'parts'
        self.state.filter_members = ['first@example.com']
        self.state.filter_due = 'Overdue'
        self.state.filter_projects = []
        self.state.status_filter = []
        self.namespace['reset_board_filters']()
        self.assertEqual(self.state.filter_keyword, '')
        self.assertEqual(self.state.filter_members, [])
        self.assertEqual(self.state.filter_due, 'Any date')
        self.assertEqual(self.state.filter_projects, ['PRJ-001'])
        self.assertEqual(self.state.status_filter, self.state.statuses)


if __name__ == '__main__':
    unittest.main()
