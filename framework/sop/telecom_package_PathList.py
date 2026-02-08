# 每个可能的path分别进行生成
# python代码将每个路径和对应的classification output 对应
# 根据SOP图构建，确保与sop_graph.py完全一致

import json
from typing import Dict, List, Any


def generate_path_list():
    
    path_list = []

    # ========== Enquiry分支 ==========
    # 路径1: Enquiry + Agree + Data + NoContract -> ChangeOrder
    path_list.append({
        "Classification_items": ["Enquiry", "Agree", "Data", "Calm"],
        "system_variables": {"PackageStatus": "NoContract", "Penalty": 0},
        "expected_path": ["step1", "step2", "step3", "step6", "step4"],
        "final_output": {"Action": "ChangeOrder"}
    })

    # 路径2: Enquiry + Agree + Voice + NoContract -> ChangeOrder
    path_list.append({
        "Classification_items": ["Enquiry", "Agree", "Voice", "Calm"],
        "system_variables": {"PackageStatus": "NoContract", "Penalty": 0},
        "expected_path": ["step1", "step2", "step3", "step6", "step4"],
        "final_output": {"Action": "ChangeOrder"}
    })

    # 路径3: Enquiry + Agree + Data + Contracted + Penalty=0 -> ChangeOrder
    path_list.append({
        "Classification_items": ["Enquiry", "Agree", "Data", "Calm"],
        "system_variables": {"PackageStatus": "Contracted", "Penalty": 0},
        "expected_path": ["step1", "step2", "step3", "step6", "step4", "step5"],
        "final_output": {"Action": "ChangeOrder"}
    })

    # 路径4: Enquiry + Agree + Voice + Contracted + Penalty=0 -> ChangeOrder
    path_list.append({
        "Classification_items": ["Enquiry", "Agree", "Voice", "Calm"],
        "system_variables": {"PackageStatus": "Contracted", "Penalty": 0},
        "expected_path": ["step1", "step2", "step3", "step6", "step4", "step5"],
        "final_output": {"Action": "ChangeOrder"}
    })

    # 路径5: Enquiry + Agree + Data + Contracted + Penalty>0 + Calm -> ChangeOrder
    path_list.append({
        "Classification_items": ["Enquiry", "Agree", "Data", "Calm"],
        "system_variables": {"PackageStatus": "Contracted", "Penalty": 100},
        "expected_path": ["step1", "step2", "step3", "step6", "step4", "step5", "step7"],
        "final_output": {"Action": "ChangeOrder"}
    })

    # 路径6: Enquiry + Agree + Voice + Contracted + Penalty>0 + Calm -> ChangeOrder
    path_list.append({
        "Classification_items": ["Enquiry", "Agree", "Voice", "Calm"],
        "system_variables": {"PackageStatus": "Contracted", "Penalty": 100},
        "expected_path": ["step1", "step2", "step3", "step6", "step4", "step5", "step7"],
        "final_output": {"Action": "ChangeOrder"}
    })

    # 路径7: Enquiry + Agree + Data + Contracted + Penalty>0 + Discontent -> TransHuman
    path_list.append({
        "Classification_items": ["Enquiry", "Agree", "Data", "Discontent"],
        "system_variables": {"PackageStatus": "Contracted", "Penalty": 100},
        "expected_path": ["step1", "step2", "step3", "step6", "step4", "step5", "step7"],
        "final_output": {"Action": "TransHuman"}
    })

    # 路径8: Enquiry + Agree + Voice + Contracted + Penalty>0 + Discontent -> TransHuman
    path_list.append({
        "Classification_items": ["Enquiry", "Agree", "Voice", "Discontent"],
        "system_variables": {"PackageStatus": "Contracted", "Penalty": 100},
        "expected_path": ["step1", "step2", "step3", "step6", "step4", "step5", "step7"],
        "final_output": {"Action": "TransHuman"}
    })

    # 路径9: Enquiry + Reject + Data + NoContract -> GoodBye
    path_list.append({
        "Classification_items": ["Enquiry", "Reject", "Data", "Calm"],
        "system_variables": {"PackageStatus": "NoContract", "Penalty": 0},
        "expected_path": ["step1", "step2", "step3", "step6"],
        "final_output": {"Action": "GoodBye"}
    })

    # 路径10: Enquiry + Reject + Voice + NoContract -> GoodBye
    path_list.append({
        "Classification_items": ["Enquiry", "Reject", "Voice", "Calm"],
        "system_variables": {"PackageStatus": "NoContract", "Penalty": 0},
        "expected_path": ["step1", "step2", "step3", "step6"],
        "final_output": {"Action": "GoodBye"}
    })

    # 路径11: Enquiry + Reject + Data + Contracted -> GoodBye
    path_list.append({
        "Classification_items": ["Enquiry", "Reject", "Data", "Calm"],
        "system_variables": {"PackageStatus": "Contracted", "Penalty": 0},
        "expected_path": ["step1", "step2", "step3", "step6"],
        "final_output": {"Action": "GoodBye"}
    })

    # 路径12: Enquiry + Hesitate + Data + NoContract -> GoodBye
    path_list.append({
        "Classification_items": ["Enquiry", "Hesitate", "Data", "Calm"],
        "system_variables": {"PackageStatus": "NoContract", "Penalty": 0},
        "expected_path": ["step1", "step2", "step3", "step6"],
        "final_output": {"Action": "GoodBye"}
    })

    # 路径13: Enquiry + Hesitate + Voice + NoContract -> GoodBye
    path_list.append({
        "Classification_items": ["Enquiry", "Hesitate", "Voice", "Calm"],
        "system_variables": {"PackageStatus": "NoContract", "Penalty": 0},
        "expected_path": ["step1", "step2", "step3", "step6"],
        "final_output": {"Action": "GoodBye"}
    })

    # 路径14: Enquiry + Hesitate + Data + Contracted -> GoodBye
    path_list.append({
        "Classification_items": ["Enquiry", "Hesitate", "Data", "Calm"],
        "system_variables": {"PackageStatus": "Contracted", "Penalty": 0},
        "expected_path": ["step1", "step2", "step3", "step6"],
        "final_output": {"Action": "GoodBye"}
    })

    # ========== Change分支 ==========
    # 路径15: Change + Data + NoContract -> ChangeOrder
    path_list.append({
        "Classification_items": ["Change", None, "Data", "Calm"],
        "system_variables": {"PackageStatus": "NoContract", "Penalty": 0},
        "expected_path": ["step1", "step2", "step4"],
        "final_output": {"Action": "ChangeOrder"}
    })

    # 路径16: Change + Voice + NoContract -> ChangeOrder
    path_list.append({
        "Classification_items": ["Change", None, "Voice", "Calm"],
        "system_variables": {"PackageStatus": "NoContract", "Penalty": 0},
        "expected_path": ["step1", "step2", "step4"],
        "final_output": {"Action": "ChangeOrder"}
    })

    # 路径17: Change + Data + Contracted + Penalty=0 -> ChangeOrder
    path_list.append({
        "Classification_items": ["Change", None, "Data", "Calm"],
        "system_variables": {"PackageStatus": "Contracted", "Penalty": 0},
        "expected_path": ["step1", "step2", "step4", "step5"],
        "final_output": {"Action": "ChangeOrder"}
    })

    # 路径18: Change + Voice + Contracted + Penalty=0 -> ChangeOrder
    path_list.append({
        "Classification_items": ["Change", None, "Voice", "Calm"],
        "system_variables": {"PackageStatus": "Contracted", "Penalty": 0},
        "expected_path": ["step1", "step2", "step4", "step5"],
        "final_output": {"Action": "ChangeOrder"}
    })

    # 路径19: Change + Data + Contracted + Penalty>0 + Calm -> ChangeOrder
    path_list.append({
        "Classification_items": ["Change", None, "Data", "Calm"],
        "system_variables": {"PackageStatus": "Contracted", "Penalty": 200},
        "expected_path": ["step1", "step2", "step4", "step5", "step7"],
        "final_output": {"Action": "ChangeOrder"}
    })

    # 路径20: Change + Voice + Contracted + Penalty>0 + Calm -> ChangeOrder
    path_list.append({
        "Classification_items": ["Change", None, "Voice", "Calm"],
        "system_variables": {"PackageStatus": "Contracted", "Penalty": 200},
        "expected_path": ["step1", "step2", "step4", "step5", "step7"],
        "final_output": {"Action": "ChangeOrder"}
    })

    # 路径21: Change + Data + Contracted + Penalty>0 + Discontent -> TransHuman
    path_list.append({
        "Classification_items": ["Change", None, "Data", "Discontent"],
        "system_variables": {"PackageStatus": "Contracted", "Penalty": 300},
        "expected_path": ["step1", "step2", "step4", "step5", "step7"],
        "final_output": {"Action": "TransHuman"}
    })

    # 路径22: Change + Voice + Contracted + Penalty>0 + Discontent -> TransHuman
    path_list.append({
        "Classification_items": ["Change", None, "Voice", "Discontent"],
        "system_variables": {"PackageStatus": "Contracted", "Penalty": 300},
        "expected_path": ["step1", "step2", "step4", "step5", "step7"],
        "final_output": {"Action": "TransHuman"}
    })

    # ========== Cancel分支 ==========
    # 路径23: Cancel + NoContract -> ChangeOrder
    # 注意：Cancel分支不需要ConsumptionProfile和EmotionTag（除非Penalty>0）
    path_list.append({
        "Classification_items": ["Cancel", None, None, "Calm"],
        "system_variables": {"PackageStatus": "NoContract", "Penalty": 0},
        "expected_path": ["step1", "step2", "step5"],
        "final_output": {"Action": "ChangeOrder"}
    })

    # 路径24: Cancel + Contracted + Penalty=0 -> ChangeOrder
    path_list.append({
        "Classification_items": ["Cancel", None, None, "Calm"],
        "system_variables": {"PackageStatus": "Contracted", "Penalty": 0},
        "expected_path": ["step1", "step2", "step5"],
        "final_output": {"Action": "ChangeOrder"}
    })

    # 路径25: Cancel + Contracted + Penalty>0 + Calm -> ChangeOrder
    path_list.append({
        "Classification_items": ["Cancel", None, None, "Calm"],
        "system_variables": {"PackageStatus": "Contracted", "Penalty": 250},
        "expected_path": ["step1", "step2", "step5", "step7"],
        "final_output": {"Action": "ChangeOrder"}
    })

    # 路径26: Cancel + Contracted + Penalty>0 + Discontent -> TransHuman
    path_list.append({
        "Classification_items": ["Cancel", None, None, "Discontent"],
        "system_variables": {"PackageStatus": "Contracted", "Penalty": 600},
        "expected_path": ["step1", "step2", "step5", "step7"],
        "final_output": {"Action": "TransHuman"}
    })

    return path_list


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
        "enquiry_data_agree": {
            "description": "咨询流量套餐（倾向办理）",
            "possible_paths": [1, 3, 5, 7],  # 流量+Agree路径
            "required_conditions": {
                "ConsumptionType": "Enquiry",
                "ApplicationTendency": "Agree",
                "ConsumptionProfile": "Data",
            }
        },

        "enquiry_voice_agree": {
            "description": "咨询通话套餐（倾向办理）",
            "possible_paths": [2, 4, 6, 8],  # 通话+Agree路径
            "required_conditions": {
                "ConsumptionType": "Enquiry",
                "ApplicationTendency": "Agree",
                "ConsumptionProfile": "Voice",
            }
        },

        "enquiry_hesitate": {
            "description": "咨询但犹豫不决",
            "possible_paths": [12, 13, 14],  # Hesitate路径都是GoodBye
            "required_conditions": {
                "ConsumptionType": "Enquiry",
                "ApplicationTendency": "Hesitate",
            }
        },

        "enquiry_reject": {
            "description": "咨询但拒绝办理",
            "possible_paths": [9, 10, 11],  # Reject路径都是GoodBye
            "required_conditions": {
                "ConsumptionType": "Enquiry",
                "ApplicationTendency": "Reject",
            }
        },

        "change_no_contract": {
            "description": "更换套餐（无合约）",
            "possible_paths": [15, 16],  # Change+NoContract路径
            "required_conditions": {
                "ConsumptionType": "Change",
                "PackageStatus": "NoContract",
            }
        },

        "change_with_contract_no_penalty": {
            "description": "更换套餐（有合约无违约金）",
            "possible_paths": [17, 18],  # Change+Contracted+Penalty=0路径
            "required_conditions": {
                "ConsumptionType": "Change",
                "PackageStatus": "Contracted",
                "Penalty": 0,
            }
        },

        "change_with_penalty_calm": {
            "description": "更换套餐（有违约金且情绪平静）",
            "possible_paths": [19, 20],  # Change+Penalty>0+Calm路径
            "required_conditions": {
                "ConsumptionType": "Change",
                "PackageStatus": "Contracted",
                "EmotionTag": "Calm",
            }
        },

        "change_with_penalty_discontent": {
            "description": "更换套餐（有违约金且情绪不满）",
            "possible_paths": [21, 22],  # Change+Penalty>0+Discontent路径
            "required_conditions": {
                "ConsumptionType": "Change",
                "PackageStatus": "Contracted",
                "EmotionTag": "Discontent",
            }
        },

        "cancel_no_penalty": {
            "description": "取消套餐（无违约金）",
            "possible_paths": [23, 24],  # Cancel+Penalty=0路径
            "required_conditions": {
                "ConsumptionType": "Cancel",
                "Penalty": 0,
            }
        },

        "cancel_with_penalty_calm": {
            "description": "取消套餐（有违约金且情绪平静）",
            "possible_paths": [25],  # Cancel+Penalty>0+Calm路径
            "required_conditions": {
                "ConsumptionType": "Cancel",
                "PackageStatus": "Contracted",
                "EmotionTag": "Calm",
            }
        },

        "cancel_with_penalty_discontent": {
            "description": "取消套餐（有违约金且情绪不满）",
            "possible_paths": [26],  # Cancel+Penalty>0+Discontent路径
            "required_conditions": {
                "ConsumptionType": "Cancel",
                "PackageStatus": "Contracted",
                "EmotionTag": "Discontent",
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
        from sop_graph import build_telecom_package_sop_graph

        # 获取SOP图的标准化路径（不含start和end）
        sop_graph = build_telecom_package_sop_graph()
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
