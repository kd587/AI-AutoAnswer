(() => {
  'use strict';
  const questions = [
    { type: 'single', stem: '1. 哪种结构遵循先进先出原则？', choices: ['A. 栈', 'B. 队列', 'C. 图'] },
    { type: 'multiple', stem: '2. 哪些属于 Python 容器？', choices: ['A. 列表', 'B. 整数', 'C. 字典'] },
    { type: 'single', stem: '3. 哪个标签创建链接？', choices: ['A. p', 'B. div', 'C. span', 'D. a'] },
  ];
  const area = document.querySelector('#practice');
  const choiceArea = area.querySelector('.choices');
  let index = 0;

  function render() {
    choiceArea.replaceChildren();
    area.querySelector('.number').textContent = `${index + 1} / ${questions.length}`;
    if (index >= questions.length) {
      area.querySelector('.stem').textContent = '';
      area.querySelector('#done').hidden = false;
      area.querySelector('.next').hidden = true;
      return;
    }
    const question = questions[index];
    area.querySelector('.stem').textContent = question.stem;
    for (const text of question.choices) {
      const row = document.createElement('label');
      row.className = 'answer';
      const input = document.createElement('input');
      input.type = question.type === 'single' ? 'radio' : 'checkbox';
      input.name = `q-${index}`;
      const label = document.createElement('span');
      label.textContent = text;
      row.append(input, label);
      choiceArea.append(row);
    }
  }
  area.querySelector('.next').addEventListener('click', () => {
    if (![...choiceArea.querySelectorAll('input')].some(input => input.checked)) return;
    index++;
    area.querySelector('#completed').textContent = String(index);
    render();
  });
  render();
})();
