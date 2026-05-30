
"""EpiAlert main entry point.

This is where everything starts.  We initialise the data layer,
show the login screen, and drive the main menu loop.  Every
user-facing action is wrapped in try/except so the app never
crashes unexpectedly.

The two agent roles have strictly separated menus:
    Health Agent:    register patients, search, update status,
                     review own entries.
    Department Agent: view cases, detect epidemics, view alerts,
                      generate/export reports, view analytics.

Run it with:  python main.py
"""

# Import the system module to handle OS-level interactions (e.g., exiting the program)
import sys

# Import global configuration variables (application name, ANSI colors, and menu definitions)
from config import APP_NAME, Colors, HEALTH_MENU, DEPT_MENU
# Import logical engines and core data layer manager components
from core import (
    Analytics,
    DataManager,
    EpidemicDetector,
    ReportEngine,
    ReportExporter,
)
# Import data structures (class models) for agents and patients
from models import Agent, HealthAgent, DepartmentAgent, Patient
# Import user interface utilities (Console UI) for I/O operations and rendering
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


# ═══════════════════════════════════════════════════════════════════════════════
# Health Agent actions — data entry only
# ═══════════════════════════════════════════════════════════════════════════════

def do_register(dm: DataManager, agent: Agent) -> None:
    """Walk the user through patient registration.

    Every field is collected step by step using numbered selections
    for region, province, commune, disease, and status.  The date
    auto-fills with the current timestamp when the user presses
    Enter.  The entered_by field records the health agent's ID.

    Args:
        dm:    The data manager instance.
        agent: The currently logged-in health agent.
    """
    # Display the section header for patient registration
    header("Register New Patient")

    # Prompt for first name and handle cancellation if left blank
    first = read_str("First name")
    if not first:
        warn("Cancelled.") # Notify user of cancellation
        pause()            # Pause to give the user time to read the message
        return             # Abort the workflow and return to the main menu
    
    # Prompt for last name and handle cancellation
    last = read_str("Last name")
    if not last:
        warn("Cancelled.")
        pause()
        return
    
    # Safely read integer for age with a strict validation range between 0 and 150
    age = read_int("Age", 0, 150)
    
    # Interactive selection for gender and handle cancellation
    gender = pick_gender()
    if not gender:
        warn("Cancelled.")
        pause()
        return
    
    # Select from a predefined list of monitored diseases and handle cancellation
    disease = pick_disease()
    if not disease:
        warn("Cancelled.")
        pause()
        return
    
    # Select the initial clinical status of the patient and handle cancellation
    status = pick_status()
    if not status:
        warn("Cancelled.")
        pause()
        return
    
    # Hierarchical geographical selection: Step 1 - Region
    region = pick_region()
    if not region:
        warn("Cancelled.")
        pause()
        return
    
    # Hierarchical geographical selection: Step 2 - Province (filtered by chosen region)
    province = pick_province(region)
    if not province:
        warn("Cancelled.")
        pause()
        return
    
    # Hierarchical geographical selection: Step 3 - Commune (filtered by chosen province)
    commune = pick_commune(province)
    if not commune:
        warn("Cancelled.")
        pause()
        return
    
    # Select the reporting healthcare facility (filtered by region)
    facility = pick_facility(region)
    if not facility:
        warn("Cancelled.")
        pause()
        return
    
    # Capture or automatically generate the timestamp for the case report
    # Date auto-fills with current timestamp
    date = read_date("Date reported")

    # Instantiate the Patient model with a temporary ID (0) and the current agent's ID
    p = Patient(
        0, first, last, age, gender, disease, status,
        region, province, commune, facility, date,
        agent.get_id(),
    )
    # Persist the patient record via DataManager, which returns a unique database ID
    pid = dm.add_patient(p)
    
    # Check if the database write succeeded (a positive ID confirms insertion)
    if pid > 0:
        ok(f"Patient registered - ID: {pid}") # Success message
        show_patient(p)                        # Display the saved patient details card
    else:
        err("Failed to save patient record.")  # Display error message on database failure
    pause()


def do_search(dm: DataManager, agent: Agent) -> None:
    """Search for a patient by ID or free text.

    Args:
        dm:    The data manager instance.
        agent: The currently logged-in health agent.
    """
    # Display the section header for patient lookup
    header("Search Patient")
    # Render search mode options with Cyan highlighted numbers
    print(f"  {Colors.CYAN}1.{Colors.RESET}  By ID")
    print(
        f"  {Colors.CYAN}2.{Colors.RESET}"
        f"  By name / disease / region"
    )
    # Capture the user's menu choice, restricted strictly to options 1 and 2
    c = choose(1, 2)
    
    # Option 1: Exact search by unique numerical patient ID
    if c == 1:
        pid = read_int("Patient ID", 1, 99999) # Secured integer input
        p = dm.find_patient_by_id(pid)         # Query the database layer
        if p:
            show_patient(p)                    # Render detailed patient sheet if found
        else:
            err(f"No patient with ID {pid}.") # Error message if record doesn't exist
            
    # Option 2: Full-text multi-criteria query (matches name, disease, or region)
    else:
        q = read_str("Search term") # Read string input
        if not q:
            warn("Cancelled.")
            pause()
            return
        results = dm.search_patients(q) # Execute the search query engine
        if results:
            ok(f"Found {len(results)} match(es):") # Notify user of match count
            show_patient_table(results)            # Render matched entries in a structured table
        else:
            info(f"No results for '{q}'.")        # Notify user when zero matches are returned
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
    # Display the section header for modifying clinical status
    header("Update Patient Status")
    pid = read_int("Patient ID", 1, 99999) # Ask for the target patient identifier
    p = dm.find_patient_by_id(pid)         # Fetch the existing patient record
    if not p:
        err(f"No patient with ID {pid}.")  # Terminate workflow if patient ID is invalid
        pause()
        return
        
    show_patient(p) # Show current file details for visual validation before editing
    new = pick_status() # Select the new clinical state (e.g., Recovered, Deceased, Under Treatment)
    if not new:
        warn("Cancelled.")
        pause()
        return
        
    # Explicitly prompt for user confirmation before modifying the database state
    if confirm(
        f"Change status from '{p.get_status()}' to '{new}'?"
    ):
        # Attempt to save changes and re-display the updated record on success
        if dm.update_patient_status(pid, new):
            ok("Status updated.")
            show_patient(dm.find_patient_by_id(pid))
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
    # Pull records registered exclusively by the currently logged-in agent's ID
    entries = dm.get_entries_by_agent(agent.get_id())
    
    # Conditional rendering depending on whether the agent has registered records
    if entries:
        ok(
            f"You have entered {len(entries)} patient(s):"
        )
        show_patient_table(entries) # Display personal entries in a clean dashboard table
    else:
        info("You have not entered any patients yet.") # Handle empty state for newly created accounts
    pause()


# ═══════════════════════════════════════════════════════════════════════════════
# Department Agent actions — consultation and analysis only
# ═══════════════════════════════════════════════════════════════════════════════

def do_view_cases(dm: DataManager, agent: Agent) -> None:
    """View disease cases filtered by region, disease, or all.

    Args:
        dm:    The data manager instance.
        agent: The currently logged-in department agent.
    """
    header("View Disease Cases")
    # Menu options for broad epidemiological dataset filtering
    print(f"  {Colors.CYAN}1.{Colors.RESET}  By region")
    print(f"  {Colors.CYAN}2.{Colors.RESET}  By disease")
    print(f"  {Colors.CYAN}3.{Colors.RESET}  All cases")
    c = choose(1, 3) # Capture structural filter choice (1, 2, or 3)
    
    # Geographical Filter: View cases bound to a specific region
    if c == 1:
        r = pick_region()
        if not r:
            warn("Cancelled.")
            pause()
            return
        show_case_table(dm.get_cases_by_region(r)) # Render cases matching selected region
        
    # Pathological Filter: View cases bound to a specific disease
    elif c == 2:
        d = pick_disease()
        if not d:
            warn("Cancelled.")
            pause()
            return
        show_case_table(dm.get_cases_by_disease(d)) # Render cases matching selected pathology
        
    # No Filter: Return and render the entire national case tracking registry
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
    c = choose(1, 2)
    
    # Instantiate the statistical threshold evaluation engine
    det = EpidemicDetector(dm)
    
    # Targeted Scan: Evaluate outbreak metrics on a single region
    if c == 1:
        r = pick_region()
        if not r:
            warn("Cancelled.")
            pause()
            return
        info(f"Scanning {r}...")
        alerts = det.detect_by_region(r) # Trigger regional detection logic
        
    # Macro Scan: Perform a sweeping anomaly detection across all territory regions
    else:
        info("Scanning all regions...")
        alerts = det.detect_all_regions() # Trigger nationwide cluster analysis
        
    # Output evaluation: Trigger system alerts or confirm public health stability
    if alerts:
        warn(f"{len(alerts)} new alert(s) detected!") # Warn if safety thresholds are breached
        show_alert_list(alerts)                       # Print listing of all triggered hot-spots
    else:
        ok("All zones within thresholds - no new alerts.") # Confirm everything is safe
    pause()


def do_view_alerts(dm: DataManager, agent: Agent) -> None:
    """Display all currently active epidemiological alerts.

    Args:
        dm:    The data manager instance.
        agent: The currently logged-in department agent.
    """
    header("Active Alerts")
    # Fetch all unresolved/active epidemiological alert files from memory
    active = dm.get_active_alerts()
    
    # Conditional UI branch based on the presence of public health threats
    if active:
        warn(f"{len(active)} active alert(s):")
        show_alert_list(active) # Map out all active alerts for immediate action
    else:
        ok("No active alerts at this time.") # Output reassuring message when system state is clear
    pause()


def do_report(dm: DataManager, agent: Agent) -> None:
    """Generate and display a zone, regional, or national report.

    Args:
        dm:    The data manager instance.
        agent: The currently logged-in department agent.
    """
    header("Generate Report")
    # Granularity selection menu for statistical consolidation
    print(f"  {Colors.CYAN}1.{Colors.RESET}  Zone level")
    print(
        f"  {Colors.CYAN}2.{Colors.RESET}  Regional level"
    )
    print(
        f"  {Colors.CYAN}3.{Colors.RESET}  National level"
    )
    c = choose(1, 3)
    
    # Initialize the core mathematical calculation engine
    eng = ReportEngine(dm)
    
    # Granularity Level 1: Micro-localized analytical reports (Region -> Province -> Commune)
    if c == 1:
        r = pick_region()
        if not r:
            warn("Cancelled.")
            pause()
            return
        p = pick_province(r)
        if not p:
            warn("Cancelled.")
            pause()
            return
        cm = pick_commune(p)
        if not cm:
            warn("Cancelled.")
            pause()
            return
        # Calculate and output specific municipal indicators
        show_report(eng.generate_zone_report(r, p, cm))
        
    # Granularity Level 2: Intermediary reports combining an entire medical administrative region
    elif c == 2:
        r = pick_region()
        if not r:
            warn("Cancelled.")
            pause()
            return
        show_report(eng.generate_region_report(r))
        
    # Granularity Level 3: Consolidated macroeconomic public health report covering the entire country
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
    # Select target territorial boundary to serialize for official archiving or transmission
    print(f"  {Colors.CYAN}1.{Colors.RESET}  Zone level")
    print(
        f"  {Colors.CYAN}2.{Colors.RESET}"
        f"  Regional level"
    )
    print(
        f"  {Colors.CYAN}3.{Colors.RESET}"
        f"  National level"
    )
    c = choose(1, 3)
    
    # Initialize utility handler responsible for physical file outputs
    exp = ReportExporter(dm)
    # Establish local path placeholders for output file tracking
    txt_path = ""
    md_path = ""
    
    # Branching execution for localized Zone (Commune) data extraction
    if c == 1:
        r = pick_region()
        if not r:
            warn("Cancelled.")
            pause()
            return
        p = pick_province(r)
        if not p:
            warn("Cancelled.")
            pause()
            return
        cm = pick_commune(p)
        if not cm:
            warn("Cancelled.")
            pause()
            return
        # Write flat raw text and structured markdown documents to disk
        txt_path = exp.export_zone_report(r, p, cm)
        md_path = exp.export_zone_md(r, p, cm)
        
    # Branching execution for full Regional data compilation
    elif c == 2:
        r = pick_region()
        if not r:
            warn("Cancelled.")
            pause()
            return
        txt_path = exp.export_region_report(r)
        md_path = exp.export_region_md(r)
        
    # Branching execution for centralized National data compilation
    else:
        txt_path = exp.export_national_report()
        md_path = exp.export_national_md()
        
    # Verify and notify file generation status for raw text output (.txt)
    if txt_path:
        ok(f"TXT report saved to: {txt_path}")
    else:
        err("TXT export failed.")
        
    # Verify and notify file generation status for rich tables document (.md)
    if md_path:
        ok(f"MD report saved to:  {md_path}")
    else:
        err("MD export failed.")
        
    # Confirm final archival logging if at least one file export transaction completed successfully
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
    # Instantly trigger calculations and print KPIs to the terminal dashboard
    show_report(Analytics(dm).generate_dashboard())
    pause()


# ═══════════════════════════════════════════════════════════════════════════════
# Dispatch tables — role-specific
# ═══════════════════════════════════════════════════════════════════════════════

# Route dictionary (Dispatch Table) binding menu entries to their function calls and role permissions
_HEALTH_HANDLERS: dict[int, tuple] = {
    1: (do_register, "register_patient"),    # Option 1: File a new case entry
    2: (do_search, "search_patient"),        # Option 2: Run a file database query
    3: (do_update, "update_status"),         # Option 3: Adjust ongoing case clinical standing
    4: (do_own_entries, "view_own_entries"), # Option 4: Review audit trails for the current user
    # 5 = Color legend (no permission needed)
    # 6 = Exit
}

# Route dictionary mapping Department Officer commands to respective analytics functions
_DEPT_HANDLERS: dict[int, tuple] = {
    1: (do_view_cases, "view_cases"),       # Option 1: View raw data matrices
    2: (do_detect, "detect_epidemic"),      # Option 2: Compute threshold deviations
    3: (do_view_alerts, "view_alerts"),     # Option 3: Track open emergency conditions
    4: (do_report, "generate_report"),      # Option 4: Compile point-in-time statistics
    5: (do_export, "export_report"),        # Option 5: Save summaries to storage volumes
    6: (do_analytics, "view_analytics"),    # Option 6: Review tactical trend dashboards
    # 7 = Color legend (no permission needed)
    # 8 = Exit
}


# ═══════════════════════════════════════════════════════════════════════════════
# Main loop
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    """Run the EpiAlert application.

    1. Initialise the DataManager (loads .txt files).
    2. Show the login screen.
    3. Loop: display role-specific menu -> dispatch -> repeat.
    4. Exit cleanly on user request.
    """
    # Instantiate DataManager (triggers parsing of persistent structural text databases)
    dm = DataManager()

    # Attempt user authentication check via interactive console screen
    try:
        agent = login() # Trigger UI authentication routine
    except Exception:
        # Fallback contingency: secure execution using a restricted Guest shell if login crashes
        agent = HealthAgent("Guest", "HA-0000", "Centre")
        warn("Login failed - using guest account.")

    # Main infinite lifecycle menu iteration loop
    while True:
        try:
            show_banner() # Render application header art branding on every loop pass

            # ------------------------------------------------------------------
            # Execution Block: Clinical Field Agent Role Workflow
            # ------------------------------------------------------------------
            if isinstance(agent, HealthAgent):
                # Print current session identities wrapped in Green text formatting
                print(
                    f"\n  {Colors.GREEN}{Colors.BOLD}"
                    f"Logged in: {agent}{Colors.RESET}"
                )
                show_health_menu() # Output choice menu matching Health Agent privileges
                choice = choose(1, len(HEALTH_MENU)) # Secure selection number entry

                # Catch specific global terminal option: Display UI color semantics
                if choice == len(HEALTH_MENU) - 1:
                    show_legend()
                # Catch specific global terminal option: Graceful exit execution sequence
                elif choice == len(HEALTH_MENU):
                    if confirm("Exit EpiAlert?"):
                        ok(
                            f"Thank you for using {APP_NAME}."
                            f" Stay safe."
                        )
                        sys.exit(0) # Terminate runtime engine with clean OS signal 0
                # Dispatch standard data management functionalities (Options 1 to 4)
                else:
                    # Unpack target routing parameters from the dispatch table
                    handler, perm = _HEALTH_HANDLERS.get(
                        choice, (None, "")
                    )
                    if handler is None:
                        continue # Guard against missing configurations by re-looping
                    # Enforce Role-Based Access Control (RBAC) via class permissions evaluation
                    if perm and not agent.can_perform(perm):
                        err(
                            "You do not have permission"
                            " for this action."
                        )
                        pause()
                    else:
                        handler(dm, agent) # Safely invoke the requested business logic function

            # ------------------------------------------------------------------
            # Execution Block: Department Strategist/Decision-Maker Workflow
            # ------------------------------------------------------------------
            elif isinstance(agent, DepartmentAgent):
                # Print current session identities wrapped in Blue text formatting
                print(
                    f"\n  {Colors.BLUE}{Colors.BOLD}"
                    f"Logged in: {agent}{Colors.RESET}"
                )
                show_dept_menu() # Display macro-analytical command options
                choice = choose(1, len(DEPT_MENU)) # Capture targeted choice integer

                # Special Option handling: Display ANSI system color map legend
                if choice == len(DEPT_MENU) - 1:
                    show_legend()
                # Special Option handling: Graceful shutdown workflow
                elif choice == len(DEPT_MENU):
                    if confirm("Exit EpiAlert?"):
                        ok(
                            f"Thank you for using {APP_NAME}."
                            f" Stay safe."
                        )
                        sys.exit(0)
                # Dispatch strategic monitoring functionalities (Options 1 to 6)
                else:
                    # Extract callable actions and verification strings from the dispatch map
                    handler, perm = _DEPT_HANDLERS.get(
                        choice, (None, "")
                    )
                    if handler is None:
                        continue
                    # Check operational access rights before executing computations
                    if perm and not agent.can_perform(perm):
                        err(
                            "You do not have permission"
                            " for this action."
                        )
                        pause()
                    else:
                        handler(dm, agent) # Safely call the selected dashboard or export script

        # Handle hardware termination signal events (e.g., user presses Ctrl+C)
        except KeyboardInterrupt:
            print(
                f"\n  {Colors.YELLOW}Interrupted"
                f" - choose Exit to quit.{Colors.RESET}"
            )
            pause() # Force a program hold to maintain integrity and prevent unclean thread deaths
            
        # Global Catch-All Exception Firewall
        # Safeguards execution against any unexpected bugs, preventing catastrophic software crashes
        except Exception as exc:
            err(f"Unexpected error: {exc}") # Print diagnostic telemetry information safely
            info(
                "The application will continue."
                " Please try again."
            )
            pause() # Recover structural state and return safely back to the core operational loops


# Python standard idiom confirming the script is run directly from a shell interface
if __name__ == "__main__":
    main() # Call program main execution sequence to activate the software core
