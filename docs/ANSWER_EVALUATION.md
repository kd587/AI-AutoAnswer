# 浏览器端答案质量评测

`npm test` 中的 30 题 DOM 测试使用模拟 API，并从模拟题库的标准答案构造响应。它验证识别后的选择、状态确认和翻页流程，**不测量 DeepSeek 答题正确率**。

`answer_eval.cjs` 是独立的可选评测工具。它向 API 只发送题型、题干、选项；本地的 `expected` 仅用于响应回来后评分。它不会操作浏览器或网页。示例数据见 [`evaluation.sample.json`](../AI_AutoAnswer/test_web/evaluation.sample.json)。

## 运行

准备一份自己有权使用、带人工核对标准答案的 JSON 数组；每题字段为 `id`、`type`（`single` 或 `multiple`）、`stem`、`options`（A–H 到选项文字的映射）和 `expected`（正确字母数组）。单次最多 100 题，先用少量题控制 API 费用。不要将含私人题目或平台内容的数据集提交到公共仓库。

在 PowerShell 中设置**新生成且未公开**的密钥后，执行：

```powershell
$env:DEEPSEEK_API_KEY = Read-Host 'DeepSeek API Key'
node AI_AutoAnswer/test_web/answer_eval.cjs --live AI_AutoAnswer/test_web/evaluation.sample.json
Remove-Item Env:DEEPSEEK_API_KEY
```

也可以设置 `DEEPSEEK_MODEL` 指定模型。CLI 不写入密钥、题干或逐题响应文件；输出只有汇总统计。运行需要 Node.js 24 或兼容的内置 `fetch` 版本以及联网能力。该命令真实调用 API，可能产生费用；自动化测试不会调用外网。

## 如何读结果

- `exact`：答案集合与标准答案完全一致的题数，尤其多选必须全部匹配。
- `incorrect`：给出了格式有效、但集合不一致的答案。
- `abstained`：模型明确表示无法可靠回答。
- `invalid`：响应格式、题型、答案标签或截断校验失败。
- `api_errors`：请求或网络失败。
- `answer_rate`：有效回答题数 / 总题数。
- `accuracy_answered`：`exact / (exact + incorrect)`；没有有效回答时为 `null`。
- `accuracy_all`：`exact / total`，把弃答、无效响应和 API 失败计入未答对。
- `by_type`：分别列出单选和多选的题数、答对、答错、弃答、格式失败与请求失败，避免总体分数掩盖多选题表现。

这是给定数据集的**答案质量**指标，不代表网页识别率、点击可靠性或其他网站的兼容性。公开结果时应同时写明数据来源、题量、题型比例、模型名、日期和是否人工核对标准答案；两道示例题不足以代表真实表现。
