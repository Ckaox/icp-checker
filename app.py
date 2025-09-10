# app.py
from fastapi import FastAPI
from pydantic import BaseModel
import re, unicodedata
from typing import List, Dict, Any, Tuple, Optional

app = FastAPI(title="ICP + Dept + Role (rule-engine)")

# ---------- Utils ----------
def norm(s: str) -> str:
    s = (s or "").strip().lower()
    s = unicodedata.normalize("NFD", s)
    s = s.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", s)

def split_csv(s: Optional[str]) -> List[str]:
    if not s: return []
    return [x.strip() for x in s.split(",") if x.strip()]

def to_regex(items: List[str]) -> List[str]:
    out = []
    for it in items:
        if len(it) >= 2 and it.startswith("/") and it.endswith("/"):
            out.append(it[1:-1])
        else:
            out.append(r"\b" + re.escape(it) + r"\b")
    return out

def any_match(text: str, patterns: List[str]) -> bool:
    return any(re.search(p, text, re.I) for p in patterns) if patterns else False

def dynamic_role_label(dep: str, text: str) -> str:
    pairs = [
        (r"\bvice ?president(e)?\b|\bvp\b",                         "vicepresidentes"),
        (r"\bhead\b|\bdirect(or|ora)\b",                            "directores"),
        (r"\bmanager\b|\bgerente\b",                                "gerentes"),
        (r"\bjef[ea]\b|\bprincipal\b|\blead\b",                     "jefes"),
        (r"\bcoordinador(a)?\b|\bcoordinator\b",                    "coordinadores"),
        (r"\bresponsable\b",                                        "responsables"),
        (r"\bcontroller\b|\bcontrolador\b",                         "responsables de control de gestión"),
        (r"\baccountant\b|\bcontador(a)?\b|\bcontable(s)?\b",       "responsables contables"),
        (r"\bstrategist\b|\bestratega\b",                           "estrategas"),
        (r"\bejecutiv[oa]s?\b|\bexecutive\b",                       "ejecutivos"),
        (r"\bgestor(es)?\b",                                        "gestores"),
    ]
    for pat, lbl in pairs:
        if re.search(pat, text, re.I):
            return f"{lbl} de {dep.lower()}"
    return f"encargados de {dep.lower()}"

# ---------- Owners & C-suite (prioridad máxima) ----------
OWNERS = [
    r"\bfounder(s)?\b", r"\bco[- ]?founder(s)?\b",
    r"\bowner(s)?\b", r"\bpropietari[oa]s?\b",
    r"\bpartner(s)?\b|\bsocio(s)?\b",
    r"\bpresident(e|a)?\b", r"\bchair(man|woman)?\b"
]

# (patrones, label, departamento destino)
C_SUITE_MAP: List[Tuple[List[str], str, str]] = [
    (["\\bcmo\\b","chief marketing officer"],                         "CMOs",          "Marketing"),
    (["\\bcio\\b","chief information officer"],                       "CIOs",          "Tecnologia"),
    (["\\bcto\\b","chief technical","chief technology( officer)?"],   "CTOs",          "Tecnologia"),
    (["\\bciso\\b","chief information security officer"],             "CISOs",         "Tecnologia"),
    (["\\bcco\\b","chief commercial officer"],                        "CCOs",          "Ventas"),
    (["\\bcso\\b","chief sales officer"],                             "CSOs (Sales)",  "Ventas"),
    (["\\bcro\\b","chief revenue officer"],                           "CROs",          "Ventas"),
    (["\\bceo\\b","chief executive officer"],                         "CEOs",          "C-Suite"),
    (["\\bcfo\\b","chief financial officer"],                         "CFOs",          "C-Suite"),
    (["\\bcoo\\b","chief (of )?operations|chief operating( officer)?|operations officer"], "COOs","C-Suite"),
    (["\\bcao\\b","chief administrat(ive|ion) officer"],              "CAOs",          "C-Suite"),
]

# ---------- Seniority / Excludes comunes (sin C-levels) ----------
SENIORITY_COMMON = [
    r"\bvp\b|\bvice ?president(e)?\b",
    r"\bhead\b|\bdirect(or|ora)\b|\bdireccion\b|\bdirecci[oó]n\b",
    r"\bmanager\b|\bgerente\b|\bjef[ea]\b|\bresponsable\b|\blead\b|\bprincipal\b",
    r"\bcoordinador(a)?\b|\bcoordinator\b",
    r"\bstrategist\b|\bestratega\b",
    r"\bejecutiv[oa]s?\b|\bexecutive\b",
    r"\bgestor(es)?\b",
    r"\badministrador(a)?\b",
    r"\bcontroller\b|\bcontrolador\b",
    r"\baccountant\b|\bcontador(a)?\b|\bcontable(s)?\b",
    r"\bdepartment\b|\bdepartamento\b|\bdpto\b",
]

EXCLUDE_COMMON = [
    r"\bjunior\b|\bjr\b", r"\btrainee\b|\bbecari[oa]\b|\bintern\b",
    r"\bassistant\b|\basistente\b",
    r"\bspecialist\b|\bespecialista\b|\bconsultant\b",
    r"\bcommunity\b|\bartist\b|\bart\b",
    r"\bdesign\b|\bdise[nñ]o\b|\badvisor\b",
    r"\banalytics?\b|\banalista\b|\bdata\b",
    r"\bpaid\b|\bcustomer\b",
]

# ---------- Áreas (sinónimos ES/EN) ----------
TECH_AREAS = {
    "sistemas":         r"(?:\bsystem(s)?\b|\b(it\s*)?systems?\b|sistemas?)",
    "redes":            r"(?:\bnetwork(s)?\b|redes?)",
    "infraestructura":  r"(?:infraestructura|infrastructure)",
    "implementaciones": r"(?:implementation|implementaci[oó]n|deployment|despliegue)",
    "ingeniería":       r"(?:ingenier[íi]a|engineer(?:ing)?)",
    "it":               r"(?:\bti\b|\bit\b|informaci[oó]n|information)",
    "tecnología":       r"(?:tecnolog[íi]a|technology|tech|sistemas)",
    "devops":           r"(?:\bdevops\b)",
    "qa":               r"(?:\bqa\b|quality assurance|tester|testing|aseguramiento de calidad|control de calidad|quality control)",
    "proyectos":        r"(?:project manager|project lead|jefe de proyecto|gestor de proyecto|\bpm\b)",
    "arquitectura":     r"(?:arquitectur[ao]|\barchitecture\b|architect)",
    "seguridad":        r"(?:security|seguridad|infosec|ciberseguridad|cyber ?security)",
    "plataforma":       r"(?:platform|plataforma)",
    "nube":             r"(?:cloud|nube|aws|azure|gcp|google cloud)",
    "datos":            r"(?:data|datos|bi|business intelligence|analitica)",
}

MKT_AREAS = {
    "marketing":        r"\bmarketing\b",
    "marca":            r"(?:\bbrand(ing)?\b|\bmarca\b)",
    "contenido":        r"(?:\bcontenid[oa]\b|\bcontent\b)",
    "comunicaciones":   r"(?:\bcomunicaciones?\b|\bcomms\b|communications?)",
    "publicidad":       r"(?:\bpublicidad\b|\badvertis(ing|ement|ements)?\b|paid media)",
    "email":            r"\bemail\b",
    "automatización":   r"\bautomation\b|\bmarketing automation\b|hubspot|marketo",
    "inbound":          r"\binbound\b",
    "performance":      r"\bperformance\b|growth",
    "social":           r"(?:social media|redes sociales|community)",
    "seo":              r"\bseo\b|search engine optimization",
    "sem":              r"\bsem\b|paid search|google ads",
}

SALES_AREAS = {
    "ventas":           r"\bventas\b|\bsales\b",
    "comercial":        r"\bcomercial(es)?\b",
    "revenue":          r"\brevenue\b",
    "gtm":              r"\bgo[- ]?to[- ]?market\b|\bgtm\b",
    "bd":               r"\bbusiness ?development\b|\bbd[rm]?\b",
    "accounts":         r"\baccount (manager|executive)\b|\bae\b|\bam\b",
    "partner":          r"\bpartner(ship|s)?\b|alianzas|partnerships?",
    "presales":         r"\bpre[- ]?sales?\b|preventas",
    "postventa":        r"(?:post[- ]?sales?|postventa|customer success)",
}

FIN_AREAS = {
    "contabilidad":        r"(?:\baccounting\b|\bcontabilidad\b|\baccount\b|\bcontador(a)?\b|\bcontable(s)?\b)",
    "control de gestión":  r"(?:\bcontroller\b|\bcontrolador\b|\bcontrol de gesti[oó]n\b)",
    "finanzas":            r"(?:\bfinance\b|\bfinancial\b|\bfinanzas?\b|\bfinanciera\b)",
    "fiscalidad":          r"\bfiscal\b|tax",
    "tesorería":           r"(?:\btreasury\b|\btesorer[ií]a\b|cash management)",
    "ar":                  r"\baccounts? receivable\b|\bcuentas? por cobrar\b|\bar\b",
    "ap":                  r"\baccounts? payable\b|\bcuentas? por pagar\b|\bap\b",
    "fp&a":                r"\bfp&a\b|\bfinancial planning\b|\bplanning & analysis\b",
    "inversiones":         r"(?:investment|inversiones|asset management|portafolio|portfolio)",
    "auditoría":           r"(?:audit(?:ing)?|auditor[ií]a|auditor)",
    "riesgo":              r"(?:risk|riesgo)",
}

HR_AREAS = {
    "rrhh":               r"(?:recursos humanos|human resources|\bhr\b|\bpeople\b)",
    "talento":            r"(?:talent|talento|people operations|people ops|people partner)",
    "reclutamiento":      r"(?:recruit(ing|er)?|reclutamiento|selecci[oó]n|acquisition|acquisitions?)",
    "onboarding":         r"(?:onboarding|inducci[oó]n)",
    "capacitacion":       r"(?:capacita(c|ç)[ií]on|training|learning|l&d|learning and development)",
    "compensaciones":     r"(?:compensation|benefits|compensaciones|beneficios|c&b|total rewards)",
    "nomina":             r"(?:payroll|n[oó]mina)",
    "relaciones laborales": r"(?:labor relations|relaciones laborales)",
    "desempeno":          r"(?:performance management|desempe[ñn]o|evaluaci[oó]n de desempeño)",
    "cultura":            r"(?:culture|cultura|engagement|clima)",
}

LEGAL_AREAS = {
    "legal":              r"(?:legal|jur[ií]dico|law|legal affairs|asuntos legales)",
    "contratos":          r"(?:contracts?|contratos?)",
    "compliance":         r"(?:compliance|cumplimiento|regulatorio|regulatory|gobernanza|governance)",
    "asesoria":           r"(?:counsel|abogad[oa]s?|asesor(?:a)? legal|legal counsel|general counsel|gc\b)",
    "propiedad intelectual": r"(?:ip|propiedad intelectual|patentes|marcas|copyright)",
    "corporativo":        r"(?:corporate|societario|corporativo|m&a|fusiones|adquisiciones)",
    "litigios":           r"(?:litigation|litigios|disputes|arbitraje|arbitration)",
    "privacidad":         r"(?:privacy|privacidad|datos personales|gdpr|ccpa|data protection)",
}

OPS_AREAS = {
    "operaciones":        r"(?:operaciones|operations|ops\b)",
    "logistica":          r"(?:log[íi]stica|logistics|last mile|almac[eé]n|warehouse)",
    "supply chain":       r"(?:supply ?chain|cadena de suministro|planning|s&op|procurement|compras)",
    "fulfillment":        r"(?:fulfillment|operaci[oó]n de pedidos|preparaci[oó]n de pedidos)",
    "servicio":           r"(?:servicio al cliente|customer service|soporte|support)",
    "calidad":            r"(?:quality|calidad|qa operaciones)",
    "h&s":                r"(?:seguridad e higiene|hse|eHS|health & safety|seguridad industrial)",
}

# ---------- Acciones (labels o plantillas) ----------
GEN_ACTIONS = [
    {"re": r"(?:\bhead\b|\bdirect(or|ora)\b|VP|vice ?president(e)?)", "template": "directores de {area}"},
    {"re": r"(?:\bmanager\b|\bgerente\b)",                            "template": "gerentes de {area}"},
    {"re": r"(?:\bjef[ea]\b|\bprincipal\b|\blead\b)",                 "template": "jefes de {area}"},
    {"re": r"(?:\bcoordinador(a)?\b|\bcoordinator\b)",                "template": "coordinadores de {area}"},
    {"re": r"\bresponsable\b",                                        "template": "responsables de {area}"},
]

TECH_ACTIONS = [
    {"re": r"(?:\b(it\s*)?systems?\s*admin(?:istrator)?\b|\bsys\s*admin\b|\bsysadmin\b)", "label": "administradores de sistemas"},
    {"re": r"(?:\bnetwork\s*admin(?:istrator)?\b|\bredes?\s*admin(?:istrador|istradora)?\b)", "label": "administradores de redes"},
    {"re": r"systems?\s*and\s*network\s*admin(?:istrator)?", "label": "administradores de sistemas"},
    {"re": TECH_AREAS["qa"],        "label": "líderes de qa"},
    {"re": TECH_AREAS["proyectos"], "label": "project managers"},
    {"re": r"\bdevops\b",           "label": "devops"},
    *GEN_ACTIONS,
]

MKT_ACTIONS = [
    {"re": r"\bbrand(ing)?\b.*\bmanager\b|\bbrand manager\b",   "label": "gerentes de marca"},
    {"re": r"\bcontent\b.*\bmanager\b|\bcontent manager\b",     "label": "gerentes de contenido"},
    *GEN_ACTIONS,
]

SALES_ACTIONS = [
    {"re": r"\baccount manager\b",   "label": "account managers"},
    {"re": r"\baccount executive\b", "label": "account executives"},
    *GEN_ACTIONS,
]

FIN_ACTIONS = [
    {"re": FIN_AREAS["control de gestión"], "label": "responsables de control de gestión"},
    {"re": r"(?:\baccountant\b|\bcontador(a)?\b|\bcontable(s)?\b)", "label": "responsables contables"},
    {"re": FIN_AREAS["tesorería"],  "label": "responsables de tesorería"},
    {"re": FIN_AREAS["fiscalidad"], "label": "responsables fiscales"},
    {"re": FIN_AREAS["ar"],         "label": "responsables de cuentas"},
    {"re": FIN_AREAS["ap"],         "label": "responsables de cuentas"},
    {"re": FIN_AREAS["fp&a"],       "label": "responsables de FP&A"},
    *GEN_ACTIONS,
]

HR_ACTIONS = [
    {"re": r"(?:recruit(ing|er)?|selecci[oó]n|acquisition|acquisitions?)", "label": "reclutadores"},
    {"re": r"(?:hrbp|people partner|business partner)",                   "label": "business partners de rr. hh."},
    {"re": r"(?:payroll|n[oó]mina)",                                      "label": "responsables de nómina"},
    {"re": r"(?:compensation|benefits|total rewards|compensaciones|beneficios)", "label": "responsables de compensaciones y beneficios"},
    {"re": r"(?:training|learning|l&d|learning and development|capacitaci[oó]n)", "label": "responsables de capacitación"},
    *GEN_ACTIONS,
]

LEGAL_ACTIONS = [
    {"re": r"(?:general counsel|gc\b)",                                   "label": "general counsels"},
    {"re": r"(?:counsel|abogad[oa]s?|asesor(?:a)? legal)",                "label": "asesores legales"},
    {"re": r"(?:contracts?|contratos?)",                                  "label": "responsables de contratos"},
    {"re": r"(?:compliance|cumplimiento|regulatorio|regulatory|governance|gobernanza)", "label": "responsables de compliance"},
    {"re": r"(?:privacy|privacidad|gdpr|ccpa|data protection)",           "label": "responsables de privacidad"},
    *GEN_ACTIONS,
]

OPS_ACTIONS = [
    {"re": r"(?:log[íi]stica|logistics|warehouse|almac[eé]n|last mile)",  "label": "responsables de logística"},
    {"re": r"(?:supply ?chain|cadena de suministro|procurement|compras|planning|s&op)", "label": "responsables de supply chain"},
    {"re": r"(?:fulfillment|operaci[oó]n de pedidos|preparaci[oó]n de pedidos)", "label": "responsables de fulfillment"},
    {"re": r"(?:customer service|servicio al cliente|soporte|support)",   "label": "responsables de servicio al cliente"},
    {"re": r"(?:health & safety|seguridad e higiene|hse|ehs|seguridad industrial)", "label": "responsables de seguridad e higiene"},
    *GEN_ACTIONS,
]

# ---------- Dept config (orden importa; Marketing > Ventas tie-break) ----------
DEPARTMENTS: List[Tuple[str, Dict[str, Any]]] = [
    ("Marketing", {
        "must": [r"\bmarketing\b"],
        "seniority": SENIORITY_COMMON,
        "exclude": EXCLUDE_COMMON + [r"\btrade\b", r"\bperformance\b", r"\bproduct\b", r"\bads\b", r"\barea\b", r"\baccount\b"],
        "areas": MKT_AREAS, "actions": MKT_ACTIONS,
    }),
    ("Tecnologia", {
        "must": [
            r"\b(it|ti)\b", r"\bsistemas\b", r"\btechnology\b|\btech\b",
            r"\binformatic[ao]\b|\binformation\b",
            r"\bsoftware\b|\bplatform\b", r"\barquitectur[ao]?\b|\barchitecture\b",
            r"\binfraestructura\b|\binfrastructure\b", r"\boperaciones\b|\boperations\b",
            r"\bsecurity\b|\bseguridad\b",
        ],
        "seniority": SENIORITY_COMMON,
        "exclude": EXCLUDE_COMMON + [r"\bdesarrollo ?de ?negocio\b|\bbusiness ?development\b"],
        "areas": TECH_AREAS, "actions": TECH_ACTIONS,
    }),
    ("Ventas", {
        "must": [
            r"\bcomercial(es)?\b", r"\bventas\b", r"\bsales\b",
            r"\brevenue\b", r"\bgo[- ]?to[- ]?market\b|\bgtm\b",
            r"\bbusiness ?development\b|\bbd[rm]?\b",
            r"\baccount (manager|executive)\b|\bae\b|\bam\b",
            r"\bpartner(ship|s)?\b",
        ],
        "seniority": SENIORITY_COMMON,
        "exclude": EXCLUDE_COMMON + [r"\bmarketing\b"],
        "areas": SALES_AREAS, "actions": SALES_ACTIONS,
    }),
    ("Finanzas", {
        "must": [
            r"\bfinance\b|\bfinancial\b|\bfinanzas?\b|\bfinanciera\b",
            r"\baccounting\b|\bcontabilidad\b|\baccount\b",
            r"\bcontador(a)?\b|\bcontable(s)?\b|investment",
        ],
        "seniority": SENIORITY_COMMON + [r"\bfiscal\b", r"\bcontroller\b|\bcontrolador\b",
                                         r"\badministraci[oó]n\b|\badministrador(a)?\b|\badministrativ[oa]s?\b"],
        "exclude": EXCLUDE_COMMON + [r"\bkey\b"],
        "areas": FIN_AREAS, "actions": FIN_ACTIONS,
    }),
    ("RR. HH.", {
        "must": [r"(?:recursos humanos|human resources|\bhr\b|\bpeople\b|talent)"],
        "seniority": SENIORITY_COMMON,
        "exclude": EXCLUDE_COMMON,
        "areas": HR_AREAS, "actions": HR_ACTIONS,
    }),
    ("Legal", {
        "must": [r"(?:legal|jur[ií]dico|law|legal affairs|asuntos legales|compliance|contracts?)"],
        "seniority": SENIORITY_COMMON,
        "exclude": EXCLUDE_COMMON,
        "areas": LEGAL_AREAS, "actions": LEGAL_ACTIONS,
    }),
    ("Operaciones", {
        "must": [r"(?:operaciones|operations|ops|log[íi]stica|logistics|supply ?chain|fulfillment|warehouse|almac[eé]n)"],
        "seniority": SENIORITY_COMMON,
        "exclude": EXCLUDE_COMMON,
        "areas": OPS_AREAS, "actions": OPS_ACTIONS,
    }),
]

# ---------- Helpers de plantillas ----------
def detect_area(text: str, areas: Dict[str, str]) -> Optional[str]:
    for area, pat in areas.items():
        if re.search(pat, text, re.I):
            return area
    return None

def dept_label_from_templates(text: str, areas: Dict[str, str], actions: List[Dict[str, str]]) -> Optional[str]:
    for act in actions:
        if re.search(act["re"], text, re.I):
            if "label" in act:
                return act["label"]
            if "template" in act:
                area = detect_area(text, areas)
                if area:
                    return act["template"].format(area=area)
    return None

# ---------- IO ----------
class In(BaseModel):
    job_title: str
    excludes: Optional[str] = ""

class Out(BaseModel):
    input: str
    is_icp: bool
    department: str
    role_generic: str
    why: Dict[str, Any]

# ---------- Core ----------
def classify_one(job_title: str, external_excludes: List[str]) -> Dict[str, Any]:
    original = job_title
    t = norm(job_title)

    # Excludes externos
    if any_match(t, external_excludes):
        return {"input": original, "is_icp": False, "department": "", "role_generic": "", "why": {"excluded_by": "external_excludes"}}

    # Owners
    if any_match(t, OWNERS):
        return {"input": original, "is_icp": True, "department": "C-Suite", "role_generic": "propietarios", "why": {"matched": "owners"}}

    # C-Suite
    for pats, label, dep_fn in C_SUITE_MAP:
        if any(re.search(p, t, re.I) for p in pats):
            return {"input": original, "is_icp": True, "department": dep_fn, "role_generic": label, "why": {"matched": label}}

    # Tie-break Marketing sobre Ventas
    marketing_signal = bool(re.search(r"\bmarketing\b", t, re.I))

    # Departamentos en orden
    for dep, cfg in DEPARTMENTS:
        must_ok   = any_match(t, cfg["must"])
        senior_ok = any_match(t, cfg["seniority"])
        excl_hit  = any_match(t, cfg.get("exclude", [])) or any_match(t, external_excludes)

        if dep == "Ventas" and must_ok and marketing_signal:
            continue

        if must_ok and senior_ok and not excl_hit:
            specific = dept_label_from_templates(t, cfg["areas"], cfg["actions"])
            if specific:
                return {"input": original, "is_icp": True, "department": dep, "role_generic": specific,
                        "why": {"must": True, "seniority": True, "exclude": False, "matched": "templates"}}
            dyn = dynamic_role_label(dep, t)
            return {"input": original, "is_icp": True, "department": dep, "role_generic": dyn,
                    "why": {"must": True, "seniority": True, "exclude": False, "matched": "dynamic"}}

    return {"input": original, "is_icp": False, "department": "", "role_generic": "", "why": {"no_match": True}}

# ---------- API ----------
@app.post("/classify", response_model=Out)
def classify(inp: In):
    external_excludes = to_regex(split_csv(inp.excludes))
    return classify_one(inp.job_title, external_excludes)

@app.get("/health")
def health():
    return {"ok": True}


