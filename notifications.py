"""Send new-task notifications after the ticket has been saved."""
import os
from pathlib import Path
import smtplib
import ssl
import tomllib
from email.message import EmailMessage
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def task_url(app_url: str, task_id: str) -> str:
    """Keep deployment paths/query options while linking to a stable ticket ID."""
    url = urlsplit(app_url.strip())
    if url.scheme not in {'http', 'https'} or not url.hostname or not task_id:
        raise ValueError('A valid application URL and task ID are required')
    query = [(key, value) for key, value in parse_qsl(url.query, keep_blank_values=True) if key != 'task']
    query.append(('task', task_id))
    return urlunsplit((url.scheme, url.netloc, url.path, urlencode(query), ''))


def smtp_settings() -> dict:
    path = Path(__file__).parent / '.streamlit' / 'secrets.toml'
    settings = tomllib.loads(path.read_text(encoding='utf-8')).get('smtp', {}) if path.exists() else {}
    settings = dict(settings)
    for name in ('host', 'port', 'username', 'password', 'from_email', 'security', 'app_url'):
        value = os.environ.get(f'PP_SMTP_{name.upper()}')
        if value is not None:
            settings[name] = value
    return settings


def send_new_task_notification(task: dict) -> dict[str, str]:
    try:
        settings = smtp_settings()
        if not settings.get('host') or not settings.get('from_email'):
            return {'status': 'not_configured', 'message': 'Task saved. Email was not sent: configure the SMTP sender in .streamlit/secrets.toml or PP_SMTP_* environment variables.'}
        if not settings.get('app_url'):
            return {'status': 'not_configured', 'message': 'Task saved. Email was not sent: configure smtp.app_url or PP_SMTP_APP_URL so the notification can link to the task.'}
        link = task_url(settings['app_url'], task.get('id', ''))
        security = settings.get('security', 'starttls')
        if security not in {'starttls', 'ssl', 'none'}:
            raise ValueError('Invalid SMTP security mode')
        port = int(settings.get('port', 465 if security == 'ssl' else 587))
        recipients = list(dict.fromkeys(task['responsible_emails']))
        message = EmailMessage()
        message['Subject'] = f"New task assigned: {task['title']}"
        message['From'] = settings['from_email']
        message['To'] = ', '.join(recipients)
        body = f"You have been assigned a new task.\n\nTask: {task['title']}\nStatus: {task['status']}\nDue date: {task['due']}\n\nDetails:\n{task['description']}\n"
        body += f"\nOpen task: {link}\n"
        message.set_content(body)
        context = ssl.create_default_context()
        options = {'host': settings['host'], 'port': port, 'timeout': 10}
        if security == 'ssl':
            options['context'] = context
        client = smtplib.SMTP_SSL if security == 'ssl' else smtplib.SMTP
        with client(**options) as smtp:
            if security == 'starttls':
                smtp.ehlo()
                smtp.starttls(context=context)
                smtp.ehlo()
            if settings.get('username'):
                smtp.login(settings['username'], settings.get('password', ''))
            refused = smtp.send_message(message, to_addrs=recipients)
        if refused:
            return {'status': 'partial', 'message': f"Task saved. The email server rejected {len(refused)} of {len(recipients)} recipients. Check the SMTP account and recipient addresses."}
        return {'status': 'sent', 'message': f'Email notification accepted by the mail server for {len(recipients)} responsible person(s).'}
    except (OSError, smtplib.SMTPException, ValueError, TypeError):
        # Do not expose credentials or server responses in the task UI.
        return {'status': 'failed', 'message': 'Task saved, but the email notification failed. Check the SMTP settings and mail server connection.'}
