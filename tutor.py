"""
tutor.py — DeepSeek AI Tutor with thinking mode + gTTS voice.
Model is hardcoded to deepseek-flash (no env override — prevents 400 errors).
Thinking mode enabled for maximum intelligence.
"""
import os
import io
import time
import traceback

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from gtts import gTTS
from telegram import InputFile

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"

# HARDCODED — do NOT override via env var. Valid names: deepseek-flash, deepseek-v4-pro
DEEPSEEK_MODEL = "deepseek-flash"

if OPENAI_AVAILABLE and DEEPSEEK_API_KEY:
    _CLIENT = OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
        timeout=120.0,
        max_retries=2,
    )
    print(f"[tutor] DeepSeek client ready (model={DEEPSEEK_MODEL}, thinking=ON)")
else:
    _CLIENT = None
    print("[tutor] WARNING: DeepSeek not configured — check DEEPSEEK_API_KEY")


SYSTEM_PROMPT = """You are the UTME Success Coach AI Tutor — an elite JAMB tutor
for Nigerian students. You explain questions the way a brilliant, patient
teacher would.

STRICT OUTPUT FORMAT:
1. What the question is asking (1 short sentence).
2. Step-by-step solution (numbered steps, show every calculation).
3. Final answer (bold, unmistakable).
4. One exam tip (only if genuinely useful).

RULES:
- No greetings, no filler ("Sure!", "Great question!").
- Never say you are an AI.
- Stay strictly within the JAMB/UTME syllabus.
- If the question is off-syllabus, reply exactly:
  "This question is outside the UTME syllabus."
- Keep the explanation under 220 words.
- Simple English for a Nigerian secondary school student.
- Correct subject terminology.
- Maths/Physics/Chemistry: show every step, never skip.
- English/Literature: quote the relevant text when useful.
"""


def ask_tutor(question_text: str, subject: str = "") -> str:
    """Return a plain-text explanation. Retries once on transient errors."""
    if _CLIENT is None:
        return (
            "⚠️ The AI Tutor isn't configured yet. "
            "Ask the admin to set DEEPSEEK_API_KEY on the server."
        )

    user_prompt = question_text
    if subject:
        user_prompt = f"Subject: {subject}\n\nQuestion:\n{question_text}"

    last_error = None
    for attempt in (1, 2):
        try:
            response = _CLIENT.chat.completions.create(
                model=DEEPSEEK_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                stream=False,
                reasoning_effort="high",
                extra_body={"thinking": {"type": "enabled"}},
            )
            text = (response.choices[0].message.content or "").strip()
            if text:
                print(f"[tutor] OK (attempt {attempt}, {len(text)} chars)")
                return text
            last_error = "empty response"
        except Exception as e:
            last_error = f"{type(e).__name__}: {e}"
            print(f"[tutor] attempt {attempt} failed -> {last_error}")
            traceback.print_exc()
            time.sleep(1.5)

    return (
        "⚠️ The Tutor is temporarily unavailable. Please try again in a moment.\n\n"
        f"_Diagnostic: {last_error}_"
    )


def make_voice(text: str):
    """Generate MP3 in memory, slower pace for assimilation."""
    try:
        clean = (
            text.replace("*", "")
                .replace("_", "")
                .replace("`", "")
                .replace("#", "")
        )
        tts = gTTS(text=clean, lang="en", slow=True)
        buf = io.BytesIO()
        tts.write_to_fp(buf)
        buf.seek(0)
        return buf
    except Exception as e:
        print(f"[tutor] voice generation failed: {e}")
        return None


def build_voice_inputfile(text: str):
    buf = make_voice(text)
    if buf is None:
        return None
    return InputFile(buf, filename="tutor_explanation.mp3")


def ping():
    """Health check at startup."""
    if _CLIENT is None:
        return False, "no client"
    try:
        r = _CLIENT.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[{"role": "user", "content": "Say OK"}],
            max_tokens=10,
            stream=False,
        )
        return True, (r.choices[0].message.content or "").strip()
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"
