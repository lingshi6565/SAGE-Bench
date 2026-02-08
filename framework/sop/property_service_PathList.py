# 每个可能的path分别进行生成
# python代码将每个路径和对应的classification output对应
# 根据SOP流程构建，确保与sop_graph.py完全一致

import json
from typing import Dict, List, Any


def generate_path_list():
    """
    根据5个分类字段和2个系统变量生成所有可能的决策路径
    与sop_graph.py中的build_property_service_sop_graph()保持一致

    字段说明:
    1. CoreIntention: String ("Payment"/"Complaint"/"Repair") - 住户对话的意图
    2. EmotionTag: String ("Calm"/"Discontent") - 住户在对话中表现的情绪
    3. RepairItemCategory: String ("IndoorFacilities"/"EnvironmentalHygiene") - 住户报修事项的具体分类
    4. RelatedScope: String ("Personal"/"Public") - 事项涉及的范围
    5. EmergencyLevel: String ("Urgent"/"NoUrgent") - 事项紧急程度
    
    系统变量:
    1. HouseStatus: String ("Occupied"/"Rented"/"UnOccupied") - 业主房屋的居住状态
    2. FeePaymentStatus: String ("Settled"/"Unpaid") - 业主物业费的缴费状态
    """
    path_list = []

    # ==================== GROUP A: CoreIntention=Payment 分支 ====================
    # step1 -> step2 -> step3: 检查房屋状态
    #   - UnOccupied -> ACTION=PayInformation (END)
    #   - Occupied/Rented -> step6
    # step6: 检查缴费状态
    #   - Settled -> ACTION=PayInformation (END)
    #   - Unpaid -> ACTION=Payment (END)

    # 路径1: Payment + Occupied + Settled
    path_list.append({
        "Classification_items": ["Payment", None, None, None, None],
        "system_variables": {"HouseStatus": "Occupied", "FeePaymentStatus": "Settled"},
        "expected_path": ["step1", "step2", "step3", "step6"],
        "final_output": {"Action": "PayInformation"}
    })

    # 路径2: Payment + Occupied + Unpaid
    path_list.append({
        "Classification_items": ["Payment", None, None, None, None],
        "system_variables": {"HouseStatus": "Occupied", "FeePaymentStatus": "Unpaid"},
        "expected_path": ["step1", "step2", "step3", "step6"],
        "final_output": {"Action": "Payment"}
    })

    # 路径3: Payment + Rented + Settled
    path_list.append({
        "Classification_items": ["Payment", None, None, None, None],
        "system_variables": {"HouseStatus": "Rented", "FeePaymentStatus": "Settled"},
        "expected_path": ["step1", "step2", "step3", "step6"],
        "final_output": {"Action": "PayInformation"}
    })

    # 路径4: Payment + Rented + Unpaid
    path_list.append({
        "Classification_items": ["Payment", None, None, None, None],
        "system_variables": {"HouseStatus": "Rented", "FeePaymentStatus": "Unpaid"},
        "expected_path": ["step1", "step2", "step3", "step6"],
        "final_output": {"Action": "Payment"}
    })

    # 路径5: Payment + UnOccupied
    path_list.append({
        "Classification_items": ["Payment", None, None, None, None],
        "system_variables": {"HouseStatus": "UnOccupied"},
        "expected_path": ["step1", "step2", "step3"],
        "final_output": {"Action": "PayInformation"}
    })

    # ==================== GROUP B: CoreIntention=Complaint 分支 ====================
    # step1 -> step2 -> step3: 检查房屋状态
    #   - UnOccupied -> step7
    #   - Occupied/Rented -> step6
    # step6: 检查缴费状态
    #   - Unpaid -> ACTION=Payment (END)
    #   - Settled -> step7
    # step7: 检查情绪
    #   - Calm -> ACTION=Comfort (END)
    #   - Discontent -> ACTION=TransHuman (END)

    # 路径6: Complaint + Occupied + Settled + Calm
    path_list.append({
        "Classification_items": ["Complaint", "Calm", None, None, None],
        "system_variables": {"HouseStatus": "Occupied", "FeePaymentStatus": "Settled"},
        "expected_path": ["step1", "step2", "step3", "step6", "step7"],
        "final_output": {"Action": "Comfort"}
    })

    # 路径7: Complaint + Occupied + Settled + Discontent
    path_list.append({
        "Classification_items": ["Complaint", "Discontent", None, None, None],
        "system_variables": {"HouseStatus": "Occupied", "FeePaymentStatus": "Settled"},
        "expected_path": ["step1", "step2", "step3", "step6", "step7"],
        "final_output": {"Action": "TransHuman"}
    })

    # 路径8: Complaint + Occupied + Unpaid
    path_list.append({
        "Classification_items": ["Complaint", None, None, None, None],
        "system_variables": {"HouseStatus": "Occupied", "FeePaymentStatus": "Unpaid"},
        "expected_path": ["step1", "step2", "step3", "step6"],
        "final_output": {"Action": "Payment"}
    })

    # 路径9: Complaint + Rented + Settled + Calm
    path_list.append({
        "Classification_items": ["Complaint", "Calm", None, None, None],
        "system_variables": {"HouseStatus": "Rented", "FeePaymentStatus": "Settled"},
        "expected_path": ["step1", "step2", "step3", "step6", "step7"],
        "final_output": {"Action": "Comfort"}
    })

    # 路径10: Complaint + Rented + Settled + Discontent
    path_list.append({
        "Classification_items": ["Complaint", "Discontent", None, None, None],
        "system_variables": {"HouseStatus": "Rented", "FeePaymentStatus": "Settled"},
        "expected_path": ["step1", "step2", "step3", "step6", "step7"],
        "final_output": {"Action": "TransHuman"}
    })

    # 路径11: Complaint + Rented + Unpaid
    path_list.append({
        "Classification_items": ["Complaint", None, None, None, None],
        "system_variables": {"HouseStatus": "Rented", "FeePaymentStatus": "Unpaid"},
        "expected_path": ["step1", "step2", "step3", "step6"],
        "final_output": {"Action": "Payment"}
    })

    # 路径12: Complaint + UnOccupied + Calm
    path_list.append({
        "Classification_items": ["Complaint", "Calm", None, None, None],
        "system_variables": {"HouseStatus": "UnOccupied"},
        "expected_path": ["step1", "step2", "step3", "step7"],
        "final_output": {"Action": "Comfort"}
    })

    # 路径13: Complaint + UnOccupied + Discontent
    path_list.append({
        "Classification_items": ["Complaint", "Discontent", None, None, None],
        "system_variables": {"HouseStatus": "UnOccupied"},
        "expected_path": ["step1", "step2", "step3", "step7"],
        "final_output": {"Action": "TransHuman"}
    })

    # ==================== GROUP C: CoreIntention=Repair 分支 ====================
    # step1 -> step2 -> step4 -> step5: 检查事项范围
    #   - Personal -> step6
    #   - Public -> step8
    # step6: 检查缴费状态（Personal时）
    #   - Unpaid -> ACTION=Reject (END)
    #   - Settled -> step8 (继续判断紧急程度)
    # step8: 检查紧急程度
    #   - Urgent -> ACTION=TransHuman (END)
    #   - NoUrgent -> ACTION=Registration (END)


    # 路径14: Repair + Indoor + Personal + Unpaid
    path_list.append({
        "Classification_items": ["Repair", None, "IndoorFacilities", "Personal", None],
        "system_variables": {"FeePaymentStatus": "Unpaid"},
        "expected_path": ["step1", "step2", "step4", "step5", "step6_repair"],
        "final_output": {"Action": "Reject"}
    })


    # 路径15: Repair + Environmental + Personal + Unpaid
    path_list.append({
        "Classification_items": ["Repair", None, "EnvironmentalHygiene", "Personal", None],
        "system_variables": {"FeePaymentStatus": "Unpaid"},
        "expected_path": ["step1", "step2", "step4", "step5", "step6_repair"],
        "final_output": {"Action": "Reject"}
    })

    # 路径16: Repair + Indoor + Personal + Settled + Urgent (补充的缺失路径)
    path_list.append({
        "Classification_items": ["Repair", None, "IndoorFacilities", "Personal", "Urgent"],
        "system_variables": {"FeePaymentStatus": "Settled"},
        "expected_path": ["step1", "step2", "step4", "step5", "step6_repair", "step8"],
        "final_output": {"Action": "TransHuman"}
    })

    # 路径17: Repair + Indoor + Personal + Settled + NoUrgent (补充的缺失路径)
    path_list.append({
        "Classification_items": ["Repair", None, "IndoorFacilities", "Personal", "NoUrgent"],
        "system_variables": {"FeePaymentStatus": "Settled"},
        "expected_path": ["step1", "step2", "step4", "step5", "step6_repair", "step8"],
        "final_output": {"Action": "Registration"}
    })

    # 路径18: Repair + Environmental + Personal + Settled + Urgent (补充的缺失路径)
    path_list.append({
        "Classification_items": ["Repair", None, "EnvironmentalHygiene", "Personal", "Urgent"],
        "system_variables": {"FeePaymentStatus": "Settled"},
        "expected_path": ["step1", "step2", "step4", "step5", "step6_repair", "step8"],
        "final_output": {"Action": "TransHuman"}
    })

    # 路径19: Repair + Environmental + Personal + Settled + NoUrgent (补充的缺失路径)
    path_list.append({
        "Classification_items": ["Repair", None, "EnvironmentalHygiene", "Personal", "NoUrgent"],
        "system_variables": {"FeePaymentStatus": "Settled"},
        "expected_path": ["step1", "step2", "step4", "step5", "step6_repair", "step8"],
        "final_output": {"Action": "Registration"}
    })

    # 路径20: Repair + Indoor + Public + Urgent
    path_list.append({
        "Classification_items": ["Repair", None, "IndoorFacilities", "Public", "Urgent"],
        "system_variables": {},
        "expected_path": ["step1", "step2", "step4", "step5", "step8"],
        "final_output": {"Action": "TransHuman"}
    })

    # 路径21: Repair + Indoor + Public + NoUrgent
    path_list.append({
        "Classification_items": ["Repair", None, "IndoorFacilities", "Public", "NoUrgent"],
        "system_variables": {},
        "expected_path": ["step1", "step2", "step4", "step5", "step8"],
        "final_output": {"Action": "Registration"}
    })

    # 路径22: Repair + Environmental + Public + Urgent
    path_list.append({
        "Classification_items": ["Repair", None, "EnvironmentalHygiene", "Public", "Urgent"],
        "system_variables": {},
        "expected_path": ["step1", "step2", "step4", "step5", "step8"],
        "final_output": {"Action": "TransHuman"}
    })

    # 路径23: Repair + Environmental + Public + NoUrgent
    path_list.append({
        "Classification_items": ["Repair", None, "EnvironmentalHygiene", "Public", "NoUrgent"],
        "system_variables": {},
        "expected_path": ["step1", "step2", "step4", "step5", "step8"],
        "final_output": {"Action": "Registration"}
    })

    return path_list


def get_intent_path_mapping() -> Dict[str, Dict]:
    """
    定义用户意图与可能的决策路径之间的映射关系
    支持多对多关系，用于指导测试场景生成
    
    路径分布:
    - 路径1-5: Payment分支 (5条)
    - 路径6-13: Complaint分支 (8条)
    - 路径14-23: Repair分支 (10条)
    """
    return {
        "payment_inquiry": {
            "description": "缴费咨询 - 业主咨询物业费缴费情况",
            "possible_paths": [1, 2, 3, 4, 5],  # 所有Payment路径
            "required_conditions": {
                "CoreIntention": "Payment",
            }
        },

        "payment_occupied": {
            "description": "自住房缴费 - 自住房业主的缴费处理",
            "possible_paths": [1, 2],  # Payment + Occupied
            "required_conditions": {
                "CoreIntention": "Payment",
                "HouseStatus": "Occupied",
            }
        },

        "payment_rented": {
            "description": "租赁房缴费 - 租赁房业主的缴费处理",
            "possible_paths": [3, 4],  # Payment + Rented
            "required_conditions": {
                "CoreIntention": "Payment",
                "HouseStatus": "Rented",
            }
        },

        "payment_unoccupied": {
            "description": "空置房缴费 - 空置房业主的缴费处理",
            "possible_paths": [5],  # Payment + UnOccupied
            "required_conditions": {
                "CoreIntention": "Payment",
                "HouseStatus": "UnOccupied",
            }
        },

        "payment_unpaid": {
            "description": "欠费缴纳 - 业主补交欠费",
            "possible_paths": [2, 4],  # Payment + Unpaid
            "required_conditions": {
                "CoreIntention": "Payment",
                "FeePaymentStatus": "Unpaid",
            }
        },

        "complaint_occupied_settled_calm": {
            "description": "自住房投诉平静已缴费 - 自住房已缴费投诉且平静",
            "possible_paths": [6],  # Complaint + Occupied + Settled + Calm
            "required_conditions": {
                "CoreIntention": "Complaint",
                "HouseStatus": "Occupied",
                "FeePaymentStatus": "Settled",
                "EmotionTag": "Calm",
            }
        },

        "complaint_occupied_settled_discontent": {
            "description": "自住房投诉不满已缴费 - 自住房已缴费投诉且不满",
            "possible_paths": [7],  # Complaint + Occupied + Settled + Discontent
            "required_conditions": {
                "CoreIntention": "Complaint",
                "HouseStatus": "Occupied",
                "FeePaymentStatus": "Settled",
                "EmotionTag": "Discontent",
            }
        },

        "complaint_occupied_unpaid": {
            "description": "自住房投诉欠费 - 自住房欠费的投诉处理",
            "possible_paths": [8],  # Complaint + Occupied + Unpaid
            "required_conditions": {
                "CoreIntention": "Complaint",
                "HouseStatus": "Occupied",
                "FeePaymentStatus": "Unpaid",
            }
        },

        "complaint_rented_settled_calm": {
            "description": "租赁房投诉平静已缴费 - 租赁房已缴费投诉且平静",
            "possible_paths": [9],  # Complaint + Rented + Settled + Calm
            "required_conditions": {
                "CoreIntention": "Complaint",
                "HouseStatus": "Rented",
                "FeePaymentStatus": "Settled",
                "EmotionTag": "Calm",
            }
        },

        "complaint_rented_settled_discontent": {
            "description": "租赁房投诉不满已缴费 - 租赁房已缴费投诉且不满",
            "possible_paths": [10],  # Complaint + Rented + Settled + Discontent
            "required_conditions": {
                "CoreIntention": "Complaint",
                "HouseStatus": "Rented",
                "FeePaymentStatus": "Settled",
                "EmotionTag": "Discontent",
            }
        },

        "complaint_rented_unpaid": {
            "description": "租赁房投诉欠费 - 租赁房欠费的投诉处理",
            "possible_paths": [11],  # Complaint + Rented + Unpaid
            "required_conditions": {
                "CoreIntention": "Complaint",
                "HouseStatus": "Rented",
                "FeePaymentStatus": "Unpaid",
            }
        },

        "complaint_unoccupied_calm": {
            "description": "空置房投诉平静 - 空置房业主平静的投诉",
            "possible_paths": [12],  # Complaint + UnOccupied + Calm
            "required_conditions": {
                "CoreIntention": "Complaint",
                "HouseStatus": "UnOccupied",
                "EmotionTag": "Calm",
            }
        },

        "complaint_unoccupied_discontent": {
            "description": "空置房投诉不满 - 空置房业主不满的投诉",
            "possible_paths": [13],  # Complaint + UnOccupied + Discontent
            "required_conditions": {
                "CoreIntention": "Complaint",
                "HouseStatus": "UnOccupied",
                "EmotionTag": "Discontent",
            }
        },

        "repair_indoor_personal_unpaid": {
            "description": "室内报修欠费 - 室内设施个户报修但欠费",
            "possible_paths": [14],  # Repair + IndoorFacilities + Personal + Unpaid
            "required_conditions": {
                "CoreIntention": "Repair",
                "RepairItemCategory": "IndoorFacilities",
                "RelatedScope": "Personal",
                "FeePaymentStatus": "Unpaid",
            }
        },

        "repair_environmental_personal_unpaid": {
            "description": "卫生报修欠费 - 环卫设施个户报修但欠费",
            "possible_paths": [15],  # Repair + EnvironmentalHygiene + Personal + Unpaid
            "required_conditions": {
                "CoreIntention": "Repair",
                "RepairItemCategory": "EnvironmentalHygiene",
                "RelatedScope": "Personal",
                "FeePaymentStatus": "Unpaid",
            }
        },

        "repair_indoor_personal_settled_urgent": {
            "description": "室内个户报修已缴费紧急 - 室内设施个户报修且已缴费且紧急",
            "possible_paths": [16],  # Repair + IndoorFacilities + Personal + Settled + Urgent
            "required_conditions": {
                "CoreIntention": "Repair",
                "RepairItemCategory": "IndoorFacilities",
                "RelatedScope": "Personal",
                "FeePaymentStatus": "Settled",
                "EmergencyLevel": "Urgent",
            }
        },

        "repair_indoor_personal_settled_normal": {
            "description": "室内个户报修已缴费非紧急 - 室内设施个户报修且已缴费且非紧急",
            "possible_paths": [17],  # Repair + IndoorFacilities + Personal + Settled + NoUrgent
            "required_conditions": {
                "CoreIntention": "Repair",
                "RepairItemCategory": "IndoorFacilities",
                "RelatedScope": "Personal",
                "FeePaymentStatus": "Settled",
                "EmergencyLevel": "NoUrgent",
            }
        },

        "repair_environmental_personal_settled_urgent": {
            "description": "卫生个户报修已缴费紧急 - 环卫设施个户报修且已缴费且紧急",
            "possible_paths": [18],  # Repair + EnvironmentalHygiene + Personal + Settled + Urgent
            "required_conditions": {
                "CoreIntention": "Repair",
                "RepairItemCategory": "EnvironmentalHygiene",
                "RelatedScope": "Personal",
                "FeePaymentStatus": "Settled",
                "EmergencyLevel": "Urgent",
            }
        },

        "repair_environmental_personal_settled_normal": {
            "description": "卫生个户报修已缴费非紧急 - 环卫设施个户报修且已缴费且非紧急",
            "possible_paths": [19],  # Repair + EnvironmentalHygiene + Personal + Settled + NoUrgent
            "required_conditions": {
                "CoreIntention": "Repair",
                "RepairItemCategory": "EnvironmentalHygiene",
                "RelatedScope": "Personal",
                "FeePaymentStatus": "Settled",
                "EmergencyLevel": "NoUrgent",
            }
        },

        "repair_indoor_public_urgent": {
            "description": "室内公共紧急报修 - 室内公共设施紧急维修",
            "possible_paths": [20],  # Repair + IndoorFacilities + Public + Urgent
            "required_conditions": {
                "CoreIntention": "Repair",
                "RepairItemCategory": "IndoorFacilities",
                "RelatedScope": "Public",
                "EmergencyLevel": "Urgent",
            }
        },

        "repair_indoor_public_normal": {
            "description": "室内公共普通报修 - 室内公共设施非紧急维修",
            "possible_paths": [21],  # Repair + IndoorFacilities + Public + NoUrgent
            "required_conditions": {
                "CoreIntention": "Repair",
                "RepairItemCategory": "IndoorFacilities",
                "RelatedScope": "Public",
                "EmergencyLevel": "NoUrgent",
            }
        },

        "repair_environmental_public_urgent": {
            "description": "卫生公共紧急报修 - 卫生公共设施紧急维修",
            "possible_paths": [22],  # Repair + EnvironmentalHygiene + Public + Urgent
            "required_conditions": {
                "CoreIntention": "Repair",
                "RepairItemCategory": "EnvironmentalHygiene",
                "RelatedScope": "Public",
                "EmergencyLevel": "Urgent",
            }
        },

        "repair_environmental_public_normal": {
            "description": "卫生公共普通报修 - 卫生公共设施非紧急维修",
            "possible_paths": [23],  # Repair + EnvironmentalHygiene + Public + NoUrgent
            "required_conditions": {
                "CoreIntention": "Repair",
                "RepairItemCategory": "EnvironmentalHygiene",
                "RelatedScope": "Public",
                "EmergencyLevel": "NoUrgent",
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
    from sop_graph import build_property_service_sop_graph

    # 获取SOP图的标准化路径（不含start和end）
    sop_graph = build_property_service_sop_graph()
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
        print(f"  System Variables: {path['system_variables']}")
        print(f"  Expected Path: {' -> '.join(path['expected_path'])}")
        print(f"  Final Output: {path['final_output']}")
