"""Exercise the app's CSV save boundary without starting its Streamlit UI."""
import ast
import copy
import csv
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import uuid4


class State(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__


class TaskPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.state = State()
        self.namespace = dict(
            csv=csv, json=json, os=os, tempfile=tempfile, Path=Path, uuid4=uuid4,
            st=SimpleNamespace(session_state=self.state),
            TASK_DATABASE_CSV=Path(self.directory.name) / 'tasks.csv',
        )
        source = Path(__file__).resolve().parents[1] / 'app.py'
        tree = ast.parse(source.read_text(encoding='utf-8-sig'))
        functions = {
            'csv_json_list', 'task_from_csv_row', 'task_to_csv_row',
            'responsible_emails_list', 'load_tasks_from_csv',
            'write_tasks_to_csv', 'save_tasks_to_csv', 'apply_board_edit',
        }
        constants = {'TASK_CSV_FIELDS', 'DEFAULT_STATUSES', 'DEFAULT_PEOPLE', 'DEFAULT_PROJECT_IDS'}
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
        for updates in ({'responsible_emails': []}, {'responsible_emails': 'bad'}, {'id': 'changed'}):
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


if __name__ == '__main__':
    unittest.main()
