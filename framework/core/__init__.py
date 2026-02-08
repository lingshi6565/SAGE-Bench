"""
核心模块 - 模拟器、生成器等
Core Module - Simulator, Generator, etc.
"""

from .simulator import (
    DialogueSimulator,
    SimulationResult,
    SimulationTurn,
)

__all__ = [
    "DialogueSimulator",
    "SimulationResult",
    "SimulationTurn",
]
