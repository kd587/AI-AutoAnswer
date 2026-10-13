const { test } = require('node:test');
const assert = require('node:assert/strict');
const { evaluateCases, validateCases } = require('./answer_eval.cjs');

const cases = [
  { id: 'one', type: 'single', stem: '先进先出结构？', options: { A: '栈', B: '队列' }, expected: ['B'] },
  { id: 'two', type: 'multiple', stem: '容器？', options: { A: '列表', B: '整数', C: '字典' }, expected: ['A', 'C'] },
  { id: 'three', type: 'single', stem: '超链接标签？', options: { A: '<a>', B: '<p>' }, expected: ['A'] },
];

test('live evaluation request never includes grading answer and reports exact matches separately', async () => {
  const seen = [];
  const responses = [
    { is_question: true, question_type: 'single', answers: ['B'], can_answer: true },
    { is_question: true, question_type: 'multiple', answers: ['A'], can_answer: true },
    { is_question: true, question_type: 'single', answers: [], can_answer: false },
  ];
  const report = await evaluateCases(cases, async payload => {
    seen.push(payload);
    return { choices: [{ finish_reason: 'stop', message: { content: JSON.stringify(responses[seen.length - 1]) } }],
      usage: { prompt_tokens: 10, completion_tokens: 5 } };
  });
  assert.equal(report.total, 3);
  assert.equal(report.exact, 1);
  assert.equal(report.incorrect, 1);
  assert.equal(report.abstained, 1);
  assert.equal(report.invalid, 0);
  assert.equal(report.prompt_tokens, 30);
  assert.equal(report.completion_tokens, 15);
  assert.equal(report.answer_rate, 2 / 3);
  assert.equal(report.accuracy_answered, 1 / 2);
  assert.equal(report.accuracy_all, 1 / 3);
  assert.equal(seen.length, 3);
  assert.ok(seen.every(payload => !JSON.stringify(payload).includes('expected')));
  assert.ok(seen.every(payload => !JSON.stringify(payload).includes('correct')));
});

test('evaluation counts malformed provider output without making a selection', async () => {
  const report = await evaluateCases(cases.slice(0, 1), async () => ({
    choices: [{ finish_reason: 'stop', message: { content: '{"answers":["Z"]}' } }],
  }));
  assert.equal(report.invalid, 1);
  assert.equal(report.exact, 0);
});

test('evaluation dataset rejects duplicate ids and missing ground truth', () => {
  assert.throws(() => validateCases([cases[0], cases[0]]), /重复/);
  assert.throws(() => validateCases([{ ...cases[0], expected: ['Z'] }]), /标准答案/);
});
