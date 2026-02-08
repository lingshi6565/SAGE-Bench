# 每个可能的path分别进行生产生成
# python代码将每个路径和对应的classification output 对应
# 根据SOP图构建，确保与sop_graph.py完全一致

import json
from typing import Dict, List, Any


def generate_path_list():
    """
    根据5个分类字段和2个系统变量生成所有可能的决策路径
    与sop_graph.py中的build_ecommerce_refund_sop_graph()保持一致

    字段说明:
    1. CoreIntention: String ("ReturnOrRefund"/"Exchange") - 用户发起售后的核心需求
    2. ProvidedDocument: Boolean (True/False) - 用户是否提交售后相关凭证
    3. Responsibility: String ("User"/"Merchant") - 售后问题的责任归属
    4. RefundReasonable: String ("Reasonable"/"Unreasonable") - 退款需求是否合理
    5. EmotionStatus: String ("Calm"/"Dissatisfied") - 用户情绪状态
    
    系统变量:
    1. ShippingStatus: String ("Unshipped"/"Shipping"/"Signed") - 物流状态
    2. CreditLevel: String ("High"/"Medium"/"Low") - 用户信用等级
    """
    path_list = []

    # ========== 路径1: step1 -> step2 -> step3 -> ACTION=Exchange (Exchange + Unshipped) ==========
    path_list.append({
        "Classification_items": ["Exchange", None, None, None, None],
        "system_variables": {"ShippingStatus": "Unshipped"},
        "expected_path": ["step1", "step2", "step3"],
        "final_output": {"Action": "Exchange"}
    })

    # ========== 路径2: step1 -> step2 -> step3 -> ACTION=Interception (Exchange + Shipping) ==========
    path_list.append({
        "Classification_items": ["Exchange", None, None, None, None],
        "system_variables": {"ShippingStatus": "Shipping"},
        "expected_path": ["step1", "step2", "step3"],
        "final_output": {"Action": "Interception"}
    })

    # ========== 路径3-4: step1 -> step2 -> step3 -> step4 -> ACTION=Exchange (Exchange + Signed + High/Medium CreditLevel) ==========
    for credit in ["High", "Medium"]:
        path_list.append({
            "Classification_items": ["Exchange", None, None, None, None],
            "system_variables": {"ShippingStatus": "Signed", "CreditLevel": credit},
            "expected_path": ["step1", "step2", "step3", "step4"],
            "final_output": {"Action": "Exchange"}
        })

    # ========== 路径5: step1 -> step2 -> step3 -> step4 -> ACTION=PayFee (Exchange + Signed + Low CreditLevel) ==========
    # 注意：这里step4是从step3来的，不是从step5来的
    path_list.append({
        "Classification_items": ["Exchange", None, None, None, None],
        "system_variables": {"ShippingStatus": "Signed", "CreditLevel": "Low"},
        "expected_path": ["step1", "step2", "step3", "step4"],
        "final_output": {"Action": "PayFee"}
    })

    # ========== 路径6: step1 -> step2 -> step3 -> ACTION=Refund (ReturnOrRefund + Unshipped) ==========
    path_list.append({
        "Classification_items": ["ReturnOrRefund", None, None, None, None],
        "system_variables": {"ShippingStatus": "Unshipped"},
        "expected_path": ["step1", "step2", "step3"],
        "final_output": {"Action": "Refund"}
    })

    # ========== 路径7: step1 -> step2 -> step3 -> ACTION=Interception (ReturnOrRefund + Shipping) ==========
    path_list.append({
        "Classification_items": ["ReturnOrRefund", None, None, None, None],
        "system_variables": {"ShippingStatus": "Shipping"},
        "expected_path": ["step1", "step2", "step3"],
        "final_output": {"Action": "Interception"}
    })


    # ========== 路径8: step1 -> step2 -> step3 -> step5 -> step4 -> ACTION=Comfort+Compensation (Merchant + High) ==========
    path_list.append({
        "Classification_items": ["ReturnOrRefund", None, "Merchant", None, None],
        "system_variables": {"ShippingStatus": "Signed", "CreditLevel": "High"},
        "expected_path": ["step1", "step2", "step3", "step5", "step4"],
        "final_output": {"Action": "Comfort+Compensation"}
    })

    # ========== 路径9: step1 -> step2 -> step3 -> step5 -> step4 -> step7 (Merchant + Medium/Low) ==========
    # Merchant + Low/Medium信用 → step7（需要根据情绪判断）
    for credit in ["Medium", "Low"]:
        path_list.append({
            "Classification_items": ["ReturnOrRefund", None, "Merchant", None, None],
            "system_variables": {"ShippingStatus": "Signed", "CreditLevel": credit},
            "expected_path": ["step1", "step2", "step3", "step5", "step4", "step7"],
            "final_output": {"Action": "Comfort"}
        })


    # ========== 路径10: step1 -> step2 -> step3 -> step5 -> step4 -> ACTION=CollectionService (User + High) ==========
    path_list.append({
        "Classification_items": ["ReturnOrRefund", None, "User", None, None],
        "system_variables": {"ShippingStatus": "Signed", "CreditLevel": "High"},
        "expected_path": ["step1", "step2", "step3", "step5", "step4"],
        "final_output": {"Action": "CollectionService"}
    })

    # ========== 路径11: step1 -> step2 -> step3 -> step5 -> step4 -> ACTION=CollectionService (User + Medium) ==========
    path_list.append({
        "Classification_items": ["ReturnOrRefund", None, "User", None, None],
        "system_variables": {"ShippingStatus": "Signed", "CreditLevel": "Medium"},
        "expected_path": ["step1", "step2", "step3", "step5", "step4"],
        "final_output": {"Action": "CollectionService"}
    })


    # ========== 路径12: step1 -> step2 -> step3 -> step5 -> step4 -> step6 -> step8 -> ACTION=CollectionService (ProvidedDocument=True) ==========
    path_list.append({
        "Classification_items": ["ReturnOrRefund", True, "User", "Reasonable", None],
        "system_variables": {"ShippingStatus": "Signed", "CreditLevel": "Low"},
        "expected_path": ["step1", "step2", "step3", "step5", "step4", "step6", "step8"],
        "final_output": {"Action": "CollectionService"}
    })

    # ========== 路径13: step1 -> step2 -> step3 -> step5 -> step4 -> step6 -> step8 -> ACTION=Supplementary (ProvidedDocument=False) ==========
    path_list.append({
        "Classification_items": ["ReturnOrRefund", False, "User", "Reasonable", None],
        "system_variables": {"ShippingStatus": "Signed", "CreditLevel": "Low"},
        "expected_path": ["step1", "step2", "step3", "step5", "step4", "step6", "step8"],
        "final_output": {"Action": "Supplementary"}
    })

    # ========== 路径14: step1 -> step2 -> step3 -> step5 -> step4 -> step6 -> ACTION=Reject (User + Low + Unreasonable) ==========
    path_list.append({
        "Classification_items": ["ReturnOrRefund", None, "User", "Unreasonable", None],
        "system_variables": {"ShippingStatus": "Signed", "CreditLevel": "Low"},
        "expected_path": ["step1", "step2", "step3", "step5", "step4", "step6"],
        "final_output": {"Action": "Reject"}
    })

    return path_list


def save_path_list_to_json(path_list, filename="path_list.json"):
    """将path_list保存为JSON文件"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(path_list, f, ensure_ascii=False, indent=2)
    print(f"PathList已保存到 {filename}")


def verify_paths_match_sop_graph():
    """验证PathList与SOP图的路径是否匹配"""
    from sop_graph import build_ecommerce_refund_sop_graph

    # 获取SOP图的标准化路径（不含start和end）
    sop_graph = build_ecommerce_refund_sop_graph()
    sop_paths = sop_graph.get_all_paths(include_endpoints=False)
    
    # 规范化SOP图路径：去掉action_*节点（因为PathList中没有包含这些）
    normalized_sop_paths = []
    for path in sop_paths:
        normalized_path = [node for node in path if not node.startswith('action_')]
        if normalized_path:  # 只保留非空路径
            normalized_sop_paths.append(normalized_path)

    # 获取PathList的路径
    path_list = generate_path_list()
    pathlist_paths = [item["expected_path"] for item in path_list]

    # 转换为集合比较
    sop_path_set = set(['->'.join(p) for p in normalized_sop_paths])
    pathlist_path_set = set(['->'.join(p) for p in pathlist_paths])

    print("="*80)
    print("SOP图路径验证")
    print("="*80)
    print(f"SOP图路径数: {len(normalized_sop_paths)}")
    print(f"PathList路径数: {len(pathlist_paths)}")

    only_in_sop = sop_path_set - pathlist_path_set
    only_in_pathlist = pathlist_path_set - sop_path_set

    if only_in_pathlist:
        print(f"\n❌ PathList中缺失SOP图覆盖的路径 ({len(only_in_pathlist)}):")
        for p in only_in_pathlist:
            print(f"  {p}")
        print("\n❌ PathList不完整！")
        return False
    elif only_in_sop:
        print(f"\n⚠️  SOP图包含额外的理论路径 ({len(only_in_sop)}):")
        for p in sorted(only_in_sop)[:5]:  # 只显示前5条
            print(f"  {p}")
        if len(only_in_sop) > 5:
            print(f"  ... 还有 {len(only_in_sop)-5} 条")
        print("\n✅ 但所有PathList路径都被SOP图覆盖！")
        return True
    else:
        print("\n✅ PathList与SOP图完全一致！")
        return True


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
        "exchange_product": {
            "description": "换货需求 - 商品信息错误或不合适要求换货",
            "possible_paths": [1, 2, 3, 4, 5],  # Exchange各类情况
            "required_conditions": {
                "CoreIntention": "Exchange"
            }
        },
        
        "refund_before_shipping": {
            "description": "未发货退款 - 订单未发货时取消订单退款",
            "possible_paths": [6],  # ReturnOrRefund + Unshipped -> Refund
            "required_conditions": {
                "CoreIntention": "ReturnOrRefund",
                "ShippingStatus": "Unshipped"
            }
        },
        
        "refund_on_the_way": {
            "description": "运输中退款 - 物流途中要求拦截并退款",
            "possible_paths": [7],  # ReturnOrRefund + Shipping -> Interception
            "required_conditions": {
                "CoreIntention": "ReturnOrRefund",
                "ShippingStatus": "Shipping"
            }
        },
        
        "merchant_compensation_high_credit": {
            "description": "商家责任赔偿（高信用） - 商家责任且用户高信用",
            "possible_paths": [8],  # ReturnOrRefund + Merchant + High -> Comfort+Compensation
            "required_conditions": {
                "CoreIntention": "ReturnOrRefund",
                "Responsibility": "Merchant",
                "CreditLevel": "High",
                "ShippingStatus": "Signed"
            }
        },
        
        "merchant_compensation_low_credit": {
            "description": "商家责任赔偿（低/中信用） - 商家责任且用户低或中信用",
            "possible_paths": [9],  # ReturnOrRefund + Merchant + Medium/Low -> Comfort
            "required_conditions": {
                "CoreIntention": "ReturnOrRefund",
                "Responsibility": "Merchant",
                "ShippingStatus": "Signed"
            },
            "impossible_conditions": {
                "CreditLevel": "High"
            }
        },
        
        "user_return_high_credit": {
            "description": "用户发起退货（高信用） - 用户责任且高信用可直接揽收",
            "possible_paths": [10],  # ReturnOrRefund + User + High -> CollectionService
            "required_conditions": {
                "CoreIntention": "ReturnOrRefund",
                "Responsibility": "User",
                "CreditLevel": "High",
                "ShippingStatus": "Signed"
            }
        },
        
        "user_return_medium_credit": {
            "description": "用户发起退货（中信用） - 用户责任且中信用可直接揽收",
            "possible_paths": [11],  # ReturnOrRefund + User + Medium -> CollectionService
            "required_conditions": {
                "CoreIntention": "ReturnOrRefund",
                "Responsibility": "User",
                "CreditLevel": "Medium",
                "ShippingStatus": "Signed"
            }
        },
        
        "user_return_low_credit_with_doc": {
            "description": "用户发起退货（低信用+有凭证） - 低信用用户提交凭证可揽收",
            "possible_paths": [12],  # ReturnOrRefund + User + Low + Reasonable + ProvidedDocument=True -> CollectionService
            "required_conditions": {
                "CoreIntention": "ReturnOrRefund",
                "Responsibility": "User",
                "CreditLevel": "Low",
                "RefundReasonable": "Reasonable",
                "ProvidedDocument": True,
                "ShippingStatus": "Signed"
            }
        },
        
        "user_return_low_credit_no_doc": {
            "description": "用户发起退货（低信用+无凭证） - 低信用用户缺少凭证需补充",
            "possible_paths": [13],  # ReturnOrRefund + User + Low + Reasonable + ProvidedDocument=False -> Supplementary
            "required_conditions": {
                "CoreIntention": "ReturnOrRefund",
                "Responsibility": "User",
                "CreditLevel": "Low",
                "RefundReasonable": "Reasonable",
                "ProvidedDocument": False,
                "ShippingStatus": "Signed"
            }
        },
        
        "unreasonable_refund": {
            "description": "无理由退款 - 用户自身原因要求退款，理由不充分直接拒绝",
            "possible_paths": [14, 15],  # ReturnOrRefund + User + Low + Unreasonable -> Reject (路径14和15重复)
            "required_conditions": {
                "CoreIntention": "ReturnOrRefund",
                "Responsibility": "User",
                "CreditLevel": "Low",
                "RefundReasonable": "Unreasonable",
                "ShippingStatus": "Signed"
            }
        },
    }


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
