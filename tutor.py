"""
tutor.py — DeepSeek AI Tutor with thinking mode + gTTS voice.
200% smart: uses reasoning_effort="high" and thinking mode.
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

# "deepseek-flash" = fast + smart (recommended)
# "deepseek-v4-pro" = even smarter but slower/costlier
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-flash")

if OPENAI_AVAILABLE and DEEPSEEK_API_KEY:
    _CLIENT = OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
        timeout=90.0,       # longer timeout for thinking mode
        max_retries=2,
    )
    print(f"[tutor] DeepSeek client ready (model={DEEPSEEK_MODEL})")
else:
    _CLIENT = None
    print("[tutor] WARNING: DeepSeek not configured — check DEEPSEEK_API_KEY")


SYSTEM_PROMPT = """You are the UTME Success Coach AI Tutor — an expert JAMB tutor
for Nigerian students. You explain questions the way a patient, brilliant
teacher would.

STRICT OUTPUT FORMAT:
1. What the question is asking (1 short sentence).
2. Step-by-step solution (numbered steps, show calculations clearly).
3. Final answer (bold, unmistakable).
4. One exam tip (optional, only if genuinely helpful).

RULES:
- No greetings, no filler ("Sure!", "Great question!").
- Never say you are an AI.
- Stay strictly within the JAMB/UTME syllabus for the subject.
- If the question is outside the UTME syllabus, reply exactly:
  "This question is outside the UTME syllabus."
- Keep the explanation under 220 words.
- Use simple English suitable for a Nigerian secondary school student.
- Use correct subject terminology.
- For Maths/Physics/Chemistry: show every step, don't skip.
- For English/Literature: quote the relevant text when useful.
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
                temperature=0.3,
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
        # Strip markdown symbols so the voice reads cleanly
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
    """Health check — call this at startup to verify the key works."""
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
