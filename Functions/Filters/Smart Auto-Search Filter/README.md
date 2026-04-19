# Smart Auto-Search Filter

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Open WebUI](https://img.shields.io/badge/Open%20WebUI-Filter-green)
![Type](https://img.shields.io/badge/Type-Inlet-yellowgreen)
[![Author](https://img.shields.io/badge/author-shakerbr-blue.svg)](https://github.com/shakerbr)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An intelligent inlet filter that uses a micro-agent to determine if native web search is required, protecting Image and Memory tools from context pollution.

---

## ✨ Features

- **Intelligent Routing**: Uses LLM to determine if web search is needed for each user message
- **Context Awareness**: Detects when search is NOT needed (image generation, memory saving, coding tasks)
- **Chain-of-Thought Engine**: Structured prompts for accurate classification decisions
- **JSON Response Parsing**: Extracts reasoning and boolean decision from model output
- **Automatic SearXNG Triggering**: Activates web search when appropriate

---

## 🔧 Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `classification_model` | `str` | `""` | Model ID for routing decisions (blank = current chat model) |

---

## 📖 How to Use

1. **Prerequisite**: Set up [SearXNG](https://github.com/searxng/searxng) as your Open WebUI search provider
2. **Import**: Paste the filter code directly into Open WebUI's Functions section
3. **Enable**: Activate the filter for your desired models/workspace
4. **Automatic**: The filter automatically analyzes each user message

The filter will:
- ✅ Automatically analyze each user message
- ✅ Trigger SearXNG web search when appropriate
- ✅ Print reasoning logs for debugging
- ✅ Protect image/memory tools from unnecessary search activation

---

## 🎯 Use Cases

| Scenario | Search Triggered? |
|----------|-------------------|
| "Generate an image of a sunset" | ❌ No |
| "Remember that my birthday is June 15" | ❌ No |
| "Write a Python function to sort a list" | ❌ No |
| "What's the latest news on AI?" | ✅ Yes |
| "Compare iPhone vs Android 2026" | ✅ Yes |
| "What's the weather today?" | ✅ Yes |

---

## 🖼️ Showcase

![Showcase of Smart Auto-Search Filter](image-placeholder.png)

---

## ⚠️ Requirements

> [!IMPORTANT]
> This filter requires **SearXNG** to be configured as your Open WebUI web search provider. Without SearXNG, the search functionality will not work.

> [!TIP]
> Leave `classification_model` blank to use the currently active chat model for routing decisions. Specify a model ID if you prefer using a faster/smaller model for classification.

---

## 🔍 How It Works

```
User Message → Inlet Filter → Micro-Agent Analysis
                                   ↓
                          Chain-of-Thought Prompting
                                   ↓
                          JSON Response Parsing
                                   ↓
                          ┌─────────────────┐
                          │  Search Needed? │
                          └────────┬────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    ↓                             ↓
               Yes: Trigger                 No: Pass Through
               SearXNG Search               Original Message
```

---

## 📁 File Location

```
Functions/Filters/Smart Auto-Search Filter/
├── README.md
└── smart-auto-search-filter.py
```

---

## 🤝 Contributing

Found a bug or have an improvement? Contributions are welcome! Feel free to submit issues or pull requests.

---

## 📜 License

This project is provided as-is for use with Open WebUI. Modify and distribute freely.