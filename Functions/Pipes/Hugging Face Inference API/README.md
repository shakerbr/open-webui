# Hugging Face Inference API

![Version](https://img.shields.io/badge/version-1.0-blue)
[![Hugging Face](https://img.shields.io/badge/Hugging%20Face-Inference%20API-yellow?logo=huggingface)](https://huggingface.co/docs/api-inference)
[![Open WebUI](https://img.shields.io/badge/Open%20WebUI-Pipe-orange)](https://openwebui.com)
[![Author](https://img.shields.io/badge/author-shakerbr-blue.svg)](https://github.com/shakerbr)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An internal pipe for Open WebUI that integrates [Hugging Face Serverless Inference API](https://huggingface.co/docs/api-inference) with custom model lists, memory injection, and dynamic parameters.

## Overview

This pipe enables Open WebUI to use Hugging Face's unified Router API, providing access to thousands of state-of-the-art language models — from Llama and Mistral to Qwen and beyond — all through a single, consistent endpoint.

> [!NOTE]
>> Hugging Face's Serverless Inference API offers free access to many models with rate limits. For higher throughput, consider [Hugging Face Inference Endpoints](https://huggingface.co/docs/inference-endpoints).

## Features

| Feature | Description |
|---------|-------------|
| 📋 **Configurable Model List** | Define your own models via comma-separated IDs in Valves |
| 🌐 **Hugging Face Router API** | Uses the unified `router.huggingface.co` inference endpoint |
| 🧠 **System Prompt Handling** | Merges system context into user messages for compatibility |
| 🔁 **Message Alternation Enforcement** | Ensures strict user/assistant role alternation |
| 📡 **Streaming Support** | Full SSE (Server-Sent Events) streaming for real-time responses |
| ⚙️ **Dynamic Parameters** | Passes through temperature, top_p, top_k, max_tokens, etc. |

## Configuration

### Valves

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `HF_TOKEN` | `str` | `""` | Hugging Face API token (required) |
| `HF_MODEL_IDS` | `str` | `"meta-llama/Llama-3.3-70B-Instruct,mistralai/Mistral-7B-Instruct-v0.3,Qwen/Qwen2.5-72B-Instruct"` | Comma-separated model IDs |

### Getting a Hugging Face API Token

To use this pipe, you'll need a Hugging Face Access Token:

1. **Navigate to Hugging Face Settings**:
   - Go to [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
   - Or: Profile → Settings → Access Tokens

2. **Create a new token**:
   - Click **"Create new token"**
   - Give it a descriptive name (e.g., "Open WebUI Inference")

3. **Select token type**:
   - For read-only access to inference APIs, a **"Read"** token is sufficient
   - For accessing gated models, you may need to accept their license on the model page first

4. **Generate and copy the token**:
   - Click **"Generate token"**
   - Copy the token immediately (you won't see it again)

> [!WARNING]
> Treat your API token like a password. Never commit it to version control or share it publicly.

### Rate Limits & Quotas

Hugging Face's Serverless Inference API has the following limits:

| Tier | Rate Limit | Notes |
|------|------------|-------|
| **Free (anonymous)** | ~1,000 requests/month | No token required, heavily rate-limited |
| **Free (with token)** | Higher quotas | Logged-in users get better limits |
| **Pro ($9/month)** | Increased quotas | Priority access to serverless inference |

> [!TIP]
> For production workloads or higher throughput, consider [Hugging Face Inference Endpoints](https://huggingface.co/docs/inference-endpoints) — dedicated, scalable infrastructure you can deploy in seconds.

## How to Use

1. **Install the Pipe**: 
   - Paste the [`hf-inference-api.py`](hf-inference-api.py) file into your Open WebUI Functions section

2. **Configure Your Token**:
   - Open Open WebUI Settings → Functions
   - Find "Hugging Face" and click the gear icon (⚙️)
   - Paste your Hugging Face token into the `HF_TOKEN` field

3. **Customize Models (Optional)**:
   - Edit `HF_MODEL_IDS` to add your preferred models
   - Use full model IDs like `meta-llama/Llama-3.3-70B-Instruct`
   - Separate multiple models with commas

4. **Select a Model**:
   - Start a new chat
   - Select "Hugging Face" from the model dropdown
   - Choose your preferred model from the list

5. **Chat Normally**: System prompts are automatically handled — just start talking!

## Default Models

The pipe comes pre-configured with these high-quality models:

| Model | Size | Description |
|-------|------|-------------|
| **Llama 3.3 70B Instruct** | 70B | Meta's latest instruction-tuned model with excellent reasoning |
| **Mistral 7B Instruct v0.3** | 7B | Fast, efficient, and capable model from Mistral AI |
| **Qwen 2.5 72B Instruct** | 72B | Alibaba's powerful multilingual model |

> [!TIP]
> You can add any model from [Hugging Face Hub](https://huggingface.co/models?pipeline_tag=text-generation) that supports the Inference API. Look for the "Inference API" widget on model pages.

## Technical Details

### System Prompt Handling

The Hugging Face Router API works best with user/assistant message pairs. This pipe handles system prompts by:

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

| Parameter | Description |
|-----------|-------------|
| `temperature` | Controls randomness (0.0 to 2.0) |
| `top_p` | Nucleus sampling threshold |
| `top_k` | Top-k sampling |
| `max_tokens` | Maximum response length |
| `stop` | Stop sequences |
| `presence_penalty` | Penalize repeated topics |
| `frequency_penalty` | Penalize repeated tokens |

## Showcase

![Showcase of Hugging Face Inference API](image-placeholder.png)

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "API Error: 401" | Verify your `HF_TOKEN` is set correctly in Valves |
| "API Error: 403" | Some models require accepting a license; visit the model page first |
| "API Error: 429" | Rate limited — wait and retry, or upgrade to Pro |
| Empty responses | Model may be loading; try again in a few seconds |
| Model not found | Check the model ID format: `org/model-name` |

## Requirements

- Open WebUI version `0.6.32` or higher
- Valid Hugging Face Access Token
- Network access to `router.huggingface.co`
- Access to models (some require license acceptance)

## Credits

- **Author**: [shakerbr](https://github.com/shakerbr)
- **License**: MIT
- **Hugging Face API Docs**: [huggingface.co/docs/api-inference](https://huggingface.co/docs/api-inference)

---

> [!IMPORTANT]
> This is a community-maintained pipe and is not officially affiliated with Hugging Face. Model availability and pricing may change — always check the [official documentation](https://huggingface.co/docs/api-inference) for the latest information.