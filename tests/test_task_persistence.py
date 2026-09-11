"""Exercise the app's CSV save boundary without starting its Streamlit UI."""
import ast
import base64
import mimetypes
from urllib.parse import urlsplit, quote
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
            base64=base64, mimetypes=mimetypes, urlsplit=urlsplit, quote=quote,
            send_new_task_notification=lambda task: {"status": "sent", "message": "Accepted by test mail server"},
            ATTACHMENTS_DIR=Path(self.directory.name) / "attachments",
            csv=csv, json=json, os=os, re=re, tempfile=tempfile, Path=Path, uuid4=uuid4, date=date,
            st=SimpleNamespace(session_state=self.state),
            TASK_DATABASE_CSV=Path(self.directory.name) / 'tasks.csv',
            BOARD_LABELS_JSON=Path(self.directory.name) / 'labels.json',
            BOARD_COLUMNS_JSON=Path(self.directory.name) / 'columns.json',
        )
        source = Path(__file__).resolve().parents[1] / 'app.py'
        tree = ast.parse(source.read_text(encoding='utf-8-sig'))
        functions = {
            'save_uploaded_files', 'cleanup_uploaded_files', 'safe_storage_name', 'unique_file_path',
            'clean_attachment_link', 'local_folder_uri', 'upload_payload', 'attachment_link_items', 'add_task', 'apply_new_task',
            'merge_board_labels', 'load_board_labels', 'write_board_labels',
            'csv_json_list', 'task_from_csv_row', 'task_to_csv_row',
            'responsible_emails_list', 'load_tasks_from_csv',
            'write_tasks_to_csv', 'save_tasks_to_csv', 'apply_board_edit',
            'normalize_email', 'clean_responsible_emails', 'normalize_name',
            'load_board_columns', 'write_board_columns', 'rename_board_columns',
            'apply_column_rename', 'rename_values', 'add_value',
            'move_board_column', 'apply_column_action', 'task_matches_filters', 'reset_board_filters',
        }
        constants = {'MAX_ATTACHMENT_BYTES', 'TASK_CSV_FIELDS', 'DEFAULT_STATUSES', 'DEFAULT_PROJECT_IDS'}
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

    def test_stale_session_add_preserves_columns_saved_by_another_session(self):
        old_snapshot = self.state.statuses.copy()
        self.namespace['add_value']('statuses', 'First new', 'Column')
        self.state.statuses = old_snapshot
        success, message = self.namespace['add_value']('statuses', 'Second new', 'Column')
        self.assertTrue(success, message)
        self.assertEqual(self.namespace['load_board_columns'](), old_snapshot + ['First new', 'Second new'])
        self.assertEqual(self.state.statuses, self.namespace['load_board_columns']())

    def test_stale_session_cannot_duplicate_a_saved_column(self):
        old_snapshot = self.state.statuses.copy()
        self.namespace['add_value']('statuses', 'Shared column', 'Column')
        self.state.statuses = old_snapshot
        before = self.namespace['BOARD_COLUMNS_JSON'].read_bytes()
        success, _ = self.namespace['add_value']('statuses', 'Shared column', 'Column')
        self.assertFalse(success)
        self.assertEqual(self.namespace['BOARD_COLUMNS_JSON'].read_bytes(), before)

    def test_stale_rename_and_reorder_retain_later_column_additions(self):
        old_snapshot = self.state.statuses.copy()
        self.namespace['add_value']('statuses', 'Shared column', 'Column')
        self.state.statuses = old_snapshot.copy()
        success, message = self.namespace['rename_board_columns'](['Ready', *old_snapshot[1:]])
        self.assertTrue(success, message)
        self.assertEqual(self.namespace['load_board_columns'](), ['Ready', *old_snapshot[1:], 'Shared column'])
        self.state.statuses = ['Ready', *old_snapshot[1:]]
        success, message = self.namespace['move_board_column']('Completed', 'Ready', 'before')
        self.assertTrue(success, message)
        self.assertIn('Shared column', self.namespace['load_board_columns']())

    def test_pending_filter_updates_accumulate_consecutive_additions(self):
        self.state.status_filter = ['Completed']
        self.namespace['add_value']('statuses', 'First new', 'Column')
        self.namespace['add_value']('statuses', 'Second new', 'Column')
        self.assertEqual(self.state.updated_status_filter, ['Completed', 'First new', 'Second new'])

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

    def test_labels_save_and_reload_without_changing_project(self):
        label = dict(id='urgent', name='Urgent', color='#f87168')
        self.namespace['apply_board_edit'](dict(
            event_id='label-save', task_id='ticket-a',
            updates={'labels': ['urgent', 'urgent'], 'title': 'Updated'}, label_changes=[label],
        ))
        self.assertTrue(self.state.board_save_result['ok'])
        saved = self.namespace['load_tasks_from_csv']()[0]
        self.assertEqual(saved['labels'], ['urgent'])
        self.assertEqual(saved['project_id'], 'PRJ-001')
        self.assertEqual(saved['project'], 'Demo')
        self.assertEqual(self.namespace['load_board_labels'](), [label])
        self.edit({'labels': []})
        self.assertEqual(self.namespace['load_tasks_from_csv']()[0]['labels'], [])
        self.assertEqual(self.namespace['load_board_labels'](), [label])

    def test_shared_label_edit_preserves_assignments_and_other_labels(self):
        self.namespace['write_board_labels']([
            dict(id='urgent', name='Urgent', color='#f87168'),
            dict(id='review', name='Review', color='#4bce97'),
        ])
        self.state.tasks[0]['labels'] = ['urgent']
        self.state.tasks.append(self.state.tasks[0] | {'id': 'ticket-b'})
        self.namespace['save_tasks_to_csv']()
        self.namespace['apply_board_edit'](dict(
            event_id='rename-label', task_id='ticket-a', updates={'labels': ['urgent']},
            label_changes=[dict(id='urgent', name='Priority', color='#F5CD47')],
        ))
        self.assertTrue(self.state.board_save_result['ok'])
        self.assertEqual([t['labels'] for t in self.namespace['load_tasks_from_csv']()], [['urgent'], ['urgent']])
        catalog = self.namespace['load_board_labels']()
        self.assertEqual(catalog[0], dict(id='urgent', name='Priority', color='#f5cd47'))
        self.assertEqual(catalog[1]['name'], 'Review')

    def test_invalid_labels_leave_saved_data_unchanged(self):
        original = self.namespace['TASK_DATABASE_CSV'].read_bytes()
        cases = [
            ({'labels': ['missing']}, []),
            ({'labels': [123]}, []),
            ({'labels': []}, [dict(id='x', name='', color='#4bce97')]),
            ({'labels': []}, [dict(id='x', name='Review', color='red')]),
            ({'labels': []}, [dict(id='x', name='Review', color='#4bce97'), dict(id='y', name=' review ', color='#4bce97')]),
            ({'labels': []}, 'invalid'),
        ]
        for index, (updates, changes) in enumerate(cases):
            with self.subTest(index=index):
                self.namespace['apply_board_edit'](dict(event_id=str(index), task_id='ticket-a', updates=updates, label_changes=changes))
                self.assertFalse(self.state.board_save_result['ok'])
                self.assertEqual(self.namespace['TASK_DATABASE_CSV'].read_bytes(), original)
                self.assertFalse(self.namespace['BOARD_LABELS_JSON'].exists())

    def test_label_file_failure_prevents_ticket_changes(self):
        original = self.namespace['TASK_DATABASE_CSV'].read_bytes()
        with patch.dict(self.namespace, write_board_labels=lambda labels: (_ for _ in ()).throw(OSError('Disk full'))):
            self.namespace['apply_board_edit'](dict(
                event_id='fail-label', task_id='ticket-a', updates={'labels': ['x']},
                label_changes=[dict(id='x', name='Review', color='#4bce97')],
            ))
        self.assertFalse(self.state.board_save_result['ok'])
        self.assertEqual(self.namespace['TASK_DATABASE_CSV'].read_bytes(), original)

    def test_ticket_failure_rolls_back_label_changes(self):
        previous = [dict(id='x', name='Review', color='#4bce97')]
        self.namespace['write_board_labels'](previous)
        with patch.dict(self.namespace, write_tasks_to_csv=lambda tasks: (_ for _ in ()).throw(OSError('Disk full'))):
            self.namespace['apply_board_edit'](dict(
                event_id='fail-ticket', task_id='ticket-a', updates={'labels': ['x']},
                label_changes=[dict(id='x', name='Ready', color='#f87168')],
            ))
        self.assertFalse(self.state.board_save_result['ok'])
        self.assertEqual(self.namespace['load_board_labels'](), previous)

    def test_uploaded_file_bytes_and_link_survive_reload(self):
        contents = b'Hello file!\x00\xff'
        event = dict(event_id='upload', task_id='ticket-a',
                     updates={'attachments': ['https://example.com/spec?version=2']},
                     uploaded_files=[{'name': 'spec.txt', 'data': base64.b64encode(contents).decode()}])
        self.namespace['apply_board_edit'](event)
        self.assertTrue(self.state.board_save_result['ok'])
        attachments = self.namespace['load_tasks_from_csv']()[0]['attachments']
        self.assertEqual(attachments[0], 'https://example.com/spec?version=2')
        self.assertEqual((Path(self.directory.name) / attachments[1]).read_bytes(), contents)
        items = self.namespace['attachment_link_items'](attachments)
        self.assertEqual(items[0]['href'], attachments[0])
        self.assertEqual(items[1]['name'], 'spec.txt')
        self.assertEqual(base64.b64decode(items[1]['href'].split(',', 1)[1]), contents)
        self.assertTrue(items[1]['preview'])
        self.namespace['apply_board_edit'](event)
        self.assertEqual(len(list(self.namespace['ATTACHMENTS_DIR'].rglob('*.txt'))), 1)

    def test_same_name_uploads_do_not_overwrite_and_names_stay_in_storage(self):
        upload = lambda name, data: dict(name=name, data=base64.b64encode(data).decode())
        references = self.namespace['save_uploaded_files']('ticket-a', [
            upload('report.txt', b'first'), upload('report.txt', b'second'), upload('../../outside.txt', b'third')])
        self.assertEqual(len(set(references)), 3)
        root = self.namespace['ATTACHMENTS_DIR'].resolve()
        for reference, expected in zip(references, [b'first', b'second', b'third']):
            path = (Path(self.directory.name) / reference).resolve()
            self.assertTrue(path.is_relative_to(root))
            self.assertEqual(path.read_bytes(), expected)

    def test_invalid_upload_or_local_link_does_not_change_ticket(self):
        before = self.namespace['TASK_DATABASE_CSV'].read_bytes()
        for index, (updates, uploads) in enumerate([
            ({'attachments': ['javascript:alert(1)']}, []),
            ({'attachments': ['relative/path']}, []),
            ({'attachments': []}, [{'name': 'test.txt', 'data': 'not base64!'}]),
            ({'attachments': []}, [{'name': '', 'data': ''}]),
            ({'attachments': []}, 'invalid'),
        ]):
            with self.subTest(index=index):
                self.namespace['apply_board_edit'](dict(event_id=f'bad-upload-{index}', task_id='ticket-a', updates=updates, uploaded_files=uploads))
                self.assertFalse(self.state.board_save_result['ok'])
                self.assertEqual(self.namespace['TASK_DATABASE_CSV'].read_bytes(), before)
        self.assertFalse(self.namespace['ATTACHMENTS_DIR'].exists())

    def test_upload_total_size_limit_rejects_before_writing(self):
        with patch.dict(self.namespace, MAX_ATTACHMENT_BYTES=3):
            with self.assertRaises(ValueError):
                self.namespace['save_uploaded_files']('ticket-a', [
                    dict(name='a', data=base64.b64encode(b'12').decode()),
                    dict(name='b', data=base64.b64encode(b'34').decode()),
                ])
        self.assertFalse(self.namespace['ATTACHMENTS_DIR'].exists())

    def test_file_cleanup_after_ticket_save_failure(self):
        before = self.namespace['TASK_DATABASE_CSV'].read_bytes()
        with patch.dict(self.namespace, write_tasks_to_csv=lambda tasks: (_ for _ in ()).throw(OSError('Disk full'))):
            self.namespace['apply_board_edit'](dict(
                event_id='failed-upload', task_id='ticket-a', updates={'attachments': []},
                uploaded_files=[dict(name='test.txt', data=base64.b64encode(b'hello').decode())],
            ))
        self.assertFalse(self.state.board_save_result['ok'])
        self.assertEqual(self.namespace['TASK_DATABASE_CSV'].read_bytes(), before)
        self.assertFalse(any(path.is_file() for path in self.namespace['ATTACHMENTS_DIR'].rglob('*')))

    def test_new_task_upload_saves_contents_and_link(self):
        success, message = self.namespace['add_task'](
            'New task', 'PRJ-001', 'Demo', ['person@example.com'], 'Backlog / To Do',
            '2026-10-01', 'Details', ['https://example.com/file'],
            uploaded_files=[dict(name='new.txt', data=base64.b64encode(b'new file').decode())],
        )
        self.assertTrue(success, message)
        saved = self.namespace['load_tasks_from_csv']()[-1]
        self.assertEqual(saved['attachments'][0], 'https://example.com/file')
        self.assertEqual((Path(self.directory.name) / saved['attachments'][1]).read_bytes(), b'new file')

    def test_missing_and_outside_files_are_not_exposed(self):
        private = Path(self.directory.name) / 'private.txt'
        private.write_text('private')
        items = self.namespace['attachment_link_items']([str(private), 'missing.txt', r'C:\test.txt'])
        self.assertTrue(all(not item['href'].startswith('data:') for item in items))
        self.state.tasks[0]['attachments'] = ['missing.txt']
        self.namespace['save_tasks_to_csv']()
        self.edit({'attachments': ['missing.txt'], 'title': 'Still editable'})
        self.assertTrue(self.state.board_save_result['ok'])
        self.edit({'attachments': []})
        self.assertEqual(self.namespace['load_tasks_from_csv']()[0]['attachments'], [])

    def test_local_folder_references_save_and_render_without_reading_them(self):
        paths = [r'C:\Program Files', r'\\server\shared folder', '/srv/shared folder', 'file:///C:/Documents']
        self.edit({'attachments': paths})
        self.assertTrue(self.state.board_save_result['ok'])
        items = self.namespace['attachment_link_items'](self.namespace['load_tasks_from_csv']()[0]['attachments'])
        self.assertEqual(items[0]['href'], 'file:///C:/Program%20Files')
        self.assertEqual(items[1]['href'], 'file://server/shared%20folder')
        self.assertTrue(all(item['kind'] == 'folder' for item in items))
        self.assertEqual([item['reference'] for item in items], paths)

    def test_label_filters_match_any_selected_label_and_unlabelled_tasks(self):
        matches = self.namespace['task_matches_filters']
        task = self.state.tasks[0] | {'labels': ['urgent']}
        self.assertTrue(matches(task, labels=[]))
        self.assertTrue(matches(task, labels=['urgent', 'review']))
        self.assertFalse(matches(task, labels=['review']))
        self.assertFalse(matches(task, labels=['__no_labels__']))
        self.assertTrue(matches(self.state.tasks[0], labels=['__no_labels__']))
        self.assertTrue(matches(task, labels=['__no_labels__', 'urgent']))

    def test_new_task_notifies_only_after_save_and_records_sending_failure(self):
        def notify(task):
            self.assertIn(task['id'], [saved['id'] for saved in self.namespace['load_tasks_from_csv']()])
            return {'status': 'failed', 'message': 'Mail server unavailable'}
        with patch.dict(self.namespace, send_new_task_notification=notify):
            success, message = self.namespace['add_task']('Notification task', 'PRJ-001', 'Demo', ['person@example.com'], 'Backlog / To Do', '2026-10-01', 'Details', [])
        self.assertTrue(success, message)
        self.assertEqual(self.namespace['load_tasks_from_csv']()[-1]['email_notification_status'], 'failed')
        self.assertFalse(self.namespace['load_tasks_from_csv']()[-1]['email_notification'])
        self.assertEqual(self.state.last_notification_result['status'], 'failed')

    def new_task_event(self, **updates):
        return dict(event_id='create-event', action='create_task', updates=dict(
            title='New shared-form task', responsible_emails=['new@example.com'],
            status='In Progress', due='2026-10-01', description='Details', attachments=[], labels=[],
        ) | updates)

    def test_shared_form_creates_without_project_fields_with_labels_and_file(self):
        event = self.new_task_event(labels=['review'], attachments=['https://example.com/file'])
        event['label_changes'] = [dict(id='review', name='Review', color='#4bce97')]
        event['uploaded_files'] = [dict(name='review.txt', data=base64.b64encode(b'Review file').decode())]
        self.namespace['apply_new_task'](event)
        self.assertTrue(self.state.board_save_result['ok'])
        task = self.namespace['load_tasks_from_csv']()[-1]
        self.assertEqual(task['project_id'], '')
        self.assertEqual(task['project'], '')
        self.assertEqual(task['status'], 'In Progress')
        self.assertEqual(task['labels'], ['review'])
        self.assertEqual(task['email_notification_status'], 'sent')
        self.assertEqual((Path(self.directory.name) / task['attachments'][1]).read_bytes(), b'Review file')
        self.assertTrue(self.state.show_task_created_notice)
        self.namespace['apply_new_task'](event)
        self.assertEqual(len(self.namespace['load_tasks_from_csv']()), 2)
        self.edit({'title': 'Edited shared-form task'}, task_id=task['id'])
        self.assertTrue(self.state.board_save_result['ok'])
        self.assertEqual(self.namespace['load_tasks_from_csv']()[-1]['title'], 'Edited shared-form task')

    def test_invalid_shared_form_create_never_sends_email_or_writes_ticket(self):
        original = self.namespace['TASK_DATABASE_CSV'].read_bytes()
        cases = [dict(title=''), dict(responsible_emails=[]), dict(status='Missing'), dict(labels=['missing']), dict(due='invalid'), dict(project_id='PRJ-002')]
        for index, updates in enumerate(cases):
            with self.subTest(index=index), patch.dict(self.namespace, send_new_task_notification=lambda task: self.fail('Unexpected email')):
                self.namespace['apply_new_task'](self.new_task_event(**updates) | {'event_id': f'invalid-{index}'})
                self.assertFalse(self.state.board_save_result['ok'])
                self.assertEqual(self.namespace['TASK_DATABASE_CSV'].read_bytes(), original)

    def test_failed_creation_rolls_back_labels_uploads_and_skips_email(self):
        original = self.namespace['TASK_DATABASE_CSV'].read_bytes()
        event = self.new_task_event(labels=['review'])
        event['label_changes'] = [dict(id='review', name='Review', color='#4bce97')]
        event['uploaded_files'] = [dict(name='review.txt', data=base64.b64encode(b'Review file').decode())]
        with patch.dict(self.namespace,
                        write_tasks_to_csv=lambda tasks: (_ for _ in ()).throw(OSError('Disk full')),
                        send_new_task_notification=lambda task: self.fail('Unexpected email')):
            self.namespace['apply_new_task'](event)
        self.assertFalse(self.state.board_save_result['ok'])
        self.assertEqual(self.namespace['TASK_DATABASE_CSV'].read_bytes(), original)
        self.assertEqual(self.namespace['load_board_labels'](), [])
        self.assertFalse(any(path.is_file() for path in self.namespace['ATTACHMENTS_DIR'].rglob('*')))

    def test_clear_filters_restores_all_categories(self):
        self.state.project_ids = ['PRJ-001']
        self.state.filter_keyword = 'parts'
        self.state.filter_members = ['first@example.com']
        self.state.filter_due = 'Overdue'
        self.state.filter_labels = ['urgent']
        self.state.status_filter = []
        self.namespace['reset_board_filters']()
        self.assertEqual(self.state.filter_keyword, '')
        self.assertEqual(self.state.filter_members, [])
        self.assertEqual(self.state.filter_due, 'Any date')
        self.assertEqual(self.state.filter_labels, [])
        self.assertEqual(self.state.status_filter, self.state.statuses)


if __name__ == '__main__':
    unittest.main()
