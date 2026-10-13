// ==UserScript==
// @name         AI AutoAnswer · 本地模拟题库
// @namespace    https://localhost/ai-autoanswer-fixture
// @version      0.2.0
// @description  仅用于 AI AutoAnswer 本地 30 题模拟页面的 DOM 答题流程测试
// @match        file:///*/test_web/index.html*
// @match        http://127.0.0.1:8765/index.html*
// @match        http://localhost:8765/index.html*
// @connect      api.deepseek.com
// @grant        GM_getValue
// @grant        GM_setValue
// @grant        GM_xmlhttpRequest
// @run-at       document-idle
// @noframes
// ==/UserScript==

(function () {
  'use strict';

  const LABELS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
  const MAX_QUESTIONS = 30;
  const MAX_REQUESTS = 40;
  const MAX_MS = 10 * 60 * 1000;

  function parseAnswer(raw, optionLabels, observedType) {
    const value = typeof raw === 'string' ? JSON.parse(raw) : raw;
    if (!value || typeof value !== 'object' || Array.isArray(value)) throw Error('AI 响应不是 JSON 对象');
    const expected = ['answers', 'can_answer', 'is_question', 'question_type'];
    const actual = Object.keys(value).sort();
    if (JSON.stringify(actual) !== JSON.stringify(expected)) throw Error('AI 响应字段不符合约定');
    if (value.is_question !== true || value.can_answer !== true) throw Error('AI 无法可靠回答当前题');
    if (value.question_type !== observedType) throw Error('AI 题型与页面控件不一致');
    if (!Array.isArray(value.answers) || !value.answers.length) throw Error('AI 未提供答案');
    if (observedType === 'single' && value.answers.length !== 1) throw Error('单选题答案数量错误');
    if (new Set(value.answers).size !== value.answers.length) throw Error('AI 答案包含重复选项');
    if (!value.answers.every(x => typeof x === 'string' && optionLabels.includes(x))) {
      throw Error('AI 答案不在当前页面选项中');
    }
    return value.answers;
  }

  function readQuestion(doc) {
    const stem = doc.querySelector('#question-text')?.textContent?.trim() || '';
    if (/练习完成/.test(stem)) return { finished: true };
    if (!stem || /正在加载/.test(stem)) throw Error('题目仍在加载');
    const chip = doc.querySelector('#type-chip')?.textContent?.trim();
    const type = chip === '单选题' ? 'single' : chip === '多选题' ? 'multiple' : null;
    if (!type) throw Error('无法判断题型');
    const options = new Map();
    for (const input of doc.querySelectorAll('#options label.option input')) {
      const label = input.closest('label');
      const shown = label?.querySelector('.option-text')?.textContent?.trim() || '';
      const match = /^([A-Z])[.．、\s]+(.+)$/s.exec(shown);
      if (!match || !LABELS.includes(match[1]) || options.has(match[1])) throw Error('选项标签缺失或重复');
      if (input.type !== (type === 'single' ? 'radio' : 'checkbox')) throw Error('题型与选项控件不一致');
      if (!input.isConnected || input.disabled) throw Error('选项不可操作');
      options.set(match[1], { input, text: match[2].trim() });
    }
    if (options.size < 2) throw Error('当前页面选项不完整');
    const counter = doc.querySelector('#counter')?.textContent?.trim() || '';
    return { stem, type, options, fingerprint: `${counter}\n${stem}` };
  }

  // Add a site adapter here and a matching @match rule when extending this script.
  // Keep the automation loop below independent of each site's CSS selectors.
  const ADAPTERS = [{
    id: 'fixture',
    matches(url, doc) {
      const localFile = url.protocol === 'file:' && /\/test_web\/index\.html$/i.test(url.pathname);
      const localHttp = ['127.0.0.1', 'localhost'].includes(url.hostname) &&
        url.port === '8765' && url.pathname === '/index.html';
      return (localFile || localHttp) &&
        !!doc.querySelector('.header-badge')?.textContent?.includes('本地练习');
    },
    readQuestion,
    isSelected(option) { return option.input.checked; },
    select(option) { option.input.click(); },
    findNextButton(doc) { return doc.querySelector('#next-button'); },
    canAdvance(button) { return !!button && !button.disabled && !button.hidden && button.textContent.includes('下一题'); },
    advance(button) { button.click(); },
  }];

  function selectAdapter(url, doc) {
    return ADAPTERS.find(adapter => adapter.matches(url, doc)) || null;
  }

  function redactLogDetail(value) {
    return String(value).replace(/Bearer\s+sk-[A-Za-z0-9_-]+/gi, 'Bearer [REDACTED]')
      .replace(/sk-[A-Za-z0-9_-]{16,}/g, '[REDACTED]');
  }

  function formatRunLogCsv(events) {
    const cell = value => {
      const redacted = redactLogDetail(value);
      const safe = /^[\u0000-\u0020]*[=+@-]/.test(redacted) ? `'${redacted}` : redacted;
      return `"${safe.replace(/"/g, '""')}"`;
    };
    return 'time,stage,detail\r\n' + events.map(event =>
      [event.time, event.stage, event.detail].map(cell).join(',')).join('\r\n') + '\r\n';
  }

  // Export pure DOM/JSON checks for the local Node test harness.
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = { parseAnswer, readQuestion, selectAdapter, formatRunLogCsv };
    return;
  }

  const adapter = selectAdapter(new URL(location.href), document);
  if (!adapter) return;
  const scriptStatus = document.querySelector('#script-status');
  if (scriptStatus) scriptStatus.textContent = '脚本已加载；请在右上角面板设置 Key 并开始。';

  let running = false;
  let generation = 0;
  let currentRequest = null;
  let processed = 0;
  let requests = 0;
  let startedAt = 0;
  const events = [];

  const panel = document.createElement('aside');
  panel.id = 'aa-tm-panel';
  panel.style.cssText = 'position:fixed;top:12px;right:12px;z-index:2147483647;width:260px;padding:12px;background:#142139;color:white;border-radius:10px;box-shadow:0 5px 20px #0005;font:13px system-ui';
  const title = document.createElement('strong');
  title.textContent = 'AI AutoAnswer · 本地测试';
  const status = document.createElement('div');
  status.style.cssText = 'margin:9px 0;white-space:pre-wrap;word-break:break-word';
  status.textContent = '待启动';
  const start = document.createElement('button');
  start.textContent = '开始';
  const stop = document.createElement('button');
  stop.textContent = '停止';
  const keyButton = document.createElement('button');
  keyButton.textContent = '设置 Key';
  const modelButton = document.createElement('button');
  modelButton.textContent = '设置模型';
  const exportButton = document.createElement('button');
  exportButton.textContent = '导出日志';
  for (const button of [start, stop, keyButton, modelButton, exportButton]) {
    button.type = 'button';
    button.style.cssText = 'margin:0 5px 0 0;padding:5px 9px;border:0;border-radius:5px;background:#3973df;color:white;cursor:pointer';
  }
  const eventLog = document.createElement('pre');
  eventLog.style.cssText = 'max-height:140px;overflow:auto;white-space:pre-wrap;word-break:break-word;font:11px/1.5 monospace';
  eventLog.setAttribute('aria-label', '运行日志');
  panel.append(title, status, start, stop, keyButton, modelButton, exportButton, eventLog);
  document.body.append(panel);

  function say(message) { status.textContent = `${message}\n已处理 ${processed} 题 · API ${requests} 次`; }
  function logEvent(stage, detail) {
    const entry = { time: new Date().toISOString(), stage, detail: redactLogDetail(detail) };
    events.push(entry);
    if (events.length > 300) events.shift();
    eventLog.textContent = events.slice(-12).map(item =>
      `${item.time.slice(11, 19)} [${item.stage}] ${item.detail}`).join('\n');
  }
  function stopped() { return !running; }
  function halt(message) {
    running = false;
    generation += 1;
    currentRequest?.abort?.();
    currentRequest = null;
    say(message);
    logEvent('STOP', message);
  }

  function waitForNext(fingerprint, ticket) {
    return new Promise((resolve, reject) => {
      const deadline = Date.now() + 10000;
      const timer = setInterval(() => {
        if (ticket !== generation || stopped()) { clearInterval(timer); reject(Error('任务已停止')); return; }
        if (Date.now() > deadline) { clearInterval(timer); reject(Error('点击下一题后页面 10 秒内未变化')); return; }
        try {
          const next = adapter.readQuestion(document);
          if (next.finished || next.fingerprint !== fingerprint) { clearInterval(timer); resolve(next); }
        } catch (_) { /* Loading and temporary empty options are expected here. */ }
      }, 150);
    });
  }

  function askDeepSeek(question, key, ticket) {
    return new Promise((resolve, reject) => {
      const lines = [...question.options].map(([label, option]) => `${label}. ${option.text}`).join('\n');
      const prompt = `题型：${question.type === 'single' ? '单选' : '多选'}\n题目：${question.stem}\n选项：\n${lines}`;
      requests += 1;
      const request = GM_xmlhttpRequest({
        method: 'POST', url: 'https://api.deepseek.com/chat/completions', timeout: 30000,
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${key}` },
        data: JSON.stringify({ model: GM_getValue('model', 'deepseek-flash'), response_format: { type: 'json_object' },
          thinking: { type: 'disabled' }, max_tokens: 150,
          messages: [
            { role: 'system', content: '只返回 JSON 对象，字段严格为 is_question(boolean)、question_type(single 或 multiple)、answers(选项字母数组)、can_answer(boolean)。无法判断时 can_answer=false。不要输出解析、坐标或其他字段。' },
            { role: 'user', content: prompt },
          ] }),
        onload: response => {
          currentRequest = null;
          if (ticket !== generation) return;
          if (response.status < 200 || response.status >= 300) { reject(Error(`DeepSeek HTTP ${response.status}`)); return; }
          try {
            const body = JSON.parse(response.responseText);
            if (body.choices?.[0]?.finish_reason === 'length') throw Error('AI 响应被截断');
            const answer = parseAnswer(body.choices?.[0]?.message?.content, [...question.options.keys()], question.type);
            resolve(answer);
          } catch (error) { reject(error); }
        },
        onerror: () => { currentRequest = null; reject(Error('DeepSeek 网络请求失败')); },
        ontimeout: () => { currentRequest = null; reject(Error('DeepSeek 请求超时')); },
        onabort: () => { currentRequest = null; reject(Error('任务已停止')); },
      });
      currentRequest = request;
    });
  }

  async function run(ticket) {
    const key = String(GM_getValue('deepseek_key', '')).trim();
    if (!key) { halt('请先点“设置 Key”'); return; }
    let previous = null;
    try {
      while (ticket === generation && running) {
        const question = adapter.readQuestion(document);
        if (question.finished) { halt('本地练习完成'); return; }
        logEvent('RECOGNIZE', `识别题型 ${question.type}、选项 ${question.options.size} 个`);
        if (processed >= MAX_QUESTIONS || requests >= MAX_REQUESTS || Date.now() - startedAt > MAX_MS) {
          throw Error('达到题量、调用次数或运行时间上限');
        }
        if (question.fingerprint === previous) throw Error('连续识别到同一道题');
        previous = question.fingerprint;
        const optionSnapshot = [...question.options].map(([label, option]) => [label, option.text]);
        say(`正在分析：${question.stem.slice(0, 32)}`);
        logEvent('REQUEST_AI', `请求第 ${processed + 1} 题`);
        const answers = await askDeepSeek(question, key, ticket);
        logEvent('ANSWER', `收到选项 ${answers.join('、')}`);
        if (ticket !== generation || !running) return;
        const live = adapter.readQuestion(document);
        if (live.fingerprint !== question.fingerprint) throw Error('AI 返回前题目已变化');
        if (live.options.size !== question.options.size) throw Error('AI 返回前选项已变化');
        if (JSON.stringify([...live.options].map(([label, option]) => [label, option.text])) !== JSON.stringify(optionSnapshot)) {
          throw Error('AI 返回前选项已变化');
        }
        for (const answer of answers) {
          const option = live.options.get(answer);
          if (!option?.input?.isConnected) throw Error(`选项 ${answer} 已失效`);
          if (!adapter.isSelected(option)) adapter.select(option);
        }
        const selected = [...live.options].filter(([, option]) => adapter.isSelected(option)).map(([label]) => label);
        if (selected.length !== answers.length || answers.some(answer => !selected.includes(answer))) {
          throw Error('点击后选中状态与答案不一致');
        }
        logEvent('VERIFY', `选中状态已确认：${selected.join('、')}`);
        const next = adapter.findNextButton(document);
        if (!adapter.canAdvance(next)) throw Error('下一题按钮不可用');
        say(`已选择 ${answers.join('、')}，正在翻页`);
        if (ticket !== generation || !running) return;
        adapter.advance(next);
        await waitForNext(question.fingerprint, ticket);
        logEvent('NEXT', '已确认题目发生变化');
        processed += 1;
      }
    } catch (error) {
      if (ticket === generation) {
        logEvent('ERROR', error.message);
        halt(`已停止：${error.message}`);
      }
    }
  }

  start.addEventListener('click', () => {
    if (running) return;
    running = true;
    processed = 0;
    requests = 0;
    startedAt = Date.now();
    generation += 1;
    logEvent('START', `适配器 ${adapter.id}；最多 ${MAX_QUESTIONS} 题`);
    run(generation);
  });
  stop.addEventListener('click', () => halt('用户已停止'));
  exportButton.addEventListener('click', () => {
    const blob = new Blob([formatRunLogCsv(events)], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'ai-autoanswer-run-log.csv';
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 0);
  });
  keyButton.addEventListener('click', () => {
    const value = prompt('输入 DeepSeek API Key（保存在篡改猴脚本存储中）', '');
    if (value !== null && value.trim()) { GM_setValue('deepseek_key', value.trim()); say('Key 已保存到脚本存储'); }
  });
  modelButton.addEventListener('click', () => {
    const value = prompt('DeepSeek 模型名称', GM_getValue('model', 'deepseek-flash'));
    if (value === null) return;
    const model = value.trim();
    if (!/^[A-Za-z0-9._-]{1,80}$/.test(model)) { say('模型名称无效'); return; }
    GM_setValue('model', model);
    say(`模型已设置为 ${model}`);
    logEvent('CONFIG', `模型 ${model}`);
  });
})();
