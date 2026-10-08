"""
tutor.py — DeepSeek AI Tutor (Mr. Ellams) with RAG + Nigerian Male Voice + JAMB Trap Detector.
"""
import os
import io
import re
import json
import glob
import time
import traceback
import asyncio
from pathlib import Path

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except Exception:
    GTTS_AVAILABLE = False

try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
    print("[tutor] ✅ Edge TTS available (Nigerian male voice ready)")
except ImportError:
    EDGE_TTS_AVAILABLE = False
    print("[tutor] edge-tts not installed — using gTTS fallback")

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-flash"

VOICE_MALE_NIGERIAN = "en-NG-AbeoNeural"
VOICE_FEMALE_NIGERIAN = "en-NG-EzinneNeural"
VOICE_RATE = "-5%"
VOICE_PITCH = "-2Hz"

try:
    from rank_bm25 import BM25Okapi
    BM25_AVAILABLE = True
    print("[tutor] BM25 retrieval ready")
except ImportError:
    BM25_AVAILABLE = False
    print("[tutor] rank_bm25 not installed — BM25 disabled")

_EMBED_MODEL = None
EMBEDDING_AVAILABLE = False
try:
    from sentence_transformers import SentenceTransformer
    EMBEDDING_AVAILABLE = True
except ImportError:
    pass

_KB_CHUNKS = []
_KB_BM25 = None
_KB_EMBEDDINGS = None
_KB_TOKENIZED = []
_KB_READY = False
_KB_BUILDING = False

if OPENAI_AVAILABLE and DEEPSEEK_API_KEY:
    _CLIENT = OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
        timeout=120.0,
        max_retries=2,
    )
    print(f"[tutor] DeepSeek client ready (model={DEEPSEEK_MODEL})")
else:
    _CLIENT = None
    print("[tutor] WARNING: DeepSeek not configured — check DEEPSEEK_API_KEY")


# ═══════════════════════════════════════════════════════
# KNOWLEDGE BASE
# ═══════════════════════════════════════════════════════

def _tokenize(text):
    return re.findall(r"[a-z0-9]+", text.lower())


def _load_questions_databank():
    chunks = []
    for file in sorted(glob.glob("questions_*.json")):
        try:
            data = json.loads(Path(file).read_text(encoding="utf-8"))
            items = data if isinstance(data, list) else data.get("questions", [])
            for q in items:
                if not isinstance(q, dict):
                    continue
                parts = []
                if q.get("subject"):
                    parts.append(f"Subject: {q['subject']}")
                if q.get("topic"):
                    parts.append(f"Topic: {q['topic']}")
                if q.get("question"):
                    parts.append(f"Question: {q['question']}")
                for L in ("A", "B", "C", "D", "E"):
                    opt = q.get(f"option_{L.lower()}")
                    if opt:
                        parts.append(f"Option {L}: {opt}")
                if q.get("answer"):
                    parts.append(f"Correct Answer: {q['answer']}")
                if q.get("explanation"):
                    parts.append(f"Explanation: {q['explanation']}")
                text = "\n".join(parts)
                if len(text) < 30:
                    continue
                chunks.append({
                    "text": text,
                    "subject": (q.get("subject") or "").lower(),
                    "subject_key": (q.get("subject_key") or "").lower(),
                    "source": Path(file).name,
                    "type": "past_question",
                })
        except Exception as e:
            print(f"[tutor] Error loading {file}: {e}")
    return chunks


def _load_syllabus_files():
    chunks = []
    syllabus_dir = Path("syllabus")
    if not syllabus_dir.exists():
        return chunks
    for txt_file in sorted(syllabus_dir.glob("*.txt")):
        try:
            text = txt_file.read_text(encoding="utf-8", errors="ignore")
            for i in range(0, len(text), 700):
                chunk = text[i:i+800].strip()
                if len(chunk) < 50:
                    continue
                chunks.append({
                    "text": chunk,
                    "subject": txt_file.stem.lower(),
                    "subject_key": txt_file.stem.lower(),
                    "source": txt_file.name,
                    "type": "syllabus",
                })
        except Exception as e:
            print(f"[tutor] Error loading {txt_file}: {e}")
    return chunks


def _build_embeddings(texts):
    global _EMBED_MODEL
    if not EMBEDDING_AVAILABLE:
        return None
    try:
        if _EMBED_MODEL is None:
            print("[tutor] Loading all-MiniLM-L6-v2…")
            _EMBED_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
        import numpy as np
        embs = _EMBED_MODEL.encode(texts, batch_size=32,
                                    show_progress_bar=False, convert_to_numpy=True)
        return embs.astype("float32")
    except Exception as e:
        print(f"[tutor] Embedding build failed: {e}")
        return None


def build_knowledge_base(force_rebuild=False):
    global _KB_CHUNKS, _KB_BM25, _KB_EMBEDDINGS, _KB_TOKENIZED, _KB_READY, _KB_BUILDING
    if _KB_READY and not force_rebuild:
        return True
    if _KB_BUILDING:
        return False
    _KB_BUILDING = True
    try:
        print("[tutor] Building knowledge base…")
        t0 = time.time()
        chunks = _load_questions_databank()
        chunks.extend(_load_syllabus_files())
        if not chunks:
            print("[tutor] No chunks loaded — LLM-only mode")
            _KB_READY = True
            _KB_BUILDING = False
            return False
        _KB_CHUNKS = chunks
        texts = [c["text"] for c in chunks]
        if BM25_AVAILABLE:
            _KB_TOKENIZED = [_tokenize(t) for t in texts]
            _KB_BM25 = BM25Okapi(_KB_TOKENIZED)
        if EMBEDDING_AVAILABLE and not force_rebuild:
            emb = _build_embeddings(texts)
            if emb is not None:
                _KB_EMBEDDINGS = emb
        print(f"[tutor] ✅ KB ready in {time.time()-t0:.1f}s "
              f"({len(chunks)} chunks, BM25={_KB_BM25 is not None})")
        _KB_READY = True
        _KB_BUILDING = False
        return True
    except Exception as e:
        print(f"[tutor] ❌ KB build failed: {e}")
        traceback.print_exc()
        _KB_BUILDING = False
        return False


# ═══════════════════════════════════════════════════════
# RETRIEVAL
# ═══════════════════════════════════════════════════════

def _bm25_search(query, top_k=5, subject_filter=None):
    if _KB_BM25 is None or not _KB_CHUNKS:
        return []
    tokens = _tokenize(query)
    if not tokens:
        return []
    scores = _KB_BM25.get_scores(tokens)
    ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
    results = []
    for idx in ranked:
        if scores[idx] <= 0:
            break
        chunk = _KB_CHUNKS[idx]
        if subject_filter:
            sf = subject_filter.lower()
            if sf not in chunk.get("subject_key", "") and sf not in chunk.get("subject", ""):
                continue
        results.append({"chunk": chunk, "score": float(scores[idx])})
        if len(results) >= top_k:
            break
    return results


def _semantic_search(query, top_k=5, subject_filter=None):
    if _KB_EMBEDDINGS is None or _EMBED_MODEL is None:
        return []
    try:
        import numpy as np
        q_emb = _EMBED_MODEL.encode([query], convert_to_numpy=True).astype("float32")
        norms = np.linalg.norm(_KB_EMBEDDINGS, axis=1) * np.linalg.norm(q_emb)
        norms[norms == 0] = 1e-9
        sims = (_KB_EMBEDDINGS @ q_emb.T).flatten() / norms
        ranked = np.argsort(sims)[::-1]
        results = []
        for idx in ranked:
            chunk = _KB_CHUNKS[int(idx)]
            if subject_filter:
                sf = subject_filter.lower()
                if sf not in chunk.get("subject_key", "") and sf not in chunk.get("subject", ""):
                    continue
            results.append({"chunk": chunk, "score": float(sims[idx])})
            if len(results) >= top_k:
                break
        return results
    except Exception as e:
        print(f"[tutor] Semantic search failed: {e}")
        return []


def retrieve_context(query, subject=None, top_k=5):
    if not _KB_READY or not _KB_CHUNKS:
        return []
    bm25_results = _bm25_search(query, top_k=top_k * 2, subject_filter=subject)
    semantic_results = _semantic_search(query, top_k=top_k * 2, subject_filter=subject)
    seen = set()
    merged = []
    for r in bm25_results:
        key = r["chunk"]["text"][:120]
        if key not in seen:
            seen.add(key)
            merged.append(r)
    for r in semantic_results:
        key = r["chunk"]["text"][:120]
        if key not in seen:
            seen.add(key)
            merged.append(r)
    return merged[:top_k]


def _format_context(results, max_per_chunk=800):
    if not results:
        return ""
    lines = ["\n=== RETRIEVED FROM JAMB DATABANK ===\n"]
    for i, r in enumerate(results, 1):
        c = r["chunk"]
        tag = f"[{i}] ({c.get('type','doc')} | {c.get('subject','general')})"
        lines.append(f"{tag}\n{c['text'][:max_per_chunk]}\n")
    lines.append("=== END OF RETRIEVED CONTEXT ===\n")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════
# SYSTEM PROMPTS
# ═══════════════════════════════════════════════════════

SYSTEM_PROMPT = """You are "Mr. Ellams", a seasoned Nigerian JAMB tutor with 20 years of
classroom experience. You explain questions like a brilliant, patient Nigerian
secondary school teacher, guiding the student calmly and professionally.

You have a RETRIEVED CONTEXT section below containing real JAMB past questions
and syllabus excerpts. USE THIS CONTEXT AS YOUR PRIMARY SOURCE OF TRUTH.

STRUCTURE YOUR ANSWER FOR SPOKEN DELIVERY (the student will also hear this):

1. **The Answer**: State the correct answer first, clearly.
   Example: "The correct answer is option B — Temperature."

2. **Why It Is Correct**: Explain step by step, as if teaching at a blackboard.
   Show every calculation for Maths/Physics/Chemistry.

3. **Key Principle**: Name the underlying concept in one short sentence.

4. **Exam Tip**: A short memorable way to remember it for the exam.

RULES:
- Use simple, clear, professional Nigerian English.
- No greetings like "Sure!", "Great question!", "Hello!"
- No emojis in the spoken portion.
- Keep total explanation under 250 words.
- If the retrieved context contains a matching past question, cite it.
- If the question is off-syllabus, reply exactly:
  "This question is outside the UTME syllabus."
"""


TRAP_DETECTOR_PROMPT = """You are the JAMB Trap Detector — a specialist coach who analyses
why a student failed a JAMB question and exposes the trap JAMB set.

You will be given:
- The question text
- The student's WRONG answer
- The CORRECT answer
- The topic

Your job is to explain in Nigerian student slang, short and punchy, no big grammar.
Follow this exact structure:

1. WHY THE CORRECT ANSWER IS CORRECT (simple English, 2-3 lines max)

2. WHY THE STUDENT'S ANSWER IS THE TRAP (explain the mind game JAMB is playing.
   80% of students pick this wrong answer.)

3. JAMB HISTORY: Show how JAMB has set this same trap in 2021 and 2023
   (make up realistic-sounding year references consistent with the topic).

4. PRACTICE QUESTION: Give 1 similar JAMB-style question to test if they learned.
   Include 4 options and mark the correct answer at the end.

End your response with exactly this line (replace 18 with a random small number):
"You want me to fix your next failure Q18?"

Keep it under 220 words total.
"""


# ═══════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════

def ask_tutor(question_text: str, subject: str = "") -> str:
    if _CLIENT is None:
        return ("⚠️ The AI Tutor isn't configured yet. "
                "Ask the admin to set DEEPSEEK_API_KEY on the server.")
    results = retrieve_context(question_text, subject=subject, top_k=5)
    context_block = _format_context(results) if results else ""
    user_prompt = ""
    if subject:
        user_prompt += f"Subject: {subject}\n\n"
    if context_block:
        user_prompt += context_block + "\n"
    user_prompt += f"STUDENT QUESTION:\n{question_text}"
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
                print(f"[tutor] OK (attempt {attempt}, {len(text)} chars, ctx={len(results)})")
                return text
            last_error = "empty response"
        except Exception as e:
            last_error = f"{type(e).__name__}: {e}"
            print(f"[tutor] attempt {attempt} failed -> {last_error}")
            time.sleep(1.5)
    return (f"⚠️ The Tutor is temporarily unavailable. Please try again.\n\n"
            f"_Diagnostic: {last_error}_")


def analyze_failure(question_text: str, user_answer: str,
                    correct_answer: str, topic: str = "General") -> str:
    """JAMB Trap Detector — analyses a single failed question."""
    if _CLIENT is None:
        return "⚠️ AI Tutor is not configured."

    user_prompt = (
        f"Question: {question_text}\n"
        f"Student answered: {user_answer} (WRONG)\n"
        f"Correct: {correct_answer}\n"
        f"Topic: {topic}\n\n"
        f"Now analyse this failure."
    )

    last_error = None
    for attempt in (1, 2):
        try:
            response = _CLIENT.chat.completions.create(
                model=DEEPSEEK_MODEL,
                messages=[
                    {"role": "system", "content": TRAP_DETECTOR_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                stream=False,
                reasoning_effort="high",
                extra_body={"thinking": {"type": "enabled"}},
            )
            text = (response.choices[0].message.content or "").strip()
            if text:
                print(f"[tutor] Trap analysis OK ({len(text)} chars)")
                return text
            last_error = "empty response"
        except Exception as e:
            last_error = f"{type(e).__name__}: {e}"
            print(f"[tutor] Trap analysis attempt {attempt} failed -> {last_error}")
            time.sleep(1.5)
    return f"⚠️ Trap analysis unavailable. Please try again.\n\n_{last_error}_"


# ═══════════════════════════════════════════════════════
# VOICE — Nigerian Male Teacher (Mr. Ellams)
# ═══════════════════════════════════════════════════════

def _clean_for_speech(text: str) -> str:
    clean = text
    clean = re.sub(r'\*\*(.*?)\*\*', r'\1', clean)
    clean = re.sub(r'\*(.*?)\*', r'\1', clean)
    clean = re.sub(r'`(.*?)`', r'\1', clean)
    clean = re.sub(r'[*_#`\[\]]', '', clean)
    clean = re.sub(r'\n+', '. ', clean)
    clean = re.sub(r'\s+', ' ', clean)
    clean = re.sub(r'\.\s*\.', '.', clean)
    return clean.strip()[:2500]


def make_voice_professional(text: str):
    clean = _clean_for_speech(text)
    if not clean:
        return None
    if EDGE_TTS_AVAILABLE:
        try:
            async def _gen():
                communicate = edge_tts.Communicate(
                    clean, VOICE_MALE_NIGERIAN, rate=VOICE_RATE, pitch=VOICE_PITCH)
                buf = io.BytesIO()
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        buf.write(chunk["data"])
                buf.seek(0)
                return buf
            buf = asyncio.run(_gen())
            if buf and buf.getbuffer().nbytes > 0:
                print(f"[tutor] ✅ Edge TTS ({buf.getbuffer().nbytes} bytes)")
                return buf
        except Exception as e:
            print(f"[tutor] Edge TTS failed: {type(e).__name__}: {e}")
        try:
            async def _gen_f():
                communicate = edge_tts.Communicate(
                    clean, VOICE_FEMALE_NIGERIAN, rate=VOICE_RATE)
                buf = io.BytesIO()
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        buf.write(chunk["data"])
                buf.seek(0)
                return buf
            buf = asyncio.run(_gen_f())
            if buf and buf.getbuffer().nbytes > 0:
                print("[tutor] ✅ Edge TTS (female fallback)")
                return buf
        except Exception as e:
            print(f"[tutor] Edge TTS female fallback failed: {e}")
    if GTTS_AVAILABLE:
        try:
            tts = gTTS(text=clean, lang="en", tld="com.ng", slow=True)
            buf = io.BytesIO()
            tts.write_to_fp(buf)
            buf.seek(0)
            print("[tutor] ✅ gTTS (Nigerian) fallback")
            return buf
        except Exception as e:
            print(f"[tutor] gTTS failed: {e}")
    return None


def make_voice(text: str):
    return make_voice_professional(text)


def build_voice_inputfile(text: str):
    try:
        from telegram import InputFile
    except ImportError:
        return None
    buf = make_voice_professional(text)
    if buf is None:
        return None
    return InputFile(buf, filename="ellams_explanation.mp3")


def ping():
    if _CLIENT is None:
        return False, "no client"
    try:
        r = _CLIENT.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[{"role": "user", "content": "Say OK"}],
            max_tokens=10, stream=False,
        )
        llm_status = (r.choices[0].message.content or "").strip()
    except Exception as e:
        llm_status = f"LLM error: {type(e).__name__}: {e}"
    kb_status = (
        f"KB: {len(_KB_CHUNKS)} chunks, BM25={_KB_BM25 is not None}"
        if _KB_READY else "KB: not built"
    )
    voice_status = "Edge-TTS" if EDGE_TTS_AVAILABLE else ("gTTS" if GTTS_AVAILABLE else "none")
    ok = "OK" in llm_status.upper() or "ok" in llm_status.lower()
    return ok, f"{llm_status} | {kb_status} | Voice: {voice_status}"


def get_kb_stats():
    subjects = {}
    for c in _KB_CHUNKS:
        s = c.get("subject") or "unknown"
        subjects[s] = subjects.get(s, 0) + 1
    return {
        "total_chunks": len(_KB_CHUNKS),
        "bm25_ready": _KB_BM25 is not None,
        "embeddings_ready": _KB_EMBEDDINGS is not None,
        "subjects": subjects,
        "ready": _KB_READY,
        "voice_engine": "edge-tts" if EDGE_TTS_AVAILABLE else ("gtts" if GTTS_AVAILABLE else "none"),
        "voice_name": VOICE_MALE_NIGERIAN,
        "tutor_name": "Mr. Ellams",
    }
