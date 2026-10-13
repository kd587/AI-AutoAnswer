const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { JSDOM } = require('jsdom');

const root = __dirname;
const source = name => fs.readFileSync(path.join(root, name), 'utf8');
const dom = new JSDOM(source('alternate.html'), {
  url: 'http://127.0.0.1:8765/alternate.html', runScripts: 'outside-only',
});
const w = dom.window;
w.eval(source('alternate.js'));
let calls = 0;
w.GM_getValue = (key, fallback) => key === 'deepseek_key' ? 'test-only-key' : fallback;
w.GM_setValue = () => {};
w.GM_xmlhttpRequest = opts => {
  const answers = [['B'], ['A', 'C'], ['D']][calls++];
  const kind = answers.length === 1 && calls !== 2 ? 'single' : 'multiple';
  const timer = setTimeout(() => opts.onload({ status: 200, responseText: JSON.stringify({
    choices: [{ message: { content: JSON.stringify({
      is_question: true, question_type: kind, answers, can_answer: true,
    }) } }],
  }) }), 1);
  return { abort() { clearTimeout(timer); opts.onabort(); } };
};
w.eval(source('autoanswer.user.js'));
const panel = w.document.querySelector('#aa-tm-panel');
assert.ok(panel, 'selector adapter should match the second local layout');
panel.querySelector('button').click();
const deadline = Date.now() + 10000;
const poll = setInterval(() => {
  const status = panel.querySelector('div').textContent;
  if (/本地练习完成/.test(status)) {
    clearInterval(poll);
    assert.equal(calls, 3);
    assert.equal(w.document.querySelector('#completed').textContent, '3');
    assert.match(panel.querySelector('[aria-label="运行日志"]').textContent, /SUMMARY.*已确认选择=3/);
    console.log('PASS: selector adapter completed 3 questions in a second local DOM layout');
    w.close();
  } else if (/已停止/.test(status) || Date.now() > deadline) {
    clearInterval(poll);
    console.error('FAIL:', status, 'calls=', calls);
    w.close();
    process.exitCode = 1;
  }
}, 100);
