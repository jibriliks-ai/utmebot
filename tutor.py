"""
tutor.py
AI Tutor using Google Gemini + gTTS voice output.
Get a free API key at https://aistudio.google.com/apikey
"""
import os
import io

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

from gtts import gTTS
from telegram import InputFile

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

if GENAI_AVAILABLE and GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    _MODEL = genai.GenerativeModel("gemini-1.5-flash")
else:
    _MODEL = None


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
    if _MODEL is None:
        return (
            "The AI Tutor is not configured yet. "
            "Ask the admin to set the GEMINI_API_KEY environment variable."
        )
    prompt = SYSTEM_PROMPT
    if subject:
        prompt += f"\nSubject: {subject}\n"
    prompt += f"\nStudent's question:\n{question_text}\n\nYour explanation:"
    try:
        response = _MODEL.generate_content(prompt)
        text = (response.text or "").strip()
        return text or "I couldn't generate an explanation. Try rephrasing."
    except Exception as e:
        return f"Sorry, the tutor hit an error: {e}"


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