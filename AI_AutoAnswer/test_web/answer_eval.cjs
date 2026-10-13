const fs = require('node:fs');
const { buildChatRequest, parseAnswer } = require('./autoanswer.user.js');

function validateCases(cases) {
  if (!Array.isArray(cases) || cases.length < 1 || cases.length > 100) {
    throw Error('评测数据必须包含 1 至 100 道题');
  }
  const ids = new Set();
  for (const item of cases) {
    if (!item || typeof item.id !== 'string' || !item.id.trim() || ids.has(item.id)) {
      throw Error('题目 ID 缺失或重复');
    }
    ids.add(item.id);
    if (!['single', 'multiple'].includes(item.type) || typeof item.stem !== 'string' || !item.stem.trim()) {
      throw Error(`题目 ${item.id} 的题型或题干无效`);
    }
    const entries = item.options && !Array.isArray(item.options) && typeof item.options === 'object'
      ? Object.entries(item.options) : [];
    if (entries.length < 2 || entries.length > 8 || entries.some(([label, value]) =>
      !/^[A-H]$/.test(label) || typeof value !== 'string' || !value.trim())) {
      throw Error(`题目 ${item.id} 的选项无效`);
    }
    const labels = new Set(entries.map(([label]) => label));
    if (!Array.isArray(item.expected) || !item.expected.length ||
        (item.type === 'single' && item.expected.length !== 1) ||
        new Set(item.expected).size !== item.expected.length ||
        item.expected.some(label => !labels.has(label))) {
      throw Error(`题目 ${item.id} 的标准答案无效`);
    }
  }
}

async function evaluateCases(cases, request, model = 'deepseek-flash') {
  validateCases(cases);
  if (!/^[A-Za-z0-9._-]{1,80}$/.test(model)) throw Error('模型名称无效');
  const counts = () => ({ total: 0, exact: 0, incorrect: 0, abstained: 0,
    invalid: 0, api_errors: 0 });
  const report = { ...counts(), total: cases.length, model,
    by_type: { single: counts(), multiple: counts() },
    prompt_tokens: 0, completion_tokens: 0 };
  const record = (type, field) => {
    report[field]++;
    report.by_type[type][field]++;
  };
  for (const item of cases) {
    report.by_type[item.type].total++;
    const question = { type: item.type, stem: item.stem,
      options: new Map(Object.entries(item.options).map(([label, text]) => [label, { text }])) };
    let response;
    try {
      response = await request(buildChatRequest(question, model));
    } catch (_) {
      record(item.type, 'api_errors');
      continue;
    }
    report.prompt_tokens += response?.usage?.prompt_tokens || 0;
    report.completion_tokens += response?.usage?.completion_tokens || 0;
    try {
      if (response?.choices?.[0]?.finish_reason === 'length') throw Error('truncated');
      const content = response?.choices?.[0]?.message?.content;
      const value = JSON.parse(content);
      if (value?.is_question === true && value?.can_answer === false &&
          value.question_type === item.type && Array.isArray(value.answers) && value.answers.length === 0 &&
          Object.keys(value).sort().join(',') === 'answers,can_answer,is_question,question_type') {
        record(item.type, 'abstained');
        continue;
      }
      const answer = parseAnswer(value, [...question.options.keys()], item.type);
      const expected = new Set(item.expected);
      if (answer.length === expected.size && answer.every(label => expected.has(label))) {
        record(item.type, 'exact');
      } else record(item.type, 'incorrect');
    } catch (_) {
      record(item.type, 'invalid');
    }
  }
  report.answer_rate = (report.exact + report.incorrect) / report.total;
  report.accuracy_answered = report.exact + report.incorrect > 0
    ? report.exact / (report.exact + report.incorrect) : null;
  report.accuracy_all = report.exact / report.total;
  return report;
}

async function main() {
  const [flag, filename] = process.argv.slice(2);
  if (flag !== '--live' || !filename || process.argv.length !== 4) {
    throw Error('用法：node answer_eval.cjs --live <评测数据.json>');
  }
  const key = process.env.DEEPSEEK_API_KEY;
  if (!key) throw Error('请先设置 DEEPSEEK_API_KEY 环境变量');
  const cases = JSON.parse(fs.readFileSync(filename, 'utf8'));
  validateCases(cases);
  const report = await evaluateCases(cases, async payload => {
    const response = await fetch('https://api.deepseek.com/chat/completions', {
      method: 'POST', signal: AbortSignal.timeout(30000),
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${key}` },
      body: JSON.stringify(payload),
    });
    if (!response.ok) throw Error(`HTTP ${response.status}`);
    return response.json();
  }, process.env.DEEPSEEK_MODEL || 'deepseek-flash');
  process.stdout.write(JSON.stringify(report, null, 2) + '\n');
}

if (require.main === module) {
  main().catch(error => {
    process.stderr.write(`评测未完成：${error.message.replace(/sk-[A-Za-z0-9_-]{16,}/g, '[REDACTED]')}\n`);
    process.exitCode = 1;
  });
}

module.exports = { validateCases, evaluateCases };
