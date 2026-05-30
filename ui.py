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

from __future__ import annotations

import os
from datetime import datetime
from functools import lru_cache
from typing import Optional  # noqa: F401 — kept for type hints

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
    INSTITUTION_CATEGORIES,
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

__all__: list[str] = [
    "clear_screen",
    "header",
    "sub",
    "ok",
    "err",
    "warn",
    "info",
    "dim",
    "pause",
    "show_banner",
    "show_legend",
    "show_institutions",
    "show_health_menu",
    "show_dept_menu",
    "choose",
    "confirm",
    "pick",
    "pick_region",
    "pick_province",
    "pick_commune",
    "pick_disease",
    "pick_status",
    "pick_gender",
    "pick_facility",
    "pick_or_enter",
    "read_str",
    "read_int",
    "read_date",
    "show_patient",
    "show_patient_table",
    "show_alert",
    "show_alert_list",
    "show_case_table",
    "show_report",
    "login",
]


# Drawing helpers

_W: int = 60  # standard line width


def clear_screen() -> None:
    """Clear the terminal (Windows and Unix)."""
    os.system("cls" if os.name == "nt" else "clear")


# Pre-compute horizontal rules of common characters so we never rebuild
# the same string on every call.  The lru_cache avoids allocating a new
# string each time _rule("-") is invoked inside a tight loop.
@lru_cache(maxsize=8)
def _rule(char: str = "-") -> str:
    """Return a horizontal rule of width _W.

    Args:
        char: Single character to repeat.  Defaults to '-'.

    Returns:
        A string of length _W consisting of *char* repeated.
    """
    return char * _W


def _center(text: str, width: int = _W) -> str:
    """Center-align text within a given width.

    Args:
        text:  The string to centre.
        width: Total line width.  Defaults to _W (60).

    Returns:
        The centred string.
    """
    return text.center(width)


# Message shortcuts

def header(text: str) -> None:
    """Print a section header between thin rules.

    Args:
        text: Header title (cyan, bold, uppercase).
    """
    rule = _rule("-")
    print(f"\n  {Colors.CYAN}{rule}{Colors.RESET}")
    print(
        f"  {Colors.CYAN}{Colors.BOLD}{text.upper()}{Colors.RESET}"
    )
    print(f"  {Colors.CYAN}{rule}{Colors.RESET}")


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
    """Print a success message in green.

    Args:
        msg: The message text.
    """
    print(f"  {Colors.GREEN}  {msg}{Colors.RESET}")


def err(msg: str) -> None:
    """Print an error message in red.

    Args:
        msg: The message text.
    """
    print(f"  {Colors.RED}  {msg}{Colors.RESET}")


def warn(msg: str) -> None:
    """Print a warning message in yellow.

    Args:
        msg: The message text.
    """
    print(f"  {Colors.YELLOW}  {msg}{Colors.RESET}")


def info(msg: str) -> None:
    """Print an informational message in blue.

    Args:
        msg: The message text.
    """
    print(f"  {Colors.BLUE}  {msg}{Colors.RESET}")


def dim(msg: str) -> None:
    """Print a subtle/secondary message in gray.

    Args:
        msg: The message text.
    """
    print(f"  {Colors.GRAY}{msg}{Colors.RESET}")


def pause() -> None:
    """Wait for the user to press Enter.

    Catches EOFError so the program does not crash when input is
    piped (e.g. during automated testing).
    """
    try:
        input(
            f"\n  {Colors.GRAY}Press Enter to continue..."
            f"{Colors.RESET}"
        )
    except EOFError:
        pass


# Banner — sober, national branding

# Number of key partners shown in the startup banner.  The rest are
# summarised as "... and N more partners".
_BANNER_PARTNER_COUNT: int = 6


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
    now: str = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Cache rule strings used multiple times in this function
    eq_rule = _rule("=")
    dash_rule = _rule("-")

    # Top rule
    print(f"\n  {Colors.WHITE}{eq_rule}{Colors.RESET}")

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

    print(f"  {Colors.WHITE}{dash_rule}{Colors.RESET}")

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

    print(f"  {Colors.CYAN}{dash_rule}{Colors.RESET}")

    # Institutional partners — key ones in the banner
    print(
        f"  {Colors.GRAY}{_center('In Partnership With')}"
        f"{Colors.RESET}"
    )
    # Show the first N key partners; the rest get a summary line
    key_partners = INSTITUTIONS[:_BANNER_PARTNER_COUNT]
    for name, _abbrev in key_partners:
        print(
            f"  {Colors.WHITE}{_center(name)}{Colors.RESET}"
        )
    remaining: int = len(INSTITUTIONS) - _BANNER_PARTNER_COUNT
    if remaining > 0:
        dim(
            f"  ... and {remaining} more partners"
        )

    # Version and date
    print(f"  {Colors.CYAN}{dash_rule}{Colors.RESET}")
    print(
        f"  {Colors.GRAY}{_center(f'v{APP_VERSION}  |  {now}')}"
        f"{Colors.RESET}"
    )

    # Bottom rule
    print(f"  {Colors.WHITE}{eq_rule}{Colors.RESET}")


# Colour legend

def show_legend() -> None:
    """Display the colour legend for diseases, statuses, and alerts.

    Gives users a quick visual reference so they can read tables and
    alerts at a glance without guessing what each colour means.
    """
    header("Color Legend")
    dot_rule = _rule(".")

    # Status colours
    print(f"\n  {Colors.BOLD}PATIENT STATUS{Colors.RESET}")
    print(f"  {Colors.CYAN}{dot_rule}{Colors.RESET}")
    for status in PATIENT_STATUSES:
        color: str = STATUS_COLORS.get(status, Colors.WHITE)
        icon: str = STATUS_ICONS.get(status, "?")
        label: str = STATUS_LABELS.get(status, "")
        print(
            f"    {color}{Colors.BOLD}{icon}{Colors.RESET}"
            f"  {color}{status}{Colors.RESET}"
        )
        print(
            f"       {Colors.GRAY}{label}{Colors.RESET}"
        )

    # Severity colours
    print(f"\n  {Colors.BOLD}ALERT SEVERITY{Colors.RESET}")
    print(f"  {Colors.CYAN}{dot_rule}{Colors.RESET}")
    for level in ("Warning", "Critical", "Emergency"):
        sev_color: str = SEVERITY_COLORS.get(level, Colors.WHITE)
        sev_icon: str = SEVERITY_ICONS.get(level, "")
        sev_label: str = SEVERITY_LABELS.get(level, "")
        print(
            f"    {sev_color}{Colors.BOLD}{sev_icon}{Colors.RESET}"
            f"  {sev_color}{level}{Colors.RESET}"
        )
        print(
            f"       {Colors.GRAY}{sev_label}{Colors.RESET}"
        )

    # Disease colours
    print(f"\n  {Colors.BOLD}DISEASE CODING{Colors.RESET}")
    print(f"  {Colors.CYAN}{dot_rule}{Colors.RESET}")
    for disease, dis_color in DISEASE_COLORS.items():
        dis_label: str = DISEASE_LEGEND.get(disease, "")
        threshold: int = DISEASE_THRESHOLDS.get(disease, 0)
        print(
            f"    {dis_color}{Colors.BOLD}*{Colors.RESET}"
            f"  {dis_color}{disease}{Colors.RESET}"
        )
        print(
            f"       {Colors.GRAY}{dis_label}{Colors.RESET}"
        )
        print(
            f"       {Colors.DIM}Alert threshold:"
            f" {threshold} confirmed cases{Colors.RESET}"
        )

    # Interface colours
    print(f"\n  {Colors.BOLD}INTERFACE COLORS{Colors.RESET}")
    print(f"  {Colors.CYAN}{dot_rule}{Colors.RESET}")
    interface_items: list[tuple[str, str, str]] = [
        (Colors.CYAN, "---", "Section headers / structure"),
        (Colors.WHITE, "---", "Data values / content"),
        (Colors.GRAY, "---", "Hints / secondary info"),
        (Colors.BLUE, "---", "Sub-headers / info messages"),
        (Colors.GREEN, "---", "Success / recovered"),
        (Colors.YELLOW, "---", "Warning / suspected"),
        (Colors.RED, "---", "Error / critical / confirmed"),
        (Colors.MAGENTA, "---", "Emergency / emerging"),
    ]
    for clr, sample, desc in interface_items:
        print(
            f"    {clr}{sample}{Colors.RESET}"
            f"  {desc}"
        )

    pause()


# Institutions display

# Human-readable headings for each category key in INSTITUTION_CATEGORIES.
# The keys must match exactly what config.py defines.
_CATEGORY_LABELS: dict[str, str] = {
    "Government": "Government & Public Health Institutions",
    "Research": "Research & Training Institutions",
    "International": "International Organisations",
    "NGO": "Non-Governmental Organisations",
}


def show_institutions() -> None:
    """Display institutional partners grouped by category.

    Iterates over INSTITUTION_CATEGORIES (from config) and prints each
    group under a labelled sub-header.  For every institution the full
    name is shown together with its abbreviation in parentheses.
    """
    header("Institutional Partners")

    for cat_key, members in INSTITUTION_CATEGORIES.items():
        # Look up a human-friendly heading; fall back to the key itself
        heading: str = _CATEGORY_LABELS.get(cat_key, cat_key)
        sub(heading)

        for name, abbrev in members:
            print(
                f"    {Colors.WHITE}{name}{Colors.RESET}"
                f"  {Colors.GRAY}({abbrev}){Colors.RESET}"
            )

        # Show how many institutions are in this category
        dim(f"    ({len(members)} institution(s) in this group)")

    # Summary total
    total: int = sum(
        len(members) for members in INSTITUTION_CATEGORIES.values()
    )
    print()
    ok(f"Total: {total} institutional partner(s)")
    pause()


# Menu display — role-specific

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
    # Build the prompt string once instead of on every loop iteration
    prompt_str: str = (
        f"  {Colors.WHITE}Choice ({min_v}-{max_v}): "
        f"{Colors.RESET}"
    )
    while True:
        try:
            raw: str = input(prompt_str)
            val: int = int(raw)
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
    prompt_str: str = (
        f"  {Colors.YELLOW}{prompt} (y/n): {Colors.RESET}"
    )
    while True:
        raw: str = input(prompt_str).strip().lower()
        if raw in ("y", "yes"):
            return True
        if raw in ("n", "no"):
            return False
        err("Enter 'y' or 'n'.")


# Numbered selection helpers

# Pre-compute lists that are rebuilt on every call to the original
# pick_region / pick_disease / pick_status functions.  Since REGIONS,
# DISEASE_NAMES, and PATIENT_STATUSES are constant at runtime, we can
# safely materialise them once at import time.
_REGION_LIST: list[str] = list(REGIONS.keys())
_DISEASE_LIST: list[str] = list(DISEASE_NAMES)
_STATUS_LIST: list[str] = list(PATIENT_STATUSES)

# Pre-build gender labels so pick_gender() does not reconstruct them
# on every invocation.
_GENDER_LABELS: list[str] = [
    f"{g} - {'Male' if g == 'M' else 'Female'}"
    for g in VALID_GENDERS
]


def pick(options: list[str], title: str) -> str:
    """Display a numbered list and let the user pick one option.

    Args:
        options: Items to choose from.
        title:   Prompt displayed above the list.

    Returns:
        The selected option string, or "" if cancelled.
    """
    sub(title)
    n: int = len(options)
    for i, opt in enumerate(options, start=1):
        print(
            f"    {Colors.CYAN}{i:3d}.{Colors.RESET}  {opt}"
        )
    print(f"    {Colors.GRAY}  0.  Cancel{Colors.RESET}")

    # Build the prompt once
    prompt_str: str = (
        f"  {Colors.WHITE}Select (0-{n}): {Colors.RESET}"
    )
    while True:
        try:
            raw: str = input(prompt_str)
            idx: int = int(raw)
            if idx == 0:
                return ""
            if 1 <= idx <= n:
                return options[idx - 1]
            err(f"Enter a number between 0 and {n}.")
        except ValueError:
            err("Invalid input - please enter a number.")
        except EOFError:
            return ""


def pick_region() -> str:
    """Let the user select a region from the 13 regions."""
    return pick(_REGION_LIST, "Select a Region")


def pick_province(region: str) -> str:
    """Let the user select a province within a region.

    Args:
        region: Parent region name.

    Returns:
        The selected province, or "" if cancelled.
    """
    provs: list[str] = PROVINCES.get(region, [])
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
    coms: list[str] = COMMUNES.get(province, [])
    if not coms:
        err(f"No communes found for {province}.")
        return ""
    return pick(coms, f"Communes in {province}")


def pick_disease() -> str:
    """Let the user select a disease from the monitored list."""
    return pick(_DISEASE_LIST, "Select a Disease")


def pick_status() -> str:
    """Let the user select a patient status."""
    return pick(_STATUS_LIST, "Select Status")


def pick_gender() -> str:
    """Let the user select a gender.  Returns "M" or "F"."""
    result: str = pick(_GENDER_LABELS, "Select Gender")
    return result[0] if result else ""


def pick_facility(region: str) -> str:
    """Let the user select a health facility in a region.

    Args:
        region: Region name.

    Returns:
        The selected facility name, or "" if cancelled.
    """
    facs: list[str] = HEALTH_FACILITIES.get(region, [])
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
    n: int = len(options) + 1
    print(
        f"    {Colors.YELLOW}{n:3d}.{Colors.RESET}"
        f"  Enter a new {field_name}..."
    )
    print(f"    {Colors.GRAY}  0.  Cancel{Colors.RESET}")

    # Build prompt once
    prompt_str: str = (
        f"  {Colors.WHITE}Select (0-{n}): {Colors.RESET}"
    )
    while True:
        try:
            raw: str = input(prompt_str)
            idx: int = int(raw)
            if idx == 0:
                return ""
            if 1 <= idx <= len(options):
                return options[idx - 1]
            if idx == n:
                custom: str = read_str(
                    f"Enter {field_name}"
                )
                return custom if custom else ""
            err(f"Enter a number between 0 and {n}.")
        except ValueError:
            err("Invalid input - please enter a number.")
        except EOFError:
            return ""


# Free-text input helpers

def read_str(prompt: str, min_len: int = 1) -> str:
    """Read a non-empty string from the user.

    Args:
        prompt:  Prompt text.
        min_len: Minimum accepted length.

    Returns:
        The validated string.
    """
    prompt_str: str = (
        f"  {Colors.WHITE}{prompt}: {Colors.RESET}"
    )
    while True:
        try:
            raw: str = input(prompt_str).strip()
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
    prompt_str: str = (
        f"  {Colors.WHITE}{prompt}: {Colors.RESET}"
    )
    while True:
        try:
            raw: str = input(prompt_str)
            val: int = int(raw)
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
    prompt_str: str = (
        f"  {Colors.WHITE}{prompt}"
        f" (YYYY-MM-DD, Enter = now): {Colors.RESET}"
    )
    while True:
        try:
            raw: str = input(prompt_str).strip()
            if raw == "":
                # Auto-fill with current date AND time
                return datetime.now().strftime("%Y-%m-%d %H:%M")
            datetime.strptime(raw, "%Y-%m-%d")
            return raw
        except ValueError:
            err("Invalid format - use YYYY-MM-DD.")


# Data display — patient cards, tables, alerts

def show_patient(p: Patient) -> None:
    """Display a single patient as a styled card with colour coding.

    The disease name is coloured according to DISEASE_COLORS and the
    status is coloured according to STATUS_COLORS.

    Args:
        p: The Patient to display.
    """
    icon: str = STATUS_ICONS.get(p.get_status(), "?")
    status_color: str = p.get_status_color()
    disease_color: str = p.get_disease_color()
    dash_rule = _rule("-")

    print(f"""
  {Colors.CYAN}{dash_rule}{Colors.RESET}
  {Colors.BOLD}Patient #{p.patient_id}{Colors.RESET}
  {Colors.CYAN}{dash_rule}{Colors.RESET}
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
  {Colors.CYAN}{dash_rule}{Colors.RESET}""")


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

    dot_rule = _rule(".")
    print(
        f"\n  {Colors.BOLD}"
        f"{'ID':<5} {'Name':<22} {'Disease':<28}"
        f" {'Status':<11} {'Region'}{Colors.RESET}"
    )
    print(f"  {Colors.GRAY}{dot_rule}{Colors.RESET}")

    for p in patients:
        icon: str = STATUS_ICONS.get(p.get_status(), "?")
        # Truncate name to fit column width
        name: str = f"{p.first_name} {p.last_name}"[:21]
        disease_color: str = p.get_disease_color()
        status_color: str = p.get_status_color()
        # Build coloured fragments once per row
        dis_colored: str = (
            f"{disease_color}{p.disease[:27]}{Colors.RESET}"
        )
        status_colored: str = (
            f"{status_color}{icon} {p.get_status()[:9]}"
            f"{Colors.RESET}"
        )
        print(
            f"  {p.patient_id:<5} {name:<22}"
            f" {dis_colored:<28} {status_colored:<11}"
            f" {p.region}"
        )

    print(f"  {Colors.GRAY}{dot_rule}{Colors.RESET}")
    dim(f"  Total: {len(patients)} patient(s)")


def show_alert(a: Alert) -> None:
    """Display a single alert with severity colouring.

    Args:
        a: The Alert to display.
    """
    c: str = a.get_severity_color()
    sev_icon: str = SEVERITY_ICONS.get(a.severity, "")
    # Build the state label once
    state: str = (
        f"{Colors.GREEN}ACTIVE{Colors.RESET}"
        if a.is_active()
        else f"{Colors.GRAY}RESOLVED{Colors.RESET}"
    )
    disease_color: str = DISEASE_COLORS.get(a.disease, Colors.WHITE)
    dash_rule = _rule("-")

    print(f"""
  {c}{dash_rule}{Colors.RESET}
  {c}{Colors.BOLD}[{sev_icon} {a.severity.upper()}]\
{Colors.RESET}  {disease_color}{a.disease}{Colors.RESET}
  Location   {a.get_location()}
  Cases      {a.case_count}  (threshold: {a.threshold})
  Status     {state}
  Date       {a.date_created}
  {a.message}
  {c}{dash_rule}{Colors.RESET}""")


def show_alert_list(alerts: list[Alert]) -> None:
    """Display a list of alerts with a severity summary.

    The summary line counts alerts at each severity level so the
    user can gauge the overall situation at a glance.

    Args:
        alerts: List of Alert objects.
    """
    if not alerts:
        info("No alerts to display.")
        return
    for a in alerts:
        show_alert(a)
    # Count by severity — single pass, O(n)
    wc: int = 0
    cc: int = 0
    ec: int = 0
    for a in alerts:
        if a.severity == "Warning":
            wc += 1
        elif a.severity == "Critical":
            cc += 1
        elif a.severity == "Emergency":
            ec += 1
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

    dot_rule = _rule(".")
    print(
        f"\n  {Colors.BOLD}"
        f"{'ID':<4} {'Disease':<28} {'Location':<28}"
        f" {'S':>3} {'C':>3} {'R':>3} {'D':>3}"
        f" {'Tot':>4}{Colors.RESET}"
    )
    print(f"  {Colors.GRAY}{dot_rule}{Colors.RESET}")
    dim("  S=Suspected  C=Confirmed  R=Recovered  D=Deceased")

    for c in cases:
        loc: str = f"{c.region}/{c.province}/{c.commune}"[:27]
        dis_color: str = c.get_disease_color()
        print(
            f"  {c.case_id:<4}"
            f" {dis_color}{c.disease[:27]}{Colors.RESET}"
            f" {loc:<28} {c.suspected:>3} {c.confirmed:>3}"
            f" {c.recovered:>3} {c.deceased:>3}"
            f" {c.get_total_cases():>4}"
        )

    print(f"  {Colors.GRAY}{dot_rule}{Colors.RESET}")
    dim(f"  Total: {len(cases)} record(s)")


def show_report(text: str) -> None:
    """Display a generated report.

    Args:
        text: The report string.
    """
    print(f"\n{Colors.WHITE}{text}{Colors.RESET}")


# Login screen — enhanced role selection

# Timestamp format used when generating agent IDs
_AGENT_ID_FMT: str = "%Y%m%d%H%M%S"

# Role-to-colour mapping for the login screen role list
_ROLE_COLORS: dict[str, str] = {
    "Health Agent": Colors.GREEN,
    "Department Agent": Colors.BLUE,
}


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

    # Role selection with descriptions
    print(
        f"\n  {Colors.WHITE}Select your role:{Colors.RESET}"
    )
    dot_rule = _rule(".")
    print(f"  {Colors.CYAN}{dot_rule}{Colors.RESET}")
    for i, role in enumerate(AGENT_ROLES, start=1):
        desc: str = ROLE_DESCRIPTIONS.get(role, "")
        color: str = _ROLE_COLORS.get(role, Colors.WHITE)
        print(
            f"  {color}{i}.{Colors.RESET}"
            f"  {Colors.BOLD}{role}{Colors.RESET}"
        )
        print(
            f"      {Colors.GRAY}{desc}{Colors.RESET}"
        )
    print(f"  {Colors.CYAN}{dot_rule}{Colors.RESET}")

    role_idx: int = choose(1, len(AGENT_ROLES))

    # Name
    name: str = read_str("Your name")
    if not name:
        name = "Guest"

    # Region selection (both roles need a region)
    region: str = pick_region()
    if not region:
        region = "Centre"

    # Health facility selection
    facility: str = pick_facility(region)

    # Create the agent based on role
    if role_idx == 1:
        # Health Agent: region + facility + province + commune
        province: str = pick_province(region)
        commune: str = (
            pick_commune(province) if province else ""
        )
        agent_id: str = f"HA-{datetime.now().strftime(_AGENT_ID_FMT)}"
        return HealthAgent(
            name,
            agent_id,
            region,
            province,
            commune,
            facility,
        )
    else:
        # Department Agent: department + supervision level
        dept: str = read_str("Department name")
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
        lvl_idx: int = choose(1, 2)
        supervision: str = (
            "regional" if lvl_idx == 1 else "national"
        )
        agent_id = f"DA-{datetime.now().strftime(_AGENT_ID_FMT)}"
        return DepartmentAgent(
            name,
            agent_id,
            dept,
            region,
            "",
            facility,
            supervision,
        )
