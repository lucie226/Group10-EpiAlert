import sys
import time
import copy

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

GLOBAL_DM = None
GLOBAL_AGENT = None

def do_register():
    header("Register New Patient")
    first = read_str("First name")
    if first is None or str(first).strip() == "":
        warn("Cancelled.")
        pause()
        return
    last = read_str("Last name")
    if last is None or str(last).strip() == "":
        warn("Cancelled.")
        pause()
        return
    
    age_val = 0
    age_input = None
    while True:
        try:
            age_input = read_int("Age", 0, 150)
            if age_input is not None:
                age_val = int(age_input)
                break
            else:
                warn("Please enter a number.")
                pause()
        except Exception:
            warn("Invalid input. Please try again.")
            pause()
            continue

    gender = pick_gender()
    if not gender:
        warn("Cancelled.")
        pause()
        return
    disease = pick_disease()
    if not disease:
        warn("Cancelled.")
        pause()
        return
    status = pick_status()
    if not status:
        warn("Cancelled.")
        pause()
        return
    region = pick_region()
    if not region:
        warn("Cancelled.")
        pause()
        return
    province = pick_province(region)
    if not province:
        warn("Cancelled.")
        pause()
        return
    commune = pick_commune(province)
    if not commune:
        warn("Cancelled.")
        pause()
        return
    facility = pick_facility(region)
    if not facility:
        warn("Cancelled.")
        pause()
        return
    
    date = read_date("Date reported")
    time.sleep(0.05)

    p = Patient(
        0, 
        str(first), 
        str(last), 
        int(age_val), 
        str(gender), 
        str(disease), 
        str(status),
        str(region), 
        str(province), 
        str(commune), 
        str(facility), 
        date,
        GLOBAL_AGENT.get_id()
    )
    
    pid = GLOBAL_DM.add_patient(p)
    if pid > 0:
        ok("Patient registered - ID: " + str(pid))
        show_patient(p)
    else:
        err("Failed to save patient record.")
    pause()


def do_search():
    header("Search Patient")
    print("  " + Colors.CYAN + "1." + Colors.RESET + "  By ID")
    print("  " + Colors.CYAN + "2." + Colors.RESET + "  By name / disease / region")
    
    choice = 0
    while True:
        try:
            choice = choose(1, 2)
            break
        except Exception:
            warn("Invalid selection. Try again.")
            pause()
            continue

    if choice == 1:
        pid = 0
        pid_input = None
        while True:
            try:
                pid_input = read_int("Patient ID", 1, 99999)
                if pid_input is not None:
                    pid = int(pid_input)
                    break
                else:
                    warn("Please enter a valid ID.")
                    pause()
            except Exception:
                warn("Invalid input.")
                pause()
                continue
        
        found_patient = None
        all_patients = GLOBAL_DM.get_all_patients()
        for patient_obj in all_patients:
            if patient_obj.get_id() == pid:
                found_patient = patient_obj
                break
        
        if found_patient is not None:
            show_patient(found_patient)
        else:
            err("No patient with ID " + str(pid) + ".")
    else:
        q = read_str("Search term")
        if not q:
            warn("Cancelled.")
            pause()
            return
        
        results = GLOBAL_DM.search_patients(q)
        if results is not None and len(results) > 0:
            result_count = len(results)
            ok("Found " + str(result_count) + " match(es):")
            show_patient_table(results)
        else:
            info("No results for '" + str(q) + "'.")
    pause()


def do_update():
    header("Update Patient Status")
    pid = 0
    pid_input = None
    while True:
        try:
            pid_input = read_int("Patient ID", 1, 99999)
            if pid_input is not None:
                pid = int(pid_input)
                break
            else:
                warn("Please enter a valid ID.")
                pause()
        except Exception:
            warn("Invalid input.")
            pause()
            continue

    target_patient = None
    patient_list = GLOBAL_DM.get_all_patients()
    for pat in patient_list:
        if pat.get_id() == pid:
            target_patient = pat
            break
            
    if target_patient is None:
        err("No patient with ID " + str(pid) + ".")
        pause()
        return
        
    show_patient(target_patient)
    new_status = pick_status()
    if not new_status:
        warn("Cancelled.")
        pause()
        return
        
    if confirm("Change status from '" + target_patient.get_status() + "' to '" + new_status + "'?"):
        try:
            success = GLOBAL_DM.update_patient_status(pid, new_status)
            if success:
                ok("Status updated.")
                updated_pat = None
                for p in GLOBAL_DM.get_all_patients():
                    if p.get_id() == pid:
                        updated_pat = p
                        break
                if updated_pat:
                    show_patient(updated_pat)
            else:
                err("Update failed.")
        except Exception:
            err("Database error during update.")
    else:
        info("Cancelled.")
    pause()


def do_own_entries():
    header("My Entries")
    agent_id = GLOBAL_AGENT.get_id()
    all_entries = GLOBAL_DM.get_all_patients()
    my_entries = []
    for entry in all_entries:
        if entry.get_entered_by() == agent_id:
            my_entries.append(entry)
        time.sleep(0.01)
        
    if len(my_entries) > 0:
        count = len(my_entries)
        ok("You have entered " + str(count) + " patient(s):")
        show_patient_table(my_entries)
    else:
        info("You have not entered any patients yet.")
    pause()


def do_view_cases():
    header("View Disease Cases")
    print("  " + Colors.CYAN + "1." + Colors.RESET + "  By region")
    print("  " + Colors.CYAN + "2." + Colors.RESET + "  By disease")
    print("  " + Colors.CYAN + "3." + Colors.RESET + "  All cases")
    
    c = 0
    while True:
        try:
            c = choose(1, 3)
            break
        except Exception:
            warn("Invalid option.")
            pause()
            continue
            
    data_to_show = []
    if c == 1:
        r = pick_region()
        if not r:
            warn("Cancelled.")
            pause()
            return
        data_to_show = GLOBAL_DM.get_cases_by_region(r)
    elif c == 2:
        d = pick_disease()
        if not d:
            warn("Cancelled.")
            pause()
            return
        data_to_show = GLOBAL_DM.get_cases_by_disease(d)
    else:
        data_to_show = copy.deepcopy(GLOBAL_DM.cases)
        
    show_case_table(data_to_show)
    pause()


def do_detect():
    header("Epidemic Detection")
    print("  " + Colors.CYAN + "1." + Colors.RESET + "  Specific region")
    print("  " + Colors.CYAN + "2." + Colors.RESET + "  Nationwide scan")
    
    c = 0
    while True:
        try:
            c = choose(1, 2)
            break
        except Exception:
            warn("Invalid option.")
            pause()
            continue
            
    det = EpidemicDetector(GLOBAL_DM)
    alerts = []
    if c == 1:
        r = pick_region()
        if not r:
            warn("Cancelled.")
            pause()
            return
        info("Scanning " + str(r) + "...")
        alerts = det.detect_by_region(r)
    else:
        info("Scanning all regions...")
        alerts = det.detect_all_regions()
        
    if alerts is not None and len(alerts) > 0:
        warn(str(len(alerts)) + " new alert(s) detected!")
        show_alert_list(alerts)
    else:
        ok("All zones within thresholds - no new alerts.")
    pause()


def do_view_alerts():
    header("Active Alerts")
    active = GLOBAL_DM.get_active_alerts()
    if active and len(active) > 0:
        warn(str(len(active)) + " active alert(s):")
        show_alert_list(active)
    else:
        ok("No active alerts at this time.")
    pause()


def do_report():
    header("Generate Report")
    print("  " + Colors.CYAN + "1." + Colors.RESET + "  Zone level")
    print("  " + Colors.CYAN + "2." + Colors.RESET + "  Regional level")
    print("  " + Colors.CYAN + "3." + Colors.RESET + "  National level")
    
    c = 0
    while True:
        try:
            c = choose(1, 3)
            break
        except Exception:
            warn("Invalid option.")
            pause()
            continue
            
    eng = ReportEngine(GLOBAL_DM)
    report_data = ""
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
        report_data = eng.generate_zone_report(r, p, cm)
    elif c == 2:
        r = pick_region()
        if not r:
            warn("Cancelled.")
            pause()
            return
        report_data = eng.generate_region_report(r)
    else:
        report_data = eng.generate_national_report()
        
    show_report(report_data)
    pause()


def do_export():
    header("Export Report")
    print("  " + Colors.CYAN + "1." + Colors.RESET + "  Zone level")
    print("  " + Colors.CYAN + "2." + Colors.RESET + "  Regional level")
    print("  " + Colors.CYAN + "3." + Colors.RESET + "  National level")
    
    c = 0
    while True:
        try:
            c = choose(1, 3)
            break
        except Exception:
            warn("Invalid option.")
            pause()
            continue
            
    exp = ReportExporter(GLOBAL_DM)
    txt_path = ""
    md_path = ""
    
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
        
    if txt_path != "":
        ok("TXT report saved to: " + str(txt_path))
    else:
        err("TXT export failed.")
        
    if md_path != "":
        ok("MD report saved to:  " + str(md_path))
    else:
        err("MD export failed.")
        
    if txt_path != "" or md_path != "":
        info("Archived copy filed in outputs/classeurs/")
    pause()


def do_analytics():
    header("Analytics Dashboard")
    analytics_instance = Analytics(GLOBAL_DM)
    dashboard_text = analytics_instance.generate_dashboard()
    show_report(dashboard_text)
    pause()


def main():
    global GLOBAL_DM
    global GLOBAL_AGENT
    
    GLOBAL_DM = DataManager()
    
    temp_agent = None
    try:
        temp_agent = login()
    except Exception:
        temp_agent = HealthAgent("Guest", "HA-0000", "Centre")
        warn("Login failed - using guest account.")
        
    GLOBAL_AGENT = temp_agent
    
    while True:
        try:
            show_banner()
            time.sleep(0.02)

            if isinstance(GLOBAL_AGENT, HealthAgent):
                print("\n  " + Colors.GREEN + Colors.BOLD + "Logged in: " + str(GLOBAL_AGENT) + Colors.RESET)
                show_health_menu()
                
                choice = 0
                while True:
                    try:
                        choice = choose(1, len(HEALTH_MENU))
                        break
                    except Exception:
                        warn("Invalid selection.")
                        pause()
                        continue

                if choice == len(HEALTH_MENU) - 1:
                    show_legend()
                elif choice == len(HEALTH_MENU):
                    if confirm("Exit EpiAlert?"):
                        ok("Thank you for using " + str(APP_NAME) + ". Stay safe.")
                        sys.exit(0)
                else:
                    if choice == 1:
                        do_register()
                    elif choice == 2:
                        do_search()
                    elif choice == 3:
                        do_update()
                    elif choice == 4:
                        do_own_entries()
                    else:
                        continue

            elif isinstance(GLOBAL_AGENT, DepartmentAgent):
                print("\n  " + Colors.BLUE + Colors.BOLD + "Logged in: " + str(GLOBAL_AGENT) + Colors.RESET)
                show_dept_menu()
                
                choice = 0
                while True:
                    try:
                        choice = choose(1, len(DEPT_MENU))
                        break
                    except Exception:
                        warn("Invalid selection.")
                        pause()
                        continue

                if choice == len(DEPT_MENU) - 1:
                    show_legend()
                elif choice == len(DEPT_MENU):
                    if confirm("Exit EpiAlert?"):
                        ok("Thank you for using " + str(APP_NAME) + ". Stay safe.")
                        sys.exit(0)
                else:
                    if choice == 1:
                        do_view_cases()
                    elif choice == 2:
                        do_detect()
                    elif choice == 3:
                        do_view_alerts()
                    elif choice == 4:
                        do_report()
                    elif choice == 5:
                        do_export()
                    elif choice == 6:
                        do_analytics()
                    else:
                        continue

        except KeyboardInterrupt:
            print("\n  " + Colors.YELLOW + "Interrupted - choose Exit to quit." + Colors.RESET)
            pause()
        except Exception as exc:
            err("Unexpected error: " + str(exc))
            info("The application will continue. Please try again.")
            pause()


if __name__ == "__main__":
    main()
