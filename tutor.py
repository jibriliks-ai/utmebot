"""
tutor.py — Enhanced DeepSeek AI Tutor with RAG (Retrieval-Augmented Generation).
Combines:
- BM25 keyword retrieval from questions_*.json databank (no API key needed)
- Optional semantic search via sentence-transformers (if installed)
- DeepSeek thinking mode for reasoning
- gTTS voice generation
"""
import os
import io
import re
import json
import glob
import time
import pickle
import traceback
from pathlib import Path

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from gtts import gTTS
from telegram import InputFile

# ── Config ──────────────────────────────────────────────
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"

# HARDCODED — do NOT override via env var. Valid names: deepseek-flash, deepseek-v4-pro
DEEPSEEK_MODEL = "deepseek-flash"

# ── BM25 (lightweight, no API key needed) ───────────────
try:
    from rank_bm25 import BM25Okapi
    BM25_AVAILABLE = True
    print("[tutor] BM25 retrieval ready")
except ImportError:
    BM25_AVAILABLE = False
    print("[tutor] rank_bm25 not installed — BM25 retrieval disabled")

# ── Optional embedding model (lazy-loaded, heavy) ───────
_EMBED_MODEL = None
EMBEDDING_AVAILABLE = False
try:
    from sentence_transformers import SentenceTransformer
    EMBEDDING_AVAILABLE = True
    print("[tutor] sentence-transformers available (semantic search ready)")
except ImportError:
    print("[tutor] sentence-transformers not installed — semantic search disabled")

# ── Knowledge Base (in-memory) ──────────────────────────
_KB_CHUNKS = []          # List of dicts: {text, subject, source, type}
_KB_BM25 = None          # BM25 index
_KB_EMBEDDINGS = None    # numpy array of embeddings
_KB_TOKENIZED = []       # Tokenized corpus for BM25
_KB_READY = False
_KB_BUILDING = False

# ── LLM Client ──────────────────────────────────────────
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


# ═══════════════════════════════════════════════════════
# KNOWLEDGE BASE BUILDER
# ═══════════════════════════════════════════════════════

def _tokenize(text):
    """Simple lowercase word tokenizer for BM25."""
    return re.findall(r"[a-z0-9]+", text.lower())


def _load_questions_databank():
    """Load all questions_*.json files into searchable chunks."""
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
                if q.get("year"):
                    parts.append(f"Year: {q['year']}")
                if q.get("question"):
                    parts.append(f"Question: {q['question']}")
                for L in ("A", "B", "C", "D", "E"):
                    opt = q.get(f"option_{L.lower()}")
                    if opt:
                        parts.append(f"Option {L}: {opt}")
                if q.get("answer"):
                    parts.append(f"Correct Answer: {q['answer']}")
                if q.get("answer_text"):
                    parts.append(f"Answer Text: {q['answer_text']}")
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
    """Load optional syllabus/*.txt files as additional knowledge."""
    chunks = []
    syllabus_dir = Path("syllabus")
    if not syllabus_dir.exists():
        return chunks
    for txt_file in sorted(syllabus_dir.glob("*.txt")):
        try:
            text = txt_file.read_text(encoding="utf-8", errors="ignore")
            # Chunk by ~800 chars with 100 overlap
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
    """Build embeddings with all-MiniLM-L6-v2 (lazy-loaded, CPU-only)."""
    global _EMBED_MODEL
    if not EMBEDDING_AVAILABLE:
        return None
    try:
        if _EMBED_MODEL is None:
            print("[tutor] Loading all-MiniLM-L6-v2 (first time ~80MB download)...")
            _EMBED_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
        import numpy as np
        embeddings = _EMBED_MODEL.encode(
            texts,
            batch_size=32,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        return embeddings.astype("float32")
    except Exception as e:
        print(f"[tutor] Embedding build failed: {e}")
        return None


def build_knowledge_base(force_rebuild=False):
    """
    Build the in-memory knowledge base from questions + syllabus.
    Called once at bot startup. Fast (<5s for 5000 questions).
    """
    global _KB_CHUNKS, _KB_BM25, _KB_EMBEDDINGS, _KB_TOKENIZED, _KB_READY, _KB_BUILDING

    if _KB_READY and not force_rebuild:
        return True
    if _KB_BUILDING:
        return False
    _KB_BUILDING = True

    try:
        print("[tutor] Building knowledge base...")
        t0 = time.time()

        # Load sources
        chunks = _load_questions_databank()
        chunks.extend(_load_syllabus_files())

        if not chunks:
            print("[tutor] No knowledge chunks loaded — tutor will use LLM-only mode")
            _KB_READY = True
            _KB_BUILDING = False
            return False

        _KB_CHUNKS = chunks
        texts = [c["text"] for c in chunks]

        # Build BM25
        if BM25_AVAILABLE:
            _KB_TOKENIZED = [_tokenize(t) for t in texts]
            _KB_BM25 = BM25Okapi(_KB_TOKENIZED)
            print(f"[tutor] BM25 index built ({len(texts)} chunks)")

        # Optionally build embeddings (only if sentence-transformers installed)
        if EMBEDDING_AVAILABLE and not force_rebuild:
            emb = _build_embeddings(texts)
            if emb is not None:
                _KB_EMBEDDINGS = emb
                print(f"[tutor] Embedding index built ({emb.shape})")

        elapsed = time.time() - t0
        print(f"[tutor] ✅ Knowledge base ready in {elapsed:.1f}s "
              f"({len(chunks)} chunks, BM25={BM25_AVAILABLE}, "
              f"Embed={_KB_EMBEDDINGS is not None})")

        _KB_READY = True
        _KB_BUILDING = False
        return True

    except Exception as e:
        print(f"[tutor] ❌ Knowledge base build failed: {e}")
        traceback.print_exc()
        _KB_BUILDING = False
        return False


# ═══════════════════════════════════════════════════════
# RETRIEVAL
# ═══════════════════════════════════════════════════════

def _bm25_search(query, top_k=5, subject_filter=None):
    """BM25 keyword retrieval."""
    if _KB_BM25 is None or not _KB_CHUNKS:
        return []
    tokens = _tokenize(query)
    if not tokens:
        return []
    scores = _KB_BM25.get_scores(tokens)
    # Get top N*3 (to allow subject filtering)
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
    """Semantic search using embeddings (if available)."""
    if _KB_EMBEDDINGS is None or _EMBED_MODEL is None:
        return []
    try:
        import numpy as np
        q_emb = _EMBED_MODEL.encode([query], convert_to_numpy=True).astype("float32")
        # Cosine similarity
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
    """
    Hybrid retrieval: combine BM25 + semantic results.
    Falls back gracefully if any component is unavailable.
    """
    if not _KB_READY or not _KB_CHUNKS:
        return []

    bm25_results = _bm25_search(query, top_k=top_k * 2, subject_filter=subject)
    semantic_results = _semantic_search(query, top_k=top_k * 2, subject_filter=subject)

    # Merge (deduplicate by chunk text)
    seen = set()
    merged = []
    # Interleave: BM25 first (keyword matches are strong signals)
    for r in bm25_results:
        key = r["chunk"]["text"][:120]
        if key not in seen:
            seen.add(key)
            r["source_type"] = "bm25"
            merged.append(r)
    for r in semantic_results:
        key = r["chunk"]["text"][:120]
        if key not in seen:
            seen.add(key)
            r["source_type"] = "semantic"
            merged.append(r)

    return merged[:top_k]


def _format_context(results, max_per_chunk=800):
    """Format retrieved chunks into a context block for the prompt."""
    if not results:
        return ""
    lines = ["\n=== RETRIEVED FROM JAMB DATABANK ===\n"]
    for i, r in enumerate(results, 1):
        c = r["chunk"]
        tag = f"[{i}] ({c.get('type','doc')} | {c.get('subject','general')} | {c.get('source','')})"
        lines.append(f"{tag}\n{c['text'][:max_per_chunk]}\n")
    lines.append("=== END OF RETRIEVED CONTEXT ===\n")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════
# SYSTEM PROMPT
# ═══════════════════════════════════════════════════════

SYSTEM_PROMPT = """You are the UTME Success Coach AI Tutor — an elite JAMB tutor
for Nigerian students. You explain questions the way a brilliant, patient
teacher would.

You have access to a RETRIEVED CONTEXT section below containing real JAMB past
questions and syllabus excerpts. USE THIS CONTEXT AS YOUR PRIMARY SOURCE OF TRUTH.

STRICT OUTPUT FORMAT:
1. **What the question is asking** (1 short sentence).
2. **Step-by-step solution** (numbered steps, show every calculation).
3. **Final Answer** (bold, unmistakable).
4. **One exam tip** (only if genuinely useful).

RULES:
- If the retrieved context contains a matching past question, use its answer
  and explanation directly. Mention "From JAMB past questions" when you do.
- If the context does not contain a direct match, answer from your JAMB
  syllabus knowledge, but stay strictly within UTME scope.
- No greetings, no filler ("Sure!", "Great question!").
- Never say you are an AI.
- Keep the explanation under 250 words.
- Simple English for a Nigerian secondary school student.
- Maths/Physics/Chemistry: show every step, never skip.
- English/Literature: quote the relevant text when useful.
- If the question is completely off-syllabus, reply exactly:
  "This question is outside the UTME syllabus."
"""


# ═══════════════════════════════════════════════════════
# PUBLIC API (matches your existing tutor.py signatures)
# ═══════════════════════════════════════════════════════

def ask_tutor(question_text: str, subject: str = "") -> str:
    """
    Return a plain-text explanation grounded in retrieved JAMB context.
    Retries once on transient errors. Falls back to LLM-only if KB is empty.
    """
    if _CLIENT is None:
        return (
            "⚠️ The AI Tutor isn't configured yet. "
            "Ask the admin to set DEEPSEEK_API_KEY on the server."
        )

    # 1. Retrieve relevant context from the knowledge base
    results = retrieve_context(question_text, subject=subject, top_k=5)
    context_block = _format_context(results) if results else ""

    # 2. Build the augmented user prompt
    user_prompt = ""
    if subject:
        user_prompt += f"Subject: {subject}\n\n"
    if context_block:
        user_prompt += context_block + "\n"
    user_prompt += f"STUDENT QUESTION:\n{question_text}"

    # 3. Call DeepSeek (with retry)
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
                n_ctx = len(results)
                print(f"[tutor] OK (attempt {attempt}, {len(text)} chars, "
                      f"ctx={n_ctx} chunks)")
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
    """
    Health check at startup.
    Returns (ok: bool, detail: str).
    """
    if _CLIENT is None:
        return False, "no client"

    # Check DeepSeek reachability
    try:
        r = _CLIENT.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[{"role": "user", "content": "Say OK"}],
            max_tokens=10,
            stream=False,
        )
        llm_status = (r.choices[0].message.content or "").strip()
    except Exception as e:
        llm_status = f"LLM error: {type(e).__name__}: {e}"

    # Check knowledge base
    kb_status = (
        f"KB: {len(_KB_CHUNKS)} chunks, "
        f"BM25={_KB_BM25 is not None}, "
        f"Embed={_KB_EMBEDDINGS is not None}"
        if _KB_READY else "KB: not built"
    )

    ok = "OK" in llm_status.upper() or "ok" in llm_status.lower()
    return ok, f"{llm_status} | {kb_status}"


def get_kb_stats():
    """Return knowledge base statistics (for /debug)."""
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
    }
