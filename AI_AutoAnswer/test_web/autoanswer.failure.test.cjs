const { test } = require('node:test');
const assert = require('node:assert/strict');
const { JSDOM } = require('jsdom');
const fs = require('node:fs');
const path = require('node:path');

const root = __dirname;
const source = name => fs.readFileSync(path.join(root, name), 'utf8');
const response = answers => ({ status: 200, responseText: JSON.stringify({
  choices: [{ message: { content: JSON.stringify({
    is_question: true, question_type: 'single', answers, can_answer: true,
  }) } }],
}) });

function createPage(requestHandler, startQuestion = 1) {
  const dom = new JSDOM(source('index.html'), {
    url: `http://127.0.0.1:8765/index.html?start=${startQuestion}`, runScripts: 'outside-only',
  });
  const w = dom.window;
  w.eval(source('questions.js'));
  w.eval(source('app.js'));
  const store = new Map([['deepseek_key', 'test-only-key']]);
  w.GM_getValue = (key, fallback) => store.has(key) ? store.get(key) : fallback;
  w.GM_setValue = (key, value) => store.set(key, value);
  w.GM_xmlhttpRequest = opts => requestHandler(w, opts);
  w.eval(source('autoanswer.user.js'));
  const buttons = [...w.document.querySelectorAll('#aa-tm-panel button')];
  return { w, buttons, store, start: buttons[0], stop: buttons[1], status: () => w.document.querySelector('#aa-tm-panel div').textContent,
    log: () => w.document.querySelector('[aria-label="运行日志"]').textContent,
    close: () => w.close() };
}

test('model can be configured from the panel without editing source', () => {
  const page = createPage(() => { throw Error('No API request expected'); });
  try {
    page.w.prompt = () => ' deepseek-v4-pro ';
    const button = page.buttons.find(item => item.textContent === '设置模型');
    assert.ok(button);
    button.click();
    assert.equal(page.store.get('model'), 'deepseek-v4-pro');
  } finally { page.close(); }
});

test('fixture page visibly confirms when the userscript has loaded', () => {
  const page = createPage(() => { throw Error('No API request expected'); });
  try {
    assert.match(page.w.document.querySelector('#script-status').textContent, /脚本已加载/);
  } finally { page.close(); }
});

async function waitFor(check, timeoutMs = 1500) {
  const end = Date.now() + timeoutMs;
  while (!check()) {
    if (Date.now() > end) throw Error('Timed out waiting for expected state');
    await new Promise(resolve => setTimeout(resolve, 10));
  }
}

test('invalid AI answer stops before selecting any option', async () => {
  const page = createPage((_w, opts) => {
    setTimeout(() => opts.onload(response(['Z'])), 0);
    return { abort() { opts.onabort(); } };
  });
  try {
    page.start.click();
    await waitFor(() => /已停止/.test(page.status()));
    assert.match(page.log(), /ERROR.*答案不在当前页面/);
    assert.equal(page.w.document.querySelectorAll('#options input:checked').length, 0);
  } finally { page.close(); }
});

test('changed option text during AI request stops before selecting', async () => {
  const page = createPage((w, opts) => {
    setTimeout(() => {
      w.document.querySelector('#options .option-text').textContent = 'A. 已变更的选项';
      opts.onload(response(['B']));
    }, 0);
    return { abort() { opts.onabort(); } };
  });
  try {
    page.start.click();
    await waitFor(() => /已停止/.test(page.status()));
    assert.match(page.log(), /选项已变化/);
    assert.equal(page.w.document.querySelectorAll('#options input:checked').length, 0);
  } finally { page.close(); }
});

test('stop aborts a pending AI request without selecting', async () => {
  let aborted = 0;
  const page = createPage((_w, opts) => ({ abort() { aborted++; opts.onabort(); } }));
  try {
    page.start.click();
    page.stop.click();
    assert.equal(aborted, 1);
    assert.match(page.status(), /用户已停止/);
    assert.equal(page.w.document.querySelectorAll('#options input:checked').length, 0);
  } finally { page.close(); }
});

test('preselected extra choice stops before any new multi-select clicks', async () => {
  const page = createPage((_w, opts) => {
    setTimeout(() => opts.onload({ status: 200, responseText: JSON.stringify({
      choices: [{ message: { content: JSON.stringify({
        is_question: true, question_type: 'multiple', answers: ['A', 'C'], can_answer: true,
      }) } }],
    }) }), 0);
    return { abort() { opts.onabort(); } };
  }, 21);
  try {
    const inputs = [...page.w.document.querySelectorAll('#options input')];
    inputs[5].click();
    page.start.click();
    await waitFor(() => /已停止/.test(page.status()));
    assert.match(page.log(), /预先选中了其他选项/);
    assert.deepEqual([...page.w.document.querySelectorAll('#options input:checked')], [inputs[5]]);
  } finally { page.close(); }
});
