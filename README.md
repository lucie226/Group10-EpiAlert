# 1. Project Title and Description

## **EpiAlert**

Epidemiological Surveillance System for Burkina Faso.

A terminal-based tool for tracking disease outbreaks, detecting epidemics early, and generating epidemiological reports across the 13 regions of Burkina Faso. Designed for health agents (data entry) and department supervisors (consultation and analysis) working on the front lines of public health surveillance.

---

# 2. How to Run the Project

- **Python 3.10+** required.
- **No external dependencies** — the project uses only Python standard library modules.
- **Command:**

```
python main.py
```

- Data files are created automatically in `data/` on first run.

---

# 3. Features

- **Health Agent role** — register patients, update status, review own entries
- **Department Agent role** — view reports, run epidemic detection, export data, analytics dashboard
- Strict role separation: data entry vs. consultation/analysis
- Epidemiological surveillance by zone, region, and national level
- Automatic epidemic detection with disease-specific thresholds
- Alert system with severity levels: Warning / Critical / Emergency
- Epidemiological reports at zone, regional, and national scale
- Export to `.txt` and `.md` (Markdown with professional tables)
- Auto-archiving into `outputs/classeurs/` by region and province
- Analytics dashboard with mortality rates and weekly trends
- Colour-coded diseases, statuses, and alerts with built-in visual legend
- Health centre selection during login
- All 13 regions of Burkina Faso with provinces and communes
- Auto-timestamp on patient registration

---

# 4. Technologies Used

- **Python 3.10+**
- Standard modules: `os`, `sys`, `datetime`, `abc`
- No external dependencies

---

# 5. Project Structure

```
EpiAlert/
  main.py               Main entry point with role-specific dispatch
  config.py             Constants, regions, diseases, thresholds, colours, partners
  models.py             Agent, HealthAgent, DepartmentAgent, Patient, DiseaseCase, Alert
  core.py               DataManager, EpidemicDetector, ReportEngine, ReportExporter, Analytics
  ui.py                 Terminal UI — banner, menus, tables, input helpers, colour legend
  data/                 .txt data files (patients, cases, alerts)
  outputs/              Quick-access exported reports (.txt and .md)
  outputs/classeurs/    Auto-archived reports sorted by region/province
  .gitignore            Git ignore rules
  setup_branches.sh     Git branch automation script for team distribution
```

---

# 6. OOP Structure

| Principle       | Implementation                                                                 |
|-----------------|---------------------------------------------------------------------------------|
| Encapsulation   | `Patient._status` and `Alert._is_active` — private attributes with getter/setter methods |
| Abstraction     | `Agent` is an abstract base class (`ABC`) with `@abstractmethod` declarations |
| Inheritance     | `HealthAgent` / `DepartmentAgent` extend `Agent`; `ReportExporter` extends `ReportEngine` |
| Polymorphism    | `get_permissions()` and `can_perform()` return different results per agent type |

**Role separation:**

| Health Agent (data entry) | Department Agent (consultation & analysis) |
|---------------------------|---------------------------------------------|
| Register patients | View disease cases by zone |
| Search patients | Run epidemic detection |
| Update patient status | View active alerts |
| Review own entries | Generate reports |
| | Export reports (.txt and .md) |
| | View analytics dashboard |

---

# 7. Institutional Partners

- Ministry of Health, Burkina Faso (MS/BF)
- National Institute of Public Health (INSP)
- Centre for Emergency Health Operations (CORUS)
- National Observatory of Population Health (ONSP)
- General Directorate of Health and Public Hygiene (DGSHP)
- Health Information and Epidemiological Surveillance Centres (CISSE)
- General Directorate of Studies and Sectoral Statistics (DGESS)
- Centre Muraz — Bobo-Dioulasso
- Health Research Centre of Nouna (CRSN)
- Centre for Research and Training on Malaria (CNRFP)
- Health Sciences Research Institute (IRSS)
- Burkina Field Epidemiology and Laboratory Training Program (BFETP)
- Integrated Disease Surveillance and Response (SIMR)
- World Health Organization (OMS)
- UNICEF Burkina Faso
- Red Cross of Burkina Faso (CRB)
- Doctors Without Borders (MSF)
- Africa Centres for Disease Control and Prevention
- Administrative data based on the territorial division of Burkina Faso (Government)
- Health infrastructure based on the Ministry of Health of Burkina Faso
- Epidemiological thresholds inspired by WHO guidelines
- Data flow modelled after the Integrated Disease Surveillance and Response (SIMR) framework
- Python documentation, Python Standard Library

---

# 8. Github Profiles

| Team Member | GitHub Profile | Contributions |
| :--- | :--- | :--- |
| **OUEDRAOGO Lucienne** | [GitHub Profile](https://github.com/lucie226) | Data Management, `README.md`, Project Directory Structure |
| **OUEDRAOGO Grace Melyka Nongbzanga** | [GitHub Profile](https://github.com/graceouedraogo2011-collab) | Configuration (`config.py`) |
| **NASSA Kiswendsida** | [GitHub Profile](https://github.com/nassakiswendsida21-dotcom) | Model Development (`models.py`) |
| **OUEDA Mohamed Hamine** | [GitHub Profile](https://github.com/ouedamohamed) | Core Logic Development (`core.py`) |
| **NAVE Attaoullah** | [GitHub Profile](https://github.com/naveattaoullah-max) | Main Application Entry Point (`main.py`) |
| **OUEDRAOGO Aubin Arnaud Relwendé** | [GitHub Profile](https://github.com/aubinarnaudrelwendoo-commits) | Initialization (`__init__.py`), UI Development (`ui.py`), Research & Documentation |
