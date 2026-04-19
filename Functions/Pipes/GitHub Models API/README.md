# GitHub Models API

![Version](https://img.shields.io/badge/version-1.0-blue)
[![GitHub Models](https://img.shields.io/badge/GitHub-Models-blue?logo=github)](https://github.com/marketplace/models)
[![Open WebUI](https://img.shields.io/badge/Open%20WebUI-Pipe-orange)](https://openwebui.com)
[![Author](https://img.shields.io/badge/author-shakerbr-blue.svg)](https://github.com/shakerbr)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A pipe for Open WebUI that integrates [GitHub Models](https://github.com/marketplace/models) — GitHub's free AI model inference service. Dynamically fetches all available models and intelligently handles system prompts.

## Overview

This pipe enables Open WebUI to use GitHub's Models API, providing access to a wide range of state-of-the-art language models including GPT-4, Llama, Phi, and more — all for free with a GitHub Personal Access Token.

> [!NOTE]
> GitHub Models is currently in beta and free to use. Rate limits and availability may change. Visit [GitHub Models](https://github.com/marketplace/models) for the latest information.

## Features

| Feature | Description |
|---------|-------------|
| 🔍 **Dynamic Model Discovery** | Automatically fetches available models from GitHub's catalog endpoint |
| 🔄 **Fallback Endpoint** | Gracefully falls back to Azure inference endpoint if catalog fails |
| 🧠 **System Prompt Handling** | Injects system context into the last user message to bypass API limitations |
| 🔁 **Message Alternation Enforcement** | Ensures strict user/assistant role alternation required by the API |
| 📡 **Streaming Support** | Full streaming response support for real-time token generation |
| ⚙️ **Parameter Passthrough** | Supports temperature, top_p, max_tokens, stop, presence_penalty, frequency_penalty |

## Configuration

### Valves

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `GITHUB_TOKEN` | `str` | `""` | GitHub Personal Access Token (PAT) with `read:model` scope |

### Getting a GitHub Personal Access Token

To use this pipe, you'll need a GitHub Personal Access Token (PAT) with the appropriate permissions:

1. **Navigate to GitHub Settings**:
   - Go to [github.com/settings/tokens](https://github.com/settings/tokens)
   - Or: Profile → Settings → Developer settings → Personal access tokens → Tokens (classic)

2. **Create a new token**:
   - Click **"Generate new token (classic)"**
   - Give it a descriptive name (e.g., "Open WebUI GitHub Models")

3. **Select required scopes**:
   - ✅ `read:model` — Required to access GitHub Models API
   - This is the minimum scope needed; no additional permissions are required

4. **Generate and copy the token**:
   - Click **"Generate token"**
   - Copy the token immediately (you won't see it again)

> [!WARNING]
> Treat your PAT like a password. Never commit it to version control or share it publicly.

## How to Use

1. **Install the Pipe**: Paste the [`github-models-api.py`](github-models-api.py) file into your Open WebUI Functions section

2. **Configure Your Token**: 
   - Open Open WebUI Settings → Functions
   - Find "GitHub Models API" and click the gear icon (⚙️)
   - Paste your GitHub PAT into the `GITHUB_TOKEN` field

3. **Select a Model**: 
   - Start a new chat
   - Select "GitHub API" from the model dropdown
   - Choose your preferred model from the dynamically populated list

4. **Chat Normally**: System prompts are automatically handled — just start talking!

## Available Models

GitHub Models provides access to a variety of models including:

| Model Family | Examples |
|--------------|----------|
| **OpenAI GPT** | GPT-4o, GPT-4o-mini, GPT-4 Turbo |
| **Meta Llama** | Llama 3.2, Llama 3.1, Llama 2 |
| **Microsoft Phi** | Phi-4, Phi-3.5, Phi-3 |
| **Mistral** | Mistral Large, Mistral Small, Codestral |
| **Cohere** | Command R, Command R+ |

> [!TIP]
> The model list is fetched dynamically, so new models are automatically available as GitHub adds them!

## Technical Details

### System Prompt Handling

GitHub Models API has limitations with system prompts. This pipe works around this by:

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

## Showcase

![Showcase of GitHub Models API](image-placeholder.png)

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "GitHub Token not configured" | Set your PAT in the Valves configuration |
| "API Error fetching models" | Verify your token has `read:model` scope |
| "No models found" | Check if GitHub Models is available in your region |
| Empty responses | Ensure the model ID is correct; some models may have different capabilities |

## Requirements

- Open WebUI version `0.6.32` or higher
- Valid GitHub Personal Access Token with `read:model` scope
- Network access to `models.github.ai` and `models.inference.ai.azure.com`

## Credits

- **Author**: [shakerbr](https://github.com/shakerbr)
- **License**: MIT
- **GitHub Models**: [github.com/marketplace/models](https://github.com/marketplace/models)

---

> [!IMPORTANT]
> This is an community-maintained pipe and is not officially affiliated with GitHub or Microsoft.