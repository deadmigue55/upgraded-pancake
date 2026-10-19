"""
Core actuarial calculation engines: exposure tracking, mortality tables, and credibility theory.
"""

from reinsurance_analytics.core.exposure import ExposureEngine, ExposureMethod
from reinsurance_analytics.core.mortality_tables import GompertzMakehamTable, SOAVBTBenchmark
from reinsurance_analytics.core.credibility import (
    LimitedFluctuationCredibility,
    BuhlmannStraubCredibility,
    CredibilityResult,
)

__all__ = [
    "ExposureEngine",
    "ExposureMethod",
    "GompertzMakehamTable",
    "SOAVBTBenchmark",
    "LimitedFluctuationCredibility",
    "BuhlmannStraubCredibility",
    "CredibilityResult",
]
