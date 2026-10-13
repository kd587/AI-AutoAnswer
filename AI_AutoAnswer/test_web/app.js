(function () {
  'use strict';

  const { questions, displayOptions, gradeSelection, visibleOptionText } = globalThis.AutoAnswerFixture;
  const get = id => document.getElementById(id);
  const area = get('question-area');
  const options = get('options');
  const nextButton = get('next-button');
  const params = new URLSearchParams(location.search);
  const initial = Number(params.get('start'));
  let index = Number.isInteger(initial) && initial >= 1 && initial <= questions.length ? initial - 1 : 0;
  let selected = new Set();
  let completed = new Set();
  let correct = new Set();
  let loadingTimer = null;

  function updateProgress() {
    get('counter').textContent = index < questions.length
      ? `${String(index + 1).padStart(2, '0')} / ${questions.length}`
      : `${questions.length} / ${questions.length}`;
    get('progress').setAttribute('aria-valuenow', String(Math.min(index + 1, questions.length)));
    get('progress-fill').style.width = `${Math.min((index + 1) / questions.length * 100, 100)}%`;
    get('completed-count').textContent = String(completed.size);
    get('jump-input').value = String(Math.min(index + 1, questions.length));
  }

  function updateSelection() {
    const q = questions[index];
    const labels = displayOptions(q, index)
      .filter(option => selected.has(option.id)).map(option => option.label);
    get('selection-note').textContent = labels.length
      ? `已选择：${labels.join('、')}`
      : q.type === 'single' ? '请选择一个选项' : '请选择所有符合条件的选项';
  }

  function render() {
    updateProgress();
    options.replaceChildren();
    area.classList.remove('finished');
    get('diagram').hidden = true;
    nextButton.hidden = false;
    nextButton.disabled = false;
    get('load-status').textContent = '就绪';

    if (index >= questions.length) {
      area.classList.add('finished');
      get('type-chip').hidden = true;
      get('question-id').textContent = '30 道模拟题已结束';
      get('question-text').innerHTML = '<span class="finished-icon" aria-hidden="true">✓</span>练习完成';
      get('selection-note').textContent = `已处理 ${completed.size} 题，其中选对 ${correct.size} 题。无最终提交操作。`;
      get('current-type').textContent = '已完成';
      get('load-status').textContent = '任务完成';
      nextButton.hidden = true;
      return;
    }

    const q = questions[index];
    const multiple = q.type === 'multiple';
    get('type-chip').hidden = false;
    get('type-chip').textContent = multiple ? '多选题' : '单选题';
    get('type-chip').classList.toggle('multiple', multiple);
    get('question-id').textContent = `题目 ${String(q.id).padStart(2, '0')}`;
    get('question-text').textContent = `${q.id}. ${q.prompt}`;
    get('diagram').hidden = !q.diagram;
    get('current-type').textContent = multiple ? '多选' : '单选';
    nextButton.firstChild.textContent = '下一题 ';

    for (const option of displayOptions(q, index)) {
      const label = document.createElement('label');
      label.className = 'option';
      label.dataset.optionId = option.id;
      const input = document.createElement('input');
      input.type = multiple ? 'checkbox' : 'radio';
      input.name = `question-${q.id}`;
      input.value = option.id;
      input.checked = selected.has(option.id);
      input.setAttribute('aria-label', visibleOptionText(option));
      const text = document.createElement('span');
      text.className = 'option-text';
      text.textContent = visibleOptionText(option);
      input.addEventListener('change', () => {
        if (!multiple) selected = new Set([option.id]);
        else if (input.checked) selected.add(option.id);
        else selected.delete(option.id);
        updateSelection();
      });
      label.append(input, text);
      options.append(label);
    }
    options.classList.toggle('unreadable', get('unreadable-toggle').checked);
    updateSelection();
  }

  function goNext() {
    if (index >= questions.length || loadingTimer !== null) return;
    if (!selected.size) {
      get('load-status').textContent = '请先选择答案';
      return;
    }
    if (get('stuck-toggle').checked) {
      get('load-status').textContent = '模拟加载失败：页面未变化';
      return;
    }
    const q = questions[index];
    completed.add(q.id);
    if (gradeSelection(q, selected)) correct.add(q.id);
    else correct.delete(q.id);
    nextButton.disabled = true;
    get('load-status').textContent = '正在加载下一题…';
    get('question-text').textContent = '正在加载下一题…';
    options.replaceChildren();
    get('selection-note').textContent = '请稍候';
    const delay = get('slow-toggle').checked ? 2500 : 350 + (index % 3) * 200;
    loadingTimer = setTimeout(() => {
      loadingTimer = null;
      index += 1;
      selected = new Set();
      render();
    }, delay);
  }

  function jump(toIndex) {
    if (loadingTimer !== null) clearTimeout(loadingTimer);
    loadingTimer = null;
    index = toIndex;
    selected = new Set();
    render();
  }

  nextButton.addEventListener('click', goNext);
  get('jump-button').addEventListener('click', () => {
    const value = Number(get('jump-input').value);
    if (Number.isInteger(value) && value >= 1 && value <= questions.length) jump(value - 1);
  });
  get('reset-button').addEventListener('click', () => {
    completed = new Set();
    correct = new Set();
    jump(0);
  });
  get('unreadable-toggle').addEventListener('change', () => {
    options.classList.toggle('unreadable', get('unreadable-toggle').checked);
  });
  render();
})();
