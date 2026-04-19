"""
title: GitHub Models API
description: Pipe for GitHub Models API. Dynamically fetches all models and bypasses system prompt issues.
author: shakerbr
author_url: https://github.com/shakerbr
version: 1.0
license: MIT
required_open_webui_version: 0.6.32
"""

from typing import Optional, Union, Generator, Iterator
from pydantic import BaseModel, Field
import requests
import json


class Pipe:
    class Valves(BaseModel):
        GITHUB_TOKEN: str = Field(
            default="", description="Your GitHub Personal Access Token (PAT)"
        )

    def __init__(self):
        self.type = "pipe"
        self.id = "github_models_api"
        self.name = "GitHub API "
        self.valves = self.Valves()

    def pipes(self):
        if not self.valves.GITHUB_TOKEN:
            return [
                {
                    "id": "error",
                    "name": "GitHub Token not configured. Please set it in Valves.",
                }
            ]

        try:
            # First, attempt to use the GitHub catalog endpoint to fetch available models dynamically
            url = "https://models.github.ai/catalog/models"
            headers = {
                "Authorization": f"Bearer {self.valves.GITHUB_TOKEN}",
                "X-GitHub-Api-Version": "2022-11-28",
                "Accept": "application/vnd.github+json",
            }

            r = requests.get(url, headers=headers)

            # If standard catalog endpoint fails, fallback to Azure inference endpoint format
            if not r.ok:
                url = "https://models.inference.ai.azure.com/models"
                headers = {
                    "Authorization": f"Bearer {self.valves.GITHUB_TOKEN}",
                    "Accept": "application/json",
                }
                r = requests.get(url, headers=headers)

            r.raise_for_status()
            data = r.json()

            # Handle different possible JSON formats (GitHub list vs OpenAI standard 'data' array)
            models_list = (
                data.get("data", [])
                if isinstance(data, dict)
                else data if isinstance(data, list) else []
            )

            available_models = []
            for m in models_list:
                model_id = m.get("id", m.get("name"))
                if not model_id:
                    continue
                # Some APIs return a 'friendly_name', fallback to ID if needed
                model_name = m.get("friendly_name", m.get("name", model_id))
                available_models.append({"id": model_id, "name": model_name})

            if not available_models:
                return [
                    {"id": "error", "name": "No models found or empty list returned."}
                ]

            return available_models

        except Exception as e:
            return [{"id": "error", "name": f"API Error fetching models: {str(e)}"}]

    def pipe(self, body: dict, __user__: dict) -> Union[str, Generator, Iterator]:
        if not self.valves.GITHUB_TOKEN:
            return "Error: GITHUB_TOKEN is not configured in Valves. Please set it via Open WebUI settings."

        messages = body.get("messages", [])
        system_text = ""
        processed_messages = []

        # 1. Extract system messages & normalize roles
        for msg in messages:
            role = msg.get("role", "user")
            content = str(msg.get("content", ""))

            if role == "system":
                system_text += content + "\n\n"
            else:
                norm_role = "assistant" if role == "model" else role
                processed_messages.append({"role": norm_role, "content": content})

        # 2. Enforce strict alternation
        alternating_messages = []
        for msg in processed_messages:
            if not alternating_messages:
                if msg["role"] == "assistant":
                    alternating_messages.append(
                        {
                            "role": "user",
                            "content": "[Conversation started by assistant]",
                        }
                    )
                alternating_messages.append(msg)
            else:
                last_msg = alternating_messages[-1]
                if last_msg["role"] == msg["role"]:
                    last_msg["content"] += "\n\n" + msg["content"]
                else:
                    alternating_messages.append(msg)

        # 3. Inject system/memory context
        if system_text and alternating_messages:
            for i in range(len(alternating_messages) - 1, -1, -1):
                if alternating_messages[i]["role"] == "user":
                    original = alternating_messages[i]["content"]
                    alternating_messages[i][
                        "content"
                    ] = f"[System Context/Memory]\n{system_text.strip()}\n[End Context]\n\n{original}"
                    break
        elif system_text and not alternating_messages:
            alternating_messages.append(
                {
                    "role": "user",
                    "content": f"[System Context/Memory]\n{system_text.strip()}\n[End Context]",
                }
            )

        # Strip the internal Open WebUI prefix from the model name
        model_id = body.get("model", "")
        if "." in model_id:
            # Split only on the first dot to prevent breaking model IDs that contain dots
            model_id = model_id.split(".", 1)[-1]

        # 4. Build payload with dynamic parameter passthrough
        payload = {
            "model": model_id,
            "messages": alternating_messages,
            "stream": body.get("stream", True),
        }

        # Dynamically inject allowed UI parameters
        allowed_params = [
            "temperature",
            "top_p",
            "top_k",
            "max_tokens",
            "stop",
            "presence_penalty",
            "frequency_penalty",
        ]
        for param in allowed_params:
            if param in body:
                payload[param] = body[param]

        headers = {
            "Authorization": f"Bearer {self.valves.GITHUB_TOKEN}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        # 5. Execute request with UTF-8 encoding
        url = "https://models.github.ai/inference/chat/completions"
        try:
            r = requests.post(
                url, headers=headers, json=payload, stream=payload["stream"]
            )
            r.raise_for_status()
            r.encoding = "utf-8"

            if payload["stream"]:

                def generate():
                    for chunk in r.iter_lines():
                        if chunk:
                            line = chunk.decode("utf-8")
                            if line.startswith("data: ") and line != "data: [DONE]":
                                try:
                                    data = json.loads(line[6:])
                                    delta = data["choices"][0].get("delta", {})
                                    if "content" in delta:
                                        yield delta["content"]
                                except Exception:
                                    continue

                return generate()
            else:
                return r.json()["choices"][0]["message"]["content"]

        except Exception as e:
            return f"API Error: {str(e)}\nDetails: {r.text if 'r' in locals() else ''}"
