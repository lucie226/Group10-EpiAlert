"""Terminal user interface for EpiAlert.

Everything you see on screen is drawn here.  We use ANSI escape codes
for colours and formatting on dark terminal backgrounds.  The design
is: sober, readable, professional — no flashy ASCII art, just clean
layout that makes information easy to scan.

Key design choices:
    * 60-character width for horizontal rules
    * 2-space left margin everywhere
    * Colour-coded diseases and statuses (with a built-in legend)
    * Severity-coloured alerts (yellow / red / magenta)
    * Numbered selections for every choice
    * Role-specific menus (Health Agent vs Department Agent)
    * No "About" screen — the banner says it all
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


# ── Drawing helpers ───────────────────────────────────────────────────────────

_W = 60  # standard line width


def clear_screen() -> None:
    """Clear the terminal (Windows and Unix)."""
    os.system("cls" if os.name == "nt" else "clear")


def _rule(char: str = "-") -> str:
    """Return a horizontal rule of width _W."""
    return char * _W


def _center(text: str, width: int = _W) -> str:
    """Center-align text within a given width."""
    return text.center(width)


# ── Message shortcuts ─────────────────────────────────────────────────────────

def header(text: str) -> None:
    """Print a section header between thin rules.

    Args:
        text: Header title (cyan, bold, uppercase).
    """
    print(f"\n  {Colors.CYAN}{_rule('-')}{Colors.RESET}")
    print(
        f"  {Colors.CYAN}{Colors.BOLD}{text.upper()}{Colors.RESET}"
    )
    print(f"  {Colors.CYAN}{_rule('-')}{Colors.RESET}")


def sub(text: str) -> None:
    """Print a sub-header with a dotted rule.

    Args:
        text: Sub-header text (blue).
    """
    print(
        f"\n  {Colors.BLUE}{Colors.BOLD}  {text}{Colors.RESET}"
    )
    print(f"  {Colors.BLUE}  {_rule('.')}{Colors.RESET}")


def ok(msg: str) -> None:
    """Print a success message in green."""
    print(f"  {Colors.GREEN}  {msg}{Colors.RESET}")


def err(msg: str) -> None:
    """Print an error message in red."""
    print(f"  {Colors.RED}  {msg}{Colors.RESET}")


def warn(msg: str) -> None:
    """Print a warning message in yellow."""
    print(f"  {Colors.YELLOW}  {msg}{Colors.RESET}")


def info(msg: str) -> None:
    """Print an informational message in blue."""
    print(f"  {Colors.BLUE}  {msg}{Colors.RESET}")


def dim(msg: str) -> None:
    """Print a subtle/secondary message in gray."""
    print(f"  {Colors.GRAY}{msg}{Colors.RESET}")


def pause() -> None:
    """Wait for the user to press Enter."""
    try:
        input(
            f"\n  {Colors.GRAY}Press Enter to continue..."
            f"{Colors.RESET}"
        )
    except EOFError:
        pass


# ── Banner — sober, national branding ─────────────────────────────────────────

def show_banner() -> None:
    """Display the EpiAlert startup banner.

    Layout:
        1. BURKINA FASO (bold, white, centred)
        2. National motto in French, then English
        3. EpiAlert name, tagline, slogan
        4. Ministry of Health + key surveillance partners
        5. Version and date
    """
    clear_screen()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Top rule
    print(f"\n  {Colors.WHITE}{_rule('=')}{Colors.RESET}")

    # Country name — centred, bold, white
    print(
        f"  {Colors.BOLD}{Colors.WHITE}"
        f"{_center('BURKINA FASO')}{Colors.RESET}"
    )

    # National motto
    print(
        f"  {Colors.WHITE}{_center(MOTTO_FR)}{Colors.RESET}"
    )
    print(
        f"  {Colors.GRAY}{_center(MOTTO_EN)}{Colors.RESET}"
    )

    print(f"  {Colors.WHITE}{_rule('-')}{Colors.RESET}")

    # App name — centred, bold, cyan
    print(
        f"  {Colors.BOLD}{Colors.CYAN}"
        f"{_center(APP_NAME)}{Colors.RESET}"
    )

    # Tagline
    print(
        f"  {Colors.WHITE}{_center(APP_TAGLINE)}{Colors.RESET}"
    )

    # Slogan
    print(
        f"  {Colors.GRAY}{_center(APP_SLOGAN)}{Colors.RESET}"
    )

    print(f"  {Colors.CYAN}{_rule('-')}{Colors.RESET}")

    # Institutional partners — key ones in the banner
    print(
        f"  {Colors.GRAY}{_center('In Partnership With')}"
        f"{Colors.RESET}"
    )
    # Show first 6 key partners in the banner
    key_partners = INSTITUTIONS[:6]
    for name, _abbrev in key_partners:
        print(
            f"  {Colors.WHITE}{_center(name)}{Colors.RESET}"
        )
    dim(
        f"  ... and {len(INSTITUTIONS) - 6} more partners"
    )

    # Version and date
    print(f"  {Colors.CYAN}{_rule('-')}{Colors.RESET}")
    print(
        f"  {Colors.GRAY}{_center(f'v{APP_VERSION}  |  {now}')}"
        f"{Colors.RESET}"
    )

    # Bottom rule
    print(f"  {Colors.WHITE}{_rule('=')}{Colors.RESET}")


# ── Colour legend ─────────────────────────────────────────────────────────────

def show_legend() -> None:
    """Display the colour legend for diseases, statuses, and alerts.

    Gives users a quick visual reference so they can read tables and
    alerts at a glance without guessing what each colour means.
    """
    header("Color Legend")

    # -- Status colours --
    print(f"\n  {Colors.BOLD}PATIENT STATUS{Colors.RESET}")
    print(f"  {Colors.CYAN}{_rule('.')}{Colors.RESET}")
    for status in PATIENT_STATUSES:
        color = STATUS_COLORS.get(status, Colors.WHITE)
        icon = STATUS_ICONS.get(status, "?")
        label = STATUS_LABELS.get(status, "")
        print(
            f"    {color}{Colors.BOLD}{icon}{Colors.RESET}"
            f"  {color}{status}{Colors.RESET}"
        )
        print(
            f"       {Colors.GRAY}{label}{Colors.RESET}"
        )

    # -- Severity colours --
    print(f"\n  {Colors.BOLD}ALERT SEVERITY{Colors.RESET}")
    print(f"  {Colors.CYAN}{_rule('.')}{Colors.RESET}")
    for level in ("Warning", "Critical", "Emergency"):
        color = SEVERITY_COLORS.get(level, Colors.WHITE)
        icon = SEVERITY_ICONS.get(level, "")
        label = SEVERITY_LABELS.get(level, "")
        print(
            f"    {color}{Colors.BOLD}{icon}{Colors.RESET}"
            f"  {color}{level}{Colors.RESET}"
        )
        print(
            f"       {Colors.GRAY}{label}{Colors.RESET}"
        )

    # -- Disease colours --
    print(f"\n  {Colors.BOLD}DISEASE CODING{Colors.RESET}")
    print(f"  {Colors.CYAN}{_rule('.')}{Colors.RESET}")
    for disease, color in DISEASE_COLORS.items():
        label = DISEASE_LEGEND.get(disease, "")
        threshold = DISEASE_THRESHOLDS.get(disease, 0)
        print(
            f"    {color}{Colors.BOLD}*{Colors.RESET}"
            f"  {color}{disease}{Colors.RESET}"
        )
        print(
            f"       {Colors.GRAY}{label}{Colors.RESET}"
        )
        print(
            f"       {Colors.DIM}Alert threshold:"
            f" {threshold} confirmed cases{Colors.RESET}"
        )

    # -- Interface colours --
    print(f"\n  {Colors.BOLD}INTERFACE COLORS{Colors.RESET}")
    print(f"  {Colors.CYAN}{_rule('.')}{Colors.RESET}")
    print(
        f"    {Colors.CYAN}---{Colors.RESET}"
        f"  Section headers / structure"
    )
    print(
        f"    {Colors.WHITE}---{Colors.RESET}"
        f"  Data values / content"
    )
    print(
        f"    {Colors.GRAY}---{Colors.RESET}"
        f"  Hints / secondary info"
    )
    print(
        f"    {Colors.BLUE}---{Colors.RESET}"
        f"  Sub-headers / info messages"
    )
    print(
        f"    {Colors.GREEN}---{Colors.RESET}"
        f"  Success / recovered"
    )
    print(
        f"    {Colors.YELLOW}---{Colors.RESET}"
        f"  Warning / suspected"
    )
    print(
        f"    {Colors.RED}---{Colors.RESET}"
        f"  Error / critical / confirmed"
    )
    print(
        f"    {Colors.MAGENTA}---{Colors.RESET}"
        f"  Emergency / emerging"
    )

    pause()


# ── Menu display — role-specific ──────────────────────────────────────────────

def show_health_menu() -> None:
    """Display the Health Agent menu (data entry only)."""
    print(
        f"\n  {Colors.GREEN}{Colors.BOLD}"
        f"HEALTH AGENT MENU{Colors.RESET}"
    )
    print(
        f"  {Colors.GREEN}{_rule('.')}{Colors.RESET}"
    )
    for i, label in enumerate(HEALTH_MENU, start=1):
        print(
            f"  {Colors.GREEN}{i:2d}.{Colors.RESET}"
            f"  {Colors.WHITE}{label}{Colors.RESET}"
        )
    print(f"  {Colors.GRAY}{_rule('.')}{Colors.RESET}")


def show_dept_menu() -> None:
    """Display the Department Agent menu (consultation & analysis)."""
    print(
        f"\n  {Colors.BLUE}{Colors.BOLD}"
        f"DEPARTMENT AGENT MENU{Colors.RESET}"
    )
    print(
        f"  {Colors.BLUE}{_rule('.')}{Colors.RESET}"
    )
    for i, label in enumerate(DEPT_MENU, start=1):
        print(
            f"  {Colors.BLUE}{i:2d}.{Colors.RESET}"
            f"  {Colors.WHITE}{label}{Colors.RESET}"
        )
    print(f"  {Colors.GRAY}{_rule('.')}{Colors.RESET}")


def choose(min_v: int, max_v: int) -> int:
    """Prompt the user for a numeric choice within a range.

    Never crashes — non-numeric and out-of-range inputs are caught
    and the user is asked again.

    Args:
        min_v: Minimum valid value.
        max_v: Maximum valid value.

    Returns:
        The validated integer choice.
    """
    while True:
        try:
            raw = input(
                f"  {Colors.WHITE}Choice ({min_v}-{max_v}): "
                f"{Colors.RESET}"
            )
            val = int(raw)
            if min_v <= val <= max_v:
                return val
            err(f"Enter a number between {min_v} and {max_v}.")
        except ValueError:
            err("Invalid input - please enter a number.")
        except EOFError:
            return max_v


def confirm(prompt: str) -> bool:
    """Ask a yes/no question.

    Args:
        prompt: The question to display.

    Returns:
        True if the user answered yes, False otherwise.
    """
    while True:
        raw = input(
            f"  {Colors.YELLOW}{prompt} (y/n): {Colors.RESET}"
        ).strip().lower()
        if raw in ("y", "yes"):
            return True
        if raw in ("n", "no"):
            return False
        err("Enter 'y' or 'n'.")


# ── Numbered selection helpers ────────────────────────────────────────────────

def pick(options: list[str], title: str) -> str:
    """Display a numbered list and let the user pick one option.

    Args:
        options: Items to choose from.
        title:   Prompt displayed above the list.

    Returns:
        The selected option string, or "" if cancelled.
    """
    sub(title)
    for i, opt in enumerate(options, start=1):
        print(
            f"    {Colors.CYAN}{i:3d}.{Colors.RESET}  {opt}"
        )
    print(f"    {Colors.GRAY}  0.  Cancel{Colors.RESET}")

    while True:
        try:
            raw = input(
                f"  {Colors.WHITE}Select (0-{len(options)}): "
                f"{Colors.RESET}"
            )
            idx = int(raw)
            if idx == 0:
                return ""
            if 1 <= idx <= len(options):
                return options[idx - 1]
            err(
                f"Enter a number between 0 and {len(options)}."
            )
        except ValueError:
            err("Invalid input - please enter a number.")
        except EOFError:
            return ""


def pick_region() -> str:
    """Let the user select a region from the 13 regions."""
    return pick(list(REGIONS.keys()), "Select a Region")


def pick_province(region: str) -> str:
    """Let the user select a province within a region.

    Args:
        region: Parent region name.

    Returns:
        The selected province, or "" if cancelled.
    """
    provs = PROVINCES.get(region, [])
    if not provs:
        err(f"No provinces found for {region}.")
        return ""
    return pick(provs, f"Provinces in {region}")


def pick_commune(province: str) -> str:
    """Let the user select a commune within a province.

    Args:
        province: Parent province name.

    Returns:
        The selected commune, or "" if cancelled.
    """
    coms = COMMUNES.get(province, [])
    if not coms:
        err(f"No communes found for {province}.")
        return ""
    return pick(coms, f"Communes in {province}")


def pick_disease() -> str:
    """Let the user select a disease from the monitored list."""
    return pick(list(DISEASE_NAMES), "Select a Disease")


def pick_status() -> str:
    """Let the user select a patient status."""
    return pick(list(PATIENT_STATUSES), "Select Status")


def pick_gender() -> str:
    """Let the user select a gender.  Returns "M" or "F"."""
    labels = [
        f"{g} - {'Male' if g == 'M' else 'Female'}"
        for g in VALID_GENDERS
    ]
    result = pick(labels, "Select Gender")
    return result[0] if result else ""


def pick_facility(region: str) -> str:
    """Let the user select a health facility in a region.

    Args:
        region: Region name.

    Returns:
        The selected facility name, or "" if cancelled.
    """
    facs = HEALTH_FACILITIES.get(region, [])
    if not facs:
        err(f"No facilities found for {region}.")
        return ""
    return pick(facs, f"Health Facilities in {region}")


def pick_or_enter(
    options: list[str], title: str, field_name: str = "value"
) -> str:
    """Display a numbered list with an option to enter a custom value.

    This is used when the user can either pick from existing entries
    or type in a new one (e.g. a new locality or department).

    Args:
        options:    Items to choose from.
        title:      Prompt displayed above the list.
        field_name: Name of the field for the custom input prompt.

    Returns:
        The selected option string, the custom entry, or "" if
        cancelled.
    """
    sub(title)
    for i, opt in enumerate(options, start=1):
        print(
            f"    {Colors.CYAN}{i:3d}.{Colors.RESET}  {opt}"
        )
    n = len(options) + 1
    print(
        f"    {Colors.YELLOW}{n:3d}.{Colors.RESET}"
        f"  Enter a new {field_name}..."
    )
    print(f"    {Colors.GRAY}  0.  Cancel{Colors.RESET}")

    while True:
        try:
            raw = input(
                f"  {Colors.WHITE}Select (0-{n}): "
                f"{Colors.RESET}"
            )
            idx = int(raw)
            if idx == 0:
                return ""
            if 1 <= idx <= len(options):
                return options[idx - 1]
            if idx == n:
                custom = read_str(
                    f"Enter {field_name}"
                )
                return custom if custom else ""
            err(f"Enter a number between 0 and {n}.")
        except ValueError:
            err("Invalid input - please enter a number.")
        except EOFError:
            return ""


# ── Free-text input helpers ───────────────────────────────────────────────────

def read_str(prompt: str, min_len: int = 1) -> str:
    """Read a non-empty string from the user.

    Args:
        prompt:  Prompt text.
        min_len: Minimum accepted length.

    Returns:
        The validated string.
    """
    while True:
        try:
            raw = input(
                f"  {Colors.WHITE}{prompt}: {Colors.RESET}"
            ).strip()
            if len(raw) >= min_len:
                return raw
            err(f"At least {min_len} character(s) required.")
        except EOFError:
            return ""


def read_int(
    prompt: str, lo: int = 0, hi: int = 150
) -> int:
    """Read an integer within a range from the user.

    Args:
        prompt: Prompt text.
        lo:     Minimum accepted value.
        hi:     Maximum accepted value.

    Returns:
        The validated integer.
    """
    while True:
        try:
            raw = input(
                f"  {Colors.WHITE}{prompt}: {Colors.RESET}"
            )
            val = int(raw)
            if lo <= val <= hi:
                return val
            err(f"Enter a number between {lo} and {hi}.")
        except ValueError:
            err("Invalid input - please enter a whole number.")
        except EOFError:
            return 0


def read_date(prompt: str) -> str:
    """Read a date in YYYY-MM-DD format.

    Pressing Enter without typing defaults to right now (with time).

    Args:
        prompt: Prompt text.

    Returns:
        A validated date string, including time if auto-filled.
    """
    while True:
        try:
            raw = input(
                f"  {Colors.WHITE}{prompt}"
                f" (YYYY-MM-DD, Enter = now): {Colors.RESET}"
            ).strip()
            if raw == "":
                # Auto-fill with current date AND time
                return datetime.now().strftime("%Y-%m-%d %H:%M")
            datetime.strptime(raw, "%Y-%m-%d")
            return raw
        except ValueError:
            err("Invalid format - use YYYY-MM-DD.")


# ── Data display — patient cards, tables, alerts ──────────────────────────────

def show_patient(p: Patient) -> None:
    """Display a single patient as a styled card with colour coding.

    The disease name is coloured according to DISEASE_COLORS and the
    status is coloured according to STATUS_COLORS.

    Args:
        p: The Patient to display.
    """
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
    """Display a compact table of patients with colour coding.

    Disease and status columns are coloured according to the
    DISEASE_COLORS and STATUS_COLORS mappings.

    Args:
        patients: List of Patient objects.
    """
    if not patients:
        info("No patients found.")
        return

    print(
        f"\n  {Colors.BOLD}"
        f"{'ID':<5} {'Name':<22} {'Disease':<28}"
        f" {'Status':<11} {'Region'}{Colors.RESET}"
    )
    print(f"  {Colors.GRAY}{_rule('.')}{Colors.RESET}")

    for p in patients:
        icon = STATUS_ICONS.get(p.get_status(), "?")
        name = f"{p.first_name} {p.last_name}"[:21]
        disease_color = p.get_disease_color()
        status_color = p.get_status_color()
        dis_colored = (
            f"{disease_color}{p.disease[:27]}{Colors.RESET}"
        )
        status_colored = (
            f"{status_color}{icon} {p.get_status()[:9]}"
            f"{Colors.RESET}"
        )
        print(
            f"  {p.patient_id:<5} {name:<22}"
            f" {dis_colored:<28} {status_colored:<11}"
            f" {p.region}"
        )

    print(f"  {Colors.GRAY}{_rule('.')}{Colors.RESET}")
    dim(f"  Total: {len(patients)} patient(s)")


def show_alert(a: Alert) -> None:
    """Display a single alert with severity colouring.

    Args:
        a: The Alert to display.
    """
    c = a.get_severity_color()
    sev_icon = SEVERITY_ICONS.get(a.severity, "")
    state = (
        f"{Colors.GREEN}ACTIVE{Colors.RESET}"
        if a.is_active()
        else f"{Colors.GRAY}RESOLVED{Colors.RESET}"
    )
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
    """Display a list of alerts with a severity summary.

    Args:
        alerts: List of Alert objects.
    """
    if not alerts:
        info("No alerts to display.")
        return
    for a in alerts:
        show_alert(a)
    wc = sum(1 for a in alerts if a.severity == "Warning")
    cc = sum(1 for a in alerts if a.severity == "Critical")
    ec = sum(1 for a in alerts if a.severity == "Emergency")
    print(
        f"\n  {Colors.YELLOW}Warning: {wc}{Colors.RESET}"
        f"  |  {Colors.RED}Critical: {cc}{Colors.RESET}"
        f"  |  {Colors.MAGENTA}Emergency: {ec}{Colors.RESET}"
    )


def show_case_table(cases: list[DiseaseCase]) -> None:
    """Display disease case records in a table with disease colours.

    Args:
        cases: List of DiseaseCase objects.
    """
    if not cases:
        info("No disease cases found.")
        return

    print(
        f"\n  {Colors.BOLD}"
        f"{'ID':<4} {'Disease':<28} {'Location':<28}"
        f" {'S':>3} {'C':>3} {'R':>3} {'D':>3}"
        f" {'Tot':>4}{Colors.RESET}"
    )
    print(f"  {Colors.GRAY}{_rule('.')}{Colors.RESET}")
    dim("  S=Suspected  C=Confirmed  R=Recovered  D=Deceased")

    for c in cases:
        loc = f"{c.region}/{c.province}/{c.commune}"[:27]
        dis_color = c.get_disease_color()
        print(
            f"  {c.case_id:<4}"
            f" {dis_color}{c.disease[:27]}{Colors.RESET}"
            f" {loc:<28} {c.suspected:>3} {c.confirmed:>3}"
            f" {c.recovered:>3} {c.deceased:>3}"
            f" {c.get_total_cases():>4}"
        )

    print(f"  {Colors.GRAY}{_rule('.')}{Colors.RESET}")
    dim(f"  Total: {len(cases)} record(s)")


def show_report(text: str) -> None:
    """Display a generated report.

    Args:
        text: The report string.
    """
    print(f"\n{Colors.WHITE}{text}{Colors.RESET}")


# ── Login screen — enhanced role selection ────────────────────────────────────

def login() -> Agent:
    """Display the login screen and return the chosen agent.

    The user picks a role (Health Agent or Department Agent), enters
    their name, selects a region, and optionally a health facility.
    Each role has a different set of parameters — they are not
    interchangeable.

    Returns:
        A HealthAgent or DepartmentAgent instance.
    """
    show_banner()
    header("Welcome to EpiAlert")

    # -- Role selection with descriptions --
    print(
        f"\n  {Colors.WHITE}Select your role:{Colors.RESET}"
    )
    print(f"  {Colors.CYAN}{_rule('.')}{Colors.RESET}")
    for i, role in enumerate(AGENT_ROLES, start=1):
        desc = ROLE_DESCRIPTIONS.get(role, "")
        if role == "Health Agent":
            color = Colors.GREEN
        else:
            color = Colors.BLUE
        print(
            f"  {color}{i}.{Colors.RESET}"
            f"  {Colors.BOLD}{role}{Colors.RESET}"
        )
        print(
            f"      {Colors.GRAY}{desc}{Colors.RESET}"
        )
    print(f"  {Colors.CYAN}{_rule('.')}{Colors.RESET}")

    role_idx = choose(1, len(AGENT_ROLES))

    # -- Name --
    name = read_str("Your name")
    if not name:
        name = "Guest"

    # -- Region selection (both roles need a region) --
    region = pick_region()
    if not region:
        region = "Centre"

    # -- Health facility selection --
    facility = pick_facility(region)

    # -- Create the agent based on role --
    if role_idx == 1:
        # Health Agent: region + facility + province + commune
        province = pick_province(region)
        commune = (
            pick_commune(province) if province else ""
        )
        return HealthAgent(
            name,
            f"HA-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            region,
            province,
            commune,
            facility,
        )
    else:
        # Department Agent: department + supervision level
        dept = read_str("Department name")
        if not dept:
            dept = "Epidemiology"
        print(
            f"\n  {Colors.WHITE}Supervision level:{Colors.RESET}"
        )
        print(
            f"  {Colors.BLUE}1.{Colors.RESET}  Regional"
        )
        print(
            f"  {Colors.BLUE}2.{Colors.RESET}  National"
        )
        lvl_idx = choose(1, 2)
        supervision = (
            "regional" if lvl_idx == 1 else "national"
        )
        return DepartmentAgent(
            name,
            f"DA-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            dept,
            region,
            "",
            facility,
            supervision,
        )
