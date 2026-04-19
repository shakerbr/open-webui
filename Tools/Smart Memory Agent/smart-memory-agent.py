"""
title: Smart Memory Agent
description: Human-like memory with contextual awareness, conflict detection, and natural response guidance embedded in tool returns.
author: shakerbr
author_url: https://github.com/shakerbr
version: 1.0.0
license: MIT
required_open_webui_version: 0.6.32
"""

import re
import time
from typing import Optional, Callable, Any
from datetime import datetime
from fastapi import Request
from pydantic import BaseModel, Field
from open_webui.main import app as webui_app
from open_webui.models.users import Users, UserModel
from open_webui.routers.memories import (
    add_memory,
    query_memory,
    update_memory_by_id,
    delete_memory_by_id,
    AddMemoryForm,
    QueryMemoryForm,
    MemoryUpdateModel,
)

# ──────────────────────────────────────────────
# Topic Consolidation Map
# ──────────────────────────────────────────────
_TOPIC_ALIASES = {
    # Name/identity variants → Personal Information
    "personal identity": "Personal Information",
    "preferred name": "Personal Information",
    "nickname": "Personal Information",
    "name": "Personal Information",
    "user name": "Personal Information",
    "full name": "Personal Information",
    "contact info": "Personal Information",
    "contact information": "Personal Information",
    "phone": "Personal Information",
    "phone number": "Personal Information",
    "email": "Personal Information",
    "location": "Personal Information",
    "residence": "Personal Information",
    "address": "Personal Information",
    "birthday": "Personal Information",
    "birth date": "Personal Information",
    "age": "Personal Information",
    # Social → Online Presence
    "social media": "Online Presence",
    "social accounts": "Online Presence",
    "socials": "Online Presence",
    "linkedin": "Online Presence",
    "github": "Online Presence",
    "instagram": "Online Presence",
    "facebook": "Online Presence",
    "twitter": "Online Presence",
    # Work → Professional Experience
    "work experience": "Professional Experience",
    "work history": "Professional Experience",
    "job": "Professional Experience",
    "job history": "Professional Experience",
    "career": "Professional Experience",
    "employment": "Professional Experience",
    # Personal → Personal Background
    "hobbies": "Personal Background",
    "interests": "Personal Background",
    "fun facts": "Personal Background",
    "about me": "Personal Background",
    "background": "Personal Background",
}

# Phrases that indicate PREFERENCE, not replacement
_PREFERENCE_PHRASES = [
    "prefer to be called",
    "prefer to be known as",
    "prefer",
    "like to be called",
    "like to be known as",
    "friends call me",
    "call me",
    "nickname is",
    "my nickname",
    "go by",
    "i go by",
    "known as",
    "also known as",
    "aka",
]

# Phrases that indicate REPLACEMENT
_REPLACEMENT_PHRASES = [
    "my name is",
    "i am",
    "my real name is",
    "actually my name is",
    "changed my name to",
    "new name is",
]

# Suspicious claim patterns (tests, jokes, grandiose claims)
_SUSPICIOUS_PATTERNS = [
    r"\bnobel\s+prize\b",
    r"\bbillion\s+dollar",
    r"\bi\s+am\s+god\b",
    r"\bi\s+am\s+batman\b",
    r"\bi\s+am\s+superman\b",
    r"\bi\s+am\s+the\s+president\b",
    r"\bi\s+invented\s+",
    r"\bi\s+own\s+google\b",
    r"\bi\s+own\s+apple\b",
    r"\bi\s+am\s+a\s+billionaire\b",
    r"\bi\s+am\s+drake\b",
    r"\bi\s+am\s+eminem\b",
    r"\bi\s+am\s+taylor\s+swift\b",
    r"just\s+kidding",
    r"i\s+was\s+joking",
    r"i\s+was\s+kidding",
    r"jk\b",
    r"lol\s+jk",
    r"haha",
    r"just\s+testing",
    r"i\s+am\s+testing\s+you",
    r"this\s+is\s+a\s+test",
]

# Core identity fields that conflict requires user confirmation
_IDENTITY_FIELDS = [
    "name",
    "full name",
    "phone",
    "email",
    "address",
    "location",
    "live in",
    "lives in",
    "born",
    "birthday",
]

_TOPIC_RE = re.compile(r"^\[Topic:\s*(.*?)\]\s*\n?(.*)", re.DOTALL | re.IGNORECASE)
_DATE_TAG_RE = re.compile(r"\(Logged:\s*[\d-]+\)")
_FORMERLY_RE = re.compile(r"\[Formerly:.*?\]")


# ──────────────────────────────────────────────
# Helper Classes
# ──────────────────────────────────────────────
class EventEmitter:
    def __init__(self, cb: Callable[[dict], Any] = None):
        self._cb = cb

    async def emit(self, desc: str, status: str = "in_progress", done: bool = False):
        if self._cb:
            await self._cb(
                {
                    "type": "status",
                    "data": {"status": status, "description": desc, "done": done},
                }
            )


def _dummy_request() -> Request:
    return Request(scope={"type": "http", "app": webui_app})


def _parse_memory(content: str) -> tuple[str, str]:
    m = _TOPIC_RE.match(content)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return "", content.strip()


def _extract_bullets(body: str) -> list[str]:
    return [ln.strip() for ln in body.split("\n") if ln.strip()]


def _clean_bullet(line: str) -> str:
    s = line.strip()
    s = _DATE_TAG_RE.sub("", s)
    s = _FORMERLY_RE.sub("", s)
    s = s.lstrip("- ").strip()
    return s


def _bullet_signature(line: str) -> str:
    s = _clean_bullet(line)
    s = re.sub(r"\s+", " ", s.lower())
    return s


def _token_jaccard(a: str, b: str) -> float:
    ta = set(a.lower().split())
    tb = set(b.lower().split())
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _is_semantic_duplicate(
    new_sig: str, existing_sigs: list[str], threshold: float = 0.70
) -> bool:
    for sig in existing_sigs:
        if _token_jaccard(new_sig, sig) >= threshold:
            return True
    return False


def _topic_similarity(a: str, b: str) -> float:
    if a.lower().strip() == b.lower().strip():
        return 1.0
    wa = set(re.findall(r"\w+", a.lower()))
    wb = set(re.findall(r"\w+", b.lower()))
    if not wa or not wb:
        return 0.0
    inter = wa & wb
    union = wa | wb
    jaccard = len(inter) / len(union)
    subset_bonus = 0.2 if (wa <= wb or wb <= wa) else 0.0
    return min(jaccard + subset_bonus, 1.0)


def _resolve_topic_alias(topic: str) -> str:
    key = topic.strip().lower()
    return _TOPIC_ALIASES.get(key, topic.strip())


def _format_bullet(fact: str, date: str) -> str:
    clean = fact.strip().lstrip("- ").strip()
    if not clean:
        return ""
    return f"- {clean} (Logged: {date})"


def _contains_preference_phrase(text: str) -> bool:
    lower = text.lower()
    return any(phrase in lower for phrase in _PREFERENCE_PHRASES)


def _contains_replacement_phrase(text: str) -> bool:
    lower = text.lower()
    return any(phrase in lower for phrase in _REPLACEMENT_PHRASES)


def _is_suspicious_claim(text: str) -> tuple[bool, str]:
    lower = text.lower()
    for pattern in _SUSPICIOUS_PATTERNS:
        if re.search(pattern, lower, re.IGNORECASE):
            return True, pattern.replace(r"\b", "").replace(r"\s+", " ").replace(
                "\\", ""
            )
    return False, ""


def _extract_name_like(text: str) -> Optional[str]:
    """Try to extract a name from 'I am X' or 'My name is X' patterns."""
    patterns = [
        r"my\s+(?:real\s+)?name\s+is\s+([A-Za-z]+)",
        r"i\s+am\s+([A-Za-z]+)(?:\s|$)",
        r"i'm\s+([A-Za-z]+)(?:\s|$)",
        r"call\s+me\s+([A-Za-z]+)",
        r"known\s+as\s+([A-Za-z]+)",
    ]
    for p in patterns:
        m = re.search(p, text.lower())
        if m:
            name = m.group(1).strip().capitalize()
            # Filter out common words that aren't names
            if name.lower() not in [
                "a",
                "an",
                "the",
                "not",
                "sure",
                "here",
                "there",
                "going",
                "from",
            ]:
                return name
    return None


def _find_best_match(
    results, target_topic: str
) -> tuple[Optional[str], str, str, float]:
    best_id = None
    best_topic = ""
    best_body = ""
    best_sim = 0.0

    if not results or not results.ids or not results.ids[0]:
        return None, "", "", 0.0

    for idx, mem_id in enumerate(results.ids[0]):
        content = results.documents[0][idx]
        db_topic, db_body = _parse_memory(content)
        if not db_topic:
            continue
        sim = _topic_similarity(target_topic, db_topic)
        if sim > best_sim:
            best_sim = sim
            best_id = mem_id
            best_topic = db_topic
            best_body = db_body

    return best_id, best_topic, best_body, best_sim


async def _search_memories(user, query: str, k: int = 10):
    dummy_req = _dummy_request()
    try:
        return await query_memory(
            request=dummy_req,
            form_data=QueryMemoryForm(content=query, k=k),
            user=user,
        )
    except Exception:
        return None


def _build_response_guidance(
    status: str,
    topic: str,
    action_taken: str,
    is_minor: bool = False,
    conflict_info: dict = None,
    is_embedded: bool = False,
    is_preference: bool = False,
    is_name_related: bool = False,
    stored_name: str = None,
) -> str:
    """
    Build natural language guidance for the LLM on how to respond.
    This is the KEY function that makes the LLM respond naturally.
    """
    guidance_parts = []

    # ─── SUCCESS CASES ───
    if status == "SUCCESS":
        if is_preference and stored_name:
            # This was a "prefer to be called" type statement
            guidance_parts.append(f"""
═══════════════════════════════════════════════════════════════
MEMORY SAVED: Added preferred name to "{topic}"
User wants to be called by a preferred name/nickname.
Their full name is still on file as: {stored_name}
═══════════════════════════════════════════════════════════════

HOW TO RESPOND:
This is a MINOR update. Respond naturally to the user's message.
You MAY briefly acknowledge the name preference ("Got it, I'll call you [preferred]!")
Or just continue the conversation naturally — acknowledgment is optional.
Do NOT say "I have saved this to my database" or similar robotic phrases.
Be warm, casual, and human-like.
""")
        elif is_embedded:
            # Fact was embedded in a longer message
            guidance_parts.append(f"""
═══════════════════════════════════════════════════════════════
MEMORY SAVED: Added to "{topic}"
The fact was mentioned alongside other content in the user's message.
═══════════════════════════════════════════════════════════════

HOW TO RESPOND:
Respond to the MAIN content of the user's message normally.
You do NOT need to explicitly mention that you saved anything.
Just have a natural conversation. The fact is safely stored.
Do NOT say "I have saved" or "I will remember" unless it fits naturally.
""")
        elif is_minor:
            guidance_parts.append(f"""
═══════════════════════════════════════════════════════════════
MEMORY SAVED: Updated "{topic}"
═══════════════════════════════════════════════════════════════

HOW TO RESPOND:
This is a routine update. Acknowledgment is optional.
You can say something brief like "Got it!" or "Noted!" or just continue.
Do NOT explain what you saved. Be natural and conversational.
""")
        else:
            guidance_parts.append(f"""
═══════════════════════════════════════════════════════════════
MEMORY SAVED: Added to "{topic}"
═══════════════════════════════════════════════════════════════

HOW TO RESPOND:
You saved new information about the user.
Acknowledgment is optional. You can briefly say "Got it" or "I'll remember that"
or continue naturally. Match the user's tone — formal, casual, playful.
Do NOT explain your memory system or mention databases.
""")

    # ─── CONFLICT CASES ───
    elif status == "CONFLICT":
        old_val = conflict_info.get("old", "")
        new_val = conflict_info.get("new", "")
        guidance_parts.append(f"""
═══════════════════════════════════════════════════════════════
MEMORY CONFLICT DETECTED
Existing: {old_val}
New claim: {new_val}
═══════════════════════════════════════════════════════════════

HOW TO RESPOND:
The user just told you something that contradicts what you have on file.
This could be:
• A nickname / preferred name (ADD to existing info)
• An actual name change (REPLACE the old info)
• A joke or test (DO NOT SAVE)
• A persona or alter ego they use online
• A mistake or typo

ASK THE USER in a natural, conversational way.
Match their tone. If they're being playful, be playful back.
Examples of natural responses:
• "Wait, I thought your name was {old_val}? Is {new_val} a nickname, or did you change it?"
• "Hold on — {new_val}? I had you down as {old_val}. Are you messing with me or is this for real?"
• "{new_val}, really? I could've sworn you said {old_val} earlier. Nickname? Alter ego? What's the story?"
• "Interesting! I remember your name being {old_val}. Is {new_val} a stage name or something?"

Do NOT mention "my database" or "my memory" or "on file."
Just ask like a human would.
""")

    # ─── DUPLICATE CASES ───
    elif status == "DUPLICATE":
        guidance_parts.append(f"""
═══════════════════════════════════════════════════════════════
MEMORY: Already exists in "{topic}"
═══════════════════════════════════════════════════════════════

HOW TO RESPOND:
You already have this information. Do NOT acknowledge saving anything.
Just respond normally to the user's message.
If they're confirming something, you can briefly confirm: "Yes, I remember you mentioned that."
Otherwise, continue the conversation naturally.
""")

    # ─── SUSPICIOUS CASES ───
    elif status == "SUSPICIOUS":
        pattern = conflict_info.get("pattern", "")
        guidance_parts.append(f"""
═══════════════════════════════════════════════════════════════
SUSPICIOUS CLAIM DETECTED
Pattern matched: "{pattern}"
═══════════════════════════════════════════════════════════════

HOW TO RESPOND:
The user's claim seems unusual, exaggerated, or might be a joke/test.
DO NOT SAVE THIS.
Respond naturally. If it seems like a joke, play along.
If it might be real but unlikely, ask for clarification in a fun way.
Examples:
• "A Nobel prize huh? 🏆 Which category — Physics or Peace?"
• "Drake!? The rapper? No way. Prove it — drop a verse."
• "Batman? I always knew there was something dark and mysterious about you."

Use your judgment. If they're clearly joking, joke back.
If they might be serious, ask clarifying questions.
""")

    return "\n".join(guidance_parts)


# ──────────────────────────────────────────────
# Main Tool Class
# ──────────────────────────────────────────────
class Tools:
    def __init__(self):
        pass

    # ==========================================
    #  1. MEMORIZE
    # ==========================================
    async def memorize_fact(
        self,
        topic: str,
        new_fact: str,
        action: str,
        exact_old_fact_to_replace: str = "",
        __user__: dict = None,
        __request__: Any = None,
        __model__: dict = None,
        __messages__: list = None,
        __message_id__: str = "",
        __event_emitter__: Callable[[dict], Any] = None,
    ) -> str:
        """
        Save personal information to persistent memory.

        ═══════════════════════════════════════════════════════════
        WHEN TO CALL THIS TOOL:
        ═══════════════════════════════════════════════════════════
        • User shares a FACT about themselves (name, job, location, preferences, etc.)
        • User CORRECTS previous information
        • User EXPLICITLY asks you to remember something
        • The information is CLEARLY about the user, not someone else
        • You are CONFIDENT this is real (not a joke, test, or exaggeration)

        DO NOT CALL THIS TOOL IF:
        • User is clearly joking ("I am Batman", "I won a Nobel prize yesterday lol")
        • User is being sarcastic
        • User is telling a story about someone else
        • Information is hypothetical ("If I were rich...")
        • User is testing you ("What if I told you my name is...")
        • The "fact" is obviously impossible or absurd

        ═══════════════════════════════════════════════════════════
        HOW TO STRUCTURE FACTS:
        ═══════════════════════════════════════════════════════════
        • ONE fact per bullet. Be specific and clear.
        • Start with "User" when possible.
        • GOOD: "User prefers to be called Shaker."
        • GOOD: "User works as a software developer at Microsoft."
        • BAD: "Shaker works at Microsoft" (unclear if this is the user)
        • BAD: "User is cool and funny and lives in Paris and loves pizza" (multiple facts)

        ═══════════════════════════════════════════════════════════
        TOPIC GUIDELINES:
        ═══════════════════════════════════════════════════════════
        Use these CANONICAL topics:
        • "Personal Information" — name, nickname, phone, email, location, birthday
        • "Online Presence" — social media, LinkedIn, GitHub, etc.
        • "Professional Experience" — jobs, work history, career
        • "Education" — degrees, schools, certifications
        • "Skills" — technical skills, languages, tools
        • "Portfolio" — projects, websites, creative work
        • "Personal Background" — hobbies, interests, life story
        • "Relationships" — family, friends, partners
        • "Preferences" — likes, dislikes, favorites
        • "Goals" — aspirations, plans, targets

        DO NOT create micro-topics like "Preferred Name" or "My Dog".
        Merge into the canonical topics above.

        ═══════════════════════════════════════════════════════════
        ACTION TYPES:
        ═══════════════════════════════════════════════════════════
        • action="ADD" — Append new information (default)
        • action="UPDATE" — Replace specific existing information
          (requires exact_old_fact_to_replace)

        :param topic: Canonical topic name.
        :param new_fact: The fact to save.
        :param action: "ADD" or "UPDATE".
        :param exact_old_fact_to_replace: Required for UPDATE.
        :return: Status with response guidance.
        """
        emitter = EventEmitter(__event_emitter__)
        dummy_req = _dummy_request()
        today = datetime.now().strftime("%Y-%m-%d")
        action = action.strip().upper()
        if action not in ("ADD", "UPDATE"):
            action = "ADD"

        try:
            user = Users.get_user_by_id(__user__["id"])

            # ── Resolve topic alias ──
            canonical_topic = _resolve_topic_alias(topic)
            if canonical_topic != topic:
                await emitter.emit(
                    f"↳ Topic '{topic}' → '{canonical_topic}'", "in_progress", False
                )
                topic = canonical_topic

            # ── Format incoming facts ──
            new_bullets = []
            for line in new_fact.split("\n"):
                b = _format_bullet(line, today)
                if b:
                    new_bullets.append(b)
            if not new_bullets:
                await emitter.emit("∅ Empty fact.", "complete", True)
                return "ERROR: No facts to save."

            # ── Suspicious claim check ──
            is_suspicious, matched_pattern = _is_suspicious_claim(new_fact)
            if is_suspicious:
                await emitter.emit("⚠ Suspicious claim detected.", "complete", True)
                return _build_response_guidance(
                    status="SUSPICIOUS",
                    topic=topic,
                    action_taken="NONE",
                    conflict_info={"pattern": matched_pattern},
                )

            # ── Check if this is a PREFERENCE vs REPLACEMENT ──
            is_preference = _contains_preference_phrase(new_fact)
            is_replacement = _contains_replacement_phrase(new_fact)
            is_name_related = any(
                kw in new_fact.lower() for kw in ["name", "call me", "nickname"]
            )

            # ── Search for existing memories ──
            await emitter.emit(f"⌕ Searching '{topic}'…", "in_progress", False)

            best_id = None
            best_topic = topic
            best_body = ""
            best_sim = 0.0

            for query_str in [f"[Topic: {topic}]", new_fact[:200]]:
                results = await _search_memories(user, query_str, k=10)
                mid, mt, mb, ms = _find_best_match(results, topic)
                if ms > best_sim and ms >= 0.55:
                    best_sim = ms
                    best_id = mid
                    best_topic = mt
                    best_body = mb

            # ── Extract existing name if available ──
            stored_name = None
            if best_body:
                for bullet in _extract_bullets(best_body):
                    clean = _clean_bullet(bullet).lower()
                    if "full name" in clean or (
                        "name is" in clean and "prefer" not in clean
                    ):
                        # Extract the name from the bullet
                        m = re.search(
                            r"(?:full\s+)?name\s+(?:is\s+)?([A-Za-z\s]+)", clean
                        )
                        if m:
                            stored_name = m.group(1).strip().title()
                            break

            # ── CONFLICT DETECTION for identity fields ──
            is_identity_conflict = False
            conflict_old = ""
            conflict_new = ""

            if best_id and action == "ADD":
                existing_bullets = _extract_bullets(best_body)
                existing_sigs = [_bullet_signature(b) for b in existing_bullets]

                for nb in new_bullets:
                    new_sig = _bullet_signature(nb)
                    # Check for conflicts
                    for i, existing_sig in enumerate(existing_sigs):
                        # Same category, different value?
                        if _token_jaccard(new_sig, existing_sig) < 0.50:
                            # Different content — check if same field category
                            new_words = set(new_sig.split())
                            old_words = set(existing_sig.split())

                            # Check for identity field conflicts
                            for field in _IDENTITY_FIELDS:
                                if field in new_sig and field in existing_sig:
                                    # Same field, different values
                                    is_identity_conflict = True
                                    conflict_old = _clean_bullet(existing_bullets[i])
                                    conflict_new = _clean_bullet(nb)
                                    break
                            if is_identity_conflict:
                                break
                    if is_identity_conflict:
                        break

            # If this is a name claim that differs from stored name, it's a conflict
            if not is_identity_conflict and stored_name and is_name_related:
                extracted_name = _extract_name_like(new_fact)
                if extracted_name:
                    # Check if this name is different from stored
                    if extracted_name.lower() not in stored_name.lower():
                        # But if it's a PREFERENCE phrase, it's not a conflict — it's an addition
                        if not is_preference:
                            is_identity_conflict = True
                            conflict_old = f"User's name is {stored_name}"
                            conflict_new = f"User's name is {extracted_name}"

            if is_identity_conflict:
                await emitter.emit("⚠ Conflict detected.", "complete", True)
                return _build_response_guidance(
                    status="CONFLICT",
                    topic=best_topic,
                    action_taken="NONE",
                    conflict_info={"old": conflict_old, "new": conflict_new},
                )

            # ── Existing node found ──
            if best_id:
                existing_bullets = _extract_bullets(best_body)
                existing_sigs = [_bullet_signature(b) for b in existing_bullets]

                # UPDATE action
                if action == "UPDATE" and exact_old_fact_to_replace:
                    await emitter.emit("⎔ Updating…", "in_progress", False)
                    snippet_lower = exact_old_fact_to_replace.strip().lower()
                    replaced = False
                    updated_lines = []

                    for line in existing_bullets:
                        if not replaced and snippet_lower[:30] in line.lower():
                            old_clean = _clean_bullet(line)
                            for nb in new_bullets:
                                updated_lines.append(f"{nb}  [Formerly: {old_clean}]")
                            replaced = True
                        else:
                            updated_lines.append(line)

                    if not replaced:
                        updated_lines = list(existing_bullets)
                        for nb in new_bullets:
                            sig = _bullet_signature(nb)
                            if not _is_semantic_duplicate(sig, existing_sigs):
                                updated_lines.append(nb)
                                existing_sigs.append(sig)

                    final_content = f"[Topic: {best_topic}]\n" + "\n".join(
                        updated_lines
                    )
                    await update_memory_by_id(
                        memory_id=best_id,
                        request=dummy_req,
                        form_data=MemoryUpdateModel(content=final_content),
                        user=user,
                    )
                    await emitter.emit("⊛ Updated.", "complete", True)
                    return _build_response_guidance(
                        status="SUCCESS",
                        topic=best_topic,
                        action_taken="UPDATE",
                        is_minor=True,
                    )

                # ADD action with preference handling
                await emitter.emit("⊕ Adding…", "in_progress", False)
                added = 0
                skipped = 0
                merged = list(existing_bullets)

                for nb in new_bullets:
                    sig = _bullet_signature(nb)
                    if _is_semantic_duplicate(sig, existing_sigs):
                        skipped += 1
                    else:
                        merged.append(nb)
                        existing_sigs.append(sig)
                        added += 1

                if added == 0:
                    await emitter.emit("≡ Already exists.", "complete", True)
                    return _build_response_guidance(
                        status="DUPLICATE",
                        topic=best_topic,
                        action_taken="NONE",
                    )

                final_content = f"[Topic: {best_topic}]\n" + "\n".join(merged)
                await update_memory_by_id(
                    memory_id=best_id,
                    request=dummy_req,
                    form_data=MemoryUpdateModel(content=final_content),
                    user=user,
                )
                await emitter.emit("⊛ Saved.", "complete", True)

                # Determine if this is embedded in a longer conversation
                # by checking the last message length
                is_embedded = False
                if __messages__:
                    for msg in reversed(__messages__):
                        if msg.get("role") == "user":
                            content = msg.get("content", "")
                            if len(content.split()) > 20:  # Long message
                                is_embedded = True
                            break

                return _build_response_guidance(
                    status="SUCCESS",
                    topic=best_topic,
                    action_taken="ADD",
                    is_minor=(added <= 1 and not is_name_related),
                    is_embedded=is_embedded,
                    is_preference=is_preference,
                    is_name_related=is_name_related,
                    stored_name=stored_name if is_preference else None,
                )

            # ── Create new node ──
            else:
                await emitter.emit("❖ Creating node…", "in_progress", False)
                formatted = f"[Topic: {topic}]\n" + "\n".join(new_bullets)
                await add_memory(
                    request=dummy_req,
                    form_data=AddMemoryForm(content=formatted),
                    user=user,
                )
                await emitter.emit("✦ Created.", "complete", True)

                # Check if embedded
                is_embedded = False
                if __messages__:
                    for msg in reversed(__messages__):
                        if msg.get("role") == "user":
                            content = msg.get("content", "")
                            if len(content.split()) > 20:
                                is_embedded = True
                            break

                return _build_response_guidance(
                    status="SUCCESS",
                    topic=topic,
                    action_taken="CREATE",
                    is_minor=len(new_bullets) <= 1,
                    is_embedded=is_embedded,
                    is_preference=is_preference,
                )

        except Exception as e:
            await emitter.emit(f"⊗ Error: {e}", "error", True)
            return f"SYSTEM ERROR: {e}"

    # ==========================================
    #  2. RECALL
    # ==========================================
    async def recall_memory(
        self,
        search_query: str,
        __user__: dict = None,
        __request__: Any = None,
        __model__: dict = None,
        __messages__: list = None,
        __message_id__: str = "",
        __event_emitter__: Callable[[dict], Any] = None,
    ) -> str:
        """
        Search and retrieve information from the user's memory.

        Call this when:
        • User asks "do you remember…", "what do you know about me…"
        • You need stored info to answer a question
        • User references something from a previous conversation
        • BEFORE saving identity facts (to check for conflicts)

        :param search_query: What to search for.
        :return: Matching memories with response guidance.
        """
        emitter = EventEmitter(__event_emitter__)

        try:
            user = Users.get_user_by_id(__user__["id"])
            await emitter.emit(f"⌕ Searching: '{search_query}'…", "in_progress", False)

            results = await _search_memories(user, search_query, k=10)

            if not results or not results.ids or not results.ids[0]:
                await emitter.emit("∅ Nothing found.", "complete", True)
                return """
═══════════════════════════════════════════════════════════════
MEMORY: No matching information found.
═══════════════════════════════════════════════════════════════

HOW TO RESPOND:
You don't have this information stored.
You can say: "I don't remember you mentioning that before — would you like to tell me about it?"
Or respond naturally to continue the conversation.
Do NOT say "I searched my database" or similar.
"""

            seen = set()
            formatted = []
            for idx, mem_id in enumerate(results.ids[0]):
                if mem_id in seen:
                    continue
                seen.add(mem_id)
                content = results.documents[0][idx]
                db_topic, db_body = _parse_memory(content)
                if db_topic:
                    formatted.append(f"📌 {db_topic}:\n{db_body}")
                else:
                    formatted.append(f"📌 {content}")

            output = "\n\n".join(formatted)
            await emitter.emit(f"✦ Found {len(formatted)} node(s).", "complete", True)

            return f"""
═══════════════════════════════════════════════════════════════
MEMORY FOUND:
{output}
═══════════════════════════════════════════════════════════════

HOW TO RESPOND:
Use this information naturally in your response.
Do NOT say "according to my database" or "I found in my memory."
Just use the information as if you naturally remember it.
If asked how you know, say "You told me earlier" or similar.
"""

        except Exception as e:
            await emitter.emit(f"⊗ Error: {e}", "error", True)
            return f"SYSTEM ERROR: {e}"

    # ==========================================
    #  3. FORGET
    # ==========================================
    async def forget_fact(
        self,
        exact_text_snippet: str,
        delete_entire_topic: bool = False,
        __user__: dict = None,
        __request__: Any = None,
        __model__: dict = None,
        __messages__: list = None,
        __message_id__: str = "",
        __event_emitter__: Callable[[dict], Any] = None,
    ) -> str:
        """
        Delete information from the user's memory.

        Call this when:
        • User explicitly says "forget that", "delete", "remove"
        • User says they were joking about something you saved
        • User corrects information and wants the old version gone

        :param exact_text_snippet: Quote of what to delete.
        :param delete_entire_topic: True = delete whole topic node.
        :return: Status with response guidance.
        """
        emitter = EventEmitter(__event_emitter__)
        dummy_req = _dummy_request()

        try:
            user = Users.get_user_by_id(__user__["id"])
            await emitter.emit("⌕ Locating…", "in_progress", False)

            results = await _search_memories(user, exact_text_snippet, k=5)

            if not results or not results.ids or not results.ids[0]:
                await emitter.emit("∅ Not found.", "complete", True)
                return """
═══════════════════════════════════════════════════════════════
MEMORY: Could not find that information.
═══════════════════════════════════════════════════════════════

HOW TO RESPOND:
You couldn't find that information to delete.
You can say: "I don't think I had that saved — maybe it was never stored?"
Or: "I couldn't find that in my memory. Did you tell me about that before?"
Respond naturally and conversationally.
"""

            # Find best match
            target_id = None
            target_content = ""
            snippet_lower = exact_text_snippet.strip().lower()

            for idx, mem_id in enumerate(results.ids[0]):
                content = results.documents[0][idx]
                if snippet_lower[:30] in content.lower():
                    target_id = mem_id
                    target_content = content
                    break

            if not target_id:
                target_id = results.ids[0][0]
                target_content = results.documents[0][0]

            db_topic, db_body = _parse_memory(target_content)

            if delete_entire_topic:
                await delete_memory_by_id(
                    memory_id=target_id, request=dummy_req, user=user
                )
                await emitter.emit(f"⊛ Deleted '{db_topic}'.", "complete", True)
                return f"""
═══════════════════════════════════════════════════════════════
MEMORY DELETED: Entire topic "{db_topic}" removed.
═══════════════════════════════════════════════════════════════

HOW TO RESPOND:
You deleted the entire topic.
Briefly acknowledge: "Done, I've forgotten all of that."
Or: "Alright, that's been removed from my memory."
Be casual and don't over-explain.
"""

            # Surgical removal
            bullets = _extract_bullets(db_body)
            remaining = []
            removed = 0

            for line in bullets:
                if removed == 0 and snippet_lower[:30] in line.lower():
                    removed += 1
                else:
                    remaining.append(line)

            if removed == 0:
                await delete_memory_by_id(
                    memory_id=target_id, request=dummy_req, user=user
                )
                await emitter.emit("⊛ Deleted whole node.", "complete", True)
                return f"""
═══════════════════════════════════════════════════════════════
MEMORY DELETED: Entire topic "{db_topic}" removed.
═══════════════════════════════════════════════════════════════

HOW TO RESPOND:
You couldn't isolate the specific bullet, so you deleted the whole topic.
Say: "Alright, I've removed that entire topic from my memory."
"""

            if not remaining:
                await delete_memory_by_id(
                    memory_id=target_id, request=dummy_req, user=user
                )
                await emitter.emit("⊛ Last bullet — node deleted.", "complete", True)
                return f"""
═══════════════════════════════════════════════════════════════
MEMORY DELETED: "{db_topic}" is now empty and removed.
═══════════════════════════════════════════════════════════════

HOW TO RESPOND:
That was the last piece of info in that topic.
Say: "Got it, I've forgotten that. Since that was the last thing, I've cleared the whole topic."
"""

            updated = f"[Topic: {db_topic}]\n" + "\n".join(remaining)
            await update_memory_by_id(
                memory_id=target_id,
                request=dummy_req,
                form_data=MemoryUpdateModel(content=updated),
                user=user,
            )
            await emitter.emit("⊛ Bullet removed.", "complete", True)
            return f"""
═══════════════════════════════════════════════════════════════
MEMORY DELETED: One fact removed from "{db_topic}".
{len(remaining)} fact(s) remain in that topic.
═══════════════════════════════════════════════════════════════

HOW TO RESPOND:
You removed just that one fact.
Say: "Done, I've forgotten that specific thing."
Or: "Alright, that's been removed."
Be brief and casual.
"""

        except Exception as e:
            await emitter.emit(f"⊗ Error: {e}", "error", True)
            return f"SYSTEM ERROR: {e}"
