"""
title: Hugging Face Inference API
description: Internal pipe for Hugging Face Serverless API. Supports custom model lists via Valves, memory injection, and dynamic parameters.
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
        HF_TOKEN: str = Field(default="")
        # You can add or remove models here separated by commas directly in the Open WebUI interface
        HF_MODEL_IDS: str = Field(
            default="meta-llama/Llama-3.3-70B-Instruct,mistralai/Mistral-7B-Instruct-v0.3,Qwen/Qwen2.5-72B-Instruct"
        )

    def __init__(self):
        self.type = "pipe"
        self.id = "huggingface_api"
        # Added the space you requested
        self.name = "Hugging Face "
        self.valves = self.Valves()

    def pipes(self):
        # Dynamically parse the comma-separated model list from your Valves
        raw_models = [
            m.strip() for m in self.valves.HF_MODEL_IDS.split(",") if m.strip()
        ]
        models = []
        for model_id in raw_models:
            # Clean up the display name (e.g., turns "meta-llama/Llama-3.3-70B-Instruct" into "Llama-3.3-70B-Instruct")
            name = model_id.split("/")[-1]
            models.append({"id": model_id, "name": name})
        return models

    def pipe(self, body: dict, __user__: dict) -> Union[str, Generator, Iterator]:
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

        # 4. Clean the Model ID
        # Open WebUI prepends your custom pipe ID (e.g. "hugging_face_inference_pipe.meta-llama/...")
        # We split on the very first dot to extract the raw Hugging Face repo ID safely.
        model_id = body.get("model", "")
        if "." in model_id:
            clean_model_id = model_id.split(".", 1)[1]
        else:
            clean_model_id = model_id

        # 5. Build payload with dynamic parameter passthrough
        payload = {
            "model": clean_model_id,
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
            "Authorization": f"Bearer {self.valves.HF_TOKEN}",
            "Content-Type": "application/json",
        }

        # Hugging Face's brand new unified Router API
        url = "https://router.huggingface.co/v1/chat/completions"

        # 6. Execute request with UTF-8 encoding
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
