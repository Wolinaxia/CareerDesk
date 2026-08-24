<p align="center">
  <strong>简体中文</strong> · <a href="en/README.md">English</a>
</p>

<p align="center">
  <img src="frontend/public/logo-light-512.png" alt="CareerDesk 标志" width="112" />
</p>

<h1 align="center">CareerDesk：你的专属求职助手</h1>

<p align="center">
  <strong>由 AI 智能体协助的求职工作台，完全开源免费。</strong><br />
  这是我为自己今年秋招做的工具，希望也能帮到同样在找工作的你。<br />
  希望我们在今年的求职季旗开得胜。
</p>

<p align="center">
  <a href="backend/pyproject.toml"><img alt="Python 3.12–3.13" src="https://img.shields.io/badge/Python-3.12%E2%80%933.13-3776AB?style=for-the-badge&amp;logo=python&amp;logoColor=white" /></a>
  <a href="backend/"><img alt="后端 FastAPI" src="https://img.shields.io/badge/Backend-FastAPI-009688?style=for-the-badge&amp;logo=fastapi&amp;logoColor=white" /></a>
  <a href="frontend/"><img alt="前端 React 19" src="https://img.shields.io/badge/Frontend-React%2019-61DAFB?style=for-the-badge&amp;logo=react&amp;logoColor=20232A" /></a>
  <br />
  <a href="backend/pyproject.toml"><img alt="版本 1.0.2" src="https://img.shields.io/badge/Version-v1.0.2-EA6B38?style=for-the-badge" /></a>
  <a href="https://github.com/xinhuangcs/CareerDesk/actions/workflows/unsigned-release.yml"><img alt="构建 GitHub Actions" src="https://img.shields.io/badge/Build-GitHub%20Actions-6E78FF?style=for-the-badge&amp;logo=githubactions&amp;logoColor=white" /></a>
  <a href="LICENSE"><img alt="MIT 许可证" src="https://img.shields.io/badge/License-MIT-E1B800?style=for-the-badge" /></a>
</p>

<p align="center">
  <a href="#-什么是-careerdesk">什么是 CareerDesk？</a> ·
  <a href="#-核心功能">核心功能</a> ·
  <a href="#-一键安装使用">快速开始</a> ·
  <a href="#-隐私与安全">隐私与安全</a> ·
  <a href="#-参与贡献">参与贡献</a>
</p>

---

## 🧭 什么是 CareerDesk？

CareerDesk 是一个完全开源免费的求职工作台。它把可视化投递管理与求职智能体放在一起，围绕你自己的记录解答求职季中的各种问题，例如投递情况分析、本周规划、面试复盘与情绪支持；同时内嵌一组确定性自动化工作流，完成公司与岗位调研、简历适配分析、题集生成、模拟面试等功能。

> CareerDesk 是运行在本机的桌面应用，不是托管式网站服务，也不是自动海投工具。

https://github.com/user-attachments/assets/5230d010-0f2d-493e-b088-3bbbd7969572

<p align="center"><sub>一段简短的演示：看板、调研与求职助手。</sub></p>

## ✨ 核心功能

<table>
  <tr>
    <td width="100%" valign="top">
      <h3>📊 求职进度面板</h3>
      <p>还在用 Excel、笔记本和多个招聘软件管理申请？CareerDesk 把所有公司、岗位和进度放进一张看板，可视化管理，还支持现有表格一键导入。</p>
    </td>
  </tr>
  <tr>
    <td width="100%" valign="top">
      <h3>🔎 公司与岗位调研</h3>
      <p>还在一家一家搜索公司和岗位资料？一次点击完成调研，并把分散的公开信息整理成清晰、有来源引用的报告。</p>
    </td>
  </tr>
  <tr>
    <td width="100%" valign="top">
      <h3>📝 简历适配分析</h3>
      <p>想知道你的简历是否真的适合这个岗位？选择一份简历对照完整 JD，快速看清优势、缺口和有用的修改建议。</p>
    </td>
  </tr>
  <tr>
    <td width="100%" valign="top">
      <h3>🎯 岗位定制练习</h3>
      <p>想提前了解这个岗位可能怎么面？根据你的简历与 JD 生成定制题目，按自己的节奏练习并获得结构化反馈。</p>
    </td>
  </tr>
  <tr>
    <td width="100%" valign="top">
      <h3>🤝 求职智能助手</h3>
      <p>一个人求职难免疲惫。让助手帮你整理岗位、分析投递、规划计划，或只是单纯陪你聊聊天。长期偏好支持多个彼此独立的求职方向，避免混用不同路线的岗位标准和简历侧重；还支持上传 PDF、文档、表格和图片，也可以在输入框直接粘贴截图。</p>
    </td>
  </tr>
  <tr>
    <td width="100%" valign="top">
      <h3>📅 日程与待办</h3>
      <p>把课程、招聘会、笔试、面试和截止日期放进周/月日历。日程支持优先级、每周重复、关联岗位和撞车比较；无具体时间的待办以更小的便签区分，完成后可直接勾选划掉。</p>
    </td>
  </tr>
  <tr>
    <td width="100%" valign="top">
      <h3>🧠 模型由你选择</h3>
      <p>主流云端模型、本地 Ollama、vLLM、SGLang，以及自定义 OpenAI-compatible 接口都能接入；不配置模型也能使用看板、日历等本地功能。</p>
    </td>
  </tr>
</table>

## 🚀 一键安装使用

从 [GitHub Releases](https://github.com/xinhuangcs/CareerDesk/releases) 下载适合你的便捷安装包：

- **macOS Apple Silicon：** `CareerDesk-<版本>-macos-arm64-UNSIGNED.zip`
- **Windows x64：** `CareerDesk-<版本>-windows-x64-UNSIGNED.zip`

### 首次打开需要手动放行一次

本项目没有购买 Apple 和微软的代码签名证书，所以系统会把它当作「来源不明的软件」拦下来。**这是因为没有付费签名，不是因为系统检测到了风险。** 安装包全部由 GitHub Actions 从公开源码自动构建，Release 附有 SHA-256 校验值和构建来源证明，可自行核对。

**macOS**

1. 解压后把 `CareerDesk.app` 拖到「应用程序」文件夹（或桌面等任意位置；数据不跟随 App 移动）
2. 双击打开，会提示无法验证开发者——点「完成」
3. 打开「系统设置」→「隐私与安全性」，向下滚动到「安全性」一栏
4. 找到「已阻止使用 CareerDesk」，点右侧的「仍要打开」
5. 再点一次「仍要打开」并验证身份

**Windows**

1. **先把压缩包完整解压**（放到任意你喜欢的位置都行），不要在压缩包里直接运行
2. 运行 `CareerDesk` 文件夹里的 `CareerDesk.exe`
3. 出现「Windows 已保护你的电脑」时，点「更多信息」
4. 点「仍要运行」

两个系统都只需做一次，之后正常打开即可。

**升级新版本**：直接下载新安装包，按同样方式安装并替换旧版即可；求职数据保存在系统用户数据目录中（不在应用文件夹里），旧数据会自动保留沿用。

**Windows 常见疑问**（以下仅涉及 Windows；macOS 用户无需任何额外操作）

- 文件夹里的 `careerdesk-data(.exe)` 是备份/恢复命令行工具，双击会显示使用说明；日常使用请打开 `CareerDesk`。
- 应用在浏览器里打开时功能完全相同；如果更想要独立的应用窗口，安装 Microsoft Edge WebView2 Runtime 后重新打开即可（缺少该组件时会自动改用浏览器）。
- 想要桌面快捷方式：双击文件夹里的 `Add-Desktop-Shortcut.cmd` 一次；生成的桌面图标可以随意移动。以后挪动了文件夹，再双击一次刷新即可。

### 自定义 OpenAI-compatible 接口（源码运行）

如果模型服务或中转站兼容 OpenAI API，可在项目 `.env` 中配置：

```dotenv
APP_LLM_MODEL=openai_compatible:your-model
APP_LLM_CONTEXT_WINDOW=请填写服务商公布的数值
APP_LLM_MAX_OUTPUT_TOKENS=请填写服务商公布的数值
OPENAI_BASE_URL=https://your-provider.example/v1
OPENAI_API_KEY=your-key
```

完全停止并重新启动 CareerDesk 后生效。服务地址只允许带可选路径的 `http(s)` URL，不能包含凭据、查询参数或 fragment；模型容量必须以服务商文档为准。桌面发行包的模型、凭据与联网权限可在应用设置中管理。

## 🔐 隐私与安全

### 本地日历 MCP

源码安装和桌面发行包提供 `careerdesk-calendar-mcp`，可让 Codex 等本地 MCP 客户端通过标准输入输出管理日程与待办。它复用 CareerDesk 配置的本地用户和数据目录，**仅允许本机 stdio 使用，禁止改成 SSE/HTTP 或暴露到网络**。写入操作使用 revision 防并发覆盖，失败或超时后必须先重新读取再重试。

源码环境可将下面的命令配置为 MCP Server：

```text
<仓库路径>/backend/.venv/bin/python -m careerdesk.mcp.calendar_server
```

可用工具覆盖日程/待办的查询、新建、修改、完成和删除，以及岗位关联与时间冲突查询。删除操作还要求显式传入 `confirm="DELETE"`。桌面发行包中请使用随包附带的 `careerdesk-calendar-mcp` 可执行文件。

### 隐私

你的投递、简历、面试记录、对话和生成产物都保存在自己的电脑上。只有明确使用已授权的外部服务时，完成当次操作所需的材料才会直接发给你配置的大语言模型等服务商；严格离线模式可以暂停全部应用内出网能力。

### 安全

本项目使用 Fable 5 以及 GPT-5.6-sol 进行了多轮 AI 辅助审查。带标签的安装包由 GitHub Actions 从仓库源码构建，并经过发行检查、冻结应用 smoke、SHA-256 和构建来源证明。打包过程因此可以追溯，但这不等于独立安全审计或绝对安全保证。

## 🤝 参与贡献

所有 Issue 和 PR 都非常欢迎。你可以新增一个主题或背景、提出一个功能、修复一个 Bug、帮助测试其他平台、或是提出一个需求。源码运行、整体架构图、本地检查和 PR 流程见 [CONTRIBUTING.md](zh/CONTRIBUTING.md)。

## 📄 许可、署名与免责声明

CareerDesk 按 [MIT License](LICENSE) 开源。第三方库、产品名、模型名、公司名及其他引用材料仍归各自权利人所有；出现在本项目中不代表双方存在关联或背书。桌面发行包仍会单独携带所需的依赖许可证与署名。

本项目在 Fable 5 以及 GPT-5.6-sol 的协助下完成；AI 辅助开发仍可能产生错误。CareerDesk 及其 AI 输出均按现状提供。责任、隐私、联网、未签名发行、安全报告、贡献与第三方权利见[统一声明](zh/DISCLAIMER.md)。
