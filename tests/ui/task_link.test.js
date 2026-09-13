const {JSDOM} = require('jsdom');
const fs = require('node:fs');
const assert = require('node:assert/strict');
const template = fs.readFileSync(0, 'utf8');
const data = JSON.parse(template.match(/const data = (.*);\n/)[1]);
data.tasks = [{id: 'linked-task', title: 'Review drawing', status: data.statuses[0],
  due: '2026-10-01', description: 'Check dimensions', responsible_emails: ['owner@example.com'],
  labels: [], attachments: [], attachment_links: []}];
for (const taskId of ['linked-task', null, 'missing-task']) {
  data.open_task_id = taskId;
  const html = template.replace(/const data = .*;\n/, () => `const data = ${JSON.stringify(data)};\n`);
  const messages = [];
  const dom = new JSDOM(html, {runScripts: 'dangerously', url: 'http://localhost', beforeParse(w) {
    w.postMessage = message => messages.push(message);
    w.CSS = {escape: value => value};
  }});
  try {
    const d = dom.window.document;
    assert.equal(d.getElementById('edit-modal').classList.contains('open'), taskId === 'linked-task');
    if (taskId === 'linked-task') {
      assert.equal(d.getElementById('edit-title').value, 'Review drawing');
      assert.equal(d.getElementById('edit-description').value, 'Check dimensions');
      d.getElementById('edit-cancel').click();
      assert.equal(d.getElementById('edit-modal').classList.contains('open'), false);
    }
    assert.equal(messages.length, 0, 'opening a link must not save or send notifications');
  } finally {
    dom.window.close();
  }
}
console.log('Task link UI tests passed');
