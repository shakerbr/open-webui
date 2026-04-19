# Smart Actions V1

[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/shakerbr)
[![Open WebUI](https://img.shields.io/badge/Open%20WebUI-0.6.32%2B-purple.svg)](https://openwebui.com)
![Open WebUI](https://img.shields.io/badge/Open%20WebUI-Action-darkblue)
[![Author](https://img.shields.io/badge/author-shakerbr-blue.svg)](https://github.com/shakerbr)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> A universal multi-tool widget framework for Open WebUI that provides message actions for translation and document export capabilities.

---

## Overview

Smart Actions V1 is an elegant action plugin that extends Open WebUI with powerful message manipulation capabilities. Designed for self-hosting enthusiasts who demand both functionality and aesthetics, this plugin seamlessly integrates into your workflow with theme-aware widgets and intelligent language detection.

---

## Features

### 🌐 Smart Translation
Translates messages to any language using your active chat model. Supports complex markdown content and preserves formatting throughout the translation process.

### 📄 DOCX Export
Converts messages to professionally formatted Word documents with full markdown rendering. Perfect for archiving conversations or sharing content externally.

### 🔤 RTL Language Support
Automatically detects and properly formats Right-to-Left languages including:
- Arabic (العربية)
- Hebrew (עברית)
- Kurdish (کوردی)
- Persian (فارسی)
- Urdu (اردو)

### 💻 Code Block Protection
Intelligently preserves code blocks during translation, ensuring your code snippets remain intact and unmodified.

### 🎨 Theme Awareness
Automatic light/dark theme detection and adaptation. Widgets seamlessly blend with your Open WebUI interface preferences.

### 🖱️ Interactive Menu
Clean, user-friendly input dialog for quick action selection without cluttering your interface.

---

## Configuration

### Valves

Configure the plugin through Open WebUI's valve settings:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `TRANSLATION_MODEL` | `str` | `""` | Model ID for translation. Leave blank to use the active chat model. |

> **💡 Tip**: Leaving `TRANSLATION_MODEL` empty allows the plugin to use your currently selected model, providing a seamless experience without additional configuration.

---

## How to Use

1. **Activate the Action**: Click the action button (✨) on any message in your chat

2. **Choose Your Action**:
   - **Translate**: Type a language name (e.g., `Arabic`, `French`, `Spanish`, `Kurdish`)
   - **Export**: Type `docx` to download the message as a Word document

3. **View Results**: 
   - Translations appear in an elegant widget with copy functionality
   - DOCX files download automatically with markdown preserved

### Translation Widget Features

- One-click copy to clipboard
- Full markdown rendering support
- RTL text automatic alignment
- Responsive design for all screen sizes

---

## Showcase

![Showcase of Smart Actions V1](image-placeholder.png)

> 📸 *Screenshots demonstrating the plugin in action*

---

## Technical Details

### Requirements

- **Open WebUI**: Version 0.6.32 or higher
- **No external dependencies**: Uses only Open WebUI's built-in capabilities

### Architecture

```
Smart Actions V1
├── Translation Engine (uses active model API)
├── DOCX Generator (client-side HTML-to-DOCX conversion)
├── RTL Detector (Unicode-based script analysis)
└── Theme Adapter (CSS custom properties)
```

---

## Installation

Simply paste the plugin code directly into your Open WebUI Functions section. No pip installs, no external dependencies—pure Open WebUI integration.

1. Navigate to **Admin Panel → Functions**
2. Click **+ Add Function**
3. Paste the [`smart-actions-v1.py`](smart-actions-v1.py) content
4. Save and activate the function

---

## Extensibility

Smart Actions V1 is designed as a framework for easy extension. The modular architecture allows adding new actions by implementing the action routing pattern. Future versions may include additional export formats and transformation capabilities.

---

## Contributing

Contributions are welcome! Whether it's bug reports, feature requests, or pull requests—let's make this plugin better together.

---

## License

This project is licensed under the MIT License—feel free to use, modify, and distribute as needed.

---

## Author

**shakerbr**  
[GitHub](https://github.com/shakerbr)

---

> Made with ❤️ for the Open WebUI community