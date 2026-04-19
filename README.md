# 🛠️ Open WebUI Tools & Functions Collection

[![GitHub stars](https://img.shields.io/github/stars/yourusername/open-webui?style=social)](https://github.com/yourusername/open-webui/stargazers)
[![Open WebUI](https://img.shields.io/badge/Open%20WebUI-Compatible-blueviolet)](https://github.com/open-webui/open-webui)
[![Last Updated](https://img.shields.io/github/last-commit/yourusername/open-webui?color=brightgreen)](https://github.com/yourusername/open-webui/commits/main)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](http://makeapullrequest.com)
[![Author](https://img.shields.io/badge/author-shakerbr-blue.svg)](https://github.com/shakerbr)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> A curated collection of custom tools, functions (actions, filters, pipes), and setups for the [Open WebUI](https://github.com/open-webui/open-webui) ecosystem.

---

## 📖 Introduction

Welcome to the **Open WebUI Tools & Functions Collection** — a community-driven repository of custom extensions, utilities, and integrations designed to enhance your self-hosted Open WebUI experience.

### Who Is This For?

- 🖥️ **Self-hosting enthusiasts** looking to extend Open WebUI capabilities
- 🤖 **Open WebUI users** seeking powerful add-ons for their AI workflows
- 🔧 **AI hobbyists** interested in custom tools and integrations
- 🚀 **Developers** wanting to contribute to the growing Open WebUI ecosystem

---

## 📂 Directory Index

| Category | Name | Description |
|----------|------|-------------|
| **Actions** | | *Message-level widgets for enhanced interactions* |
| | [Smart-Actions-V1](./Functions/Actions/Smart-Actions-V1/) | Translation & DOCX export widget |
| | [Smart-Actions-V2](./Functions/Actions/Smart-Actions-V2/) | Multi-format exports + TTS read-aloud player |
| **Filters** | | *Inlet/outlet processors for request/response handling* |
| | [LangfuseV2](./Functions/Filters/LangfuseV2/) | LLM observability and tracing integration |
| | [Smart Auto-Search Filter](./Functions/Filters/Smart%20Auto-Search%20Filter/) | Intelligent web search routing |
| | [Smart Image Shortcode Renderer](./Functions/Filters/Smart%20Image%20Shortcode%20Renderer/) | Image shortcode → real images conversion |
| **Pipes** | | *Model provider integrations* |
| | [GitHub Models API](./Functions/Pipes/GitHub%20Models%20API/) | GitHub Models integration |
| | [Hugging Face Inference API](./Functions/Pipes/Hugging%20Face%20Inference%20API/) | HF Serverless API integration |
| | [Puter Models API](./Functions/Pipes/Puter%20Models%20API/) | Puter AI integration |
| **Tools** | | *LLM-callable utilities and agents* |
| | [Smart Memory Agent](./Tools/Smart%20Memory%20Agent/) | Human-like memory system for AI |
| **Setups** | | *Configuration templates* |
| | Coming Soon | Pre-configured setup templates (in development) |

---

## 🚀 Installation Guide

Getting started with these tools and functions is straightforward. Follow these steps:

<details>
<summary>📖 Click to expand installation instructions</summary>

### Step 1: Navigate to the Desired Tool
Browse the repository structure above and navigate to the folder containing the tool or function you want to install.

### Step 2: Open the Python File
Each tool/function contains a `.py` file (e.g., `smart-actions-v1.py`). Click to view the raw code.

### Step 3: Copy the Raw Code
- On GitHub: Click the "Raw" button and copy the entire contents
- Or download the file directly

### Step 4: Import into Open WebUI
1. Open your **Open WebUI** instance
2. Navigate to **Admin Panel → Functions** (or **Tools**)
3. Click **Import** or **+ Add**
4. Paste the copied code into the editor
5. Save the function/tool

### Step 5: Configure Valves
Each tool/function has customizable settings called **Valves**. Refer to the individual README in each folder for specific configuration options.

</details>

---

## 📋 Quick Reference

<details>
<summary>🔧 What are Actions, Filters, Pipes, and Tools?</summary>

| Type | Purpose | When It Runs |
|------|---------|--------------|
| **Actions** | Message-level widgets (buttons, UI elements) | User-triggered on specific messages |
| **Filters** | Inlet/outlet processors | Before/after model inference |
| **Pipes** | Model provider integrations | When routing to external APIs |
| **Tools** | LLM-callable utilities | When the AI needs external capabilities |

</details>

---

## 🤝 Contributing & Feedback

We love community contributions! Here's how you can help:

### ⭐ Show Your Support
If you find this repository useful, please consider **starring** it — it helps others discover these tools!

### 🐛 Report Issues
Found a bug or have a feature request? [Open an issue](https://github.com/yourusername/open-webui/issues) with:
- Clear description of the problem/suggestion
- Steps to reproduce (for bugs)
- Your Open WebUI version

### 🔀 Submit Pull Requests
Have an improvement or new tool to share?
1. Fork the repository
2. Create a feature branch
3. Submit a pull request

### 💬 Share Feedback
Your feedback helps improve these tools for everyone. Don't hesitate to share:
- How you're using these tools
- What's working well
- What could be improved

---

## 📜 License

This repository is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [Open WebUI](https://github.com/open-webui/open-webui) — The amazing platform these tools are built for
- All contributors who have helped improve this collection

---

<p align="center">
  <strong>Made with ❤️ for the Open WebUI community</strong>
</p>