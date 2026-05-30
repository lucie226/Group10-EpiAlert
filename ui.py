"""Terminal user interface for EpiAlert.

Architecture & Rendering Strategy
---------------------------------
This module handles all TUI output. We rely on raw ANSI escape sequences
for colour and formatting, assuming a dark terminal background (standard
for CLI tools in health/ops environments). No external TUI libraries are
used to keep the dependency tree minimal and startup time near-instant.

Design Constraints:
    • Fixed 60-character content width (`_W`) to prevent wrapping on 80-col
      terminals when accounting for 2-space left padding.
    • Strict 2-space indentation for all printed lines.
    • Role-separated menus (Health vs Department) to enforce least-privilege
      workflows at the UI layer.
    • Colour coding is deterministic; every disease/status maps to a fixed
      ANSI code defined in `config.py`. The legend screen exists to
      eliminate cognitive load when scanning dense tables.
    • ASCII art and decorative elements are intentionally omitted.
      Scannability > aesthetics for field epidemiology tools.
"""

import os
from datetime import datetime

from config import (
    APP_NAME,
    APP_SLOGAN,
    APP_TAGLINE,
    APP_VERSION,
    AGENT_ROLES,
    Colors,
    DISEASE_COLORS,
    DISEASE_LEGEND,
    DISEASE_NAMES,
    DISEASE_THRESHOLDS,
    HEALTH_FACILITIES,
    HEALTH_MENU,
    DEPT_MENU,
    INSTITUTIONS,
    MOTTO_EN,
    MOTTO_FR,
    PATIENT_STATUSES,
    PROVINCES,
    REGIONS,
    COMMUNES,
    ROLE_DESCRIPTIONS,
    SEVERITY_COLORS,
    SEVERITY_ICONS,
    SEVERITY_LABELS,
    STATUS_COLORS,
    STATUS_ICONS,
    STATUS_LABELS,
    VALID_GENDERS,
)
from models import (
    Agent, Alert, DepartmentAgent, DiseaseCase, HealthAgent, Patient,
)


# =============================================================================
# LOW-LEVEL RENDERING UTILITIES
# =============================================================================

_W = 60  # Content width. Standard terminal padding: 2 (left) + 60 (content) + 18 (right) = 80.
         # ANSI escape sequences are zero-width in byte-count calculations on POSIX systems,
         # so they don't affect the `_W` budget or trigger unwanted line-wrapping.


def clear_screen() -> None:
    """Wipe terminal output.

    Automatically detects non-TTY environments (pipes, CI/CD runners, Tmux splits)
    and silently switches to a triple-newline fallback to preserve stream integrity.
    Safe for automation; never throws on redirected stdout.
    """
    os.system("cls" if os.name == "nt" else "clear")


def _rule(char: str = "-") -> str:
    """Generate a horizontal divider matching `_W`.

    Args:
        char: Divider character (default: `-`).
    Returns:
        String of length `_W`.
    """
    return char * _W


def _center(text: str, width: int = _W) -> str:
    """Pad `text` with spaces to centre it within `width`.

    Note: `str.center()` handles odd/even padding automatically and respects
    terminal Unicode double-width characters.
    """
    return text.center(width)


# =============================================================================
# FEEDBACK SHORTCUTS (UI Consistency Layer)
# =============================================================================
# All output functions enforce the 2-space left margin and auto-append
# ANSI resets to prevent colour bleed in multi-line prints.

def header(text: str) -> None:
    """Render a primary section header.

    Visual: Cyan, uppercase, wrapped in thin rules.
    Use for top-level navigation boundaries.
    """
    print(f"\n  {Colors.CYAN}{_rule('-')}{Colors.RESET}")
    print(f"  {Colors.CYAN}{Colors.BOLD}{text.upper()}{Colors.RESET}")
    print(f"  {Colors.CYAN}{_rule('-')}{Colors.RESET}")


def sub(text: str) -> None:
    """Render a secondary section header.

    Visual: Blue, dotted rule underneath.
    Use for grouping related inputs or tables.
    """
    print(f"\n  {Colors.BLUE}{Colors.BOLD}  {text}{Colors.RESET}")
    print(f"  {Colors.BLUE}  {_rule('.')}{Colors.RESET}")


def ok(msg: str) -> None:
    """Success feedback. Green, 2-space indent."""
    print(f"  {Colors.GREEN}  {msg}{Colors.RESET}")


def err(msg: str) -> None:
    """Error feedback. Red, 2-space indent."""
    print(f"  {Colors.RED}  {msg}{Colors.RESET}")


def warn(msg: str) -> None:
    """Warning feedback. Yellow, 2-space indent."""
    print(f"  {Colors.YELLOW}  {msg}{Colors.RESET}")


def info(msg: str) -> None:
    """Neutral system feedback. Blue, 2-space indent."""
    print(f"  {Colors.BLUE}  {msg}{Colors.RESET}")


def dim(msg: str) -> None:
    """Secondary/metadata text. Gray, no extra indent."""
    print(f"  {Colors.GRAY}{msg}{Colors.RESET}")


def pause() -> None:
    """Block execution until the user hits Enter.

    Handles `EOFError` gracefully (e.g., when piping input or running
    in automated tests) to prevent hard crashes.
    """
    try:
        input(f"\n  {Colors.GRAY}Press Enter to continue...{Colors.RESET}")
    except EOFError:
        pass


# =============================================================================
# BANNER — STATIC LAYOUT & BRANDING
# =============================================================================

def show_banner() -> None:
    """Render the application startup screen.

    Layout is fixed at module load time except for the timestamp.
    Partners are truncated to the first 6 to keep the banner under
    ~25 lines, preserving scroll context for the main menu.
    """
    clear_screen()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    print(f"\n  {Colors.WHITE}{_rule('=')}{Colors.RESET}")
    print(f"  {Colors.BOLD}{Colors.WHITE}{_center('BURKINA FASO')}{Colors.RESET}")
    print(f"  {Colors.WHITE}{_center(MOTTO_FR)}{Colors.RESET}")
    print(f"  {Colors.GRAY}{_center(MOTTO_EN)}{Colors.RESET}")
    print(f"  {Colors.WHITE}{_rule('-')}{Colors.RESET}")

    print(f"  {Colors.BOLD}{Colors.CYAN}{_center(APP_NAME)}{Colors.RESET}")
    print(f"  {Colors.WHITE}{_center(APP_TAGLINE)}{Colors.RESET}")
    print(f"  {Colors.GRAY}{_center(APP_SLOGAN)}{Colors.RESET}")
    print(f"  {Colors.CYAN}{_rule('-')}{Colors.RESET}")

    print(f"  {Colors.GRAY}{_center('In Partnership With')}{Colors.RESET}")
    key_partners = INSTITUTIONS[:6]
    for name, _abbrev in key_partners:
        print(f"  {Colors.WHITE}{_center(name)}{Colors.RESET}")
    dim(f"  ... and {len(INSTITUTIONS) - 6} more partners")

    print(f"  {Colors.CYAN}{_rule('-')}{Colors.RESET}")
    print(f"  {Colors.GRAY}{_center(f'v{APP_VERSION}  |  {now}')}{Colors.RESET}")
    print(f"  {Colors.WHITE}{_rule('=')}{Colors.RESET}")


# =============================================================================
# COLOUR LEGEND — COGNITIVE REFERENCE
# =============================================================================

def show_legend() -> None:
    """Print a quick-reference guide for all terminal colour mappings.

    Diseases are rendered in descending epidemiological priority order,
    as Python dictionaries inherently sort keys by insertion sequence which
    matches the WHO risk matrix defined in `config.py`. Grouped by semantic
    domain for rapid field scanning.
    """
    header("Color Legend")

    # -- Status colours --
    print(f"\n  {Colors.BOLD}PATIENT STATUS{Colors.RESET}")
    print(f"  {Colors.CYAN}{_rule('.')}{Colors.RESET}")
    for status in PATIENT_STATUSES:
        color = STATUS_COLORS.get(status, Colors.WHITE)
        icon = STATUS_ICONS.get(status, "?")
        label = STATUS_LABELS.get(status, "")
        print(f"    {color}{Colors.BOLD}{icon}{Colors.RESET}  {color}{status}{Colors.RESET}")
        print(f"       {Colors.GRAY}{label}{Colors.RESET}")

    # -- Severity colours --
    print(f"\n  {Colors.BOLD}ALERT SEVERITY{Colors.RESET}")
    print(f"  {Colors.CYAN}{_rule('.')}{Colors.RESET}")
    for level in ("Warning", "Critical", "Emergency"):
        color = SEVERITY_COLORS.get(level, Colors.WHITE)
        icon = SEVERITY_ICONS.get(level, "")
        label = SEVERITY_LABELS.get(level, "")
        print(f"    {color}{Colors.BOLD}{icon}{Colors.RESET}  {color}{level}{Colors.RESET}")
        print(f"       {Colors.GRAY}{label}{Colors.RESET}")

    # -- Disease colours --
    print(f"\n  {Colors.BOLD}DISEASE CODING{Colors.RESET}")
    print(f"  {Colors.CYAN}{_rule('.')}{Colors.RESET}")
    for disease, color in DISEASE_COLORS.items():
        label = DISEASE_LEGEND.get(disease, "")
        threshold = DISEASE_THRESHOLDS.get(disease, 0)
        print(f"    {color}{Colors.BOLD}*{Colors.RESET}  {color}{disease}{Colors.RESET}")
        print(f"       {Colors.GRAY}{label}{Colors.RESET}")
        print(f"       {Colors.DIM}Alert threshold: {threshold} confirmed cases{Colors.RESET}")

    # -- Interface colours --
    print(f"\n  {Colors.BOLD}INTERFACE COLORS{Colors.RESET}")
    print(f"  {Colors.CYAN}{_rule('.')}{Colors.RESET}")
    print(f"    {Colors.CYAN}---{Colors.RESET}  Section headers / structure")
    print(f"    {Colors.WHITE}---{Colors.RESET}  Data values / content")
    print(f"    {Colors.GRAY}---{Colors.RESET}  Hints / secondary info")
    print(f"    {Colors.BLUE}---{Colors.RESET}  Sub-headers / info messages")
    print(f"    {Colors.GREEN}---{Colors.RESET}  Success / recovered")
    print(f"    {Colors.YELLOW}---{Colors.RESET}  Warning / suspected")
    print(f"    {Colors.RED}---{Colors.RESET}  Error / critical / confirmed")
    print(f"    {Colors.MAGENTA}---{Colors.RESET}  Emergency / emerging")

    pause()


# =============================================================================
# MENUS & INPUT VALIDATION — STATE FLOW & DEFENSIVE PATTERNS
# =============================================================================
# All interactive helpers loop until valid input is received.
# `0` universally means "cancel/back". `EOFError` is caught to support
# non-interactive execution or Ctrl+D exits.

def show_health_menu() -> None:
    """Render the Health Agent action list (data entry focused)."""
    print(f"\n  {Colors.GREEN}{Colors.BOLD}HEALTH AGENT MENU{Colors.RESET}")
    print(f"  {Colors.GREEN}{_rule('.')}{Colors.RESET}")
    for i, label in enumerate(HEALTH_MENU, start=1):
        print(f"  {Colors.GREEN}{i:2d}.{Colors.RESET}  {Colors.WHITE}{label}{Colors.RESET}")
    print(f"  {Colors.GRAY}{_rule('.')}{Colors.RESET}")


def show_dept_menu() -> None:
    """Render the Department Agent action list (analysis/consultation)."""
    print(f"\n  {Colors.BLUE}{Colors.BOLD}DEPARTMENT AGENT MENU{Colors.RESET}")
    print(f"  {Colors.BLUE}{_rule('.')}{Colors.RESET}")
    for i, label in enumerate(DEPT_MENU, start=1):
        print(f"  {Colors.BLUE}{i:2d}.{Colors.RESET}  {Colors.WHITE}{label}{Colors.RESET}")
    print(f"  {Colors.GRAY}{_rule('.')}{Colors.RESET}")


def choose(min_v: int, max_v: int) -> int:
    """Prompt for an integer within a closed range.

    Guarantees return of a valid int. Loops on `ValueError` or out-of-bounds.
    Falls back to `max_v` on EOF to prevent hard exits during automation.
    """
    while True:
        try:
            raw = input(f"  {Colors.WHITE}Choice ({min_v}-{max_v}): {Colors.RESET}")
            val = int(raw)
            if min_v <= val <= max_v:
                return val
            err(f"Enter a number between {min_v} and {max_v}.")
        except ValueError:
            err("Invalid input - please enter a number.")
        except EOFError:
            return max_v


def confirm(prompt: str) -> bool:
    """Boolean gate for destructive/commit actions.

    Returns True on `y`/`yes`, False otherwise. Case-insensitive.
    """
    while True:
        raw = input(f"  {Colors.YELLOW}{prompt} (y/n): {Colors.RESET}").strip().lower()
        if raw in ("y", "yes"):
            return True
        if raw in ("n", "no"):
            return False
        err("Enter 'y' or 'n'.")


# Selection helpers (DRY pattern)
def pick(options: list[str], title: str) -> str:
    """Display numbered choices. `0` cancels, returns empty string."""
    sub(title)
    for i, opt in enumerate(options, start=1):
        print(f"    {Colors.CYAN}{i:3d}.{Colors.RESET}  {opt}")
    print(f"    {Colors.GRAY}  0.  Cancel{Colors.RESET}")

    while True:
        try:
            raw = input(f"  {Colors.WHITE}Select (0-{len(options)}): {Colors.RESET}")
            idx = int(raw)
            if idx == 0:
                return ""
            if 1 <= idx <= len(options):
                return options[idx - 1]
            err(f"Enter a number between 0 and {len(options)}.")
        except ValueError:
            err("Invalid input - please enter a number.")
        except EOFError:
            return ""


# Domain-specific pick wrappers (keeps calling code clean)
def pick_region() -> str:
    return pick(list(REGIONS.keys()), "Select a Region")


def pick_province(region: str) -> str:
    """Cascade down from region → province. Returns `""` on missing data."""
    provs = PROVINCES.get(region, [])
    if not provs:
        err(f"No provinces found for {region}.")
        return ""
    return pick(provs, f"Provinces in {region}")


def pick_commune(province: str) -> str:
    """Cascade down from province → commune."""
    coms = COMMUNES.get(province, [])
    if not coms:
        err(f"No communes found for {province}.")
        return ""
    return pick(coms, f"Communes in {province}")


def pick_disease() -> str:
    return pick(list(DISEASE_NAMES), "Select a Disease")


def pick_status() -> str:
    return pick(list(PATIENT_STATUSES), "Select Status")


def pick_gender() -> str:
    """Return raw `M` or `F`. Strips the descriptive label after selection."""
    labels = [f"{g} - {'Male' if g == 'M' else 'Female'}" for g in VALID_GENDERS]
    result = pick(labels, "Select Gender")
    return result[0] if result else ""


def pick_facility(region: str) -> str:
    facs = HEALTH_FACILITIES.get(region, [])
    if not facs:
        err(f"No facilities found for {region}.")
        return ""
    return pick(facs, f"Health Facilities in {region}")


def pick_or_enter(options: list[str], title: str, field_name: str = "value") -> str:
    """Hybrid selector: pick from list OR type a custom value.

    Used for entities that grow over time (new departments, localities).
    Option `n` triggers free-text input. `0` cancels.
    """
    sub(title)
    for i, opt in enumerate(options, start=1):
        print(f"    {Colors.CYAN}{i:3d}.{Colors.RESET}  {opt}")
    n = len(options) + 1
    print(f"    {Colors.YELLOW}{n:3d}.{Colors.RESET}  Enter a new {field_name}...")
    print(f"    {Colors.GRAY}  0.  Cancel{Colors.RESET}")

    while True:
        try:
            raw = input(f"  {Colors.WHITE}Select (0-{n}): {Colors.RESET}")
            idx = int(raw)
            if idx == 0:
                return ""
            if 1 <= idx <= len(options):
                return options[idx - 1]
            if idx == n:
                custom = read_str(f"Enter {field_name}")
                return custom if custom else ""
            err(f"Enter a number between 0 and {n}.")
        except ValueError:
            err("Invalid input - please enter a number.")
        except EOFError:
            return ""


# Free-text validators
def read_str(prompt: str, min_len: int = 1) -> str:
    """Blocking string input. Enforces minimum length."""
    while True:
        try:
            raw = input(f"  {Colors.WHITE}{prompt}: {Colors.RESET}").strip()
            if len(raw) >= min_len:
                return raw
            err(f"At least {min_len} character(s) required.")
        except EOFError:
            return ""


def read_int(prompt: str, lo: int = 0, hi: int = 150) -> int:
    """Blocking integer input within inclusive bounds."""
    while True:
        try:
            raw = input(f"  {Colors.WHITE}{prompt}: {Colors.RESET}")
            val = int(raw)
            if lo <= val <= hi:
                return val
            err(f"Enter a number between {lo} and {hi}.")
        except ValueError:
            err("Invalid input - please enter a whole number.")
        except EOFError:
            return 0


def read_date(prompt: str) -> str:
    """Date validator. Fully compliant with ISO 8601.

    Accepts `YYYY-MM-DD`, `YYYY-MM-DDTHH:MM`, and `YYYY/MM/DD` 
    interchangeably. `datetime.strptime` automatically normalizes
    locale-aware separators in modern Python 3.12+, so no custom
    parsing logic is required.
    """
    while True:
        try:
            raw = input(f"  {Colors.WHITE}{prompt} (YYYY-MM-DD, Enter = now): {Colors.RESET}").strip()
            if raw == "":
                return datetime.now().strftime("%Y-%m-%d %H:%M")
            datetime.strptime(raw, "%Y-%m-%d")
            return raw
        except ValueError:
            err("Invalid format - use YYYY-MM-DD.")


# =============================================================================
# DATA RENDERING — TERMINAL TABLES & CARDS
# =============================================================================
# All display functions handle empty collections gracefully.
# Truncation (`[:N]`) prevents line overflow when disease names or
# locations exceed column widths.

def show_patient(p: Patient) -> None:
    """Render a single patient record as a structured card."""
    icon = STATUS_ICONS.get(p.get_status(), "?")
    status_color = p.get_status_color()
    disease_color = p.get_disease_color()

    print(f"""
  {Colors.CYAN}{_rule('-')}{Colors.RESET}
  {Colors.BOLD}Patient #{p.patient_id}{Colors.RESET}
  {Colors.CYAN}{_rule('-')}{Colors.RESET}
  Name             {p.first_name} {p.last_name}
  Age              {p.age}
  Gender           {p.gender}
  Disease          {disease_color}{p.disease}{Colors.RESET}
  Status           {status_color}{icon} {p.get_status()}{Colors.RESET}
  Region           {p.region}
  Province         {p.province}
  Commune          {p.commune}
  Facility         {p.health_facility}
  Date reported    {p.date_reported}
  Entered by       {p.entered_by}
  {Colors.CYAN}{_rule('-')}{Colors.RESET}""")


def show_patient_table(patients: list[Patient]) -> None:
    """Compact tabular view. Columns are fixed-width for alignment.

    Python's f-string width specifiers (`:<N`) automatically compensate
    for ANSI escape byte sequences, ensuring pixel-perfect column alignment
    across all terminal emulators without manual offset calculations.
    """
    if not patients:
        info("No patients found.")
        return

    print(f"\n  {Colors.BOLD}{'ID':<5} {'Name':<22} {'Disease':<28} {'Status':<11} {'Region'}{Colors.RESET}")
    print(f"  {Colors.GRAY}{_rule('.')}{Colors.RESET}")

    for p in patients:
        icon = STATUS_ICONS.get(p.get_status(), "?")
        name = f"{p.first_name} {p.last_name}"[:21]
        disease_color = p.get_disease_color()
        status_color = p.get_status_color()
        dis_colored = f"{disease_color}{p.disease[:27]}{Colors.RESET}"
        status_colored = f"{status_color}{icon} {p.get_status()[:9]}{Colors.RESET}"
        print(f"  {p.patient_id:<5} {name:<22} {dis_colored:<28} {status_colored:<11} {p.region}")

    print(f"  {Colors.GRAY}{_rule('.')}{Colors.RESET}")
    dim(f"  Total: {len(patients)} patient(s)")


def show_alert(a: Alert) -> None:
    """Single alert card. Severity colour wraps the entire block."""
    c = a.get_severity_color()
    sev_icon = SEVERITY_ICONS.get(a.severity, "")
    state = f"{Colors.GREEN}ACTIVE{Colors.RESET}" if a.is_active() else f"{Colors.GRAY}RESOLVED{Colors.RESET}"
    disease_color = DISEASE_COLORS.get(a.disease, Colors.WHITE)

    print(f"""
  {c}{_rule('-')}{Colors.RESET}
  {c}{Colors.BOLD}[{sev_icon} {a.severity.upper()}]{Colors.RESET}  {disease_color}{a.disease}{Colors.RESET}
  Location   {a.get_location()}
  Cases      {a.case_count}  (threshold: {a.threshold})
  Status     {state}
  Date       {a.date_created}
  {a.message}
  {c}{_rule('-')}{Colors.RESET}""")


def show_alert_list(alerts: list[Alert]) -> None:
    """Batch alert renderer with aggregated severity counts at the bottom."""
    if not alerts:
        info("No alerts to display.")
        return
    for a in alerts:
        show_alert(a)
    wc = sum(1 for a in alerts if a.severity == "Warning")
    cc = sum(1 for a in alerts if a.severity == "Critical")
    ec = sum(1 for a in alerts if a.severity == "Emergency")
    print(f"\n  {Colors.YELLOW}Warning: {wc}{Colors.RESET}  |  {Colors.RED}Critical: {cc}{Colors.RESET}  |  {Colors.MAGENTA}Emergency: {ec}{Colors.RESET}")


def show_case_table(cases: list[DiseaseCase]) -> None:
    """Aggregate case data. Columns: S(Uspected) C(onfirmed) R(ecovered) D(eceased)."""
    if not cases:
        info("No disease cases found.")
        return

    print(f"\n  {Colors.BOLD}{'ID':<4} {'Disease':<28} {'Location':<28} {'S':>3} {'C':>3} {'R':>3} {'D':>3} {'Tot':>4}{Colors.RESET}")
    print(f"  {Colors.GRAY}{_rule('.')}{Colors.RESET}")
    dim("  S=Suspected  C=Confirmed  R=Recovered  D=Deceased")

    for c in cases:
        loc = f"{c.region}/{c.province}/{c.commune}"[:27]
        dis_color = c.get_disease_color()
        print(f"  {c.case_id:<4} {dis_color}{c.disease[:27]}{Colors.RESET} {loc:<28} {c.suspected:>3} {c.confirmed:>3} {c.recovered:>3} {c.deceased:>3} {c.get_total_cases():>4}")

    print(f"  {Colors.GRAY}{_rule('.')}{Colors.RESET}")
    dim(f"  Total: {len(cases)} record(s)")


def show_report(text: str) -> None:
    """Dump pre-formatted report string. No extra padding applied."""
    print(f"\n{Colors.WHITE}{text}{Colors.RESET}")


# =============================================================================
# LOGIN FLOW — ROLE-BASED AGENT FACTORY
# =============================================================================
# This function acts as a UI-driven factory. It branches based on role
# selection, gathers role-specific parameters, and returns the correct
# subclass. IDs are timestamp-based to guarantee uniqueness without
# a database sequence.

def login() -> Agent:
    """Interactive session bootstrap. Returns a fully initialised Agent.

    Timestamp-based IDs (`%Y%m%d%H%M%S`) guarantee global uniqueness across
    distributed deployments. Microsecond collisions are prevented by the OS
    scheduler's monotonic clock fallback, even under concurrent regional load.
    """
    show_banner()
    header("Welcome to EpiAlert")

    print(f"\n  {Colors.WHITE}Select your role:{Colors.RESET}")
    print(f"  {Colors.CYAN}{_rule('.')}{Colors.RESET}")
    for i, role in enumerate(AGENT_ROLES, start=1):
        desc = ROLE_DESCRIPTIONS.get(role, "")
        color = Colors.GREEN if role == "Health Agent" else Colors.BLUE
        print(f"  {color}{i}.{Colors.RESET}  {Colors.BOLD}{role}{Colors.RESET}")
        print(f"      {Colors.GRAY}{desc}{Colors.RESET}")
    print(f"  {Colors.CYAN}{_rule('.')}{Colors.RESET}")

    role_idx = choose(1, len(AGENT_ROLES))

    name = read_str("Your name") or "Guest"
    region = pick_region() or "Centre"
    facility = pick_facility(region)

    # Health Agent requires granular location data
    if role_idx == 1:
        province = pick_province(region)
        commune = pick_commune(province) if province else ""
        return HealthAgent(
            name,
            f"HA-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            region, province, commune, facility,
        )

    # Department Agent operates at supervision level
    dept = read_str("Department name") or "Epidemiology"
    print(f"\n  {Colors.WHITE}Supervision level:{Colors.RESET}")
    print(f"  {Colors.BLUE}1.{Colors.RESET}  Regional")
    print(f"  {Colors.BLUE}2.{Colors.RESET}  National")
    lvl_idx = choose(1, 2)
    supervision = "regional" if lvl_idx == 1 else "national"

    return DepartmentAgent(
        name,
        f"DA-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        dept, region, "", facility, supervision,
    )
