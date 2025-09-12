# app.py
from fastapi import FastAPI
from pydantic import BaseModel
import re, unicodedata
from typing import List, Dict, Any, Tuple, Optional

app = FastAPI(title="ICP + Dept + Role (areas+seniority engine)")

# ---------------- Utils ----------------
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


# ---------------- Owners & C-Suite (prioridad máxima) ----------------
OWNERS = [
    r"\bfounder(s)?\b", r"\bco[- ]?founder(s)?\b",
    r"\bfundador(a)?s?\b", r"\bco[- ]?fundador(a)?s?\b",
    r"\bowner(s)?\b", r"\bpropietari[oa]s?\b",
    r"\bsoci[oa]s?\b", r"\bpartner(s)?\b",
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


# ---------------- Seniority / Excludes comunes (sin C-levels) ----------------
# Mantenemos esto para gatear ICP (must + seniority) y para fallback si no hay área
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

# -------- Router de Proyectos (PM) --------
PM_PATTERN = r"(?:\bproject (manager|lead|director)\b|\bjefe de proyecto(s)?\b|\bgestor de proyecto(s)?\b|\bpm\b|\bdirect(or|ora) de proyecto(s)?\b)"

# ---- Títulos "sueltos" (sin área/dep) que deben contar como C-Suite
SOLO_TITLES = [
    (r"^\s*vp\s*$|^\s*vice ?president(e)?\s*$", "vicepresidentes"),
    (r"^\s*director(a)?\s*$",                  "directores"),
    (r"^\s*gerente\s*$",                       "gerentes"),
    (r"^\s*manager\s*$",                       "managers"),
]

# ---- Departamentos "solo" (nombres/abreviaturas) -> responsables de {dep}
DEPT_STANDALONE = [
    # Marketing
    (r"^\s*(marketing|mkt)\s*$",                    ("Marketing", "responsables de marketing")),
    # Tecnología / IT
    (r"^\s*(it|ti|sistemas|tecnolog[ií]a|technology|tech)\s*$", ("Tecnologia", "responsables de tecnologia")),
    # Ventas / Comercial
    (r"^\s*(ventas|sales|comercial(?:es)?)\s*$",    ("Ventas", "responsables de ventas")),
    # Finanzas / Contabilidad
    (r"^\s*(finanzas?|finance|financial|contabilidad|accounting)\s*$", ("Finanzas", "responsables de finanzas")),
    # RR. HH.
    (r"^\s*(rr\.?\s*hh\.?|r\.?\s*r\.?\s*h\.?\s*h\.?|recursos humanos|hr|human resources|people)\s*$",
     ("RR. HH.", "responsables de recursos humanos")),
    # Legal
    (r"^\s*(legal|jur[ií]dico|law|legal affairs)\s*$", ("Legal", "responsables de legal")),
    # Operaciones
    (r"^\s*(operaciones|operations|ops|log[ií]stica|logistics|supply ?chain)\s*$",
     ("Operaciones", "responsables de operaciones")),
]

TECH_HINTS = [
    r"\b(it|ti)\b", r"\bsistemas\b", r"\btechnology\b|\btech\b",
    r"\binformatic[ao]\b|\binformation\b",
    r"\bsoftware\b|\bplatform\b", r"\barquitectur[ao]?\b|\barchitecture\b",
    r"\binfraestructura\b|\binfrastructure\b",
    r"\bsecurity\b|\bseguridad\b",
    r"\bcloud\b|\bnube\b|aws|azure|\bgcp\b|\bgoogle cloud\b",
    r"\bdevops\b", r"\bdata\b|bi|analytics?"
]

MKT_HINTS = [
    r"\bmarketing\b", r"\bbrand(ing)?\b|\bmarca\b", r"\bcontent\b|\bcontenid[oa]\b",
    r"\bcomunicaciones?\b|\bcomms\b|communications?",
    r"\bpublicidad\b|\badvertis(ing|ement|ements)?\b|paid media",
    r"\bseo\b|\bsem\b|\bperformance\b|\bgrowth\b|\bautomation\b|\bemail\b|social media|redes sociales"
]

OPS_HINTS = [
    r"\boperaciones\b|\boperations\b|\bops\b",
]

# ---------------- Seniorities genéricos (forman “{seniority} de {área}”) ----------------
GEN_SENIORITIES: List[Tuple[str, str]] = [
    (r"(?:\bhead\b|\bdirect(or|ora)\b|VP|vice ?president(e)?)", "directores"),
    (r"(?:\bmanager\b|\bgerente\b)",                            "gerentes"),
    (r"(?:\bjef[ea]\b|\bprincipal\b|\blead\b)",                 "jefes"),
    (r"(?:\bcoordinador(a)?\b|\bcoordinator\b)",                "coordinadores"),
    (r"\bresponsable\b",                                        "responsables"),
    (r"(?:\bcontroller\b|\bcontrolador\b)",                     "responsables de control de gestión"),
    (r"(?:\baccountant\b|\bcontador(a)?\b|\bcontable(s)?\b)",   "responsables contables"),
    (r"(?:\bstrategist\b|\bestratega\b)",                       "estrategas"),
    (r"(?:\bejecutiv[oa]s?\b|\bexecutive\b)",                   "ejecutivos"),
    (r"(?:\bgestor(es)?\b)",                                    "gestores"),
]

def seniority_label(text: str) -> Optional[str]:
    for pat, plural in GEN_SENIORITIES:
        if re.search(pat, text, re.I):
            return plural
    return None


# ---------------- Áreas por departamento (sinónimos ES/EN) ----------------
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
    "proyectos":        r"(?:project manager|director de proyectos|proyectos|project|project lead|jefe de proyecto|gestor de proyecto|\bpm\b)",
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
    "performance":      r"(?:\bperformance\b|growth)",
    "social":           r"(?:social media|redes sociales|community)",
    "seo":              r"(?:\bseo\b|search engine optimization)",
    "sem":              r"(?:\bsem\b|paid search|google ads)",
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
    "fiscalidad":          r"(?:\bfiscal\b|tax)",
    "tesorería":           r"(?:\btreasury\b|\btesorer[ií]a\b|cash management)",
    "ar":                  r"(?:accounts? receivable|cuentas? por cobrar|\bar\b)",
    "ap":                  r"(?:accounts? payable|cuentas? por pagar|\bap\b)",
    "fp&a":                r"(?:\bfp&a\b|financial planning|planning & analysis)",
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
    "h&s":                r"(?:seguridad e higiene|hse|ehs|health & safety|seguridad industrial)",
}


# ---------------- Reglas especiales (labels fijos por depto) ----------------
# Tecnología: sysadmin/netadmin/QA/PM/DevOps, etc.
SPECIAL_TECH: List[Tuple[str, str]] = [
    (r"(?:\b(it\s*)?systems?\s*admin(?:istrator)?\b|\bsys\s*admin\b|\bsysadmin\b)", "administradores de sistemas"),
    (r"(?:\bnetwork\s*admin(?:istrator)?\b|\bredes?\s*admin(?:istrador|istradora)?\b)", "administradores de redes"),
    (r"systems?\s*and\s*network\s*admin(?:istrator)?", "administradores de sistemas"),
    (TECH_AREAS["qa"],        "líderes de qa"),
    (TECH_AREAS["proyectos"], "project managers"),
    (r"\bdevops\b",           "devops"),
]

# Marketing: atajos comunes
SPECIAL_MKT: List[Tuple[str, str]] = [
    (r"\bbrand(ing)?\b.*\bmanager\b|\bbrand manager\b",   "gerentes de marca"),
    (r"\bcontent\b.*\bmanager\b|\bcontent manager\b",     "gerentes de contenido"),
]

# Ventas: atajos comunes
SPECIAL_SALES: List[Tuple[str, str]] = [
    (r"\baccount manager\b",   "account managers"),
    (r"\baccount executive\b", "account executives"),
]

# Finanzas: roles “bonitos”
SPECIAL_FIN: List[Tuple[str, str]] = [
    (FIN_AREAS["control de gestión"], "responsables de control de gestión"),
    (r"(?:\baccountant\b|\bcontador(a)?\b|\bcontable(s)?\b)", "responsables contables"),
    (FIN_AREAS["tesorería"],  "responsables de tesorería"),
    (FIN_AREAS["fiscalidad"], "responsables fiscales"),
    (FIN_AREAS["ar"],         "responsables de cuentas por cobrar"),
    (FIN_AREAS["ap"],         "responsables de cuentas por pagar"),
    (FIN_AREAS["fp&a"],       "responsables de FP&A"),
]

# RRHH
SPECIAL_HR: List[Tuple[str, str]] = [
    (r"(?:recruit(ing|er)?|selecci[oó]n|acquisition|acquisitions?)", "reclutadores"),
    (r"(?:hrbp|people partner|business partner)",                   "business partners de rr. hh."),
    (r"(?:payroll|n[oó]mina)",                                      "responsables de nómina"),
    (r"(?:compensation|benefits|total rewards|compensaciones|beneficios)", "responsables de compensaciones y beneficios"),
    (r"(?:training|learning|l&d|learning and development|capacitaci[oó]n)", "responsables de capacitación"),
]

# Legal
SPECIAL_LEGAL: List[Tuple[str, str]] = [
    (r"(?:general counsel|gc\b)",                                   "general counsels"),
    (r"(?:counsel|abogad[oa]s?|asesor(?:a)? legal)",                "asesores legales"),
    (r"(?:contracts?|contratos?)",                                  "responsables de contratos"),
    (r"(?:compliance|cumplimiento|regulatorio|regulatory|governance|gobernanza)", "responsables de compliance"),
    (r"(?:privacy|privacidad|gdpr|ccpa|data protection)",           "responsables de privacidad"),
]

# Operaciones
SPECIAL_OPS: List[Tuple[str, str]] = [
    (r"(?:log[íi]stica|logistics|warehouse|almac[eé]n|last mile)",  "responsables de logística"),
    (r"(?:supply ?chain|cadena de suministro|procurement|compras|planning|s&op)", "responsables de supply chain"),
    (r"(?:fulfillment|operaci[oó]n de pedidos|preparaci[oó]n de pedidos)", "responsables de fulfillment"),
    (r"(?:customer service|servicio al cliente|soporte|support)",   "responsables de servicio al cliente"),
    (r"(?:health & safety|seguridad e higiene|hse|ehs|seguridad industrial)", "responsables de seguridad e higiene"),
]


# ---------------- Motor: “especiales” -> “{seniority} de {área}” ----------------
def detect_first(text: str, pairs: List[Tuple[str, str]]) -> Optional[str]:
    for pat, label in pairs:
        if re.search(pat, text, re.I):
            return label
    return None

def detect_area(text: str, areas: Dict[str, str]) -> Optional[str]:
    for area, pat in areas.items():
        if re.search(pat, text, re.I):
            return area
    return None

def label_by_area_and_seniority(dep: str, text: str, areas: Dict[str, str], specials: List[Tuple[str, str]]) -> Optional[str]:
    # 1) Reglas especiales
    sp = detect_first(text, specials)
    if sp:
        return sp
    # 2) Genérico: {seniority} de {área} (si hay ambas; si no hay área, usamos depto)
    sen = seniority_label(text)
    if not sen:
        return None
    area = detect_area(text, areas)
    return f"{sen} de {(area or dep).lower()}"


# ---------------- Dept config (orden importa; tie-break Marketing > Ventas) ----------------
DEPARTMENTS: List[Tuple[str, Dict[str, Any]]] = [
    ("Marketing", {
        "must": [r"\bmarketing\b"],
        "seniority": SENIORITY_COMMON,
        "exclude": EXCLUDE_COMMON + [r"\btrade\b", r"\bperformance\b", r"\bproduct\b", r"\bads\b", r"\barea\b", r"\baccount\b"],
        "areas": MKT_AREAS, "specials": SPECIAL_MKT,
    }),
    ("Tecnologia", {
        "must": [
            r"\b(it|ti)\b", r"\bsistemas\b", r"\btechnology\b|\btech\b",
            r"\binformatic[ao]\b|\binformation\b",
            r"\bsoftware\b|\bplatform\b", r"\barquitectur[ao]?\b|\barchitecture\b",
            r"\binfraestructura\b|\binfrastructure\b",
            r"\bsecurity\b|\bseguridad\b",
        ],
        "seniority": SENIORITY_COMMON,
        "exclude": EXCLUDE_COMMON + [r"\bdesarrollo ?de ?negocio\b|\bbusiness ?development\b"],
        "areas": TECH_AREAS, "specials": SPECIAL_TECH,
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
        "areas": SALES_AREAS, "specials": SPECIAL_SALES,
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
        "areas": FIN_AREAS, "specials": SPECIAL_FIN,
    }),
    ("RR. HH.", {
        "must": [r"(?:recursos humanos|human resources|\bhr\b|\bpeople\b|talent)"],
        "seniority": SENIORITY_COMMON,
        "exclude": EXCLUDE_COMMON,
        "areas": HR_AREAS, "specials": SPECIAL_HR,
    }),
    ("Legal", {
        "must": [r"(?:legal|jur[ií]dico|law|legal affairs|asuntos legales|compliance|contracts?)"],
        "seniority": SENIORITY_COMMON,
        "exclude": EXCLUDE_COMMON,
        "areas": LEGAL_AREAS, "specials": SPECIAL_LEGAL,
    }),
    ("Operaciones", {
        "must": [r"(?:operaciones|operations|ops|log[íi]stica|logistics|supply ?chain|fulfillment|warehouse|almac[eé]n)"],
        "seniority": SENIORITY_COMMON,
        "exclude": EXCLUDE_COMMON,
        "areas": OPS_AREAS, "specials": SPECIAL_OPS,
    }),
]


# ---------------- IO ----------------
class In(BaseModel):
    job_title: str
    excludes: Optional[str] = ""

class Out(BaseModel):
    input: str
    is_icp: bool
    department: str
    role_generic: str
    why: Dict[str, Any]


# ---------------- Core ----------------
def dynamic_role_label(dep: str, text: str) -> str:
    # Último fallback: usa seniority si lo encuentra; si no, “encargados de …”
    sen = seniority_label(text)
    if sen:
        return f"{sen} de {dep.lower()}"
    return f"encargados de {dep.lower()}"

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
            
    # --- VP / Director / Gerente / Manager "sueltos" -> C-Suite genérico
    for pat, plural_label in SOLO_TITLES:
        if re.search(pat, t, re.I):
            return {
                "input": original,
                "is_icp": True,
                "department": "C-Suite",
                "role_generic": plural_label,
                "why": {"matched": "solo_title"}
            }

    # --- Departamento "solo" (Marketing, RRHH, etc.) -> responsables de {dep}
    for pat, (dep_name, role_lbl) in DEPT_STANDALONE:
        if re.search(pat, t, re.I):
            return {
                "input": original,
                "is_icp": True,
                "department": dep_name,
                "role_generic": role_lbl,
                "why": {"matched": "standalone_department"}
            }

        # --- Router específico para Proyectos (PM / Director de Proyectos) ---
    if re.search(PM_PATTERN, t, re.I):
        # Detectamos contexto
        if any_match(t, TECH_HINTS):
            dep = "Tecnologia"
        elif any_match(t, MKT_HINTS):
            dep = "Marketing"
        elif any_match(t, OPS_HINTS):
            dep = "Operaciones"
        else:
            # Preferencia por Tecnología cuando no hay contexto claro
            dep = "Tecnologia"

        # Etiqueta por seniority -> "... de proyectos"
        sen = seniority_label(t) or "responsables"
        label = f"{sen} de proyectos"

        return {
            "input": original,
            "is_icp": True,
            "department": dep,
            "role_generic": label,
            "why": {"matched": "pm_router", "department_routed": dep}
        }
            
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
            label = label_by_area_and_seniority(dep, t, cfg["areas"], cfg["specials"])
            if label:
                return {"input": original, "is_icp": True, "department": dep, "role_generic": label,
                        "why": {"must": True, "seniority": True, "exclude": False, "matched": "area+seniority/special"}}
            # Fallback final
            dyn = dynamic_role_label(dep, t)
            return {"input": original, "is_icp": True, "department": dep, "role_generic": dyn,
                    "why": {"must": True, "seniority": True, "exclude": False, "matched": "fallback"}}

    # Sin match
    return {"input": original, "is_icp": False, "department": "", "role_generic": "", "why": {"no_match": True}}


# ---------------- API ----------------
@app.post("/classify", response_model=Out)
def classify(inp: In):
    external_excludes = to_regex(split_csv(inp.excludes))
    return classify_one(inp.job_title, external_excludes)

@app.get("/health")
def health():
    return {"ok": True}



