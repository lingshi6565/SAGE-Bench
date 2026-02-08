# 每个可能的path分别进行生产生成
# python代码将每个路径和对应的classification output 对应
# 根据SOP图构建，确保与sop_graph.py完全一致

import json
from typing import Dict, List, Any


def generate_path_list():
    """
    根据6个分类字段生成所有可能的决策路径
    与sop_graph.py中的build_online_education_sop_graph()保持一致

    字段说明:
    1. DescriptionClear: Boolean (True/False) - 问题描述清晰度
    2. QuestionRelevance: Boolean (True/False) - 问题与课程关联性
    3. EmotionTendency: String ("Calm"/"Dissatisfied") - 学员情绪倾向
    4. ResolveDependency: String ("LowDependency"/"MediumDependency"/"HighDependency") - 问题解决依赖度
    5. RepeatedRaised: Boolean (True/False) - 问题是否重复反馈
    6. RegardingRefund: Boolean (True/False) - 是否涉及退费需求
    """
    path_list = []

    # ========== 路径1: step1 -> step2 -> action_guide (问题不清晰) ==========
    # DescriptionClear = False -> 引导用户
    path_list.append({
        "Classification_items": [False, None, None, None, None, None],
        "isRiskUser": "none",
        "expected_path": ["step1", "step2", "action_guide"],
        "final_output": {"Action": "GUIDE", "PLAN": "none"}
    })

    # ========== 路径2: step1 -> step2 -> step3 -> step4 -> action_review (重复反馈) ==========
    # DescriptionClear = True, QuestionRelevance = True, RepeatedRaised = True -> 审核
    path_list.append({
        "Classification_items": [True, True, None, None, True, None],
        "isRiskUser": "none",
        "expected_path": ["step1", "step2", "step3", "step4", "action_review"],
        "final_output": {"Action": "REVIEW", "PLAN": "none"}
    })

    # ========== 路径3: step1 -> step2 -> step3 -> step4 -> step5 -> action_comfort (不满+课程相关) ==========
    # DescriptionClear = True, QuestionRelevance = True, RepeatedRaised = False, EmotionTendency = Dissatisfied -> 安抚
    path_list.append({
        "Classification_items": [True, True, "Dissatisfied", None, False, None],
        "isRiskUser": "none",
        "expected_path": ["step1", "step2", "step3", "step4", "step5", "action_comfort"],
        "final_output": {"Action": "COMFORT", "PLAN": "none"}
    })

    # ========== 路径4: 课程相关 + 退费 + 风险用户 ==========
    # DescriptionClear = True, QuestionRelevance = True, RepeatedRaised = False, EmotionTendency = Calm
    # RegardingRefund = True, isRiskUser = True -> NEGOTIATE
    for dependency in ["LowDependency", "MediumDependency", "HighDependency"]:
        path_list.append({
            "Classification_items": [True, True, "Calm", dependency, False, True],
            "isRiskUser": True,
            "expected_path": ["step1", "step2", "step3", "step4", "step5", "step6", "step7", "step8", "action_negotiate"],
            "final_output": {"Action": "NEGOTIATE", "PLAN": "none"}
        })

    # ========== 路径5: 课程相关 + 退费 + 非风险用户 ==========
    # DescriptionClear = True, QuestionRelevance = True, RepeatedRaised = False, EmotionTendency = Calm
    # RegardingRefund = True, isRiskUser = False -> REFUND
    for dependency in ["LowDependency", "MediumDependency", "HighDependency"]:
        path_list.append({
            "Classification_items": [True, True, "Calm", dependency, False, True],
            "isRiskUser": False,
            "expected_path": ["step1", "step2", "step3", "step4", "step5", "step6", "step7", "step8", "action_refund"],
            "final_output": {"Action": "REFUND", "PLAN": "none"}
        })

    # ========== 路径6: 课程相关 + 无退费 + PLAN ==========
    # DescriptionClear = True, QuestionRelevance = True, RepeatedRaised = False, EmotionTendency = Calm
    # RegardingRefund = False -> PLAN (根据依赖度选择具体的Plan)
    for dependency in ["LowDependency", "MediumDependency", "HighDependency"]:
        path_list.append({
            "Classification_items": [True, True, "Calm", dependency, False, False],
            "isRiskUser": "none",
            "expected_path": ["step1", "step2", "step3", "step4", "step5", "step6", "step7", "action_plan"],
            "final_output": {
                "Action": "PLAN",
                "PLAN": get_course_plan(dependency)
            }
        })

    # ========== 路径7: 非课程相关 + 退费 + 风险用户 ==========
    # DescriptionClear = True, QuestionRelevance = False, RegardingRefund = True, isRiskUser = True -> NEGOTIATE
    for dependency in ["LowDependency", "MediumDependency", "HighDependency"]:
        path_list.append({
            "Classification_items": [True, False, None, dependency, None, True],
            "isRiskUser": True,
            "expected_path": ["step1", "step2", "step3", "step6", "step7", "step8", "action_negotiate"],
            "final_output": {"Action": "NEGOTIATE", "PLAN": "none"}
        })

    # ========== 路径8: 非课程相关 + 退费 + 非风险用户 ==========
    # DescriptionClear = True, QuestionRelevance = False, RegardingRefund = True, isRiskUser = False -> REFUND
    for dependency in ["LowDependency", "MediumDependency", "HighDependency"]:
        path_list.append({
            "Classification_items": [True, False, None, dependency, None, True],
            "isRiskUser": False,
            "expected_path": ["step1", "step2", "step3", "step6", "step7", "step8", "action_refund"],
            "final_output": {"Action": "REFUND", "PLAN": "none"}
        })

    # ========== 路径9: 非课程相关 + 无退费 + PLAN ==========
    # DescriptionClear = True, QuestionRelevance = False, RegardingRefund = False -> PLAN
    for dependency in ["LowDependency", "MediumDependency", "HighDependency"]:
        path_list.append({
            "Classification_items": [True, False, None, dependency, None, False],
            "isRiskUser": "none",
            "expected_path": ["step1", "step2", "step3", "step6", "step7", "action_plan"],
            "final_output": {
                "Action": "PLAN",
                "PLAN": get_non_course_plan(dependency)
            }
        })

    return path_list


def get_course_plan(dependency):
    """根据课程相关的依赖度返回对应Plan (与SOP图一致)"""
    plans = {
        "HighDependency": "PLAN_A",
        "MediumDependency": "PLAN_B",
        "LowDependency": "PLAN_C"
    }
    return plans.get(dependency, "none")


def get_non_course_plan(dependency):
    """根据非课程相关的依赖度返回对应Plan (与SOP图一致)"""
    plans = {
        "HighDependency": "PLAN_D",
        "MediumDependency": "PLAN_E",
        "LowDependency": "PLAN_F"
    }
    return plans.get(dependency, "none")


def get_intent_path_mapping():
    """
    定义Intent与可能路径的映射关系
    
    这样可以确保:
    1. 每个Intent只生成它可能走到的路径对应的用户画像
    2. 所有路径都至少被一个Intent覆盖
    
    返回格式:
    {
        "intent_name": {
            "description": "意图描述",
            "possible_paths": [路径索引列表, 从1开始],
            "required_conditions": {必须满足的条件},
            "impossible_conditions": {不可能满足的条件}
        }
    }
    """
    return {
        "seek_answer": {
            "description": "寻求问题答案 - 学习过程中遇到不理解的知识点",
            "possible_paths": [1, 2, 3, 10, 11, 12],  # GUIDE, REVIEW, COMFORT, PLAN(课程相关,路径10-12)
            "impossible_conditions": {
                "RegardingRefund": True,  # 寻求答案的用户不会要求退费
            }
        },
        
        "technical_issue": {
            "description": "技术问题 - 平台使用或功能问题",
            "possible_paths": [1, 2, 3, 10, 11, 12, 19, 20, 21],  # GUIDE, REVIEW, COMFORT, PLAN(课程/非课程)
            "impossible_conditions": {
                "RegardingRefund": True,  # 技术问题不会直接要求退费
            }
        },
        
        "complaint": {
            "description": "投诉课程质量 - 对教学内容或服务不满",
            "possible_paths": [2, 3, 10, 11, 12],  # REVIEW, COMFORT, PLAN(课程相关)
            "impossible_conditions": {}  # 投诉可能演变为任何情况
        },
        
        "refund_request": {
            "description": "明确要求退款",
            "possible_paths": [4, 5, 6, 7, 8, 9, 13, 14, 15, 16, 17, 18],  # NEGOTIATE/REFUND (课程/非课程相关,所有退费路径)
            "required_conditions": {
                "RegardingRefund": True,  # 必须涉及退费
            }
        },
        
        "consultation": {
            "description": "咨询确认 - 友好咨询课程信息",
            "possible_paths": [10, 11, 12, 19, 20, 21],  # PLAN(课程/非课程相关,所有PLAN路径)
            "impossible_conditions": {
                "RegardingRefund": True,     # 友好咨询不会要求退费
                "EmotionTendency": "Dissatisfied",  # 友好咨询不会不满
            }
        },
    }


def save_path_list_to_json(path_list, filename="path_list.json"):
    """将path_list保存为JSON文件"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(path_list, f, ensure_ascii=False, indent=2)
    print(f"PathList已保存到 {filename}")


def verify_paths_match_sop_graph():
    """验证PathList与SOP图的路径是否匹配"""
    from sop_graph import build_online_education_sop_graph

    # 获取SOP图的标准化路径（不含start和end）
    sop_graph = build_online_education_sop_graph()
    sop_paths = sop_graph.get_all_paths(include_endpoints=False)

    # 获取PathList的路径
    path_list = generate_path_list()
    pathlist_paths = [item["expected_path"] for item in path_list]

    # 转换为集合比较
    sop_path_set = set(['->'.join(p) for p in sop_paths])
    pathlist_path_set = set(['->'.join(p) for p in pathlist_paths])

    print("="*80)
    print("SOP图路径验证")
    print("="*80)
    print(f"SOP图路径数: {len(sop_paths)}")
    print(f"PathList路径数: {len(pathlist_paths)}")

    only_in_sop = sop_path_set - pathlist_path_set
    only_in_pathlist = pathlist_path_set - sop_path_set

    if only_in_sop:
        print(f"\n⚠️  PathList缺失的路径 ({len(only_in_sop)}):")
        for p in only_in_sop:
            print(f"  {p}")

    if only_in_pathlist:
        print(f"\n⚠️  SOP图缺失的路径 ({len(only_in_pathlist)}):")
        for p in only_in_pathlist:
            print(f"  {p}")

    if not only_in_sop and not only_in_pathlist:
        print("\n✅ PathList与SOP图完全一致！")
        return True
    else:
        print("\n❌ PathList与SOP图存在差异！")
        return False


if __name__ == "__main__":
    # 验证路径一致性
    verify_paths_match_sop_graph()

    # 生成PathList
    All_Paths = generate_path_list()
    print(f"\n总路径数: {len(All_Paths)}")

    # 保存到文件
    save_path_list_to_json(All_Paths, "path_list.json")

    # 打印所有路径
    print("\n" + "="*80)
    print("所有路径详情:")
    print("="*80)
    for i, path in enumerate(All_Paths):
        print(f"\n路径 {i+1}:")
        print(f"  Classification: {path['Classification_items']}")
        print(f"  isRiskUser: {path['isRiskUser']}")
        print(f"  Expected Path: {' -> '.join(path['expected_path'])}")
        print(f"  Final Output: {path['final_output']}")
