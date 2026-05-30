"""Core business logic for EpiAlert.

The pipeline:

    Data -> Detection -> Alerting -> Reporting -> Analysis

We use in-memory indexes (dictionaries) for fast lookups instead of
scanning through lists every time.  Patient search-by-ID is O(1)
instead of O(n), which matters as the database grows.

Classes:
    DataManager:      Loads / saves .txt files and manages in-memory data.
    EpidemicDetector: Compares case counts to epidemic thresholds.
    ReportEngine:     Generates formatted epidemiological reports.
    ReportExporter:   Writes reports to .txt and .md files
                      (extends ReportEngine).
    Analytics:        Statistical analysis and dashboard data.
"""

# Import the standard os module for file and directory path manipulations
import os
# Import datetime to handle timestamping for reports and records
from datetime import datetime

# Import global constants and configurations from the local config module
from config import (
    ALERTS_FILE,
    CASES_FILE,
    CLASSEURS_DIR,
    COMMUNES,
    DATA_DIR,
    DISEASE_THRESHOLDS,
    MOTTO_EN,
    MOTTO_FR,
    OUTPUTS_DIR,
    PATIENTS_FILE,
    PROVINCES,
    REGIONS,
)
# Import data structures for alerts, cases, and patients from the local models module
from models import Alert, DiseaseCase, Patient


# ═══════════════════════════════════════════════════════════════════════════════
# DataManager
# ═══════════════════════════════════════════════════════════════════════════════

class DataManager:
    """Manages all data persistence using pipe-delimited .txt files.

    On startup we load every record from the three data files into
    memory and build lookup indexes for fast access.  If a file does
    not exist yet, the corresponding list and index start empty.

    Speed optimisation:
        _patient_index maps patient_id -> Patient for O(1) lookups.
        _cases_by_region maps region_name -> list of cases.
        _cases_by_disease maps disease_name -> list of cases.

    Attributes:
        patients: All loaded patient records.
        cases:    All loaded disease-case records.
        alerts:   All loaded alert records.
    """

    def __init__(self) -> None:
        """Initialise the manager and load all data from disk."""
        # Initialize primary data stores as empty lists
        self.patients: list[Patient] = []
        self.cases: list[DiseaseCase] = []
        self.alerts: list[Alert] = []

        # Indexes — rebuilt after every load to maintain rapid O(1) lookups
        self._patient_index: dict[int, Patient] = {}
        self._cases_by_region: dict[str, list[DiseaseCase]] = {}
        self._cases_by_disease: dict[str, list[DiseaseCase]] = {}

        # Execute initialization pipeline: setup directories, load files, and map indexes
        self._ensure_dirs()
        self._load_patients()
        self._load_cases()
        self._load_alerts()
        self._rebuild_indexes()

    # -- Private: directory setup -----------------------------------------------

    def _ensure_dirs(self) -> None:
        """Create data/, outputs/, and classeurs/ directories if missing."""
        # Loop through essential root directories and create them safely if missing
        for d in (DATA_DIR, OUTPUTS_DIR, CLASSEURS_DIR):
            if not os.path.exists(d):
                os.makedirs(d, exist_ok=True)
                
        # Build out a nested hierarchical folder structure for organized archiving
        # Create region subfolders inside the main classeurs directory
        for region_name in REGIONS:
            # Note: _safe() is presumably a sanitization function imported elsewhere or built-in
            rdir = os.path.join(CLASSEURS_DIR, _safe(region_name))
            os.makedirs(rdir, exist_ok=True)
            # Create corresponding province subfolders inside each specific region folder
            for prov in PROVINCES.get(region_name, []):
                pdir = os.path.join(rdir, _safe(prov))
                os.makedirs(pdir, exist_ok=True)

    # -- Private: index management ----------------------------------------------

    def _rebuild_indexes(self) -> None:
        """Rebuild lookup dictionaries from the current lists."""
        # Map patient IDs directly to Patient objects via dictionary comprehension
        self._patient_index = {p.patient_id: p for p in self.patients}
        
        # Reset and repopulate the region-based grouping dictionary
        self._cases_by_region = {}
        for c in self.cases:
            self._cases_by_region.setdefault(c.region, []).append(c)
            
        # Reset and repopulate the disease-based grouping dictionary
        self._cases_by_disease = {}
        for c in self.cases:
            self._cases_by_disease.setdefault(c.disease, []).append(c)

    # -- Patient operations -----------------------------------------------------

    def _load_patients(self) -> None:
        """Load patient records from the .txt file into memory."""
        self.patients = []
        # Abort loading if the database file does not exist yet
        if not os.path.exists(PATIENTS_FILE):
            return
            
        try:
            # Open the file with UTF-8 encoding to support international characters
            with open(PATIENTS_FILE, "r", encoding="utf-8") as fh:
                for line in fh:
                    # Deserialize raw text lines into Patient class instances
                    patient = Patient.from_file_line(line)
                    if patient is not None:
                        self.patients.append(patient)
        except (IOError, OSError):
            # Fallback to an empty list if file reading fails to prevent crashes
            self.patients = []

    def save_patients(self) -> bool:
        """Write all patient records back to the .txt file.

        The file header includes field descriptions and a timestamp
        so that anyone opening the file can immediately understand
        the format.

        Returns:
            True on success, False on I/O error.
        """
        try:
            # Open file in overwrite mode ("w") ensuring UTF-8 compliance
            with open(PATIENTS_FILE, "w", encoding="utf-8") as fh:
                # Write standard textual database headers for human readability
                fh.write(
                    "# ========================================================"
                    "====\n"
                )
                fh.write("# EpiAlert - Patient Records Database\n")
                fh.write(
                    f"# Last updated:"
                    f" {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
                )
                fh.write(f"# Total records: {len(self.patients)}\n")
                fh.write(
                    "# ========================================================"
                    "====\n"
                )
                fh.write("# Fields:\n")
                fh.write(
                    "#   id | first_name | last_name | age | gender"
                    " | disease |\n"
                )
                fh.write(
                    "#   status | region | province | commune"
                    " | facility | date_reported\n"
                )
                fh.write(
                    "#   | entered_by (agent ID)\n"
                )
                fh.write(
                    "# ========================================================"
                    "====\n"
                )
                # Serialize and write every patient object sequentially
                for p in self.patients:
                    fh.write(p.to_file_line() + "\n")
            return True # Confirm successful save operation
        except (IOError, OSError):
            return False # Signal failure without crashing the runtime

    def add_patient(self, patient: Patient) -> int:
        """Add a new patient and persist to disk.

        The patient_id is auto-assigned as max(existing_ids) + 1.
        We also update the index right away.

        Args:
            patient: A Patient object (patient_id may be 0).

        Returns:
            The assigned ID, or -1 if the save failed.
        """
        # Dynamically calculate the next available ID sequence number
        next_id = max(
            (p.patient_id for p in self.patients), default=0
        ) + 1
        patient.patient_id = next_id # Assign calculated unique ID to the object
        
        # Insert object into primary list and update the O(1) access index
        self.patients.append(patient)
        self._patient_index[next_id] = patient
        
        # Attempt to save to disk and return the ID on success, or -1 on failure
        return next_id if self.save_patients() else -1

    def find_patient_by_id(self, patient_id: int) -> Patient | None:
        """Look up a patient by ID using the index (O(1) lookup).

        Args:
            patient_id: The numeric ID to search for.

        Returns:
            The matching Patient, or None if not found.
        """
        # Utilize dictionary getter to avoid KeyErrors
        return self._patient_index.get(patient_id)

    def search_patients(self, query: str) -> list[Patient]:
        """Search patients by name, disease, or region (case-insensitive).

        Args:
            query: Free-text search term.

        Returns:
            A list of matching Patient objects.
        """
        q = query.lower() # Normalize search string to lowercase for comparison
        # Return a list comprehension filtering matches across multiple entity properties
        return [
            p for p in self.patients
            if q in p.first_name.lower()
            or q in p.last_name.lower()
            or q in p.disease.lower()
            or q in p.region.lower()
        ]

    def get_entries_by_agent(self, agent_id: str) -> list[Patient]:
        """Return all patients entered by a specific health agent.

        This lets health agents review only their own entries.

        Args:
            agent_id: The agent's unique ID string.

        Returns:
            A list of Patient objects entered by that agent.
        """
        # Filter patients matching the creator's ID
        return [
            p for p in self.patients if p.entered_by == agent_id
        ]

    def update_patient_status(
        self, patient_id: int, new_status: str
    ) -> bool:
        """Update a patient's status by ID.

        Args:
            patient_id: The patient's numeric ID.
            new_status: Must be one of PATIENT_STATUSES.

        Returns:
            True if the update succeeded, False otherwise.
        """
        # Fetch the patient reference from the memory map
        patient = self.find_patient_by_id(patient_id)
        if patient is None:
            return False # Reject operation if patient does not exist
            
        # Delegate state transition to the object's method
        if not patient.set_status(new_status):
            return False # Reject operation if status validation fails
            
        # Persist the mutated state to disk
        return self.save_patients()

    # -- Disease-case operations ------------------------------------------------

    def _load_cases(self) -> None:
        """Load disease-case records from the .txt file."""
        self.cases = []
        if not os.path.exists(CASES_FILE):
            return
            
        try:
            with open(CASES_FILE, "r", encoding="utf-8") as fh:
                for line in fh:
                    # Parse each text row into a DiseaseCase domain model
                    case = DiseaseCase.from_file_line(line)
                    if case is not None:
                        self.cases.append(case)
        except (IOError, OSError):
            self.cases = []

    def save_cases(self) -> bool:
        """Write all disease-case records to the .txt file.

        Returns:
            True on success, False on I/O error.
        """
        try:
            with open(CASES_FILE, "w", encoding="utf-8") as fh:
                # Construct file structure metadata headers
                fh.write(
                    "# ========================================================"
                    "====\n"
                )
                fh.write("# EpiAlert - Disease Case Records\n")
                fh.write(
                    f"# Last updated:"
                    f" {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
                )
                fh.write(f"# Total records: {len(self.cases)}\n")
                fh.write(
                    "# ========================================================"
                    "====\n"
                )
                fh.write("# Fields:\n")
                fh.write(
                    "#   id | disease | region | province | commune |\n"
                )
                fh.write(
                    "#   suspected | confirmed | recovered | deceased"
                    " |\n"
                )
                fh.write(
                    "#   date_reported | week_number\n"
                )
                fh.write(
                    "# ========================================================"
                    "====\n"
                )
                # Output formatted data strings for every case instance
                for c in self.cases:
                    fh.write(c.to_file_line() + "\n")
            return True
        except (IOError, OSError):
            return False

    def get_cases_by_region(self, region: str) -> list[DiseaseCase]:
        """Return all cases for a given region using the index."""
        # Utilize the pre-computed dictionary for immediate retrieval
        return self._cases_by_region.get(region, [])

    def get_cases_by_disease(self, disease: str) -> list[DiseaseCase]:
        """Return all cases for a given disease using the index."""
        # Return matched disease cluster using the O(1) mapping dictionary
        return self._cases_by_disease.get(disease, [])

    def get_cases_by_zone(
        self, region: str, province: str, commune: str
    ) -> list[DiseaseCase]:
        """Return all cases for a specific geographic zone.

        We filter the region's cases (from the index) by province and
        commune, which is faster than scanning all cases.

        Args:
            region:   Region name.
            province: Province name.
            commune:  Commune name.

        Returns:
            A list of matching DiseaseCase objects.
        """
        # Narrow the search space by starting with the region-specific index
        region_cases = self._cases_by_region.get(region, [])
        # Apply secondary filtering for micro-level geographic boundaries
        return [
            c for c in region_cases
            if c.province.lower() == province.lower()
            and c.commune.lower() == commune.lower()
        ]

    def aggregate_cases(self) -> dict[str, dict[str, int]]:
        """Aggregate confirmed cases by disease and region.

        Returns:
            A nested dict: disease -> region -> total_confirmed.
        """
        result: dict[str, dict[str, int]] = {}
        for case in self.cases:
            # Ensure the top-level disease key exists
            result.setdefault(case.disease, {})
            # Ensure the secondary region key exists and defaults to 0
            result[case.disease].setdefault(case.region, 0)
            # Accumulate the confirmed count iteratively
            result[case.disease][case.region] += case.confirmed
        return result

    # -- Alert operations -------------------------------------------------------

    def _load_alerts(self) -> None:
        """Load alert records from the .txt file."""
        self.alerts = []
        if not os.path.exists(ALERTS_FILE):
            return
            
        try:
            with open(ALERTS_FILE, "r", encoding="utf-8") as fh:
                for line in fh:
                    # Construct Alert model instances from data rows
                    alert = Alert.from_file_line(line)
                    if alert is not None:
                        self.alerts.append(alert)
        except (IOError, OSError):
            self.alerts = []

    def save_alerts(self) -> bool:
        """Write all alert records to the .txt file.

        Returns:
            True on success, False on I/O error.
        """
        try:
            with open(ALERTS_FILE, "w", encoding="utf-8") as fh:
                # Add human-readable contextual headers for the data structure
                fh.write(
                    "# ========================================================"
                    "====\n"
                )
                fh.write("# EpiAlert - Alert Records\n")
                fh.write(
                    f"# Last updated:"
                    f" {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
                )
                fh.write(f"# Total records: {len(self.alerts)}\n")
                fh.write(
                    "# ========================================================"
                    "====\n"
                )
                fh.write("# Fields:\n")
                fh.write(
                    "#   id | disease | region | province | commune"
                    " | case_count |\n"
                )
                fh.write(
                    "#   threshold | message | severity"
                    " | date_created | is_active\n"
                )
                fh.write(
                    "# ========================================================"
                    "====\n"
                )
                # Flush the memory list of alerts onto the file system
                for a in self.alerts:
                    fh.write(a.to_file_line() + "\n")
            return True
        except (IOError, OSError):
            return False

    def add_alert(self, alert: Alert) -> int:
        """Add a new alert and persist to disk.

        Args:
            alert: An Alert object (alert_id may be 0).

        Returns:
            The assigned ID, or -1 if the save failed.
        """
        # Compute auto-increment identifier safely, defaulting to 0 if list is empty
        next_id = max(
            (a.alert_id for a in self.alerts), default=0
        ) + 1
        alert.alert_id = next_id
        self.alerts.append(alert)
        
        # Save to disk and evaluate success boolean to return ID or -1
        return next_id if self.save_alerts() else -1

    def get_active_alerts(self) -> list[Alert]:
        """Return all alerts that are currently active."""
        # Utilize the internal method of the Alert class for state filtering
        return [a for a in self.alerts if a.is_active()]

    def get_alerts_by_region(self, region: str) -> list[Alert]:
        """Return all alerts for a given region."""
        # Case-insensitive equality check on the region parameter
        return [
            a for a in self.alerts
            if a.region.lower() == region.lower()
        ]

    # -- Statistics -------------------------------------------------------------

    def get_total_patients(self) -> int:
        """Return the total number of patient records."""
        return len(self.patients)

    def count_by_status(self) -> dict[str, int]:
        """Count patients grouped by status."""
        counts: dict[str, int] = {}
        # Iterate over records mapping frequency of clinical states
        for p in self.patients:
            counts[p.get_status()] = counts.get(
                p.get_status(), 0
            ) + 1
        return counts

    def count_by_region(self) -> dict[str, int]:
        """Count patients grouped by region."""
        counts: dict[str, int] = {}
        # Aggregate geospatial frequency distributions
        for p in self.patients:
            counts[p.region] = counts.get(p.region, 0) + 1
        return counts

    def count_by_disease(self) -> dict[str, int]:
        """Count patients grouped by disease."""
        counts: dict[str, int] = {}
        # Map frequency for prevalent health conditions
        for p in self.patients:
            counts[p.disease] = counts.get(p.disease, 0) + 1
        return counts


# ═══════════════════════════════════════════════════════════════════════════════
# EpidemicDetector
# ═══════════════════════════════════════════════════════════════════════════════

class EpidemicDetector:
    """Detects epidemics by comparing case counts to thresholds.

    Severity rules:
        Warning   — cases exceed threshold by 1-50 %
        Critical  — cases exceed threshold by 51-100 %
        Emergency — cases exceed threshold by > 100 %

    Attributes:
        data_manager: Reference to the DataManager.
    """

    def __init__(self, data_manager: DataManager) -> None:
        """Initialise the detector.

        Args:
            data_manager: The data source for case records.
        """
        # Inject dependency to abstract database interactions
        self.data_manager = data_manager

    def determine_severity(
        self, case_count: int, threshold: int
    ) -> str:
        """Figure out the severity level from the excess ratio.

        Args:
            case_count: Current number of confirmed cases.
            threshold:  Epidemic threshold for the disease.

        Returns:
            "Warning", "Critical", or "Emergency".
        """
        # Protect against ZeroDivisionError and enforce immediate emergency
        if threshold == 0:
            return "Emergency"
            
        # Calculate percentage overrun above the safe threshold baseline
        excess = ((case_count - threshold) / threshold) * 100.0
        
        # Categorize threat tier based on defined metric brackets
        if excess <= 50.0:
            return "Warning"
        if excess <= 100.0:
            return "Critical"
        return "Emergency"

    def detect_by_zone(
        self, region: str, province: str, commune: str
    ) -> list[Alert]:
        """Detect epidemics in a single geographic zone.

        Args:
            region:   Region name.
            province: Province name.
            commune:  Commune name.

        Returns:
            A list of newly created Alert objects.
        """
        new_alerts: list[Alert] = []
        # Filter all available case reports strictly bounded to this municipality
        zone_cases = self.data_manager.get_cases_by_zone(
            region, province, commune
        )

        # Tally up confirmed cases per disease for this zone
        totals: dict[str, int] = {}
        for case in zone_cases:
            # Aggregate confirmation numbers for the specific pathology
            totals[case.disease] = (
                totals.get(case.disease, 0) + case.confirmed
            )

        # Evaluate computed totals against global baseline constants
        for disease, total_confirmed in totals.items():
            threshold = DISEASE_THRESHOLDS.get(disease, 999) # Safe default is high
            
            # Trigger alert condition if limit is broken
            if total_confirmed > threshold:
                severity = self.determine_severity(
                    total_confirmed, threshold
                )
                # Formulate a descriptive payload for the alert broadcast
                message = (
                    f"EPIDEMIC ALERT: {disease} cases in "
                    f"{region} / {province} / {commune} have "
                    f"exceeded the threshold "
                    f"({total_confirmed} cases vs. "
                    f"threshold of {threshold})."
                )
                # Instantiate and record the alert framework structure
                new_alerts.append(Alert(
                    alert_id=0,
                    disease=disease,
                    region=region,
                    province=province,
                    commune=commune,
                    case_count=total_confirmed,
                    threshold=threshold,
                    message=message,
                    severity=severity,
                    date_created=datetime.now().strftime("%Y-%m-%d"),
                ))
        return new_alerts

    def detect_by_region(self, region: str) -> list[Alert]:
        """Detect epidemics across all zones in a region.

        Args:
            region: Region name.

        Returns:
            A list of new Alert objects.
        """
        all_new: list[Alert] = []
        # Iterate over geographic mapping trees dynamically to sweep entire regions
        for province in PROVINCES.get(region, []):
            for commune in COMMUNES.get(province, []):
                # Extend payload with detections found at the granular zone level
                all_new.extend(
                    self.detect_by_zone(region, province, commune)
                )
                
        # Persist newly discovered alert conditions immediately to the database
        for alert in all_new:
            self.data_manager.add_alert(alert)
        return all_new

    def detect_all_regions(self) -> list[Alert]:
        """Detect epidemics across all regions of Burkina Faso.

        Returns:
            A list of new Alert objects.
        """
        all_new: list[Alert] = []
        # Deeply nest traversal over the entire nation's administrative tree
        for region_name in REGIONS:
            for province in PROVINCES.get(region_name, []):
                for commune in COMMUNES.get(province, []):
                    # Consolidate country-wide evaluations
                    all_new.extend(
                        self.detect_by_zone(
                            region_name, province, commune
                        )
                    )
                    
        # Commit all national alerts into permanent storage
        for alert in all_new:
            self.data_manager.add_alert(alert)
        return all_new


# ═══════════════════════════════════════════════════════════════════════════════
# ReportEngine
# ═══════════════════════════════════════════════════════════════════════════════

class ReportEngine:
    """Generates formatted epidemiological reports.

    Reports come in three flavours: zone, region, and national.  Each
    one includes case counts, patient statistics, and active alerts
    for the relevant geographic scope.

    Attributes:
        data_manager: Reference to the DataManager.
    """

    def __init__(self, data_manager: DataManager) -> None:
        """Initialise the report engine.

        Args:
            data_manager: The data source.
        """
        self.data_manager = data_manager # Store database context wrapper

    def generate_zone_report(
        self, region: str, province: str, commune: str
    ) -> str:
        """Generate a report for a single zone.

        Args:
            region:   Region name.
            province: Province name.
            commune:  Commune name.

        Returns:
            A formatted report string.
        """
        dm = self.data_manager
        
        # Pull required contextual subsets bound to the requested municipality
        cases = dm.get_cases_by_zone(region, province, commune)
        patients = [
            p for p in dm.patients
            if p.region == region
            and p.province == province
            and p.commune == commune
        ]
        active = [
            a for a in dm.get_active_alerts()
            if a.region == region
            and a.province == province
            and a.commune == commune
        ]
        
        # Stamp report header with exact current timestamp
        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        # Initialize buffer list to assemble document lines efficiently
        lines: list[str] = []
        w = 60 # Set document width boundary for ASCII formatting
        
        # Build Standardized Output Heading Structure
        lines.append("=" * w)
        lines.append("  EPIDEMIOLOGICAL REPORT  -  ZONE LEVEL")
        lines.append(f"  Region:    {region}")
        lines.append(f"  Province:  {province}")
        lines.append(f"  Commune:   {commune}")
        lines.append(f"  Date:      {now}")
        lines.append("=" * w)

        # Section 1: Aggregate Disease Data Block
        lines.append(
            f"\n  DISEASE CASES  ({len(cases)} records)"
        )
        lines.append("-" * 40)
        if cases:
            # Format and append statistics for each localized disease record
            for c in cases:
                lines.append(
                    f"  {c.disease}: {c.get_total_cases()} total"
                    f"  (Confirmed: {c.confirmed},"
                    f" Deceased: {c.deceased})"
                )
        else:
            lines.append(
                "  No disease cases recorded for this zone."
            )

        # Section 2: Clinical Status Metrics Block
        lines.append(
            f"\n  PATIENT STATISTICS  ({len(patients)} patients)"
        )
        lines.append("-" * 40)
        if patients:
            sc: dict[str, int] = {}
            # Consolidate raw statuses into numerical count buckets
            for p in patients:
                sc[p.get_status()] = sc.get(p.get_status(), 0) + 1
            # Dump the mapped status counts to the buffer
            for status, count in sc.items():
                lines.append(f"  {status}: {count}")
        else:
            lines.append(
                "  No patients registered for this zone."
            )

        # Section 3: Priority Notification Feed Block
        lines.append(f"\n  ACTIVE ALERTS  ({len(active)})")
        lines.append("-" * 40)
        if active:
            for a in active:
                # Indicate severity tier next to the disease identifier
                lines.append(f"  [{a.severity}] {a.disease}")
                lines.append(f"    {a.message}")
        else:
            lines.append("  No active alerts for this zone.")

        # Finish report and collapse buffer into a single printable text string
        lines.append("\n" + "=" * w)
        return "\n".join(lines)

    def generate_region_report(self, region: str) -> str:
        """Generate a regional epidemiological report.

        Args:
            region: Region name.

        Returns:
            A formatted report string.
        """
        dm = self.data_manager
        
        # Batch extract region-wide data aggregates
        cases = dm.get_cases_by_region(region)
        patients = [p for p in dm.patients if p.region == region]
        alerts = [
            a for a in dm.get_alerts_by_region(region)
            if a.is_active()
        ]
        
        # Calculate macro-level clinical outcomes
        total_conf = sum(c.confirmed for c in cases)
        total_dec = sum(c.deceased for c in cases)
        total_rec = sum(c.recovered for c in cases)
        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        lines: list[str] = []
        w = 60
        
        # Build Standardized Regional Document Header
        lines.append("=" * w)
        lines.append(
            "  EPIDEMIOLOGICAL REPORT  -  REGIONAL LEVEL"
        )
        lines.append(f"  Region:  {region}")
        # Automatically determine Capital location by querying dict lookup
        lines.append(
            f"  Capital: {REGIONS.get(region, 'N/A')}"
        )
        lines.append(f"  Date:    {now}")
        lines.append("=" * w)

        # Section 1: Summary Matrix
        lines.append("\n  SUMMARY")
        lines.append("-" * 40)
        lines.append(f"  Patients:       {len(patients)}")
        lines.append(f"  Case records:   {len(cases)}")
        lines.append(f"  Confirmed:      {total_conf}")
        lines.append(f"  Recovered:      {total_rec}")
        lines.append(f"  Deceased:       {total_dec}")
        
        # Compute and append specific mortality KPI metric safely
        if total_conf > 0:
            lines.append(
                f"  Mortality rate:"
                f" {(total_dec / total_conf) * 100:.1f}%"
            )

        # Section 2: Pathological Overview
        lines.append("\n  DISEASE BREAKDOWN")
        lines.append("-" * 40)
        dc: dict[str, int] = {}
        # Accumulate confirmed infection counts per condition
        for c in cases:
            dc[c.disease] = dc.get(c.disease, 0) + c.confirmed
            
        if dc:
            # Sort the dictionary descending to highlight the most prevalent issues
            for disease, count in sorted(
                dc.items(), key=lambda x: x[1], reverse=True
            ):
                lines.append(f"  {disease}: {count} confirmed")
        else:
            lines.append("  No disease data available.")

        # Section 3: Critical Area Heatmap (Alerts)
        lines.append(f"\n  ACTIVE ALERTS  ({len(alerts)})")
        lines.append("-" * 40)
        if alerts:
            for a in alerts:
                # Include exact nested geographic location reference
                lines.append(
                    f"  [{a.severity}] {a.disease}"
                    f" - {a.get_location()}"
                )
        else:
            lines.append(
                "  No active alerts for this region."
            )

        lines.append("\n" + "=" * w)
        return "\n".join(lines)

    def generate_national_report(self) -> str:
        """Generate a national epidemiological report.

        Returns:
            A formatted report string covering all 13 regions.
        """
        dm = self.data_manager
        
        # Compute grand totals summing over the entire nation's case tables
        all_conf = sum(c.confirmed for c in dm.cases)
        all_dec = sum(c.deceased for c in dm.cases)
        all_rec = sum(c.recovered for c in dm.cases)
        active = dm.get_active_alerts()
        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        lines: list[str] = []
        w = 60
        
        # Render National Command Center Dashboard Header
        lines.append("=" * w)
        lines.append("  NATIONAL EPIDEMIOLOGICAL REPORT")
        lines.append("  Burkina Faso")
        lines.append(f"  Date: {now}")
        lines.append("=" * w)

        # Section 1: Totalized Top-Level Metrics
        lines.append("\n  NATIONAL SUMMARY")
        lines.append("-" * 40)
        lines.append(f"  Regions covered:   {len(REGIONS)}")
        lines.append(f"  Total patients:    {dm.get_total_patients()}")
        lines.append(f"  Total confirmed:   {all_conf}")
        lines.append(f"  Total recovered:   {all_rec}")
        lines.append(f"  Total deceased:    {all_dec}")
        if all_conf > 0:
            lines.append(
                f"  Mortality rate:"
                f" {(all_dec / all_conf) * 100:.1f}%"
            )
        lines.append(f"  Active alerts:     {len(active)}")

        # Section 2: Regional Sub-Total Mapping
        lines.append("\n  REGIONAL BREAKDOWN")
        lines.append("-" * 40)
        pr = dm.count_by_region()
        # Ensure alignment with official constant mapping sequence
        for r in REGIONS:
            lines.append(f"  {r}: {pr.get(r, 0)} patients")

        # Section 3: National Threat Analysis (Disease frequencies)
        lines.append("\n  DISEASE DISTRIBUTION")
        lines.append("-" * 40)
        dd = dm.count_by_disease()
        # Sequence list prioritized by highest patient load
        for disease, count in sorted(
            dd.items(), key=lambda x: x[1], reverse=True
        ):
            lines.append(f"  {disease}: {count} patients")

        # Section 4: Full State of Emergency Tracker
        lines.append(f"\n  ALL ACTIVE ALERTS  ({len(active)})")
        lines.append("-" * 40)
        if active:
            for a in active:
                # Output complete spatial and quantitative footprint of anomalies
                lines.append(
                    f"  [{a.severity}] {a.disease}"
                    f" - {a.get_location()}"
                    f" ({a.case_count} cases)"
                )
        else:
            lines.append("  No active alerts nationwide.")

        lines.append("\n" + "=" * w)
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# ReportExporter (inherits from ReportEngine)
# ═══════════════════════════════════════════════════════════════════════════════

class ReportExporter(ReportEngine):
    """Exports epidemiological reports to .txt and .md files.

    Inherits all the report-generation logic from ReportEngine and
    adds the ability to write output to the outputs/ directory.
    Every exported report is also auto-classified into the
    classeurs/ directory structure for safe archiving.

    The .md files are black-and-white, professionally formatted
    documents with structured tables, suitable for analysis by
    health professionals.

    Attributes:
        data_manager: Reference to the DataManager.
    """

    def __init__(self, data_manager: DataManager) -> None:
        """Initialise the exporter.

        Args:
            data_manager: The data source.
        """
        # Call the parent ReportEngine constructor to inherit instance variables
        super().__init__(data_manager)

    # -- .txt export ------------------------------------------------------------

    def export_zone_report(
        self, region: str, province: str, commune: str
    ) -> str:
        """Export a zone-level .txt report.

        Args:
            region:   Region name.
            province: Province name.
            commune:  Commune name.

        Returns:
            The file path on success, or "" on failure.
        """
        # Compute the raw report body text utilizing parent class methods
        report = self.generate_zone_report(region, province, commune)
        
        # Cleanly structure physical file name preventing forbidden path characters
        safe = _safe(f"zone_{region}_{province}_{commune}")
        path = os.path.join(OUTPUTS_DIR, f"{safe}_report.txt")
        
        # Write flat representation and dispatch duplicate to internal archives
        if _write_file(path, report):
            _archive_copy(
                report, f"{safe}_report.txt",
                region, province,
            )
            return path
        return ""

    def export_region_report(self, region: str) -> str:
        """Export a regional .txt report.

        Args:
            region: Region name.

        Returns:
            The file path on success, or "" on failure.
        """
        # Execute text block compilation and assign it to memory variable
        report = self.generate_region_report(region)
        
        # Sanitize identifier string to avoid OS-level routing exceptions
        safe = _safe(f"region_{region}")
        path = os.path.join(OUTPUTS_DIR, f"{safe}_report.txt")
        
        # Finalize storage write operation and archive simultaneously
        if _write_file(path, report):
            _archive_copy(
                report, f"{safe}_report.txt", region,
            )
            return path
        return ""

    def export_national_report(self) -> str:
        """Export a national .txt report.

        Returns:
            The file path on success, or "" on failure.
        """
        # Instruct base generator to map standard macroscopic report layout
        report = self.generate_national_report()
        # Hardcode canonical filename destination inside designated flat directory
        path = os.path.join(OUTPUTS_DIR, "national_report.txt")
        
        # Commit byte stream entirely without deep archiving checks
        _write_file(path, report)
        return path

    # -- .md export (black-and-white, professional) -----------------------------

    def export_zone_md(
        self, region: str, province: str, commune: str
    ) -> str:
        """Export a zone-level Markdown report.

        The .md file is formatted for professional analysis:
