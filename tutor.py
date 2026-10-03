"""
tutor.py
AI Tutor using DeepSeek API + gTTS voice output.
DeepSeek is OpenAI-compatible — we use the OpenAI SDK pointed at DeepSeek.
Get a key at https://platform.deepseek.com/api_keys
"""
import os
import io

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from gtts import gTTS
from telegram import InputFile

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-flash"

if OPENAI_AVAILABLE and DEEPSEEK_API_KEY:
    _CLIENT = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
else:
    _CLIENT = None


SYSTEM_PROMPT = """You are an expert UTME (JAMB) tutor for Nigerian students.
Your job: explain questions clearly, step by step, in the style of a patient
teacher. Focus on:
1. Restating what the question is really asking.
2. Walking through the method, step by step.
3. Giving the final answer clearly.
4. One short exam tip if useful.

Rules:
- Never add filler like "Sure!", "Great question!", or greetings.
- Never mention you are an AI.
- Keep it under 200 words.
- Stay strictly within the JAMB syllabus for the relevant subject.
- If the question is off-topic or unsafe, reply exactly: "This is outside the UTME syllabus."
"""


def ask_tutor(question_text: str, subject: str = "") -> str:
    if _CLIENT is None:
        return (
            "The AI Tutor is not configured yet. "
            "Ask the admin to set the DEEPSEEK_API_KEY environment variable."
        )
    prompt = question_text
    if subject:
        prompt = f"Subject: {subject}\n\n{prompt}"

    try:
        response = _CLIENT.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            stream=False,
            temperature=0.3,
        )
        text = (response.choices[0].message.content or "").strip()
        return text or "I couldn't generate an explanation. Try rephrasing."
    except Exception as e:
        print(f"[tutor] DeepSeek error: {e}")
        return f"Sorry, the tutor hit an error. Please try again in a moment."


def make_voice(text: str):
    try:
        tts = gTTS(text=text, lang="en", slow=True)
        buf = io.BytesIO()
        tts.write_to_fp(buf)
        buf.seek(0)
        return buf
    except Exception:
        return None


def build_voice_inputfile(text: str):
    buf = make_voice(text)
    if buf is None:
        return None
    return InputFile(buf, filename="tutor_explanation.mp3")
