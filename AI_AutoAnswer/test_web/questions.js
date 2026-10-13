(function (root) {
  'use strict';

  function question(id, type, prompt, texts, correct, diagram = false) {
    return {
      id,
      type,
      prompt,
      options: texts.map((text, index) => ({ id: `choice-${index}`, text })),
      correct: correct.map(index => `choice-${index}`),
      diagram,
    };
  }

  const questions = [
    question(1, 'single', '哪一种数据结构遵循先进先出（FIFO）原则？', ['栈', '队列', '二叉树', '图'], [1], true),
    question(2, 'single', '在 Python 中，哪个类型通常用于保存一组不重复的元素？', ['列表 list', '元组 tuple', '集合 set', '字符串 str'], [2]),
    question(3, 'single', 'HTML 中用于创建超链接的标签是哪一个？', ['<p>', '<a>', '<div>', '<span>'], [1]),
    question(4, 'single', '十进制数 10 对应的二进制表示是哪个？', ['1001', '1010', '1100', '1110'], [1]),
    question(5, 'single', '下列哪一个 HTTP 状态码通常表示资源未找到？', ['200', '301', '404', '500', '204', '201'], [2]),
    question(6, 'single', '在关系型数据库中，哪条 SQL 语句用于读取数据？', ['DELETE', 'INSERT', 'UPDATE', 'SELECT'], [3]),
    question(7, 'single', 'CSS 中设置文字颜色的属性是哪个？', ['background', 'color', 'font-size', 'border'], [1]),
    question(8, 'single', '哪一个 Python 关键字用于定义函数？', ['class', 'return', 'def', 'import'], [2]),
    question(9, 'single', '一个字节通常包含多少位？', ['4 位', '8 位', '16 位', '32 位'], [1]),
    question(10, 'single', '下列哪种排序算法在最坏情况下仍保持 O(n log n) 时间复杂度？', ['冒泡排序', '插入排序', '归并排序', '选择排序'], [2]),
    question(11, 'single', 'JavaScript 中，严格相等比较使用哪个运算符？', ['=', '==', '===', '!='], [2]),
    question(12, 'single', 'IPv4 地址由多少位组成？', ['16 位', '32 位', '64 位', '128 位'], [1]),
    question(13, 'single', '下列哪一项适合用栈实现？', ['打印任务排队', '撤销最近一次操作', '按到达顺序服务', '轮询队列'], [1]),
    question(14, 'single', '在 Python 中，len([1, 2, 3]) 的结果是什么？', ['2', '3', '4', '报错'], [1]),
    question(15, 'single', '下列哪种协议主要用于安全浏览网页？', ['HTTP', 'HTTPS', 'FTP', 'SMTP'], [1]),
    question(16, 'single', '计算机中 CPU 的主要作用是什么？', ['长期存储文件', '执行指令和处理数据', '显示图像', '连接键盘'], [1]),
    question(17, 'single', '在 Git 中，哪个命令用于查看工作区状态？', ['git log', 'git status', 'git clone', 'git init'], [1]),
    question(18, 'single', '下列哪个文件扩展名通常代表 JSON 数据？', ['.csv', '.json', '.png', '.exe'], [1]),
    question(19, 'single', '逻辑表达式 true && false 的结果是？', ['true', 'false', 'null', 'undefined'], [1]),
    question(20, 'single', '在二维图像中，一个像素通常表示什么？', ['整张图', '图像中的一个采样点', '文件大小', '刷新率'], [1]),
    question(21, 'multiple', '下列哪些属于 Python 内置容器类型？（多选）', ['列表 list', '整数 int', '字典 dict', '浮点数 float', '集合 set', '布尔值 bool'], [0, 2, 4]),
    question(22, 'multiple', '下列哪些是常见的 HTTP 请求方法？（多选）', ['GET', 'POST', 'SELECT', 'PUT'], [0, 1, 3]),
    question(23, 'multiple', '下列哪些属于关系型数据库？（多选）', ['SQLite', 'PostgreSQL', 'MySQL', 'Redis'], [0, 1, 2]),
    question(24, 'multiple', '下列哪些是有效的 Python 布尔值？（多选）', ['True', 'False', 'TRUE', 'FALSE'], [0, 1]),
    question(25, 'multiple', '下列哪些属于 CSS 布局技术？（多选）', ['Flexbox', 'Grid', 'HTTP', 'Float'], [0, 1, 3]),
    question(26, 'multiple', '下列哪些数据结构支持按索引直接读取元素？（多选）', ['Python 列表', 'Python 元组', 'Python 集合', 'Python 字符串'], [0, 1, 3]),
    question(27, 'multiple', '下列哪些是常见的图像文件格式？（多选）', ['PNG', 'JPEG', 'SVG', 'MP3'], [0, 1, 2]),
    question(28, 'multiple', '下列哪些运算符可用于 Python 的数值运算？（多选）', ['+', '*', '//', 'and'], [0, 1, 2]),
    question(29, 'multiple', '下列哪些方法可用于提高账户安全性？（多选）', ['启用多因素认证', '使用独立强密码', '公开验证码', '及时安装安全更新'], [0, 1, 3]),
    question(30, 'multiple', '下列哪些是适合自动化测试验证的结果？（多选）', ['题号增加', '选项状态发生变化', '页面进入完成状态', '鼠标坐标始终固定'], [0, 1, 2]),
  ];

  function displayOptions(q, rotation) {
    const offset = ((rotation % q.options.length) + q.options.length) % q.options.length;
    return q.options.slice(offset).concat(q.options.slice(0, offset))
      .map((option, index) => ({ ...option, label: String.fromCharCode(65 + index) }));
  }

  function gradeSelection(q, selected) {
    return selected.size === q.correct.length && q.correct.every(id => selected.has(id));
  }

  function visibleOptionText(option) {
    return `${option.label}. ${option.text}`;
  }

  const api = { questions, displayOptions, gradeSelection, visibleOptionText };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.AutoAnswerFixture = api;
})(globalThis);
