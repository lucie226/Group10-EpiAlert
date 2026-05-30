"""EpiAlert — main entry point.

This is where everything starts.  We initialise the data layer,
show the login screen, and drive the main menu loop.  Every
user-facing action is wrapped in try/except so the app never
crashes unexpectedly.

The two agent roles have strictly separated menus:

    Health Agent
        Register patients, search, update status, review own
        entries, and batch-register multiple patients at once.

    Department Agent
        View cases, detect epidemics, view alerts, generate /
        export reports, view analytics.

Run it with::

    python main.py
"""

from __future__ import annotations

import sys
from typing import Union

from config import APP_NAME, Colors, HEALTH_MENU, DEPT_MENU
from core import (
    Analytics,
    DataManager,
    EpidemicDetector,
    ReportEngine,
    ReportExporter,
)
from models import Agent, HealthAgent, DepartmentAgent, Patient
from ui import (
    choose,
    confirm,
    err,
    header,
    info,
    login,
    ok,
    pause,
    pick_commune,
    pick_disease,
    pick_facility,
    pick_gender,
    pick_province,
    pick_region,
    pick_status,
    read_date,
    read_int,
    read_str,
    show_banner,
    show_case_table,
    show_health_menu,
    show_dept_menu,
    show_legend,
    show_alert_list,
    show_patient,
    show_patient_table,
    show_report,
    warn,
)

# Public API — ``from main import *`` only exports these names.
__all__: list[str] = [
    "main",
    "do_register",
    "do_register_batch",
    "do_search",
    "do_update",
    "do_own_entries",
    "do_view_cases",
    "do_detect",
    "do_view_alerts",
    "do_report",
    "do_export",
    "do_analytics",
]


# Section: Health Agent actions — data entry only


def do_register(dm: DataManager, agent: Agent) -> None:
    """Walk the user through patient registration.

    Every field is collected step by step using numbered selections
    for region, province, commune, disease, and status.  The date
    auto-fills with the current timestamp when the user presses
    Enter.  The entered_by field records the health agent's ID.

    This is the single-patient version.  For registering several
    patients in one session see :func:`do_register_batch`.

    Args:
        dm:    The data manager instance.
        agent: The currently logged-in health agent.
    """
    header("Register New Patient")

    # Collect demographic fields — any blank entry cancels the operation
    first: str = read_str("First name")
    if not first:
        warn("Cancelled.")
        pause()
        return
    last: str = read_str("Last name")
    if not last:
        warn("Cancelled.")
        pause()
        return
    age: int = read_int("Age", 0, 150)
    gender: str = pick_gender()
    if not gender:
        warn("Cancelled.")
        pause()
        return
    disease: str = pick_disease()
    if not disease:
        warn("Cancelled.")
        pause()
        return
    status: str = pick_status()
    if not status:
        warn("Cancelled.")
        pause()
        return
    region: str = pick_region()
    if not region:
        warn("Cancelled.")
        pause()
        return
    province: str = pick_province(region)
    if not province:
        warn("Cancelled.")
        pause()
        return
    commune: str = pick_commune(province)
    if not commune:
        warn("Cancelled.")
        pause()
        return
    facility: str = pick_facility(region)
    if not facility:
        warn("Cancelled.")
        pause()
        return
    # Date auto-fills with current timestamp when the user presses Enter
    date: str = read_date("Date reported")

    p: Patient = Patient(
        0, first, last, age, gender, disease, status,
        region, province, commune, facility, date,
        agent.get_id(),
    )
    pid: int = dm.add_patient(p)
    if pid > 0:
        ok(f"Patient registered - ID: {pid}")
        show_patient(p)
    else:
        err("Failed to save patient record.")
    pause()


def do_register_batch(dm: DataManager, agent: Agent) -> None:
    """Register multiple patients in one interactive session.

    After each successful registration the user is asked
    "Add another? (y/n)".  The loop continues until the user
    answers "n" or cancels a field entry.  All patients are
    registered with the same agent ID.

    This is useful during field campaigns where a health agent
    needs to enter several patient records consecutively without
    navigating back to the main menu each time.

    Args:
        dm:    The data manager instance.
        agent: The currently logged-in health agent.
    """
    header("Batch Register Patients")
    count: int = 0

    while True:
        # Announce which patient we are on (1-based for display)
        count += 1
        info(f"--- Patient #{count} ---")

        # Collect demographic fields — same flow as do_register
        first: str = read_str("First name")
        if not first:
            warn("Cancelled this patient.")
            count -= 1
            break
        last: str = read_str("Last name")
        if not last:
            warn("Cancelled this patient.")
            count -= 1
            break
        age: int = read_int("Age", 0, 150)
        gender: str = pick_gender()
        if not gender:
            warn("Cancelled this patient.")
            count -= 1
            break
        disease: str = pick_disease()
        if not disease:
            warn("Cancelled this patient.")
            count -= 1
            break
        status: str = pick_status()
        if not status:
            warn("Cancelled this patient.")
            count -= 1
            break
        region: str = pick_region()
        if not region:
            warn("Cancelled this patient.")
            count -= 1
            break
        province: str = pick_province(region)
        if not province:
            warn("Cancelled this patient.")
            count -= 1
            break
        commune: str = pick_commune(province)
        if not commune:
            warn("Cancelled this patient.")
            count -= 1
            break
        facility: str = pick_facility(region)
        if not facility:
            warn("Cancelled this patient.")
            count -= 1
            break
        # Date auto-fills with current timestamp
        date: str = read_date("Date reported")

        p: Patient = Patient(
            0, first, last, age, gender, disease, status,
            region, province, commune, facility, date,
            agent.get_id(),
        )
        pid: int = dm.add_patient(p)
        if pid > 0:
            ok(f"Patient registered - ID: {pid}")
            show_patient(p)
        else:
            err("Failed to save patient record.")
            count -= 1

        # Ask whether to continue — this is the core batch mechanism
        if not confirm("Add another patient?"):
            break

    # Summary of the batch session
    if count > 0:
        ok(f"Batch complete: {count} patient(s) registered.")
    else:
        info("No patients were registered.")
    pause()


def do_search(dm: DataManager, agent: Agent) -> None:
    """Search for a patient by ID or free text.

    Args:
        dm:    The data manager instance.
        agent: The currently logged-in health agent.
    """
    header("Search Patient")
    print(f"  {Colors.CYAN}1.{Colors.RESET}  By ID")
    print(
        f"  {Colors.CYAN}2.{Colors.RESET}"
        f"  By name / disease / region"
    )
    c: int = choose(1, 2)
    if c == 1:
        pid: int = read_int("Patient ID", 1, 99999)
        p: Union[Patient, None] = dm.find_patient_by_id(pid)
        if p:
            show_patient(p)
        else:
            err(f"No patient with ID {pid}.")
    else:
        q: str = read_str("Search term")
        if not q:
            warn("Cancelled.")
            pause()
            return
        results: list[Patient] = dm.search_patients(q)
        if results:
            ok(f"Found {len(results)} match(es):")
            show_patient_table(results)
        else:
            info(f"No results for '{q}'.")
    pause()


def do_update(dm: DataManager, agent: Agent) -> None:
    """Prompt the user to update a patient's status.

    Only the health agent who originally entered the record should
    update it, but we allow any health agent to update for
    operational flexibility.

    Args:
        dm:    The data manager instance.
        agent: The currently logged-in health agent.
    """
    header("Update Patient Status")
    pid: int = read_int("Patient ID", 1, 99999)
    p: Union[Patient, None] = dm.find_patient_by_id(pid)
    if not p:
        err(f"No patient with ID {pid}.")
        pause()
        return
    show_patient(p)
    new: str = pick_status()
    if not new:
        warn("Cancelled.")
        pause()
        return
    if confirm(
        f"Change status from '{p.get_status()}' to '{new}'?"
    ):
        if dm.update_patient_status(pid, new):
            ok("Status updated.")
            updated: Union[Patient, None] = dm.find_patient_by_id(pid)
            if updated:
                show_patient(updated)
        else:
            err("Update failed.")
    else:
        info("Cancelled.")
    pause()


def do_own_entries(dm: DataManager, agent: Agent) -> None:
    """Show all patients entered by the currently logged-in agent.

    This lets health agents review their own work.

    Args:
        dm:    The data manager instance.
        agent: The currently logged-in health agent.
    """
    header("My Entries")
    entries: list[Patient] = dm.get_entries_by_agent(agent.get_id())
    if entries:
        ok(
            f"You have entered {len(entries)} patient(s):"
        )
        show_patient_table(entries)
    else:
        info("You have not entered any patients yet.")
    pause()


# Section: Department Agent actions — consultation and analysis only


def do_view_cases(dm: DataManager, agent: Agent) -> None:
    """View disease cases filtered by region, disease, or all.

    Args:
        dm:    The data manager instance.
        agent: The currently logged-in department agent.
    """
    header("View Disease Cases")
    print(f"  {Colors.CYAN}1.{Colors.RESET}  By region")
    print(f"  {Colors.CYAN}2.{Colors.RESET}  By disease")
    print(f"  {Colors.CYAN}3.{Colors.RESET}  All cases")
    c: int = choose(1, 3)
    if c == 1:
        r: str = pick_region()
        if not r:
            warn("Cancelled.")
            pause()
            return
        show_case_table(dm.get_cases_by_region(r))
    elif c == 2:
        d: str = pick_disease()
        if not d:
            warn("Cancelled.")
            pause()
            return
        show_case_table(dm.get_cases_by_disease(d))
    else:
        show_case_table(dm.cases)
    pause()


def do_detect(dm: DataManager, agent: Agent) -> None:
    """Run the epidemic detection engine on a region or nationwide.

    Args:
        dm:    The data manager instance.
        agent: The currently logged-in department agent.
    """
    header("Epidemic Detection")
    print(
        f"  {Colors.CYAN}1.{Colors.RESET}  Specific region"
    )
    print(
        f"  {Colors.CYAN}2.{Colors.RESET}  Nationwide scan"
    )
    c: int = choose(1, 2)
    det: EpidemicDetector = EpidemicDetector(dm)
    alerts: list = []
    if c == 1:
        r: str = pick_region()
        if not r:
            warn("Cancelled.")
            pause()
            return
        info(f"Scanning {r}...")
        alerts = det.detect_by_region(r)
    else:
        info("Scanning all regions...")
        alerts = det.detect_all_regions()
    if alerts:
        warn(f"{len(alerts)} new alert(s) detected!")
        show_alert_list(alerts)
    else:
        ok("All zones within thresholds - no new alerts.")
    pause()


def do_view_alerts(dm: DataManager, agent: Agent) -> None:
    """Display all currently active epidemiological alerts.

    Args:
        dm:    The data manager instance.
        agent: The currently logged-in department agent.
    """
    header("Active Alerts")
    active: list = dm.get_active_alerts()
    if active:
        warn(f"{len(active)} active alert(s):")
        show_alert_list(active)
    else:
        ok("No active alerts at this time.")
    pause()


def do_report(dm: DataManager, agent: Agent) -> None:
    """Generate and display a zone, regional, or national report.

    Args:
        dm:    The data manager instance.
        agent: The currently logged-in department agent.
    """
    header("Generate Report")
    print(f"  {Colors.CYAN}1.{Colors.RESET}  Zone level")
    print(
        f"  {Colors.CYAN}2.{Colors.RESET}  Regional level"
    )
    print(
        f"  {Colors.CYAN}3.{Colors.RESET}  National level"
    )
    c: int = choose(1, 3)
    eng: ReportEngine = ReportEngine(dm)
    if c == 1:
        r: str = pick_region()
        if not r:
            warn("Cancelled.")
            pause()
            return
        p: str = pick_province(r)
        if not p:
            warn("Cancelled.")
            pause()
            return
        cm: str = pick_commune(p)
        if not cm:
            warn("Cancelled.")
            pause()
            return
        show_report(eng.generate_zone_report(r, p, cm))
    elif c == 2:
        r = pick_region()
        if not r:
            warn("Cancelled.")
            pause()
            return
        show_report(eng.generate_region_report(r))
    else:
        show_report(eng.generate_national_report())
    pause()


def do_export(dm: DataManager, agent: Agent) -> None:
    """Export a report to .txt and .md files.

    Both a .txt (plain text) and a .md (Markdown) version are
    generated.  The .md version is professionally formatted with
    tables for health professionals.  Every export is auto-filed
    into the classeurs/ directory tree for safe archiving.

    Args:
        dm:    The data manager instance.
        agent: The currently logged-in department agent.
    """
    header("Export Report")
    print(f"  {Colors.CYAN}1.{Colors.RESET}  Zone level")
    print(
        f"  {Colors.CYAN}2.{Colors.RESET}  Regional level"
    )
    print(
        f"  {Colors.CYAN}3.{Colors.RESET}  National level"
    )
    c: int = choose(1, 3)
    exp: ReportExporter = ReportExporter(dm)
    txt_path: str = ""
    md_path: str = ""
    if c == 1:
        r: str = pick_region()
        if not r:
            warn("Cancelled.")
            pause()
            return
        p: str = pick_province(r)
        if not p:
            warn("Cancelled.")
            pause()
            return
        cm: str = pick_commune(p)
        if not cm:
            warn("Cancelled.")
            pause()
            return
        txt_path = exp.export_zone_report(r, p, cm)
        md_path = exp.export_zone_md(r, p, cm)
    elif c == 2:
        r = pick_region()
        if not r:
            warn("Cancelled.")
            pause()
            return
        txt_path = exp.export_region_report(r)
        md_path = exp.export_region_md(r)
    else:
        txt_path = exp.export_national_report()
        md_path = exp.export_national_md()
    if txt_path:
        ok(f"TXT report saved to: {txt_path}")
    else:
        err("TXT export failed.")
    if md_path:
        ok(f"MD report saved to:  {md_path}")
    else:
        err("MD export failed.")
    if txt_path or md_path:
        info("Archived copy filed in outputs/classeurs/")
    pause()


def do_analytics(dm: DataManager, agent: Agent) -> None:
    """Display the text-based analytics dashboard.

    Args:
        dm:    The data manager instance.
        agent: The currently logged-in department agent.
    """
    header("Analytics Dashboard")
    show_report(Analytics(dm).generate_dashboard())
    pause()


# Section: Dispatch tables — role-specific

# Each entry maps a menu choice number to a (handler, permission) tuple.
# The handler is the function to call; the permission string must appear
# in the agent's permission set for the action to be allowed.
_HEALTH_HANDLERS: dict[int, tuple] = {
    1: (do_register, "register_patient"),
    2: (do_search, "search_patient"),
    3: (do_update, "update_status"),
    4: (do_own_entries, "view_own_entries"),
    # Note: do_register_batch is available but not yet wired
    # into the HEALTH_MENU.  To activate it, add a menu label
    # in config.py HEALTH_MENU and an entry here, e.g.:
    #   5: (do_register_batch, "register_patient"),
    # Menu items for Legend and Exit are handled separately
    # inside _handle_health_agent(), not via this dispatch table.
}

_DEPT_HANDLERS: dict[int, tuple] = {
    1: (do_view_cases, "view_cases"),
    2: (do_detect, "detect_epidemic"),
    3: (do_view_alerts, "view_alerts"),
    4: (do_report, "generate_report"),
    5: (do_export, "export_report"),
    6: (do_analytics, "view_analytics"),
    # 7 = Color legend (no permission needed)
    # 8 = Exit
}


# Section: Main loop


def main() -> None:
    """Run the EpiAlert application.

    1. Initialise the DataManager (loads .txt files).
    2. Show the login screen.
    3. Loop: display role-specific menu -> dispatch -> repeat.
    4. Exit cleanly on user request.

    The loop is wrapped in a broad try/except so that unexpected
    errors never crash the application.  A :class:`KeyboardInterrupt`
    is caught separately so the user is reminded to use the Exit
    option instead of Ctrl-C.
    """
    dm: DataManager = DataManager()

    # Attempt login — fall back to a guest health agent on any failure
    try:
        agent: Agent = login()
    except Exception:
        agent = HealthAgent("Guest", "HA-0000", "Centre")
        warn("Login failed - using guest account.")

    while True:
        try:
            show_banner()

            if isinstance(agent, HealthAgent):
                _handle_health_agent(dm, agent)
            elif isinstance(agent, DepartmentAgent):
                _handle_dept_agent(dm, agent)
            else:
                # Defensive: unknown agent type — should never happen
                err("Unknown agent type. Please restart.")
                sys.exit(1)

        except KeyboardInterrupt:
            # User pressed Ctrl-C — remind them to use Exit option
            print(
                f"\n  {Colors.YELLOW}Interrupted"
                f" - choose Exit to quit.{Colors.RESET}"
            )
            pause()
        except EOFError:
            # Input stream closed (e.g. piped input ended)
            print(
                f"\n  {Colors.YELLOW}Input ended"
                f" - exiting.{Colors.RESET}"
            )
            sys.exit(0)
        except Exception as exc:
            err(f"Unexpected error: {exc}")
            info(
                "The application will continue."
                " Please try again."
            )
            pause()


def _handle_health_agent(dm: DataManager, agent: HealthAgent) -> None:
    """Display the Health Agent menu and dispatch the chosen action.

    The Health Agent menu includes single registration, batch
    registration, search, update, own entries, color legend,
    and exit.  This helper keeps :func:`main` concise by
    isolating the role-specific dispatch logic.

    Args:
        dm:    The data manager instance.
        agent: The currently logged-in health agent.
    """
    print(
        f"\n  {Colors.GREEN}{Colors.BOLD}"
        f"Logged in: {agent}{Colors.RESET}"
    )
    show_health_menu()
    menu_len: int = len(HEALTH_MENU)
    choice: int = choose(1, menu_len)

    # Legend is the second-to-last item in the menu
    if choice == menu_len - 1:
        show_legend()
    # Exit is the last item
    elif choice == menu_len:
        if confirm("Exit EpiAlert?"):
            ok(
                f"Thank you for using {APP_NAME}."
                f" Stay safe."
            )
            sys.exit(0)
    else:
        # Dispatch through the handler table
        handler, perm = _HEALTH_HANDLERS.get(choice, (None, ""))
        if handler is None:
            # The menu item exists but has no handler registered
            # (e.g. a future menu slot not yet wired up)
            warn("This option is not yet available.")
            pause()
            return
        if perm and not agent.can_perform(perm):
            err(
                "You do not have permission"
                " for this action."
            )
            pause()
        else:
            handler(dm, agent)


def _handle_dept_agent(dm: DataManager, agent: DepartmentAgent) -> None:
    """Display the Department Agent menu and dispatch the chosen action.

    The Department Agent menu includes view cases, epidemic
    detection, view alerts, generate report, export report,
    analytics, color legend, and exit.  This helper keeps
    :func:`main` concise by isolating the role-specific dispatch
    logic.

    Args:
        dm:    The data manager instance.
        agent: The currently logged-in department agent.
    """
    print(
        f"\n  {Colors.BLUE}{Colors.BOLD}"
        f"Logged in: {agent}{Colors.RESET}"
    )
    show_dept_menu()
    menu_len: int = len(DEPT_MENU)
    choice: int = choose(1, menu_len)

    # Legend is the second-to-last item in the menu
    if choice == menu_len - 1:
        show_legend()
    # Exit is the last item
    elif choice == menu_len:
        if confirm("Exit EpiAlert?"):
            ok(
                f"Thank you for using {APP_NAME}."
                f" Stay safe."
            )
            sys.exit(0)
    else:
        # Dispatch through the handler table
        handler, perm = _DEPT_HANDLERS.get(choice, (None, ""))
        if handler is None:
            warn("This option is not yet available.")
            pause()
            return
        if perm and not agent.can_perform(perm):
            err(
                "You do not have permission"
                " for this action."
            )
            pause()
        else:
            handler(dm, agent)


if __name__ == "__main__":
    main()
