const {JSDOM} = require('jsdom');
const fs = require('node:fs');
const assert = require('node:assert/strict');
let template = fs.readFileSync(0, 'utf8');
const data = JSON.parse(template.match(/const data = (.*);\n/)[1]);
const [source, destination] = data.statuses;
data.statuses.push('Empty');
data.tasks = ['a', 'b', 'c', 'd'].map((id, i) => ({
  id, title: `Task ${id}`, status: i === 0 ? source : destination, due: '',
  responsible_emails: [], labels: [], description: '', attachments: [], attachment_links: [],
}));
template = template.replace(/const data = .*;\n/, () => `const data = ${JSON.stringify(data)};\n`);
const messages = [];
const dom = new JSDOM(template, {runScripts: 'dangerously', url: 'http://localhost', beforeParse(w) {
  w.postMessage = message => messages.push(message);
}});
const w = dom.window, d = w.document;
const [first, second, empty] = d.querySelectorAll('.dropzone');
const card = d.getElementById('a');
const transfer = {setData() {}, getData() { return 'a'; }};
const drag = (element, type, y = 0, relatedTarget = null) => {
  const event = new w.Event(type, {bubbles: true, cancelable: true});
  Object.assign(event, {dataTransfer: transfer, clientY: y, relatedTarget});
  element.dispatchEvent(event);
  return event;
};
const gap = () => d.querySelector('.task-drop-gap');
const ackFailure = () => w.dispatchEvent(new w.MessageEvent('message', {source: w, data: {
  type: 'planner:save-result', result: {event_id: messages.at(-1).value.event_id, ok: false, error: 'Disk full'},
}}));
try {
  // Model laid-out cards: each card is 100px high with 9px bottom spacing.
  for (const zone of [first, second, empty]) {
    zone.querySelectorAll('.task-card').forEach((item, i) => {
      item.getBoundingClientRect = () => ({top: 100 + i * 109, height: 100});
    });
  }
  drag(second, 'dragover', 200);
  assert.equal(gap(), null, 'external drags must not create a task placeholder');
  drag(card, 'dragstart');
  assert(card.classList.contains('task-dragging'));
  assert.equal(drag(second, 'dragover', 90).defaultPrevented, true);
  assert.equal(gap().nextElementSibling.id, 'b', 'top insertion');
  assert.equal(w.getComputedStyle(gap()).flexBasis, '18px');
  for (let i = 0; i < 5; i++) {
    drag(d.getElementById('b'), 'dragover', 200);
    assert.equal(gap().previousElementSibling.id, 'b');
    assert.equal(gap().nextElementSibling.id, 'c', 'stable gap between neighboring cards');
    assert.equal(d.querySelectorAll('.task-drop-gap').length, 1);
  }
  drag(second, 'dragleave', 200, d.getElementById('c'));
  assert(gap(), 'moving over a child keeps the gap');
  drag(second, 'dragover', 900);
  assert.equal(gap().previousElementSibling.id, 'd');
  assert(gap().nextElementSibling.classList.contains('column-add-task'), 'bottom gap is above Add task');
  drag(empty, 'dragover', 100);
  assert.equal(gap().parentElement, empty);
  assert.equal(second.classList.contains('drag-over'), false);
  drag(d.querySelector('.column-header'), 'dragover');
  assert.equal(gap(), null, 'leaving task zones clears the gap');
  drag(first, 'dragover', 100);
  assert(gap().nextElementSibling.classList.contains('column-add-task'), 'dragged card is excluded');
  drag(card, 'dragend');
  assert.equal(gap(), null);
  assert.equal(card.classList.contains('task-dragging'), false);
  assert.equal(messages.length, 0, 'cancel does not save');
  for (const [zone, y, anchor, status] of [[second, 200, 'c', destination], [second, 900, null, destination], [empty, 100, null, 'Empty']]) {
    drag(card, 'dragstart');
    drag(zone, 'dragover', y);
    drag(zone, 'drop', y);
    assert.equal(gap(), null);
    assert.equal(messages.at(-1).value.before_task_id, anchor);
    assert.equal(messages.at(-1).value.updates.status, status);
    assert.equal(messages.at(-1).value.task_id, 'a');
    assert.equal(drag(card, 'dragstart').defaultPrevented, true, 'block a second move while saving');
    ackFailure();
    assert.match(d.getElementById('save-error').textContent, /Disk full/);
    assert.equal(card.parentElement, first, 'failed saves keep the original position');
  }
  console.log('PASS: small insertion gap at top/middle/bottom/empty columns, stable child hover, cancel cleanup, exact drop payload, pending-save guard and failed-save recovery.');
} finally { w.close(); }
