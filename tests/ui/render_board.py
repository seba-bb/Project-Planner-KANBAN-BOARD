"""Render a test board without importing Streamlit or opening live application data."""
import ast
import json
from datetime import date
from pathlib import Path
from types import SimpleNamespace

source = Path(__file__).resolve().parents[2] / 'app.py'
tree = ast.parse(source.read_text(encoding='utf-8-sig'))
functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in {'build_board_html', 'sort_column_tasks', 'responsible_emails_list'}]
namespace = dict(json=json, date=date, load_column_settings=lambda: {}, st=SimpleNamespace(session_state=SimpleNamespace(users=[])),
                 load_board_labels=lambda: [], attachment_link_items=lambda items: [])
exec(compile(ast.Module(body=functions, type_ignores=[]), str(source), 'exec'), namespace)
print(namespace['build_board_html'](['Backlog / To Do', 'In Progress'], []))
