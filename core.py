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

from __future__ import annotations

import os
from collections import Counter, defaultdict
from datetime import datetime
from functools import lru_cache
from typing import Optional

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
from models import Alert, DiseaseCase, Patient

__all__ = [
    "DataManager",
    "EpidemicDetector",
    "ReportEngine",
    "ReportExporter",
    "Analytics",
    "_safe",
    "_write_file",
    "_archive_copy",
]


# Module-level helpers


@lru_cache(maxsize=256)
def _safe(name: str) -> str:
    """Make a string safe for use as a file or directory name.

    Replaces spaces, apostrophes, and slashes with underscores.
    Cached because the same region/province names are reused
    heavily throughout the application.

    Args:
        name: The raw string.

    Returns:
        A filesystem-safe string.
    """
    return (
        name.replace(" ", "_")
        .replace("'", "")
        .replace("/", "_")
    )


def _write_file(path: str, content: str) -> bool:
    """Write content to a file, creating parent dirs if needed.

    Args:
        path:    Absolute file path.
        content: Text content to write.

    Returns:
        True on success, False on I/O error.
    """
    try:
        parent: str = os.path.dirname(path)
        if parent and not os.path.exists(parent):
            os.makedirs(parent, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
        return True
    except (IOError, OSError):
        return False


def _archive_copy(
    content: str,
    filename: str,
    region: str,
    province: str = "",
) -> None:
    """Save a copy of the report into the classeurs directory tree.

    Reports are filed under classeurs/<region>/<province>/ so they
    are easy to find by geographic area.  This prevents data loss
    -- even if the quick-access copy in outputs/ is deleted, the
    archived version in classeurs/ remains.

    Args:
        content:  The report text.
        filename: Original filename (used as-is in the archive).
        region:   Region name for the top-level folder.
        province: Province name for the subfolder (optional).
    """
    if province:
        dest_dir: str = os.path.join(
            CLASSEURS_DIR, _safe(region), _safe(province)
        )
    else:
        dest_dir = os.path.join(CLASSEURS_DIR, _safe(region))
    os.makedirs(dest_dir, exist_ok=True)
    _write_file(os.path.join(dest_dir, filename), content)


# DataManager


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
        self.patients: list[Patient] = []
        self.cases: list[DiseaseCase] = []
        self.alerts: list[Alert] = []

        # Indexes -- rebuilt after every load
        self._patient_index: dict[int, Patient] = {}
        self._cases_by_region: dict[str, list[DiseaseCase]] = {}
        self._cases_by_disease: dict[str, list[DiseaseCase]] = {}

        self._ensure_dirs()
        self._load_patients()
        self._load_cases()
        self._load_alerts()
        self._rebuild_indexes()

    # Private: directory setup

    def _ensure_dirs(self) -> None:
        """Create data/, outputs/, and classeurs/ directories if missing."""
        for d in (DATA_DIR, OUTPUTS_DIR, CLASSEURS_DIR):
            if not os.path.exists(d):
                os.makedirs(d, exist_ok=True)
        # Create region subfolders inside classeurs
        for region_name in REGIONS:
            rdir: str = os.path.join(CLASSEURS_DIR, _safe(region_name))
            os.makedirs(rdir, exist_ok=True)
            # Province subfolders
            for prov in PROVINCES.get(region_name, []):
                pdir: str = os.path.join(rdir, _safe(prov))
                os.makedirs(pdir, exist_ok=True)

    # Private: index management

    def _rebuild_indexes(self) -> None:
        """Rebuild lookup dictionaries from the current lists.

        Optimised to iterate over self.cases only once, building
        both the region index and the disease index in the same
        pass.  This halves the number of iterations compared to
        building each index separately.
        """
        self._patient_index = {p.patient_id: p for p in self.patients}

        # Single pass through self.cases for both indexes
        by_region: dict[str, list[DiseaseCase]] = defaultdict(list)
        by_disease: dict[str, list[DiseaseCase]] = defaultdict(list)
        for c in self.cases:
            by_region[c.region].append(c)
            by_disease[c.disease].append(c)

        # Convert defaultdicts back to plain dicts so .get() behaves
        # exactly as callers expect (returns [] instead of KeyError)
        self._cases_by_region = dict(by_region)
        self._cases_by_disease = dict(by_disease)

    # Patient operations

    def _load_patients(self) -> None:
        """Load patient records from the .txt file into memory."""
        self.patients = []
        if not os.path.exists(PATIENTS_FILE):
            return
        try:
            with open(PATIENTS_FILE, "r", encoding="utf-8") as fh:
                for line in fh:
                    patient: Optional[Patient] = Patient.from_file_line(line)
                    if patient is not None:
                        self.patients.append(patient)
        except (IOError, OSError):
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
            with open(PATIENTS_FILE, "w", encoding="utf-8") as fh:
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
                for p in self.patients:
                    fh.write(p.to_file_line() + "\n")
            return True
        except (IOError, OSError):
            return False

    def add_patient(self, patient: Patient) -> int:
        """Add a new patient and persist to disk.

        The patient_id is auto-assigned as max(existing_ids) + 1.
        We also update the index right away.

        Args:
            patient: A Patient object (patient_id may be 0).

        Returns:
            The assigned ID, or -1 if the save failed.
        """
        next_id: int = max(
            (p.patient_id for p in self.patients), default=0
        ) + 1
        patient.patient_id = next_id
        self.patients.append(patient)
        self._patient_index[next_id] = patient
        return next_id if self.save_patients() else -1

    def add_patients(self, patients: list[Patient]) -> list[int]:
        """Add multiple patients in a single batch and persist once.

        This is far more efficient than calling add_patient() in a
        loop because it writes to disk only once after all patients
        have been added to the in-memory list and index.

        Args:
            patients: A list of Patient objects (patient_id may be 0).

        Returns:
            A list of assigned IDs in the same order as input.
            Individual entries are -1 if the overall save failed.
        """
        if not patients:
            return []
        # Determine the starting ID for this batch
        base_id: int = max(
            (p.patient_id for p in self.patients), default=0
        ) + 1
        assigned_ids: list[int] = []
        for i, patient in enumerate(patients):
            pid: int = base_id + i
            patient.patient_id = pid
            self.patients.append(patient)
            self._patient_index[pid] = patient
            assigned_ids.append(pid)
        # Single disk write for the entire batch
        if not self.save_patients():
            return [-1] * len(patients)
        return assigned_ids

    def find_patient_by_id(self, patient_id: int) -> Optional[Patient]:
        """Look up a patient by ID using the index (O(1) lookup).

        Args:
            patient_id: The numeric ID to search for.

        Returns:
            The matching Patient, or None if not found.
        """
        return self._patient_index.get(patient_id)

    def search_patients(self, query: str) -> list[Patient]:
        """Search patients by name, disease, or region (case-insensitive).

        Args:
            query: Free-text search term.

        Returns:
            A list of matching Patient objects.
        """
        q: str = query.lower()
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
        patient: Optional[Patient] = self.find_patient_by_id(patient_id)
        if patient is None:
            return False
        if not patient.set_status(new_status):
            return False
        return self.save_patients()

    # Disease-case operations

    def _load_cases(self) -> None:
        """Load disease-case records from the .txt file."""
        self.cases = []
        if not os.path.exists(CASES_FILE):
            return
        try:
            with open(CASES_FILE, "r", encoding="utf-8") as fh:
                for line in fh:
                    case: Optional[DiseaseCase] = DiseaseCase.from_file_line(line)
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
                for c in self.cases:
                    fh.write(c.to_file_line() + "\n")
            return True
        except (IOError, OSError):
            return False

    def add_case(self, case: DiseaseCase) -> int:
        """Add a new disease case and persist to disk.

        The case_id is auto-assigned as max(existing_ids) + 1.
        We also update the indexes right away.

        Args:
            case: A DiseaseCase object (case_id may be 0).

        Returns:
            The assigned ID, or -1 if the save failed.
        """
        next_id: int = max(
            (c.case_id for c in self.cases), default=0
        ) + 1
        case.case_id = next_id
        self.cases.append(case)
        # Update both indexes incrementally
        self._cases_by_region.setdefault(case.region, []).append(case)
        self._cases_by_disease.setdefault(case.disease, []).append(case)
        return next_id if self.save_cases() else -1

    def add_cases(self, cases: list[DiseaseCase]) -> list[int]:
        """Add multiple disease cases in a single batch and persist once.

        More efficient than calling add_case() in a loop because it
        writes to disk only once after all cases have been added.

        Args:
            cases: A list of DiseaseCase objects (case_id may be 0).

        Returns:
            A list of assigned IDs in the same order as input.
            Individual entries are -1 if the overall save failed.
        """
        if not cases:
            return []
        base_id: int = max(
            (c.case_id for c in self.cases), default=0
        ) + 1
        assigned_ids: list[int] = []
        for i, case in enumerate(cases):
            cid: int = base_id + i
            case.case_id = cid
            self.cases.append(case)
            self._cases_by_region.setdefault(case.region, []).append(case)
            self._cases_by_disease.setdefault(case.disease, []).append(case)
            assigned_ids.append(cid)
        if not self.save_cases():
            return [-1] * len(cases)
        return assigned_ids

    def get_cases_by_region(self, region: str) -> list[DiseaseCase]:
        """Return all cases for a given region using the index."""
        return self._cases_by_region.get(region, [])

    def get_cases_by_disease(self, disease: str) -> list[DiseaseCase]:
        """Return all cases for a given disease using the index."""
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
        region_cases: list[DiseaseCase] = self._cases_by_region.get(region, [])
        return [
            c for c in region_cases
            if c.province.lower() == province.lower()
            and c.commune.lower() == commune.lower()
        ]

    def aggregate_cases(self) -> dict[str, dict[str, int]]:
        """Aggregate confirmed cases by disease and region.

        Uses defaultdict to avoid repeated setdefault calls
        when building the nested structure.

        Returns:
            A nested dict: disease -> region -> total_confirmed.
        """
        # Nested defaultdict for concise aggregation
        result: dict[str, dict[str, int]] = defaultdict(
            lambda: defaultdict(int)  # type: ignore[assignment]
        )
        for case in self.cases:
            result[case.disease][case.region] += case.confirmed
        # Convert inner defaultdicts to plain dicts for callers
        return {d: dict(r) for d, r in result.items()}

    # Alert operations

    def _load_alerts(self) -> None:
        """Load alert records from the .txt file."""
        self.alerts = []
        if not os.path.exists(ALERTS_FILE):
            return
        try:
            with open(ALERTS_FILE, "r", encoding="utf-8") as fh:
                for line in fh:
                    alert: Optional[Alert] = Alert.from_file_line(line)
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
        next_id: int = max(
            (a.alert_id for a in self.alerts), default=0
        ) + 1
        alert.alert_id = next_id
        self.alerts.append(alert)
        return next_id if self.save_alerts() else -1

    def get_active_alerts(self) -> list[Alert]:
        """Return all alerts that are currently active."""
        return [a for a in self.alerts if a.is_active()]

    def get_alerts_by_region(self, region: str) -> list[Alert]:
        """Return all alerts for a given region."""
        return [
            a for a in self.alerts
            if a.region.lower() == region.lower()
        ]

    # Statistics

    def get_total_patients(self) -> int:
        """Return the total number of patient records."""
        return len(self.patients)

    def count_by_status(self) -> dict[str, int]:
        """Count patients grouped by status.

        Uses collections.Counter for concise and efficient tallying.
        """
        return Counter(p.get_status() for p in self.patients)

    def count_by_region(self) -> dict[str, int]:
        """Count patients grouped by region.

        Uses collections.Counter for concise and efficient tallying.
        """
        return Counter(p.region for p in self.patients)

    def count_by_disease(self) -> dict[str, int]:
        """Count patients grouped by disease.

        Uses collections.Counter for concise and efficient tallying.
        """
        return Counter(p.disease for p in self.patients)


# EpidemicDetector


class EpidemicDetector:
    """Detects epidemics by comparing case counts to thresholds.

    Severity rules:
        Warning   -- cases exceed threshold by 1-50 %
        Critical  -- cases exceed threshold by 51-100 %
        Emergency -- cases exceed threshold by > 100 %

    Attributes:
        data_manager: Reference to the DataManager.
    """

    def __init__(self, data_manager: DataManager) -> None:
        """Initialise the detector.

        Args:
            data_manager: The data source for case records.
        """
        self.data_manager: DataManager = data_manager

    @staticmethod
    @lru_cache(maxsize=512)
    def determine_severity(
        case_count: int, threshold: int
    ) -> str:
        """Figure out the severity level from the excess ratio.

        Cached because the same (case_count, threshold) pairs are
        frequently recomputed across zones and regions.

        Args:
            case_count: Current number of confirmed cases.
            threshold:  Epidemic threshold for the disease.

        Returns:
            "Warning", "Critical", or "Emergency".
        """
        if threshold == 0:
            return "Emergency"
        excess: float = ((case_count - threshold) / threshold) * 100.0
        if excess <= 50.0:
            return "Warning"
        if excess <= 100.0:
            return "Critical"
        return "Emergency"

    def detect_by_zone(
        self, region: str, province: str, commune: str
    ) -> list[Alert]:
        """Detect epidemics in a single geographic zone.

        Uses defaultdict to accumulate confirmed case counts per
        disease in a single pass, avoiding manual dict.get() calls.

        Args:
            region:   Region name.
            province: Province name.
            commune:  Commune name.

        Returns:
            A list of newly created Alert objects.
        """
        new_alerts: list[Alert] = []
        zone_cases: list[DiseaseCase] = self.data_manager.get_cases_by_zone(
            region, province, commune
        )

        # Tally confirmed cases per disease using defaultdict
        totals: dict[str, int] = defaultdict(int)
        for case in zone_cases:
            totals[case.disease] += case.confirmed

        for disease, total_confirmed in totals.items():
            threshold: int = DISEASE_THRESHOLDS.get(disease, 999)
            if total_confirmed > threshold:
                severity: str = self.determine_severity(
                    total_confirmed, threshold
                )
                message: str = (
                    f"EPIDEMIC ALERT: {disease} cases in "
                    f"{region} / {province} / {commune} have "
                    f"exceeded the threshold "
                    f"({total_confirmed} cases vs. "
                    f"threshold of {threshold})."
                )
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
        for province in PROVINCES.get(region, []):
            for commune in COMMUNES.get(province, []):
                all_new.extend(
                    self.detect_by_zone(region, province, commune)
                )
        for alert in all_new:
            self.data_manager.add_alert(alert)
        return all_new

    def detect_all_regions(self) -> list[Alert]:
        """Detect epidemics across all regions of Burkina Faso.

        Returns:
            A list of new Alert objects.
        """
        all_new: list[Alert] = []
        for region_name in REGIONS:
            for province in PROVINCES.get(region_name, []):
                for commune in COMMUNES.get(province, []):
                    all_new.extend(
                        self.detect_by_zone(
                            region_name, province, commune
                        )
                    )
        for alert in all_new:
            self.data_manager.add_alert(alert)
        return all_new


# ReportEngine


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
        self.data_manager: DataManager = data_manager

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
        dm: DataManager = self.data_manager
        cases: list[DiseaseCase] = dm.get_cases_by_zone(region, province, commune)
        patients: list[Patient] = [
            p for p in dm.patients
            if p.region == region
            and p.province == province
            and p.commune == commune
        ]
        active: list[Alert] = [
            a for a in dm.get_active_alerts()
            if a.region == region
            and a.province == province
            and a.commune == commune
        ]
        now: str = datetime.now().strftime("%Y-%m-%d %H:%M")

        lines: list[str] = []
        w: int = 60
        lines.append("=" * w)
        lines.append("  EPIDEMIOLOGICAL REPORT  -  ZONE LEVEL")
        lines.append(f"  Region:    {region}")
        lines.append(f"  Province:  {province}")
        lines.append(f"  Commune:   {commune}")
        lines.append(f"  Date:      {now}")
        lines.append("=" * w)

        lines.append(
            f"\n  DISEASE CASES  ({len(cases)} records)"
        )
        lines.append("-" * 40)
        if cases:
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

        lines.append(
            f"\n  PATIENT STATISTICS  ({len(patients)} patients)"
        )
        lines.append("-" * 40)
        if patients:
            # Counter is cleaner than manual dict.get() tallies
            sc: Counter[str] = Counter(p.get_status() for p in patients)
            for status, count in sc.items():
                lines.append(f"  {status}: {count}")
        else:
            lines.append(
                "  No patients registered for this zone."
            )

        lines.append(f"\n  ACTIVE ALERTS  ({len(active)})")
        lines.append("-" * 40)
        if active:
            for a in active:
                lines.append(f"  [{a.severity}] {a.disease}")
                lines.append(f"    {a.message}")
        else:
            lines.append("  No active alerts for this zone.")

        lines.append("\n" + "=" * w)
        return "\n".join(lines)

    def generate_region_report(self, region: str) -> str:
        """Generate a regional epidemiological report.

        Args:
            region: Region name.

        Returns:
            A formatted report string.
        """
        dm: DataManager = self.data_manager
        cases: list[DiseaseCase] = dm.get_cases_by_region(region)
        patients: list[Patient] = [p for p in dm.patients if p.region == region]
        alerts: list[Alert] = [
            a for a in dm.get_alerts_by_region(region)
            if a.is_active()
        ]
        total_conf: int = sum(c.confirmed for c in cases)
        total_dec: int = sum(c.deceased for c in cases)
        total_rec: int = sum(c.recovered for c in cases)
        now: str = datetime.now().strftime("%Y-%m-%d %H:%M")

        lines: list[str] = []
        w: int = 60
        lines.append("=" * w)
        lines.append(
            "  EPIDEMIOLOGICAL REPORT  -  REGIONAL LEVEL"
        )
        lines.append(f"  Region:  {region}")
        lines.append(
            f"  Capital: {REGIONS.get(region, 'N/A')}"
        )
        lines.append(f"  Date:    {now}")
        lines.append("=" * w)

        lines.append("\n  SUMMARY")
        lines.append("-" * 40)
        lines.append(f"  Patients:       {len(patients)}")
        lines.append(f"  Case records:   {len(cases)}")
        lines.append(f"  Confirmed:      {total_conf}")
        lines.append(f"  Recovered:      {total_rec}")
        lines.append(f"  Deceased:       {total_dec}")
        if total_conf > 0:
            lines.append(
                f"  Mortality rate:"
                f" {(total_dec / total_conf) * 100:.1f}%"
            )

        lines.append("\n  DISEASE BREAKDOWN")
        lines.append("-" * 40)
        # Counter efficiently aggregates confirmed counts per disease
        dc: Counter[str] = Counter()
        for c in cases:
            dc[c.disease] += c.confirmed
        if dc:
            for disease, count in sorted(
                dc.items(), key=lambda x: x[1], reverse=True
            ):
                lines.append(f"  {disease}: {count} confirmed")
        else:
            lines.append("  No disease data available.")

        lines.append(f"\n  ACTIVE ALERTS  ({len(alerts)})")
        lines.append("-" * 40)
        if alerts:
            for a in alerts:
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
        dm: DataManager = self.data_manager
        all_conf: int = sum(c.confirmed for c in dm.cases)
        all_dec: int = sum(c.deceased for c in dm.cases)
        all_rec: int = sum(c.recovered for c in dm.cases)
        active: list[Alert] = dm.get_active_alerts()
        now: str = datetime.now().strftime("%Y-%m-%d %H:%M")

        lines: list[str] = []
        w: int = 60
        lines.append("=" * w)
        lines.append("  NATIONAL EPIDEMIOLOGICAL REPORT")
        lines.append("  Burkina Faso")
        lines.append(f"  Date: {now}")
        lines.append("=" * w)

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

        lines.append("\n  REGIONAL BREAKDOWN")
        lines.append("-" * 40)
        pr: dict[str, int] = dm.count_by_region()
        for r in REGIONS:
            lines.append(f"  {r}: {pr.get(r, 0)} patients")

        lines.append("\n  DISEASE DISTRIBUTION")
        lines.append("-" * 40)
        dd: dict[str, int] = dm.count_by_disease()
        for disease, count in sorted(
            dd.items(), key=lambda x: x[1], reverse=True
        ):
            lines.append(f"  {disease}: {count} patients")

        lines.append(f"\n  ALL ACTIVE ALERTS  ({len(active)})")
        lines.append("-" * 40)
        if active:
            for a in active:
                lines.append(
                    f"  [{a.severity}] {a.disease}"
                    f" - {a.get_location()}"
                    f" ({a.case_count} cases)"
                )
        else:
            lines.append("  No active alerts nationwide.")

        lines.append("\n" + "=" * w)
        return "\n".join(lines)


# ReportExporter (inherits from ReportEngine)


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
        super().__init__(data_manager)

    # .txt export

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
        report: str = self.generate_zone_report(region, province, commune)
        safe: str = _safe(f"zone_{region}_{province}_{commune}")
        path: str = os.path.join(OUTPUTS_DIR, f"{safe}_report.txt")
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
        report: str = self.generate_region_report(region)
        safe: str = _safe(f"region_{region}")
        path: str = os.path.join(OUTPUTS_DIR, f"{safe}_report.txt")
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
        report: str = self.generate_national_report()
        path: str = os.path.join(OUTPUTS_DIR, "national_report.txt")
        _write_file(path, report)
        return path

    # .md export (black-and-white, professional)

    def export_zone_md(
        self, region: str, province: str, commune: str
    ) -> str:
        """Export a zone-level Markdown report.

        The .md file is formatted for professional analysis:
        no colours, structured tables, clear layout.

        Args:
            region:   Region name.
            province: Province name.
            commune:  Commune name.

        Returns:
            The file path on success, or "" on failure.
        """
        md: str = self._zone_md(region, province, commune)
        safe: str = _safe(f"zone_{region}_{province}_{commune}")
        path: str = os.path.join(OUTPUTS_DIR, f"{safe}_report.md")
        if _write_file(path, md):
            _archive_copy(
                md, f"{safe}_report.md", region, province,
            )
            return path
        return ""

    def export_region_md(self, region: str) -> str:
        """Export a regional Markdown report.

        Args:
            region: Region name.

        Returns:
            The file path on success, or "" on failure.
        """
        md: str = self._region_md(region)
        safe: str = _safe(f"region_{region}")
        path: str = os.path.join(OUTPUTS_DIR, f"{safe}_report.md")
        if _write_file(path, md):
            _archive_copy(
                md, f"{safe}_report.md", region,
            )
            return path
        return ""

    def export_national_md(self) -> str:
        """Export a national Markdown report.

        Returns:
            The file path on success, or "" on failure.
        """
        md: str = self._national_md()
        path: str = os.path.join(OUTPUTS_DIR, "national_report.md")
        _write_file(path, md)
        return path

    # MD generation helpers

    @staticmethod
    def _md_header(
        title: str, subtitle: str = ""
    ) -> str:
        """Generate a standard Markdown header block.

        Includes Burkina Faso, the national motto, and EpiAlert
        branding at the top of every exported .md document.

        Args:
            title:    Report title.
            subtitle: Optional subtitle (e.g. region name).

        Returns:
            A formatted Markdown header string.
        """
        now: str = datetime.now().strftime("%Y-%m-%d %H:%M")
        lines: list[str] = [
            "# BURKINA FASO",
            f"## {MOTTO_FR}",
            f"*{MOTTO_EN}*",
            "",
            "---",
            "",
            f"### EpiAlert — {title}",
        ]
        if subtitle:
            lines.append(f"**{subtitle}**")
        lines.extend([
            f"Generated: {now}",
            "",
            "---",
            "",
        ])
        return "\n".join(lines)

    def _zone_md(
        self, region: str, province: str, commune: str
    ) -> str:
        """Generate a zone-level Markdown report.

        Args:
            region:   Region name.
            province: Province name.
            commune:  Commune name.

        Returns:
            A formatted Markdown string.
        """
        dm: DataManager = self.data_manager
        cases: list[DiseaseCase] = dm.get_cases_by_zone(region, province, commune)
        patients: list[Patient] = [
            p for p in dm.patients
            if p.region == region
            and p.province == province
            and p.commune == commune
        ]
        active: list[Alert] = [
            a for a in dm.get_active_alerts()
            if a.region == region
            and a.province == province
            and a.commune == commune
        ]

        lines: list[str] = [
            self._md_header(
                "Zone Epidemiological Report",
                f"{region} / {province} / {commune}",
            ),
            "## Disease Cases",
            "",
        ]

        if cases:
            lines.append(
                "| Disease | Total | Suspected | Confirmed"
                " | Recovered | Deceased |"
            )
            lines.append(
                "|---------|-------|-----------|----------"
                "|-----------|----------|"
            )
            for c in cases:
                lines.append(
                    f"| {c.disease} | {c.get_total_cases()}"
                    f" | {c.suspected} | {c.confirmed}"
                    f" | {c.recovered} | {c.deceased} |"
                )
        else:
            lines.append("No disease cases recorded.")

        lines.extend([
            "",
            "## Patient Statistics",
            "",
        ])

        if patients:
            lines.append(
                "| Status | Count |"
            )
            lines.append(
                "|--------|-------|"
            )
            # Counter provides a clean one-liner for status tallies
            sc: Counter[str] = Counter(p.get_status() for p in patients)
            for status, count in sc.items():
                lines.append(f"| {status} | {count} |")
        else:
            lines.append("No patients registered.")

        lines.extend([
            "",
            f"## Active Alerts ({len(active)})",
            "",
        ])
        if active:
            for a in active:
                lines.append(
                    f"- **[{a.severity}]** {a.disease}"
                    f" — {a.case_count} cases"
                    f" (threshold: {a.threshold})"
                )
        else:
            lines.append("No active alerts.")

        return "\n".join(lines)

    def _region_md(self, region: str) -> str:
        """Generate a regional Markdown report.

        Args:
            region: Region name.

        Returns:
            A formatted Markdown string.
        """
        dm: DataManager = self.data_manager
        cases: list[DiseaseCase] = dm.get_cases_by_region(region)
        patients: list[Patient] = [p for p in dm.patients if p.region == region]
        alerts: list[Alert] = [
            a for a in dm.get_alerts_by_region(region)
            if a.is_active()
        ]
        total_conf: int = sum(c.confirmed for c in cases)
        total_dec: int = sum(c.deceased for c in cases)
        total_rec: int = sum(c.recovered for c in cases)

        lines: list[str] = [
            self._md_header(
                "Regional Epidemiological Report",
                f"{region} (Capital: {REGIONS.get(region, 'N/A')})",
            ),
            "## Summary",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Patients | {len(patients)} |",
            f"| Case records | {len(cases)} |",
            f"| Confirmed | {total_conf} |",
            f"| Recovered | {total_rec} |",
            f"| Deceased | {total_dec} |",
        ]
        if total_conf > 0:
            lines.append(
                f"| Mortality rate"
                f" | {(total_dec / total_conf) * 100:.1f}% |"
            )

        lines.extend([
            "",
            "## Disease Breakdown",
            "",
            "| Disease | Confirmed cases |",
            "|---------|----------------|",
        ])
        # Counter handles disease-case aggregation concisely
        dc: Counter[str] = Counter()
        for c in cases:
            dc[c.disease] += c.confirmed
        for disease, count in sorted(
            dc.items(), key=lambda x: x[1], reverse=True
        ):
            lines.append(f"| {disease} | {count} |")

        lines.extend([
            "",
            f"## Active Alerts ({len(alerts)})",
            "",
        ])
        if alerts:
            for a in alerts:
                lines.append(
                    f"- **[{a.severity}]** {a.disease}"
                    f" — {a.get_location()}"
                )
        else:
            lines.append("No active alerts.")

        return "\n".join(lines)

    def _national_md(self) -> str:
        """Generate a national Markdown report.

        Returns:
            A formatted Markdown string.
        """
        dm: DataManager = self.data_manager
        all_conf: int = sum(c.confirmed for c in dm.cases)
        all_dec: int = sum(c.deceased for c in dm.cases)
        all_rec: int = sum(c.recovered for c in dm.cases)
        active: list[Alert] = dm.get_active_alerts()

        lines: list[str] = [
            self._md_header("National Epidemiological Report"),
            "## National Summary",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Regions covered | {len(REGIONS)} |",
            f"| Total patients | {dm.get_total_patients()} |",
            f"| Total confirmed | {all_conf} |",
            f"| Total recovered | {all_rec} |",
            f"| Total deceased | {all_dec} |",
        ]
        if all_conf > 0:
            lines.append(
                f"| Mortality rate"
                f" | {(all_dec / all_conf) * 100:.1f}% |"
            )
        lines.append(f"| Active alerts | {len(active)} |")

        lines.extend([
            "",
            "## Regional Breakdown",
            "",
            "| Region | Patients |",
            "|--------|----------|",
        ])
        pr: dict[str, int] = dm.count_by_region()
        for r in REGIONS:
            lines.append(f"| {r} | {pr.get(r, 0)} |")

        lines.extend([
            "",
            "## Disease Distribution",
            "",
            "| Disease | Patients |",
            "|---------|----------|",
        ])
        dd: dict[str, int] = dm.count_by_disease()
        for disease, count in sorted(
            dd.items(), key=lambda x: x[1], reverse=True
        ):
            lines.append(f"| {disease} | {count} |")

        lines.extend([
            "",
            f"## Active Alerts ({len(active)})",
            "",
        ])
        if active:
            lines.append(
                "| Severity | Disease | Location | Cases |"
            )
            lines.append(
                "|----------|---------|----------|-------|"
            )
            for a in active:
                lines.append(
                    f"| {a.severity} | {a.disease}"
                    f" | {a.get_location()} | {a.case_count} |"
                )
        else:
            lines.append("No active alerts nationwide.")

        return "\n".join(lines)


# Analytics


class Analytics:
    """Statistical analysis and dashboard data provider.

    Pulls aggregate stats from the DataManager -- disease distribution,
    regional distribution, mortality rates, weekly trends, and alert
    summaries.

    Attributes:
        data_manager: Reference to the DataManager.
    """

    def __init__(self, data_manager: DataManager) -> None:
        """Initialise the analytics engine.

        Args:
            data_manager: The data source.
        """
        self.data_manager: DataManager = data_manager

    def get_disease_distribution(self) -> dict[str, int]:
        """Return patient counts grouped by disease."""
        return self.data_manager.count_by_disease()

    def get_regional_distribution(self) -> dict[str, int]:
        """Return patient counts grouped by region."""
        return self.data_manager.count_by_region()

    def get_status_distribution(self) -> dict[str, int]:
        """Return patient counts grouped by status."""
        return self.data_manager.count_by_status()

    def get_mortality_by_disease(self) -> dict[str, float]:
        """Calculate mortality rate per disease.

        Uses Counter for efficient tallying of both total and
        deceased patients per disease in a single pass.

        Returns:
            A dict disease -> mortality_percentage.
        """
        total: Counter[str] = Counter()
        deceased: Counter[str] = Counter()
        for p in self.data_manager.patients:
            total[p.disease] += 1
            if p.get_status() == "Deceased":
                deceased[p.disease] += 1
        return {
            d: (deceased.get(d, 0) / total[d]) * 100.0
            for d in total
            if total[d] > 0
        }

    def get_weekly_trend(
        self, disease: str
    ) -> list[tuple[int, int]]:
        """Return the weekly confirmed-case trend for a disease.

        Uses defaultdict to avoid dict.get() calls when
        accumulating per-week counts.

        Args:
            disease: Disease name.

        Returns:
            A list of (week_number, confirmed_cases) tuples.
        """
        weekly: dict[int, int] = defaultdict(int)  # type: ignore[assignment]
        for c in self.data_manager.cases:
            if c.disease == disease:
                weekly[c.week_number] += c.confirmed
        return sorted(weekly.items())

    def get_top_regions(
        self, limit: int = 5
    ) -> list[tuple[str, int]]:
        """Return the top regions by patient count.

        Args:
            limit: Maximum number of regions to return.

        Returns:
            A list of (region, count) tuples in descending order.
        """
        return sorted(
            self.get_regional_distribution().items(),
            key=lambda x: x[1],
            reverse=True,
        )[:limit]

    def get_alert_summary(self) -> dict[str, int]:
        """Return alert counts grouped by severity level.

        Uses Counter for a concise one-liner aggregation.
        """
        summary: Counter[str] = Counter(
            a.severity for a in self.data_manager.get_active_alerts()
        )
        # Ensure all three severity levels appear even if count is 0
        for level in ("Warning", "Critical", "Emergency"):
            summary.setdefault(level, 0)
        return dict(summary)

    def generate_dashboard(self) -> str:
        """Generate a text-based analytics dashboard.

        Returns:
            A formatted dashboard string with key metrics, charts,
            and alert summary.
        """
        dm: DataManager = self.data_manager
        now: str = datetime.now().strftime("%Y-%m-%d %H:%M")
        w: int = 60

        lines: list[str] = []
        lines.append("=" * w)
        lines.append("  EPIALERT  ANALYTICS  DASHBOARD")
        lines.append(f"  Last updated: {now}")
        lines.append("=" * w)

        lines.append("\n  KEY METRICS")
        lines.append("-" * 40)
        lines.append(f"  Total patients:  {dm.get_total_patients()}")
        lines.append(
            f"  Active alerts:   {len(dm.get_active_alerts())}"
        )

        lines.append("\n  STATUS DISTRIBUTION")
        lines.append("-" * 40)
        for status, count in self.get_status_distribution().items():
            bar: str = "#" * count
            lines.append(f"  {status:12s} | {bar} ({count})")

        lines.append("\n  DISEASE DISTRIBUTION")
        lines.append("-" * 40)
        for disease, count in sorted(
            self.get_disease_distribution().items(),
            key=lambda x: x[1],
            reverse=True,
        ):
            bar = "#" * count
            lines.append(
                f"  {disease:45s} | {bar} ({count})"
            )

        lines.append("\n  MORTALITY RATE BY DISEASE")
        lines.append("-" * 40)
        for disease, rate in sorted(
            self.get_mortality_by_disease().items(),
            key=lambda x: x[1],
            reverse=True,
        ):
            lines.append(
                f"  {disease:45s} | {rate:.1f}%"
            )

        lines.append("\n  TOP AFFECTED REGIONS")
        lines.append("-" * 40)
        for region, count in self.get_top_regions():
            bar = "#" * count
            lines.append(
                f"  {region:25s} | {bar} ({count})"
            )

        lines.append("\n  ALERT SUMMARY")
        lines.append("-" * 40)
        for sev, count in self.get_alert_summary().items():
            lines.append(
                f"  {sev:12s} | {'!' * count} ({count})"
            )

        lines.append("\n" + "=" * w)
        return "\n".join(lines)
