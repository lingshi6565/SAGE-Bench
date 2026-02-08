# 每个可能的path分别进行生成
# python代码将每个路径和对应的classification output对应
# 根据SOP图构建，确保与sop_graph.py完全一致

import json
from typing import Dict, List, Any


def generate_path_list():
    """
    根据5个分类字段和2个系统变量生成所有可能的决策路径
    与sop_graph.py中的build_government_enterprise_sop_graph()保持一致

    字段说明:
    1. CoreDemand: String ("RescheduleOrRefund"/"Complaint"/"Inqury") - 用户核心诉求
    2. ChangeReason: String ("Personal"/"Airline"/"Weather") - 改退签原因（仅RescheduleOrRefund使用）
    3. UserEmotion: String ("Urgent"/"Dissatisfied"/"Normal") - 用户情绪状态
    4. DocumentValidity: String ("Valid"/"Invalid") - 凭证是否有效
    5. IsInfoComplete: String ("Complete"/"Incomplete") - 信息是否完善
    
    系统变量:
    1. memberLevel: String ("VIP"/"Regular"/"Blacklist") - 用户会员等级
    2. hasInsurance: Boolean (True/False) - 是否购买保险
    """
    path_list = []

    # ==================== 路径1-2: 咨询分支 ====================
    # 1字段分类 -> 2核心诉求 -> 5信息是否完善
    
    # 路径1: Inqury + Incomplete -> 补充凭证
    path_list.append({
        "Classification_items": ["Inqury", None, None, None, "Incomplete"],
        "system_variables": {},
        "expected_path": ["step1", "step2", "step5"],
        "final_output": {"Action": "Supplementary"}
    })

    # 路径2: Inqury + Complete -> 查询信息
    path_list.append({
        "Classification_items": ["Inqury", None, None, None, "Complete"],
        "system_variables": {},
        "expected_path": ["step1", "step2", "step5"],
        "final_output": {"Action": "Enquiry"}
    })

    # ==================== 路径3-6: 改退票+个人原因分支 ====================
    # 1字段分类 -> 2核心诉求 -> 3变更原因(Personal) -> 5信息是否完善 -> 7是否购买保险
    
    # 路径3: Personal + Incomplete -> 补充凭证
    path_list.append({
        "Classification_items": ["RescheduleOrRefund", "Personal", None, None, "Incomplete"],
        "system_variables": {},
        "expected_path": ["step1", "step2", "step3", "step5"],
        "final_output": {"Action": "Supplementary"}
    })

    # 路径4: Personal + Incomplete -> 补充凭证
    path_list.append({
        "Classification_items": ["RescheduleOrRefund", "Personal", None, "Invalid", "Complete"],
        "system_variables": {},
        "expected_path": ["step1", "step2", "step3", "step5", "step8"],
        "final_output": {"Action": "Supplementary"}
    })

    # 路径5: Personal + Complete + hasInsurance=True -> 改退票
    path_list.append({
        "Classification_items": ["RescheduleOrRefund", "Personal", None, "Valid", "Complete"],
        "system_variables": {"hasInsurance": True, "memberLevel": "Regular"},
        "expected_path": ["step1", "step2", "step3", "step5", "step8", "step4", "step7"],
        "final_output": {"Action": "RescheduleOrRefund"}
    })

    # 路径6: Personal + Complete + hasInsurance=False -> 改退票+扣除手续费
    path_list.append({
        "Classification_items": ["RescheduleOrRefund", "Personal", None, "Valid", "Complete"],
        "system_variables": {"hasInsurance": False, "memberLevel": "Regular"},
        "expected_path": ["step1", "step2", "step3", "step5", "step8", "step4","step7"],
        "final_output": {"Action": "RescheduleOrRefund+HandlingFee"}
    })

    # 路径7: Personal + Complete + memberLevel=VIP -> 改退票+补偿
    path_list.append({
        "Classification_items": ["RescheduleOrRefund", "Personal", None, "Valid", "Complete"],
        "system_variables": {"memberLevel": "VIP"},
        "expected_path": ["step1", "step2", "step3", "step5", "step8", "step4"],
        "final_output": {"Action": "RescheduleOrRefund"}
    })

    # 路径8: Personal + Complete + memberLevel=VIP -> 改退票+补偿
    path_list.append({
        "Classification_items": ["RescheduleOrRefund", "Personal", None, "Valid", "Complete"],
        "system_variables": {"memberLevel": "Blacklist"},
        "expected_path": ["step1", "step2", "step3", "step5", "step8", "step4"],
        "final_output": {"Action": "Reject"}
    })

    # ==================== 路径7-12: 改退票+航司/天气原因分支 ====================
    # 1字段分类 -> 2核心诉求 -> 3变更原因(Airline/Weather) -> 4会员等级
    
    # 路径9: Airline + Regular -> 改退票
    path_list.append({
        "Classification_items": ["RescheduleOrRefund", "Airline", None, None, None],
        "system_variables": {"memberLevel": "Regular"},
        "expected_path": ["step1", "step2", "step3", "step4"],
        "final_output": {"Action": "RescheduleOrRefund"}
    })

    # 路径10: Airline + VIP -> 改退票+补偿
    path_list.append({
        "Classification_items": ["RescheduleOrRefund", "Airline", None, None, None],
        "system_variables": {"memberLevel": "VIP"},
        "expected_path": ["step1", "step2", "step3", "step4"],
        "final_output": {"Action": "RescheduleOrRefund+Compensation"}
    })

    # 路径11: Airline + Blacklist -> 拒绝请求
    path_list.append({
        "Classification_items": ["RescheduleOrRefund", "Airline", None, None, None],
        "system_variables": {"memberLevel": "Blacklist"},
        "expected_path": ["step1", "step2", "step3", "step4"],
        "final_output": {"Action": "RescheduleOrRefund"}
    })

    # 路径12: Airline + Regular -> 改退票
    path_list.append({
        "Classification_items": ["RescheduleOrRefund", "Weather", None, None, None],
        "system_variables": {"memberLevel": "Regular"},
        "expected_path": ["step1", "step2", "step3", "step4"],
        "final_output": {"Action": "RescheduleOrRefund"}
    })

    # 路径13: Airline + VIP -> 改退票+补偿
    path_list.append({
        "Classification_items": ["RescheduleOrRefund", "Weather", None, None, None],
        "system_variables": {"memberLevel": "VIP"},
        "expected_path": ["step1", "step2", "step3", "step4"],
        "final_output": {"Action": "RescheduleOrRefund+Compensation"}
    })

    # 路径14: Airline + Blacklist -> 拒绝请求
    path_list.append({
        "Classification_items": ["RescheduleOrRefund", "Weather", None, None, None],
        "system_variables": {"memberLevel": "Blacklist"},
        "expected_path": ["step1", "step2", "step3", "step4"],
        "final_output": {"Action": "RescheduleOrRefund"}
    })

    # ==================== 路径13-16: 投诉分支 ====================
    # 1字段分类 -> 2核心诉求 -> 4会员等级
    
    # 路径15: Complaint + Regular + Normal情绪 -> 安抚
    path_list.append({
        "Classification_items": ["Complaint", None, "Normal", None, None],
        "system_variables": {"memberLevel": "Regular"},
        "expected_path": ["step1", "step2", "step4", "step6"],
        "final_output": {"Action": "Comfort"}
    })

    # 路径16: Complaint + Regular + 其他情绪 + 无合理凭证 -> 安抚
    path_list.append({
        "Classification_items": ["Complaint", None, "Urgent", "Invalid", None],
        "system_variables": {"memberLevel": "Regular"},
        "expected_path": ["step1", "step2", "step4", "step6", "step8"],
        "final_output": {"Action": "Comfort"}
    })

    # 路径17: Complaint + Regular + 其他情绪 + 有合理凭证 -> 赔偿
    path_list.append({
        "Classification_items": ["Complaint", None, "Dissatisfied", "Valid", None],
        "system_variables": {"memberLevel": "Regular"},
        "expected_path": ["step1", "step2", "step4", "step6", "step8"],
        "final_output": {"Action": "Compensation"}
    })

    # 路径18: Complaint + VIP -> 转人工
    path_list.append({
        "Classification_items": ["Complaint", None, None, None, None],
        "system_variables": {"memberLevel": "VIP"},
        "expected_path": ["step1", "step2", "step4"],
        "final_output": {"Action": "TransHuman"}
    })

    # 路径19: Complaint + VIP -> 转人工
    path_list.append({
        "Classification_items": ["Complaint", None, None, None, None],
        "system_variables": {"memberLevel": "Blacklist"},
        "expected_path": ["step1", "step2", "step4"],
        "final_output": {"Action": "Reject"}
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
        "inquiry_incomplete": {
            "description": "信息不完整的咨询 - 用户信息不完整需补充",
            "possible_paths": [1],
            "required_conditions": {
                "CoreDemand": "Inqury",
                "IsInfoComplete": "Incomplete",
            }
        },

        "inquiry_complete": {
            "description": "完整的咨询 - 用户提供完整信息的咨询",
            "possible_paths": [2],
            "required_conditions": {
                "CoreDemand": "Inqury",
                "IsInfoComplete": "Complete",
            }
        },

        "personal_reason_incomplete": {
            "description": "个人原因改签（信息不完整）",
            "possible_paths": [3],
            "required_conditions": {
                "CoreDemand": "RescheduleOrRefund",
                "ChangeReason": "Personal",
                "IsInfoComplete": "Incomplete",
            }
        },

        "personal_reason_invalid_doc": {
            "description": "个人原因改签（信息完整+凭证无效）",
            "possible_paths": [4],
            "required_conditions": {
                "CoreDemand": "RescheduleOrRefund",
                "ChangeReason": "Personal",
                "IsInfoComplete": "Complete",
                "DocumentValidity": "Invalid",
            }
        },

        "personal_reason_regular_with_insurance": {
            "description": "个人原因改签（普通会员+有保险）",
            "possible_paths": [5],
            "required_conditions": {
                "CoreDemand": "RescheduleOrRefund",
                "ChangeReason": "Personal",
                "IsInfoComplete": "Complete",
                "DocumentValidity": "Valid",
                "memberLevel": "Regular",
                "hasInsurance": True,
            }
        },

        "personal_reason_regular_no_insurance": {
            "description": "个人原因改签（普通会员+无保险）",
            "possible_paths": [6],
            "required_conditions": {
                "CoreDemand": "RescheduleOrRefund",
                "ChangeReason": "Personal",
                "IsInfoComplete": "Complete",
                "DocumentValidity": "Valid",
                "memberLevel": "Regular",
                "hasInsurance": False,
            }
        },

        "personal_reason_vip": {
            "description": "VIP个人原因改签",
            "possible_paths": [7],
            "required_conditions": {
                "CoreDemand": "RescheduleOrRefund",
                "ChangeReason": "Personal",
                "IsInfoComplete": "Complete",
                "DocumentValidity": "Valid",
                "memberLevel": "VIP",
            }
        },

        "personal_reason_blacklist": {
            "description": "黑名单个人原因改签",
            "possible_paths": [8],
            "required_conditions": {
                "CoreDemand": "RescheduleOrRefund",
                "ChangeReason": "Personal",
                "IsInfoComplete": "Complete",
                "DocumentValidity": "Valid",
                "memberLevel": "Blacklist",
            }
        },

        "airline_reason_regular": {
            "description": "航司原因改签（普通会员）",
            "possible_paths": [9],
            "required_conditions": {
                "CoreDemand": "RescheduleOrRefund",
                "ChangeReason": "Airline",
                "memberLevel": "Regular",
            }
        },

        "airline_reason_vip": {
            "description": "航司原因改签（VIP）",
            "possible_paths": [10],
            "required_conditions": {
                "CoreDemand": "RescheduleOrRefund",
                "ChangeReason": "Airline",
                "memberLevel": "VIP",
            }
        },

        "airline_reason_blacklist": {
            "description": "航司原因改签（黑名单）",
            "possible_paths": [11],
            "required_conditions": {
                "CoreDemand": "RescheduleOrRefund",
                "ChangeReason": "Airline",
                "memberLevel": "Blacklist",
            }
        },

        "weather_reason_regular": {
            "description": "天气原因改签（普通会员）",
            "possible_paths": [12],
            "required_conditions": {
                "CoreDemand": "RescheduleOrRefund",
                "ChangeReason": "Weather",
                "memberLevel": "Regular",
            }
        },

        "weather_reason_vip": {
            "description": "天气原因改签（VIP）",
            "possible_paths": [13],
            "required_conditions": {
                "CoreDemand": "RescheduleOrRefund",
                "ChangeReason": "Weather",
                "memberLevel": "VIP",
            }
        },

        "weather_reason_blacklist": {
            "description": "天气原因改签（黑名单）",
            "possible_paths": [14],
            "required_conditions": {
                "CoreDemand": "RescheduleOrRefund",
                "ChangeReason": "Weather",
                "memberLevel": "Blacklist",
            }
        },

        "complaint_regular_normal_emotion": {
            "description": "投诉-普通会员情绪正常",
            "possible_paths": [15],
            "required_conditions": {
                "CoreDemand": "Complaint",
                "UserEmotion": "Normal",
                "memberLevel": "Regular",
            }
        },

        "complaint_regular_urgent_invalid_doc": {
            "description": "投诉-普通会员紧急情绪无凭证",
            "possible_paths": [16],
            "required_conditions": {
                "CoreDemand": "Complaint",
                "UserEmotion": "Urgent",
                "DocumentValidity": "Invalid",
                "memberLevel": "Regular",
            }
        },

        "complaint_regular_dissatisfied_valid_doc": {
            "description": "投诉-普通会员不满情绪有凭证",
            "possible_paths": [17],
            "required_conditions": {
                "CoreDemand": "Complaint",
                "UserEmotion": "Dissatisfied",
                "DocumentValidity": "Valid",
                "memberLevel": "Regular",
            }
        },

        "vip_complaint": {
            "description": "VIP投诉转人工",
            "possible_paths": [18],
            "required_conditions": {
                "CoreDemand": "Complaint",
                "memberLevel": "VIP",
            }
        },

        "blacklist_complaint": {
            "description": "黑名单投诉拒绝",
            "possible_paths": [19],
            "required_conditions": {
                "CoreDemand": "Complaint",
                "memberLevel": "Blacklist",
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
        from sop_graph import build_government_enterprise_sop_graph

        # 获取SOP图的标准化路径（不含start和end）
        sop_graph = build_government_enterprise_sop_graph()
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
