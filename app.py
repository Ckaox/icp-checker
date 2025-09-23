# app.py
from fastapi import FastAPI, Response
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel
import re, unicodedata
from typing import List, Dict, Any, Tuple, Optional

app = FastAPI(
    title="ICP + Dept + Role (areas+seniority engine)",
    default_response_class=ORJSONResponse  # Faster JSON serialization
)

# Add gzip compression for faster responses
app.add_middleware(GZipMiddleware, minimum_size=500)

# ---------------- Utils ----------------
# Normalization cache for performance
_norm_cache: Dict[str, str] = {}
_norm_cache_max_size = 500

def norm(s: str) -> str:
    """Optimized text normalization with caching"""
    if not s:
        return ""
    
    # Check cache first
    if s in _norm_cache:
        return _norm_cache[s]
    
    # Normalize
    result = s.strip().lower()
    result = unicodedata.normalize("NFD", result)
    result = result.encode("ascii", "ignore").decode("ascii")
    result = re.sub(r"\s+", " ", result)
    
    # Cache with size limit
    if len(_norm_cache) < _norm_cache_max_size:
        _norm_cache[s] = result
    
    return result

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

def singularize_role(role_generic: str) -> str:
    """Convierte roles genéricos plurales a singular"""
    if not role_generic:
        return ""
    
    # Diccionario de conversiones específicas
    singular_map = {
        # C-Suite
        "CEOs": "CEO",
        "CFOs": "CFO", 
        "CTOs": "CTO",
        "CMOs": "CMO",
        "COOs": "COO",
        "CIOs": "CIO",
        "CHROs": "CHRO",
        "CSOs (Sales)": "CSO (Sales)",
        "CROs": "CRO",
        "CDOs": "CDO",
        "CAOs": "CAO",
        "CQAs": "CQA",
        "CISOs": "CISO",
        "CCOs": "CCO",
        
        # Roles genéricos plurales
        "propietarios": "propietario",
        "directores": "director",
        "gerentes": "gerente", 
        "managers": "manager",
        "vicepresidentes": "vicepresidente",
        "ejecutivos": "ejecutivo",
        "coordinadores": "coordinador",
        "responsables": "responsable",
        "estrategas": "estratega",
        "gestores": "gestor",
        "supervisores": "supervisor",
        "administrativos": "administrativo",
        
        # Roles específicos con "de"
        "directores generales": "director general",
        "directores asociados": "director asociado",
        "directores regionales": "director regional",
        "jefes de departamento": "jefe de departamento",
        "directores de administración": "director de administración",
        
        # Tecnología
        "gerentes de tecnología": "gerente de tecnología",
        "gerentes de tecnologia": "gerente de tecnologia",
        "gerentes de ti": "gerente de ti", 
        "administradores de sistemas": "administrador de sistemas",
        "administradores de redes": "administrador de redes",
        "líderes de qa": "líder de qa",
        "project managers": "project manager",
        "gerentes técnicos": "gerente técnico",
        "directores técnicos": "director técnico",
        "líderes técnicos": "líder técnico",
        "analistas técnicos": "analista técnico",
        "gerentes de soporte": "gerente de soporte",
        "responsables de soporte al cliente": "responsable de soporte al cliente",
        
        # Marketing
        "gerentes de marketing": "gerente de marketing",
        "gerentes de marca": "gerente de marca",
        "gerentes de contenido": "gerente de contenido",
        "equipos de marketing": "equipo de marketing",
        "directores de marketing": "director de marketing",
        
        # Ventas
        "gerentes de ventas": "gerente de ventas",
        "account managers": "account manager",
        "account executives": "account executive",
        "directores de ventas": "director de ventas",
        
        # Finanzas
        "gerentes de finanzas": "gerente de finanzas",
        "directores financieros": "director financiero",
        "responsables de control de gestión": "responsable de control de gestión",
        "responsables contables": "responsable contable",
        "responsables de tesorería": "responsable de tesorería",
        "responsables fiscales": "responsable fiscal",
        "responsables de cuentas por cobrar": "responsable de cuentas por cobrar",
        "responsables de cuentas por pagar": "responsable de cuentas por pagar",
        "responsables de FP&A": "responsable de FP&A",
        "responsables de proyectos": "responsable de proyectos",
        "responsables de operaciones": "responsable de operaciones",
        
        # RR.HH.
        "gerentes de recursos humanos": "gerente de recursos humanos",
        "gerentes de rrhh": "gerente de rrhh",
        "directores de rrhh": "director de rrhh",
        "reclutadores": "reclutador",
        "business partners de rr. hh.": "business partner de rr. hh.",
        "responsables de nómina": "responsable de nómina",
        "responsables de compensaciones y beneficios": "responsable de compensaciones y beneficios",
        "responsables de capacitación": "responsable de capacitación",
        
        # Legal
        "gerentes legales": "gerente legal",
        
        # Operaciones  
        "gerentes de operaciones": "gerente de operaciones",
        "responsables de supply chain": "responsable de logística",
        
        # Producto
        "gerentes de producto": "gerente de producto",
        "product managers": "product manager",
        
        # Proyectos
        "gerentes de proyectos": "gerente de proyectos",
        "directores de proyectos": "director de proyectos", 
        "directores de PMO": "director de PMO",
        
        # Ejecutivos
        "CEOs": "CEO",
        "COOs": "COO",
        "vice presidents": "vicepresidente",
        "vicepresidentes": "vicepresidente",
        "presidents": "presidente",
        "presidentes": "presidente",
        "head of departments": "jefe de departamento",
        "head of departments": "jefe de departamento",
        "heads of department": "jefe de departamento",
        "PMO directors": "director de PMO",
        
        # Legal
        "general counsels": "general counsel",
        "asesores legales": "asesor legal",
        "responsables de contratos": "responsable de contratos",
        "responsables de compliance": "responsable de compliance",
        "responsables de privacidad": "responsable de privacidad",
        
        # Operaciones
        "responsables de logística": "responsable de logística",
        "responsables de supply chain": "responsable de logística",
        "responsables de fulfillment": "responsable de fulfillment",
        "responsables de servicio al cliente": "responsable de servicio al cliente",
        "responsables de seguridad e higiene": "responsable de seguridad e higiene",
        "directores industriales": "director industrial",
        "directores de operaciones": "director de operaciones",
        "gerentes de operaciones": "gerente de operaciones",
        "supervisores de operaciones": "supervisor de operaciones",
        "directores de producción": "director de producción",
        
        # Producto
        "product managers": "product manager",
        "product owners": "product owner",
        "directores de producto": "director de producto",
        "responsables de diseño de producto": "responsable de diseño de producto",
        "investigadores de usuario": "investigador de usuario",
        
        # Proyectos
        "directores de proyectos": "director de proyectos",
        "coordinadores de proyectos": "coordinador de proyectos",
        "líderes de proyectos": "líder de proyectos",
        "responsables de PMO": "responsable de PMO",
        "scrum masters": "scrum master",
        "seniors de PMO": "senior de PMO",
    }
    
    # Buscar coincidencia exacta primero
    if role_generic in singular_map:
        return singular_map[role_generic]
    
    # Reglas genéricas para casos no cubiertos
    # Convertir "X de Y" plural a singular
    if " de " in role_generic:
        parts = role_generic.split(" de ", 1)
        if len(parts) == 2:
            first_part = parts[0]
            second_part = parts[1]
            
            # Singularizar la primera parte
            if first_part.endswith("es") and len(first_part) > 3:
                first_part = first_part[:-2]  # "gerentes" -> "gerente"
            elif first_part.endswith("s") and len(first_part) > 2:
                first_part = first_part[:-1]  # "directores" -> "director"
            
            return f"{first_part} de {second_part}"
    
    # Reglas simples para palabras sueltas
    if role_generic.endswith("es") and len(role_generic) > 3:
        return role_generic[:-2]  # "gerentes" -> "gerente"
    elif role_generic.endswith("s") and len(role_generic) > 2 and not role_generic.endswith("us"):
        return role_generic[:-1]  # "directores" -> "director"
    
    # Si no se puede singularizar, devolver tal como está
    return role_generic

# Compiled regex cache for performance
_compiled_regex_cache: Dict[str, re.Pattern] = {}

# Result cache for frequently requested roles
_result_cache: Dict[str, Dict[str, Any]] = {}
_cache_max_size = 1000

def get_compiled_regex(pattern: str) -> re.Pattern:
    """Get compiled regex with caching for performance"""
    if pattern not in _compiled_regex_cache:
        _compiled_regex_cache[pattern] = re.compile(pattern, re.IGNORECASE)
    return _compiled_regex_cache[pattern]

def get_cached_result(role: str) -> Optional[Dict[str, Any]]:
    """Get cached classification result"""
    return _result_cache.get(role.lower().strip())

def cache_result(role: str, result: Dict[str, Any]) -> None:
    """Cache classification result with size limit"""
    key = role.lower().strip()
    if len(_result_cache) >= _cache_max_size:
        # Remove oldest entry (simple FIFO)
        oldest_key = next(iter(_result_cache))
        del _result_cache[oldest_key]
    _result_cache[key] = result

def any_match(text: str, patterns: List[str]) -> bool:
    """Optimized pattern matching with compiled regex"""
    if not patterns:
        return False
    for pattern in patterns:
        if get_compiled_regex(pattern).search(text):
            return True
    return False


# Fast early-exit patterns for most common roles (performance optimization)
FAST_PATTERNS = {
    # C-Suite (highest priority) - exact matches
    r"\bceo\b": ("CEOs", "Ejecutivo"),
    r"\bcto\b": ("CTOs", "Tecnologia"), 
    r"\bcfo\b": ("CFOs", "Ejecutivo"),
    r"\bcmo\b": ("CMOs", "Marketing"),
    r"\bcoo\b": ("COOs", "Ejecutivo"),
    r"\bcio\b": ("CIOs", "Tecnologia"),
    r"\bchro\b": ("CHROs", "RR.HH."),
    r"\bcso\b": ("CSOs", "Ventas"),
    r"\bcro\b": ("CROs", "Ventas"),
    
    # Ultra-common manager patterns
    r"^marketing\s+manager$": ("gerentes de marketing", "Marketing"),
    r"^sales\s+manager$": ("gerentes de ventas", "Ventas"),
    r"^hr\s+manager$": ("gerentes de recursos humanos", "RR.HH."),
    r"^it\s+manager$": ("gerentes de tecnologia", "Tecnologia"),
    r"^product\s+manager$": ("product managers", "Producto"),
    r"^project\s+manager$": ("project managers", "Tecnologia"),
    r"^account\s+manager$": ("account managers", "Ventas"),
    r"^brand\s+manager$": ("gerentes de marca", "Marketing"),
    r"^operations\s+manager$": ("gerentes de operaciones", "Operaciones"),
    
    # Spanish patterns
    r"^gerentes?\s+de\s+marketing$": ("gerentes de marketing", "Marketing"),
    r"^gerentes?\s+de\s+ventas$": ("gerentes de ventas", "Ventas"),
    r"^gerentes?\s+de\s+recursos\s+humanos$": ("gerentes de recursos humanos", "RR.HH."),
    r"^gerentes?\s+de\s+tecnolog[íi]a$": ("gerentes de tecnologia", "Tecnologia"),
    r"^gerentes?\s+de\s+producto$": ("gerentes de producto", "Producto"),
    r"^gerentes?\s+de\s+proyectos$": ("gerentes de proyectos", "Proyectos"),
    r"^directores?\s+de\s+marketing$": ("directores de marketing", "Marketing"),
    r"^directores?\s+de\s+ventas$": ("directores de ventas", "Ventas"),
    r"^directores?\s+de\s+finanzas$": ("directores de finanzas", "Finanzas"),
    
    # Technical roles (very common)
    r"^software\s+engineer$": ("encargados de tecnologia", "Tecnologia"),
    r"^data\s+scientist$": ("encargados de tecnologia", "Tecnologia"),
    r"^system\s+administrator$": ("administradores de sistemas", "Tecnologia"),
    
    # New optimized roles
    r"^chief\s+marketing$": ("CMOs", "Marketing"),
    r"^marketing\s+team$": ("equipos de marketing", "Marketing"),
    
    # Common director patterns
    r"^marketing\s+director$": ("directores de marketing", "Marketing"),
    r"^sales\s+director$": ("directores de ventas", "Ventas"),
    r"^technology\s+director$": ("directores de tecnologia", "Tecnologia"),
}

def fast_classify(text: str) -> Optional[Tuple[str, str]]:
    """Ultra-fast classification for common patterns"""
    text_lower = text.lower()
    for pattern, (role, dept) in FAST_PATTERNS.items():
        if get_compiled_regex(pattern).search(text_lower):
            return (role, dept)
    return None
OWNERS = [
    r"\bfounder(s)?\b", r"\bco[- ]?founder(s)?\b",
    r"\bfundador(a)?s?\b", r"\bco[- ]?fundador(a)?s?\b",
    r"\bowner(s)?\b", r"\bpropietari[oa]s?\b",
    r"\bdue[nñ][oa]s?\b",
    r"\bsoci[oa]s?\b", r"\bpartner(s)?\b",
    r"\bchair(man|woman)?\b"
]

GENERAL_MANAGEMENT = [
    r"\bdirector\s+general\b", r"\bgeneral\s+manager\b",
    r"\bgerente\s+general\b", r"\bmanaging\s+director\b"
]

# ---------------- Hierarchy Levels ----------------
HIERARCHY_LEVELS = {
    "C-Suite": [
        r"\bceo\b", r"\bcfo\b", r"\bcto\b", r"\bcmo\b", r"\bcio\b", r"\bcoo\b", 
        r"\bchro\b", r"\bcdo\b", r"\bciso\b", r"\bcco\b", r"\bcso\b", r"\bcro\b", 
        r"\bcao\b", r"\bcqa\b", r"\bchief\b"
    ],
    "VP/Director": [
        r"\bvp\b", r"\bvice\s*president\b", r"\bdirect(or|ora)\b", r"\bhead\s+of\b",
        r"\bdeputy\b", r"\bsubdirect(or|ora)\b"
    ],
    "Manager": [
        r"\bmanager\b", r"\bgerente\b"
    ],
    "Lead": [
        r"\bjef[ea]\b", r"\blead\b", r"\bleader\b", r"\bprincipal\b",
        r"\bcoordinador(a)?\b", r"\bcoordinator\b", r"\bresponsable\b"
    ],
    "Specialist": [
        r"\bspecialist\b", r"\bespecialista\b", r"\bengineer\b", r"\bingeniero\b",
        r"\banalyst\b", r"\banalista\b", r"\bexecutive\b", r"\bejecutiv[oa]\b"
    ]
}

# ---------------- Subdivisiones por Departamento ----------------
TECH_SUBDIVISIONS = {
    "Datos": [r"\bdata\b", r"\banalytics\b", r"\bbi\b", r"\bbusiness intelligence\b"],
    "Ingeniería": [r"\bengineer\b", r"\bingeniería\b", r"\bdevelop\b", r"\bsoftware\b"],
    "Técnico": [r"\btechnical\b", r"\btécnico\b", r"\btech\b"],
    "Producto": [r"\bproduct\b", r"\bproducto\b", r"\bpm\b"],
    "Infraestructura": [r"\binfrastructure\b", r"\bcloud\b", r"\bdevops\b", r"\bsystem\b"],
    "General": []  # fallback
}

MARKETING_SUBDIVISIONS = {
    "Digital": [r"\bdigital\b", r"\bonline\b", r"\bppc\b", r"\bsem\b", r"\bseo\b"],
    "Tradicional": [r"\btraditional\b", r"\bprint\b", r"\btv\b", r"\bradio\b"],
    "Contenido": [r"\bcontent\b", r"\bcontenido\b", r"\bbrand\b", r"\bcopy\b"],
    "Crecimiento": [r"\bgrowth\b", r"\bcrecimiento\b", r"\bacquisition\b"],
    "Rendimiento": [r"\bperformance\b", r"\bmetrics\b", r"\banalytics\b"],
    "Social": [r"\bsocial\b", r"\bcommunity\b", r"\binfluencer\b"],
    "General": []  # fallback
}

SALES_SUBDIVISIONS = {
    "Ventas Internas": [r"\binside\b", r"\binbound\b", r"\binternal\b"],
    "Ventas de Campo": [r"\bfield\b", r"\boutside\b", r"\bexternal\b"],
    "Canal": [r"\bchannel\b", r"\bpartner\b", r"\bindirect\b"],
    "Cuentas Clave": [r"\bkey account\b", r"\benterprise\b", r"\bstrategic\b"],
    "General": []  # fallback
}

FINANCE_SUBDIVISIONS = {
    "Contabilidad": [r"\baccounting\b", r"\bcontabilidad\b", r"\baccountant\b"],
    "Tesorería": [r"\btreasury\b", r"\btesorería\b", r"\bcash\b"],
    "Control": [r"\bcontrol\b", r"\bcontroller\b", r"\baudit\b"],
    "FP&A": [r"\bfp&a\b", r"\bplanning\b", r"\banalysis\b", r"\bbudget\b"],
    "Crédito": [r"\bcredit\b", r"\brisk\b", r"\bcollections\b"],
    "General": []  # fallback
}

OPERATIONS_SUBDIVISIONS = {
    "Logística": [r"\blogistics\b", r"\bwarehouse\b", r"\bshipping\b"],
    "Cadena de Suministro": [r"\bsupply chain\b", r"\bprocurement\b", r"\bsourcing\b"],
    "Calidad": [r"\bquality\b", r"\bqi\b", r"\bqc\b"],
    "Servicio al Cliente": [r"\bcustomer service\b", r"\bsupport\b", r"\bservice\b"],
    "General": []  # fallback
}

HR_SUBDIVISIONS = {
    "Talento": [r"\btalent\b", r"\brecruit\b", r"\bacquisition\b"],
    "Compensación": [r"\bcompensation\b", r"\bbenefits\b", r"\bpayroll\b"],
    "Aprendizaje": [r"\blearning\b", r"\btraining\b", r"\bl&d\b"],
    "Business Partner": [r"\bbusiness\s+partner\b", r"\bhrbp\b"],
    "General": []  # fallback
}

PRODUCT_SUBDIVISIONS = {
    "Gestión": [r"\bmanagement\b", r"\bmanager\b", r"\bowner\b"],
    "Diseño": [r"\bdesign\b", r"\bux\b", r"\bui\b", r"\buser\s+experience\b"],
    "Estrategia": [r"\bstrategy\b", r"\bstrateg\b", r"\bportfolio\b"],
    "Investigación": [r"\bresearch\b", r"\banalyst\b", r"\binsights\b"],
    "General": []  # fallback
}

PROJECTS_SUBDIVISIONS = {
    "Gestión": [r"\bmanagement\b", r"\bmanager\b", r"\bpm\b"],
    "Planificación": [r"\bplanning\b", r"\bschedule\b", r"\bcronograma\b"],
    "Coordinación": [r"\bcoordination\b", r"\bcoordinator\b"],
    "Implementación": [r"\bimplementation\b", r"\bdeployment\b", r"\bexecution\b"],
    "Metodologías": [r"\bagile\b", r"\bscrum\b", r"\bwaterfall\b", r"\bpmi\b"],
    "General": []  # fallback
}

# (patrones, label, departamento destino)
C_SUITE_MAP: List[Tuple[List[str], str, str]] = [
    (["\\bcmo\\b","chief marketing officer","chief marketing"],       "CMOs",          "Marketing"),
    (["\\bcio\\b","chief information officer","chief information technology officer"], "CIOs",          "Tecnologia"),
    (["\\bcto\\b","chief technical officer","chief technology officer","chief transformation & technology officer","ctto","chief of technology","chief product and technology officer","technical chief"], "CTOs",          "Tecnologia"),
    (["\\bciso\\b","chief information security officer"],             "CISOs",         "Tecnologia"),
    (["\\bcco\\b","chief commercial officer"],                        "CCOs",          "Ventas"),
    (["\\bcso\\b","chief sales officer"],                             "CSOs (Sales)",  "Ventas"),
    (["\\bcro\\b","chief revenue officer"],                           "CROs",          "Ventas"),
    (["\\bceo\\b","chief executive officer"],                         "CEOs",          "Ejecutivo"),
    (["\\bcfo\\b","chief financial officer"],                         "CFOs",          "Ejecutivo"),
    (["\\bcdo\\b","chief data officer","chief digital officer"],      "CDOs",          "Ejecutivo"),
    (["\\bchro\\b","chief human resources officer"],                  "CHROs",         "RR. HH."),
    (["\\bcoo\\b","chief (of )?operations|chief operating( officer)?|operations officer"], "COOs","Ejecutivo"),
    (["\\bcao\\b","chief administrat(ive|ion) officer"],              "CAOs",          "Ejecutivo"),
    (["\\bcqa\\b","cqa"],                                             "CQAs",          "Tecnologia"),
]


# ---------------- Seniority / Excludes comunes (sin C-levels) ----------------
# Mantenemos esto para gatear ICP (must + seniority) y para fallback si no hay área
SENIORITY_COMMON = [
    r"\bvp\b|\bvice ?president(e)?\b",
    r"\bhead\b|\bdirect(or|ora)\b|\bdireccion\b|\bdirecci[oó]n\b",
    r"\bmanager\b|\bgerente\b|\bjef[ea]\b|\bresponsable\b|\blead\b|\bprincipal\b|\bleader\b",
    r"\bcoordinador(a)?\b|\bcoordinator\b",
    r"\bstrategist\b|\bestratega\b",
    r"\bejecutiv[oa]s?\b|\bexecutive\b",
    r"\bgestor(es)?\b",
    r"\badministrador(a)?\b|\badministrator\b",
    r"\bcontroller\b|\bcontrolador\b",
    r"\baccountant\b|\bcontador(a)?\b|\bcontable(s)?\b",
    r"\bdepartment\b|\bdepartamento\b|\bdpto\b",
    r"\bteam\b|\bequipo\b",  # Agregado para Marketing Team y similares
    # Agregamos roles técnicos y de análisis
    r"\bengineer\b|\bingeniero\b",
    r"\banalyst\b|\banalista\b",
    r"\bscientist\b|\bcient[íi]fico\b",
    r"\bspecialist\b|\bespecialista\b",
    r"\brepresentative\b|\brepresentante\b",
    r"\bconsultant\b|\bconsultor(a)?\b",
    r"\bplanner\b|\bplanificador(a)?\b",  # Agregado para Financial Planner
    r"\brecruiter\b|\breclutador(a)?\b",  # Agregado para Recruiter
]

EXCLUDE_COMMON = [
    r"\bjunior\b|\bjr\b", r"\btrainee\b|\bbecari[oa]\b|\bintern\b",
    r"\bassistant\b|\basistente\b",
    r"\bcommunity\b|\bartist\b|\bart\b",
    r"\bdesign\b|\bdise[nñ]o\b|\badvisor\b",
    # Removido: analytics, analista, data - ahora son roles válidos
    r"\bpaid\b|\bcustomer\b",
]

# -------- Router de Proyectos (PM) --------
PM_PATTERN = r"(?:\bproject (manager|lead|director)\b|\bjefe de proyecto(s)?\b|\bgestor de proyecto(s)?\b|\bpm\b|\bdirect(or|ora) de proyecto(s)?\b)"

# ---- Títulos "sueltos" (sin área/dep) que deben contar como C-Suite
SOLO_TITLES = [
    (r"^\s*vp\s*$|^\s*vice ?president(e)?\s*$", "vicepresidentes"),
    (r"^\s*president(e)?\s*$", "presidentes"),
    (r"^\s*director(a)?\s*$",                  "directores"),
    (r"^\s*gerente\s*$",                       "gerentes"),
    (r"^\s*manager\s*$",                       "managers"),
    (r"^\s*ejecutiv[oa]s?\s*$",               "ejecutivos"),
    (r"^\s*administraci[óo]n\s*$",            "responsables de administración"),
    (r"^\s*administrativ[oa]s?\s*$",          "administrativos"),
    (r"^\s*head of department\s*$",           "jefes de departamento"),
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
    r"\bindustrial\b|\bmanufactur\b|\bfabric\b|\bconstrucci[oó]n\b|\bconstruction\b",
    r"\bproducci[oó]n\b|\bproduction\b|\bplanta\b|\bplant\b",
    r"\bcalidad\b|\bquality\b|\bmantenimiento\b|\bmaintenance\b",
]

# ---------------- Seniorities genéricos (forman “{seniority} de {área}”) ----------------
GEN_SENIORITIES: List[Tuple[str, str]] = [
    (r"(?:\bhead\b|\bdirect(or|ora)\b)", "directores"),
    (r"(?:\bvp\b|\bvice ?president(e)?)", "vicepresidentes"),
    (r"(?:\bmanager\b|\bgerente\b)",                            "gerentes"),
    (r"(?:\bjef[ea]\b|\bprincipal\b|\blead\b|\bleader\b)", "jefes"),
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
        if get_compiled_regex(pat).search(text):
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
    "tecnología":       r"(?:tecnolog[íi]a|technology|tech|technical|tecnico)",
    "devops":           r"(?:\bdevops\b)",
    "qa":               r"(?:\bqa\b|quality assurance|tester|testing|aseguramiento de calidad|control de calidad|quality control)",
    "proyectos":        r"(?:project|proyectos|jefe de proyecto|gestor de proyecto|\bpm\b)",
    "arquitectura":     r"(?:arquitectur[ao]|\barchitecture\b|architect)",
    "seguridad":        r"(?:security|seguridad|infosec|ciberseguridad|cyber ?security)",
    "plataforma":       r"(?:platform|plataforma)",
    "nube":             r"(?:cloud|nube|aws|azure|gcp|google cloud)",
    "datos":            r"(?:data|datos|bi|business intelligence|analitica)",
    "soporte":          r"(?:support|soporte|help ?desk|service ?desk|technical ?support)",
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

PRODUCT_AREAS = {
    "gestión de producto": r"(?:product management|gestión de producto|product owner|po\b)",
    "desarrollo":         r"(?:product development|desarrollo de producto)",
    "estrategia":         r"(?:product strategy|estrategia de producto)",
    "portfolio":          r"(?:portfolio|portafolio)",
    "design":             r"(?:product design|diseño de producto|ux|ui|user experience|user interface)",
    "research":           r"(?:user research|investigación|market research)",
}

PROJECTS_AREAS = {
    "gestión":            r"(?:project management|gestión de proyectos|project manager|pm\b)",
    "planificación":      r"(?:planning|planificación|schedule|cronograma)",
    "coordinación":       r"(?:coordination|coordinación|coordinator)",
    "seguimiento":        r"(?:tracking|seguimiento|monitoring|control)",
    "implementación":     r"(?:implementation|implementación|deployment|despliegue)",
    "metodologías":       r"(?:agile|scrum|waterfall|metodologías|pmi|prince2)",
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
    # Reglas especiales para roles técnicos
    (r"(?:technical\s+(?:support|service|manager)|tech\s+(?:support|service|manager))", "gerentes técnicos"),
    (r"(?:technical\s+director|tech\s+director)", "directores técnicos"),
    (r"(?:technical\s+lead|tech\s+lead)", "líderes técnicos"),
    (r"(?:technical\s+analyst|tech\s+analyst)", "analistas técnicos"),
    (r"(?:support\s+manager)", "gerentes de soporte"),
    (r"(?:customer\s+support|help\s+desk)", "responsables de soporte al cliente"),
]

# Marketing: atajos comunes
SPECIAL_MKT: List[Tuple[str, str]] = [
    (r"\bbrand(ing)?\b.*\bmanager\b|\bbrand manager\b",   "gerentes de marca"),
    (r"\bcontent\b.*\bmanager\b|\bcontent manager\b",     "gerentes de contenido"),
    (r"\bmarketing team\b",                               "equipos de marketing"),
]

# Ventas: atajos comunes
SPECIAL_SALES: List[Tuple[str, str]] = [
    (r"\baccount manager\b",   "account managers"),
    (r"\baccount executive\b", "account executives"),
]

# Finanzas: roles “bonitos”
SPECIAL_FIN: List[Tuple[str, str]] = [
    (r"(?:director\s+financiero|financial\s+director)", "directores financieros"),
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
    (r"(?:director\s+de\s+rr\.?\s*hh\.?|director\s+de\s+recursos\s+humanos)", "directores de rrhh"),
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
    (r"(?:director\s+industrial|industrial\s+director)", "directores industriales"),
]

# Producto
SPECIAL_PRODUCT: List[Tuple[str, str]] = [
    (r"(?:product manager|pm\b|gestor de producto)",                "product managers"),
    (r"(?:product owner|po\b|propietario de producto)",             "product owners"),
    (r"(?:product director|director de producto)",                  "directores de producto"),
    (r"(?:ux|ui|user experience|user interface|diseño de producto)", "responsables de diseño de producto"),
    (r"(?:user research|investigación de usuario)",                 "investigadores de usuario"),
]

# Proyectos
SPECIAL_PROJECTS: List[Tuple[str, str]] = [
    (r"(?:project manager|pm\b|gestor de proyectos|jefe de proyecto)", "project managers"),
    (r"(?:project director|director de proyectos)",                    "directores de proyectos"),
    (r"(?:pmo\s+director|director\s+pmo|director de pmo)",             "directores de PMO"),
    (r"(?:project coordinator|coordinador de proyectos)",              "coordinadores de proyectos"),
    (r"(?:project lead|líder de proyecto)",                            "líderes de proyectos"),
    (r"(?:pmo|project management office|oficina de proyectos)",        "responsables de PMO"),
    (r"(?:scrum master|agile coach)",                                   "scrum masters"),
    (r"(?:pmo\s+senior|senior\s+pmo)",                                 "seniors de PMO"),
]


# ---------------- Motor: “especiales” -> “{seniority} de {área}” ----------------
def detect_first(text: str, pairs: List[Tuple[str, str]]) -> Optional[str]:
    for pat, label in pairs:
        if get_compiled_regex(pat).search(text):
            return label
    return None

def detect_area(text: str, areas: Dict[str, str]) -> Optional[str]:
    for area, pat in areas.items():
        if get_compiled_regex(pat).search(text):
            return area
    return None

def detect_hierarchy_level(text: str) -> str:
    """Detecta el nivel de jerarquía del título"""
    text_norm = norm(text)
    
    for level, patterns in HIERARCHY_LEVELS.items():
        if any(get_compiled_regex(pat).search(text_norm) for pat in patterns):
            return level
    
    return "Specialist"  # fallback

def detect_subdivision(text: str, department: str) -> str:
    """Detecta la subdivisión según el departamento"""
    text_norm = norm(text)
    
    subdivision_map = {
        "Tecnologia": TECH_SUBDIVISIONS,
        "Marketing": MARKETING_SUBDIVISIONS,
        "Ventas": SALES_SUBDIVISIONS,
        "Finanzas": FINANCE_SUBDIVISIONS,
        "Operaciones": OPERATIONS_SUBDIVISIONS,
        "RR. HH.": HR_SUBDIVISIONS,
        "Producto": PRODUCT_SUBDIVISIONS,
        "Proyectos": PROJECTS_SUBDIVISIONS,
    }
    
    if department not in subdivision_map:
        return "General"
    
    subdivisions = subdivision_map[department]
    
    for subdivision, patterns in subdivisions.items():
        if subdivision == "General":
            continue
        if any(get_compiled_regex(pat).search(text_norm) for pat in patterns):
            return subdivision
    
    return "General"  # fallback

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
        "must": [
            r"\bmarketing\b", r"\bbrand\b", r"\bmarket\b",
            r"\bcontent\b|\bcontenido\b",  # Agregado para Content Manager
            r"\bgrowth\b|\bcrecimiento\b",  # Agregado para Growth Manager
            r"\bcampaign\b|\bcampaña\b",  # Agregado para Campaign Manager
            r"\bsocial\b|\bmedia\b",  # Agregado para Social Media Manager
        ],
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
            r"\btechnical\b|\btecnico\b", r"\bengineering\b|\bingenier[íi]a\b|\bengineer\b",
            r"\bproject\b|\bproyecto\b", r"\bqa\b|\bquality\b",
            r"\bde tecnolog[íi]a\b", r"\borganizaci[oó]n\b", r"\bde la informaci[oó]n\b",
            r"\bde proyectos\b",
            r"\bdata\b|\banalytics\b|\bscience\b",  # Agregado para Data Scientist
            r"\bdatabase\b|\bdb\b",  # Agregado para Database Administrator
            r"\bsystem\b|\bnetwork\b",  # Agregado para System/Network Administrator
            r"\bsupport\b|\bsoporte\b",  # Agregado para Support roles
            r"\bhelp ?desk\b|\bservice ?desk\b",  # Agregado para Help Desk roles
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
            r"\bfinance\b|\bfinancial\b|\bfinanzas?\b|\bfinanciera\b|\bfinanciero\b",
            r"\baccounting\b|\bcontabilidad\b|\baccount\b",
            r"\bcontador(a)?\b|\bcontable(s)?\b|\binvestment\b",
            r"\baccountant\b",  # Agregado específicamente para Accountant
            r"\bcontroller\b|\bcontrolador\b",  # Agregado para Controller
            r"\bplanner\b|\bplanning\b",  # Agregado para Financial Planner
            r"\btreasury\b|\btesorería\b",  # Agregado para Treasury Manager
            r"\bcredit\b|\bcrédito\b",  # Agregado para Credit Analyst
        ],
        "seniority": SENIORITY_COMMON + [r"\bfiscal\b", r"\bcontroller\b|\bcontrolador\b",
                                         r"\badministraci[oó]n\b|\badministrador(a)?\b|\badministrativ[oa]s?\b"],
        "exclude": EXCLUDE_COMMON + [r"\bkey\b"],
        "areas": FIN_AREAS, "specials": SPECIAL_FIN,
    }),
    ("RR. HH.", {
        "must": [
            r"(?:recursos humanos|human resources|\bhr\b|\bpeople\b|talent|\brrhh\b|\brr\.?\s*hh\.?)",
            r"\brecruit(er|ing)?\b|\breclutamiento\b",  # Agregado para Recruiter
            r"\bcompensation\b|\bcompensaciones\b",  # Agregado para Compensation Manager
            r"\btraining\b|\bcapacitaci[oó]n\b",  # Agregado para Training Manager
            r"\bpayroll\b|\bn[oó]mina\b",  # Agregado para Payroll Manager
        ],
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
        "must": [r"(?:operaciones|operations|ops|log[íi]stica|logistics|supply ?chain|fulfillment|warehouse|almac[eé]n|industrial)"],
        "seniority": SENIORITY_COMMON,
        "exclude": EXCLUDE_COMMON,
        "areas": OPS_AREAS, "specials": SPECIAL_OPS,
    }),
    ("Producto", {
        "must": [r"(?:product|producto|product management|gestión de producto)"],
        "seniority": SENIORITY_COMMON,
        "exclude": EXCLUDE_COMMON,
        "areas": PRODUCT_AREAS, "specials": SPECIAL_PRODUCT,
    }),
    ("Proyectos", {
        "must": [r"(?:project|proyecto|project management|gestión de proyectos|pm\b|pmo|scrum|agile)"],
        "seniority": SENIORITY_COMMON,
        "exclude": EXCLUDE_COMMON,
        "areas": PROJECTS_AREAS, "specials": SPECIAL_PROJECTS,
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
    subdivision: str
    hierarchy_level: str
    role_generic: str
    role_generic_singular: str
    why: Dict[str, Any]


# ---------------- Core ----------------
def create_result(original: str, is_icp: bool, department: str = "", subdivision: str = "", 
                 hierarchy_level: str = "", role_generic: str = "", why: Dict[str, Any] = None) -> Dict[str, Any]:
    """Helper function to create consistent results with role_generic_singular"""
    if why is None:
        why = {}
    
    role_generic_singular = singularize_role(role_generic) if role_generic else ""
    
    return {
        "input": original,
        "is_icp": is_icp,
        "department": department,
        "subdivision": subdivision,
        "hierarchy_level": hierarchy_level,
        "role_generic": role_generic,
        "role_generic_singular": role_generic_singular,
        "why": why
    }

def dynamic_role_label(dep: str, text: str) -> str:
    # Último fallback: usa seniority si lo encuentra; si no, “encargados de …”
    sen = seniority_label(text)
    if sen:
        return f"{sen} de {dep.lower()}"
    return f"encargados de {dep.lower()}"

def classify_one(job_title: str, external_excludes: List[str]) -> Dict[str, Any]:
    # Check cache first (only for common case with no external excludes)
    if not external_excludes:
        cached = get_cached_result(job_title)
        if cached:
            return cached

    # Perform classification
    result = _classify_one_internal(job_title, external_excludes)
    
    # Cache result if no external excludes (most common case)
    if not external_excludes:
        cache_result(job_title, result)
    
    return result

def _classify_one_internal(job_title: str, external_excludes: List[str]) -> Dict[str, Any]:

    original = job_title
    t = norm(job_title)

    # OPTIMIZATION: Fast path for very common roles (early exit)
    if not external_excludes:  # Only for simple cases
        fast_result = fast_classify(job_title)
        if fast_result:
            role_generic, department = fast_result
            hierarchy_level = detect_hierarchy_level(original)
            subdivision = detect_subdivision(original, department)
            return create_result(original, True, department, subdivision, hierarchy_level, role_generic, {"matched": "fast_path"})

    # Excludes externos
    if any_match(t, external_excludes):
        return create_result(original, False, why={"excluded_by": "external_excludes"})

    # Owners (pero damos prioridad a C-Suite específicos)
    if any_match(t, OWNERS):
        # Si tiene términos específicos de C-Suite, damos prioridad a esos
        for pats, label, dep_fn in C_SUITE_MAP:
            if any(get_compiled_regex(p).search(t) for p in pats):
                hierarchy_level = detect_hierarchy_level(original)
                subdivision = detect_subdivision(original, dep_fn)
                return create_result(original, True, dep_fn, subdivision, hierarchy_level, label, {"matched": f"{label}_over_owner"})
        
        # Si no hay C-Suite específico, entonces es propietario
        hierarchy_level = detect_hierarchy_level(original)
        subdivision = detect_subdivision(original, "Ejecutivo")
        return create_result(original, True, "Ejecutivo", subdivision, hierarchy_level, "propietarios", {"matched": "owners"})

    # General Management
    if any_match(t, GENERAL_MANAGEMENT):
        hierarchy_level = detect_hierarchy_level(original)
        subdivision = detect_subdivision(original, "Ejecutivo")
        return create_result(original, True, "Ejecutivo", subdivision, hierarchy_level, "directores", {"matched": "general_management"})

    # C-Suite
    for pats, label, dep_fn in C_SUITE_MAP:
        if any(get_compiled_regex(p).search(t) for p in pats):
            hierarchy_level = detect_hierarchy_level(original)
            subdivision = detect_subdivision(original, dep_fn)
            return create_result(original, True, dep_fn, subdivision, hierarchy_level, label, {"matched": label})
            
    # --- Area Director / Area Manager -> Ejecutivo (más genéricos)
    area_roles_pattern = r"\barea\s+(director|manager|gerente)\b"
    if get_compiled_regex(area_roles_pattern).search(t):
        role_label = "directores" if "director" in t.lower() else "gerentes"
        hierarchy_level = detect_hierarchy_level(original)
        subdivision = detect_subdivision(original, "Ejecutivo")
        return create_result(original, True, "Ejecutivo", subdivision, hierarchy_level, role_label, {"matched": "area_roles"})

    # --- Nuevos roles específicos de Ejecutivo
    ejecutivo_patterns = [
        (r"\bassociate\s+director\b", "directores asociados"),
        (r"\bdirector\s+of\s+administration\b", "directores de administración"),
        (r"\bdirector\s+regional\b", "directores regionales"),
        (r"\bregional\s+director\b", "directores regionales"),
    ]
    
    for pattern, label in ejecutivo_patterns:
        if get_compiled_regex(pattern).search(t):
            hierarchy_level = detect_hierarchy_level(original)
            subdivision = detect_subdivision(original, "Ejecutivo")
            return create_result(original, True, "Ejecutivo", subdivision, hierarchy_level, label, {"matched": "nuevos_ejecutivo_roles"})

    # --- VP / Director / Gerente / Manager "sueltos" -> Ejecutivo genérico
    for pat, plural_label in SOLO_TITLES:
        if get_compiled_regex(pat).search(t):
            hierarchy_level = detect_hierarchy_level(original)
            subdivision = detect_subdivision(original, "Ejecutivo")
            return create_result(original, True, "Ejecutivo", subdivision, hierarchy_level, plural_label, {"matched": "solo_title"})

    # --- Departamento "solo" (Marketing, RRHH, etc.) -> responsables de {dep}
    for pat, (dep_name, role_lbl) in DEPT_STANDALONE:
        if get_compiled_regex(pat).search(t):
            hierarchy_level = detect_hierarchy_level(original)
            subdivision = detect_subdivision(original, dep_name)
            return create_result(original, True, dep_name, subdivision, hierarchy_level, role_lbl, {"matched": "standalone_department"})

    # --- Router específico para Proyectos (PM / Director de Proyectos) ---
    if re.search(PM_PATTERN, t, re.I):
        if any_match(t, TECH_HINTS):
            dep = "Tecnologia"
        elif any_match(t, MKT_HINTS):
            dep = "Marketing"
        elif any_match(t, OPS_HINTS):
            dep = "Operaciones"
        else:
            dep = "Tecnologia"

        sen = seniority_label(t) or "responsables"
        label = f"{sen} de proyectos"
        hierarchy_level = detect_hierarchy_level(original)
        subdivision = detect_subdivision(original, dep)
        return create_result(original, True, dep, subdivision, hierarchy_level, label, {"matched": "pm_router", "department_routed": dep})
                
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
            hierarchy_level = detect_hierarchy_level(original)
            subdivision = detect_subdivision(original, dep)
            if label:
                return create_result(original, True, dep, subdivision, hierarchy_level, label, {"must": True, "seniority": True, "exclude": False, "matched": "area+seniority/special"})
            # Fallback final
            dyn = dynamic_role_label(dep, t)
            return create_result(original, True, dep, subdivision, hierarchy_level, dyn, {"must": True, "seniority": True, "exclude": False, "matched": "fallback"})

    # Sin match
    return create_result(original, False, why={"no_match": True})


# ---------------- API ----------------
# Common roles to pre-warm cache at startup (optimized for Clay usage)
COMMON_ROLES = [
    # C-Suite (most frequent)
    "CEO", "CTO", "CFO", "CMO", "COO", "CIO", "CHRO", "CSO", "CRO",
    
    # Managers (very common in Clay)
    "Marketing Manager", "Sales Manager", "Technical Support Manager",
    "HR Manager", "IT Manager", "Operations Manager", "Financial Manager",
    "Product Manager", "Project Manager", "Account Manager", "Brand Manager",
    
    # Directors & VPs
    "Marketing Director", "Sales Director", "Technology Director", "HR Director",
    "VP Marketing", "VP Sales", "VP Technology", "VP Operations",
    
    # Technical roles
    "Software Engineer", "Data Scientist", "System Administrator", "Engineer",
    
    # New roles
    "Chief Marketing", "Marketing Team",
    
    # Common variations
    "Director of Marketing", "Head of Sales", "Engineering Manager",
    "Business Analyst", "Content Manager"
]

def warm_cache():
    """Pre-warm cache with common roles for faster startup performance"""
    for role in COMMON_ROLES:
        classify_one(role, [])
    print(f"✅ Cache warmed with {len(COMMON_ROLES)} common roles")

# Warm cache on startup
warm_cache()

@app.post("/classify")
def classify(inp: In, response: Response):
    """Ultra-optimized endpoint with all performance enhancements"""
    # Skip excludes processing if empty (most common case) - optimization from classify-fast
    if not inp.excludes or inp.excludes.strip() == "":
        external_excludes = []
    else:
        external_excludes = to_regex(split_csv(inp.excludes))
    
    # Optimized headers
    response.headers["Cache-Control"] = "public, max-age=7200"  # 2 hour cache
    response.headers["X-Cache-Status"] = "HIT" if not external_excludes and get_cached_result(inp.job_title) else "MISS"
    
    # Ultra-fast path for empty inputs (enhanced validation)
    if not inp.job_title or len(inp.job_title.strip()) < 2:
        return ORJSONResponse(create_result(inp.job_title, False, why={"empty_input": True}))
    
    result = classify_one(inp.job_title, external_excludes)
    
    # Add performance metrics
    response.headers["X-Fast-Path"] = "1" if result.get("why", {}).get("matched") == "fast_path" else "0"
    
    return ORJSONResponse(result)

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/cache-stats")
def cache_stats():
    """Get cache performance statistics"""
    return {
        "compiled_regex_cache_size": len(_compiled_regex_cache),
        "result_cache_size": len(_result_cache),
        "result_cache_max_size": _cache_max_size
    }



