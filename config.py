"""Configuration module for EpiAlert.

Centralizes all static reference data and application constants.
Keeping configuration isolated from business logic simplifies updates,
reduces drift between environments, and makes threshold/region changes
auditable.

Geographic boundaries reflect Burkina Faso's 2024 administrative reform.
Disease thresholds align with national MoH guidelines and WHO outbreak
response standards. Institutional partners are verified entities actively
involved in surveillance or response coordination.

Usage:
    from config import REGIONS, DISEASE_THRESHOLDS, Colors, AGENT_ROLES

Maintenance notes:
    - Add new regions/diseases here first; the rest of the codebase
      should never hardcode these values.
    - Thresholds are integers representing weekly case counts per facility.
      Adjust only with epidemiological sign-off.
"""

import os


# ── App identity ──────────────────────────────────────────────────────────────
# SemVer format. Update MINOR for feature additions, PATCH for bug fixes.
APP_NAME: str = "EpiAlert"
APP_VERSION: str = "2.0.0"
APP_TAGLINE: str = (
    "Epidemiological Surveillance System for Burkina Faso"
)
APP_SLOGAN: str = (
    "Detect early. Respond fast. Save lives."
)
APP_DESCRIPTION: str = (
    "A terminal-based tool for tracking disease outbreaks,"
    " detecting epidemics, and generating epidemiological"
    " reports across the 13 regions of Burkina Faso."
)

# National motto of Burkina Faso.
MOTTO_EN: str = "The Homeland or Death, We Shall Overcome"


# ── Institutional partners ────────────────────────────────────────────────────
# Stored as (full_name, official_acronym) to support both UI display and
# export metadata. Order matches reporting hierarchy / data-sharing agreements.
INSTITUTIONS: list[tuple[str, str]] = [
    ("Ministry of Health, Burkina Faso", "MS/BF"),
    ("National Institute of Public Health (INSP)", "INSP"),
    ("Centre for Emergency Health Operations (CORUS)", "CORUS"),
    ("National Observatory of Population Health (ONSP)", "ONSP"),
    ("General Directorate of Health and Public Hygiene (DGSHP)", "DGSHP"),
    ("Health Information and Epidemiological Surveillance Centres (CISSE)", "CISSE"),
    ("General Directorate of Studies and Sectoral Statistics (DGESS)", "DGESS"),
    ("Centre Muraz — Bobo-Dioulasso", "Centre Muraz"),
    ("Health Research Centre of Nouna (CRSN)", "CRSN"),
    ("Centre for Research and Training on Malaria (CNRFP)", "CNRFP"),
    ("Health Sciences Research Institute (IRSS)", "IRSS"),
    ("Burkina Field Epidemiology and Laboratory Training Program (BFETP)", "BFETP"),
    ("Integrated Disease Surveillance and Response (SIMR)", "SIMR"),
    ("World Health Organization (OMS)", "WHO"),
    ("UNICEF Burkina Faso", "UNICEF-BF"),
    ("Red Cross of Burkina Faso (CRB)", "CRB"),
    ("Doctors Without Borders (MSF)", "MSF"),
    ("Africa Centres for Disease Control and Prevention", "Africa CDC"),
]


# ── File paths ────────────────────────────────────────────────────────────────
# Resolve paths relative to this file so the project works consistently
# regardless of the working directory at launch.
_BASE_DIR: str = os.path.dirname(os.path.abspath(__file__))
DATA_DIR: str = os.path.join(_BASE_DIR, "data")
OUTPUTS_DIR: str = os.path.join(_BASE_DIR, "outputs")
CLASSEURS_DIR: str = os.path.join(OUTPUTS_DIR, "classeurs")
PATIENTS_FILE: str = os.path.join(DATA_DIR, "patients.txt")
CASES_FILE: str = os.path.join(DATA_DIR, "cases.txt")
ALERTS_FILE: str = os.path.join(DATA_DIR, "alerts.txt")

# NOTE: The app must ensure DATA_DIR and OUTPUTS_DIR exist on startup.
# This module intentionally does not create directories to keep it stateless.


# ── Patient statuses and icons ────────────────────────────────────────────────
# Canonical status strings used across the data layer. Order matters for
# dropdowns and report sorting.
PATIENT_STATUSES: tuple[str, ...] = (
    "Suspected", "Confirmed", "Recovered", "Deceased",
)

# Single-character glyphs for compact terminal rendering.
STATUS_ICONS: dict[str, str] = {
    "Suspected": "?",
    "Confirmed": "!",
    "Recovered": "+",
    "Deceased": "x",
}

# ANSI foreground colors matching the severity of each status.
STATUS_COLORS: dict[str, str] = {
    "Suspected": "\033[93m",
    "Confirmed": "\033[91m",
    "Recovered": "\033[92m",
    "Deceased": "\033[90m",
}

# Human-readable explanations shown in tooltips and report footers.
STATUS_LABELS: dict[str, str] = {
    "Suspected": "Under investigation",
    "Confirmed": "Laboratory-confirmed",
    "Recovered": "Discharged / healed",
    "Deceased": "Death recorded",
}


# ── Alert severity ────────────────────────────────────────────────────────────
# Ordered from lowest to highest priority. UI components rely on this order
# for sorting and escalation workflows.
SEVERITY_LEVELS: tuple[str, ...] = ("Warning", "Critical", "Emergency")

SEVERITY_COLORS: dict[str, str] = {
    "Warning": "\033[93m",
    "Critical": "\033[91m",
    "Emergency": "\033[95m",
}

SEVERITY_ICONS: dict[str, str] = {
    "Warning": "▲",
    "Critical": "▲▲",
    "Emergency": "▲▲▲",
}

SEVERITY_LABELS: dict[str, str] = {
    "Warning": "Cases exceed threshold by 1-50 %",
    "Critical": "Cases exceed threshold by 51-100 %",
    "Emergency": "Cases exceed threshold by > 100 %",
}


# ── Gender ────────────────────────────────────────────────────────────────────
# Restricted to official MoH reporting categories. Validation routines should
# reject anything outside this tuple.
VALID_GENDERS: tuple[str, ...] = ("M", "F")


# ── Burkina Faso — 13 regions (2024 reform) ──────────────────────────────────
# Hierarchical reference data: Region -> Capital | Region -> Provinces -> Communes
# Designed as read-only lookup tables. Do not mutate at runtime.
REGIONS: dict[str, str] = {
    "Boucle du Mouhoun": "Dedougou",
    "Cascades": "Banfora",
    "Centre": "Ouagadougou",
    "Centre-Est": "Tenkodogo",
    "Centre-Nord": "Kaya",
    "Centre-Ouest": "Koudougou",
    "Centre-Sud": "Manga",
    "Est": "Fada N'Gourma",
    "Hauts-Bassins": "Bobo-Dioulasso",
    "Nord": "Ouahigouya",
    "Plateau-Central": "Zorgho",
    "Sahel": "Dori",
    "Sud-Ouest": "Gaoua",
}

PROVINCES: dict[str, list[str]] = {
    "Boucle du Mouhoun": ["Bale", "Banwa", "Kossi", "Mouhoun", "Nayala", "Sourou"],
    "Cascades": ["Comoe", "Leraba"],
    "Centre": ["Kadiogo"],
    "Centre-Est": ["Boulgou", "Koulpelogo", "Kouritenga"],
    "Centre-Nord": ["Bam", "Namentenga", "Sanmatenga"],
    "Centre-Ouest": ["Boulkiemde", "Sanguie", "Sissili", "Ziro"],
    "Centre-Sud": ["Bazega", "Nahouri", "Zoundweogo"],
    "Est": ["Gnagna", "Gourma", "Komandjari", "Kompienga", "Tapoa"],
    "Hauts-Bassins": ["Houet", "Kenedougou", "Tuy"],
    "Nord": ["Loroum", "Passore", "Yatenga", "Zondoma"],
    "Plateau-Central": ["Ganzourgou", "Kourweogo", "Oubritenga"],
    "Sahel": ["Oudalan", "Seno", "Soum", "Yagha", "Djelgodji"],
    "Sud-Ouest": ["Bougouriba", "Ioba", "Noumbiel", "Poni"],
}

COMMUNES: dict[str, list[str]] = {
    "Bale": ["Boromo", "Bagassi", "Pa"],
    "Banwa": ["Solenzo", "Koubani"],
    "Kossi": ["Nouna", "Djibasso"],
    "Mouhoun": ["Dedougou", "Douroula"],
    "Nayala": ["Toma", "Yaba"],
    "Sourou": ["Tougan", "Kiembara"],
    "Comoe": ["Banfora", "Sindou", "Orodara"],
    "Leraba": ["Sindou", "Dakoro"],
    "Kadiogo": ["Ouagadougou", "Saaba", "Koubri", "Pabre", "Tanghin-Dassouri"],
    "Boulgou": ["Tenkodogo", "Garango", "Bittou"],
    "Koulpelogo": ["Pama", "Soudougui"],
    "Kouritenga": ["Koupela", "Pouytenga"],
    "Bam": ["Kongoussi", "Bourzanga"],
    "Namentenga": ["Boulsa", "Tougouri"],
    "Sanmatenga": ["Kaya", "Barsalogho", "Pissila"],
    "Boulkiemde": ["Koudougou", "Sapone", "Kombissiri"],
    "Sanguie": ["Reo", "Didyr"],
    "Sissili": ["Leo", "Silgouri"],
    "Ziro": ["Sapouy", "Gao"],
    "Bazega": ["Kombissiri", "Doulougou"],
    "Nahouri": ["Po", "Guiaro"],
    "Zoundweogo": ["Manga", "Gogo"],
    "Gnagna": ["Bogande", "Manni"],
    "Gourma": ["Fada N'Gourma", "Diapaga"],
    "Komandjari": ["Gayeri", "Matiacoali"],
    "Kompienga": ["Pama", "Madjoari"],
    "Tapoa": ["Diapaga", "Kantchari"],
    "Houet": ["Bobo-Dioulasso", "Dafra", "Do"],
    "Kenedougou": ["Orodara", "Koloko"],
    "Tuy": ["Hounde", "Bereba"],
    "Loroum": ["Titao", "Bouroum"],
    "Passore": ["Yako", "Arbolle"],
    "Yatenga": ["Ouahigouya", "Gourcy"],
    "Zondoma": ["Gourcy", "Bassi"],
    "Ganzourgou": ["Zorgho", "Mogtedo"],
    "Kourweogo": ["Bousse", "Laye"],
    "Oubritenga": ["Ziniare", "Loumbila"],
    "Oudalan": ["Gorom-Gorom", "Markoye"],
    "Seno": ["Dori", "Bani"],
    "Soum": ["Djibo", "Nassoumbou"],
    "Yagha": ["Sebba", "Mansila"],
    "Djelgodji": ["Djibo", "Kelbo"],
    "Bougouriba": ["Diebougou", "Batie"],
    "Ioba": ["Dano", "Ouessa"],
    "Noumbiel": ["Batie", "Kampti"],
    "Poni": ["Gaoua", "Kampti"],
}


# ── Monitored diseases and epidemic thresholds ────────────────────────────────
# Single source of truth for disease monitoring. Defined as a list of tuples
# to preserve ordering, then unpacked into lookup dicts/tuples for performance.
DISEASES: list[tuple[str, int]] = [
    ("Malaria", 10),
    ("Cerebrospinal Meningitis", 3),
    ("Cholera", 2),
    ("Measles", 3),
    ("Dengue", 4),
    ("Waterborne Diseases (Diarrhea)", 5),
    ("Acute Respiratory Infections (Pneumonia)", 5),
]

# Fast O(1) lookup for threshold comparisons.
DISEASE_THRESHOLDS: dict[str, int] = {
    name: threshold for name, threshold in DISEASES
}
# Preserved order for UI lists and report headers.
DISEASE_NAMES: tuple[str, ...] = tuple(name for name, _ in DISEASES)

# Color mapping aligns with clinical urgency and epidemiological context.
# See module docstring for the color coding rationale.
DISEASE_COLORS: dict[str, str] = {
    "Malaria": "\033[92m",
    "Cerebrospinal Meningitis": "\033[91m",
    "Cholera": "\033[93m",
    "Measles": "\033[96m",
    "Dengue": "\033[95m",
    "Waterborne Diseases (Diarrhea)": "\033[94m",
    "Acute Respiratory Infections (Pneumonia)": "\033[97m",
}

DISEASE_LEGEND: dict[str, str] = {
    "Malaria": "Common / Treatable — endemic, seasonal peaks in rainy season",
    "Cerebrospinal Meningitis": "Dangerous — seasonal epidemic, Sahel belt, high mortality",
    "Cholera": "Outbreak-prone — waterborne, rapid spread, dehydration risk",
    "Measles": "Vaccine-preventable — paediatric, high contagion",
    "Dengue": "Emerging threat — arboviral, urban spread, no specific treatment",
    "Waterborne Diseases (Diarrhea)": "Sanitation-linked — environmental, paediatric vulnerability",
    "Acute Respiratory Infections (Pneumonia)": "Common / Seasonal — dry season, elderly and paediatric risk",
}


# ── Health facilities per region ──────────────────────────────────────────────
# Reference list for routing reports and filtering data by facility type.
# Not exhaustive; maintained for UI completeness and export accuracy.
HEALTH_FACILITIES: dict[str, list[str]] = {
    "Centre": [
        "CHU Yalgado Ouedraogo", "CHU Pediatrique Charles de Gaulle",
        "CMA Bogodogo", "CMA Nongr-Massom", "CMA Patte d'Oie",
        "CSPS Saaba", "CSPS Koulouba", "CSPS Tanghin-Dassouri",
    ],
    "Hauts-Bassins": [
        "CHU Sourou Sanou", "CMA Dafra", "CMA Do", "CMA Orodara", "CMA Hounde",
    ],
    "Cascades": ["CMA Banfora", "CMA Sindou"],
    "Boucle du Mouhoun": ["CMA Dedougou", "CMA Boromo", "CMA Tougan", "CMA Nouna"],
    "Centre-Ouest": ["CMA Koudougou", "CMA Leo", "CMA Reo", "CMA Sapouy"],
    "Sahel": ["CHR de Dori", "CMA Dori", "CMA Gorom-Gorom", "CHR de Djibo", "CMA Djibo"],
    "Nord": ["CMA Ouahigouya", "CMA Yako", "CMA Gourcy"],
    "Centre-Nord": ["CMA Kaya", "CHR de Kaya", "CMA Kongoussi", "CSP Boulsa"],
    "Est": ["CMA Fada N'Gourma", "CMA Diapaga", "CMA Gayeri"],
    "Centre-Est": ["CMA Tenkodogo", "CMA Garango", "CMA Koupela"],
    "Centre-Sud": ["CMA Kombissiri", "CMA Po", "CMA Manga"],
    "Plateau-Central": ["CMA Zorgho", "CMA Ziniare", "CMA Bousse"],
    "Sud-Ouest": ["CMA Dano", "CMA Gaoua", "CMA Diebougou", "CMA Batie"],
}


# ── ANSI colours — dark terminal palette ──────────────────────────────────────
class Colors:
    """Namespaced ANSI escape sequences for terminal styling.

    Using a class avoids polluting the module namespace and makes it
    trivial to swap palettes later (e.g., light theme or Windows CMD
    compatibility layer). Always pair with `Colors.RESET` in output strings.
    """
    RESET: str = "\033[0m"
    BOLD: str = "\033[1m"
    DIM: str = "\033[2m"
    UNDERLINE: str = "\033[4m"
    RED: str = "\033[91m"
    GREEN: str = "\033[92m"
    YELLOW: str = "\033[93m"
    BLUE: str = "\033[94m"
    MAGENTA: str = "\033[95m"
    CYAN: str = "\033[96m"
    WHITE: str = "\033[97m"
    GRAY: str = "\033[90m"


# ── Role definitions — strictly separated ─────────────────────────────────────
# RBAC design: Health Agents only modify raw data; Department Agents only
# consume aggregated outputs. This prevents accidental overwrites and enforces
# audit trails for official reporting.
HEALTH_AGENT_ACTIONS: tuple[str, ...] = (
    "register_patient",
    "search_patient",
    "update_status",
    "view_own_entries",
)

DEPT_AGENT_ACTIONS: tuple[str, ...] = (
    "view_cases",
    "view_alerts",
    "detect_epidemic",
    "generate_report",
    "export_report",
    "view_analytics",
)

AGENT_ROLES: tuple[str, ...] = ("Health Agent", "Department Agent")

ROLE_DESCRIPTIONS: dict[str, str] = {
    "Health Agent": "Data entry — register patients, update status, review your entries",
    "Department Agent": "Consultation & analysis — view reports, detect epidemics, export data",
}


# ── Menu labels ───────────────────────────────────────────────────────────────
# UI strings kept here to support localization and consistent ordering.
# Indices map directly to action handlers; do not reorder without updating
# the routing layer.
HEALTH_MENU: list[str] = [
    "Register a new patient",
    "Search for a patient",
    "Update patient status",
    "Review my entries",
    "Color legend",
    "Exit",
]

DEPT_MENU: list[str] = [
    "View disease cases by zone",
    "Run epidemic detection",
    "View active alerts",
    "Generate epidemiological report",
    "Export report to file",
    "View analytics dashboard",
    "Color legend",
    "Exit",
]
