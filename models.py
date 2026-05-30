"""Data models for EpiAlert.

Core business objects built around the four pillars of OOP:

    Encapsulation
        Private attributes (_status, _is_active, _name, _role, _agent_id)
        are only accessible through @property getters and validated setter
        methods.  This protects data from being corrupted by outside code.

    Abstraction
        Agent is an abstract base class — you cannot instantiate it
        directly.  It forces every subclass to implement
        get_permissions() so that any Agent object will respond to that
        call even though the details differ.

    Inheritance
        HealthAgent and DepartmentAgent both extend Agent and inherit
        its concrete methods (can_perform, display_info, __str__, etc.).
        ReportExporter (in core.py) extends ReportEngine.

    Polymorphism
        get_permissions() returns different results depending on whether
        you call it on a HealthAgent or a DepartmentAgent.  Same method
        name, different behaviour.

Enhancements over the original
------------------------------
- ``__slots__`` on Patient, DiseaseCase, and Alert for memory savings.
- ``@property`` getters with backward-compatible ``get_xxx()`` wrappers.
- ``__eq__`` / ``__hash__`` on Patient and DiseaseCase for set/dict use.
- Frozenset-cached permission lookups (O(1) instead of O(n)).
- ``Patient.validate()`` classmethod for pre-construction validation.
- ``__all__`` for explicit public API.
- Full type annotations on every method signature.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from config import (
    Colors,
    DISEASE_COLORS,
    HEALTH_AGENT_ACTIONS,
    DEPT_AGENT_ACTIONS,
    PATIENT_STATUSES,
    SEVERITY_COLORS,
    STATUS_COLORS,
    VALID_GENDERS,
)

# Public API — ``from models import *`` only exports these names.
__all__: list[str] = [
    "Agent",
    "HealthAgent",
    "DepartmentAgent",
    "Patient",
    "DiseaseCase",
    "Alert",
]


# Section: Abstract Agent


class Agent(ABC):
    """Abstract base class for every system user.

    This class cannot be instantiated directly — it exists to define a
    common interface that HealthAgent and DepartmentAgent must follow.
    The ABC (Abstract Base Class) mechanism enforces this at import
    time: if a subclass forgets to implement an abstract method Python
    raises TypeError.

    Attributes (private, accessed via @property):
        _name: The agent's display name.
        _role: Human-readable role label (e.g. "Health Agent").
        _agent_id: Unique identifier string.
        _permissions_cache: Lazily-built frozenset for O(1) lookups.
    """

    def __init__(self, name: str, role: str, agent_id: str) -> None:
        self._name: str = name
        self._role: str = role
        self._agent_id: str = agent_id
        # Lazy cache — populated on first call to can_perform().
        # frozenset gives O(1) ``in`` checks vs O(n) for a tuple.
        self._permissions_cache: frozenset[str] | None = None

    # -- @property getters: the Pythonic way to expose private data --
    # Backward-compatible get_xxx() methods delegate to these properties.

    @property
    def name(self) -> str:
        """The agent's display name."""
        return self._name

    @property
    def role(self) -> str:
        """The agent's role label."""
        return self._role

    @property
    def agent_id(self) -> str:
        """The agent's unique identifier."""
        return self._agent_id

    def get_name(self) -> str:
        """Backward-compatible getter delegating to the *name* property."""
        return self.name

    def get_role(self) -> str:
        """Backward-compatible getter delegating to the *role* property."""
        return self.role

    def get_id(self) -> str:
        """Backward-compatible getter delegating to the *agent_id* property."""
        return self.agent_id

    @abstractmethod
    def get_permissions(self) -> frozenset[str]:
        """Return the set of actions this agent is allowed to perform."""
        ...

    def can_perform(self, action: str) -> bool:
        """Check whether the agent may perform *action*.

        The permission tuple returned by ``get_permissions()`` is
        converted to a frozenset on the first call and cached on the
        instance.  Subsequent calls use the cached frozenset for O(1)
        membership testing instead of scanning the tuple every time.
        """
        if self._permissions_cache is None:
            self._permissions_cache = frozenset(self.get_permissions())
        return action in self._permissions_cache

    def display_info(self) -> str:
        """Return a one-line summary suitable for UI headers."""
        return f"{self._role}: {self._name} (ID: {self._agent_id})"

    def __str__(self) -> str:
        return f"[{self._role}] {self._name}"

    def __repr__(self) -> str:
        return (
            f"Agent(name='{self._name}', role='{self._role}', "
            f"id='{self._agent_id}')"
        )


# Section: HealthAgent


class HealthAgent(Agent):
    """Field health worker responsible for data entry.

    Health agents operate at the facility level.  They register
    patients, update statuses, and review their own entries — but they
    cannot view aggregated case data or generate reports.

    Attributes (private):
        _region:    Administrative region of assignment.
        _province:  Province within the region.
        _commune:   Commune within the province.
        _facility:  Health facility name.
    """

    def __init__(
        self,
        name: str,
        agent_id: str,
        region: str,
        province: str = "",
        commune: str = "",
        facility: str = "",
    ) -> None:
        super().__init__(name, "Health Agent", agent_id)
        self._region: str = region
        self._province: str = province
        self._commune: str = commune
        self._facility: str = facility

    # -- Properties --

    @property
    def region(self) -> str:
        """The agent's assigned region."""
        return self._region

    @property
    def province(self) -> str:
        """The agent's assigned province."""
        return self._province

    @property
    def commune(self) -> str:
        """The agent's assigned commune."""
        return self._commune

    @property
    def facility(self) -> str:
        """The agent's health facility."""
        return self._facility

    # -- Backward-compatible getters --

    def get_region(self) -> str:
        """Backward-compatible getter delegating to the *region* property."""
        return self.region

    def get_province(self) -> str:
        """Backward-compatible getter delegating to the *province* property."""
        return self.province

    def get_commune(self) -> str:
        """Backward-compatible getter delegating to the *commune* property."""
        return self.commune

    def get_facility(self) -> str:
        """Backward-compatible getter delegating to the *facility* property."""
        return self.facility

    # -- Polymorphic implementations --

    def get_permissions(self) -> frozenset[str]:
        """Actions a HealthAgent may perform."""
        return HEALTH_AGENT_ACTIONS

    def __str__(self) -> str:
        parts: list[str] = [f"[Health Agent] {self._name}"]
        if self._region:
            parts.append(f"Region: {self._region}")
        if self._facility:
            parts.append(f"Facility: {self._facility}")
        return "  |  ".join(parts)


# Section: DepartmentAgent


class DepartmentAgent(Agent):
    """Department-level supervisor responsible for consultation and analysis.

    Department agents operate at the regional or provincial level.
    They can view aggregated case data, run epidemic detection,
    generate and export reports, and consult analytics — but they do
    not register individual patients.

    Attributes (private):
        _department:        Department name.
        _region:            Administrative region.
        _province:          Province within the region.
        _facility:          Facility name (if applicable).
        _supervision_level: Scope of supervision — "regional" or "provincial".
    """

    def __init__(
        self,
        name: str,
        agent_id: str,
        department: str,
        region: str = "",
        province: str = "",
        facility: str = "",
        supervision_level: str = "regional",
    ) -> None:
        super().__init__(name, "Department Agent", agent_id)
        self._department: str = department
        self._region: str = region
        self._province: str = province
        self._facility: str = facility
        self._supervision_level: str = supervision_level

    # -- Properties --

    @property
    def department(self) -> str:
        """The agent's department name."""
        return self._department

    @property
    def region(self) -> str:
        """The agent's assigned region."""
        return self._region

    @property
    def province(self) -> str:
        """The agent's assigned province."""
        return self._province

    @property
    def facility(self) -> str:
        """The agent's health facility."""
        return self._facility

    @property
    def supervision_level(self) -> str:
        """The agent's supervision scope."""
        return self._supervision_level

    # -- Backward-compatible getters --

    def get_department(self) -> str:
        """Backward-compatible getter delegating to the *department* property."""
        return self.department

    def get_region(self) -> str:
        """Backward-compatible getter delegating to the *region* property."""
        return self.region

    def get_province(self) -> str:
        """Backward-compatible getter delegating to the *province* property."""
        return self.province

    def get_facility(self) -> str:
        """Backward-compatible getter delegating to the *facility* property."""
        return self.facility

    def get_supervision_level(self) -> str:
        """Backward-compatible getter delegating to the *supervision_level* property."""
        return self.supervision_level

    # -- Polymorphic implementations --

    def get_permissions(self) -> frozenset[str]:
        """Actions a DepartmentAgent may perform."""
        return DEPT_AGENT_ACTIONS

    def __str__(self) -> str:
        parts: list[str] = [f"[Department Agent] {self._name}"]
        if self._department:
            parts.append(f"Dept: {self._department}")
        parts.append(f"Scope: {self._supervision_level}")
        return "  |  ".join(parts)


# Section: Patient


class Patient:
    """A patient in the epidemiological surveillance system.

    Each patient record captures demographics, the diagnosed disease,
    the current status, and the geographic location of the case.

    ``__slots__`` is declared here because Patient objects are the most
    numerous in the system — potentially thousands per region.  By
    replacing the per-instance ``__dict__`` with a fixed-size array of
    attribute references, each instance uses significantly less memory
    and attribute access is marginally faster.

    Note:
        ``status`` is a read-only @property backed by ``_status``.
        Mutation must go through ``set_status()``, which validates the
        new value against ``PATIENT_STATUSES``.  This is encapsulation:
        the internal state is protected from arbitrary writes.
    """

    # __slots__ tells Python to allocate a fixed set of attribute
    # references instead of a full __dict__.  This saves ~40-50 %
    # memory per instance for data-heavy classes like this one.
    __slots__ = (
        "patient_id",
        "first_name",
        "last_name",
        "age",
        "gender",
        "disease",
        "region",
        "province",
        "commune",
        "health_facility",
        "date_reported",
        "entered_by",
        "_status",
    )

    def __init__(
        self,
        patient_id: int,
        first_name: str,
        last_name: str,
        age: int,
        gender: str,
        disease: str,
        status: str,
        region: str,
        province: str,
        commune: str,
        health_facility: str,
        date_reported: str,
        entered_by: str = "",
    ) -> None:
        self.patient_id: int = patient_id
        self.first_name: str = first_name
        self.last_name: str = last_name
        self.age: int = age
        self.gender: str = gender
        self.disease: str = disease
        self.region: str = region
        self.province: str = province
        self.commune: str = commune
        self.health_facility: str = health_facility
        self.date_reported: str = date_reported
        self.entered_by: str = entered_by
        # _status is private — only set_status() may change it.
        self._status: str = ""
        self.set_status(status)

    # -- Validation before construction --

    @classmethod
    def validate(
        cls,
        patient_id: int,
        first_name: str,
        last_name: str,
        age: int,
        gender: str,
        disease: str,
        status: str,
        region: str,
        province: str,
        commune: str,
        health_facility: str,
        date_reported: str,
        entered_by: str = "",
    ) -> tuple[bool, list[str]]:
        """Validate all fields before constructing a Patient.

        Returns a ``(is_valid, errors)`` tuple.  When *is_valid* is
        ``True`` the caller can safely call ``Patient(...)``; when
        ``False`` the *errors* list explains what is wrong.

        This is the "validate-then-construct" pattern — it separates
        data validation from object creation so that the UI layer can
        display friendly error messages without catching exceptions.
        """
        errors: list[str] = []

        if not isinstance(patient_id, int) or patient_id < 0:
            errors.append("patient_id must be a non-negative integer")

        if not first_name or not isinstance(first_name, str):
            errors.append("first_name must be a non-empty string")

        if not last_name or not isinstance(last_name, str):
            errors.append("last_name must be a non-empty string")

        if not isinstance(age, int) or age < 0:
            errors.append("age must be a non-negative integer")

        if gender not in VALID_GENDERS:
            errors.append(f"gender must be one of {VALID_GENDERS}")

        if not disease or not isinstance(disease, str):
            errors.append("disease must be a non-empty string")

        if status not in PATIENT_STATUSES:
            errors.append(f"status must be one of {PATIENT_STATUSES}")

        if not region or not isinstance(region, str):
            errors.append("region must be a non-empty string")

        if not province or not isinstance(province, str):
            errors.append("province must be a non-empty string")

        if not commune or not isinstance(commune, str):
            errors.append("commune must be a non-empty string")

        if not health_facility or not isinstance(health_facility, str):
            errors.append("health_facility must be a non-empty string")

        if not date_reported or not isinstance(date_reported, str):
            errors.append("date_reported must be a non-empty string")

        # entered_by is optional — only validate type if provided.
        if entered_by and not isinstance(entered_by, str):
            errors.append("entered_by must be a string when provided")

        return (len(errors) == 0, errors)

    # -- Encapsulated status with @property --

    @property
    def status(self) -> str:
        """The patient's current status (read-only property).

        Use ``set_status()`` to change it — the setter validates the
        new value against ``PATIENT_STATUSES`` before writing.
        """
        return self._status

    def get_status(self) -> str:
        """Backward-compatible getter delegating to the *status* property."""
        return self.status

    def set_status(self, new_status: str) -> bool:
        """Attempt to change the patient's status.

        Returns ``True`` on success, ``False`` if *new_status* is not
        a recognised value.  This validates-then-writes pattern is the
        essence of encapsulation — the object guards its own invariants.
        """
        if new_status in PATIENT_STATUSES:
            self._status = new_status
            return True
        return False

    # -- Computed properties --

    @property
    def status_color(self) -> str:
        """ANSI colour code for the patient's current status."""
        return STATUS_COLORS.get(self._status, Colors.WHITE)

    @property
    def disease_color(self) -> str:
        """ANSI colour code for the patient's diagnosed disease."""
        return DISEASE_COLORS.get(self.disease, Colors.WHITE)

    @property
    def full_name(self) -> str:
        """The patient's first and last name combined."""
        return f"{self.first_name} {self.last_name}"

    # -- Backward-compatible getters for computed properties --

    def get_status_color(self) -> str:
        """Backward-compatible getter delegating to *status_color*."""
        return self.status_color

    def get_disease_color(self) -> str:
        """Backward-compatible getter delegating to *disease_color*."""
        return self.disease_color

    def get_full_name(self) -> str:
        """Backward-compatible getter delegating to *full_name*."""
        return self.full_name

    # -- Serialisation --

    def to_file_line(self) -> str:
        """Serialise the patient to a pipe-delimited file line."""
        return (
            f"{self.patient_id}|{self.first_name}|{self.last_name}|"
            f"{self.age}|{self.gender}|{self.disease}|{self._status}|"
            f"{self.region}|{self.province}|{self.commune}|"
            f"{self.health_facility}|{self.date_reported}|"
            f"{self.entered_by}"
        )

    @staticmethod
    def from_file_line(line: str) -> Patient | None:
        """Deserialise a pipe-delimited line into a Patient.

        Returns ``None`` for comment lines, blank lines, or malformed
        data — the caller can simply skip ``None`` results.
        """
        if line.startswith("#") or line.strip() == "":
            return None
        parts: list[str] = line.strip().split("|")
        if len(parts) < 12:
            return None
        try:
            entered_by: str = parts[12] if len(parts) >= 13 else ""
            return Patient(
                patient_id=int(parts[0]),
                first_name=parts[1],
                last_name=parts[2],
                age=int(parts[3]),
                gender=parts[4],
                disease=parts[5],
                status=parts[6],
                region=parts[7],
                province=parts[8],
                commune=parts[9],
                health_facility=parts[10],
                date_reported=parts[11],
                entered_by=entered_by,
            )
        except (ValueError, IndexError):
            return None

    # -- Value-based equality and hashing --
    # Two Patient objects are considered equal when they share the
    # same patient_id.  This allows Patients to be stored in sets or
    # used as dict keys without duplicates.

    def __eq__(self, other: object) -> bool:
        """Two patients are equal if they share the same patient_id."""
        if not isinstance(other, Patient):
            return NotImplemented
        return self.patient_id == other.patient_id

    def __hash__(self) -> int:
        """Hash based on patient_id so Patients work in sets/dicts."""
        return hash(self.patient_id)

    # -- String representations --

    def __str__(self) -> str:
        return (
            f"[#{self.patient_id}] {self.first_name} {self.last_name}"
            f" - {self.disease} ({self._status}) - {self.region}"
        )

    def __repr__(self) -> str:
        return (
            f"Patient(id={self.patient_id}, "
            f"name='{self.first_name} {self.last_name}')"
        )


# Section: DiseaseCase


class DiseaseCase:
    """Aggregated weekly disease case counts for a geographic zone.

    Each instance represents the tally of suspected, confirmed,
    recovered, and deceased cases for one disease in one commune
    during a specific epidemiological week.

    ``__slots__`` is used here for the same memory-efficiency reasons
    as Patient — the system may hold thousands of case records.
    """

    __slots__ = (
        "case_id",
        "disease",
        "region",
        "province",
        "commune",
        "suspected",
        "confirmed",
        "recovered",
        "deceased",
        "date_reported",
        "week_number",
    )

    def __init__(
        self,
        case_id: int,
        disease: str,
        region: str,
        province: str,
        commune: str,
        suspected: int,
        confirmed: int,
        recovered: int,
        deceased: int,
        date_reported: str,
        week_number: int,
    ) -> None:
        self.case_id: int = case_id
        self.disease: str = disease
        self.region: str = region
        self.province: str = province
        self.commune: str = commune
        self.suspected: int = suspected
        self.confirmed: int = confirmed
        self.recovered: int = recovered
        self.deceased: int = deceased
        self.date_reported: str = date_reported
        self.week_number: int = week_number

    # -- Computed properties --

    @property
    def total_cases(self) -> int:
        """Total of all case categories for this zone/week."""
        return self.suspected + self.confirmed + self.recovered + self.deceased

    @property
    def mortality_rate(self) -> float:
        """Percentage of total cases that ended in death."""
        total: int = self.total_cases
        return (self.deceased / total) * 100.0 if total else 0.0

    @property
    def recovery_rate(self) -> float:
        """Percentage of total cases that recovered."""
        total: int = self.total_cases
        return (self.recovered / total) * 100.0 if total else 0.0

    @property
    def location(self) -> str:
        """Human-readable region / province / commune path."""
        return f"{self.region} / {self.province} / {self.commune}"

    @property
    def disease_color(self) -> str:
        """ANSI colour code for this case's disease."""
        return DISEASE_COLORS.get(self.disease, Colors.WHITE)

    # -- Backward-compatible getters --

    def get_total_cases(self) -> int:
        """Backward-compatible getter delegating to *total_cases*."""
        return self.total_cases

    def get_mortality_rate(self) -> float:
        """Backward-compatible getter delegating to *mortality_rate*."""
        return self.mortality_rate

    def get_recovery_rate(self) -> float:
        """Backward-compatible getter delegating to *recovery_rate*."""
        return self.recovery_rate

    def get_location(self) -> str:
        """Backward-compatible getter delegating to *location*."""
        return self.location

    def get_disease_color(self) -> str:
        """Backward-compatible getter delegating to *disease_color*."""
        return self.disease_color

    # -- Serialisation --

    def to_file_line(self) -> str:
        """Serialise the case to a pipe-delimited file line."""
        return (
            f"{self.case_id}|{self.disease}|{self.region}|"
            f"{self.province}|{self.commune}|{self.suspected}|"
            f"{self.confirmed}|{self.recovered}|{self.deceased}|"
            f"{self.date_reported}|{self.week_number}"
        )

    @staticmethod
    def from_file_line(line: str) -> DiseaseCase | None:
        """Deserialise a pipe-delimited line into a DiseaseCase.

        Returns ``None`` for comment lines, blank lines, or malformed
        data.
        """
        if line.startswith("#") or line.strip() == "":
            return None
        parts: list[str] = line.strip().split("|")
        if len(parts) != 11:
            return None
        try:
            return DiseaseCase(
                case_id=int(parts[0]),
                disease=parts[1],
                region=parts[2],
                province=parts[3],
                commune=parts[4],
                suspected=int(parts[5]),
                confirmed=int(parts[6]),
                recovered=int(parts[7]),
                deceased=int(parts[8]),
                date_reported=parts[9],
                week_number=int(parts[10]),
            )
        except (ValueError, IndexError):
            return None

    # -- Value-based equality and hashing --

    def __eq__(self, other: object) -> bool:
        """Two disease cases are equal if they share the same case_id."""
        if not isinstance(other, DiseaseCase):
            return NotImplemented
        return self.case_id == other.case_id

    def __hash__(self) -> int:
        """Hash based on case_id so DiseaseCases work in sets/dicts."""
        return hash(self.case_id)

    # -- String representations --

    def __str__(self) -> str:
        return (
            f"[#{self.case_id}] {self.disease}"
            f" - {self.location} - Total: {self.total_cases}"
        )

    def __repr__(self) -> str:
        return (
            f"DiseaseCase(id={self.case_id}, disease='{self.disease}', "
            f"total={self.total_cases})"
        )


# Section: Alert


class Alert:
    """Epidemiological alert triggered when a disease threshold is exceeded.

    An alert is created when the number of observed cases for a disease
    in a geographic zone exceeds the configured weekly threshold.  It
    remains active until a DepartmentAgent explicitly deactivates it.

    ``__slots__`` is declared because the alert list can grow large
    during an outbreak and each saved kilobyte matters when the system
    runs on resource-constrained machines.
    """

    __slots__ = (
        "alert_id",
        "disease",
        "region",
        "province",
        "commune",
        "case_count",
        "threshold",
        "message",
        "severity",
        "date_created",
        "_is_active",
    )

    def __init__(
        self,
        alert_id: int,
        disease: str,
        region: str,
        province: str,
        commune: str,
        case_count: int,
        threshold: int,
        message: str,
        severity: str,
        date_created: str,
        is_active: bool = True,
    ) -> None:
        self.alert_id: int = alert_id
        self.disease: str = disease
        self.region: str = region
        self.province: str = province
        self.commune: str = commune
        self.case_count: int = case_count
        self.threshold: int = threshold
        self.message: str = message
        self.severity: str = severity
        self.date_created: str = date_created
        # _is_active is private — mutated only through activate/deactivate.
        self._is_active: bool = is_active

    # -- Encapsulated active state --
    # Note: is_active() remains a *method* (not a @property) to
    # preserve backward compatibility with callers who invoke it with
    # parentheses:  ``if alert.is_active():``

    def is_active(self) -> bool:
        """Return whether this alert is currently active."""
        return self._is_active

    def activate(self) -> None:
        """Reactivate a previously resolved alert."""
        self._is_active = True

    def deactivate(self) -> None:
        """Resolve (deactivate) the alert."""
        self._is_active = False

    # -- Computed properties --

    @property
    def location(self) -> str:
        """Human-readable region / province / commune path."""
        return f"{self.region} / {self.province} / {self.commune}"

    @property
    def severity_color(self) -> str:
        """ANSI colour code for this alert's severity level."""
        return SEVERITY_COLORS.get(self.severity, Colors.WHITE)

    # -- Backward-compatible getters --

    def get_location(self) -> str:
        """Backward-compatible getter delegating to *location*."""
        return self.location

    def get_severity_color(self) -> str:
        """Backward-compatible getter delegating to *severity_color*."""
        return self.severity_color

    # -- Serialisation --

    def to_file_line(self) -> str:
        """Serialise the alert to a pipe-delimited file line."""
        flag: str = "1" if self._is_active else "0"
        return (
            f"{self.alert_id}|{self.disease}|{self.region}|"
            f"{self.province}|{self.commune}|{self.case_count}|"
            f"{self.threshold}|{self.message}|{self.severity}|"
            f"{self.date_created}|{flag}"
        )

    @staticmethod
    def from_file_line(line: str) -> Alert | None:
        """Deserialise a pipe-delimited line into an Alert.

        Returns ``None`` for comment lines, blank lines, or malformed
        data.
        """
        if line.startswith("#") or line.strip() == "":
            return None
        parts: list[str] = line.strip().split("|")
        if len(parts) != 11:
            return None
        try:
            return Alert(
                alert_id=int(parts[0]),
                disease=parts[1],
                region=parts[2],
                province=parts[3],
                commune=parts[4],
                case_count=int(parts[5]),
                threshold=int(parts[6]),
                message=parts[7],
                severity=parts[8],
                date_created=parts[9],
                is_active=(parts[10] == "1"),
            )
        except (ValueError, IndexError):
            return None

    # -- String representations --

    def __str__(self) -> str:
        state: str = "ACTIVE" if self._is_active else "RESOLVED"
        return (
            f"[{self.severity}] {self.disease}"
            f" - {self.location}"
            f" ({self.case_count} vs {self.threshold}) [{state}]"
        )

    def __repr__(self) -> str:
        state: str = "ACTIVE" if self._is_active else "RESOLVED"
        return (
            f"Alert(id={self.alert_id}, disease='{self.disease}', "
            f"severity='{self.severity}', state='{state}')"
        )
