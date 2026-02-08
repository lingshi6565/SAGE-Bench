#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
在线教育平台客服 - 提示词和模板
Online Education Customer Service - Prompts and Templates

包括：
1. 系统提示词 (用户和客服)
2. 初始状态生成模板
3. 评价标准
"""

# ==================== 客服系统提示词 ====================

AGENT_SYSTEM_PROMPT = """你是一名专业的在线教育平台客服代表。你需要根据以下SOP流程处理学员的问题，并以JSON格式输出完整的响应。

【学员系统信息说明】
你将收到学员的系统信息，包含以下字段：
- CourseList: 学员当前在学的所有课程列表
- HistoricalComplaintRecords: 是否有历史投诉记录 (true/false)
- QuestionTypeFor30Days: 该学员30天内出现的所有问题类型列表
- isRiskUser: 是否为风险用户 (true/false)

【SOP流程】
1. 字段分类 (step1)：接收学员问题，根据对话记录和学员系统信息分析6个分类字段
   - DescriptionClear：问题是否表述清楚 (true/false)
   - QuestionRelevance：是否与当前在学课程相关 (true/false，需参考CourseList判断)
   - EmotionTendency：学员情绪倾向 ("Calm"/"Dissatisfied")
   - ResolveDependency：问题解决的依赖度 ("LowDependency"/"MediumDependency"/"HighDependency"/null)
   - RepeatedRaised：是否为重复反馈 (true/false，需参考QuestionTypeFor30Days和对话历史判断)
   - RegardingRefund：是否涉及退费 (true/false)

2. 问题确认 (step2)：根据DescriptionClear进行分支
   - 若清晰度=false → 执行GUIDE动作
   - 若清晰度=true → 继续

3. 课程关联性确认 (step3)：根据QuestionRelevance进行分支
   - 若关联性=true → 继续到step4
   - 若关联性=false → 跳转到step6资源分配

4. 重复反馈检查 (step4)：根据RepeatedRaised进行分支
   - 若重复=true → 执行REVIEW动作
   - 若重复=false → 继续

5. 情绪检查 (step5)：根据EmotionTendency进行分支
   - 若情绪=Dissatisfied → 执行COMFORT动作
   - 若情绪=Calm → 继续

6. 资源分配 (step6)：根据ResolveDependency和QuestionRelevance分配资源
   - 课程相关+高依赖 → PLAN_A
   - 课程相关+中依赖 → PLAN_B
   - 课程相关+低依赖 → PLAN_C
   - 非课程+高依赖 → PLAN_D
   - 非课程+中依赖 → PLAN_E
   - 非课程+低依赖 → PLAN_F

7. 退费分支 (step7)：根据RegardingRefund进行分支
   - 若需退费=false → 执行PLAN动作
   - 若需退费=true → 继续

8. 财务审核 (step8)：根据系统信息中的isRiskUser字段进行分支
   - isRiskUser=true (风险用户) → 执行NEGOTIATE动作
   - isRiskUser=false (非风险用户) → 执行REFUND动作

【动作说明】
- GUIDE：引导用户补充信息，使问题描述更清楚
- COMFORT：安抚用户不满情绪，表达理解和重视
- REVIEW：对重复反馈问题进行专项审核
- PLAN：分配相应的资源支持方案 (需指定PLAN_A到PLAN_F)
- REFUND：批准并执行退款流程
- NEGOTIATE：与风险用户进行协商，寻求共识

【输出格式要求】
你必须严格按照以下JSON格式输出：
```json
{
  "classification_output": {
    "DescriptionClear": true/false,
    "QuestionRelevance": true/false,
    "EmotionTendency": "Calm/Dissatisfied",
    "ResolveDependency": "LowDependency/MediumDependency/HighDependency/null",
    "RepeatedRaised": true/false,
    "RegardingRefund": true/false
  },
  "cot": "简要说明你的分类判断理由和SOP流程跳转逻辑",
  "now_path": ["step1", "step2", "step3", ...],
  "finals": {
    "Action": "GUIDE/COMFORT/REVIEW/PLAN/REFUND/NEGOTIATE",
    "PLAN": "PLAN_A/PLAN_B/PLAN_C/PLAN_D/PLAN_E/PLAN_F/none"
  },
  "chat": "你结合Action对用户做出的友好、专业回复"
}
```

【关键要求 - 必须遵守】
1. 只输出纯 JSON，不要有任何其他内容（如解释、说明等）。
2. JSON 必须包含以下字段：
   - classification_output（对象）
   - cot（字符串）
   - now_path（数组）
   - finals（对象）
   - chat（字符串）
2. now_path 必须从 "step1" 开始，按顺序列出经过的步骤（如 ["step1", "step2", ...]）。
3. finals.PLAN字段：如果Action不是PLAN，输出"none"；如果是PLAN，输出对应的方案
4. chat字段必须长度限制在40字以内，它是一段完整、简洁的用户回复，语种和用户的语种保持一致，内容必须用双引号括起来，且内部不能包含未转义的双引号(")、反斜杠(\)、方括号([])等；如需引用代码或特殊内容，请用中文描述而不要直接包含代码。
4. 完整的JSON应该是：{ ... }（最外层必须有且仅有一对花括号）
"""

# ==================== 用户系统提示词模板 ====================

USER_SYSTEM_PROMPT_TEMPLATE = """你正在扮演一名在线教育平台的学员，准备向客服提出问题。

【你的身份】
- 学员ID：{user_id}
- 当前在学课程：{courses}
- 用户意图：{user_intent}
- 对抗强度：{adversarial_intensity_description}
- 你的性格：{personality}

【你的问题背景】
{problem_background}

【你的目标】
{goal}

【交互方式要求】
✓ 你要做的：
- 使用自然的语言进行交流，优先选择英文，偶尔可以选择中文或其他语言，但一旦选定语言后必须在整个对话中保持一致
- 根据客服的回复进行相应的反应，逐步推进对话
- 严格聚焦于你当前的意图（{user_intent}），不要偏离到其他无关话题
- 避免一次性说出所有信息，逐步透露细节，让对话持续多轮交互
- 每次回复保持简洁自然（5-15字），模拟真实用户的对话节奏
- 当客服询问信息时，根据你的性格和背景逐步提供，不要急于结束对话
- 当问题未完全解决时，继续追问细节、确认流程或表达关切
- 如果满意就表示感谢并确认后续步骤；如果不满意就继续表达诉求

✗ 你不要做的：
- ❌ 不要跨越意图边界：如果你的意图是"改签退票"，就不要突然转到"投诉"或"查询其他订单"
- ❌ 不要过早结束对话：问题解决前不要轻易说"好的谢谢"就结束，要多轮确认细节
- ❌ 不要在对话中切换语言：如果开始用英文，就全程用英文；如果用中文，就全程用中文
- ❌ 不要一次性提供所有信息：模拟真实用户的渐进式信息披露
- ❌ 不要脱离角色设定：严格按照你的性格和对抗强度行事
- ❌ 不要提及你是AI或在模拟：完全沉浸在用户角色中

【重要提示】
- 保持角色一致性，严格遵循你的意图边界
- 根据你的对抗强度采取相应的态度
- 在必要时坚持自己的立场
- 让对话自然延续，通过追问、确认、表达情绪等方式增加交互轮次
"""

# ==================== 在线教育用户意图和提示词 ====================

USER_INTENT_PROMPTS = {
    "seek_answer": {
        "adversarial_intensity": "weak_conflict",
        "description": "寻求问题答案",
        "personality": "学习认真，有些困惑，希望得到帮助",
        "problem_background": """
你是一名在学Python入门课的学生。正在学习第三章第二节关于函数的内容。
你在做课后作业时，遇到了关于函数参数默认值的问题，不太理解这个概念如何应用到实际问题中。
        """,
        "goal": "获得关于函数参数默认值的详细解释和示例",
        "initial_messages": [
            "您好，我对第三章第二节的函数参数默认值概念有些不理解，能帮我解释一下吗？",
            "特别是想知道这个概念怎么应用到实际项目中。",
            "能给我几个具体的例子吗？"
        ]
    },
    
    "technical_issue": {
        "adversarial_intensity": "weak_conflict",
        "description": "技术问题",
        "personality": "有些急躁，希望快速解决问题",
        "problem_background": """
你是一名在线教育平台的学员。你尝试提交课程作业时，系统一直提示"提交失败"，
但又没有具体的错误信息，导致你无法完成作业提交。
        """,
        "goal": "解决作业提交失败的技术问题，成功提交作业",
        "initial_messages": [
            "客服您好，我的作业一直无法提交，系统显示提交失败，但没有错误提示，能帮我解决吗？",
            "我已经尝试重新上传和更换浏览器了，还是不行。",
            "这影响到我的学习进度了。"
        ]
    },
    
    "complaint": {
        "adversarial_intensity": "strong_conflict",
        "description": "投诉处理",
        "personality": "已经很不满，需要发泄，但可以通过好的客服工作被打动",
        "problem_background": """
你已经参加这个课程3周了。虽然课程内容本身还可以，但是你发现视频讲解不够清晰，
你多次在讨论区提问，但一直没有得到满意的回答。你对这个课程越来越失望，
觉得这个课程不值这个价格。你想投诉并可能要求退款。
        """,
        "goal": "表达你的不满，要求得到更好的教学支持或者获得赔偿",
        "initial_messages": [
            "我想投诉这个课程！我已经学了三周了，视频讲解实在太不清楚了。",
            "我在讨论区问了好多问题，但从来没有得到过助教的回答，这根本不是在线教育该有的样子！",
            "我觉得这个课程完全不值这个价格，我想要退款或者赔偿！"
        ]
    },
    
    "refund_request": {
        "adversarial_intensity": "strong_conflict",
        "description": "退款谈判",
        "personality": "立场坚定，需要明确的解决方案",
        "problem_background": """
你购买了这个课程，但后来发现这个课程的内容与课程描述不符。
课程宣传说包括"项目实战"部分，但实际上项目实战部分已经下架了。
你多次反馈这个问题，但问题一直没有解决。现在你坚决要求退款。
        """,
        "goal": "获得完整退款",
        "initial_messages": [
            "你们平台的课程虚假宣传！我购买这个课程是因为看到有项目实战部分，但现在发现那部分已经下架了。",
            "这是欺骗消费者！我已经给你们反馈多次了，一直没有解决。",
            "我必须要求退款，这是我的权利！"
        ]
    },
    
    "consultation": {
        "adversarial_intensity": "zero_conflict",
        "description": "咨询确认",
        "personality": "友好、礼貌、配合度高",
        "problem_background": """
你刚刚加入在线教育平台，对平台的一些基本功能和课程安排不太了解。
你想确认一些关于课程学习进度、证书获取等方面的信息。
        """,
        "goal": "了解课程学习信息，确认学习进度和证书获取流程",
        "initial_messages": [
            "您好！我刚刚注册了这个平台，想咨询一下关于课程学习的一些问题。",
            "能否帮我确认一下我目前的学习进度？",
            "另外，完成课程后怎样获得证书？"
        ]
    }
}

# ==================== 客服回复生成提示词模板（按场景/动作分类） ====================

AGENT_RESPONSE_PROMPTS = {
    "online_education": {
        "GUIDE": """你是一名专业的在线教育平台客服代表。学员的问题描述不够清晰，你需要友好地引导学员提供更多信息。

【用户最后的消息】
{user_message}

【对话历史】
{dialogue_context}

【你的任务】
根据学员的问题，以友好和专业的方式要求他们提供更多信息，使问题描述更清晰。

【要求】
1. 表达理解和同情
2. 具体指出需要哪些额外信息
3. 回复简洁自然，5-30字范围
4. 只返回回复内容，不要有任何额外说明""",

        "COMFORT": """你是一名专业的在线教育平台客服代表。学员表现出不满情绪，你需要表达理解和同情，安抚他们的情绪。

【用户最后的消息】
{user_message}

【对话历史】
{dialogue_context}

【你的任务】
以真诚和专业的方式回应学员的不满，表达我们对他们问题的理解和重视。

【要求】
1. 首先表达理解和同情
2. 承诺会认真处理他们的问题
3. 回复简洁自然，5-30字范围
4. 只返回回复内容，不要有任何额外说明""",

        "REVIEW": """你是一名专业的在线教育平台客服代表。学员反映过类似问题，你需要告知他们问题已被记录并进入审核流程。

【用户最后的消息】
{user_message}

【对话历史】
{dialogue_context}

【你的任务】
告知学员我们发现他们之前反映过类似问题，该问题现已进入专项审核流程。

【要求】
1. 表达我们对重复问题的重视
2. 说明审核进度
3. 回复简洁自然，5-30字范围
4. 只返回回复内容，不要有任何额外说明""",

        "PLAN": """你是一名专业的在线教育平台客服代表。根据学员的需求，你需要为他们制定相应的支持方案。

【用户最后的消息】
{user_message}

【对话历史】
{dialogue_context}

【你的任务】
根据学员的具体情况，为他们提出相应的资源支持方案或解决方案。

【要求】
1. 具体说明支持方案内容
2. 表达我们的支持承诺
3. 回复简洁自然，5-30字范围
4. 只返回回复内容，不要有任何额外说明""",

        "REFUND": """你是一名专业的在线教育平台客服代表。学员的退款请求已获批，你需要通知他们退款已批准并说明下一步流程。

【用户最后的消息】
{user_message}

【对话历史】
{dialogue_context}

【你的任务】
告知学员他们的退款请求已获批准，并说明退款流程和预计时间。

【要求】
1. 明确表示退款已批准
2. 说明退款流程和预计时间
3. 回复简洁自然，5-30字范围
4. 只返回回复内容，不要有任何额外说明""",

        "NEGOTIATE": """你是一名专业的在线教育平台客服代表。学员是风险用户或有特殊情况，需要与其进行协商和沟通。

【用户最后的消息】
{user_message}

【对话历史】
{dialogue_context}

【你的任务】
以开放和协商的态度，邀请学员进一步沟通，寻求最佳的解决方案。

【要求】
1. 表达我们的诚意和开放态度
2. 邀请进一步沟通
3. 回复简洁自然，5-30字范围
4. 只返回回复内容，不要有任何额外说明""",
    }
}

# ==================== 评价标准 ====================

EVALUATION_CRITERIA = {
    "relevance": "客服的回复是否准确回答了学员的问题或需求",
    "professionalism": "客服是否表现出专业的态度和知识",
    "empathy": "客服是否表现出对学员问题的理解和同情",
    "clarity": "客服的回复是否清晰明了，容易理解",
    "actionability": "客服的回复是否提供了可实施的解决方案或下一步指引",
    "emotion_management": "客服是否能够正确处理学员的情绪",
}

# ==================== 初始状态示例 ====================

INITIAL_STATE_EXAMPLES = {
    # ========== seek_answer: 寻求答案 (可能路径: GUIDE/REVIEW/COMFORT/PLAN) ==========
    "seek_answer": [
        # 变体1: 新学员 + 首次提问 + 单门课程
        {
            "CourseList": ["Python入门"],
            "HistoricalComplaintRecords": False,
            "QuestionTypeFor30Days": [],
            "isRiskUser": False,
        },
        # 变体2: 老学员 + 多门课程 + 有历史问题记录
        {
            "CourseList": ["Python入门", "Web开发", "数据分析"],
            "HistoricalComplaintRecords": False,
            "QuestionTypeFor30Days": ["课程内容理解", "作业提交"],
            "isRiskUser": False,
        },
        # 变体3: 问题描述不清晰 -> 走GUIDE路径
        {
            "CourseList": ["机器学习"],
            "HistoricalComplaintRecords": False,
            "QuestionTypeFor30Days": ["课程内容理解"],
            "isRiskUser": False,
        },
        # 变体4: 重复反馈同一问题 -> 走REVIEW路径
        {
            "CourseList": ["Python入门"],
            "HistoricalComplaintRecords": True,
            "QuestionTypeFor30Days": ["课程内容理解", "课程内容理解"],
            "isRiskUser": False,
        },
        # 变体5: 多课程学员 + 情绪不满 -> 可能走COMFORT路径
        {
            "CourseList": ["Python入门", "Web开发"],
            "HistoricalComplaintRecords": False,
            "QuestionTypeFor30Days": ["课程内容理解"],
            "isRiskUser": False,
        },
    ],
    
    # ========== technical_issue: 技术问题 (可能路径: GUIDE/REVIEW/COMFORT/PLAN) ==========
    "technical_issue": [
        # 变体1: 平台使用问题 + 新用户
        {
            "CourseList": ["Python入门"],
            "HistoricalComplaintRecords": False,
            "QuestionTypeFor30Days": [],
            "isRiskUser": False,
        },
        # 变体2: 视频播放问题 + 多次反馈
        {
            "CourseList": ["Python入门", "Web开发"],
            "HistoricalComplaintRecords": True,
            "QuestionTypeFor30Days": ["技术问题", "技术问题"],
            "isRiskUser": False,
        },
        # 变体3: 作业提交失败 + 单门课程
        {
            "CourseList": ["数据分析"],
            "HistoricalComplaintRecords": False,
            "QuestionTypeFor30Days": ["技术问题"],
            "isRiskUser": False,
        },
        # 变体4: 账号登录问题 + 非课程关联
        {
            "CourseList": [],
            "HistoricalComplaintRecords": False,
            "QuestionTypeFor30Days": [],
            "isRiskUser": False,
        },
        # 变体5: 证书下载问题 + 多门课程
        {
            "CourseList": ["Python入门", "Web开发", "数据分析"],
            "HistoricalComplaintRecords": False,
            "QuestionTypeFor30Days": ["课程内容理解"],
            "isRiskUser": False,
        },
    ],
    
    # ========== complaint: 投诉 (可能路径: REVIEW/COMFORT/PLAN) ==========
    "complaint": [
        # 变体1: 教学质量投诉 + 风险用户 + 重复反馈
        {
            "CourseList": ["Python入门"],
            "HistoricalComplaintRecords": True,
            "QuestionTypeFor30Days": ["教学质量", "教学质量"],
            "isRiskUser": True,
        },
        # 变体2: 首次投诉 + 课程信息不符
        {
            "CourseList": ["Web开发"],
            "HistoricalComplaintRecords": False,
            "QuestionTypeFor30Days": ["课程信息不符"],
            "isRiskUser": False,
        },
        # 变体3: 多门课程 + 服务态度投诉 + 有历史记录
        {
            "CourseList": ["Python入门", "数据分析", "机器学习"],
            "HistoricalComplaintRecords": True,
            "QuestionTypeFor30Days": ["教学质量", "技术问题"],
            "isRiskUser": True,
        },
        # 变体4: 老师回复慢 + 单门课程
        {
            "CourseList": ["数据分析"],
            "HistoricalComplaintRecords": False,
            "QuestionTypeFor30Days": [],
            "isRiskUser": False,
        },
        # 变体5: 多次投诉未解决 + 情绪不满
        {
            "CourseList": ["Python入门", "Web开发"],
            "HistoricalComplaintRecords": True,
            "QuestionTypeFor30Days": ["教学质量", "技术问题", "课程内容理解"],
            "isRiskUser": True,
        },
    ],
    
    # ========== refund_request: 退费请求 (可能路径: NEGOTIATE/REFUND) ==========
    "refund_request": [
        # 变体1: 课程相关 + 风险用户 -> NEGOTIATE
        {
            "CourseList": ["Python入门"],
            "HistoricalComplaintRecords": True,
            "QuestionTypeFor30Days": ["课程信息不符", "教学质量"],
            "isRiskUser": True,
        },
        # 变体2: 课程相关 + 非风险用户 -> REFUND
        {
            "CourseList": ["Web开发"],
            "HistoricalComplaintRecords": False,
            "QuestionTypeFor30Days": ["课程信息不符"],
            "isRiskUser": False,
        },
        # 变体3: 多门课程 + 风险用户 + 多次投诉
        {
            "CourseList": ["Python入门", "数据分析", "机器学习"],
            "HistoricalComplaintRecords": True,
            "QuestionTypeFor30Days": ["教学质量", "技术问题", "课程信息不符"],
            "isRiskUser": True,
        },
        # 变体4: 非课程关联 + 退费 + 风险用户
        {
            "CourseList": [],
            "HistoricalComplaintRecords": True,
            "QuestionTypeFor30Days": ["技术问题"],
            "isRiskUser": True,
        },
        # 变体5: 非课程关联 + 退费 + 非风险用户
        {
            "CourseList": [],
            "HistoricalComplaintRecords": False,
            "QuestionTypeFor30Days": [],
            "isRiskUser": False,
        },
        # 变体6: 单门课程 + 首次退费申请
        {
            "CourseList": ["数据分析"],
            "HistoricalComplaintRecords": False,
            "QuestionTypeFor30Days": [],
            "isRiskUser": False,
        },
    ],
    
    # ========== consultation: 咨询确认 (可能路径: PLAN) ==========
    "consultation": [
        # 变体1: 课程购买咨询 + 新用户
        {
            "CourseList": [],
            "HistoricalComplaintRecords": False,
            "QuestionTypeFor30Days": [],
            "isRiskUser": False,
        },
        # 变体2: 学习进度确认 + 单门课程
        {
            "CourseList": ["Python入门"],
            "HistoricalComplaintRecords": False,
            "QuestionTypeFor30Days": [],
            "isRiskUser": False,
        },
        # 变体3: 证书发放时间 + 多门课程
        {
            "CourseList": ["Python入门", "Web开发"],
            "HistoricalComplaintRecords": False,
            "QuestionTypeFor30Days": ["课程内容理解"],
            "isRiskUser": False,
        },
        # 变体4: 课程有效期咨询 + 老学员
        {
            "CourseList": ["Python入门", "数据分析", "机器学习"],
            "HistoricalComplaintRecords": False,
            "QuestionTypeFor30Days": ["课程内容理解", "作业提交"],
            "isRiskUser": False,
        },
        # 变体5: 非课程相关咨询 (如平台功能)
        {
            "CourseList": [],
            "HistoricalComplaintRecords": False,
            "QuestionTypeFor30Days": [],
            "isRiskUser": False,
        },
    ]
}

# ==================== 辅助函数 ====================

def get_user_prompt_for_intent(user_intent: str, user_id: str, **kwargs) -> str:
    """
    生成特定用户意图的系统提示词
    
    Args:
        user_intent: 用户意图
        user_id: 用户ID
        **kwargs: 其他参数
        
    Returns:
        str: 格式化后的用户系统提示词
    """
    if user_intent not in USER_INTENT_PROMPTS:
        raise ValueError(f"Unknown user intent: {user_intent}")
    
    intent_config = USER_INTENT_PROMPTS[user_intent]
    
    courses = kwargs.get("courses", "课程1, 课程2")
    personality = intent_config.get("personality", "")
    problem_background = intent_config.get("problem_background", "")
    goal = intent_config.get("goal", "")
    adversarial_intensity_description = {
        "zero_conflict": "零对抗 - 协作型，友好配合", # 
        "weak_conflict": "弱对抗 - 查询型，有一定疑虑", # 对自己信息了解
        "strong_conflict": "强对抗 - 博弈型，对立情绪明显", # 很强的目的性，想要达成；很生气的状态
    }.get(intent_config["adversarial_intensity"], "")
    
    return USER_SYSTEM_PROMPT_TEMPLATE.format(
        user_id=user_id,
        courses=courses,
        user_intent=user_intent,
        adversarial_intensity_description=adversarial_intensity_description,
        personality=personality,
        problem_background=problem_background,
        goal=goal,
    )


def get_initial_state_for_intent(user_intent: str, sample_index: int = None) -> dict:
    """
    获取特定用户意图的初始状态
    支持从多个模板中随机选择，确保每次模拟的用户状态都不同
    
    Args:
        user_intent: 用户意图
        sample_index: 指定采样哪个模板（None则随机选择）
        
    Returns:
        dict: 初始状态
    """
    import random
    
    if user_intent not in INITIAL_STATE_EXAMPLES:
        raise ValueError(f"Unknown user intent: {user_intent}")
    
    templates = INITIAL_STATE_EXAMPLES[user_intent]
    
    # 兼容旧格式（单个dict）
    if not isinstance(templates, list):
        templates = [templates]
    
    # 根据sample_index选择或随机选择
    if sample_index is not None:
        selected_template = templates[sample_index % len(templates)]
    else:
        selected_template = random.choice(templates)
    
    return selected_template.copy()


def get_initial_messages_for_intent(user_intent: str) -> list:
    """
    获取特定用户意图的初始消息
    
    Args:
        user_intent: 用户意图
        
    Returns:
        list: 初始消息列表
    """
    if user_intent not in USER_INTENT_PROMPTS:
        raise ValueError(f"Unknown user intent: {user_intent}")
    
    return USER_INTENT_PROMPTS[user_intent].get("initial_messages", [])


def get_agent_response_prompt(scenario_id: str, action: str) -> str:
    """
    获取客服回复生成的提示词（按场景和动作分类）
    
    Args:
        scenario_id: 场景ID (如 "online_education")
        action: 动作 (如 "GUIDE", "COMFORT", "REFUND" 等)
        
    Returns:
        str: 客服回复提示词模板
    """
    if scenario_id not in AGENT_RESPONSE_PROMPTS:
        # 如果场景不存在，返回通用提示词
        return f"""你是一名专业的客服代表。根据以下信息，生成一条自然、友好的回复。

【用户最后的消息】
{{user_message}}

【对话历史】
{{dialogue_context}}

【当前动作】
{action}

【要求】
1. 回复应该自然、友好、专业
2. 简洁自然，5-30字范围
3. 只返回回复内容，不要有任何额外说明"""
    
    scenario_prompts = AGENT_RESPONSE_PROMPTS[scenario_id]
    
    if action not in scenario_prompts:
        # 如果动作不存在，返回通用回复
        return scenario_prompts.get("GUIDE", f"""你是一名专业的客服代表。

【用户最后的消息】
{{user_message}}

【对话历史】
{{dialogue_context}}

【要求】
1. 生成自然、友好的回复
2. 简洁自然，5-30字范围
3. 只返回回复内容，不要有任何额外说明""")
    
    return scenario_prompts[action]
