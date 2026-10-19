"""
Reinsurance Analytics: Actuarial Experience Analysis & Quantitative Risk Modeling
==================================================================================

A comprehensive actuarial framework for reinsurance experience studies, credibility theory,
loss severity modeling, treaty structuring, and aggregate risk simulation.
"""

__version__ = "1.0.0"
__author__ = "Actuarial Data Science Team"

from reinsurance_analytics.core.exposure import ExposureEngine, ExposureMethod
from reinsurance_analytics.core.mortality_tables import GompertzMakehamTable, SOAVBTBenchmark
from reinsurance_analytics.core.credibility import (
    LimitedFluctuationCredibility,
    BuhlmannStraubCredibility,
    CredibilityResult,
)
from reinsurance_analytics.life.experience_study import LifeExperienceStudy, ExperienceStudyResult
from reinsurance_analytics.life.glm_modeling import ActuarialGLMExperience, SurvivalExperienceAnalyzer
from reinsurance_analytics.nonlife.distributions import (
    LossDistributionFitter,
    ParetoDistribution,
    LognormalDistribution,
    WeibullDistribution,
    GeneralizedParetoDistribution,
)
from reinsurance_analytics.nonlife.loss_experience import TreatyLossExperienceStudy
from reinsurance_analytics.nonlife.extreme_value import ExtremeValueAnalyzer
from reinsurance_analytics.treaty.structures import (
    QuotaShareTreaty,
    SurplusTreaty,
    ExcessOfLossTreaty,
    StopLossTreaty,
    ReinsuranceProgram,
)
from reinsurance_analytics.treaty.reinstatements import ReinstatementClause, ReinstatementType
from reinsurance_analytics.simulation.collective_risk import CollectiveRiskSimulator, PanjerRecursion
from reinsurance_analytics.simulation.risk_metrics import ActuarialRiskMetrics
from reinsurance_analytics.reporting.visualizer import ActuarialVisualizer
from reinsurance_analytics.reporting.report_builder import ActuarialReportBuilder
from reinsurance_analytics.data.generator import ReinsuranceDataGenerator

__all__ = [
    "ExposureEngine",
    "ExposureMethod",
    "GompertzMakehamTable",
    "SOAVBTBenchmark",
    "LimitedFluctuationCredibility",
    "BuhlmannStraubCredibility",
    "CredibilityResult",
    "LifeExperienceStudy",
    "ExperienceStudyResult",
    "ActuarialGLMExperience",
    "SurvivalExperienceAnalyzer",
    "LossDistributionFitter",
    "ParetoDistribution",
    "LognormalDistribution",
    "WeibullDistribution",
    "GeneralizedParetoDistribution",
    "TreatyLossExperienceStudy",
    "ExtremeValueAnalyzer",
    "QuotaShareTreaty",
    "SurplusTreaty",
    "ExcessOfLossTreaty",
    "StopLossTreaty",
    "ReinsuranceProgram",
    "ReinstatementClause",
    "ReinstatementType",
    "CollectiveRiskSimulator",
    "PanjerRecursion",
    "ActuarialRiskMetrics",
    "ActuarialVisualizer",
    "ActuarialReportBuilder",
    "ReinsuranceDataGenerator",
]
