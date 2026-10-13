const { test } = require('node:test');
const assert = require('node:assert/strict');
const { parseAnswer, readQuestion, selectAdapter, formatRunLogCsv, buildChatRequest } = require('./autoanswer.user.js');

function page({ type = 'single', stem = '1. 哪种结构先进先出？', labels = ['A. 栈', 'B. 队列', 'C. 图'] } = {}) {
  const inputs = labels.map(label => ({
    type: type === 'single' ? 'radio' : 'checkbox', isConnected: true, disabled: false,
    closest: () => ({ querySelector: () => ({ textContent: label }) }),
  }));
  return {
    querySelector(selector) {
      const values = {
        '#question-text': { textContent: stem },
        '#type-chip': { textContent: type === 'single' ? '单选题' : '多选题' },
        '#counter': { textContent: '01 / 30' },
      };
      return values[selector] || null;
    },
    querySelectorAll: () => inputs,
  };
}

test('reads labeled inputs and the actual question type from DOM', () => {
  const q = readQuestion(page());
  assert.equal(q.type, 'single');
  assert.equal(q.options.get('B').text, '队列');
  assert.equal(q.options.get('B').input.type, 'radio');
  assert.match(q.fingerprint, /哪种结构/);
});

test('accepts a matching single and multiple answer', () => {
  assert.deepEqual(parseAnswer('{"is_question":true,"question_type":"single","answers":["B"],"can_answer":true}', ['A', 'B'], 'single'), ['B']);
  assert.deepEqual(parseAnswer({ is_question: true, question_type: 'multiple', answers: ['A', 'C'], can_answer: true }, ['A', 'B', 'C'], 'multiple'), ['A', 'C']);
});

test('AI request contains visible question and options but no grading answer', () => {
  const question = readQuestion(page());
  const payload = buildChatRequest(question, 'deepseek-flash');
  assert.equal(payload.model, 'deepseek-flash');
  assert.deepEqual(payload.response_format, { type: 'json_object' });
  assert.match(payload.messages[1].content, /哪种结构先进先出/);
  assert.match(payload.messages[1].content, /B\. 队列/);
  assert.doesNotMatch(JSON.stringify(payload), /correct|expected|标准答案/);
});

test('rejects invented labels, mismatched type, duplicates and extra fields', () => {
  const base = { is_question: true, question_type: 'single', answers: ['B'], can_answer: true };
  assert.throws(() => parseAnswer({ ...base, answers: ['Z'] }, ['A', 'B'], 'single'), /不在/);
  assert.throws(() => parseAnswer({ ...base, question_type: 'multiple' }, ['A', 'B'], 'single'), /题型/);
  assert.throws(() => parseAnswer({ ...base, answers: ['B', 'B'] }, ['A', 'B'], 'single'), /数量/);
  assert.throws(() => parseAnswer({ ...base, reason: 'extra' }, ['A', 'B'], 'single'), /字段/);
});

test('stops on incomplete, duplicate or inconsistent page controls', () => {
  assert.throws(() => readQuestion(page({ labels: ['A. 栈'] })), /不完整/);
  assert.throws(() => readQuestion(page({ labels: ['A. 栈', 'A. 队列'] })), /重复/);
  assert.throws(() => readQuestion(page({ stem: '正在加载下一题…' })), /加载/);
  assert.equal(readQuestion(page({ stem: '练习完成' })).finished, true);
});

test('selects only the explicit local fixture adapter', () => {
  const doc = { querySelector: selector => selector === '.header-badge' ? { textContent: '本地练习 · 非真实考试' } : null };
  const adapter = selectAdapter(new URL('http://127.0.0.1:8765/index.html'), doc);
  assert.equal(adapter?.id, 'fixture');
  for (const method of ['readQuestion', 'isSelected', 'select', 'findNextButton', 'canAdvance', 'advance']) {
    assert.equal(typeof adapter[method], 'function');
  }
  assert.equal(selectAdapter(new URL('https://example.com/index.html'), doc), null);
  assert.equal(selectAdapter(new URL('http://127.0.0.1:8765/other.html'), doc), null);
  assert.equal(selectAdapter(new URL('http://127.0.0.1:8765/index.html'), { querySelector: () => null }), null);
});

test('exports readable CSV events without API credentials', () => {
  const fakeKey = 'sk-' + 'abcdefghijklmnopqrstuvwxyz1234567890';
  const csv = formatRunLogCsv([{ time: '2026-10-13T10:00:00.000Z', stage: 'ERROR', detail: `Bearer ${fakeKey}, "request failed"` }]);
  assert.match(csv, /^time,stage,detail\r?\n/);
  assert.match(csv, /ERROR/);
  assert.match(csv, /\[REDACTED\]/);
  assert.doesNotMatch(csv, /abcdefghijklmnopqrstuvwxyz1234567890/);
  assert.match(csv, /""request failed""/);
});

test('CSV export treats spreadsheet formulas as text', () => {
  const csv = formatRunLogCsv([{ time: '2026-10-13T10:00:00.000Z', stage: 'ERROR', detail: '=HYPERLINK("https://example.invalid")' }]);
  assert.match(csv, /"'=HYPERLINK\(""https:\/\/example.invalid""\)"/);
});
