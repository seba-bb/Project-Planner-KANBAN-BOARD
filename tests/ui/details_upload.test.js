const {JSDOM} = require('jsdom');
const fs = require('node:fs');
const assert = require('node:assert/strict');
let template = fs.readFileSync(0, 'utf8');
const data = JSON.parse(template.match(/const data = (.*);\n/)[1]);
const png = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a2uoAAAAASUVORK5CYII=';
data.users = ['anna@example.com'];
data.tasks = [{id: 'task-a', title: 'Review', status: data.statuses[0], due: '2026-10-01',
  responsible_emails: data.users, description: 'Keep these details', labels: [],
  attachments: ['attachments/task-a/existing.png'],
  attachment_links: [{name: 'existing.png', reference: 'attachments/task-a/existing.png', href: `data:image/png;base64,${png}`, kind: 'file', preview: true}],
}];
template = template.replace(/const data = .*;\n/, () => `const data = ${JSON.stringify(data)};\n`);
const messages = [];
const dom = new JSDOM(template, {runScripts: 'dangerously', url: 'http://localhost', beforeParse(w) {
  w.postMessage = message => messages.push(message);
  let blobId = 0;
  // jsdom omits the browser's Blob URL APIs; keep link creation observable.
  w.URL.createObjectURL = () => `blob:http://localhost/${++blobId}`;
  w.URL.revokeObjectURL = () => {};
  w.CSS = {escape: value => value};
}});
const w = dom.window, d = w.document;
const description = d.getElementById('edit-description');
const event = (target, type, fields) => {
  const e = new w.Event(type, {bubbles: true, cancelable: true});
  Object.assign(e, fields);
  target.dispatchEvent(e);
  return e;
};
const waitForFiles = async () => {
  for (let tries = 0; tries < 100; tries++) {
    if (!w.eval('attachmentReadPending')) return;
    await new Promise(resolve => setTimeout(resolve, 5));
  }
  throw new Error('File read did not finish');
};
const image = () => new w.File([Buffer.from(png, 'base64')], 'clipboard.png', {type: 'image/png'});
const paste = () => event(description, 'paste', {clipboardData: {items: [{kind: 'file', type: 'image/png', getAsFile: image}]}});
const drop = files => event(description, 'drop', {dataTransfer: {types: ['Files'], files, items: []}});

(async () => {
  try {
    w.openEditModal('task-a');
    assert.equal(d.querySelectorAll('.details-image-preview').length, 1, 'saved images are visible after opening');
    d.querySelector('.details-image-preview').click();
    assert.equal(d.querySelector('.details-image-preview').getAttribute('aria-expanded'), 'true');
    assert.equal(event(description, 'paste', {clipboardData: {items: [{kind: 'string', type: 'text/plain'}], files: []}}).defaultPrevented, false);
    const transfer = {types: ['Files'], files: [], items: []};
    event(description, 'dragover', {dataTransfer: transfer});
    assert(d.getElementById('details-dropzone').classList.contains('file-drag-over'));
    assert.equal(transfer.dropEffect, 'copy');
    assert.equal(drop([new w.File(['file bytes'], 'notes.txt', {type: 'text/plain'})]).defaultPrevented, true);
    await waitForFiles();
    assert.equal(paste().defaultPrevented, true);
    await waitForFiles();
    assert.equal(description.value, 'Keep these details');
    assert.equal(d.querySelectorAll('.details-image-preview').length, 2);
    assert.equal(messages.length, 0, 'uploads wait until the task is saved');
    d.getElementById('edit-save').click();
    const saved = messages.at(-1).value;
    assert.equal(saved.action, 'edit_task');
    assert.equal(saved.updates.description, 'Keep these details');
    assert.deepEqual(Array.from(saved.uploaded_files, file => file.name), ['notes.txt', 'clipboard.png']);
    assert.equal(saved.uploaded_files[0].data, Buffer.from('file bytes').toString('base64'));
    assert.equal(saved.uploaded_files[1].data, png);
    assert.equal(saved.updates.attachments[0], 'attachments/task-a/existing.png');
    w.dispatchEvent(new w.MessageEvent('message', {source: w, data: {type: 'planner:save-result', result: {event_id: saved.event_id, ok: false, error: 'Disk full'}}}));
    assert.equal(d.querySelectorAll('.details-image-preview').length, 2, 'failed saves retain queued images');
    w.closeEditModal();
    w.openNewTask(data.statuses[0]);
    assert.equal(d.querySelectorAll('.details-image-preview').length, 0, 'cancelled images do not leak into another task');
    drop([{name: 'too-large.bin', size: 21 * 1024 * 1024}]);
    assert.match(d.getElementById('details-upload-status').textContent, /20 MB/);
    const folder = event(description, 'drop', {dataTransfer: {types: ['Files'], files: [], items: [{webkitGetAsEntry: () => ({isDirectory: true})}]}});
    assert.equal(folder.defaultPrevented, true);
    assert.match(d.getElementById('details-upload-status').textContent, /individual files/);
    const originalReader = w.readUpload;
    let finishRead;
    w.readUpload = () => new Promise(resolve => { finishRead = resolve; });
    paste();
    paste();
    assert.match(d.getElementById('details-upload-status').textContent, /wait/);
    w.closeEditModal();
    w.openEditModal('task-a');
    finishRead({name: 'late.png', size: 1, data: png, href: `data:image/png;base64,${png}`, kind: 'file'});
    await new Promise(resolve => setTimeout(resolve, 0));
    assert.equal(d.querySelectorAll('.details-image-preview').length, 1, 'late reads cannot modify another editing session');
    w.readUpload = originalReader;
    w.closeEditModal();
    w.openNewTask(data.statuses[0]);
    d.getElementById('edit-title').value = 'Pasted picture';
    paste();
    await waitForFiles();
    d.getElementById('edit-attachment-links').querySelector('.attachment-remove').click();
    assert.equal(d.querySelectorAll('.details-image-preview').length, 0, 'removing the attachment removes its preview');
    paste();
    await waitForFiles();
    d.getElementById('edit-save').click();
    assert.equal(messages.at(-1).value.action, 'create_task');
    assert.equal(messages.at(-1).value.uploaded_files[0].data, png);
    console.log('PASS: file drop, image paste and previews, text paste preserved, exact save bytes for Add/Edit, limits, folder rejection, failed-save retention and cancelled-read isolation.');
  } finally { w.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
