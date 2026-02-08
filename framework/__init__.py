"""
多轮对话评测框架
Multi-turn Dialogue Evaluation Framework

支持多场景、多对抗强度、基于SOP图的对话评测系统
"""

__version__ = "0.1.0"

# 导入主要组件
from .config import (
    ScenarioConfig,
    AdversarialIntensity,
    get_scenario_config,
    list_available_scenarios,
)

from .sop import (
    SOPGraph,
    get_sop_graph,
)

from .models import (
    UserModel,
    UserProfile,
    UserModelFactory,
    AgentModel,
    AgentTurnOutput,
)

from .core import (
    DialogueSimulator,
    SimulationResult,
)

from .evaluator import (
    Evaluator,
    EvaluationReport,
)

__all__ = [
    "ScenarioConfig",
    "AdversarialIntensity",
    "get_scenario_config",
    "list_available_scenarios",
    "SOPGraph",
    "get_sop_graph",
    "UserModel",
    "UserProfile",
    "UserModelFactory",
    "AgentModel",
    "AgentTurnOutput",
    "DialogueSimulator",
    "SimulationResult",
    "Evaluator",
    "EvaluationReport",
]
