# Puter Models API

![Version](https://img.shields.io/badge/version-1.0-blue)
[![Puter](https://img.shields.io/badge/Puter-AI%20API-purple?logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwL3N2ZyIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJ3aGl0ZSI+PHBhdGggZD0iTTEyIDJDNi40OCAyIDIgNi40OCAyIDEyczQuNDggMTAgMTAgMTAgMTAtNC40OCAxMC0xMFMxNy41MiAyIDEyIDJ6bTAgMThjLTQuNDEgMC04LTMuNTktOC04czMuNTktOCA4LTggOCAzLjU5IDggOC0zLjU5IDgtOCA4eiIvPjwvc3ZnPg==)](https://puter.com)
[![Open WebUI](https://img.shields.io/badge/Open%20WebUI-Pipe-orange)](https://openwebui.com)
[![Author](https://img.shields.io/badge/author-shakerbr-blue.svg)](https://github.com/shakerbr)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A pipe for Open WebUI that integrates [Puter AI API](https://puter.com) — a free, privacy-first cloud platform providing access to multiple state-of-the-art AI models without requiring API keys or subscriptions.

## Overview

This pipe enables Open WebUI to use Puter's AI API, providing access to various language models from providers like OpenAI, Anthropic, Meta, and more — all for free through Puter's generous free tier.

> [!NOTE]
> Puter is a privacy-first, open-source cloud operating system that runs in your browser. It offers free access to multiple AI models as part of its platform. No credit card or subscription required.

## What is Puter?

[Puter](https://puter.com) is a free, privacy-focused cloud platform that provides:

- 🌐 **No Installation Required** — Runs entirely in your browser
- 🔒 **Privacy-First** — Your data stays on your device
- 🤖 **Free AI Access** — Multiple AI models available at no cost
- 💻 **Cloud Desktop** — Full cloud operating system experience
- 🔑 **No API Keys** — Authentication handled through your Puter account

Puter offers access to models from major providers including GPT-4, Claude, Llama, and more, all through a unified interface without managing multiple API subscriptions.

## Features

| Feature | Description |
|---------|-------------|
| 🔍 **Dynamic Model Discovery** | Automatically fetches available models from Puter's models endpoint |
| 🔄 **Fallback Mechanism** | Gracefully falls back to base models endpoint if details endpoint fails |
| 🌐 **Browser User-Agent** | Uses standard browser User-Agent to prevent Cloudflare/WAF blocking |
| 🧠 **System Prompt Handling** | Injects system context into the last user message to bypass API limitations |
| 🔁 **Message Alternation Enforcement** | Ensures strict user/assistant role alternation required by the API |
| 📡 **Streaming Support** | Full streaming response support for real-time token generation |
| 🏷️ **Provider Attribution** | Shows model provider in display name (e.g., "GPT-4 (OpenAI)") |
| ⚙️ **Parameter Passthrough** | Supports temperature, top_p, top_k, max_tokens, stop, presence_penalty, frequency_penalty |

## Configuration

### Valves

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `PUTER_AUTH_TOKEN` | `str` | `""` | Your Puter auth.token from browser Local Storage |

### Getting Your Puter Auth Token

To use this pipe, you'll need to extract your authentication token from Puter's website:

1. **Log in to Puter**:
   - Go to [puter.com](https://puter.com)
   - Sign in or create a free account

2. **Open Developer Tools**:
   - Press `F12` or right-click → "Inspect"
   - Navigate to the **Application** tab (Chrome/Edge) or **Storage** tab (Firefox)

3. **Find Local Storage**:
   - Expand **Local Storage** in the left sidebar
   - Click on `https://puter.com`
   - Find the key named `puter_auth_token` or look for `auth.token` in the stored data

4. **Copy the Token**:
   - Double-click the value to select it
   - Copy the token string (it's typically a long JWT or session identifier)

> [!WARNING]
> Treat your auth token like a password. Never share it publicly or commit it to version control. If compromised, log out of Puter and log back in to generate a new token.

<details>
<summary>📖 Alternative Method: Console Extraction</summary>

If you prefer using the console, paste this in Puter's browser console:

```javascript
// Method 1: Check localStorage directly
console.log(localStorage.getItem('puter_auth_token'));

// Method 2: If Puter stores auth differently
console.log(JSON.parse(localStorage.getItem('puter_auth') || '{}')?.token);
```

Copy the output value and use it as your `PUTER_AUTH_TOKEN`.
</details>

## How to Use

1. **Install the Pipe**: Paste the [`puter-models-api.py`](puter-models-api.py) file into your Open WebUI Functions section

2. **Configure Your Token**: 
   - Open Open WebUI Settings → Functions
   - Find "Puter API" and click the gear icon (⚙️)
   - Paste your Puter auth token into the `PUTER_AUTH_TOKEN` field

3. **Select a Model**: 
   - Start a new chat
   - Select "Puter API" from the model dropdown
   - Choose your preferred model from the dynamically populated list

4. **Chat Normally**: System prompts are automatically handled — just start talking!

## Available Models

Puter provides access to a variety of models from major providers:

| Model Family | Examples |
|--------------|----------|
| **OpenAI GPT** | GPT-4o, GPT-4 Turbo, GPT-3.5 |
| **Anthropic Claude** | Claude 3.5 Sonnet, Claude 3 Opus |
| **Meta Llama** | Llama 3.2, Llama 3.1 |
| **Mistral** | Mistral Large, Mixtral |
| **Google Gemini** | Gemini Pro, Gemini Flash |

> [!TIP]
> The model list is fetched dynamically from Puter's API, so new models are automatically available as Puter adds them! Provider names are shown in parentheses for easy identification.

## Technical Details

### Model Discovery Flow

The pipe fetches models in a two-step fallback process:

1. **Primary Endpoint**: `https://api.puter.com/puterai/chat/models/details`
   - Returns full model metadata including provider info
   
2. **Fallback Endpoint**: `https://api.puter.com/puterai/chat/models`
   - Used if primary endpoint fails (e.g., 404 errors)

### System Prompt Handling

Puter's API may have limitations with system prompts. This pipe works around this by:

1. Extracting all system messages from the conversation
2. Injecting the combined system context into the last user message
3. Wrapping system content in `[System Context/Memory]...[End Context]` markers

This ensures your custom instructions and personality settings work correctly.

### Message Alternation

The API requires strict alternation between user and assistant messages. The pipe:

- Normalizes role names (e.g., `model` → `assistant`)
- Merges consecutive messages from the same role
- Prepends a placeholder if the conversation starts with an assistant message

### Parameter Support

The following OpenAI-compatible parameters are passed through to the API:

- `temperature` — Controls randomness (0.0 to 2.0)
- `top_p` — Nucleus sampling threshold
- `top_k` — Top-k sampling
- `max_tokens` — Maximum response length
- `stop` — Stop sequences
- `presence_penalty` — Penalize repeated topics
- `frequency_penalty` — Penalize repeated tokens

### User-Agent Handling

The pipe includes a standard browser User-Agent header to prevent Cloudflare or WAF (Web Application Firewall) from silently blocking requests. This ensures reliable connectivity to Puter's API.

## Showcase

![Showcase of Puter Models API](image-placeholder.png)

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Puter Token not configured" | Extract and set your auth token in Valves |
| "API Error fetching models" | Verify your token is valid; try logging out and back into Puter |
| "No models found" | Check if Puter services are operational; try refreshing the token |
| Empty responses | Ensure the model ID is correct; some models may have different capabilities |
| Cloudflare/WAF blocking | The pipe includes browser User-Agent; ensure you're using the latest version |

## Requirements

- Open WebUI version `0.6.32` or higher
- Valid Puter account with auth token
- Network access to `api.puter.com`

## Credits

- **Author**: [shakerbr](https://github.com/shakerbr)
- **License**: MIT
- **Puter**: [puter.com](https://puter.com)

---

> [!IMPORTANT]
> This is a community-maintained pipe and is not officially affiliated with Puter. Puter's API and model availability may change. Visit [puter.com](https://puter.com) for the latest information on their services and terms of use.