"""CutSignal: uncertainty-aware fitness decision analytics."""

from cutsignal.analysis.cut import CutAnalysisConfig, CutAnalysisResult, analyze_cut
from cutsignal.analysis.strength import StrengthAnalysisConfig, StrengthAnalysisResult, analyze_strength
from cutsignal.models import DailyObservation, DietConstraints, FoodItem, StrengthSet
from cutsignal.optimization.diet import DietPlanResult, optimize_weekly_plan
from cutsignal.pipeline import PipelineResult, run_pipeline

__all__ = [
    "CutAnalysisConfig",
    "CutAnalysisResult",
    "DailyObservation",
    "DietConstraints",
    "DietPlanResult",
    "FoodItem",
    "PipelineResult",
    "StrengthAnalysisConfig",
    "StrengthAnalysisResult",
    "StrengthSet",
    "__version__",
    "analyze_cut",
    "analyze_strength",
    "optimize_weekly_plan",
    "run_pipeline",
]

__version__ = "0.2.0"
