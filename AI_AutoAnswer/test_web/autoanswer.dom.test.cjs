const { JSDOM } = require('jsdom');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const root = __dirname;
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const dom = new JSDOM(html, { url: 'http://127.0.0.1:8765/index.html', runScripts: 'outside-only' });
const w = dom.window;
for (const name of ['questions.js', 'app.js']) w.eval(fs.readFileSync(path.join(root, name), 'utf8'));
const fixture = w.AutoAnswerFixture;
let calls = 0;
w.GM_getValue = (key, fallback) => key === 'deepseek_key' ? 'test-only-key' : fallback;
w.GM_setValue = () => {};
w.GM_xmlhttpRequest = opts => {
  calls++;
  const index = Number(w.document.getElementById('question-id').textContent.match(/\d+/)[0]) - 1;
  const question = fixture.questions[index];
  const answers = fixture.displayOptions(question, index).filter(o => question.correct.includes(o.id)).map(o => o.label);
  const timer = setTimeout(() => opts.onload({ status: 200, responseText: JSON.stringify({ choices: [{ message: { content: JSON.stringify({ is_question: true, question_type: question.type, answers, can_answer: true }) } }] }) }), 1);
  return { abort() { clearTimeout(timer); opts.onabort(); } };
};
w.eval(fs.readFileSync(path.join(root, 'autoanswer.user.js'), 'utf8'));
const buttons = [...w.document.querySelectorAll('#aa-tm-panel button')];
assert.equal(buttons[0].textContent, '开始');
buttons[0].click();
const deadline = Date.now() + 30000;
const poll = setInterval(() => {
  const text = w.document.querySelector('#aa-tm-panel div').textContent;
  if (/本地练习完成/.test(text)) {
    clearInterval(poll);
    assert.equal(calls, 30);
    assert.equal(w.document.querySelector('#completed-count').textContent, '30');
    assert.equal(w.document.querySelector('#question-text').textContent.trim(), '✓练习完成');
    console.log('PASS: Tampermonkey DOM workflow completed 30 fixture questions, 30 mock API calls');
    w.close();
  } else if (/已停止/.test(text) || Date.now() > deadline) {
    clearInterval(poll);
    console.error('FAIL:', text, 'calls=', calls);
    w.close();
    process.exitCode = 1;
  }
}, 100);
