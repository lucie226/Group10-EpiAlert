"""EpiAlert — Epidemiological Surveillance System for Burkina Faso.

Package initialisation.  Exposing the main entry point makes it
possible to run the application with::

    python -m EpiAlert

The sub-modules are intentionally *not* star-imported here to keep
the top-level namespace clean and to avoid circular imports at
startup time.
"""

__version__: str = "2.1.0"
__author__: str = "Team 10 — EpiAlert"
