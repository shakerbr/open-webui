"""
title: Smart Actions
description: Universal multi-tool widget framework for Open WebUI. Smart Translations, multi-format file exports (DOCX, MD, code, web bundles), and an advanced TTS Read-Aloud player with word/paragraph highlighting.
author: shakerbr
author_url: https://github.com/shakerbr
version: 2.0.0
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
from typing import Optional, List, Tuple


class Action:
    class Valves(BaseModel):
        TRANSLATION_MODEL: str = Field(
            default="",
            description="Model ID for translation. Leave blank to use active chat model.",
        )
        TTS_API_BASE_URL: str = Field(
            default="",
            description="TTS API base URL (e.g. http://local-tts:8000/v1 or http://host:5050/v1/audio/speech). The /audio/speech path is auto-appended if needed. Leave blank for Open WebUI built-in TTS.",
        )
        TTS_API_KEY: str = Field(
            default="",
            description="TTS API key. Leave blank to use the session token.",
        )
        TTS_DEFAULT_VOICE: str = Field(
            default="alloy",
            description="Default TTS voice (alloy, echo, fable, onyx, nova, shimmer, or custom).",
        )
        TTS_DEFAULT_MODEL: str = Field(
            default="tts-1",
            description="Default TTS model identifier.",
        )
        TTS_VOICES: str = Field(
            default="alloy,echo,fable,onyx,nova,shimmer",
            description="Comma-separated list of available TTS voices.",
        )

    def __init__(self):
        self.valves = self.Valves()

    # ─────────────────── HELPER METHODS ───────────────────

    def _extract_code_blocks(
        self, text: str, language: str = None
    ) -> List[Tuple[str, str, str]]:
        """Extract fenced code blocks. Returns [(language, code, preview)]."""
        pattern = r"```(\w*)\n(.*?)```"
        matches = re.findall(pattern, text, re.DOTALL)
        blocks = []
        for lang, code in matches:
            lang_lower = lang.strip().lower() if lang else "text"
            preview = code.strip().split("\n")[0][:60]
            if language is None or lang_lower == language.lower():
                blocks.append((lang_lower, code.strip(), preview))
        return blocks

    def _detect_web_blocks(self, text: str) -> dict:
        """Detect related web-dev code blocks (HTML, CSS, JS, PHP …)."""
        web_langs = {
            "html",
            "css",
            "javascript",
            "js",
            "php",
            "typescript",
            "ts",
            "scss",
            "sass",
            "less",
            "jsx",
            "tsx",
            "svg",
        }
        blocks = self._extract_code_blocks(text)
        web_blocks: dict = {}
        for lang, code, preview in blocks:
            if lang in web_langs:
                web_blocks.setdefault(lang, []).append((code, preview))
        return web_blocks

    def _get_smart_filename(self, body: dict, text: str, ext: str) -> str:
        """Derive a human-friendly filename from context."""
        chat = body.get("chat")
        title = chat.get("title", "") if isinstance(chat, dict) else ""
        if title.strip() and title.strip().lower() not in ("new chat", "untitled", ""):
            name = re.sub(r"[^\w\s-]", "", title).strip()
            name = re.sub(r"\s+", "_", name)[:50]
            return f"{name}.{ext}"
        heading = re.search(r"^#+ (.+)$", text, re.MULTILINE)
        if heading:
            name = re.sub(r"[^\w\s-]", "", heading.group(1)).strip()
            name = re.sub(r"\s+", "_", name)[:50]
            return f"{name}.{ext}"
        clean = re.sub(r"[^\w\s]", "", text[:100]).strip()
        words = clean.split()[:5]
        if words:
            return "_".join(words)[:50] + f".{ext}"
        return f"export.{ext}"

    async def _ask_filename(self, __event_call__, default_name: str) -> str:
        """Prompt user for a custom filename."""
        resp = await __event_call__(
            {
                "type": "input",
                "data": {
                    "title": "File Name",
                    "message": f"Enter a filename (default: {default_name})",
                    "placeholder": default_name,
                },
            }
        )
        if resp and isinstance(resp, str) and resp.strip():
            name = resp.strip()
            ext = default_name.rsplit(".", 1)[-1]
            if not name.lower().endswith(f".{ext}"):
                name = f"{name}.{ext}"
            return name
        return default_name

    async def _select_code_blocks(
        self, blocks: list, __event_call__, label: str
    ) -> list:
        """When multiple code blocks exist, let the user pick."""
        if len(blocks) <= 1:
            return blocks
        lines = [f"Found {len(blocks)} {label} blocks:\n"]
        for i, (lang, _code, preview) in enumerate(blocks, 1):
            lines.append(f"  {i}. [{lang}] {preview}")
        lines.append("\nType numbers (e.g. '1,3'), 'all', or 'last'.")
        sel = await __event_call__(
            {
                "type": "input",
                "data": {
                    "title": f"Select {label} Blocks",
                    "message": "\n".join(lines),
                    "placeholder": "all",
                },
            }
        )
        if not sel or not isinstance(sel, str) or sel.strip().lower() in ("all", ""):
            return blocks
        s = sel.strip().lower()
        if s == "last":
            return [blocks[-1]]
        try:
            idx = [int(x.strip()) - 1 for x in s.split(",") if x.strip().isdigit()]
            picked = [blocks[i] for i in idx if 0 <= i < len(blocks)]
            return picked if picked else blocks
        except Exception:
            return blocks

    def _theme_css(
        self, accent_light: str = "#3b82f6", accent_dark: str = "#60a5fa"
    ) -> str:
        return (
            f":root{{--bg:transparent;--surface:rgba(0,0,0,.04);--surface-hover:rgba(0,0,0,.08);"
            f"--text:rgba(0,0,0,.9);--text-muted:rgba(0,0,0,.6);--border:rgba(0,0,0,.12);--accent:{accent_light};--accent-soft:{accent_light}18}}"
            f':root[data-theme="dark"]{{--bg:transparent;--surface:rgba(255,255,255,.05);--surface-hover:rgba(255,255,255,.09);'
            f"--text:rgba(255,255,255,.95);--text-muted:rgba(255,255,255,.6);--border:rgba(255,255,255,.15);--accent:{accent_dark};--accent-soft:{accent_dark}18}}"
            f'@media(prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--bg:transparent;--surface:rgba(255,255,255,.05);--surface-hover:rgba(255,255,255,.09);'
            f"--text:rgba(255,255,255,.95);--text-muted:rgba(255,255,255,.6);--border:rgba(255,255,255,.15);--accent:{accent_dark};--accent-soft:{accent_dark}18}}}}"
        )

    def _theme_js(self) -> str:
        return (
            "function applyTheme(d){document.documentElement.setAttribute('data-theme',d?'dark':'light');document.documentElement.style.colorScheme=d?'dark':'light'}"
            "function initTheme(){try{const p=parent.document.documentElement;"
            "const c=()=>applyTheme(p.classList.contains('dark')||p.getAttribute('data-theme')==='dark');"
            "c();new MutationObserver(c).observe(p,{attributes:true,attributeFilter:['class','data-theme']})"
            "}catch(e){const m=window.matchMedia('(prefers-color-scheme: dark)');"
            "applyTheme(m.matches);m.addEventListener('change',e=>applyTheme(e.matches))}}"
            "function setHeight(){parent.postMessage({type:'iframe:height',height:document.body.scrollHeight+10},'*')}"
        )

    async def _emit_widget(self, __event_emitter__, html_content: str, summary: str):
        tool_id = "chatcmpl-tool-" + uuid.uuid4().hex[:16]
        a = html.escape(
            json.dumps({"title": summary, "html_code": "Rendered"}), quote=True
        )
        r = html.escape(
            json.dumps(
                {"status": "success", "code": "ui_component", "message": "Rendered"}
            ),
            quote=True,
        )
        e = html.escape(json.dumps([html_content]), quote=True)
        block = (
            f'\n<details type="tool_calls" open="true" done="true" id="{tool_id}" name=" " '
            f'arguments="{a}" result="{r}" files="" embeds="{e}">\n'
            f"<summary>{summary}</summary>\n</details>"
        )
        if __event_emitter__:
            await __event_emitter__({"type": "message", "data": {"content": block}})

    # ─────────── SVG ICON CONSTANTS ───────────

    ICON_FILE = '<svg width="22" height="22" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>'
    ICON_WORD = '<svg width="22" height="22" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"/></svg>'
    ICON_MD = '<svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor"><path d="M20.56 18H3.44C2.65 18 2 17.37 2 16.59V7.41C2 6.63 2.65 6 3.44 6h17.12c.79 0 1.44.63 1.44 1.41v9.18c0 .78-.65 1.41-1.44 1.41M6.81 15.19v-3.66l1.92 2.35 1.92-2.35v3.66h1.93V8.81h-1.93l-1.92 2.35-1.92-2.35H4.89v6.38h1.92M19.69 12h-1.92V8.81h-1.92V12h-1.93l2.89 3.28L19.69 12z"/></svg>'
    ICON_CODE = '<svg width="22" height="22" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M17.25 6.75L22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3l-4.5 16.5"/></svg>'
    ICON_WEB = '<svg width="22" height="22" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M12 21a9.004 9.004 0 008.716-6.747M12 21a9.004 9.004 0 01-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 017.843 4.582M12 3a8.997 8.997 0 00-7.843 4.582m15.686 0A11.953 11.953 0 0112 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0121 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0112 16.5a17.92 17.92 0 01-8.716-2.247m0 0A9 9 0 013 12c0-1.605.42-3.113 1.157-4.418"/></svg>'
    ICON_TRANSLATE = '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="m12.87 15.07-2.54-2.51.03-.03A17.5 17.5 0 0014.07 6H17V4h-7V2H8v2H1v2h11.17C11.5 7.92 10.44 9.75 9 11.35 8.07 10.32 7.3 9.19 6.69 8h-2c.73 1.63 1.73 3.17 2.98 4.56l-5.09 5.02L4 19l5-5 3.11 3.11zM18.5 10h-2L12 22h2l1.12-3h4.75L21 22h2zm-2.62 7l1.62-4.33L19.12 17z"/></svg>'
    ICON_SPEAKER = '<svg width="22" height="22" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M19.114 5.636a9 9 0 010 12.728M16.463 8.288a5.25 5.25 0 010 7.424M6.75 8.25l4.72-4.72a.75.75 0 011.28.53v15.88a.75.75 0 01-1.28.53l-4.72-4.72H4.51c-.88 0-1.704-.507-1.938-1.354A9.01 9.01 0 012.25 12c0-.83.112-1.633.322-2.396C2.806 8.756 3.63 8.25 4.51 8.25H6.75z"/></svg>'

    # ─────────── WIDGET BUILDERS ───────────

    def _build_download_widget(
        self,
        content: str,
        filename: str,
        mime: str,
        label: str,
        icon: str = None,
        extra_head: str = "",
    ) -> str:
        """Build a generic file-download widget."""
        if icon is None:
            icon = self.ICON_FILE
        encoded = urllib.parse.quote(content)
        tc = self._theme_css()
        tj = self._theme_js()
        return f"""<!DOCTYPE html><html><head>{extra_head}
<style>{tc}
body{{margin:0;padding:4px;font-family:system-ui,sans-serif;background:transparent;color:var(--text);overflow:hidden}}
.w{{border:1px solid var(--border);border-radius:12px;background:var(--bg);padding:16px;display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}}
.info{{display:flex;align-items:center;gap:12px;font-size:14.5px;min-width:0}}
.icon{{color:var(--accent);font-size:22px;flex-shrink:0}}
.meta strong{{display:block;margin-bottom:2px}} .meta span{{color:var(--text-muted);font-size:13px}}
.btn{{background:var(--surface);border:1px solid var(--border);color:var(--text);border-radius:8px;padding:8px 16px;font-size:13px;font-weight:500;cursor:pointer;transition:all .2s;display:flex;align-items:center;gap:6px;white-space:nowrap}}
.btn:hover{{background:var(--surface-hover)}}
.btn svg{{width:16px;height:16px}}
</style></head><body>
<div class="w">
 <div class="info"><span class="icon">{icon}</span>
  <div class="meta"><strong>{filename}</strong><span>{label}</span></div></div>
 <button class="btn" onclick="dl()"><svg fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/></svg>Download</button>
</div>
<script>
const D=decodeURIComponent("{encoded}"),F="{filename}",M="{mime}";
function dl(){{const b=new Blob([D],{{type:M}});const a=document.createElement('a');a.href=URL.createObjectURL(b);a.download=F;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),100)}}
{tj}
window.onload=()=>{{initTheme();setHeight()}};
</script></body></html>"""

    def _build_docx_widget(self, content: str, filename: str) -> str:
        """Build the DOCX-specific download widget (needs marked + html-docx-js)."""
        encoded = urllib.parse.quote(content)
        tc = self._theme_css()
        tj = self._theme_js()
        return f"""<!DOCTYPE html><html><head>
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/html-docx-js@0.3.1/dist/html-docx.min.js"></script>
<style>{tc}
body{{margin:0;padding:4px;font-family:system-ui,sans-serif;background:transparent;color:var(--text);overflow:hidden}}
.w{{border:1px solid var(--border);border-radius:12px;background:var(--bg);padding:16px;display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}}
.info{{display:flex;align-items:center;gap:12px;font-size:14.5px;min-width:0}}
.icon{{color:var(--accent);font-size:22px;flex-shrink:0}}
.meta strong{{display:block;margin-bottom:2px}} .meta span{{color:var(--text-muted);font-size:13px}}
.btn{{background:var(--surface);border:1px solid var(--border);color:var(--text);border-radius:8px;padding:8px 16px;font-size:13px;font-weight:500;cursor:pointer;transition:all .2s;display:flex;align-items:center;gap:6px;white-space:nowrap}}
.btn:hover{{background:var(--surface-hover)}}
.btn svg{{width:16px;height:16px}}
</style></head><body>
<div class="w">
 <div class="info"><span class="icon">{self.ICON_WORD}</span>
  <div class="meta"><strong>{filename}</strong><span>Word document exported</span></div></div>
 <button class="btn" onclick="dl()"><svg fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/></svg>Download</button>
</div>
<script>
const raw=decodeURIComponent("{encoded}");
function dl(){{marked.use({{gfm:true,breaks:true}});const h=marked.parse(raw);const doc='<!DOCTYPE html><html><head><meta charset="utf-8"><style>body{{font-family:Arial,sans-serif}}table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #000;padding:8px}}code{{background:#f3f4f6;padding:2px 4px}}pre{{background:#f3f4f6;padding:12px;border-radius:4px}}</style></head><body>'+h+'</body></html>';const b=htmlDocx.asBlob(doc);const a=document.createElement('a');a.href=URL.createObjectURL(b);a.download="{filename}";a.click();setTimeout(()=>URL.revokeObjectURL(a.href),100)}}
{tj}
window.onload=()=>{{initTheme();setHeight()}};
</script></body></html>"""

    def _build_web_bundle_widget(self, files: dict, archive_name: str) -> str:
        """Build a widget that downloads multiple web files as a zip using JSZip."""
        tc = self._theme_css()
        tj = self._theme_js()
        files_json = urllib.parse.quote(json.dumps(files))
        file_list_html = "".join(
            f"<div style='font-size:12px;color:var(--text-muted);padding:2px 0'>• {fn}</div>"
            for fn in files.keys()
        )
        return f"""<!DOCTYPE html><html><head>
<script src="https://cdn.jsdelivr.net/npm/jszip@3/dist/jszip.min.js"></script>
<style>{tc}
body{{margin:0;padding:4px;font-family:system-ui,sans-serif;background:transparent;color:var(--text);overflow:hidden}}
.w{{border:1px solid var(--border);border-radius:12px;background:var(--bg);padding:16px}}
.top{{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}}
.info{{display:flex;align-items:center;gap:12px;font-size:14.5px;min-width:0}}
.icon{{color:var(--accent);font-size:22px;flex-shrink:0}}
.meta strong{{display:block;margin-bottom:2px}} .meta span{{color:var(--text-muted);font-size:13px}}
.files{{margin-top:10px;padding-top:10px;border-top:1px solid var(--border)}}
.btn{{background:var(--surface);border:1px solid var(--border);color:var(--text);border-radius:8px;padding:8px 16px;font-size:13px;font-weight:500;cursor:pointer;transition:all .2s;display:flex;align-items:center;gap:6px;white-space:nowrap}}
.btn:hover{{background:var(--surface-hover)}}
.btn svg{{width:16px;height:16px}}
</style></head><body>
<div class="w">
 <div class="top">
  <div class="info"><span class="icon">{self.ICON_WEB}</span>
   <div class="meta"><strong>{archive_name}</strong><span>Web bundle ready</span></div></div>
  <button class="btn" onclick="dl()"><svg fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/></svg>Download ZIP</button>
 </div>
 <div class="files">{file_list_html}</div>
</div>
<script>
const F=JSON.parse(decodeURIComponent("{files_json}"));
async function dl(){{const z=new JSZip();for(const[n,c] of Object.entries(F))z.file(n,c);const b=await z.generateAsync({{type:"blob"}});const a=document.createElement('a');a.href=URL.createObjectURL(b);a.download="{archive_name}";a.click();setTimeout(()=>URL.revokeObjectURL(a.href),100)}}
{tj}
window.onload=()=>{{initTheme();setHeight()}};
</script></body></html>"""

    async def action(
        self,
        body: dict,
        __user__=None,
        __event_emitter__=None,
        __event_call__=None,
        __request__=None,
    ) -> Optional[dict]:

        # ── Extract message text ──
        original_text = body.get("message", {}).get("content", "")
        if not original_text and "messages" in body and len(body["messages"]) > 0:
            original_text = body["messages"][-1].get("content", "")

        if not __event_call__:
            return None

        # ── Menu prompt ──
        user_input = await __event_call__(
            {
                "type": "input",
                "data": {
                    "title": "☷ Smart Actions",
                    "message": (
                        "• Language name → Translate (e.g. Arabic, French)\n"
                        "• docx → Word document\n"
                        "• md → Markdown file\n"
                        "• py / html / css / cpp / java / … → Code blocks\n"
                        "• web → Bundled web project (HTML+CSS+JS+…)\n"
                        "• txt / json / csv / xml / sql / yaml → Text formats\n"
                        "• read → Read aloud (TTS player)"
                    ),
                    "placeholder": "Type a language, format, or 'read'…",
                },
            }
        )
        if not user_input:
            return {"status": "success"}

        cmd = user_input.strip().lower()

        # ── Format → extension / MIME / language mapping ──
        CODE_LANGS = {
            "py": ("py", "text/x-python", "python"),
            "python": ("py", "text/x-python", "python"),
            "html": ("html", "text/html", "html"),
            "css": ("css", "text/css", "css"),
            "js": ("js", "application/javascript", "javascript"),
            "javascript": ("js", "application/javascript", "javascript"),
            "ts": ("ts", "application/typescript", "typescript"),
            "typescript": ("ts", "application/typescript", "typescript"),
            "cpp": ("cpp", "text/x-c++src", "cpp"),
            "c++": ("cpp", "text/x-c++src", "cpp"),
            "c": ("c", "text/x-csrc", "c"),
            "java": ("java", "text/x-java", "java"),
            "rb": ("rb", "text/x-ruby", "ruby"),
            "ruby": ("rb", "text/x-ruby", "ruby"),
            "go": ("go", "text/x-go", "go"),
            "rs": ("rs", "text/x-rustsrc", "rust"),
            "rust": ("rs", "text/x-rustsrc", "rust"),
            "swift": ("swift", "text/x-swift", "swift"),
            "kt": ("kt", "text/x-kotlin", "kotlin"),
            "kotlin": ("kt", "text/x-kotlin", "kotlin"),
            "php": ("php", "application/x-httpd-php", "php"),
            "sh": ("sh", "application/x-sh", "bash"),
            "bash": ("sh", "application/x-sh", "bash"),
            "sql": ("sql", "application/sql", "sql"),
            "r": ("r", "text/x-r", "r"),
            "scala": ("scala", "text/x-scala", "scala"),
            "dart": ("dart", "application/dart", "dart"),
            "lua": ("lua", "text/x-lua", "lua"),
            "ps1": ("ps1", "application/x-powershell", "powershell"),
            "powershell": ("ps1", "application/x-powershell", "powershell"),
        }
        TEXT_FORMATS = {
            "txt": ("txt", "text/plain"),
            "text": ("txt", "text/plain"),
            "json": ("json", "application/json"),
            "csv": ("csv", "text/csv"),
            "xml": ("xml", "application/xml"),
            "yaml": ("yaml", "application/x-yaml"),
            "yml": ("yaml", "application/x-yaml"),
            "toml": ("toml", "application/toml"),
            "ini": ("ini", "text/plain"),
            "log": ("log", "text/plain"),
            "env": ("env", "text/plain"),
            "tex": ("tex", "application/x-tex"),
            "latex": ("tex", "application/x-tex"),
        }

        # ═══════════════════════════════════════════
        # ROUTE: DOCX EXPORT
        # ═══════════════════════════════════════════
        if cmd == "docx":
            default_fn = self._get_smart_filename(body, original_text, "docx")
            filename = await self._ask_filename(__event_call__, default_fn)
            widget = self._build_docx_widget(original_text, filename)
            await self._emit_widget(__event_emitter__, widget, "Word Export")
            return {"status": "success"}

        # ═══════════════════════════════════════════
        # ROUTE: MARKDOWN EXPORT
        # ═══════════════════════════════════════════
        if cmd in ("md", "markdown"):
            default_fn = self._get_smart_filename(body, original_text, "md")
            filename = await self._ask_filename(__event_call__, default_fn)
            widget = self._build_download_widget(
                original_text,
                filename,
                "text/markdown",
                "Markdown file exported",
                self.ICON_MD,
            )
            await self._emit_widget(__event_emitter__, widget, "Markdown Export")
            return {"status": "success"}

        # ═══════════════════════════════════════════
        # ROUTE: CODE BLOCK EXPORTS
        # ═══════════════════════════════════════════
        if cmd in CODE_LANGS:
            ext, mime, lang_key = CODE_LANGS[cmd]
            blocks = self._extract_code_blocks(original_text, lang_key)
            if not blocks:
                blocks = self._extract_code_blocks(original_text, cmd)
            if not blocks:
                if __event_emitter__:
                    await __event_emitter__(
                        {
                            "type": "notification",
                            "data": {
                                "type": "warning",
                                "content": f"No {cmd} code blocks found in this message.",
                            },
                        }
                    )
                return {"status": "success"}
            selected = await self._select_code_blocks(
                blocks, __event_call__, cmd.upper()
            )
            if len(selected) == 1:
                _, code, _ = selected[0]
                default_fn = self._get_smart_filename(body, code, ext)
                filename = await self._ask_filename(__event_call__, default_fn)
                widget = self._build_download_widget(
                    code, filename, mime, f"{cmd.upper()} file exported", self.ICON_CODE
                )
                await self._emit_widget(
                    __event_emitter__, widget, f"{cmd.upper()} Export"
                )
            else:
                for i, (_, code, preview) in enumerate(selected, 1):
                    fn = self._get_smart_filename(body, code, ext)
                    base = fn.rsplit(".", 1)[0]
                    fn = f"{base}_{i}.{ext}"
                    widget = self._build_download_widget(
                        code, fn, mime, f"Block {i}: {preview[:40]}", self.ICON_CODE
                    )
                    await self._emit_widget(
                        __event_emitter__, widget, f"{cmd.upper()} #{i}"
                    )
            return {"status": "success"}

        # ═══════════════════════════════════════════
        # ROUTE: WEB BUNDLE
        # ═══════════════════════════════════════════
        if cmd == "web":
            web_blocks = self._detect_web_blocks(original_text)
            if not web_blocks:
                if __event_emitter__:
                    await __event_emitter__(
                        {
                            "type": "notification",
                            "data": {
                                "type": "warning",
                                "content": "No web code blocks (HTML/CSS/JS/PHP) found.",
                            },
                        }
                    )
                return {"status": "success"}
            summary_lines = [
                f"Found web blocks: {', '.join(f'{k} ({len(v)})' for k, v in web_blocks.items())}\n"
            ]
            all_items = []
            for lang, items in web_blocks.items():
                for idx, (code, preview) in enumerate(items):
                    label = f"{lang}" if len(items) == 1 else f"{lang}_{idx+1}"
                    all_items.append((label, lang, code, preview))
                    summary_lines.append(f"  {len(all_items)}. [{lang}] {preview[:50]}")
            summary_lines.append("\nType numbers to include (e.g. '1,2,3'), or 'all'.")
            sel = await __event_call__(
                {
                    "type": "input",
                    "data": {
                        "title": "Select Web Files",
                        "message": "\n".join(summary_lines),
                        "placeholder": "all",
                    },
                }
            )
            if (
                not sel
                or not isinstance(sel, str)
                or sel.strip().lower() in ("all", "")
            ):
                chosen = all_items
            else:
                try:
                    idx = [
                        int(x.strip()) - 1
                        for x in sel.split(",")
                        if x.strip().isdigit()
                    ]
                    chosen = [all_items[i] for i in idx if 0 <= i < len(all_items)]
                    if not chosen:
                        chosen = all_items
                except Exception:
                    chosen = all_items
            ext_map = {
                "javascript": "js",
                "typescript": "ts",
                "jsx": "jsx",
                "tsx": "tsx",
                "scss": "scss",
                "sass": "sass",
                "less": "less",
            }
            files = {}
            for label, lang, code, _ in chosen:
                e = ext_map.get(lang, lang)
                fn = f"{label}.{e}" if f".{e}" not in label else label
                files[fn] = code
            archive = self._get_smart_filename(body, original_text, "zip")
            widget = self._build_web_bundle_widget(files, archive)
            await self._emit_widget(__event_emitter__, widget, "Web Bundle")
            return {"status": "success"}

        # ═══════════════════════════════════════════
        # ROUTE: TEXT FORMAT EXPORTS
        # ═══════════════════════════════════════════
        if cmd in TEXT_FORMATS:
            ext, mime = TEXT_FORMATS[cmd]
            if cmd in ("json", "csv", "xml", "yaml", "yml", "toml", "sql"):
                blocks = self._extract_code_blocks(original_text, cmd)
                if blocks:
                    selected = await self._select_code_blocks(
                        blocks, __event_call__, cmd.upper()
                    )
                    content = "\n\n".join(code for _, code, _ in selected)
                else:
                    content = re.sub(
                        r"<details.*?</details>", "", original_text, flags=re.DOTALL
                    ).strip()
            else:
                content = re.sub(
                    r"<details.*?</details>", "", original_text, flags=re.DOTALL
                ).strip()
            default_fn = self._get_smart_filename(body, content, ext)
            filename = await self._ask_filename(__event_call__, default_fn)
            widget = self._build_download_widget(
                content, filename, mime, f"{ext.upper()} file exported"
            )
            await self._emit_widget(__event_emitter__, widget, f"{ext.upper()} Export")
            return {"status": "success"}

        # ═══════════════════════════════════════════
        # ROUTE: TTS READ ALOUD
        # ═══════════════════════════════════════════
        if cmd in ("read", "tts", "read aloud", "speak"):
            return await self._handle_tts(
                body, original_text, __event_emitter__, __request__
            )

        # ═══════════════════════════════════════════
        # ROUTE: TRANSLATION (default fallback)
        # ═══════════════════════════════════════════
        return await self._handle_translation(
            body, original_text, user_input.strip(), __event_emitter__, __request__
        )

    # ─────────────────── TTS HANDLER ───────────────────

    async def _handle_tts(self, _body, text, __event_emitter__, __request__):
        """Build and emit the TTS read-aloud player widget.
        Audio is generated server-side and passed as base64 data URIs to the widget.
        """
        import base64

        clean = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
        clean = re.sub(r"<details.*?</details>", "", clean, flags=re.DOTALL)
        clean = re.sub(r"<think.*?</think>", "", clean, flags=re.DOTALL)
        clean = re.sub(r"[#*_`>\-\[\]\(\)!|]", "", clean)
        clean = re.sub(r"\n{3,}", "\n\n", clean).strip()

        if not clean:
            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "notification",
                        "data": {
                            "type": "warning",
                            "content": "No readable text found in this message.",
                        },
                    }
                )
            return {"status": "success"}

        base_url = (
            str(__request__.base_url).rstrip("/")
            if __request__
            else "http://localhost:8080"
        )
        tts_key = self.valves.TTS_API_KEY
        if not tts_key and __request__ and "Authorization" in __request__.headers:
            tts_key = __request__.headers["Authorization"].replace("Bearer ", "")
        voices = [v.strip() for v in self.valves.TTS_VOICES.split(",") if v.strip()]
        default_voice = self.valves.TTS_DEFAULT_VOICE
        tts_model = self.valves.TTS_DEFAULT_MODEL

        # Build the TTS speech URL — handle various base URL formats:
        #   http://host:port/v1           → .../v1/audio/speech
        #   http://host:port/v1/audio     → .../v1/audio/speech
        #   http://host:port/v1/audio/speech → use as-is
        #   (empty)                       → Open WebUI built-in endpoint
        raw_base = self.valves.TTS_API_BASE_URL.strip().rstrip("/")
        if not raw_base:
            tts_url = f"{base_url}/api/v1/audio/speech"
        elif raw_base.endswith("/speech"):
            tts_url = raw_base
        elif raw_base.endswith("/audio"):
            tts_url = f"{raw_base}/speech"
        else:
            tts_url = f"{raw_base}/audio/speech"

        # Split into paragraphs
        paragraphs = [p.strip() for p in re.split(r"\n\n+", clean) if p.strip()]
        if not paragraphs:
            paragraphs = [clean]

        # Notify user
        if __event_emitter__:
            await __event_emitter__(
                {
                    "type": "notification",
                    "data": {
                        "type": "info",
                        "content": f"Generating audio for {len(paragraphs)} paragraph(s)…",
                    },
                }
            )

        # Fetch audio for each paragraph server-side
        audio_data_list = []
        tts_errors = []
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=60)
        ) as session:
            for idx, para_text in enumerate(paragraphs):
                try:
                    tts_payload = {
                        "input": para_text,
                        "voice": default_voice,
                        "model": tts_model,
                    }
                    tts_headers = {"Content-Type": "application/json"}
                    if tts_key:
                        tts_headers["Authorization"] = f"Bearer {tts_key}"
                    async with session.post(
                        tts_url, headers=tts_headers, json=tts_payload
                    ) as resp:
                        if resp.status == 200:
                            audio_bytes = await resp.read()
                            content_type = resp.headers.get(
                                "Content-Type", "audio/mpeg"
                            )
                            mime = (
                                "audio/mpeg"
                                if "mpeg" in content_type or "mp3" in content_type
                                else content_type.split(";")[0]
                            )
                            b64 = base64.b64encode(audio_bytes).decode("ascii")
                            audio_data_list.append(f"data:{mime};base64,{b64}")
                        else:
                            err_body = await resp.text()
                            tts_errors.append(
                                f"P{idx+1}: {resp.status} {err_body[:120]}"
                            )
                            audio_data_list.append("")
                except Exception as exc:
                    tts_errors.append(
                        f"P{idx+1}: {type(exc).__name__}: {str(exc)[:120]}"
                    )
                    audio_data_list.append("")

        if tts_errors and __event_emitter__:
            err_detail = "; ".join(tts_errors[:3])
            await __event_emitter__(
                {
                    "type": "notification",
                    "data": {
                        "type": "error",
                        "content": f"TTS errors at {tts_url} — {err_detail}",
                    },
                }
            )

        # Encode data for the widget
        para_json = urllib.parse.quote(json.dumps(paragraphs))
        audio_json = urllib.parse.quote(json.dumps(audio_data_list))
        voices_json = urllib.parse.quote(json.dumps(voices))
        tc = self._theme_css("#3b82f6", "#60a5fa")
        tj = self._theme_js()

        # SVG icons (no emojis)
        play_icon = '<svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18"><polygon points="6,3 20,12 6,21"/></svg>'
        pause_icon = '<svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18"><rect x="5" y="3" width="4" height="18"/><rect x="15" y="3" width="4" height="18"/></svg>'
        prev_icon = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M6 6h2v12H6zm3.5 6l8.5 6V6z"/></svg>'
        next_icon = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M16 6h2v12h-2zm-10 6l8.5 6V6z" transform="scale(-1,1) translate(-24,0)"/></svg>'
        text_icon = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 6h16M4 12h16M4 18h10"/></svg>'

        # Build the HTML — use .replace() to inject JS to avoid f-string brace hell
        css_block = f"""<meta name="color-scheme" content="light dark">
<style>{tc}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:system-ui,-apple-system,sans-serif;background:transparent;color:var(--text);overflow:hidden;padding:4px}}
.player{{border:1px solid var(--border);border-radius:14px;background:var(--bg);overflow:hidden}}
.controls{{display:flex;align-items:center;gap:6px;padding:10px 14px;background:var(--surface);flex-wrap:wrap}}
.btn{{background:var(--surface-hover);border:1px solid var(--border);color:var(--text);border-radius:8px;padding:6px 10px;font-size:12px;cursor:pointer;transition:all .15s;display:flex;align-items:center;justify-content:center;gap:4px;white-space:nowrap;min-width:32px;height:32px}}
.btn:hover{{background:var(--border)}}
.btn svg{{width:14px;height:14px;flex-shrink:0}}
.play-btn{{min-width:38px;height:38px;border-radius:50%;background:var(--accent);color:#fff;border:none;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:opacity .15s}}
.play-btn:hover{{opacity:.85}}
select{{-webkit-appearance:none;appearance:none;border:1px solid var(--border);border-radius:8px;padding:6px 28px 6px 10px;font-size:12px;height:32px;cursor:pointer;max-width:120px;font-family:inherit;background-repeat:no-repeat;background-position:right 8px center;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6'%3E%3Cpath d='M0 0l5 6 5-6z' fill='%23888'/%3E%3C/svg%3E")}}
:root[data-theme="light"] select{{background:#f8f9fa;color:#1a1a2e;color-scheme:light}}
:root[data-theme="light"] select option{{background:#ffffff;color:#1a1a2e}}
:root[data-theme="dark"] select{{background:#2a2a3c;color:#e4e4e7;color-scheme:dark}}
:root[data-theme="dark"] select option{{background:#2a2a3c;color:#e4e4e7}}
select:focus{{outline:2px solid var(--accent);outline-offset:-1px}}
.progress-wrap{{flex:1;min-width:80px;height:6px;background:var(--surface-hover);border-radius:3px;cursor:pointer;position:relative}}
.progress-fill{{height:100%;background:var(--accent);border-radius:3px;transition:width .1s linear;width:0}}
.time{{font-size:11px;color:var(--text-muted);white-space:nowrap;min-width:70px;text-align:center}}
.expand-btn{{margin-left:auto}}
.text-area{{display:none;padding:16px;max-height:350px;overflow-y:auto;line-height:1.8;font-size:14.5px;border-top:1px solid var(--border)}}
.text-area.show{{display:block}}
.para{{padding:6px 10px;border-radius:8px;margin-bottom:6px;cursor:pointer;transition:background .2s}}
.para:hover{{background:var(--surface-hover)}}
.para.active{{background:var(--accent-soft);border-left:3px solid var(--accent)}}
.word{{display:inline;border-radius:3px;transition:background .15s,color .15s;padding:0 1px}}
.word.active{{background:var(--accent);color:#fff;border-radius:4px;padding:1px 3px}}
.loading{{display:none;align-items:center;gap:8px;padding:10px 14px;font-size:13px;color:var(--text-muted);border-top:1px solid var(--border)}}
.loading.show{{display:flex}}
.spinner{{width:16px;height:16px;border:2px solid var(--border);border-top-color:var(--accent);border-radius:50%;animation:spin .6s linear infinite}}
@keyframes spin{{to{{transform:rotate(360deg)}}}}
.err-msg{{padding:10px 14px;font-size:12px;color:var(--accent);border-top:1px solid var(--border);display:none}}
.err-msg.show{{display:block}}
</style>"""

        html_body = f"""<div class="player">
 <div class="controls">
  <button class="play-btn" id="playBtn" title="Play/Pause">{play_icon}</button>
  <button class="btn" id="prevBtn" title="Previous paragraph">{prev_icon}</button>
  <button class="btn" id="bk5Btn" title="Back 5s">-5s</button>
  <div class="progress-wrap" id="progWrap"><div class="progress-fill" id="progFill"></div></div>
  <button class="btn" id="fw5Btn" title="Forward 5s">+5s</button>
  <button class="btn" id="nextBtn" title="Next paragraph">{next_icon}</button>
  <span class="time" id="timeDisp">0:00 / 0:00</span>
  <select id="speedSel" title="Speed">
   <option value="0.5">0.5x</option><option value="0.75">0.75x</option><option value="1" selected>1x</option>
   <option value="1.25">1.25x</option><option value="1.5">1.5x</option><option value="2">2x</option>
  </select>
  <select id="voiceSel" title="Voice"></select>
  <button class="btn expand-btn" id="expandBtn" title="Show/hide text">{text_icon}</button>
 </div>
 <div class="err-msg" id="errMsg"></div>
 <div class="text-area" id="textArea"></div>
</div>"""

        # Build JS as a plain string, then inject. No f-string brace issues.
        js_code = """
var PARAS=JSON.parse(decodeURIComponent("__PARA_JSON__"));
var AUDIO_URLS=JSON.parse(decodeURIComponent("__AUDIO_JSON__"));
var VOICES=JSON.parse(decodeURIComponent("__VOICES_JSON__"));
var DEF_VOICE="__DEF_VOICE__";
var TTS_BASE="__TTS_BASE__";
var TTS_KEY="__TTS_KEY__";
var TTS_MODEL="__TTS_MODEL__";
var PLAY_SVG='__PLAY_ICON__';
var PAUSE_SVG='__PAUSE_ICON__';

var curPara=0,playing=false,currentAudio=null,wordTimer=null,curWordIdx=-1;
var paraAudios=[],paraDurations=[],totalDuration=0,voice=DEF_VOICE;

// Init voice selector
var voiceSel=document.getElementById('voiceSel');
VOICES.forEach(function(v){var o=document.createElement('option');o.value=v;o.textContent=v;if(v===DEF_VOICE)o.selected=true;voiceSel.appendChild(o)});

// Build text display with word spans
var textArea=document.getElementById('textArea');
PARAS.forEach(function(p,i){
  var div=document.createElement('div');div.className='para';div.dataset.idx=i;
  var words=p.split(/\\s+/);
  words.forEach(function(w,j){
    var span=document.createElement('span');span.className='word';span.dataset.pi=i;span.dataset.wi=j;
    span.textContent=w+' ';
    div.appendChild(span);
  });
  textArea.appendChild(div);
});

// Event delegation for text area clicks
textArea.addEventListener('click',function(e){
  var wordEl=e.target.closest('.word');
  if(wordEl){
    e.stopPropagation();
    var pi=parseInt(wordEl.dataset.pi);
    var wi=parseInt(wordEl.dataset.wi);
    if(pi===curPara){jumpToWord(pi,wi)}
    else{jumpToPara(pi)}
    return;
  }
  var paraEl=e.target.closest('.para');
  if(paraEl){jumpToPara(parseInt(paraEl.dataset.idx))}
});

// Load audio from pre-fetched data URIs
function loadAudioFromData(){
  paraAudios=[];paraDurations=[];totalDuration=0;
  var loaded=0,total=AUDIO_URLS.length;
  var errCount=0;
  return new Promise(function(resolve){
    if(!total){resolve();return}
    AUDIO_URLS.forEach(function(url,i){
      if(!url){paraAudios[i]=null;paraDurations[i]=0;loaded++;errCount++;if(loaded===total)resolve();return}
      var audio=new Audio(url);
      audio.addEventListener('loadedmetadata',function(){
        var dur=isFinite(audio.duration)?audio.duration:PARAS[i].split(/\\s+/).length*0.35;
        paraAudios[i]=audio;paraDurations[i]=dur;totalDuration+=dur;
        loaded++;if(loaded===total)resolve();
      });
      audio.addEventListener('error',function(){
        paraAudios[i]=null;paraDurations[i]=0;loaded++;errCount++;if(loaded===total)resolve();
      });
      setTimeout(function(){if(loaded<total){if(!paraAudios[i]){paraAudios[i]=null;paraDurations[i]=0;loaded++;if(loaded===total)resolve()}}},5000);
    });
  }).then(function(){
    updateTimeDisplay();
    if(errCount>0&&errCount===total){
      var em=document.getElementById('errMsg');em.textContent='Audio generation failed. Check your TTS valve settings (API URL, key, model, voice).';em.classList.add('show');
    }
  });
}

function getParaStartTime(idx){var t=0;for(var i=0;i<idx;i++)t+=(paraDurations[i]||0);return t}

function updateTimeDisplay(){
  var cur=getParaStartTime(curPara)+(currentAudio?currentAudio.currentTime:0);
  document.getElementById('timeDisp').textContent=fmt(cur)+' / '+fmt(totalDuration);
  var pct=totalDuration>0?(cur/totalDuration)*100:0;
  document.getElementById('progFill').style.width=pct+'%';
}

function fmt(s){var m=Math.floor(s/60);var sec=Math.floor(s%60);return m+':'+(sec<10?'0':'')+sec}

function highlightPara(idx){
  document.querySelectorAll('.para').forEach(function(p){p.classList.remove('active')});
  var el=textArea.children[idx];if(el){el.classList.add('active');el.scrollIntoView({behavior:'smooth',block:'nearest'})}
}

function highlightWord(pi,wi){
  document.querySelectorAll('.word.active').forEach(function(w){w.classList.remove('active')});
  if(pi<0||wi<0)return;
  var para=textArea.children[pi];if(!para)return;
  var wordEl=para.querySelectorAll('.word')[wi];
  if(wordEl){wordEl.classList.add('active');wordEl.scrollIntoView({behavior:'smooth',block:'nearest'})}
}

function startWordHighlighting(){
  stopWordHighlighting();
  if(!currentAudio||curPara>=PARAS.length)return;
  var words=PARAS[curPara].split(/\\s+/);
  var dur=paraDurations[curPara];
  if(!words.length||!dur)return;
  var wps=dur/words.length;
  curWordIdx=Math.floor(currentAudio.currentTime/wps);
  highlightWord(curPara,curWordIdx);
  wordTimer=setInterval(function(){
    if(!currentAudio||currentAudio.paused)return;
    var wi=Math.floor(currentAudio.currentTime/wps);
    if(wi!==curWordIdx&&wi<words.length){curWordIdx=wi;highlightWord(curPara,wi)}
    updateTimeDisplay();
  },80);
}

function stopWordHighlighting(){if(wordTimer){clearInterval(wordTimer);wordTimer=null}}

function playPara(idx){
  if(idx>=PARAS.length){stopPlayback();return}
  curPara=idx;highlightPara(idx);
  var audio=paraAudios[idx];
  if(!audio){curPara=idx+1;playPara(curPara);return}
  currentAudio=audio;audio.playbackRate=parseFloat(document.getElementById('speedSel').value);
  audio.currentTime=0;
  audio.onended=function(){stopWordHighlighting();curPara=idx+1;playPara(curPara)};
  audio.play().catch(function(){});
  startWordHighlighting();
}

function togglePlay(){
  if(!paraAudios.length){return}
  if(playing){
    if(currentAudio)currentAudio.pause();
    stopWordHighlighting();playing=false;
    document.getElementById('playBtn').innerHTML=PLAY_SVG;
  }else{
    playing=true;document.getElementById('playBtn').innerHTML=PAUSE_SVG;
    if(currentAudio&&currentAudio.paused&&currentAudio.currentTime>0){
      currentAudio.play().catch(function(){});
      startWordHighlighting();
    }else{playPara(curPara)}
  }
}

function stopPlayback(){
  playing=false;stopWordHighlighting();
  document.getElementById('playBtn').innerHTML=PLAY_SVG;
  highlightWord(-1,-1);curPara=0;updateTimeDisplay();
}

function prevPara(){if(curPara>0)jumpToPara(curPara-1)}
function nextPara(){if(curPara<PARAS.length-1)jumpToPara(curPara+1)}

function jumpToPara(idx){
  if(currentAudio){currentAudio.pause();currentAudio.currentTime=0}
  stopWordHighlighting();curPara=idx;highlightPara(idx);
  if(playing)playPara(idx);else updateTimeDisplay();
}

function jumpToWord(pi,wi){
  if(!paraAudios.length)return;
  if(currentAudio){currentAudio.pause()}
  stopWordHighlighting();curPara=pi;highlightPara(pi);
  var audio=paraAudios[pi];
  if(!audio)return;
  currentAudio=audio;
  var words=PARAS[pi].split(/\\s+/);
  var wps=paraDurations[pi]/words.length;
  audio.currentTime=wi*wps;
  if(playing){audio.play().catch(function(){});startWordHighlighting()}
  else{curWordIdx=wi;highlightWord(pi,wi);updateTimeDisplay()}
}

function skip(sec){
  if(!currentAudio)return;
  currentAudio.currentTime=Math.max(0,Math.min(currentAudio.duration,currentAudio.currentTime+sec));
  updateTimeDisplay();
}

function seekClick(e){
  if(!totalDuration)return;
  var rect=e.currentTarget.getBoundingClientRect();
  var pct=(e.clientX-rect.left)/rect.width;
  var target=pct*totalDuration,acc=0;
  for(var i=0;i<PARAS.length;i++){
    if(acc+paraDurations[i]>target){
      var offset=target-acc;jumpToPara(i);
      setTimeout(function(){if(currentAudio)currentAudio.currentTime=offset},100);
      return;
    }
    acc+=paraDurations[i];
  }
}

function setSpeed(v){if(currentAudio)currentAudio.playbackRate=parseFloat(v)}

function changeVoice(v){
  // Voice change requires server-side re-generation; notify user
  var em=document.getElementById('errMsg');
  em.textContent='Voice change requires re-running the action with updated valve settings.';
  em.classList.add('show');setTimeout(function(){em.classList.remove('show')},4000);
}

function toggleText(){
  var ta=document.getElementById('textArea');ta.classList.toggle('show');
  setTimeout(setHeight,300);
}

// Event listeners
document.getElementById('playBtn').addEventListener('click',togglePlay);
document.getElementById('prevBtn').addEventListener('click',prevPara);
document.getElementById('nextBtn').addEventListener('click',nextPara);
document.getElementById('bk5Btn').addEventListener('click',function(){skip(-5)});
document.getElementById('fw5Btn').addEventListener('click',function(){skip(5)});
document.getElementById('progWrap').addEventListener('click',seekClick);
document.getElementById('speedSel').addEventListener('change',function(){setSpeed(this.value)});
document.getElementById('voiceSel').addEventListener('change',function(){changeVoice(this.value)});
document.getElementById('expandBtn').addEventListener('click',toggleText);

__THEME_JS__

window.onload=function(){
  initTheme();
  loadAudioFromData().then(function(){setHeight()});
  new ResizeObserver(setHeight).observe(document.body);
};
"""
        # Inject values via .replace() — avoids all f-string brace issues
        js_code = (
            js_code.replace("__PARA_JSON__", para_json)
            .replace("__AUDIO_JSON__", audio_json)
            .replace("__VOICES_JSON__", voices_json)
            .replace("__DEF_VOICE__", default_voice)
            .replace("__TTS_BASE__", tts_url)
            .replace("__TTS_KEY__", tts_key)
            .replace("__TTS_MODEL__", tts_model)
            .replace("__PLAY_ICON__", play_icon.replace("'", "\\'"))
            .replace("__PAUSE_ICON__", pause_icon.replace("'", "\\'"))
            .replace("__THEME_JS__", tj)
        )

        tts_html = f"<!DOCTYPE html><html><head>{css_block}</head><body>{html_body}<script>{js_code}</script></body></html>"

        await self._emit_widget(__event_emitter__, tts_html, "Read Aloud")
        return {"status": "success"}

    # ─────────────────── TRANSLATION HANDLER ───────────────────

    async def _handle_translation(
        self, body, original_text, target_lang, __event_emitter__, __request__
    ):
        """Perform translation and emit the rich translation widget."""
        if __event_emitter__:
            await __event_emitter__(
                {
                    "type": "notification",
                    "data": {
                        "type": "info",
                        "content": f"Translating to {target_lang}…",
                    },
                }
            )

        clean_text = re.sub(
            r"<details.*?</details>", "", original_text, flags=re.DOTALL
        )
        clean_text = re.sub(r"<think.*?</think>", "", clean_text, flags=re.DOTALL)
        code_blocks: list = []

        def mask_code(match):
            code_blocks.append(match.group(0))
            return f"[[CODE_BLOCK_{len(code_blocks)-1}]]"

        masked_text = re.sub(r"```.*?```", mask_code, clean_text, flags=re.DOTALL)

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
        is_rtl = any(r in target_lang.lower() for r in rtl_languages)

        model_to_use = (
            self.valves.TRANSLATION_MODEL
            if self.valves.TRANSLATION_MODEL
            else body.get("model", "")
        )
        headers = {"Content-Type": "application/json"}
        if __request__ and "Authorization" in __request__.headers:
            headers["Authorization"] = __request__.headers["Authorization"]

        payload = {
            "model": model_to_use,
            "messages": [
                {
                    "role": "system",
                    "content": f"[RULE] You are a professional translator. [INSTRUCTION] Translate the user's text into {target_lang}. [OUTPUT] - Output ONLY the translated text. - Maintain all original markdown formatting. [EXCLUDE] - Any <details type= ... </details> or similar block. [DO NOT TRANSLATE] - Anything inside Code Blocks(```code```) including comments.",
                },
                {"role": "user", "content": masked_text},
            ],
            "stream": False,
        }

        is_error = False
        translated_text = ""
        try:
            base_url = (
                str(__request__.base_url).rstrip("/")
                if __request__
                else "http://localhost:8080"
            )
            api_url = f"{base_url}/api/chat/completions"
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=120)
            ) as session:
                async with session.post(
                    api_url, headers=headers, json=payload
                ) as response:
                    if response.status != 200:
                        body_text = await response.text()
                        raise Exception(
                            f"{response.status} {response.reason} - {body_text[:200]}"
                        )
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

        # Build the translation widget
        if is_error:
            widget_title = "Translation Error"
            icon_svg = '<svg class="ti" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>'
            cl, cd = "#ef4444", "#f87171"
            cdir, calign = "ltr", "left"
            copy_html = ""
        else:
            widget_title = f"Translation ({target_lang})"
            icon_svg = '<svg class="ti" width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="m12.87 15.07-2.54-2.51.03-.03A17.5 17.5 0 0014.07 6H17V4h-7V2H8v2H1v2h11.17C11.5 7.92 10.44 9.75 9 11.35 8.07 10.32 7.3 9.19 6.69 8h-2c.73 1.63 1.73 3.17 2.98 4.56l-5.09 5.02L4 19l5-5 3.11 3.11zM18.5 10h-2L12 22h2l1.12-3h4.75L21 22h2zm-2.62 7l1.62-4.33L19.12 17z"/></svg>'
            cl, cd = "#10b981", "#34d399"
            cdir = "rtl" if is_rtl else "ltr"
            calign = "right" if is_rtl else "left"
            copy_html = '<button class="ab" id="copyBtn" onclick="copyText(event)"><svg fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/></svg>Copy</button>'

        enc = urllib.parse.quote(translated_text)
        tc = self._theme_css(cl, cd)
        tj = self._theme_js()

        html_doc = f"""<!DOCTYPE html><html><head>
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<style>{tc}
body{{margin:0;padding:4px;font-family:system-ui,sans-serif;background:transparent;color:var(--text);overflow:hidden}}
.widget{{border:1px solid var(--border);border-radius:12px;background:var(--bg);overflow:hidden}}
.header{{display:flex;justify-content:space-between;align-items:center;padding:12px 16px;background:var(--surface);cursor:pointer;user-select:none;border-bottom:1px solid transparent;transition:background .2s,border-color .2s}}
.header:hover{{background:var(--surface-hover)}} .header.open{{border-bottom-color:var(--border)}}
.title{{font-weight:600;font-size:14px;display:flex;align-items:center;gap:8px}}
.ti{{color:var(--accent)}}
.actions{{display:flex;align-items:center;gap:8px}}
.ab{{background:transparent;border:1px solid var(--border);color:var(--text);border-radius:6px;padding:4px 10px;font-size:12px;cursor:pointer;transition:all .2s;display:flex;align-items:center;gap:4px}}
.ab:hover{{background:var(--border)}} .ab svg{{width:14px;height:14px}}
.chev{{transition:transform .3s;width:16px;height:16px;color:var(--text-muted);margin-left:4px}}
.chev.open{{transform:rotate(180deg)}}
.cw{{display:grid;grid-template-rows:1fr;transition:grid-template-rows .3s ease-out}}
.cw.collapsed{{grid-template-rows:0fr}} .ci{{overflow:hidden}}
.content{{padding:16px;font-size:14.5px;line-height:1.6;word-break:break-word;direction:{cdir};text-align:{calign}}}
.markdown-body p{{margin:0 0 12px}} .markdown-body p:last-child{{margin-bottom:0}}
.markdown-body a{{color:var(--accent);text-decoration:none}} .markdown-body a:hover{{text-decoration:underline}}
.markdown-body code{{background:var(--surface-hover);padding:3px 6px;border-radius:4px;font-family:monospace;font-size:90%}}
.markdown-body pre{{background:var(--surface);border:1px solid var(--border);padding:12px;border-radius:8px;overflow-x:auto;direction:ltr;text-align:left;position:relative}}
.markdown-body pre code{{background:transparent;padding:0;font-size:13px}}
.markdown-body blockquote{{margin:0 0 12px;padding:4px 16px;color:var(--text-muted)}}
.content[dir="ltr"] blockquote{{border-left:4px solid var(--border)}}
.content[dir="rtl"] blockquote{{border-right:4px solid var(--border)}}
.markdown-body table{{border-collapse:collapse;width:100%;margin-bottom:12px;font-size:14px}}
.markdown-body th,.markdown-body td{{border:1px solid var(--border);padding:8px 12px;text-align:{calign}}}
.markdown-body th{{background:var(--surface);font-weight:600}}
.markdown-body ul,.markdown-body ol{{margin:0 0 12px;padding-inline-start:24px}}
.markdown-body img{{max-width:100%;border-radius:8px}}
.markdown-body h1,.markdown-body h2,.markdown-body h3,.markdown-body h4{{margin:16px 0 8px}}
.tw{{position:relative;overflow-x:auto;margin-bottom:12px}} .markdown-body table{{margin-bottom:0}}
.bcb{{position:absolute;top:4px;right:4px;background:var(--surface);border:1px solid var(--border);color:var(--text-muted);border-radius:4px;padding:4px;cursor:pointer;opacity:0;transition:opacity .2s;display:flex}}
.markdown-body pre:hover .bcb,.tw:hover .bcb{{opacity:1}} .bcb:hover{{color:var(--text);background:var(--surface-hover)}} .bcb svg{{width:14px;height:14px}}
</style></head><body>
<div class="widget">
 <div class="header open" id="header" onclick="toggle()">
  <div class="title">{icon_svg} {widget_title}</div>
  <div class="actions">{copy_html}
   <svg class="chev open" id="chev" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7"/></svg>
  </div>
 </div>
 <div class="cw" id="wrapper"><div class="ci"><div class="content markdown-body" id="text" dir="{cdir}"></div></div></div>
</div>
<script>
const rawText=decodeURIComponent("{enc}");
marked.use({{gfm:true,breaks:true}});document.getElementById('text').innerHTML=marked.parse(rawText);
const CI='<svg fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/></svg>';
const CK='<svg fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>';
document.querySelectorAll('.markdown-body pre').forEach(pre=>{{const b=document.createElement('button');b.className='bcb';b.innerHTML=CI;b.title='Copy';b.onclick=async e=>{{e.stopPropagation();await navigator.clipboard.writeText(pre.querySelector('code').innerText);b.innerHTML=CK;setTimeout(()=>b.innerHTML=CI,2000)}};pre.appendChild(b)}});
document.querySelectorAll('.markdown-body table').forEach(tbl=>{{const w=document.createElement('div');w.className='tw';tbl.parentNode.insertBefore(w,tbl);w.appendChild(tbl);const b=document.createElement('button');b.className='bcb';b.innerHTML=CI;b.title='Copy table';b.onclick=async e=>{{e.stopPropagation();let md=Array.from(tbl.rows).map((r,i)=>{{let c=Array.from(r.cells).map(c=>c.innerText.trim());let s='| '+c.join(' | ')+' |';if(i===0)s+='\\n|'+c.map(()=>'---').join('|')+'|';return s}}).join('\\n');await navigator.clipboard.writeText(md);b.innerHTML=CK;setTimeout(()=>b.innerHTML=CI,2000)}};w.appendChild(b)}});
function toggle(){{document.getElementById('wrapper').classList.toggle('collapsed');document.getElementById('chev').classList.toggle('open');document.getElementById('header').classList.toggle('open');setTimeout(setHeight,300)}}
async function copyText(e){{if(!rawText)return;e.stopPropagation();const b=document.getElementById('copyBtn');try{{await navigator.clipboard.writeText(rawText);const o=b.innerHTML;b.innerHTML=CK+' Copied!';setTimeout(()=>b.innerHTML=o,2000)}}catch(er){{}}}}
{tj}
window.onload=()=>{{initTheme();setTimeout(setHeight,100);new ResizeObserver(setHeight).observe(document.body)}};
</script></body></html>"""

        await self._emit_widget(__event_emitter__, html_doc, "View Translation")
        return {"status": "success"}
