"""
title: Puter Models API
description: Pipe for Puter API. Dynamically fetches all models, handles streaming, and bypasses system prompt issues.
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
        PUTER_AUTH_TOKEN: str = Field(
            default="", description="Your Puter auth.token from Local Storage"
        )

    def __init__(self):
        self.type = "pipe"
        self.id = "puter_models_api"
        self.name = "Puter API "
        self.valves = self.Valves()

    def pipes(self):
        if not self.valves.PUTER_AUTH_TOKEN:
            return [
                {
                    "id": "error",
                    "name": "Puter Token not configured. Please set it in Valves.",
                }
            ]

        try:
            # We hit Puter's native details endpoint. We add a standard browser User-Agent
            # to prevent Cloudflare/WAF from silently returning empty bot-responses.
            url = "https://api.puter.com/puterai/chat/models/details"
            headers = {
                "Authorization": f"Bearer {self.valves.PUTER_AUTH_TOKEN}",
                "Accept": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            }

            r = requests.get(url, headers=headers)

            # If the primary details endpoint 404s, fallback to the base models endpoint
            if not r.ok:
                url = "https://api.puter.com/puterai/chat/models"
                r = requests.get(url, headers=headers)

            r.raise_for_status()
            data = r.json()

            # Safely extract the array no matter how Puter wraps it
            if isinstance(data, list):
                models_list = data
            elif isinstance(data, dict):
                # Try common API wrapper keys just in case
                models_list = data.get(
                    "data", data.get("models", data.get("result", []))
                )
            else:
                models_list = []

            available_models = []
            for m in models_list:
                if not isinstance(m, dict):
                    continue

                model_id = m.get("id")
                if not model_id:
                    continue

                # Format native name and provider cleanly
                model_name = m.get("name", model_id)
                provider = m.get("provider", "").title()

                display_name = (
                    f"{model_name} ({provider})"
                    if provider
                    else f"{model_name} (Puter)"
                )
                available_models.append({"id": model_id, "name": display_name})

            # THE DEBUG TRAP: If we connected but found 0 models, dump exactly
            # what Puter sent us into the UI dropdown so we can see the data shape.
            if not available_models:
                raw_json_preview = str(data)[:150]
                return [
                    {
                        "id": "error",
                        "name": f"JSON empty/wrong format. Raw response: {raw_json_preview}",
                    }
                ]

            return available_models

        except Exception as e:
            return [{"id": "error", "name": f"API Error: {str(e)}"}]

    def pipe(self, body: dict, __user__: dict) -> Union[str, Generator, Iterator]:
        if not self.valves.PUTER_AUTH_TOKEN:
            return "Error: PUTER_AUTH_TOKEN is not configured in Valves. Please set it via Open WebUI settings."

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

        # 3. Inject system/memory context safely into the final user prompt
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
            model_id = model_id.split(".", 1)[-1]

        # 4. Build payload with dynamic parameter passthrough
        payload = {
            "model": model_id,
            "messages": alternating_messages,
            "stream": body.get("stream", True),
        }

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
            "Authorization": f"Bearer {self.valves.PUTER_AUTH_TOKEN}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }

        # 5. Execute request with UTF-8 encoding to Puter's Chat Endpoint
        url = "https://api.puter.com/puterai/openai/v1/chat/completions"
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
