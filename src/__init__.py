# ============================================================
# MRD Agent - Source Package
# ============================================================
# This is the main source package for the MRD Agent.
# Exports the key components for external use.
# ============================================================

from src.models import MRDOutput, MRDState, VerifiedCompany
from src.agents import run_mrd_agent

__version__ = "2.0.0"
__all__ = ["MRDOutput", "MRDState", "VerifiedCompany", "run_mrd_agent"]
