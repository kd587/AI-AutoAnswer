# AI AutoAnswer

一个以浏览器脚本为主、可二次开发的选择题自动化项目。仓库包含两个独立入口：

- **浏览器脚本**：用于明确允许自动化的网页。当前附带的脚本支持两种本地模拟页；其他网站需要配置选择器或编写站点适配器，并添加精确的 `@match`。
- **Windows 桌面程序**：保留的实验性客户端路径，本阶段不作为主产品维护；不承诺任意第三方客户端兼容。

项目不自动提交、交卷，也不提供绕过验证码、监考或访问保护的能力。请只在个人题库或明确允许自动化的环境使用。

## 五分钟运行本地网页示例

1. 安装 Tampermonkey，在浏览器中新建脚本，将 [示例脚本](AI_AutoAnswer/test_web/autoanswer.user.js) 全文粘贴并保存。
2. 在 `AI_AutoAnswer` 目录运行 `python -m http.server 8765 --directory test_web`。
3. 打开 `http://127.0.0.1:8765/index.html`。页面右上角会出现“AI AutoAnswer · 本地测试”面板。另一个布局的三题示例在 `http://127.0.0.1:8765/alternate.html`。
4. 确认右侧显示“脚本已加载”，先点“诊断页面”检查题型、选项数与下一题按钮，再设置 Key 和模型并点击“开始”。“停止”可立即中断；“导出日志”下载本次运行事件及汇总。

不要把 Key 写入脚本、提交到 GitHub 或发到 Issue。网页脚本的 Key 保存在 Tampermonkey 存储中；桌面程序使用 Windows Credential Manager。已经公开过的 Key 应在服务商控制台撤销并重新生成。

题库本身可离线打开，但 `file://` 需要浏览器授予 Tampermonkey 文件网址权限，因此推荐上面的本地 HTTP 地址。脚本只使用页面可见的题目和选项，不读取测试题库的标准答案；启动后会把这些题目内容发送到 DeepSeek API。

## 开发与验证

```powershell
cd AI_AutoAnswer
npm --prefix test_web ci
npm --prefix test_web test

# Windows + Python 3.11
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest -q
```

Node 测试包含 DOM 中 30 道模拟题的完整选择与翻页流程，AI 响应由测试桩提供。它不验证真实 DeepSeek 答案正确率，也不等同于 Tampermonkey 扩展内或第三方网站的实测。独立的 [答案质量评测工具和结果解释](docs/ANSWER_EVALUATION.md) 可以在用户自备、已核对答案的数据集上调用真实 API；仓库尚未公布真实题库评测结果。

桌面程序的启动、Windows-MCP 运行环境、EXE 构建和当前兼容边界见 [桌面工程说明](AI_AutoAnswer/README.md)。不要只分发单个 onedir EXE；发布前按 [发布检查表](docs/RELEASE.md) 执行交互式验证。

## 二次开发

网页适配遵循 [站点适配指南](docs/WEB_ADAPTERS.md)。常见原生单选框和复选框页面可配置选择器，复杂页面仍需自定义适配器。核心循环会校验 AI 答案、点击后的选中集合和新题加载；诊断按钮可在不调用 API 的情况下检查当前页面。桌面模块的入口见 [架构说明](docs/ARCHITECTURE.md)。

欢迎提交 Issue 或 Pull Request；先阅读 [贡献指南](CONTRIBUTING.md)、[安全说明](SECURITY.md)和[更新记录](CHANGELOG.md)。代码采用 [MIT 许可证](LICENSE)，第三方组件的许可证见 [NOTICE](NOTICE.md)。

## 当前验证边界

| 路径 | 已有自动化检查 | 尚需人工验证 |
| --- | --- | --- |
| 本地网页脚本 | 两种布局的题目解析与流程测试、30 题模拟 DOM 流程 | Tampermonkey 扩展内运行、实际 API 调用、其他网站 |
| Windows 桌面 | Python 单元测试及本地模拟客户端工具 | 每个发布构建的 EXE、DPI/多屏、目标客户端兼容性 |

点击成功数不等于答题正确率。任何真实网站或客户端都必须先检查允许自动化的范围，再进行专门适配和验证。
