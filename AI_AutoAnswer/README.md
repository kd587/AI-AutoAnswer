# AI AutoAnswer

公开仓库入口、浏览器适配说明和发布检查表见[仓库首页](../README.md)。本页只介绍 Windows 桌面程序及本地模拟客户端。

面向个人模拟题库和明确允许自动化的 Windows 练习客户端。主程序使用 Python 3.11，Windows-MCP 0.8.5 服务使用独立 Python 3.13 环境；最终 onedir 包含两者冻结后的 EXE，用户运行时无须 Python、uv 或网络下载 MCP。界面自动启动私有 stdio 服务，只启用 `Snapshot,Screenshot,Click,WaitFor,Scroll,DisplayInventory`。当前版本没有 `ControlStatus`，鼠标接管由主程序自己的检测器负责。

## 使用

从源码运行，或执行 `build.bat` 后使用 `dist\AI_AutoAnswer\AI_AutoAnswer.exe`，并保留整个 onedir 目录。输入 DeepSeek API Key，选择窗口并点击“开始”。程序先恢复目标窗口并确认它在前台，再启动识别。默认最多 30 题、30 分钟、估算费用上界 1 美元。Ctrl+Shift+F12 为紧急停止；鼠标移动、目标窗口切换或关闭、截图异常、重复题目或无法验证选择会暂停或停止。不会点击交卷、最终提交或考试提交按钮。已有学习通适配器仅作保守的练习页识别；其真实客户端兼容性尚未验证。

准星选窗口：先把程序窗口移到不遮挡目标的位置，按住“拖动准星选窗口”，将鼠标拖到目标窗口的内容区域再松开。下拉框会显示选中的窗口标题、进程和句柄；若落在程序自身或窗口无法读取，运行状态与事件框会给出原因。浏览器测试时请将题库放在独立窗口，避免切换其他标签页。

密钥保存到 Windows Credential Manager，不写入源码或运行日志。SQLite 仅保留状态、错误及调用统计，不保存题干和解析。无标准答案反馈时，点击成功数不代表答题正确率。

右侧日志显示阶段耗时、识别来源、选项定位、选择验证和异常调用栈。准星选窗及连接测试等界面事件也写入 SQLite；“导出完整日志 CSV”导出历史事件，“复制当前日志”复制界面保留的最近 3000 行。日志会脱敏常见 API Key 和 Authorization 形式。

## 源码运行

构建机需要 Python 3.11 与 3.13。`build-mcp.bat` 安装 Windows-MCP 0.8.5 到 `.venv-mcp`；主程序依赖在 `.venv` 中安装。分别启动模拟客户端和主程序：

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\build-mcp.bat
.\.venv\Scripts\python.exe -m test_client.client
.\.venv\Scripts\python.exe main.py
```

模拟客户端有 20 道单选、10 道多选，包括 A–F 选项、位置变化、延迟、图文题和模拟加载失败。可运行 `python -m pytest -q`、`python -m scripts.smoke_ocr 20`、`python -m scripts.smoke_windows`。后两项分别检查 OCR 与 UIA；实际 MCP 鼠标点击需要目标位于交互式 Windows 桌面前台。

## 本地网页测试题库

双击 [`test_web/index.html`](test_web/index.html) 可在浏览器打开独立的 30 题模拟题库；无需安装依赖或联网。前 20 题为单选，后 10 题为多选，选项位置随题号变化。选中选项后点击“下一题”，最后显示完成页，不会执行最终提交。右侧“测试设置”可模拟慢速加载、下一题加载失败、OCR 无法读取选项文字，或跳到指定题号。也可用 `test_web/index.html?start=21` 从第 21 题开始。运行 `node --test test_web/quiz.test.cjs` 验证题库数据与答案映射。

浏览器窗口可以用于桌面窗口截图和点击流程的独立测试，但它与原生 Windows 客户端的 UIA 树不同，不能据此推断学习通客户端兼容性。

### 篡改猴版：只在本地模拟题库使用

[`test_web/autoanswer.user.js`](test_web/autoanswer.user.js) 是独立的 Tampermonkey 测试脚本，只匹配本项目的 `test_web/index.html` 文件页，或 `127.0.0.1:8765` / `localhost:8765` 上的该测试页。它从页面真实的单选框、复选框读取题目和选项，向 DeepSeek 请求 JSON 答案，验证答案字母与页面题型，点击当前选项并检查 `checked` 状态，再点击页面现有的“下一题”按钮并等待题目变化。脚本不读取 `questions.js` 中的标准答案，也不会点击最终提交。

使用：在浏览器安装 Tampermonkey，创建脚本并粘贴 `autoanswer.user.js` 全文。推荐在项目目录运行 `python -m http.server 8765 --directory test_web`，然后打开 `http://127.0.0.1:8765/index.html`。确认测试页显示“脚本已加载”，再点击右上角面板的“设置 Key”“设置模型”和“开始”；可随时点击“停止”，并可导出脱敏运行日志。启动后，题干与选项会发送到 DeepSeek API。如果直接使用 `file://` 打开页面，需要在浏览器扩展详情里开启 Tampermonkey 的“允许访问文件网址”。Key 保存在 Tampermonkey 的脚本存储中，不写入项目文件。运行 `npm --prefix test_web ci` 和 `npm --prefix test_web test` 可检查答案校验，并在 jsdom 中模拟整个 30 题 DOM 选择与翻页流程（DeepSeek 请求使用模拟返回）。该脚本尚未在 Tampermonkey 扩展内或真实第三方页面运行；独立 Windows 客户端无法运行浏览器用户脚本。扩展站点请阅读[适配指南](../docs/WEB_ADAPTERS.md)。

如果桌面自动运行暂停，先看主程序右侧事件框中的完整“已暂停：…”原因，并可用“导出完整日志 CSV”保存事件。点“测试连接”只验证 DeepSeek，不代表窗口截图、OCR 或点击已经通过。发布新构建前必须按[发布检查表](../docs/RELEASE.md)重新验证。

若设备应用程序控制策略阻止新生成的未签名 EXE 启动，可在已配置开发环境的电脑上双击 `start-source.bat` 运行同一份源码；这需要本项目的 `.venv` 和 `mcp_runtime`。不要绕过设备安全策略。历史开发记录中，2026-10-12 的源码曾在交互式 Windows 桌面上以确定性答案提供器完成原生 Qt 模拟客户端 30 题 MCP 点击、选中验证和翻页；该记录不等于本次发布构建已复测，也不证明 DeepSeek 答案正确率。浏览器页面经桌面截图 OCR 路径的连续运行尚未验证。

## 打包

`build.bat` 依次测试、构建 MCP 服务、构建主程序，并将服务端放到 `dist\AI_AutoAnswer\mcp_runtime\windows-mcp-server.exe`。将整个 `dist\AI_AutoAnswer` 目录分发。`build-onefile.bat` 生成单文件主程序加 MCP 服务端 sidecar，仍须分发整个 `dist-onefile` 目录。服务端只在本地 stdio 启动，主程序停止或退出时关闭。OCR 模型首次使用时缓存到 `C:\ProgramData\AI_AutoAnswer` 的 ASCII 路径，以兼容 Paddle 2.x 对含中文模型路径的限制。

Smart App Control 或企业应用控制可能拒绝未签名 EXE，需要由设备管理员签名并允许。打包成功本身不等于运行验证通过。Windows-MCP 官方项目与服务命令见[官方仓库](https://github.com/CursorTouch/Windows-MCP)。

## 兼容边界

- 仅操作用户明确选中的前台窗口；目标被遮挡、最小化、安全桌面或权限级别更高时暂停。
- Snapshot 可访问控件优先；否则 Screenshot 加 PaddleOCR。OCR 必须识别题干、至少两个带字母标签的选项，以及可确认的位置。
- DeepSeek 只返回是否是题、题型、答案编号和能否回答。答案编号必须存在于当前选项；点击后必须确认状态或图像发生变化。
- 桌面截图 OCR 路径仍有可视区域和前台切换限制；真实第三方客户端兼容性尚未实测。每个发布构建应重新执行模拟客户端的 MCP 点击验证。
