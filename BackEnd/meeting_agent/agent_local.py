import json
import re
from datetime import datetime
from pathlib import Path

# ==========================================
# 1. 路径配置
# ==========================================
SCRIPT_DIR = Path(__file__).resolve().parent
INPUT_FOLDER = SCRIPT_DIR / "Input"
OUTPUT_FOLDER = SCRIPT_DIR / "Output"


def normalize_date(date_text):
    """将日期统一为 YYYY-MM-DD。"""
    if not date_text:
        return "待定"

    match = re.search(r"(20\d{2})\D+(\d{1,2})\D+(\d{1,2})", date_text)
    if not match:
        return "待定"

    year, month, day = match.groups()
    return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"


def dedupe_list(items):
    """保留顺序去重。"""
    seen = set()
    result = []
    for item in items:
        if not item:
            continue
        key = json.dumps(item, ensure_ascii=False, sort_keys=True) if isinstance(item, (dict, list)) else str(item)
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def split_sentences(text_content):
    """把纪要粗略拆成句子。"""
    parts = re.split(r"[。\n]", text_content)
    return [part.strip(" ：:；;，,") for part in parts if part.strip(" ：:；;，,")]


def split_participants(participants_line):
    """将参会人员拆解成结构化人员列表。"""
    people = []
    for chunk in re.split(r"[，,、；;]", participants_line):
        item = chunk.strip()
        if not item:
            continue

        role = "参会人员"
        organization = "待定"
        name = item

        if item.startswith("客户经理"):
            role = "客户经理"
            organization = "我方"
            name = item.replace("客户经理", "", 1).strip() or item
        elif item.startswith("客户方"):
            role = "客户方"
            organization = "客户方"
            name = item.replace("客户方", "", 1).strip() or item
        elif item.startswith("客户"):
            role = "客户方"
            organization = "客户方"
            name = item.replace("客户", "", 1).strip() or item
        elif "工程师" in item:
            role = "技术对接"
            organization = "客户方"
            name = item.split("工程师", 1)[-1].strip() or item
        elif "处长" in item or "主任" in item or "园长" in item:
            role = "客户负责人"
            organization = "客户方"

        people.append(
            {
                "role": role,
                "name": name,
                "organization": organization,
                "display": f"{name}（{role}）" if name != item else item,
            }
        )

    return people


def extract_source_metadata(text_content, source_file):
    """提取题头里的会议元信息。"""
    topic_match = re.search(r"会议主题[:：]\s*(.+)", text_content)
    time_match = re.search(r"时间[:：]\s*(.+)", text_content)
    participants_match = re.search(r"参会人员[:：]\s*(.+)", text_content)

    topic = topic_match.group(1).strip() if topic_match else source_file.stem
    request_date = normalize_date(time_match.group(1).strip()) if time_match else "待定"
    participants = split_participants(participants_match.group(1).strip()) if participants_match else []

    project_name = re.sub(r"\s*沟通会\s*$", "", topic).strip()
    customer = "待定"
    if "图书馆" in project_name:
        customer = project_name.split("图书馆", 1)[0].strip() or "待定"
    elif "5G" in project_name:
        customer = project_name.split("5G", 1)[0].strip() or "待定"

    owner = next((item["name"] for item in participants if item["role"] == "客户经理"), "待定")
    participant_names = [item["display"] for item in participants]

    year = request_date[:4] if request_date != "待定" else str(datetime.now().year)
    project_id = f"RR-RIS-{year}-{source_file.stem.upper().replace(' ', '-')}"

    return {
        "project_id": project_id,
        "project_name": project_name or source_file.stem,
        "customer": customer,
        "request_date": request_date,
        "owner": owner,
        "participants": participant_names,
        "stakeholders": [
            {
                "role": item["role"],
                "name": item["name"],
                "organization": item["organization"],
            }
            for item in participants
        ],
        "meeting_topic": topic,
    }


def build_default_record(source_file, text_content):
    """构造标准 JSON 骨架。"""
    meta = extract_source_metadata(text_content, source_file)
    change_date = meta["request_date"] if meta["request_date"] != "待定" else datetime.now().strftime("%Y-%m-%d")
    scene_type = "室内图书馆" if "图书馆" in text_content else "室内场景"

    return {
        "project_info": {
            "id": meta["project_id"],
            "name": meta["project_name"],
            "customer": meta["customer"],
            "meeting_topic": meta["meeting_topic"],
            "request_date": meta["request_date"],
            "source": "会议纪要",
            "stage": "需求澄清 / 方案设计",
            "owner": meta["owner"],
            "participants": meta["participants"],
            "confidentiality": "内部",
            "priority": "P1",
            "version": "V1.0",
            "stakeholders": meta["stakeholders"],
            "change_log": [
                {
                    "version": "V1.0",
                    "date": change_date,
                    "author": "Agent(Local)",
                    "description": "本地规则生成初始需求稿",
                    "status": "草案",
                }
            ],
        },
        "business": {
            "scenario": scene_type,
            "motivation": "待定",
            "goals": [],
            "target_users": [],
            "value": [],
        },
        "scene": {
            "location": meta["customer"],
            "type": scene_type,
            "area": "待定",
            "ceiling_height": "待定",
            "materials": [],
            "target_zones": [],
            "existing_network": "待定",
            "transport_conditions": "待定",
            "power_supply": "待定",
            "constraints": [],
            "survey_status": "待初勘",
            "attachments": [],
        },
        "requirements": {
            "summary": "待补充",
            "functional": [],
            "kpi": [],
            "interfaces": [],
            "acceptance": [],
            "timeline": "待定",
            "next_steps": [],
        },
        "risks": [],
        "notes": [f"源文件: {source_file.name}"],
    }


def extract_key_sentences(text_content, keywords):
    """提取命中关键词的句子。"""
    return [
        sentence
        for sentence in split_sentences(text_content)
        if any(keyword in sentence for keyword in keywords)
    ]


def extract_target_zones(text_content):
    """提取重点区域。"""
    zones = []
    stop_keywords = ("信号", "电话", "投诉", "盲区", "弱覆盖", "几乎", "目前")

    for match in re.findall(r"特别是([^。；\n]+)", text_content):
        for chunk in re.split(r"[和、，,]", match):
            zone = chunk.strip().lstrip("在")
            if any(keyword in zone for keyword in stop_keywords):
                continue
            if zone:
                zones.append(zone)

    explicit_zones = [
        "三楼的阅览室",
        "地下负一层的密集书库",
        "密集书架区域",
        "靠窗的休息区",
        "靠窗休息区",
    ]
    for zone in explicit_zones:
        if zone in text_content:
            zones.append(zone)

    return dedupe_list(zones)


def extract_next_steps(text_content, default_owner):
    """从纪要里抽取下一步计划。"""
    steps = []
    section = ""

    if "下一步计划" in text_content:
        section = text_content.split("下一步计划", 1)[1]

    candidate_sentences = split_sentences(section or text_content)
    for sentence in candidate_sentences:
        if "负责" not in sentence and "提供" not in sentence:
            continue

        owner = default_owner
        due = "待定"
        notes = ""
        task = sentence

        owner_match = re.search(r"(?P<owner>[^，,；;\s]+)负责", sentence)
        if owner_match:
            owner = owner_match.group("owner")

        due_match = re.search(r"(在)?(?P<due>下周[^，,；;。]*前)", sentence)
        if not due_match:
            due_match = re.search(r"(?P<due>\d{4}[-年]\d{1,2}[-月]\d{1,2}日?前)", sentence)
        if due_match:
            due = due_match.group("due")

        task = re.sub(r"^[^，,；;\s]+负责", "", task).strip("：:，, ")
        task = re.sub(r"^(在)?下周[^，,；;。]*前", "", task).strip("：:，, ")

        if "包含" in task:
            task, _, extra = task.partition("包含")
            notes = f"包含{extra.strip()}"

        task = task.rstrip("，,；; ")

        if task:
            steps.append(
                {
                    "owner": owner,
                    "task": task,
                    "due": due,
                    "notes": notes,
                }
            )

    if not steps and section:
        due_match = re.search(r"(下周[^，,；;。]*前)", section)
        due = due_match.group(1) if due_match else "待定"
        task = re.sub(r"[:：]", "", section).strip()
        if task:
            steps.append(
                {
                    "owner": default_owner,
                    "task": task,
                    "due": due,
                    "notes": "",
                }
            )

    return dedupe_list(steps)


def build_mock_record(text_content, source_file):
    """用本地规则生成标准 JSON。"""
    record = build_default_record(source_file, text_content)
    sentences = split_sentences(text_content)
    project_name = record["project_info"]["name"]
    customer = record["project_info"]["customer"]
    default_owner = record["project_info"]["owner"]

    pain_points = extract_key_sentences(text_content, ("信号", "盲区", "死角", "投诉", "屏蔽", "弱覆盖"))
    constraints = []
    if "美观" in text_content or "明线" in text_content or "传统天线" in text_content:
        constraints.append("设备安装需美观隐形，避免明线和传统大天线外露")
    if "噪音" in text_content:
        constraints.append("施工过程需严格控制噪音")
    if "粉尘" in text_content:
        constraints.append("施工过程需严格控制粉尘")
    if "电磁兼容" in text_content or "检测报告" in text_content:
        constraints.append("需提供电磁兼容说明或相关检测资料")

    materials = []
    if "金属书架" in text_content:
        materials.append("金属书架")
    if "老楼" in text_content:
        materials.append("老楼建筑结构")
    if "天花板" in text_content:
        materials.append("室内吊顶")

    goals = [
        "消除重点区域信号盲区和弱覆盖",
        "在现有预算约束下完成 RIS 深度覆盖方案设计",
    ]
    if "电磁兼容" in text_content:
        goals.append("满足医院环境下的电磁兼容性要求")

    values = []
    if "投诉" in text_content:
        values.append("降低弱覆盖导致的用户投诉")
    if "美观" in text_content or "环境整洁" in text_content:
        values.append("兼顾覆盖效果与现场环境美观度")
    if "预算" in text_content or "专项基金" in text_content:
        values.append("在预算和审批约束内优化整体投入")

    target_users = []
    if "学生" in text_content:
        target_users.append("学生与校内管理人员")
    if "医护人员" in text_content:
        target_users.append("医护人员与进修学习人员")
    if not target_users:
        target_users.append("现场用户")

    functional = [
        {
            "id": "FR-001",
            "title": "重点区域弱覆盖治理",
            "description": "针对图书馆重点区域的弱覆盖和盲区进行 RIS 定向覆盖增强，保障基础语音与数据业务可用。",
            "priority": "P1",
        }
    ]
    if constraints:
        functional.append(
            {
                "id": "FR-002",
                "title": "现场约束适配安装",
                "description": "方案需适配现场的美观、布线和施工限制，减少对既有环境的影响。",
                "priority": "P1",
            }
        )
    if "电磁兼容" in text_content or "检测报告" in text_content:
        functional.append(
            {
                "id": "FR-003",
                "title": "电磁兼容资料交付",
                "description": "提供设备在特殊场景中的电磁兼容性说明或检测资料，支撑客户技术评估。",
                "priority": "P1",
            }
        )

    kpi = [
        {"metric": "重点区域覆盖效果", "target": "显著改善盲区和弱覆盖，满足基本语音与数据业务使用"},
        {"metric": "方案可落地性", "target": "满足预算、安装和施工约束"},
    ]

    interfaces = []
    if "平面图" in text_content:
        interfaces.append({"name": "平面图资料", "details": "客户提供图书馆平面图，用于点位仿真与部署设计"})
    if "检测报告" in text_content or "电磁兼容" in text_content:
        interfaces.append({"name": "电磁兼容资料", "details": "输出检测报告或兼容性说明，用于客户内部评估"})

    acceptance = [
        "重点区域覆盖问题得到明显改善",
        "方案满足现场安装约束并通过客户评审",
    ]
    if "电磁兼容" in text_content:
        acceptance.append("完成电磁兼容性说明或相关资料交付")

    next_steps = extract_next_steps(text_content, default_owner)
    timeline = next_steps[0]["due"] if next_steps else "待定"

    risks = []
    if "预算" in text_content or "专项基金" in text_content:
        risks.append("预算审批和成本控制可能影响方案选型和推进节奏")
    if "电磁兼容" in text_content:
        risks.append("电磁兼容评估结果可能影响设备部署方案")
    if "噪音" in text_content or "粉尘" in text_content:
        risks.append("现场施工窗口受环境要求限制，需要提前协调")

    notes = []
    for sentence in sentences:
        if "RIS" in sentence or "感兴趣" in sentence or "表示认可" in sentence:
            notes.append(sentence)

    record["business"]["scenario"] = f"{customer}图书馆深度覆盖场景" if customer != "待定" else record["business"]["scenario"]
    record["business"]["motivation"] = "；".join(pain_points) if pain_points else "现网存在明显弱覆盖问题"
    record["business"]["goals"] = dedupe_list(goals)
    record["business"]["target_users"] = dedupe_list(target_users)
    record["business"]["value"] = dedupe_list(values)

    record["scene"]["location"] = customer if customer != "待定" else project_name
    record["scene"]["type"] = "室内图书馆"
    record["scene"]["materials"] = dedupe_list(materials)
    record["scene"]["target_zones"] = extract_target_zones(text_content)
    record["scene"]["existing_network"] = "现网存在弱覆盖/盲区，重点区域语音与数据业务体验差"
    record["scene"]["constraints"] = dedupe_list(constraints)
    record["scene"]["attachments"] = [item["name"] for item in interfaces]

    record["requirements"]["summary"] = pain_points[0] if pain_points else "客户希望通过 RIS 方案解决重点区域覆盖问题"
    record["requirements"]["functional"] = functional
    record["requirements"]["kpi"] = kpi
    record["requirements"]["interfaces"] = interfaces
    record["requirements"]["acceptance"] = dedupe_list(acceptance)
    record["requirements"]["timeline"] = timeline
    record["requirements"]["next_steps"] = next_steps

    record["risks"] = dedupe_list(risks)
    record["notes"] = dedupe_list(record["notes"] + notes)
    return record


def process_single_meeting(input_file_path):
    """读取 -> 本地规则抽取 -> 保存标准 JSON。"""
    print(f"INFO: 正在读取文件: {input_file_path} ...")

    if not input_file_path.exists():
        print(f"ERROR: 找不到文件 {input_file_path}")
        return

    with input_file_path.open("r", encoding="utf-8") as file_obj:
        text_data = file_obj.read()

    print("INFO: 正在使用本地规则生成标准 JSON...")
    json_output = build_mock_record(text_data, input_file_path)

    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    output_file_path = OUTPUT_FOLDER / f"draft_{input_file_path.stem}.json"

    with output_file_path.open("w", encoding="utf-8") as file_obj:
        json.dump(json_output, file_obj, ensure_ascii=False, indent=4)

    print(f"INFO: 成功！草稿已保存至: {output_file_path}")
    print("-" * 30)


    return output_file_path

if __name__ == "__main__":
    print("--- RIS 需求理解 Agent (本地多文件测试版) 启动 ---")

    INPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    input_files = sorted(INPUT_FOLDER.glob("*.txt"))

    if not input_files:
        print(f"WARN: {INPUT_FOLDER} 中没有找到输入文件。")
    else:
        for file_path in input_files:
            process_single_meeting(file_path)

    print("INFO: 所有会议记录处理完毕。")
