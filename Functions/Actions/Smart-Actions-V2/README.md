# Smart Actions V2

[![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)](https://github.com/shakerbr)
[![Open WebUI](https://img.shields.io/badge/Open%20WebUI-0.6.32%2B-purple.svg)](https://openwebui.com)
![Open WebUI](https://img.shields.io/badge/Open%20WebUI-Action-darkblue)
[![Author](https://img.shields.io/badge/author-shakerbr-blue.svg)](https://github.com/shakerbr)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> An enhanced multi-tool widget framework for Open WebUI featuring translation, multi-format exports, and an advanced TTS Read-Aloud player with word/paragraph highlighting.

---

## Overview

Smart Actions V2 is a comprehensive action plugin that significantly extends Open WebUI's message manipulation capabilities. Building upon the foundation of V1, this version introduces extensive export format support and a feature-rich Text-to-Speech read-aloud player. Designed for self-hosting enthusiasts who demand both power and elegance, this plugin delivers theme-aware widgets with intelligent context-aware filename generation.

---

## Features

### 🌐 Smart Translation
Translates messages to any language using your active chat model or a dedicated translation model. Supports complex markdown content, preserves formatting, and includes full RTL language support.

### 📄 DOCX Export
Converts messages to professionally formatted Word documents with full markdown rendering. Perfect for archiving conversations or sharing content externally with proper formatting intact.

### 📝 Markdown Export
Export messages as clean `.md` files with preserved markdown formatting. Ideal for documentation workflows and note-taking applications.

### 💻 Code Block Export
Export code blocks by language with intelligent detection:
- `py` → Python scripts
- `js` → JavaScript files
- `html` → HTML documents
- `css` → Stylesheets
- And more languages supported!

When multiple code blocks exist, an interactive selection dialog allows you to choose which blocks to export.

### 🌐 Web Bundle Export
Bundle web project files (HTML + CSS + JS) into a convenient ZIP archive. Perfect for exporting complete web projects from chat conversations.

### 📊 Text Format Exports
Export content in various text-based formats:
- `txt` → Plain text
- `json` → JSON data
- `csv` → Comma-separated values
- `xml` → XML documents
- `yaml` → YAML configuration
- `toml` → TOML configuration

### 🎧 TTS Read-Aloud Player
An advanced Text-to-Speech audio player featuring:
- **Word Highlighting**: Real-time word-by-word highlighting during playback
- **Paragraph Tracking**: Visual paragraph navigation and highlighting
- **Voice Selection**: Multiple voice options (configurable via Valves)
- **Playback Controls**: Play, pause, and navigation features
- **Theme Integration**: Seamless light/dark theme adaptation

### 🏷️ Smart Filename Generation
Intelligently derives filenames from chat context, ensuring exported files have meaningful names based on conversation content.

### 🖱️ User Selection Dialogs
Interactive prompts when multiple options are available, such as selecting from multiple code blocks in a single message.

### 🎨 Theme Awareness
Automatic light/dark theme detection and adaptation. All widgets seamlessly blend with your Open WebUI interface preferences.

---

## Configuration

### Valves

Configure the plugin through Open WebUI's valve settings:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `TRANSLATION_MODEL` | `str` | `""` | Model ID for translation. Leave blank to use the active chat model. |
| `TTS_API_BASE_URL` | `str` | `""` | TTS API base URL. Leave blank to use Open WebUI's built-in TTS capabilities. |
| `TTS_API_KEY` | `str` | `""` | TTS API key for external services. Leave blank to use session token authentication. |
| `TTS_DEFAULT_VOICE` | `str` | `"alloy"` | Default TTS voice for audio playback. |
| `TTS_DEFAULT_MODEL` | `str` | `"tts-1"` | Default TTS model identifier. |
| `TTS_VOICES` | `str` | `"alloy,echo,fable,onyx,nova,shimmer"` | Comma-separated list of available TTS voices. |

> **💡 Tip**: The default TTS configuration works out-of-the-box with Open WebUI's built-in TTS. Only configure external TTS API settings if you need custom voice synthesis services.

---

## How to Use

1. **Activate the Action**: Click the action button (✨) on any message in your chat

2. **Choose Your Action** by typing one of the following triggers:

   | Trigger | Action |
   |---------|--------|
   | Language name (e.g., `Arabic`, `French`, `Spanish`) | Translate message |
   | `docx` | Export as Word document |
   | `md` | Export as Markdown file |
   | `py`, `js`, `html`, `css`, etc. | Export code blocks by language |
   | `web` | Bundle web files as ZIP |
   | `txt`, `json`, `csv`, `xml`, `yaml`, `toml` | Export in text format |
   | `read` or `tts` | Launch read-aloud player |

3. **View Results**:
   - Translations appear in an elegant widget with copy functionality
   - Files download automatically with smart filenames
   - TTS player opens with word/paragraph highlighting

---

## Showcase

![Showcase of Smart Actions V2](image-placeholder.png)

> 📸 *Screenshots demonstrating the plugin in action*

---

## Technical Details

### Requirements

- **Open WebUI**: Version 0.6.32 or higher
- **No external dependencies**: Uses Open WebUI's built-in capabilities for core features
- **Optional**: External TTS API for custom voice synthesis

### Architecture

```
Smart Actions V2
├── Translation Engine (uses active model or configured model API)
├── Export Modules
│   ├── DOCX Generator (client-side HTML-to-DOCX conversion)
│   ├── Markdown Exporter
│   ├── Code Block Extractor
│   ├── Web Bundle Packager (ZIP creation)
│   └── Text Format Exporters (txt, json, csv, xml, yaml, toml)
├── TTS Read-Aloud Player
│   ├── Audio Streaming
│   ├── Word Highlighting Engine
│   └── Paragraph Navigation
├── Smart Filename Generator
│   └── Context-aware naming from chat history
└── UI Components
    ├── Theme Detection
    ├── Selection Dialogs
    └── RTL Support Layer
```

---

## Comparison with V1

| Feature | V1 | V2 |
|---------|:--:|:--:|
| Translation | ✅ | ✅ |
| RTL Support | ✅ | ✅ |
| DOCX Export | ✅ | ✅ |
| Markdown Export | ❌ | ✅ |
| Code Block Export | ❌ | ✅ |
| Web Bundle Export | ❌ | ✅ |
| Text Format Exports | ❌ | ✅ |
| TTS Read-Aloud | ❌ | ✅ |
| Word Highlighting | ❌ | ✅ |
| Smart Filenames | ❌ | ✅ |
| Selection Dialogs | ❌ | ✅ |

---

## Installation

> **📋 Note**: This plugin is designed for Open WebUI. Simply paste the plugin code into your Open WebUI Functions section.

1. Navigate to **Admin Panel → Functions** in Open WebUI
2. Click **+** to create a new function
3. Paste the plugin code
4. Save and enable the function
5. Configure Valves as needed

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Author

Created by **[@shakerbr](https://github.com/shakerbr)**

---

> Made with ❤️ for the self-hosting community