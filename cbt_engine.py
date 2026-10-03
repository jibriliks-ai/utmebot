"""
cbt_engine.py — bulletproof loader v4.
Handles both list-style and dict-style options. Searches recursively,
handles any malformed input, prints exact diagnostics.
"""
import json, random, traceback
from pathlib import Path
from collections import defaultdict

ALL_QS = []
LOCAL_DATABANK = defaultdict(list)
AVAILABLE_SUBJECTS = []
_seen = set()
FOUND_FILES = []


def _fp(q):
    try:
        return (str(q.get("subject_key", "")).lower()
                + "|" + str(q.get("question", "")).strip().lower()[:200])
    except Exception:
        return ""


def _normalize(q):
    if not isinstance(q, dict):
        return None
    try:
        options = q.get("options")

        # --- Build a flat list of option strings regardless of input shape ---
        opt_list = []
        if isinstance(options, list):
            opt_list = [str(o).strip() for o in options]
        elif isinstance(options, dict):
            for L in ("A", "B", "C", "D", "E"):
                v = options.get(L)
                if v is None:
                    v = options.get(L.lower())
                if v is None:
                    v = options.get(L.upper())
                opt_list.append(str(v).strip() if v is not None else "")
        else:
            opt_list = []

        def pick(i, key):
            v = q.get(key)
            if v and str(v).strip():
                return str(v).strip()
            if i < len(opt_list):
                return opt_list[i]
            return ""

        ans = (q.get("answer_letter") or q.get("answer") or q.get("ans") or "")
        ans = str(ans).strip().upper()[:1]

        return {
            "id": str(q.get("id") or q.get("source_id") or ""),
            "subject": str(q.get("subject", "")).strip(),
            "subject_key": str(q.get("subject_key", "")).strip().lower(),
            "year": q.get("year", ""),
            "topic": str(q.get("topic", "General")),
            "question": str(q.get("question", "")).strip(),
            "option_a": pick(0, "option_a"),
            "option_b": pick(1, "option_b"),
            "option_c": pick(2, "option_c"),
            "option_d": pick(3, "option_d"),
            "option_e": pick(4, "option_e"),
            "answer": ans,
            "answer_text": str(q.get("answer_text", "")).strip(),
            "explanation": str(q.get("explanation", "")).strip(),
        }
    except Exception:
        return None


def _add(q):
    if q is None:
        return False
    if not q.get("question"):
        return False
    if not q.get("option_a") or not q.get("option_b"):
        return False
    if q.get("answer") not in list("ABCDE"):
        return False
    fp = _fp(q)
    if not fp or fp in _seen:
        return False
    _seen.add(fp)
    ALL_QS.append(q)
    key = q.get("subject_key") or q.get("subject", "").lower().replace(" ", "_")
    if key:
        LOCAL_DATABANK[key].append(q)
    return True


def _load(path):
    """Load a JSON file and return number of questions added."""
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except Exception as e:
        print(f"[cbt_engine] cannot read {path}: {e}")
        return 0

    if not raw.strip():
        print(f"[cbt_engine] {path} is empty")
        return 0

    try:
        data = json.loads(raw)
    except Exception as e:
        preview = raw[:200].replace("\n", " ")
        print(f"[cbt_engine] {path} — invalid JSON: {e}")
        print(f"[cbt_engine]    starts with: {preview!r}")
        return 0

    # Extract a list of items
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        wrapped = None
        for k in ("questions", "data", "items", "results"):
            if isinstance(data.get(k), list):
                wrapped = data[k]
                break
        if wrapped is not None:
            items = wrapped
        elif "question" in data and "options" in data:
            items = [data]
        else:
            print(f"[cbt_engine] {path} — dict without questions list")
            print(f"[cbt_engine]    keys: {list(data.keys())[:10]}")
            return 0
    else:
        print(f"[cbt_engine] {path} — top-level is {type(data).__name__}, expected list")
        print(f"[cbt_engine]    preview: {str(data)[:200]!r}")
        return 0

    n = 0
    skipped = 0
    first_skips = []

    for item in items:
        try:
            norm = _normalize(item)
            if norm is None:
                skipped += 1
                if len(first_skips) < 3:
                    first_skips.append(f"non-dict item: {type(item).__name__} = {str(item)[:80]}")
                continue
            if _add(norm):
                n += 1
            else:
                skipped += 1
                if len(first_skips) < 3:
                    first_skips.append(
                        f"missing fields: q={str(norm.get('question',''))[:40]!r} "
                        f"a={norm.get('option_a','')[:20]!r} "
                        f"ans={norm.get('answer','')!r}"
                    )
        except Exception as e:
            skipped += 1
            if len(first_skips) < 3:
                first_skips.append(f"{type(e).__name__}: {e}")

    if skipped:
        print(f"[cbt_engine]    ({skipped} item(s) skipped in {Path(path).name})")
        for s in first_skips:
            print(f"[cbt_engine]      → {s}")
    return n


def _bootstrap():
    global FOUND_FILES
    try:
        cwd = Path(".").resolve()
        print(f"[cbt_engine] searching from {cwd}")

        skip_dirs = {"__pycache__", ".git", ".venv", "venv", "env", "node_modules"}

        file_strs = []
        try:
            for p in cwd.rglob("questions_*.json"):
                try:
                    if any(part in skip_dirs for part in p.parts):
                        continue
                    file_strs.append(str(p))
                except Exception:
                    continue
        except Exception as e:
            print(f"[cbt_engine] rglob error: {e}")

        file_strs = sorted(set(file_strs))
        FOUND_FILES = [str(Path(s).relative_to(cwd)) for s in file_strs]

        if not file_strs:
            print("[cbt_engine] no files matching questions_*.json found")
            try:
                top = sorted(p.name for p in cwd.iterdir())
                print(f"[cbt_engine]    cwd contains: {top[:40]}")
            except Exception:
                pass
        else:
            print(f"[cbt_engine] found {len(file_strs)} file(s)")

        total = 0
        for s in file_strs:
            try:
                n = _load(s)
                total += n
                rel = str(Path(s).relative_to(cwd))
                print(f"[cbt_engine] → {rel}: +{n}")
            except Exception as e:
                print(f"[cbt_engine] error on {s}: {e}")
                traceback.print_exc()

        for k in sorted(LOCAL_DATABANK.keys()):
            if LOCAL_DATABANK[k]:
                AVAILABLE_SUBJECTS.append(k)

        print(f"[cbt_engine] TOTAL: {len(ALL_QS)} questions across "
              f"{len(AVAILABLE_SUBJECTS)} subjects")
        for k in AVAILABLE_SUBJECTS:
            print(f"   {k}: {len(LOCAL_DATABANK[k])}")

    except Exception as e:
        print(f"[cbt_engine] bootstrap failed: {e}")
        traceback.print_exc()


_bootstrap()


def format_question(q, i, total):
    lines = [f"Q{i}/{total}", q.get("question", "")]
    for L in ("A", "B", "C", "D", "E"):
        opt = q.get(f"option_{L.lower()}")
        if opt:
            lines.append(f"{L}) {opt}")
    return "\n".join(lines)


def search_databank(query, subject=None, limit=5):
    q = (query or "").lower().strip()
    if not q:
        return []
    pool = LOCAL_DATABANK.get(subject) if subject else None
    if not pool:
        pool = ALL_QS
    words = [w for w in q.split() if len(w) > 2]
    if not words:
        return []
    scored = []
    for item in pool:
        text = item.get("question", "").lower()
        score = sum(1 for w in words if w in text)
        if score:
            scored.append((score, item))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scored[:limit]]


def get_random_question(subject=None):
    pool = LOCAL_DATABANK.get(subject) if subject else None
    if not pool:
        pool = ALL_QS
    return random.choice(pool) if pool else None


class _Fetcher:
    def fetch(self, subject, year=None, limit=40):
        key = (subject or "").lower()
        pool = LOCAL_DATABANK.get(key, [])
        if not pool:
            pool = [q for q in ALL_QS if key and key in q["subject"].lower()]
        if not pool:
            return []
        return random.sample(pool, min(limit, len(pool)))


fetcher = _Fetcher()
