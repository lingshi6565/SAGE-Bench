# 每个可能的path分别进行生成
# python代码将每个路径和对应的classification output对应
# 根据SOP流程构建，确保与sop_graph.py完全一致

import json
from typing import Dict, List, Any


def generate_path_list():
    """
    根据6个分类字段和2个系统变量生成所有可能的决策路径
    与sop_graph.py中的build_logistics_delivery_sop_graph()保持一致

    字段说明:
    1. RiskStatus: String ("Risk"/"Safe") - 订单的危险程度
    2. InfoCompleteness: Boolean (True/False) - 用户提交信息的完整程度（是否包含订单号）
    3. UserIntention: String ("Urge"/"Complaint"/"Modify") - 用户发起请求的核心目的
    4. EmotionalState: String ("Calm"/"Dissatisfied") - 用户反馈问题时的情绪状态
    5. EmergencyLevel: String ("Urgent"/"Normal") - 事项紧急程度
    6. ComplaintValidity: Boolean (True/False) - 投诉的合理性
    
    系统变量:
    1. orderStatus: String ("Arrived"/"Delivered"/"Undelivered") - 订单的配送进度状态
    2. hasInsurance: Boolean (True/False) - 订单/包裹是否购买保险
    """
    path_list = []

    # ========== 路径1: RiskStatus=Risk分支 ==========
    # RiskStatus=Risk -> ACTION=Interception
    path_list.append({
        "Classification_items": ["Risk", None, None, None, None, None],
        "system_variables": {},
        "expected_path": ["step1", "step2"],
        "final_output": {"Action": "Interception"}
    })

    # ========== 路径2: InfoCompleteness=False分支 ==========
    # Safe + InfoCompleteness=False -> ACTION=Supplementary
    path_list.append({
        "Classification_items": ["Safe", False, None, None, None, None],
        "system_variables": {},
        "expected_path": ["step1", "step2", "step3"],
        "final_output": {"Action": "Supplementary"}
    })

    # ========== 路径3-7: UserIntention=Urge分支 ==========
    # Urge + Arrived -> ACTION=Detail
    path_list.append({
        "Classification_items": ["Safe", True, "Urge", None, None, None],
        "system_variables": {"orderStatus": "Arrived"},
        "expected_path": ["step1", "step2", "step3", "step4", "step5"],
        "final_output": {"Action": "Detail"}
    })

    # Urge + Undelivered/Delivered + Urgent/Normal变化
    for status in ["Undelivered", "Delivered"]:
        for emergency in ["Urgent", "Normal"]:
            action = "Registration" if emergency == "Urgent" else "Detail"
            path_list.append({
                "Classification_items": ["Safe", True, "Urge", None, emergency, None],
                "system_variables": {"orderStatus": status},
                "expected_path": ["step1", "step2", "step3", "step4", "step5", "step6"],
                "final_output": {"Action": action}
            })

    # ========== 路径8-10: UserIntention=Modify分支 ==========
    # Modify + Arrived -> ACTION=Reject
    path_list.append({
        "Classification_items": ["Safe", True, "Modify", None, None, None],
        "system_variables": {"orderStatus": "Arrived"},
        "expected_path": ["step1", "step2", "step3", "step4", "step5"],
        "final_output": {"Action": "Reject"}
    })

    # Modify + Delivered -> ACTION=MakeUpDifference
    path_list.append({
        "Classification_items": ["Safe", True, "Modify", None, None, None],
        "system_variables": {"orderStatus": "Delivered"},
        "expected_path": ["step1", "step2", "step3", "step4", "step5"],
        "final_output": {"Action": "MakeUpDifference"}
    })

    # Modify + Undelivered -> ACTION=Modify
    path_list.append({
        "Classification_items": ["Safe", True, "Modify", None, None, None],
        "system_variables": {"orderStatus": "Undelivered"},
        "expected_path": ["step1", "step2", "step3", "step4", "step5"],
        "final_output": {"Action": "Modify"}
    })

    # ========== 路径11-16: UserIntention=Complaint分支 ==========
    # Complaint + Arrived + Invalid -> ACTION=Comfort
    path_list.append({
        "Classification_items": ["Safe", True, "Complaint", None, None, False],
        "system_variables": {"orderStatus": "Arrived"},
        "expected_path": ["step1", "step2", "step3", "step4", "step5", "step7"],
        "final_output": {"Action": "Comfort"}
    })

    # Complaint + Arrived + Valid + hasInsurance/Emotion变化
    # Arrived + Valid + hasInsurance=True -> ACTION=Compensation
    path_list.append({
        "Classification_items": ["Safe", True, "Complaint", None, None, True],
        "system_variables": {"orderStatus": "Arrived", "hasInsurance": True},
        "expected_path": ["step1", "step2", "step3", "step4", "step5", "step7", "step8"],
        "final_output": {"Action": "Compensation"}
    })

    # Arrived + Valid + hasInsurance=False + Emotion变化
    for emotion in ["Calm", "Dissatisfied"]:
        action = "Comfort" if emotion == "Calm" else "TransHuman"
        path_list.append({
            "Classification_items": ["Safe", True, "Complaint", emotion, None, True],
            "system_variables": {"orderStatus": "Arrived", "hasInsurance": False},
            "expected_path": ["step1", "step2", "step3", "step4", "step5", "step7", "step8", "step9"],
            "final_output": {"Action": action}
        })

    # ========== 路径15-16: Complaint + Delivered/Undelivered分支 ==========
    # Complaint + Delivered/Undelivered + Urgent/Normal + 跳转到step6
    for status in ["Delivered", "Undelivered"]:
        for emergency in ["Urgent", "Normal"]:
            action = "Registration" if emergency == "Urgent" else "Detail"
            path_list.append({
                "Classification_items": ["Safe", True, "Complaint", None, emergency, None],
                "system_variables": {"orderStatus": status},
                "expected_path": ["step1", "step2", "step3", "step4", "step5", "step6"],
                "final_output": {"Action": action}
            })

    return path_list


def get_intent_path_mapping() -> Dict[str, Dict]:
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
        }
    }
    """
    return {
        "risk_package_interception": {
            "description": "风险包裹拦截 - 系统标记风险包裹需要拦截",
            "possible_paths": [1],
            "required_conditions": {
                "RiskStatus": "Risk",
            }
        },

        "info_incomplete_supplementary": {
            "description": "信息不完整补充 - 用户信息不完整需补充",
            "possible_paths": [2],
            "required_conditions": {
                "RiskStatus": "Safe",
                "InfoCompleteness": False,
            }
        },

        "urge_arrived_detail": {
            "description": "催促已到达详情 - 已到达包裹用户催促",
            "possible_paths": [3],
            "required_conditions": {
                "RiskStatus": "Safe",
                "InfoCompleteness": True,
                "UserIntention": "Urge",
                "orderStatus": "Arrived",
            }
        },

        "urge_undelivered_urgent": {
            "description": "催促未送达紧急 - 未送达包裹用户催促且紧急",
            "possible_paths": [4],
            "required_conditions": {
                "RiskStatus": "Safe",
                "InfoCompleteness": True,
                "UserIntention": "Urge",
                "orderStatus": "Undelivered",
                "EmergencyLevel": "Urgent",
            }
        },

        "urge_undelivered_normal": {
            "description": "催促未送达正常 - 未送达包裹用户催促但不紧急",
            "possible_paths": [5],
            "required_conditions": {
                "RiskStatus": "Safe",
                "InfoCompleteness": True,
                "UserIntention": "Urge",
                "orderStatus": "Undelivered",
                "EmergencyLevel": "Normal",
            }
        },

        "urge_delivered_urgent": {
            "description": "催促已送达紧急 - 已送达包裹用户催促且紧急",
            "possible_paths": [6],
            "required_conditions": {
                "RiskStatus": "Safe",
                "InfoCompleteness": True,
                "UserIntention": "Urge",
                "orderStatus": "Delivered",
                "EmergencyLevel": "Urgent",
            }
        },

        "urge_delivered_normal": {
            "description": "催促已送达正常 - 已送达包裹用户催促但不紧急",
            "possible_paths": [7],
            "required_conditions": {
                "RiskStatus": "Safe",
                "InfoCompleteness": True,
                "UserIntention": "Urge",
                "orderStatus": "Delivered",
                "EmergencyLevel": "Normal",
            }
        },

        "modify_arrived_reject": {
            "description": "修改已到达拒绝 - 已到达包裹无法修改",
            "possible_paths": [8],
            "required_conditions": {
                "RiskStatus": "Safe",
                "InfoCompleteness": True,
                "UserIntention": "Modify",
                "orderStatus": "Arrived",
            }
        },

        "modify_delivered_makeup": {
            "description": "修改已送达补差 - 已送达包裹修改需补差",
            "possible_paths": [9],
            "required_conditions": {
                "RiskStatus": "Safe",
                "InfoCompleteness": True,
                "UserIntention": "Modify",
                "orderStatus": "Delivered",
            }
        },

        "modify_undelivered_ok": {
            "description": "修改未送达通过 - 未送达包裹可修改",
            "possible_paths": [10],
            "required_conditions": {
                "RiskStatus": "Safe",
                "InfoCompleteness": True,
                "UserIntention": "Modify",
                "orderStatus": "Undelivered",
            }
        },

        "complaint_arrived_invalid": {
            "description": "投诉到达无效 - 到达包裹投诉不合理",
            "possible_paths": [11],
            "required_conditions": {
                "RiskStatus": "Safe",
                "InfoCompleteness": True,
                "UserIntention": "Complaint",
                "orderStatus": "Arrived",
                "ComplaintValidity": False,
            }
        },

        "complaint_arrived_valid_insured": {
            "description": "投诉到达有保险 - 到达包裹投诉合理且有保险",
            "possible_paths": [12],
            "required_conditions": {
                "RiskStatus": "Safe",
                "InfoCompleteness": True,
                "UserIntention": "Complaint",
                "orderStatus": "Arrived",
                "ComplaintValidity": True,
                "hasInsurance": True,
            }
        },

        "complaint_arrived_valid_uninsured_calm": {
            "description": "投诉到达无保险平静 - 到达包裹投诉合理无保险且平静",
            "possible_paths": [13],
            "required_conditions": {
                "RiskStatus": "Safe",
                "InfoCompleteness": True,
                "UserIntention": "Complaint",
                "orderStatus": "Arrived",
                "ComplaintValidity": True,
                "hasInsurance": False,
                "EmotionalState": "Calm",
            }
        },

        "complaint_arrived_valid_uninsured_dissatisfied": {
            "description": "投诉到达无保险不满 - 到达包裹投诉合理无保险且不满",
            "possible_paths": [14],
            "required_conditions": {
                "RiskStatus": "Safe",
                "InfoCompleteness": True,
                "UserIntention": "Complaint",
                "orderStatus": "Arrived",
                "ComplaintValidity": True,
                "hasInsurance": False,
                "EmotionalState": "Dissatisfied",
            }
        },

        "complaint_undelivered_urgent": {
            "description": "投诉未送达紧急 - 未送达包裹投诉用户紧急",
            "possible_paths": [15],
            "required_conditions": {
                "RiskStatus": "Safe",
                "InfoCompleteness": True,
                "UserIntention": "Complaint",
                "orderStatus": "Undelivered",
                "EmergencyLevel": "Urgent",
            }
        },

        "complaint_undelivered_normal": {
            "description": "投诉未送达正常 - 未送达包裹投诉用户不紧急",
            "possible_paths": [16],
            "required_conditions": {
                "RiskStatus": "Safe",
                "InfoCompleteness": True,
                "UserIntention": "Complaint",
                "orderStatus": "Undelivered",
                "EmergencyLevel": "Normal",
            }
        },

        "complaint_delivered_urgent": {
            "description": "投诉已送达紧急 - 已送达包裹投诉用户紧急",
            "possible_paths": [17],
            "required_conditions": {
                "RiskStatus": "Safe",
                "InfoCompleteness": True,
                "UserIntention": "Complaint",
                "orderStatus": "Delivered",
                "EmergencyLevel": "Urgent",
            }
        },

        "complaint_delivered_normal": {
            "description": "投诉已送达正常 - 已送达包裹投诉用户不紧急",
            "possible_paths": [18],
            "required_conditions": {
                "RiskStatus": "Safe",
                "InfoCompleteness": True,
                "UserIntention": "Complaint",
                "orderStatus": "Delivered",
                "EmergencyLevel": "Normal",
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
    try:
        from sop_graph import build_logistics_delivery_sop_graph

        # 获取SOP图的标准化路径（不含start和end）
        sop_graph = build_logistics_delivery_sop_graph()
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
    except ImportError:
        print("⚠️  无法导入sop_graph模块，跳过验证")
        return None


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
        print(f"  System Variables: {path['system_variables']}")
        print(f"  Expected Path: {' -> '.join(path['expected_path'])}")
        print(f"  Final Output: {path['final_output']}")
