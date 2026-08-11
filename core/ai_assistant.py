"""
Real AI assistant backend for LapDoctor, powered by Google's Gemini API.

Unlike a keyword-matching / canned-response engine, this sends the user's
actual free-form question to a real Gemini model, along with a system-context
block built from the live stats and scan results LapDoctor has already
gathered -- so answers are grounded in the user's real PC data instead of
generic, hard-coded advice.

============================== SETUP (one-time) ==============================
1. Install the SDK:
     pip install google-genai --break-system-packages

2. Get a free API key from https://aistudio.google.com/apikey

3. Paste your key into GEMINI_API_KEY below (the very next line of real code
   after these comments). That's it -- no in-app settings screen needed.

   (Alternative: instead of editing this file, you can set an environment
   variable named GEMINI_API_KEY -- if that's set, it's used automatically
   and takes priority over the value pasted below.)
================================================================================
"""

import os
import platform

# ============================================================
# PASTE YOUR GEMINI API KEY HERE (between the quotes)
# ============================================================
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# ============================================================

# Current, stable, generally-available Gemini model as of mid-2026.
# Swap for "gemini-3.5-flash-lite" for a cheaper/faster option.
DEFAULT_MODEL = "gemini-3.5-flash"

SYSTEM_PROMPT_TEMPLATE = """You are LapDoctor AI, the built-in assistant inside the LapDoctor desktop app for Windows.

You can answer ANY question the user asks -- general knowledge, casual conversation, or anything about their PC. You are not restricted to tech topics.

You have real, live data about THIS user's actual laptop below (CPU/RAM/disk/storage %, and their most recent scan results for duplicates, large files, old files, and app caches). When the question is about their PC's performance, storage, slowness, or cleanup, use this real data and reference specific numbers, files, or paths from it -- never guess or give generic advice if the real data already answers it. If the data needed to answer isn't present below, say so plainly and suggest which scan (Duplicates / Large Files / Old Files / App Caches) would find it, instead of making something up.

You can only advise -- you cannot delete, move, or modify any file yourself. If the user wants something removed, tell them to review it in the Storage Scan tab and click "Approve & Clean Selected Files" themselves.

Keep answers short and easy to read in a small chat panel: plain language, short paragraphs or bullet points, no long essays unless asked for detail.

=== LIVE SYSTEM SNAPSHOT ===
OS: {os_info}
CPU load: {cpu}%
RAM usage: {ram}%
Disk activity: {disk}%
Storage used: {storage}%

=== RECENT SCAN RESULTS (may be empty if not run yet) ===
[DUPLICATES]
{duplicates_log}

[LARGE FILES]
{large_log}

[OLD FILES]
{old_log}

[APP CACHES]
{apps_log}
"""


def get_api_key():
    """Env var takes priority so power users/devs can override without
    touching this file."""
    return os.environ.get("GEMINI_API_KEY") or GEMINI_API_KEY.strip()


def is_configured():
    return bool(get_api_key())


def build_system_prompt(context):
    return SYSTEM_PROMPT_TEMPLATE.format(
        os_info=context.get("os_info") or platform.platform(),
        cpu=context.get("cpu", "?"),
        ram=context.get("ram", "?"),
        disk=context.get("disk", "?"),
        storage=context.get("storage", "?"),
        duplicates_log=(context.get("duplicates_log") or "No duplicate scan run yet this session.").strip(),
        large_log=(context.get("large_log") or "No large-file scan run yet this session.").strip(),
        old_log=(context.get("old_log") or "No old-file scan run yet this session.").strip(),
        apps_log=(context.get("apps_log") or "No app-cache scan run yet this session.").strip(),
    )


def ask(question, context, model=None, history=None):
    """
    question: the user's free-form message.
    context: dict with keys os_info/cpu/ram/disk/storage/duplicates_log/
             large_log/old_log/apps_log (all optional).
    history: optional list of {"role": "user"|"model", "content": str}
             prior turns, for multi-turn context.
    """
    api_key = get_api_key()
    if not api_key:
        return (
            "I'm not connected to a real AI model yet.\n\n"
            "Open core/ai_assistant.py and paste your free Gemini API key "
            "into GEMINI_API_KEY at the top of the file "
            "(get one at aistudio.google.com/apikey), then restart LapDoctor."
        )

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        return (
            "The `google-genai` package isn't installed.\n\n"
            "Run this in a terminal, then restart LapDoctor:\n"
            "pip install google-genai --break-system-packages"
        )

    try:
        client = genai.Client(api_key=api_key)

        # Gemini's chat history uses role "model" for the assistant side
        # (not "assistant"), and each turn's text goes under parts.
        contents = []
        for turn in (history or []):
            role = "model" if turn.get("role") == "assistant" else turn.get("role", "user")
            contents.append(types.Content(role=role, parts=[types.Part(text=turn.get("content", ""))]))
        contents.append(types.Content(role="user", parts=[types.Part(text=question)]))

        response = client.models.generate_content(
            model=model or DEFAULT_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=build_system_prompt(context),
                max_output_tokens=800,
            ),
        )

        text = (response.text or "").strip()
        return text or "(The model returned an empty response. Try rephrasing your question.)"

    except Exception as e:
        msg = str(e)
        if "api key" in msg.lower() or "api_key" in msg.lower() or "401" in msg or "permission" in msg.lower():
            return (
                "Your Gemini API key was rejected. Double-check the key pasted into "
                "GEMINI_API_KEY in core/ai_assistant.py (get a fresh one at "
                "aistudio.google.com/apikey)."
            )
        return f"AI request failed: {msg}"
