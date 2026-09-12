from datetime import date, timedelta
import unittest

from board_statistics import calculate_statistics, chart_spec


class BoardStatisticsTests(unittest.TestCase):
    def task(self, **changes):
        return dict(status='Ready', due='', responsible_emails=[], labels=[]) | changes

    def test_due_buckets_cover_boundaries_invalid_dates_and_all_selected_columns(self):
        today = date(2026, 9, 12)
        tasks = [self.task(due=(today + timedelta(days=days)).isoformat()) for days in [-1, 0, 1, 5, 6]]
        tasks += [self.task(due=value) for value in ['', 'invalid', None]]
        stats = calculate_statistics(tasks, ['Ready', 'Empty'], [], today)
        self.assertEqual(stats['total'], 8)
        self.assertEqual([row['tasks'] for row in stats['due']], [1, 1, 2, 1, 3])
        self.assertEqual(stats['columns'], [{'name': 'Ready', 'tasks': 8}, {'name': 'Empty', 'tasks': 0}])

    def test_shared_assignments_and_labels_count_once_per_category(self):
        labels = [{'id': 'urgent', 'name': 'Urgent', 'color': '#ff0000'}, {'id': 'quality', 'name': 'Quality', 'color': '#00ff00'}]
        tasks = [self.task(responsible_emails=['Anna@example.com', 'anna@example.com', 'bob@example.com'], labels=['urgent', 'urgent', 'quality']),
                 self.task(responsible_emails='bob@example.com, carol@example.com', labels=['unknown']), self.task()]
        stats = calculate_statistics(tasks, ['Ready'], labels)
        self.assertEqual(stats['total'], 3)
        self.assertEqual(stats['assigned'], 2)
        self.assertEqual(stats['labelled'], 1)
        self.assertEqual({row['name']: row['tasks'] for row in stats['members']}, {'anna@example.com': 1, 'bob@example.com': 2, 'carol@example.com': 1, 'Unassigned': 1})
        self.assertEqual({row['name']: row['tasks'] for row in stats['labels']}, {'Urgent': 1, 'Quality': 1, 'No labels': 2})

    def test_archived_and_unselected_columns_are_excluded_without_modifying_tasks(self):
        tasks = [self.task(), self.task(archived=True), self.task(status='Archived column'), self.task(status='Filtered column')]
        original = [task.copy() for task in tasks]
        stats = calculate_statistics(tasks, ['Ready'], [])
        self.assertEqual(stats['total'], 1)
        self.assertEqual(tasks, original)
        empty = calculate_statistics(tasks, [], [])
        self.assertEqual(empty['total'], 0)
        self.assertEqual(empty['members'], [])
        self.assertEqual(empty['labels'], [])

    def test_chart_specs_validate_with_installed_vega_lite_schema(self):
        import altair as alt

        stats = calculate_statistics([self.task()], ['Ready'], [])
        for category in ['columns', 'due', 'members', 'labels']:
            spec = chart_spec(stats[category], donut=category == 'due')
            alt.Chart.from_dict(spec, validate=True)


if __name__ == '__main__':
    unittest.main()
