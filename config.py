"""Configuration module for EpiAlert.

Every constant the application needs lives here: geographic data for
Burkina Faso, disease thresholds, color codes, file paths, partner
institutions, and menu labels.  Keeping it all in one place means we
never hunt through logic code to change a threshold or a region name.

Geographic data follows the 2024 administrative reform.  Disease
thresholds are drawn from Ministry of Health guidelines and WHO
standards.  Institutional partners are real organisations that work
on epidemiological surveillance and outbreak response in Burkina Faso.

Design notes
------------
- All public names are listed in ``__all__`` so that ``from config import *``
  is predictable and static-analysis tools can see what is exported.
- Immutable collections (tuples, frozensets) are preferred wherever the
  data must not change at runtime.  This also allows CPython to store
  the object as a constant, which is marginally faster on each access.
- Type annotations are provided on every module-level variable.  They
  serve as inline documentation and let ``mypy`` / ``pyright`` catch
  accidental misuse (e.g. passing a region name where a province name
  is expected).
"""

import os
from typing import Final

# __all__ controls what ``from config import *`` exports.
# Keeping it explicit prevents leaking private helpers like _BASE_DIR.
__all__: list[str] = [
    "APP_NAME",
    "APP_VERSION",
    "APP_TAGLINE",
    "APP_SLOGAN",
    "APP_DESCRIPTION",
    "MOTTO_FR",
    "MOTTO_EN",
    "GOV_INSTITUTIONS",
    "RESEARCH_INSTITUTIONS",
    "INTERNATIONAL_INSTITUTIONS",
    "NGO_INSTITUTIONS",
    "INSTITUTIONS",
    "INSTITUTION_CATEGORIES",
    "DATA_DIR",
    "OUTPUTS_DIR",
    "CLASSEURS_DIR",
    "PATIENTS_FILE",
    "CASES_FILE",
    "ALERTS_FILE",
    "PATIENT_STATUSES",
    "STATUS_ICONS",
    "STATUS_COLORS",
    "STATUS_LABELS",
    "SEVERITY_LEVELS",
    "SEVERITY_COLORS",
    "SEVERITY_ICONS",
    "SEVERITY_LABELS",
    "VALID_GENDERS",
    "REGIONS",
    "PROVINCES",
    "COMMUNES",
    "DISEASES",
    "DISEASE_THRESHOLDS",
    "DISEASE_NAMES",
    "DISEASE_COLORS",
    "DISEASE_LEGEND",
    "HEALTH_FACILITIES",
    "Colors",
    "HEALTH_AGENT_ACTIONS",
    "DEPT_AGENT_ACTIONS",
    "AGENT_ROLES",
    "ROLE_DESCRIPTIONS",
    "HEALTH_MENU",
    "DEPT_MENU",
    "CONTRIBUTIONS",
]


# App identity

APP_NAME: Final[str] = "EpiAlert"
APP_VERSION: Final[str] = "2.0.0"
APP_TAGLINE: Final[str] = (
    "Epidemiological Surveillance System for Burkina Faso"
)
APP_SLOGAN: Final[str] = (
    "Detect early. Respond fast. Save lives."
)
APP_DESCRIPTION: Final[str] = (
    "A terminal-based tool for tracking disease outbreaks,"
    " detecting epidemics, and generating epidemiological"
    " reports across the 13 regions of Burkina Faso."
)

# Burkina Faso's national motto in French and English.
MOTTO_FR: Final[str] = "La Patrie ou la Mort, Nous Vaincrons"
MOTTO_EN: Final[str] = "The Homeland or Death, We Shall Overcome"


# Institutional partners

# Each institution is a (full_name, abbreviation) tuple.
# Tuples are used instead of lists because the pairs are never modified
# at runtime — they are fixed reference data.
GOV_INSTITUTIONS: Final[tuple[tuple[str, str], ...]] = (
    ("Ministry of Health, Burkina Faso", "MS/BF"),
    ("National Institute of Public Health (INSP)", "INSP"),
    ("Centre for Emergency Health Operations (CORUS)", "CORUS"),
    ("National Observatory of Population Health (ONSP)", "ONSP"),
    ("General Directorate of Health and Public Hygiene (DGSHP)", "DGSHP"),
    ("Health Information and Epidemiological Surveillance Centres (CISSE)", "CISSE"),
    ("General Directorate of Studies and Sectoral Statistics (DGESS)", "DGESS"),
)

RESEARCH_INSTITUTIONS: Final[tuple[tuple[str, str], ...]] = (
    ("Centre Muraz — Bobo-Dioulasso", "Centre Muraz"),
    ("Health Research Centre of Nouna (CRSN)", "CRSN"),
    ("Centre for Research and Training on Malaria (CNRFP)", "CNRFP"),
    ("Health Sciences Research Institute (IRSS)", "IRSS"),
    ("Burkina Field Epidemiology and Laboratory Training Program (BFETP)", "BFETP"),
)

INTERNATIONAL_INSTITUTIONS: Final[tuple[tuple[str, str], ...]] = (
    ("World Health Organization (OMS)", "WHO"),
    ("UNICEF Burkina Faso", "UNICEF-BF"),
    ("Africa Centres for Disease Control and Prevention", "Africa CDC"),
)

NGO_INSTITUTIONS: Final[tuple[tuple[str, str], ...]] = (
    ("Red Cross of Burkina Faso (CRB)", "CRB"),
    ("Doctors Without Borders (MSF)", "MSF"),
)

# Combine all categories into a single list for backward compatibility
# and for code that simply iterates over every partner.
INSTITUTIONS: Final[list[tuple[str, str]]] = list(
    GOV_INSTITUTIONS
    + RESEARCH_INSTITUTIONS
    + INTERNATIONAL_INSTITUTIONS
    + NGO_INSTITUTIONS
)

# Mapping category name → list of (name, abbr) tuples.
# Useful for grouped display in reports or UI panels.
INSTITUTION_CATEGORIES: Final[dict[str, tuple[tuple[str, str], ...]]] = {
    "Government": GOV_INSTITUTIONS,
    "Research": RESEARCH_INSTITUTIONS,
    "International": INTERNATIONAL_INSTITUTIONS,
    "NGO": NGO_INSTITUTIONS,
}


# File paths

# _BASE_DIR is intentionally excluded from __all__ because it is a
# private helper — nothing outside this module should rely on it.
_BASE_DIR: str = os.path.dirname(os.path.abspath(__file__))
DATA_DIR: Final[str] = os.path.join(_BASE_DIR, "data")
OUTPUTS_DIR: Final[str] = os.path.join(_BASE_DIR, "outputs")
CLASSEURS_DIR: Final[str] = os.path.join(OUTPUTS_DIR, "classeurs")
PATIENTS_FILE: Final[str] = os.path.join(DATA_DIR, "patients.txt")
CASES_FILE: Final[str] = os.path.join(DATA_DIR, "cases.txt")
ALERTS_FILE: Final[str] = os.path.join(DATA_DIR, "alerts.txt")


# Patient statuses and icons

# A tuple of status strings.  We use tuple instead of list because the
# set of statuses is fixed — new statuses should be added here
# deliberately, not appended at runtime.
PATIENT_STATUSES: Final[tuple[str, ...]] = (
    "Suspected", "Confirmed", "Recovered", "Deceased",
)

STATUS_ICONS: Final[dict[str, str]] = {
    "Suspected": "?",
    "Confirmed": "!",
    "Recovered": "+",
    "Deceased": "x",
}

# ANSI escape sequences that change the terminal text colour.
# These 7-character strings (e.g. "\033[91m") are understood by most
# Unix terminals and the Windows Terminal.  They have no effect when
# output is redirected to a file.
STATUS_COLORS: Final[dict[str, str]] = {
    "Suspected": "\033[93m",
    "Confirmed": "\033[91m",
    "Recovered": "\033[92m",
    "Deceased": "\033[90m",
}

STATUS_LABELS: Final[dict[str, str]] = {
    "Suspected": "Under investigation",
    "Confirmed": "Laboratory-confirmed",
    "Recovered": "Discharged / healed",
    "Deceased": "Death recorded",
}


# Alert severity

SEVERITY_LEVELS: Final[tuple[str, ...]] = ("Warning", "Critical", "Emergency")

SEVERITY_COLORS: Final[dict[str, str]] = {
    "Warning": "\033[93m",
    "Critical": "\033[91m",
    "Emergency": "\033[95m",
}

SEVERITY_ICONS: Final[dict[str, str]] = {
    "Warning": "▲",
    "Critical": "▲▲",
    "Emergency": "▲▲▲",
}

SEVERITY_LABELS: Final[dict[str, str]] = {
    "Warning": "Cases exceed threshold by 1-50 %",
    "Critical": "Cases exceed threshold by 51-100 %",
    "Emergency": "Cases exceed threshold by > 100 %",
}


# Gender

# frozenset is used here instead of tuple because the only operation we
# need is membership testing (``gender in VALID_GENDERS``).  A set
# provides O(1) average lookup vs O(n) for a tuple, and frozenset
# signals immutability to both the reader and the interpreter.
VALID_GENDERS: Final[frozenset[str]] = frozenset(("M", "F"))


# Burkina Faso — 13 regions (2024 reform)

# Region name → regional capital.  After the 2024 administrative
# reform Burkina Faso retained 13 regions; capital cities are where
# the regional health directorate (DRS) is headquartered.
REGIONS: Final[dict[str, str]] = {
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

# Region → list of provinces within that region.
# Province names are the keys of COMMUNES below, so any look-up that
# goes region → province → commune can chain these two dicts.
PROVINCES: Final[dict[str, list[str]]] = {
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

# Province → list of communes.  Communes are the finest granularity
# used by EpiAlert for case localisation.
COMMUNES: Final[dict[str, list[str]]] = {
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


# Monitored diseases and epidemic thresholds

# Each entry is (disease_name, weekly_case_threshold).  The threshold
# is the number of cases in a single health district per week above
# which an alert should be raised.  Values come from Ministry of
# Health guidelines and WHO standards.
DISEASES: Final[list[tuple[str, int]]] = [
    ("Malaria", 10),
    ("Cerebrospinal Meningitis", 3),
    ("Cholera", 2),
    ("Measles", 3),
    ("Dengue", 4),
    ("Waterborne Diseases (Diarrhea)", 5),
    ("Acute Respiratory Infections (Pneumonia)", 5),
]

# Derived mappings — dict comprehensions make the link to DISEASES
# explicit, so adding a disease in one place updates both dicts.
DISEASE_THRESHOLDS: Final[dict[str, int]] = {
    name: threshold for name, threshold in DISEASES
}
DISEASE_NAMES: Final[tuple[str, ...]] = tuple(name for name, _ in DISEASES)

DISEASE_COLORS: Final[dict[str, str]] = {
    "Malaria": "\033[92m",
    "Cerebrospinal Meningitis": "\033[91m",
    "Cholera": "\033[93m",
    "Measles": "\033[96m",
    "Dengue": "\033[95m",
    "Waterborne Diseases (Diarrhea)": "\033[94m",
    "Acute Respiratory Infections (Pneumonia)": "\033[97m",
}

DISEASE_LEGEND: Final[dict[str, str]] = {
    "Malaria": "Common / Treatable — endemic, seasonal peaks in rainy season",
    "Cerebrospinal Meningitis": "Dangerous — seasonal epidemic, Sahel belt, high mortality",
    "Cholera": "Outbreak-prone — waterborne, rapid spread, dehydration risk",
    "Measles": "Vaccine-preventable — paediatric, high contagion",
    "Dengue": "Emerging threat — arboviral, urban spread, no specific treatment",
    "Waterborne Diseases (Diarrhea)": "Sanitation-linked — environmental, paediatric vulnerability",
    "Acute Respiratory Infections (Pneumonia)": (
        "Common / Seasonal — dry season, elderly and paediatric risk"
    ),
}


# Health facilities per region

# Major health facilities (hospitals, CMAs, CSPS) organised by region.
# CHU = Centre Hospitalier Universitaire (university hospital)
# CHR = Centre Hospitalier Regional (regional hospital)
# CMA = Centre Medical avec Antenne chirurgicale (medical centre with surgery)
# CSPS = Centre de Sante et de Promotion Sociale (primary health centre)
HEALTH_FACILITIES: Final[dict[str, list[str]]] = {
    "Centre": [
        "CHU Yalgado Ouedraogo", "CHU Pediatrique Charles de Gaulle",
        "CMA Bogodogo", "CMA Nongr-Massom", "CMA Patte d'Oie",
        "CSPS Saaba", "CSPS Koulouba", "CSPS Tanghin-Dassouri",
    ],
    "Hauts-Bassins": ["CHU Sourou Sanou", "CMA Dafra", "CMA Do", "CMA Orodara", "CMA Hounde"],
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


# ANSI colours — dark terminal palette

class Colors:
    """ANSI escape sequences for styling text on dark terminal backgrounds.

    These codes are widely supported on Unix terminals and the modern
    Windows Terminal.  They are silently ignored when output is piped
    to a file or a non-TTY stream.

    Usage example::

        print(f"{Colors.RED}Alert!{Colors.RESET}")
    """

    RESET: Final[str] = "\033[0m"
    BOLD: Final[str] = "\033[1m"
    DIM: Final[str] = "\033[2m"
    UNDERLINE: Final[str] = "\033[4m"
    RED: Final[str] = "\033[91m"
    GREEN: Final[str] = "\033[92m"
    YELLOW: Final[str] = "\033[93m"
    BLUE: Final[str] = "\033[94m"
    MAGENTA: Final[str] = "\033[95m"
    CYAN: Final[str] = "\033[96m"
    WHITE: Final[str] = "\033[97m"
    GRAY: Final[str] = "\033[90m"


# Role definitions

# Each role maps to a set of permitted actions.  frozenset is used for
# the action collections because membership testing is the primary
# operation and immutability is guaranteed.
HEALTH_AGENT_ACTIONS: Final[frozenset[str]] = frozenset(
    ("register_patient", "search_patient", "update_status", "view_own_entries")
)
DEPT_AGENT_ACTIONS: Final[frozenset[str]] = frozenset(
    ("view_cases", "view_alerts", "detect_epidemic", "generate_report",
     "export_report", "view_analytics")
)
AGENT_ROLES: Final[tuple[str, ...]] = ("Health Agent", "Department Agent")

ROLE_DESCRIPTIONS: Final[dict[str, str]] = {
    "Health Agent": "Data entry — register patients, update status, review your entries",
    "Department Agent": "Consultation & analysis — view reports, detect epidemics, export data",
}


# Menu labels

HEALTH_MENU: Final[list[str]] = [
    "Register a new patient",
    "Search for a patient",
    "Update patient status",
    "Review my entries",
    "Color legend",
    "Exit",
]

DEPT_MENU: Final[list[str]] = [
    "View disease cases by zone",
    "Run epidemic detection",
    "View active alerts",
    "Generate epidemiological report",
    "Export report to file",
    "View analytics dashboard",
    "Color legend",
    "Exit",
]


# Team contributions

# Each team member's contributions are listed in French to match the
# project's working language.  This dict serves as both attribution
# and onboarding documentation — a new developer can see who worked on
# what and whom to ask about a given subsystem.
CONTRIBUTIONS: Final[dict[str, list[str]]] = {
    "Lucienne": [
        "Correction des fichiers de donnees patients.txt et cases.txt",
        "Ajout des horodatages automatiques dans les en-tetes de fichiers",
        "Validation des seuils epidemiques avec les referentiel MS et OMS",
        "Normalisation des noms de regions selon la reforme de 2024",
    ],
    "Grace": [
        "Conception du module de detection d'epidemies",
        "Implementation de l'algorithme de seuil par district sanitaire",
        "Refactorisation du menu agent de departement",
        "Tests unitaires pour la detection de cas anormaux",
    ],
    "Kiswendsida": [
        "Structure des dictionnaires geographiques (regions, provinces, communes)",
        "Integration des etablissements de sant%C3%A9 par region",
        "Mise en place du systeme de couleurs ANSI pour le terminal",
        "Cartographie des districts sanitaires du Sahel",
    ],
    "Nave": [
        "Implementation du module d'enregistrement des patients",
        "Gestion des statuts patients et des icones associees",
        "Export des rapports epidemiologiques en fichiers texte",
        "Amelioration de l'affichage du tableau de bord analytique",
    ],
    "Mohamed": [
        "Systeme d'alertes avec niveaux de severite (Warning, Critical, Emergency)",
        "Calcul du pourcentage de depassement des seuils",
        "Filtrage des alertes actives par region et par maladie",
        "Documentation des protocoles de notification d'urgence",
    ],
    "Arnaud": [
        "Architecture du fichier config.py et centralisation des constantes",
        "Organisation des institutions partenaires par categorie",
        "Mise en place de __all__ pour le controle des exports",
        "Revue PEP 8 et ajout des annotations de type sur tout le module",
        "Integration du dictionnaire des contributions de l'equipe",
    ],
}
