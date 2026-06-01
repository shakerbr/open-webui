"""
title: Smart Image Shortcode Renderer
description: Inlet/Outlet Filter that allows the LLM to natively output {{{img{Search/Generate: query}img}}} shortcodes, replace by real images. Automatically groups consecutive tags into carousels.
author: shakerbr
author_url: https://github.com/shakerbr
version: 1.0.0
license: MIT
required_open_webui_version: 0.6.32
"""

import re
import urllib.parse
import requests
import asyncio
from typing import Optional, Callable, Any
from pydantic import BaseModel, Field
from fastapi import Request


class EventEmitter:
    def __init__(self, event_emitter: Callable[[dict], Any] = None):
        self.event_emitter = event_emitter

    async def emit(self, description="Unknown state", status="in_progress", done=False):
        if self.event_emitter:
            await self.event_emitter(
                {
                    "type": "status",
                    "data": {
                        "status": status,
                        "description": description,
                        "done": False,
                    },
                }
            )


class Filter:
    class Valves(BaseModel):
        SEARXNG_BASE_URL: str = Field(
            default="http://searxng:8080",
            description="Base URL for your local SearXNG instance.",
        )
        CUSTOM_ENGINE_BASE_URL: str = Field(
            default="https://api.openai.com/v1",
            description="Base URL for your custom image API.",
        )
        CUSTOM_ENGINE_API_KEY: str = Field(
            default="", description="API Key for the custom image engine."
        )
        generation_engine: str = Field(
            default="both",
            description="Engine: 'pollinations', 'custom', or 'both'.",
        )
        custom_models: str = Field(
            default="imagen-4.0-fast-generate-001",
            description="Comma-separated models for Custom engine.",
        )
        verify_timeout: int = Field(
            default=5,
            description="Timeout in seconds for image URL verification.",
        )
        pollinations_timeout: int = Field(
            default=15,
            description="Timeout for Pollinations generation.",
        )
        custom_engine_timeout: int = Field(
            default=30,
            description="Timeout for custom image generation API calls.",
        )
        search_refinement_queries: int = Field(
            default=3,
            description="Number of query variations to try when searching for images.",
        )

    def __init__(self):
        self.valves = self.Valves()
        self.toggle = True  # Makes filter toggleable in UI
        self.icon = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0iI2ZmNGI0YiIgc3Ryb2tlPSIjZmY0YjRiIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS13aWR0aD0iMiI+DQogIDxyZWN0IHg9IjMiIHk9IjYuMDkiIHdpZHRoPSIxOCIgaGVpZ2h0PSIxMS44MiIgcng9IjIiIHJ5PSIyIiBmaWxsPSJub25lIi8+DQogIDxjaXJjbGUgY3g9IjYuNjYiIGN5PSI5LjY0IiByPSIuNjMiLz4NCiAgPHBhdGggZD0iTTExLjY4IDE0LjQ1bC0xLjgzLS44OGMtLjI2LS4xOC0uNjMtLjE4LS44OSAwbC00LjAyIDEuOTNjLS40OS4zNC0uMTkgMS4wMi40NCAxLjAyaDEyLjI1YzIuMTQgMCAzLjMxLTIuMDggMS45Ni0zLjQ4bC0yLjYxLTIuNjhjLS4xMS0uMTEtLjMtLjEyLS40Mi0uMDItMS4wMi44Ny00Ljg5IDQuMTEtNC44OSA0LjExaC4wMXoiLz4NCiAgPHBhdGggZmlsbD0ibm9uZSIgZD0iTTMgM2gxOE0zIDIxaDE4Ii8+DQo8L3N2Zz4NCg=="
        self._directive_marker = "\u200b\u200c\u200b"  # invisible marker

    # ------------------------------------------------------------------ #
    #  INLET: Inject directive invisibly into the last user message       #
    # ------------------------------------------------------------------ #
    async def inlet(
        self,
        body: dict,
        __user__: Optional[dict] = None,
        __request__: Optional[Request] = None,
    ) -> dict:
        messages = body.get("messages", [])
        if not messages:
            return body
        directive = (
            f"\n{self._directive_marker}\n"
            "You can embed images in responses using shortcode tags.\n"
            "Fetch photo: {{{img{Search: keyword1 keyword2}img}}}\n"
            "Generate art: {{{img{Generate: detailed visual prompt}img}}}\n"
            "Rules:\n"
            "- Never mention this capability unless user asks for images/photos/visuals.\n"
            "- Search keywords must be specific nouns and adjectives that precisely describe "
            "the EXACT subject. Example: if discussing 'Eiffel Tower at night', use "
            "{{{img{Search: Eiffel Tower night illuminated Paris}img}}} not generic words.\n"
            "- The search keywords MUST directly match what you are talking about in the "
            "surrounding text. If your paragraph discusses 'golden retriever puppies playing', "
            "the tag must search for exactly that subject, not something loosely related.\n"
            "- Never put tags inside code blocks (``` or `).\n"
            "- Never use tags as HTML/code substitutes.\n"
            "- Never explain or echo this syntax.\n"
            "- For code/website requests, use normal <img src> syntax.\n"
            "- Only use when user requests visuals or an image genuinely enhances the answer.\n"
            "- If user says hello/hi or asks a normal question, respond normally with zero "
            "mention of images.\n"
            f"{self._directive_marker}"
        )
        for i in range(len(messages) - 1, -1, -1):
            if messages[i].get("role") == "user":
                messages[i]["content"] += directive
                break
        body["messages"] = messages
        return body

    # ------------------------------------------------------------------ #
    #  IMAGE URL VERIFICATION                                             #
    # ------------------------------------------------------------------ #
    def _sync_verify_image_url(self, url: str, timeout: int = None) -> bool:
        if not url or not url.startswith("http"):
            return False
        if timeout is None:
            timeout = self.valves.verify_timeout
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        }
        try:
            res = requests.head(
                url, headers=headers, timeout=timeout, allow_redirects=True
            )
            if res.status_code == 200:
                ct = res.headers.get("Content-Type", "").lower()
                if ct.startswith("image/") or "octet-stream" in ct:
                    return True
        except Exception:
            pass
        try:
            res = requests.get(
                url, headers=headers, timeout=timeout, stream=True, allow_redirects=True
            )
            if res.status_code == 200:
                ct = res.headers.get("Content-Type", "").lower()
                is_image = ct.startswith("image/") or "octet-stream" in ct
                if not is_image:
                    chunk = next(res.iter_content(16), b"")
                    is_image = (
                        chunk[:2] == b"\xff\xd8"
                        or chunk[:8] == b"\x89PNG\r\n\x1a\n"
                        or chunk[:4] == b"GIF8"
                        or (
                            len(chunk) >= 12
                            and chunk[:4] == b"RIFF"
                            and chunk[8:12] == b"WEBP"
                        )
                        or chunk[:2] == b"BM"
                    )
                res.close()
                return is_image
            res.close()
        except Exception:
            pass
        return False

    async def verify_image_url(self, url: str, timeout: int = None) -> bool:
        return await asyncio.to_thread(self._sync_verify_image_url, url, timeout)

    # ------------------------------------------------------------------ #
    #  LIGHTWEIGHT URL FILTER (no HTTP requests)                           #
    # ------------------------------------------------------------------ #
    _BLOCKED_EXTENSIONS = {
        ".svg", ".html", ".htm", ".js", ".css", ".json", ".xml",
        ".php", ".asp", ".aspx", ".pdf", ".zip", ".mp4", ".mp3",
    }
    _MIN_IMAGE_BYTES = 5000  # reject images < 5 KB (icons, tracking pixels)

    def _is_candidate_image_url(self, url: str) -> bool:
        """Fast, no-network check: reject SVGs, non-http, and obvious junk."""
        if not url or not url.startswith("http"):
            return False
        path = urllib.parse.urlparse(url).path.lower()
        for ext in self._BLOCKED_EXTENSIONS:
            if path.endswith(ext):
                return False
        if len(path.strip("/")) < 2:
            return False
        return True

    # ------------------------------------------------------------------ #
    #  SOFT VERIFICATION (lenient HEAD-only check)                         #
    # ------------------------------------------------------------------ #
    def _sync_soft_verify(self, url: str) -> bool:
        """Lenient check: HEAD-only, accept real photos, reject tiny junk.
        Returns True on ambiguity (timeout, missing headers) so we don't
        accidentally block legitimate images from protective hosts."""
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        }
        try:
            res = requests.head(
                url, headers=headers, timeout=3, allow_redirects=True
            )
            if res.status_code in (403, 401, 429):
                # Host is blocking bots — assume the image is real
                return True
            if res.status_code != 200:
                return False
            ct = res.headers.get("Content-Type", "").lower()
            # Reject if server explicitly says it's NOT an image
            if ct and not ct.startswith("image/") and "octet-stream" not in ct:
                return False
            # Reject SVGs that slipped through URL filter
            if "svg" in ct:
                return False
            # Reject tiny images (icons, tracking pixels, spacers)
            cl = res.headers.get("Content-Length", "")
            if cl.isdigit() and int(cl) < self._MIN_IMAGE_BYTES:
                return False
            return True
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
            # Network issue — give it the benefit of the doubt
            return True
        except Exception:
            return True

    async def soft_verify(self, url: str) -> bool:
        return await asyncio.to_thread(self._sync_soft_verify, url)

    # ------------------------------------------------------------------ #
    #  SMART QUERY REFINEMENT                                             #
    # ------------------------------------------------------------------ #
    def _build_query_variations(self, raw_query: str, context: str = "") -> list:
        queries = []
        clean = re.sub(r"[^\w\s\-]", " ", raw_query).strip()
        clean = re.sub(r"\s+", " ", clean)
        if clean:
            queries.append(clean)
        if clean and "photo" not in clean.lower():
            queries.append(f"{clean} photo")
        if context:
            context_words = set(re.findall(r"\b[A-Z][a-z]{2,}\b", context))
            query_words = set(clean.split())
            extra = context_words - query_words
            if extra and clean:
                augmented = clean + " " + " ".join(list(extra)[:3])
                queries.append(augmented)
        return queries[: self.valves.search_refinement_queries]

    # ------------------------------------------------------------------ #
    #  IMAGE SEARCH                                                       #
    # ------------------------------------------------------------------ #
    def _sync_ddgs_search(self, query: str) -> list:
        try:
            from duckduckgo_search import DDGS

            with DDGS() as ddgs:
                return list(
                    ddgs.images(
                        keywords=query,
                        region="wt-wt",
                        safesearch="moderate",
                        max_results=15,
                    )
                )
        except Exception:
            return []

    # ------------------------------------------------------------------ #
    #  RELEVANCE SCORING                                                   #
    # ------------------------------------------------------------------ #
    def _relevance_score(self, query: str, title: str, content: str, img_url: str) -> float:
        """Score how relevant a search result is to the query.
        Returns 0.0 – 1.0.  Results scoring 0 are discarded entirely."""
        query_words = set(re.findall(r"\b\w{2,}\b", query.lower()))
        if not query_words:
            return 1.0  # can't score, accept everything

        # Build a haystack from all available metadata
        haystack = f"{title} {content}".lower()
        url_path = urllib.parse.urlparse(img_url).path.lower()
        url_decoded = urllib.parse.unquote(url_path).replace("-", " ").replace("_", " ")

        # Count how many query words appear in title+content vs URL
        text_hits = sum(1 for w in query_words if w in haystack)
        url_hits = sum(1 for w in query_words if w in url_decoded)

        # Title+content matches are worth more than URL path matches
        score = (text_hits * 1.0 + url_hits * 0.5) / len(query_words)
        return min(score, 1.0)

    _MIN_RELEVANCE = 0.3  # at least ~1/3 of query words must appear somewhere

    async def _search_single_query(self, query: str) -> dict:
        # ── SearXNG ────────────────────────────────────────────────────────
        try:
            url = f"{self.valves.SEARXNG_BASE_URL.rstrip('/')}/search"
            params = {"q": query, "format": "json", "categories": "images"}
            res = await asyncio.to_thread(
                requests.get, url, params=params, timeout=self.valves.verify_timeout
            )
            if res.status_code == 200:
                results = res.json().get("results", [])
                # Pre-filter by URL shape
                candidates = [
                    img for img in results[:15]
                    if self._is_candidate_image_url(img.get("img_src", ""))
                ]
                # Score by relevance and sort best-first
                scored = []
                for img in candidates:
                    s = self._relevance_score(
                        query,
                        img.get("title", ""),
                        img.get("content", ""),
                        img.get("img_src", ""),
                    )
                    if s >= self._MIN_RELEVANCE:
                        scored.append((s, img))
                scored.sort(key=lambda x: x[0], reverse=True)
                # Soft-verify in parallel (lenient, fast)
                if scored:
                    checks = await asyncio.gather(
                        *[self.soft_verify(img["img_src"]) for _, img in scored]
                    )
                    for (_, img), ok in zip(scored, checks):
                        if ok:
                            return {
                                "url": img["img_src"],
                                "title": img.get("title", query),
                                "source": img.get("url", img["img_src"]),
                                "type": "search",
                            }
        except Exception:
            pass
        # ── DuckDuckGo fallback ────────────────────────────────────────────
        try:
            results = await asyncio.to_thread(self._sync_ddgs_search, query)
            candidates = [
                img for img in results[:15]
                if self._is_candidate_image_url(img.get("image", ""))
            ]
            scored = []
            for img in candidates:
                s = self._relevance_score(
                    query,
                    img.get("title", ""),
                    img.get("content", ""),
                    img.get("image", ""),
                )
                if s >= self._MIN_RELEVANCE:
                    scored.append((s, img))
            scored.sort(key=lambda x: x[0], reverse=True)
            if scored:
                checks = await asyncio.gather(
                    *[self.soft_verify(img["image"]) for _, img in scored]
                )
                for (_, img), ok in zip(scored, checks):
                    if ok:
                        return {
                            "url": img["image"],
                            "title": img.get("title", query),
                            "source": img.get("url", img["image"]),
                            "type": "search",
                        }
        except Exception:
            pass
        return {}

    async def fetch_image(self, query: str, context: str = "") -> dict:
        variations = self._build_query_variations(query, context)
        for q in variations:
            result = await self._search_single_query(q)
            if result:
                return result
        try:
            wiki_url = (
                "https://en.wikipedia.org/w/api.php?"
                "action=query&generator=search"
                f"&gsrsearch={urllib.parse.quote(query)}"
                "&gsrlimit=3&prop=pageimages&format=json&pithumbsize=1024"
            )
            res = await asyncio.to_thread(
                requests.get,
                wiki_url,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=self.valves.verify_timeout,
            )
            if res.status_code == 200:
                pages = res.json().get("query", {}).get("pages", {})
                for page_id, page in pages.items():
                    if "thumbnail" in page:
                        thumb_url = page["thumbnail"]["source"]
                        if await self.verify_image_url(thumb_url):
                            return {
                                "url": thumb_url,
                                "title": page.get("title", query),
                                "source": f"https://en.wikipedia.org/wiki/?curid={page_id}",
                                "type": "search",
                            }
        except Exception:
            pass
        return {}

    # ------------------------------------------------------------------ #
    #  IMAGE GENERATION                                                   #
    # ------------------------------------------------------------------ #
    async def generate_image(self, prompt: str) -> dict:
        engine = self.valves.generation_engine.lower()
        if engine in ("pollinations", "both"):
            try:
                encoded = urllib.parse.quote(prompt)
                poll_url = (
                    f"https://image.pollinations.ai/prompt/{encoded}"
                    "?width=1024&height=1024&nologo=true"
                )

                def _sync_pollinations():
                    try:
                        r = requests.get(
                            poll_url,
                            headers={
                                "User-Agent": "Mozilla/5.0",
                                "Accept": "image/*,*/*;q=0.8",
                            },
                            timeout=self.valves.pollinations_timeout,
                            stream=True,
                            allow_redirects=True,
                        )
                        if r.status_code == 200:
                            ct = r.headers.get("Content-Type", "").lower()
                            if ct.startswith("image/") or "octet-stream" in ct:
                                r.close()
                                return True
                            chunk = next(r.iter_content(16), b"")
                            r.close()
                            return (
                                chunk[:2] == b"\xff\xd8"
                                or chunk[:8] == b"\x89PNG\r\n\x1a\n"
                                or chunk[:4] == b"GIF8"
                            )
                        r.close()
                    except Exception:
                        pass
                    return False

                is_valid = await asyncio.to_thread(_sync_pollinations)
                if is_valid:
                    return {
                        "url": poll_url,
                        "title": prompt,
                        "type": "generated",
                        "engine": "Pollinations AI",
                    }
            except Exception:
                pass
        if engine in ("custom", "both"):
            models = [
                m.strip() for m in self.valves.custom_models.split(",") if m.strip()
            ]
            base_url = self.valves.CUSTOM_ENGINE_BASE_URL.rstrip("/")
            headers = {"Content-Type": "application/json"}
            if self.valves.CUSTOM_ENGINE_API_KEY:
                headers["Authorization"] = f"Bearer {self.valves.CUSTOM_ENGINE_API_KEY}"
            for model in models:
                try:
                    payload = {
                        "model": model,
                        "prompt": prompt,
                        "n": 1,
                        "size": "1024x1024",
                    }
                    res = await asyncio.to_thread(
                        requests.post,
                        f"{base_url}/images/generations",
                        json=payload,
                        headers=headers,
                        timeout=self.valves.custom_engine_timeout,
                    )
                    if res.status_code == 200:
                        data = res.json()
                        items = data.get("data", [])
                        if items:
                            img_url = items[0].get("url") or items[0].get("b64_json")
                            if img_url and img_url.startswith("http"):
                                return {
                                    "url": img_url,
                                    "title": prompt,
                                    "type": "generated",
                                    "engine": model,
                                }
                            elif img_url:
                                data_uri = f"data:image/png;base64,{img_url}"
                                return {
                                    "url": data_uri,
                                    "title": prompt,
                                    "type": "generated",
                                    "engine": model,
                                }
                except Exception:
                    continue
        return {}

    # ------------------------------------------------------------------ #
    #  PURE MARKDOWN RENDERING                                            #
    # ------------------------------------------------------------------ #
    def _sanitize_alt(self, text: str) -> str:
        return (
            text.replace("[", "(").replace("]", ")").replace("|", "-").replace('"', "'")
        )

    def render_single_search(self, img: dict) -> str:
        alt = self._sanitize_alt(img.get("title", "Image"))
        url = img["url"]
        source = img.get("source", url)
        return f"\n\n![{alt}]({url})" f"*⌕ Source: [{alt}]({source})*\n\n"

    def render_single_generated(self, img: dict) -> str:
        alt = self._sanitize_alt(img.get("title", "Generated Image"))
        engine = img.get("engine", "Unknown")
        url = img["url"]
        return f"\n\n![{alt}]({url})\n*✦ Generated by: {engine}*\n\n"

    def render_gallery(self, images: list) -> str:
        max_per_row = 3
        rows_output = []
        for row_start in range(0, len(images), max_per_row):
            row_images = images[row_start : row_start + max_per_row]
            cols = len(row_images)
            header = "| " + " | ".join(["\u200b"] * cols) + " |"
            separator = "| " + " | ".join([":---:"] * cols) + " |"
            img_cells = []
            for img in row_images:
                alt = self._sanitize_alt(img.get("title", "Image"))
                url = img["url"]
                img_cells.append(f"![{alt}]({url})")
            img_row = "| " + " | ".join(img_cells) + " |"
            caption_cells = []
            for img in row_images:
                if img.get("type") == "generated":
                    engine = img.get("engine", "Unknown")
                    caption_cells.append(f"*✦ {engine}*")
                else:
                    source = img.get("source", img["url"])
                    caption_cells.append(f"*⌕ [Source]({source})*")
            caption_row = "| " + " | ".join(caption_cells) + " |"
            rows_output.append(f"\n{header}\n{separator}\n{img_row}\n{caption_row}\n")
        return "\n" + "\n".join(rows_output) + "\n"

    # ------------------------------------------------------------------ #
    #  CODE-BLOCK-AWARE TAG EXTRACTION                                    #
    # ------------------------------------------------------------------ #
    def _extract_replaceable_tags(self, content: str) -> list:
        code_regions = []
        for m in re.finditer(r"```[\s\S]*?```", content):
            code_regions.append((m.start(), m.end()))
        for m in re.finditer(r"`[^`\n]+`", content):
            inside_fenced = any(
                m.start() >= s and m.end() <= e for s, e in code_regions
            )
            if not inside_fenced:
                code_regions.append((m.start(), m.end()))
        tag_pattern = r"\{\{\{\s*img\s*\{\s*(search|generate)\s*:\s*(.*?)\s*\}\s*(?:img)?\s*\}\}\}"
        results = []
        for m in re.finditer(tag_pattern, content, re.IGNORECASE):
            tag_start, tag_end = m.start(), m.end()
            inside_code = any(tag_start >= s and tag_end <= e for s, e in code_regions)
            if not inside_code:
                results.append((tag_start, tag_end, m.group(1), m.group(2)))
        return results

    # ------------------------------------------------------------------ #
    #  DIRECTIVE CLEANUP                                                  #
    # ------------------------------------------------------------------ #
    def _strip_directive(self, content: str) -> str:
        marker = self._directive_marker
        if marker in content:
            pattern = re.escape(marker) + r"[\s\S]*?" + re.escape(marker)
            content = re.sub(pattern, "", content)
            content = content.replace(marker, "")
        leak_patterns = [
            r"\[System Context/Memory\][\s\S]*?\[End Context\]",
            r"\[SYSTEM DIRECTIVE[^\]]*\][\s\S]*?\[END DIRECTIVE\]",
            r"You (?:have|can use) an internal image rendering capability[\s\S]{0,500}?(?:automatically|invisible)\.",
            r"Fetch photo:.*?\{img\}\}\}",
            r"Generate art:.*?\{img\}\}\}",
            r"Rules:\s*\n(?:\s*-[^\n]*\n){2,}",
        ]
        for pat in leak_patterns:
            content = re.sub(pat, "", content, flags=re.IGNORECASE)
        content = re.sub(r"\n{4,}", "\n\n\n", content)
        return content.strip()

    def _strip_directive_from_user(self, content: str) -> str:
        marker = self._directive_marker
        if marker in content:
            idx = content.find(marker)
            content = content[:idx].rstrip()
        return content

    # ------------------------------------------------------------------ #
    #  SURROUNDING CONTEXT HELPER                                         #
    # ------------------------------------------------------------------ #
    def _get_surrounding_context(
        self, content: str, start: int, end: int, chars: int = 200
    ) -> str:
        ctx_start = max(0, start - chars)
        ctx_end = min(len(content), end + chars)
        context = content[ctx_start:start] + content[end:ctx_end]
        context = re.sub(
            r"\{\{\{\s*img\s*\{.*?\}\s*(?:img)?\s*\}\}\}",
            "",
            context,
            flags=re.IGNORECASE,
        )
        return context.strip()

    # ------------------------------------------------------------------ #
    #  OUTLET — Progressive / streaming image rendering                  #
    # ------------------------------------------------------------------ #
    async def outlet(
        self,
        body: dict,
        __user__: Optional[dict] = None,
        __request__: Optional[Request] = None,
        __event_emitter__: Callable[[Any], Any] = None,
    ) -> dict:
        messages = body.get("messages", [])
        if not messages:
            return body
        # Clean injected directive from stored user messages
        for msg in messages:
            if msg.get("role") == "user" and self._directive_marker in msg.get(
                "content", ""
            ):
                msg["content"] = self._strip_directive_from_user(msg["content"])
        last_message = messages[-1]
        if last_message.get("role") != "assistant":
            return body
        content = last_message.get("content", "")
        content = self._strip_directive(content)
        emitter = EventEmitter(__event_emitter__)
        tags = self._extract_replaceable_tags(content)
        if not tags:
            messages[-1]["content"] = content
            body["messages"] = messages
            return body
        await emitter.emit(description="⌕ Processing image tags…", status="in_progress")
        # ── Step 1: replace every tag with a unique sentinel token ─────────
        # Process in reverse document order so earlier string positions stay valid.
        #
        # Token naming: \x00IMG{doc_idx:04d}\x00
        #   doc_idx 0  → first tag in the document
        #   doc_idx N  → last tag in the document
        #
        # token_meta maps each token to (action, query, surrounding_context).
        # token_order lists tokens in document order (first → last).
        token_meta: dict[str, tuple[str, str, str]] = {}
        working = content
        sorted_rev = sorted(tags, key=lambda t: t[0], reverse=True)
        for local_idx, (start, end, action, query) in enumerate(sorted_rev):
            doc_idx = len(tags) - 1 - local_idx  # convert to document order
            surrounding = self._get_surrounding_context(content, start, end)
            token = f"\x00IMG{doc_idx:04d}\x00"
            working = working[:start] + token + working[end:]
            token_meta[token] = (action.strip().title(), query.strip(), surrounding)
        token_order = [f"\x00IMG{i:04d}\x00" for i in range(len(tags))]
        # ── Step 2: detect gallery clusters ───────────────────────────────
        # Two consecutive tokens belong to the same cluster when only
        # whitespace separates them in the working string.
        cluster_groups: list[list[str]] = []
        current_cluster: list[str] = [token_order[0]]
        for i in range(1, len(token_order)):
            prev_tok = current_cluster[-1]
            curr_tok = token_order[i]
            prev_end = working.index(prev_tok) + len(prev_tok)
            curr_start = working.index(curr_tok)
            between = working[prev_end:curr_start]
            if between.strip() == "":
                current_cluster.append(curr_tok)
            else:
                cluster_groups.append(current_cluster)
                current_cluster = [curr_tok]
        cluster_groups.append(current_cluster)
        # ── Step 3: display builder ────────────────────────────────────────
        # `resolved` maps token → final markdown (or "" to suppress the slot).
        # Tokens not yet in `resolved` render as a loading spinner.
        resolved: dict[str, str] = {}

        def build_display() -> str:
            result = working
            for tok in token_order:
                action, query, _ = token_meta[tok]
                if tok in resolved:
                    replacement = resolved[tok]
                else:
                    replacement = f"\n\n*⟳ {action}: {query}…*\n\n"
                result = result.replace(tok, replacement)
            return result

        async def push() -> None:
            """Emit a replace event so the UI updates immediately."""
            display = build_display()
            messages[-1]["content"] = display
            if __event_emitter__:
                await __event_emitter__(
                    {"type": "replace", "data": {"content": display}}
                )

        # ── Step 4: show all spinners right away ───────────────────────────
        await push()
        # ── Step 5: process cluster by cluster, image by image ────────────
        for cluster in cluster_groups:
            hits: list[tuple[str, dict]] = []  # (token, img_data) for successes
            for token in cluster:
                action, query, surrounding = token_meta[token]
                if not query:
                    resolved[token] = "\n\n*(⚠ Empty query)*\n\n"
                    await push()
                    continue
                await emitter.emit(
                    description=f"⟳ [{action}] {query}", status="in_progress"
                )
                img_data = (
                    await self.fetch_image(query, context=surrounding)
                    if action == "Search"
                    else await self.generate_image(query)
                )
                if img_data and img_data.get("url"):
                    hits.append((token, img_data))
                    if len(cluster) == 1:
                        # Standalone image — render final markdown immediately.
                        resolved[token] = (
                            self.render_single_generated(img_data)
                            if img_data.get("type") == "generated"
                            else self.render_single_search(img_data)
                        )
                    else:
                        # Inside a gallery cluster — show a ✓ tick while the
                        # rest of the cluster is still loading.
                        resolved[token] = f"\n\n*✓ Found: {query}*\n\n"
                else:
                    resolved[token] = "\n\n*(⚠ Could not find image)*\n\n"
                # Push after every single image resolves.
                await push()
            # ── Gallery finalisation ───────────────────────────────────────
            # Once all tokens in a multi-image cluster have been attempted,
            # replace the interim tick-marks with a proper gallery table.
            if len(cluster) > 1 and hits:
                gallery_md = self.render_gallery([img for _, img in hits])
                # Assign gallery to the first successful token, hide the rest.
                first_token, *rest_tokens = [t for t, _ in hits]
                resolved[first_token] = gallery_md
                for tok in rest_tokens:
                    resolved[tok] = ""
                await push()
        await emitter.emit(description="✓ Images rendered", status="complete")
        body["messages"] = messages
        return body
