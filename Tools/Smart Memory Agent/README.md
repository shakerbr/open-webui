# Smart Memory Agent

<div align="center">

[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://shields.io/)
[![Open WebUI](https://img.shields.io/badge/Open%20WebUI-0.6.32+-purple.svg)](https://openwebui.com/)
![Open WebUI](https://img.shields.io/badge/Open%20WebUI-Tool-darkgreen)
[![Author](https://img.shields.io/badge/author-shakerbr-blue.svg)](https://github.com/shakerbr)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Human-like memory with contextual awareness, conflict detection, and natural response guidance.**

[Features](#features) • [Installation](#installation) • [Usage](#how-to-use) • [Configuration](#configuration)

</div>

---

## Overview

Smart Memory Agent is a sophisticated memory system that mimics human-like memory behavior. Unlike traditional memory tools that simply store and retrieve data, this agent understands context, detects conflicts, filters suspicious claims, and provides natural response guidance to ensure conversations remain fluid and human-like.

> [!NOTE]
> This tool integrates seamlessly with Open WebUI's built-in memory system. No additional configuration or external services required.

## Features

### Core Memory Operations

| Feature | Description |
|---------|-------------|
| 🧠 **Memorize Facts** | Save personal information with intelligent topic organization |
| 🔍 **Recall Memory** | Search and retrieve stored information using semantic search |
| 🗑️ **Forget Facts** | Delete specific facts or entire memory nodes |

### Intelligence Features

| Feature | Description |
|---------|-------------|
| 🎯 **Topic Consolidation** | Aliases automatically map to canonical topics (e.g., "name" → "Personal Information") |
| ⚠️ **Conflict Detection** | Identifies contradictory information and asks for clarification |
| 🎭 **Suspicious Claim Detection** | Filters jokes, tests, and exaggerations (e.g., "I am Batman") |
| 🔄 **Preference vs Replacement** | Distinguishes between nicknames ("call me X") and actual changes ("my name is X") |
| 🧹 **Semantic Deduplication** | Jaccard similarity prevents duplicate entries |
| 💬 **Natural Response Guidance** | Every tool return includes guidance on how the LLM should respond |

### Response Behavior

| Scenario | Behavior |
|---------|----------|
| **New Information** | Optional acknowledgment ("Got it!") or natural continuation |
| **Embedded Facts** | Responds to main message content without acknowledging the save |
| **Conflicts** | Asks clarifying questions in a conversational tone |
| **Duplicates** | Continues naturally without re-acknowledging |
| **Suspicious Claims** | Plays along or asks fun clarifying questions |

---

## Installation

1. Open Open WebUI and navigate to **Workspace → Tools**
2. Click the **+** button to add a new tool
3. Paste the contents of [`smart-memory-agent.py`](./smart-memory-agent.py) directly into the editor
4. Save and enable the tool

> [!TIP]
> The tool uses Open WebUI's built-in memory system. Make sure memory is enabled in your Open WebUI settings.

---

## Configuration

### Valves

No Valves configuration required. The tool operates out-of-the-box using Open WebUI's internal memory APIs.

### Memory Persistence

Memory is persisted through Open WebUI's built-in memory system:

- Memories are stored in the configured vector database (ChromaDB by default)
- Each user has their own isolated memory space
- Memories persist across sessions and conversations
- Data is tied to your Open WebUI user account

> [!IMPORTANT]
> Memory persistence depends on your Open WebUI configuration. Ensure your database is properly backed up for production deployments.

---

## Canonical Topics

The tool uses predefined canonical topics to organize memories. User-provided topics are automatically consolidated:

| Topic | Description | Common Aliases |
|-------|-------------|----------------|
| **Personal Information** | Name, nickname, phone, email, location, birthday | name, full name, contact info, address, residence, age |
| **Online Presence** | Social media, LinkedIn, GitHub | socials, linkedin, github, instagram, twitter, facebook |
| **Professional Experience** | Jobs, work history, career | work experience, job history, employment |
| **Education** | Degrees, schools, certifications | — |
| **Skills** | Technical skills, languages, tools | — |
| **Portfolio** | Projects, websites, creative work | — |
| **Personal Background** | Hobbies, interests, life story | hobbies, interests, fun facts, about me, background |
| **Relationships** | Family, friends, partners | — |
| **Preferences** | Likes, dislikes, favorites | — |
| **Goals** | Aspirations, plans, targets | — |

> [!WARNING]
> Avoid creating micro-topics like "My Dog" or "Preferred Name". These should be consolidated into the appropriate canonical topics.

---

## Tool Methods

| Method | Purpose | Parameters |
|--------|---------|------------|
| `memorize_fact(topic, new_fact, action)` | Save or update information | `topic`: Canonical topic name<br>`new_fact`: The fact to save<br>`action`: "ADD" or "UPDATE" |
| `recall_memory(search_query)` | Search stored memories | `search_query`: What to search for |
| `forget_fact(exact_text_snippet, delete_entire_topic)` | Remove information | `exact_text_snippet`: Quote to delete<br>`delete_entire_topic`: Boolean flag |

---

## How to Use

The LLM automatically calls these tools based on conversation context:

### Memorize Facts

```
User: "My name is Alex and I work at Google."
→ Tool: memorize_fact(topic="Personal Information", new_fact="User's name is Alex", action="ADD")
→ Tool: memorize_fact(topic="Professional Experience", new_fact="User works at Google", action="ADD")
```

### Recall Memory

```
User: "Do you remember where I work?"
→ Tool: recall_memory(search_query="work job employment")
→ Response: Uses retrieved information naturally
```

### Forget Facts

```
User: "Forget that I work at Google, I actually work at Microsoft now."
→ Tool: forget_fact(exact_text_snippet="User works at Google")
→ Tool: memorize_fact(topic="Professional Experience", new_fact="User works at Microsoft", action="ADD")
```

---

## Response Guidance

Each tool return includes natural language guidance for how the LLM should respond. This ensures conversations remain fluid and human-like:

### Example: Successful Save

```
═══════════════════════════════════════════════════════════════
MEMORY SAVED: Added to "Personal Information"
═══════════════════════════════════════════════════════════════

HOW TO RESPOND:
You saved new information about the user.
Acknowledgment is optional. You can briefly say "Got it" or "I'll remember that"
or continue naturally. Match the user's tone — formal, casual, playful.
Do NOT explain your memory system or mention databases.
```

### Example: Conflict Detection

```
═══════════════════════════════════════════════════════════════
MEMORY CONFLICT DETECTED
Existing: User's name is Alex
New claim: User's name is Sam
═══════════════════════════════════════════════════════════════

HOW TO RESPOND:
The user just told you something that contradicts what you have on file.
This could be:
• A nickname / preferred name (ADD to existing info)
• An actual name change (REPLACE the old info)
• A joke or test (DO NOT SAVE)

ASK THE USER in a natural, conversational way.
```

### Example: Suspicious Claim

```
═══════════════════════════════════════════════════════════════
SUSPICIOUS CLAIM DETECTED
Pattern matched: "i am batman"
═══════════════════════════════════════════════════════════════

HOW TO RESPOND:
The user's claim seems unusual, exaggerated, or might be a joke/test.
DO NOT SAVE THIS.
Respond naturally. If it seems like a joke, play along.
Example: "Batman? I always knew there was something dark and mysterious about you."
```

---

## Showcase

![Showcase of Smart Memory Agent](image-placeholder.png)

> [!NOTE]
> Screenshots demonstrating the tool in action will be added here.

---

## Technical Details

### Dependencies

- Open WebUI 0.6.32 or higher
- FastAPI (included with Open WebUI)
- Pydantic (included with Open WebUI)

### How It Works

1. **Topic Resolution**: User topics are mapped to canonical topics via the alias dictionary
2. **Semantic Search**: Uses Open WebUI's vector database for similarity-based retrieval
3. **Conflict Detection**: Compares new claims against existing identity fields
4. **Deduplication**: Jaccard similarity (threshold: 0.70) prevents duplicate entries
5. **Response Generation**: Pre-built guidance templates ensure natural responses

### File Structure

```
smart-memory-agent.py
├── Topic Aliases (_TOPIC_ALIASES)
├── Preference Phrases (_PREFERENCE_PHRASES)
├── Replacement Phrases (_REPLACEMENT_PHRASES)
├── Suspicious Patterns (_SUSPICIOUS_PATTERNS)
├── Identity Fields (_IDENTITY_FIELDS)
├── Helper Classes
│   ├── EventEmitter
│   └── Helper Functions
└── Tools Class
    ├── memorize_fact()
    ├── recall_memory()
    └── forget_fact()
```

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<div align="center">

**Made with ❤️ by [shakerbr](https://github.com/shakerbr)**

[![GitHub](https://img.shields.io/badge/GitHub-shakerbr-black?logo=github)](https://github.com/shakerbr)

</div>