from datetime import date
from html.parser import HTMLParser
import unittest

from board_calendar import build_calendar_html, build_calendar_overview_html, calendar_tasks, shift_month


class CalendarParser(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.day = None
        self.tasks = {}
        self.dates = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'td':
            self.day = attrs['data-date']
            self.dates.append(self.day)
        if tag == 'details':
            self.tasks[attrs['data-task-id']] = (self.day, attrs['class'])


class BoardCalendarTests(unittest.TestCase):
    def task(self, task_id, due, **changes):
        return dict(id=task_id, title=task_id, status='Ready', due=due, description='', responsible_emails=[]) | changes

    def test_due_placement_highlights_boundaries_and_multiple_tasks_per_day(self):
        tasks = [self.task('past', '2026-09-11'), self.task('today', '2026-09-12'),
                 self.task('soon', '2026-09-17'), self.task('later', '2026-09-18'),
                 self.task('same-date', '2026-09-12')]
        html = build_calendar_html(tasks, date(2026, 9, 1), date(2026, 9, 12))
        parser = CalendarParser(html)
        for task in tasks:
            self.assertEqual(parser.tasks[task['id']][0], task['due'])
        self.assertIn('overdue', parser.tasks['past'][1])
        self.assertIn('due-soon', parser.tasks['today'][1])
        self.assertIn('due-soon', parser.tasks['soon'][1])
        self.assertNotIn('due-soon', parser.tasks['later'][1])
        self.assertIn('aria-current="date"', html)

    def test_leap_day_adjacent_months_and_year_navigation(self):
        tasks = [self.task('leap', '2024-02-29'), self.task('adjacent', '2024-03-01')]
        parser = CalendarParser(build_calendar_html(tasks, date(2024, 2, 1), date(2024, 2, 1)))
        self.assertEqual(parser.tasks['leap'][0], '2024-02-29')
        self.assertEqual(parser.tasks['adjacent'][0], '2024-03-01')
        self.assertEqual(len(parser.dates) % 7, 0)
        self.assertEqual(shift_month(date(2026, 12, 15), 1), date(2027, 1, 1))
        self.assertEqual(shift_month(date(2026, 1, 1), -1), date(2025, 12, 1))

    def test_archived_tasks_excluded_and_invalid_dates_grouped_separately(self):
        tasks = [self.task('archived', '2026-09-12', archived=True), self.task('missing', ''),
                 self.task('bad', '2026-02-30'), self.task('valid', '2026-09-12')]
        grouped, undated = calendar_tasks(tasks)
        self.assertEqual([task['id'] for task in grouped[date(2026, 9, 12)]], ['valid'])
        self.assertEqual([task['id'] for task in undated], ['missing', 'bad'])
        parser = CalendarParser(build_calendar_html(tasks, date(2026, 9, 1)))
        self.assertEqual(list(parser.tasks), ['valid'])

    def test_ticket_content_is_escaped(self):
        html = build_calendar_html([self.task('unsafe', '2026-09-12', title='<script>alert(1)</script>',
                                             description='<img src=x onerror=alert(1)>', status='A & B')], date(2026, 9, 1))
        self.assertNotIn('<script>', html)
        self.assertNotIn('<img ', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertIn('A &amp; B', html)

    def test_three_month_overview_crosses_year_and_does_not_duplicate_boundary_tasks(self):
        tasks = [self.task('december', '2026-12-31'), self.task('january', '2027-01-01'),
                 self.task('february', '2027-02-01'), self.task('outside', '2027-03-01')]
        html = build_calendar_overview_html(tasks, date(2026, 12, 1), date(2027, 1, 1))
        self.assertEqual(html.count('<table>'), 3)
        for month in ['December 2026', 'January 2027', 'February 2027']:
            self.assertIn(f'<caption>{month}</caption>', html)
        parser = CalendarParser(html)
        for task in tasks[:3]:
            self.assertEqual(html.count(f'data-task-id="{task["id"]}"'), 1)
            self.assertEqual(parser.tasks[task['id']][0], task['due'])
        self.assertNotIn('outside', parser.tasks)
        self.assertIn('overdue', parser.tasks['december'][1])


if __name__ == '__main__':
    unittest.main()
