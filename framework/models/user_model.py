#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
用户模型系统
User Model System

负责：
1. 定义用户画像和用户状态
2. 管理用户的对话历史和内部状态
3. 生成用户的下一步动作和话语
4. 模拟真实用户行为
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import json
from datetime import datetime


class UserState(Enum):
    """用户状态"""
    INITIAL = "initial"            # 初始状态
    INTERACTING = "interacting"    # 交互中
    RESOLVED = "resolved"          # 问题已解决
    ESCALATED = "escalated"        # 问题升级


class UserEmotionState(Enum):
    """用户情感状态"""
    CALM = "calm"                  # 平静
    SLIGHTLY_FRUSTRATED = "slightly_frustrated"  # 稍微沮丧
    FRUSTRATED = "frustrated"      # 沮丧
    ANGRY = "angry"                # 生气


@dataclass
class UserProfile:
    """用户画像"""
    user_id: str                   # 用户ID
    user_intent: str               # 用户意图
    adversarial_intensity: str     # 对抗强度 (zero_conflict, weak_conflict, strong_conflict)
    
    # 用户场景信息
    scenario_id: str               # 场景ID
    
    # 在线教育特有字段 (示例，其他场景可扩展)
    course_list: List[str] = field(default_factory=list)  # 当前在学课程列表
    historical_complaints: bool = False  # 是否有历史投诉记录
    question_types_30days: List[str] = field(default_factory=list)  # 30天内的问题类型
    is_risk_user: bool = False     # 是否为风险用户
    
    # 用户特性
    communication_style: str = "normal"  # 交流风格
    patience_level: float = 0.5    # 耐心程度 (0-1)
    conciseness_level: float = 0.5  # 语言简洁度 (0-1)
    
    # 其他信息
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UserTurn:
    """用户单轮对话"""
    turn_id: int                   # 轮次ID
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    user_message: str = ""         # 用户消息
    user_action: Optional[Dict[str, Any]] = None  # 用户动作 (如提供信息、投诉等)
    emotion_state: UserEmotionState = UserEmotionState.CALM  # 用户情感状态
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据


class UserModel:
    """
    用户模型 - 模拟真实用户行为
    
    核心功能：
    1. 维护用户状态和对话历史
    2. 根据客服回复生成用户的下一步动作
    3. 动态调整情感状态
    4. 生成自然的用户话语
    """
    
    def __init__(self, profile: UserProfile, system_prompt: str = ""):
        """
        初始化用户模型
        
        Args:
            profile: 用户画像
            system_prompt: 用户系统提示词
        """
        self.profile = profile
        self.system_prompt = system_prompt
        
        # 状态管理
        self.state = UserState.INITIAL
        self.emotion_state = UserEmotionState.CALM
        
        # 对话历史
        self.dialogue_history: List[Dict[str, str]] = []
        self.turn_history: List[UserTurn] = []
        self.current_turn = 0
        
        # 内部变量
        self.problem_resolved = False
        self.satisfaction_score = 0.5
    
    def add_assistant_message(self, message: str) -> None:
        """添加客服消息到对话历史"""
        self.dialogue_history.append({
            "role": "assistant",
            "content": message
        })
    
    def add_user_message(self, message: str, action: Optional[Dict[str, Any]] = None) -> None:
        """
        添加用户消息到对话历史
        
        Args:
            message: 用户消息
            action: 用户动作信息 (可选)
        """
        self.dialogue_history.append({
            "role": "user",
            "content": message
        })
        
        # 记录轮次信息
        turn = UserTurn(
            turn_id=self.current_turn,
            user_message=message,
            user_action=action,
            emotion_state=self.emotion_state
        )
        self.turn_history.append(turn)
        self.current_turn += 1
    
    def update_emotion_state(self, emotion: UserEmotionState) -> None:
        """更新用户情感状态"""
        self.emotion_state = emotion
    
    def update_satisfaction(self, delta: float) -> None:
        """
        更新满意度
        
        Args:
            delta: 满意度变化量 (-1 到 1)
        """
        self.satisfaction_score = max(0.0, min(1.0, self.satisfaction_score + delta))
        
        # 根据满意度调整情感状态
        if self.satisfaction_score < 0.3:
            self.emotion_state = UserEmotionState.ANGRY
        elif self.satisfaction_score < 0.5:
            self.emotion_state = UserEmotionState.FRUSTRATED
        elif self.satisfaction_score < 0.7:
            self.emotion_state = UserEmotionState.SLIGHTLY_FRUSTRATED
        else:
            self.emotion_state = UserEmotionState.CALM
    
    def set_state(self, state: UserState) -> None:
        """设置用户状态"""
        self.state = state
    
    def get_dialogue_context(self) -> Dict[str, Any]:
        """获取当前对话上下文"""
        return {
            "user_profile": {
                "user_id": self.profile.user_id,
                "user_intent": self.profile.user_intent,
                "scenario_id": self.profile.scenario_id,
            },
            "current_state": self.state.value,
            "emotion_state": self.emotion_state.value,
            "satisfaction_score": self.satisfaction_score,
            "dialogue_history": self.dialogue_history,
            "turn_count": self.current_turn,
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "profile": {
                "user_id": self.profile.user_id,
                "user_intent": self.profile.user_intent,
                "adversarial_intensity": self.profile.adversarial_intensity,
                "scenario_id": self.profile.scenario_id,
                "is_risk_user": self.profile.is_risk_user,
            },
            "state": self.state.value,
            "emotion_state": self.emotion_state.value,
            "satisfaction_score": self.satisfaction_score,
            "dialogue_history": self.dialogue_history,
            "turn_count": self.current_turn,
        }


class UserModelFactory:
    """用户模型工厂 - 根据配置创建用户模型"""
    
    @staticmethod
    def create_from_profile(profile: UserProfile, system_prompt: str = "") -> UserModel:
        """
        从用户画像创建用户模型
        
        Args:
            profile: 用户画像
            system_prompt: 系统提示词
            
        Returns:
            UserModel: 用户模型实例
        """
        return UserModel(profile, system_prompt)
    
    @staticmethod
    def create_from_dict(data: Dict[str, Any], system_prompt: str = "") -> UserModel:
        """
        从字典创建用户模型
        
        Args:
            data: 用户数据字典
            system_prompt: 系统提示词
            
        Returns:
            UserModel: 用户模型实例
        """
        profile = UserProfile(
            user_id=data.get("user_id", ""),
            user_intent=data.get("user_intent", ""),
            adversarial_intensity=data.get("adversarial_intensity", ""),
            scenario_id=data.get("scenario_id", ""),
            course_list=data.get("course_list", []),
            historical_complaints=data.get("historical_complaints", False),
            question_types_30days=data.get("question_types_30days", []),
            is_risk_user=data.get("is_risk_user", False),
            communication_style=data.get("communication_style", "normal"),
            patience_level=data.get("patience_level", 0.5),
            conciseness_level=data.get("conciseness_level", 0.5),
            metadata=data.get("metadata", {})
        )
        
        return UserModel(profile, system_prompt)
