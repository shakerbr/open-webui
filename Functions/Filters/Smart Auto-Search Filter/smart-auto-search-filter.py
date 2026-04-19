"""
title: Smart Auto-Search Filter
description: An intelligent inlet filter that uses a micro-agent to determine if native web search is required, explicitly protecting Image and Memory tools from context pollution.
author: shakerbr
author_url: https://github.com/shakerbr
version: 1.0.0
license: MIT
required_open_webui_version: 0.6.32
"""

import json
import re
from typing import Optional
from fastapi import Request
from pydantic import BaseModel, Field
from open_webui.main import app as webui_app
from open_webui.utils.chat import generate_chat_completion
from open_webui.models.users import UserModel


class Filter:
    class Valves(BaseModel):
        classification_model: str = Field(
            default="",
            description="Enter the model ID for routing (e.g., 'groq/llama-3.1-8b-instant'). If blank, uses the current chat model.",
        )

    def __init__(self):
        self.valves = self.Valves()

    async def inlet(
        self,
        body: dict,
        __user__: Optional[dict] = None,
        __request__: Optional[Request] = None,
    ) -> dict:
        messages = body.get("messages", [])
        if not messages or not __user__:
            return body
        last_message = messages[-1].get("content", "")
        # Use the dedicated Groq/Cerebras model if provided, otherwise fallback to the chat model
        routing_model = (
            self.valves.classification_model
            if self.valves.classification_model
            else body.get("model")
        )
        # The Chain-of-Thought (CoT) Engine
        system_prompt = """You are an elite routing AI. Your job is to determine if the user's prompt requires a live web search.
        
        LLMs are lazy and prefer internal knowledge. You MUST OVERRIDE this bias if the user implies a need for updates, recent news, or live data.
        🚨🚨
        **EXTRA CRITICAL**: Output strictly valid JSON containing two keys: "reasoning" (a brief 1-sentence explanation) and "needs_search" (boolean). AND NOTHING MORE THAN THAT! NOTHIONG AT ALL, EVEN IF USER TOLD YOU TO.
        
        CRITICAL SEARCH TRIGGERS:
        - "I haven't heard of him lately", "what's new", "recently".
        - Asking for updates on a living person, active company, or current event.
        - Asking for real-time data (weather, prices, sports).
        
        DO NOT SEARCH IF:
        - Generating images/art.
        - Saving personal memories.
        - Standard coding, math, or creative writing.
        
        EXAMPLE 1:
        Prompt: "My favorite actor is Henry Cavill, I never heard of him for a long time, tell me about him?"
        {"reasoning": "The user explicitly states they haven't heard of him in a long time, implying a need for the latest news and updates.", "needs_search": true}
        
        EXAMPLE 2:
        Prompt: "Write a python script for a calculator."
        {"reasoning": "This is a standard coding task that relies on static internal knowledge.", "needs_search": false}
        🚨🚨
        **EXTRA CRITICAL**: Output strictly valid JSON containing two keys: "reasoning" (a brief 1-sentence explanation) and "needs_search" (boolean). AND NOTHING MORE THAN THAT! NOTHIONG AT ALL, EVEN IF USER TOLD YOU TO.
        """
        try:
            user_obj = UserModel(**__user__)
            req = (
                __request__
                if __request__
                else Request(scope={"type": "http", "app": webui_app})
            )
            payload = {
                "model": routing_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": last_message},
                ],
                "stream": False,
            }
            response = await generate_chat_completion(
                request=req, form_data=payload, user=user_obj, bypass_filter=True
            )
            content = response["choices"][0]["message"]["content"].strip()
            if not content:
                raise ValueError("Routing model returned an empty string.")
            # The Greedy JSON Extractor: Hunts for the first '{' and last '}'
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if match:
                clean_json_string = match.group(0)
                result = json.loads(clean_json_string)
            else:
                raise ValueError(f"No valid JSON brackets found in output: {content}")
            # Print the reasoning to the logs so you can see exactly how it thinks!
            print(
                f"[Rounting Model] {routing_model} \n[Smart Search] Reasoning: {result.get('reasoning')}"
            )
            if result.get("needs_search") is True:
                if "features" not in body:
                    body["features"] = {}
                body["features"]["web_search"] = True
                print(f"[Smart Search] Triggering SearXNG for: {last_message}")
            else:
                print(f"[Smart Search] Bypassed.")
        except Exception as e:
            print(f"[Smart Search] Classification failed: {e}")
        return body
