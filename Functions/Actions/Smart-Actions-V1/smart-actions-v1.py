"""
title: Smart Actions
description: A universal multi-tool widget framework for Open WebUI. Includes Smart Translations, DOCX Export, and easily extensible for future actions.
author: shakerbr
author_url: https://github.com/shakerbr
version: 1.0.0
license: MIT
required_open_webui_version: 0.6.32
icon_url: data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0iY3VycmVudENvbG9yIj48cGF0aCBkPSJNMTEuNjQ0IDEuNTlhLjc1Ljc1IDAgMCAxIC43MTIgMGw5Ljc1IDUuMjVhLjc1Ljc1IDAgMCAxIDAgMS4zMmwtOS43NSA1LjI1YS43NS43NSAwIDAgMS0uNzEyIDBsLTkuNzUtNS4yNWEuNzUuNzUgMCAwIDEgMC0xLjMybDkuNzUtNS4yNVoiIC8+PHBhdGggZD0iTTMuMjY1IDEwLjYwMmw3LjY2OCA0LjEyOWEyLjI1IDIuMjUgMCAwIDAgMi4xMzQgMGw3LjY2OC00LjEzLTEwLjUgNS42NTRhLjc1Ljc1IDAgMCAxLS43MTIgMGwtMTAuNS01LjY1M1oiIC8+PHBhdGggZD0iTTMuMjY1IDE1Ljg1MkwxMiAyMC41NTlsOC43MzUtNC43MDctMTAuNSA1LjY1NGEuNzUuNzUgMCAwIDEtLjcxMiAwbC0xMC41LTUuNjU0WiIgLz48L3N2Zz4=
"""

import json
import html
import uuid
import aiohttp
import urllib.parse
import re
from pydantic import BaseModel, Field
from typing import Optional


class Action:
    class Valves(BaseModel):
        TRANSLATION_MODEL: str = Field(
            default="",
            description="Model ID for translation. Leave blank to use active chat model.",
        )

    def __init__(self):
        self.valves = self.Valves()

    async def action(
        self,
        body: dict,
        __user__=None,
        __event_emitter__=None,
        __event_call__=None,
        __request__=None,
    ) -> Optional[dict]:

        # 1. Extract the Message Text
        original_text = body.get("message", {}).get("content", "")
        if not original_text and "messages" in body and len(body["messages"]) > 0:
            original_text = body["messages"][-1].get("content", "")

        # 2. Interactive Menu Prompt
        if not __event_call__:
            return None

        user_input = await __event_call__(
            {
                "type": "input",
                "data": {
                    "title": "Message Actions",
                    "message": "• Type a language (e.g., Arabic, Kurdish) to translate.\n• Type 'docx' to download as a Word document.",
                    "placeholder": "Enter language or type 'docx'...",
                },
            }
        )

        if not user_input:
            # User cancelled the dialog
            return {"status": "success"}

        action_cmd = user_input.strip().lower()

        # ==========================================
        # ROUTE A: EXPORT TO DOCX
        # ==========================================
        if action_cmd == "docx":
            url_encoded_text = urllib.parse.quote(original_text)
            tool_id = "chatcmpl-tool-" + uuid.uuid4().hex[:16]

            docx_html_doc = f"""<!DOCTYPE html>
            <html>
            <head>
            <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/html-docx-js@0.3.1/dist/html-docx.min.js"></script>
            <style>
              :root {{ --bg: transparent; --surface: rgba(0, 0, 0, 0.04); --surface-hover: rgba(0, 0, 0, 0.08); --text: rgba(0, 0, 0, 0.9); --text-muted: rgba(0, 0, 0, 0.6); --border: rgba(0, 0, 0, 0.12); --theme-color: #3b82f6; }}
              :root[data-theme="dark"] {{ --bg: transparent; --surface: rgba(255, 255, 255, 0.05); --surface-hover: rgba(255, 255, 255, 0.09); --text: rgba(255, 255, 255, 0.95); --text-muted: rgba(255, 255, 255, 0.6); --border: rgba(255, 255, 255, 0.15); --theme-color: #60a5fa; }}
              @media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ --bg: transparent; --surface: rgba(255, 255, 255, 0.05); --surface-hover: rgba(255, 255, 255, 0.09); --text: rgba(255, 255, 255, 0.95); --text-muted: rgba(255, 255, 255, 0.6); --border: rgba(255, 255, 255, 0.15); --theme-color: #60a5fa; }} }}
              body {{ margin: 0; padding: 4px; font-family: system-ui, sans-serif; background: transparent; color: var(--text); overflow: hidden; }}
              .widget {{ border: 1px solid var(--border); border-radius: 12px; background: var(--bg); overflow: hidden; padding: 16px; display: flex; align-items: center; justify-content: space-between; }}
              .info {{ display: flex; align-items: center; gap: 12px; font-size: 14.5px; }}
              .icon {{ color: var(--theme-color); }}
              .action-btn {{ background: var(--surface); border: 1px solid var(--border); color: var(--text); border-radius: 6px; padding: 8px 14px; font-size: 13px; font-weight: 500; cursor: pointer; transition: all 0.2s; display: flex; align-items: center; gap: 6px; }}
              .action-btn:hover {{ background: var(--border); }}
            </style>
            </head>
            <body>
              <div class="widget">
                <div class="info">
                  <svg class="icon" width="24" height="24" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
                  <div>
                    <strong style="display:block; margin-bottom:2px;">Document Ready</strong>
                    <span style="color: var(--text-muted); font-size:13px;">Your message has been exported as a .docx file.</span>
                  </div>
                </div>
                <button class="action-btn" id="dlBtn" onclick="triggerDownload()">
                  <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>
                  Download Again
                </button>
              </div>
              <script>
                const rawText = decodeURIComponent("{url_encoded_text}");
                
                function triggerDownload() {{
                    // Parse markdown to HTML
                    marked.use({{ gfm: true, breaks: true }});
                    const htmlContent = marked.parse(rawText);
                    
                    // Wrap in full HTML document structure for Word compatibility
                    const fullDoc = '<!DOCTYPE html><html><head><meta charset="utf-8"><style>body{{font-family: Arial, sans-serif;}} table{{border-collapse: collapse; width: 100%;}} th, td{{border: 1px solid #000; padding: 8px;}} code{{background-color: #f3f4f6; padding: 2px 4px;}} pre{{background-color: #f3f4f6; padding: 12px; border-radius: 4px;}}</style></head><body>' + htmlContent + '</body></html>';
                    
                    // Convert to DOCX Blob and trigger download
                    const converted = htmlDocx.asBlob(fullDoc);
                    const link = document.createElement('a');
                    link.href = URL.createObjectURL(converted);
                    link.download = 'Chat_Export.docx';
                    link.click();
                    
                    // Clean up URL object
                    setTimeout(() => URL.revokeObjectURL(link.href), 100);
                }}

                function applyTheme(isDark) {{ document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light'); }}
                function initTheme() {{
                    try {{
                        const p = parent.document.documentElement;
                        const checkTheme = () => applyTheme(p.classList.contains('dark') || p.getAttribute('data-theme') === 'dark');
                        checkTheme();
                        new MutationObserver(checkTheme).observe(p, {{ attributes: true, attributeFilter: ['class', 'data-theme'] }});
                    }} catch(e) {{
                        const mq = window.matchMedia('(prefers-color-scheme: dark)');
                        applyTheme(mq.matches);
                        mq.addEventListener('change', (e) => applyTheme(e.matches));
                    }}
                }}

                window.onload = () => {{
                  initTheme();
                  parent.postMessage({{ type: 'iframe:height', height: document.body.scrollHeight + 10 }}, '*');
                  
                  // Auto-trigger download on first load
                  setTimeout(triggerDownload, 500);
                }};
              </script>
            </body>
            </html>"""

            args_str = html.escape(
                json.dumps({"title": "DOCX Widget", "html_code": "Rendered"}),
                quote=True,
            )
            result_str = html.escape(
                json.dumps(
                    {"status": "success", "code": "ui_component", "message": "Rendered"}
                ),
                quote=True,
            )
            embeds_str = html.escape(json.dumps([docx_html_doc]), quote=True)

            artifact_block = (
                f'\n<details type="tool_calls" open="true" done="true" id="{tool_id}" name=" " '
                f'arguments="{args_str}" result="{result_str}" files="" embeds="{embeds_str}">\n'
                f"<summary>📄 Document Export</summary>\n"
                f"</details>"
            )

            if __event_emitter__:
                await __event_emitter__(
                    {"type": "message", "data": {"content": artifact_block}}
                )

            return {"status": "success"}

        # ==========================================
        # ROUTE B: TRANSLATION
        # ==========================================
        target_lang = user_input.strip()

        # Send a quick native toast notification that translation has started
        if __event_emitter__:
            await __event_emitter__(
                {
                    "type": "notification",
                    "data": {
                        "type": "info",
                        "content": f"Translating message to {target_lang}...",
                    },
                }
            )

        # 1. Regex Masking (Bulletproof Fix)
        clean_text = re.sub(
            r"<details.*?</details>", "", original_text, flags=re.DOTALL
        )
        clean_text = re.sub(r"<think.*?</think>", "", clean_text, flags=re.DOTALL)

        code_blocks = []

        def mask_code(match):
            code_blocks.append(match.group(0))
            return f"[[CODE_BLOCK_{len(code_blocks)-1}]]"

        masked_text = re.sub(r"```.*?```", mask_code, clean_text, flags=re.DOTALL)

        # 2. Smart RTL Detection
        rtl_languages = [
            "arabic",
            "hebrew",
            "farsi",
            "persian",
            "urdu",
            "pashto",
            "sindhi",
            "sorani",
            "kurdish",
            "kurmanji",
            "bahdini",
        ]
        is_rtl = any(rtl_lang in target_lang.lower() for rtl_lang in rtl_languages)

        # 3. Setup API Call
        current_model = body.get("model", "")
        model_to_use = (
            self.valves.TRANSLATION_MODEL
            if self.valves.TRANSLATION_MODEL
            else current_model
        )

        headers = {"Content-Type": "application/json"}
        if __request__ and "Authorization" in __request__.headers:
            headers["Authorization"] = __request__.headers["Authorization"]

        payload = {
            "model": model_to_use,
            "messages": [
                {
                    "role": "system",
                    "content": f"[RULE] You are a professional translator. [INSTRUCTION] Translate the user's text into {target_lang}. [OPUTPUT] - Output ONLY the translated text. - Maintain all original markdown formatting. [EXCLUDE] - Any <details type= ... </details> or similar block. [DO NOT TRANSLATE] - Anything that is inside a Code Blocks(```code```) icluding comments.",
                },
                {"role": "user", "content": masked_text},
            ],
            "stream": False,
        }

        # 4. API Call & Unmasking
        is_error = False
        translated_text = ""

        try:
            base_url = (
                str(__request__.base_url).rstrip("/")
                if __request__
                else "http://localhost:8080"
            )
            api_url = f"{base_url}/api/chat/completions"

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    api_url, headers=headers, json=payload, timeout=60
                ) as response:
                    response.raise_for_status()
                    result = await response.json()
                    translated_text = result["choices"][0]["message"]["content"]

                    for i, code in enumerate(code_blocks):
                        translated_text = translated_text.replace(
                            f"[[CODE_BLOCK_{i}]]", code
                        )

                    translated_text = re.sub(
                        r"<details.*?</details>", "", translated_text, flags=re.DOTALL
                    )
                    translated_text = re.sub(
                        r"<think.*?</think>", "", translated_text, flags=re.DOTALL
                    )
                    translated_text = translated_text.strip()

        except Exception as e:
            is_error = True
            translated_text = f"**Error:** `{str(e)}`"

        # 5. Dynamic HTML Variables
        if is_error:
            widget_title = "Translation Error"
            icon_svg = '<svg class="title-icon" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>'
            color_light, color_dark = "#ef4444", "#f87171"
            content_dir, content_align = "ltr", "left"
            copy_btn_html = ""
        else:
            widget_title = f"Translation ({target_lang})"
            icon_svg = '<svg class="title-icon" width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="m12.87 15.07l-2.54-2.51l.03-.03A17.5 17.5 0 0 0 14.07 6H17V4h-7V2H8v2H1v2h11.17C11.5 7.92 10.44 9.75 9 11.35C8.07 10.32 7.3 9.19 6.69 8h-2c.73 1.63 1.73 3.17 2.98 4.56l-5.09 5.02L4 19l5-5l3.11 3.11zM18.5 10h-2L12 22h2l1.12-3h4.75L21 22h2zm-2.62 7l1.62-4.33L19.12 17z"/></svg>'
            color_light, color_dark = "#10b981", "#34d399"
            content_dir = "rtl" if is_rtl else "ltr"
            content_align = "right" if is_rtl else "left"
            copy_btn_html = """
                <button class="action-btn" id="copyBtn" onclick="copyText(event)">
                  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"></path></svg>
                  Copy
                </button>
            """

        url_encoded_text = urllib.parse.quote(translated_text)
        tool_id = "chatcmpl-tool-" + uuid.uuid4().hex[:16]

        # 6. Unified HTML Generation
        html_doc = f"""<!DOCTYPE html>
        <html>
        <head>
        <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
        <style>
          :root {{
            --bg: transparent; --surface: rgba(0, 0, 0, 0.04); --surface-hover: rgba(0, 0, 0, 0.08);
            --text: rgba(0, 0, 0, 0.9); --text-muted: rgba(0, 0, 0, 0.6); --border: rgba(0, 0, 0, 0.12);
            --theme-color: {color_light}; 
          }}
          :root[data-theme="dark"] {{
            --bg: transparent; --surface: rgba(255, 255, 255, 0.05); --surface-hover: rgba(255, 255, 255, 0.09);
            --text: rgba(255, 255, 255, 0.95); --text-muted: rgba(255, 255, 255, 0.6); --border: rgba(255, 255, 255, 0.15);
            --theme-color: {color_dark}; 
          }}
          @media (prefers-color-scheme: dark) {{
            :root:not([data-theme="light"]) {{
              --bg: transparent; --surface: rgba(255, 255, 255, 0.05); --surface-hover: rgba(255, 255, 255, 0.09);
              --text: rgba(255, 255, 255, 0.95); --text-muted: rgba(255, 255, 255, 0.6); --border: rgba(255, 255, 255, 0.15);
              --theme-color: {color_dark}; 
            }}
          }}
          
          body {{ margin: 0; padding: 4px; font-family: system-ui, sans-serif; background: transparent; color: var(--text); overflow: hidden; }}
          .widget {{ border: 1px solid var(--border); border-radius: 12px; background: var(--bg); overflow: hidden; }}
          
          .header {{ display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; background: var(--surface); cursor: pointer; user-select: none; border-bottom: 1px solid transparent; transition: background 0.2s, border-color 0.2s; }}
          .header:hover {{ background: var(--surface-hover); }}
          .header.open {{ border-bottom-color: var(--border); }}
          
          .title {{ font-weight: 600; font-size: 14px; display: flex; align-items: center; gap: 8px; }}
          .title-icon {{ color: var(--theme-color); }} 
          
          .actions {{ display: flex; align-items: center; gap: 8px; }}
          
          .action-btn {{ background: transparent; border: 1px solid var(--border); color: var(--text); border-radius: 6px; padding: 4px 10px; font-size: 12px; cursor: pointer; transition: all 0.2s; display: flex; align-items: center; gap: 4px; }}
          .action-btn:hover {{ background: var(--border); }}
          .action-btn svg {{ width: 14px; height: 14px; }}
          
          .chevron {{ transition: transform 0.3s; width: 16px; height: 16px; color: var(--text-muted); margin-left: 4px; }}
          .chevron.open {{ transform: rotate(180deg); }}
          
          .content-wrapper {{ display: grid; grid-template-rows: 1fr; transition: grid-template-rows 0.3s ease-out; }}
          .content-wrapper.collapsed {{ grid-template-rows: 0fr; }}
          .content-inner {{ overflow: hidden; }}
          
          .content {{ 
              padding: 16px; font-size: 14.5px; line-height: 1.6; 
              word-break: break-word; 
              direction: {content_dir}; text-align: {content_align};
          }}

          /* Markdown Styles */
          .markdown-body p {{ margin-top: 0; margin-bottom: 12px; }}
          .markdown-body p:last-child {{ margin-bottom: 0; }}
          .markdown-body a {{ color: var(--theme-color); text-decoration: none; }}
          .markdown-body a:hover {{ text-decoration: underline; }}
          .markdown-body code {{ background: var(--surface-hover); padding: 3px 6px; border-radius: 4px; font-family: monospace; font-size: 90%; }}
          .markdown-body pre {{ background: var(--surface); border: 1px solid var(--border); padding: 12px; border-radius: 8px; overflow-x: auto; direction: ltr; text-align: left; }}
          .markdown-body pre code {{ background: transparent; padding: 0; font-size: 13px; }}
          .markdown-body blockquote {{ margin: 0 0 12px 0; padding: 4px 16px; color: var(--text-muted); }}
          
          /* Smart RTL for Blockquotes */
          .content[dir="ltr"] blockquote {{ border-left: 4px solid var(--border); }}
          .content[dir="rtl"] blockquote {{ border-right: 4px solid var(--border); }}
          
          .markdown-body table {{ border-collapse: collapse; width: 100%; margin-bottom: 12px; font-size: 14px; }}
          .markdown-body th, .markdown-body td {{ border: 1px solid var(--border); padding: 8px 12px; text-align: {content_align}; }}
          .markdown-body th {{ background: var(--surface); font-weight: 600; }}
          .markdown-body ul, .markdown-body ol {{ margin-top: 0; margin-bottom: 12px; padding-inline-start: 24px; }}
          .markdown-body img {{ max-width: 100%; border-radius: 8px; }}
          .markdown-body h1, .markdown-body h2, .markdown-body h3, .markdown-body h4 {{ margin-top: 16px; margin-bottom: 8px; }}
          
          .error-text {{ color: var(--theme-color); font-family: monospace; font-size: 13px; }}

          /* Copy Buttons for Code & Tables */
          .markdown-body pre {{ position: relative; }}
          .table-wrapper {{ position: relative; overflow-x: auto; margin-bottom: 12px; }}
          .markdown-body table {{ margin-bottom: 0; }} 
          
          .block-copy-btn {{
              position: absolute; top: 4px; right: 4px;
              background: var(--surface); border: 1px solid var(--border);
              color: var(--text-muted); border-radius: 4px; padding: 4px;
              cursor: pointer; opacity: 0; transition: opacity 0.2s; display: flex;
          }}
          .markdown-body pre:hover .block-copy-btn, .table-wrapper:hover .block-copy-btn {{ opacity: 1; }}
          .block-copy-btn:hover {{ color: var(--text); background: var(--surface-hover); }}
          .block-copy-btn svg {{ width: 14px; height: 14px; }}
        </style>
        </head>
        <body>
          <div class="widget">
            <div class="header open" id="header" onclick="toggle()">
              <div class="title">
                {icon_svg}
                {widget_title}
              </div>
              <div class="actions">
                {copy_btn_html}
                <svg class="chevron open" id="chevron" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7"></path></svg>
              </div>
            </div>
            <div class="content-wrapper" id="wrapper">
              <div class="content-inner">
                <div class="content markdown-body" id="text" dir="{content_dir}"></div>
              </div>
            </div>
          </div>
          <script>
            const rawText = decodeURIComponent("{url_encoded_text}");
            
            marked.use({{ gfm: true, breaks: true }});
            document.getElementById('text').innerHTML = marked.parse(rawText);

            const copyIcon = '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"></path></svg>';
            const checkIcon = '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"></path></svg>';

            document.querySelectorAll('.markdown-body pre').forEach(pre => {{
                const btn = document.createElement('button');
                btn.className = 'block-copy-btn'; btn.innerHTML = copyIcon; btn.title = 'Copy code';
                btn.onclick = async (e) => {{
                    e.stopPropagation();
                    await navigator.clipboard.writeText(pre.querySelector('code').innerText);
                    btn.innerHTML = checkIcon; setTimeout(() => btn.innerHTML = copyIcon, 2000);
                }};
                pre.appendChild(btn);
            }});

            document.querySelectorAll('.markdown-body table').forEach(table => {{
                const wrapper = document.createElement('div');
                wrapper.className = 'table-wrapper';
                table.parentNode.insertBefore(wrapper, table);
                wrapper.appendChild(table);
                
                const btn = document.createElement('button');
                btn.className = 'block-copy-btn'; btn.innerHTML = copyIcon; btn.title = 'Copy table as Markdown';
                btn.onclick = async (e) => {{
                    e.stopPropagation();
                    let md = Array.from(table.rows).map((row, index) => {{
                        let cells = Array.from(row.cells).map(cell => cell.innerText.trim().replace(/\\|/g, '&#124;'));
                        let rowStr = '| ' + cells.join(' | ') + ' |';
                        if (index === 0) {{
                            let sep = '|' + cells.map(() => '---').join('|') + '|';
                            return rowStr + '\\n' + sep;
                        }}
                        return rowStr;
                    }}).join('\\n');
                    
                    await navigator.clipboard.writeText(md);
                    btn.innerHTML = checkIcon; setTimeout(() => btn.innerHTML = copyIcon, 2000);
                }};
                wrapper.appendChild(btn);
            }});

            function setHeight() {{ parent.postMessage({{ type: 'iframe:height', height: document.body.scrollHeight + 5 }}, '*'); }}

            function toggle() {{
              document.getElementById('wrapper').classList.toggle('collapsed');
              document.getElementById('chevron').classList.toggle('open');
              document.getElementById('header').classList.toggle('open');
              setTimeout(setHeight, 300);
            }}

            async function copyText(e) {{
              if(!rawText) return;
              e.stopPropagation();
              const btn = document.getElementById('copyBtn');
              try {{
                await navigator.clipboard.writeText(rawText);
                const originalHTML = btn.innerHTML;
                btn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"></path></svg> Copied!';
                setTimeout(() => {{ btn.innerHTML = originalHTML; }}, 2000);
              }} catch (err) {{}}
            }}

            function applyTheme(isDark) {{ document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light'); }}

            function initTheme() {{
                try {{
                    const p = parent.document.documentElement;
                    const checkTheme = () => applyTheme(p.classList.contains('dark') || p.getAttribute('data-theme') === 'dark');
                    checkTheme();
                    new MutationObserver(checkTheme).observe(p, {{ attributes: true, attributeFilter: ['class', 'data-theme'] }});
                }} catch(e) {{
                    const mq = window.matchMedia('(prefers-color-scheme: dark)');
                    applyTheme(mq.matches);
                    mq.addEventListener('change', (e) => applyTheme(e.matches));
                }}
            }}

            window.onload = () => {{
              initTheme();
              setTimeout(setHeight, 100); 
              new ResizeObserver(setHeight).observe(document.body);
            }};
          </script>
        </body>
        </html>"""

        args_str = html.escape(
            json.dumps({"title": "Translation Widget", "html_code": "Rendered"}),
            quote=True,
        )
        result_str = html.escape(
            json.dumps(
                {"status": "success", "code": "ui_component", "message": "Rendered"}
            ),
            quote=True,
        )
        embeds_str = html.escape(json.dumps([html_doc]), quote=True)

        artifact_block = (
            f'\n<details type="tool_calls" open="true" done="true" id="{tool_id}" name=" " '
            f'arguments="{args_str}" result="{result_str}" files="" embeds="{embeds_str}">\n'
            f"<summary>🌐 View Translation</summary>\n"
            f"</details>"
        )

        if __event_emitter__:
            await __event_emitter__(
                {"type": "message", "data": {"content": artifact_block}}
            )

        return {"status": "success"}
