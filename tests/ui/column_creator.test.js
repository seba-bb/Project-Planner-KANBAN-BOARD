// Run with npm install --prefix tests/ui && npm test --prefix tests/ui.
// Python rendering uses the application's VENV and never reads the live task database.
const {JSDOM} = require('jsdom');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '../..');
const template = fs.readFileSync(0, 'utf8');
const payload = JSON.parse(template.match(/const data = (.*);\n/)[1]);
const html = statuses => template.replace(/const data = .*;\n/, () => `const data = ${JSON.stringify({...payload, statuses})};\n`);
const emit = (window, source, data) => window.dispatchEvent(new window.MessageEvent('message', {source, data}));
const board = (source, onMessage) => new JSDOM(source, {
  runScripts: 'dangerously', url: 'http://localhost',
  beforeParse(window) { window.postMessage = onMessage; },
});
const submit = (dom, name) => {
  const document = dom.window.document;
  const header = document.querySelector('.add-column-header');
  if (header.querySelector('.add-column-form').hidden) header.querySelector('.add-column-button').click();
  const input = header.querySelector('input');
  assert.equal(input.hidden, false, `Column input visible for ${name}`);
  assert.equal(input.disabled, false);
  input.value = name;
  input.dispatchEvent(new dom.window.KeyboardEvent('keydown', {key: 'Enter', bubbles: true}));
};

// Acknowledgements without a frame reload must reset the whole form, not hide its input.
const messages = [];
const initial = html(['Backlog / To Do', 'In Progress']);
let dom = board(initial, message => messages.push(message));
try {
  for (const name of ['Review', 'Ready', 'Released']) {
    submit(dom, name);
    const event = messages.at(-1).value;
    assert.equal(event.name, name);
    emit(dom.window, dom.window, {type: 'planner:save-result', result: {event_id: event.event_id, ok: true}});
    assert.equal(dom.window.document.querySelector('.add-column-form').hidden, true);
    assert.equal(dom.window.document.querySelector('.add-column-header input').value, '');
  }
} finally { dom.window.close(); }

// Real saves replace the embedded frame. Reveal the next composer only after load,
// and only once for a matching successful create (never for errors or unrelated saves).
const bridge = new JSDOM(fs.readFileSync(path.join(root, 'assets/kanban_component/index.html'), 'utf8'), {runScripts: 'dangerously', url: 'http://localhost'});
const bw = bridge.window, frame = bw.document.getElementById('board-frame');
const statuses = ['Backlog / To Do', 'In Progress'];
const streamlit = [];
bw.postMessage = message => streamlit.push(message);
let forwarded = [];
const wire = () => {
  frame.contentWindow.postMessage = message => {
    forwarded.push(message);
    emit(dom.window, dom.window, message);
  };
};
const makeBoard = source => board(source, message => emit(bw, frame.contentWindow, message));
const renderFrame = (source, result) => emit(bw, bw, {type: 'streamlit:render', args: {html: source, height: 760, save_result: result}});
dom = makeBoard(initial);
try {
  wire();
  renderFrame(initial, null);
  frame.dispatchEvent(new bw.Event('load'));
  for (const name of ['Review', 'Ready', 'Released']) {
    submit(dom, name);
    const event = streamlit.findLast(message => message.type === 'streamlit:setComponentValue').value;
    assert.equal(event.action, 'add_column');
    assert.equal(event.name, name);
    statuses.push(name);
    const source = html(statuses);
    const result = {event_id: event.event_id, ok: true};
    forwarded = [];
    renderFrame(source, result);
    renderFrame(source, result); // A second render may arrive before the frame loads.
    assert.equal(forwarded.length, 0);
    dom.window.close();
    dom = makeBoard(source);
    const wrap = dom.window.document.querySelector('.board-wrap');
    Object.defineProperty(wrap, 'scrollWidth', {value: 1800});
    wire();
    frame.dispatchEvent(new bw.Event('load'));
    assert.equal(wrap.scrollLeft, 1800);
    assert.equal(dom.window.document.querySelector('.add-column-form').hidden, false);
    assert.equal(dom.window.document.activeElement, dom.window.document.querySelector('.add-column-header input'));
    renderFrame(source, result);
    assert.equal(forwarded.filter(message => message.type === 'planner:reveal-column-creator').length, 1);
  }
  submit(dom, 'Retry');
  const event = streamlit.findLast(message => message.type === 'streamlit:setComponentValue').value;
  forwarded = [];
  renderFrame(html(statuses), {event_id: event.event_id, ok: false, error: 'Disk full'});
  assert.equal(forwarded.some(message => message.type === 'planner:reveal-column-creator'), false);
  assert.match(dom.window.document.querySelector('.add-column-header [role=alert]').textContent, /Disk full/);
  assert.equal(dom.window.document.querySelector('.add-column-header input').disabled, false);
  console.log('PASS: repeated additions, full form reset, fresh-frame readiness, composer visibility/focus, one-time reveal, and retry after failure.');
} finally {
  dom.window.close();
  bw.close();
}
