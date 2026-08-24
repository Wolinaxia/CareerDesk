<p align="center">
  <a href="../README.md">简体中文</a> · <strong>English</strong>
</p>

<p align="center">
  <img src="../frontend/public/logo-light-512.png" alt="CareerDesk logo" width="112" />
</p>

<h1 align="center">CareerDesk: Your Personal Career Assistant</h1>

<p align="center">
  <strong>An AI-agent-assisted workspace for managing your job applications, completely free and open source.</strong><br />
  I built this for my own job hunt this year, and open-sourced it hoping it helps you with yours.<br />
  May we all get off to a winning start this recruiting season.
</p>

<p align="center">
  <a href="../backend/pyproject.toml"><img alt="Python 3.12–3.13" src="https://img.shields.io/badge/Python-3.12%E2%80%933.13-3776AB?style=for-the-badge&amp;logo=python&amp;logoColor=white" /></a>
  <a href="../backend/"><img alt="Backend FastAPI" src="https://img.shields.io/badge/Backend-FastAPI-009688?style=for-the-badge&amp;logo=fastapi&amp;logoColor=white" /></a>
  <a href="../frontend/"><img alt="Frontend React 19" src="https://img.shields.io/badge/Frontend-React%2019-61DAFB?style=for-the-badge&amp;logo=react&amp;logoColor=20232A" /></a>
  <br />
  <a href="../backend/pyproject.toml"><img alt="Version 1.0.2" src="https://img.shields.io/badge/Version-v1.0.2-EA6B38?style=for-the-badge" /></a>
  <a href="https://github.com/xinhuangcs/CareerDesk/actions/workflows/unsigned-release.yml"><img alt="Build GitHub Actions" src="https://img.shields.io/badge/Build-GitHub%20Actions-6E78FF?style=for-the-badge&amp;logo=githubactions&amp;logoColor=white" /></a>
  <a href="../LICENSE"><img alt="License MIT" src="https://img.shields.io/badge/License-MIT-E1B800?style=for-the-badge" /></a>
</p>

<p align="center">
  <a href="#-what-is-careerdesk">What Is CareerDesk?</a> ·
  <a href="#-key-features">Key Features</a> ·
  <a href="#-install-and-get-started">Quick Start</a> ·
  <a href="#-privacy-and-security">Privacy &amp; Security</a> ·
  <a href="#-contributing">Contributing</a>
</p>

---

## 🧭 What Is CareerDesk?

CareerDesk is a completely free and open-source workspace for managing your job applications. It combines visual application tracking with a personal application assistant that answers questions about your recruiting season from your own records, including application analysis, weekly planning, interview reflection, and emotional support. A set of built-in deterministic workflows handles company and role research, résumé fit analysis, question-set generation, and mock interviews.

> CareerDesk is a local desktop application, not a hosted web service or an automated job-application tool.

https://github.com/user-attachments/assets/5230d010-0f2d-493e-b088-3bbbd7969572

<p align="center"><sub>A short walkthrough of the board, research, and the assistant.</sub></p>

## ✨ Key Features

<table>
  <tr>
    <td width="100%" valign="top">
      <h3>📊 Job Application Progress Board</h3>
      <p>Still managing applications across spreadsheets, notes, and multiple job platforms? Put every company, role, and stage on one visual board—and import your existing files in one go.</p>
    </td>
  </tr>
  <tr>
    <td width="100%" valign="top">
      <h3>🔎 Company and Role Research</h3>
      <p>Tired of researching companies one by one? Complete company and role research with one click, then get a clear report with source citations.</p>
    </td>
  </tr>
  <tr>
    <td width="100%" valign="top">
      <h3>📝 Résumé Fit Analysis</h3>
      <p>Wonder whether your résumé really fits the role? Compare it with the full job description to uncover strengths, gaps, and useful edits.</p>
    </td>
  </tr>
  <tr>
    <td width="100%" valign="top">
      <h3>🎯 Role-Specific Practice</h3>
      <p>Want to know what the interview might ask? Generate questions from your résumé and JD, practise at your own pace, and receive structured feedback.</p>
    </td>
  </tr>
  <tr>
    <td width="100%" valign="top">
      <h3>🤝 Job Application Assistant</h3>
      <p>A recruiting season can feel exhausting when you face it alone. Let the assistant organize roles, analyse applications, make plans, or simply keep you company for a chat. Long-term preferences support independent career tracks, preventing role criteria and résumé emphasis from being blended across paths. Upload PDFs, documents, workbooks, and images, or paste screenshots directly into the composer.</p>
    </td>
  </tr>
  <tr>
    <td width="100%" valign="top">
      <h3>📅 Calendar and To-Dos</h3>
      <p>Keep classes, career fairs, assessments, interviews, and deadlines in week or month views. Events support priorities, weekly recurrence, linked roles, and conflict comparison; timeless to-dos use smaller notes and can be checked off with a strike-through.</p>
    </td>
  </tr>
  <tr>
    <td width="100%" valign="top">
      <h3>🧠 Your Choice of Model</h3>
      <p>Connect mainstream cloud models, local Ollama, vLLM, and SGLang, or a custom OpenAI-compatible endpoint. Even without a model, local features such as the board and calendar remain available.</p>
    </td>
  </tr>
</table>

## 🚀 Install and Get Started

Download the appropriate convenience build from [GitHub Releases](https://github.com/xinhuangcs/CareerDesk/releases):

- **macOS Apple Silicon:** `CareerDesk-<version>-macos-arm64-UNSIGNED.zip`
- **Windows x64:** `CareerDesk-<version>-windows-x64-UNSIGNED.zip`

### Allow it through on first launch

This project does not buy Apple or Microsoft code-signing certificates, so both systems treat the app as coming from an unidentified developer. **You are seeing this because the build is unsigned, not because your system detected anything harmful.** Every build is produced by GitHub Actions from public source, and each release ships SHA-256 checksums and a build attestation you can verify yourself.

**macOS**

1. Unzip and move `CareerDesk.app` into your Applications folder (or anywhere you like — your data never moves with the app)
2. Double-click it. macOS says the developer cannot be verified — click **Done**
3. Open **System Settings → Privacy & Security**, scroll to the **Security** section
4. Find "CareerDesk was blocked" and click **Open Anyway**
5. Click **Open Anyway** once more and authenticate

**Windows**

1. **Extract the whole archive first** (any location works) — do not run it from inside the zip
2. Run `CareerDesk.exe` inside the `CareerDesk` folder
3. When "Windows protected your PC" appears, click **More info**
4. Click **Run anyway**

Both are one-time steps.

**Upgrading:** simply download the new build and install it the same way, replacing the old one; your data lives in the system user data directory (not in the app folder) and carries over automatically.

**Windows-only notes** (macOS users need none of this)

- `careerdesk-data(.exe)` in the folder is the backup/restore command-line tool; double-clicking it shows usage. Open `CareerDesk` for everyday use.
- The browser mode is fully functional; if you would rather have a standalone app window, install the Microsoft Edge WebView2 Runtime and reopen (the browser is used automatically when that component is missing).
- For a desktop shortcut, double-click `Add-Desktop-Shortcut.cmd` inside the folder once; the icon it creates can be moved anywhere. Re-run it whenever you move the folder itself.

### Custom OpenAI-compatible endpoint (source checkout)

If your model service or gateway implements the OpenAI API, configure the project `.env` file:

```dotenv
APP_LLM_MODEL=openai_compatible:your-model
APP_LLM_CONTEXT_WINDOW=use-the-provider-documented-value
APP_LLM_MAX_OUTPUT_TOKENS=use-the-provider-documented-value
OPENAI_BASE_URL=https://your-provider.example/v1
OPENAI_API_KEY=your-key
```

Stop CareerDesk completely and restart it for the change to take effect. The endpoint must be an `http(s)` URL with an optional path and no embedded credentials, query parameters, or fragment. Use capacity values documented by the provider. Desktop builds expose model, credential, and network-permission controls in Settings.

## 🔐 Privacy and Security

### Local calendar MCP

Source installations and desktop builds include `careerdesk-calendar-mcp`, which lets local MCP clients such as Codex manage calendar events and to-dos over standard input/output. It reuses CareerDesk's configured local user and data directory. **It is restricted to local stdio and must never be changed to SSE/HTTP or exposed on a network.** Writes use revisions to prevent concurrent overwrites; after an error or timeout, read the item again before retrying.

For a source checkout, configure the following command as an MCP server:

```text
<repository>/backend/.venv/bin/python -m careerdesk.mcp.calendar_server
```

The tools cover listing, creating, updating, completing, and deleting events and to-dos, plus linked-role and conflict queries. Deletion additionally requires an explicit `confirm="DELETE"`. For desktop distributions, use the bundled `careerdesk-calendar-mcp` executable.

### Local resume MCP

Source installations and desktop builds include `careerdesk-resume-mcp`, which lets local MCP clients such as Codex read job descriptions and read or write résumé text over standard input/output. It reuses CareerDesk's configured local user and data directory. **It is restricted to local stdio and must never be changed to SSE/HTTP or exposed on a network.** Résumé names are unique and creating one never overwrites an existing name; replacing résumé text requires the `expected_content_hash` returned by the matching read and fails outright once the content has changed. Writes are not safely retryable: after an error or timeout, read the résumé list and the application binding again before retrying.

For a source checkout, configure the following command as an MCP server:

```text
<repository>/backend/.venv/bin/python -m careerdesk.mcp.resume_server
```

When `save_resume` archives a local source file, it can read only directories allowed by `APP_RESUME_MCP_ARCHIVE_SOURCE_ROOTS`, which defaults to `~/Desktop`, `~/Documents`, and `~/Downloads`.

Seven tools are available: `list_applications`, `get_application_jd`, `list_resumes`, `get_resume_text`, and `get_application_resume` read applications and résumés, and the JD is never truncated; `save_resume` creates a new résumé and can archive its source file; `update_resume_text` replaces the text against its content hash. A newly created résumé is left with a pending annotation status, so run résumé annotation from the CareerDesk UI. For desktop distributions, use the bundled `careerdesk-resume-mcp` executable.

### Privacy

Your applications, résumés, interview notes, conversations, and generated artifacts stay on your computer. Only when you explicitly use an authorized external service is the material required for that operation sent to the LLM or other provider you configured. Strict offline mode can pause all in-app network capabilities.

### Security

The codebase has gone through multiple AI-assisted review rounds using Fable 5 and GPT-5.6-sol. Tagged builds come from repository source through GitHub Actions, with release checks, frozen-app smoke tests, SHA-256 checksums, and build attestation. This makes packaging traceable but is not an independent security audit or a guarantee.

## 🤝 Contributing

Every Issue and PR is welcome. Add a theme or background, propose a feature, fix a bug, help test another platform, or simply tell us what you need. Source setup, the architecture diagram, local checks, and the PR workflow are in [CONTRIBUTING.md](../CONTRIBUTING.md).

## 📄 License, Attribution, and Disclaimer

CareerDesk is released under the [MIT License](../LICENSE). Third-party libraries, product names, model names, company names, and other referenced materials remain the property of their respective owners; their inclusion does not imply affiliation or endorsement. Required dependency licenses and attribution remain bundled separately with desktop distributions.

This project was developed with assistance from Fable 5 and GPT-5.6-sol; AI-assisted development can still produce mistakes. CareerDesk and its AI output are provided as-is. See the [consolidated notice](../DISCLAIMER.md) for liability, privacy, network access, unsigned builds, security reporting, contributions, and third-party rights.
