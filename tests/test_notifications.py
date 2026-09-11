import smtplib
import unittest
from unittest.mock import patch

import notifications


class NotificationTests(unittest.TestCase):
    def setUp(self):
        self.task = dict(title='Review drawing', status='Backlog / To Do', due='2026-10-01', description='Review the dimensions.', responsible_emails=['first@example.com', 'second@example.com'])
        self.settings = dict(host='smtp.example.com', from_email='planner@example.com', username='planner', password='test-only', security='starttls', port=587)

    def test_sends_to_all_assignees_over_tls(self):
        with patch.object(notifications, 'smtp_settings', return_value=self.settings), patch.object(notifications.smtplib, 'SMTP') as factory:
            client = factory.return_value.__enter__.return_value
            client.send_message.return_value = {}
            result = notifications.send_new_task_notification(self.task)
        self.assertEqual(result['status'], 'sent')
        client.starttls.assert_called_once()
        client.login.assert_called_once_with('planner', 'test-only')
        message = client.send_message.call_args.args[0]
        self.assertIn('Review drawing', message['Subject'])
        self.assertIn('2026-10-01', message.get_content())
        self.assertEqual(client.send_message.call_args.kwargs['to_addrs'], self.task['responsible_emails'])

    def test_missing_configuration_does_not_attempt_delivery(self):
        with patch.object(notifications, 'smtp_settings', return_value={}), patch.object(notifications.smtplib, 'SMTP') as smtp:
            result = notifications.send_new_task_notification(self.task)
        self.assertEqual(result['status'], 'not_configured')
        smtp.assert_not_called()

    def test_failed_delivery_reports_failure_without_exposing_server_response(self):
        with patch.object(notifications, 'smtp_settings', return_value=self.settings), patch.object(notifications.smtplib, 'SMTP', side_effect=smtplib.SMTPAuthenticationError(535, b'sensitive response')):
            result = notifications.send_new_task_notification(self.task)
        self.assertEqual(result['status'], 'failed')
        self.assertNotIn('sensitive response', result['message'])

    def test_partial_refusal_is_not_reported_as_sent_to_everyone(self):
        with patch.object(notifications, 'smtp_settings', return_value=self.settings), patch.object(notifications.smtplib, 'SMTP') as factory:
            factory.return_value.__enter__.return_value.send_message.return_value = {'second@example.com': (550, b'Refused')}
            result = notifications.send_new_task_notification(self.task)
        self.assertEqual(result['status'], 'partial')

    def test_ssl_and_relay_without_login(self):
        with patch.object(notifications, 'smtp_settings', return_value=dict(host='smtp.example.com', from_email='planner@example.com', security='ssl')), patch.object(notifications.smtplib, 'SMTP_SSL') as factory:
            client = factory.return_value.__enter__.return_value
            client.send_message.return_value = {}
            result = notifications.send_new_task_notification(self.task)
        self.assertEqual(result['status'], 'sent')
        self.assertEqual(factory.call_args.kwargs['port'], 465)
        client.login.assert_not_called()
        client.starttls.assert_not_called()


if __name__ == '__main__':
    unittest.main()
