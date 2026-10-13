const test = require('node:test');
const assert = require('node:assert/strict');
const { questions, displayOptions, gradeSelection, visibleOptionText } = require('./questions.js');

test('fixture contains 20 single choice and 10 multiple choice questions', () => {
  assert.equal(questions.length, 30);
  assert.equal(questions.filter(q => q.type === 'single').length, 20);
  assert.equal(questions.filter(q => q.type === 'multiple').length, 10);
  assert.equal(new Set(questions.map(q => q.id)).size, 30);
  for (const q of questions) {
    assert.ok(q.prompt.length > 8);
    assert.ok(q.options.length >= 4 && q.options.length <= 6);
    assert.equal(new Set(q.options.map(option => option.id)).size, q.options.length);
    assert.ok(q.correct.length >= 1);
    assert.ok(q.correct.every(id => q.options.some(option => option.id === id)));
    assert.equal(q.type === 'single', q.correct.length === 1);
  }
});

test('option labels move while the underlying correct choice remains stable', () => {
  const q = questions[0];
  const first = displayOptions(q, 0);
  const second = displayOptions(q, 1);
  assert.notEqual(first.find(o => q.correct.includes(o.id)).label,
                  second.find(o => q.correct.includes(o.id)).label);
  assert.ok(first.every(o => /^[A-F]$/.test(o.label)));
});

test('grading requires the exact set of choices', () => {
  const single = questions[0];
  const multiple = questions[20];
  assert.equal(gradeSelection(single, new Set(single.correct)), true);
  assert.equal(gradeSelection(multiple, new Set(multiple.correct)), true);
  assert.equal(gradeSelection(multiple, new Set(multiple.correct.slice(0, 1))), false);
  assert.equal(gradeSelection(single, new Set()), false);
});

test('the visible option is one OCR-readable labeled text', () => {
  const option = displayOptions(questions[0], 0)[0];
  assert.equal(visibleOptionText(option), `${option.label}. ${option.text}`);
});
