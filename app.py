# app.py
from fastapi import FastAPI
from pydantic import BaseModel
import re, unicodedata
from typing import List, Dict, Any, Tuple

app = FastAPI(title="ICP + Dept + Role (CSV + external + per-dept excludes)")

# ---------- Utils ----------
def norm(s: str) -> str:
    s = (s or "").strip().lower()
    s = unicodedata.normalize("NFD", s)
    s = s.encode("ascii", "ignore").decode("ascii")  # quita acentos
    return re.sub(r"\s+", " ", s)

def any_match(text: str, patterns: List[str]) -> bool:
    return any(re.search(p, text, re.I) for p in patterns) if patterns else False

def split_csv(s: str | None) -> List[str]:
    if not s:
        return []
    return [x.strip() for x in s.split(",") if x.strip()]

def to_regex(items: List[str]) -> List[str]:
    """
    - '/foo.*/' -> usa 'foo.*' como regex literal
    - 'marketing' -> convierte a r'\bmarketing\b' escapado
    """
    pats = []
    for it in items:
        if len(it) >= 2 and it.startswith("/") and it.endswith("/"):
            pats.append(it[1:-1])
        else:
            pats.append(r"\b" + re.escape(it) + r"\b")
    return pats

# ---------- Reglas ----------
C_SUITE: List[Tuple[List[str], str]] = [
    (["\\bcio\\b","chief information officer"], "CIOs"),
    (["\\bcto\\b","chief technical","chief technology( officer)?"], "CTOs"),
    (["\\bciso\\b","chief information security officer"], "CISOs"),
    (["\\bcoo\\b","chief (of )?operations","operations officer","chief software officer"], "COOs"),
    (["\\bcco\\b","chief commercial officer"], "CCOs"),
    (["\\bceo\\b","chief executive officer"], "CEOs"),
    (["\\bcfo\\b","chief financial officer"], "CFOs"),
    (["\\bcso\\b","chief (system|systems|security|strategy) officer"], "CSOs"),
    (["\\bcao\\b","chief administrat(ive|ion) officer","\\badministrador(a)?\\b"], "CAOs"),
]

DEPARTMENTS = {
    "Marketing": {
        "must": [
            r"\bmarketing\b", r"\bdigital\b", r"\bcomunicaciones?\b",
            r"\binbound\b", r"\bemail\b", r"\bautomation\b"
        ],
        "seniority": [
            r"\bchief\b|\bcmo\b",
            r"\bhead\b|\bdirect(or|ora)\b",
            r"\bmanager\b|\bgerente\b|\bjefe\b|\bresponsable\b"
        ],
        # Excludes de departamento (para decidir ICP)
        "exclude": [
            r"\bjunior\b|\bjr\b", r"\btrainee\b|\bbecari[oa]\b|\bintern\b",
            r"\bassistant\b|\basistente\b|coordinador(a)?",
            r"\bspecialist\b|\bespecialista\b|\bconsultant\b",
            r"\bcommunity\b|\bartist\b|\bart\b",
            r"\bdesign\b|\bdise[nñ]o\b|\badvisor\b",
            r"\banalytics?\b|\bdata\b|\banalista\b",
            r"\bcustomer\b|\baccount\b"
        ],
        "roles": [
            (["\\bcmo\\b","chief marketing officer"], "CMOs"),
            (["\\bhead\\b","\\bdirect(or|ora)\\b","\\bgerente\\b","\\bmanager\\b"], "Directores de Marketing"),
        ],
    },
    "Tecnologia": {
        "must": [
            r"\b(it|ti)\b", r"\bsistemas\b", r"\btech\b",
            r"\btechnology\b", r"\binformatic[ao]\b", r"\binformation\b"
        ],
        "seniority": [
            r"\bchief\b|\bcio\b|\bcto\b|\bciso\b",
            r"\bhead\b|\bdirect(or|ora)\b|\bgerente\b|\bmanager\b|\bjefe\b|\bresponsable\b|\badministrador(a)?\b"
        ],
        "exclude": [
            r"\bjunior\b|\bjr\b", r"\btrainee\b|\bbecari[oa]\b|\bintern\b",
            r"\bassistant\b|\basistente\b",
            r"\bspecialist\b|\bespecialista\b|\bconsultant\b",
            r"\bcommunity\b|\bartist\b|\bdesign\b|\badvisor\b",
            r"\banalytics?\b|\banalista\b",
            r"\bdesarrollo ?de ?negocio\b|\bbusiness ?development\b"
        ],
        "roles": [
            (["\\bcto\\b","chief technology officer"], "CTOs"),
            (["\\bcio\\b","chief information officer"], "CIOs"),
            (["\\bhead\\b","\\bdirect(or|ora)\\b","\\bgerente\\b","\\bmanager\\b"], "Directores de Tecnología"),
        ],
    },
}

# ---------- IO ----------
class In(BaseModel):
    job_titles: str            # CSV: "Head of Marketing, CMO, IT Manager"
    excludes: str | None = ""  # CSV opcional (globales, definidos desde Clay)

class ItemOut(BaseModel):
    input: str
    is_icp: bool
    department: str
    role_generic: str
    why: Dict[str, Any]

class Out(BaseModel):
    results: List[ItemOut]

# ---------- Core ----------
def classify_one(job_title: str, external_excludes: List[str]) -> Dict[str, Any]:
    original = job_title
    t = norm(job_title)

    # 0) Excludes externos (globales). Si matchea, ya no es ICP.
    if any_match(t, external_excludes):
        return {
            "input": original,
            "is_icp": False,
            "department": "",
            "role_generic": "",
            "why": {"excluded_by": "external_excludes"}
        }

    # 1) C-Suite (prioridad)
    for pats, label in C_SUITE:
        if any_match(t, pats):
            return {
                "input": original,
                "is_icp": True,
                "department": "C-Suite",
                "role_generic": label,
                "why": {"matched": label}
            }

    # 2) Departamentos (excludes combinados: externos + por-dep)
    for dep, cfg in DEPARTMENTS.items():
        must_ok   = any_match(t, cfg["must"])
        senior_ok = any_match(t, cfg["seniority"])
        dep_excl  = cfg.get("exclude", [])
        excl_hit  = any_match(t, dep_excl) or any_match(t, external_excludes)
        if must_ok and senior_ok and not excl_hit:
            for pats, label in cfg["roles"]:
                if any_match(t, pats):
                    return {
                        "input": original,
                        "is_icp": True,
                        "department": dep,
                        "role_generic": label,
                        "why": {"must": True, "seniority": True, "exclude": False, "matched": label}
                    }
            return {
                "input": original,
                "is_icp": True,
                "department": dep,
                "role_generic": f"{dep} - Dirección/Gestión",
                "why": {"must": True, "seniority": True, "exclude": False, "matched": "generic"}
            }

    # 3) No match
    return {
        "input": original,
        "is_icp": False,
        "department": "",
        "role_generic": "",
        "why": {"no_match": True}
    }

# ---------- Endpoint ----------
@app.post("/classify", response_model=Out)
def classify(inp: In):
    titles = split_csv(inp.job_titles)
    ex_items = split_csv(inp.excludes)
    external_excludes = to_regex(ex_items) if ex_items else []
    results = [classify_one(t, external_excludes) for t in titles]
    return {"results": results}
