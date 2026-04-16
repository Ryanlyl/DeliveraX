import json
import re
from datetime import datetime
from pathlib import Path

import requests

# ==========================================
# 1. 配置区域
# ==========================================
# 🔴 请务必在这里填入你的 DeepSeek API Key
API_KEY = "sk-691f42c6b4c84a5dae3b12dcaf015a58"

API_URL = "https://api.deepseek.com/chat/completions"
SCRIPT_DIR = Path(__file__).resolve().parent
INPUT_FOLDER = SCRIPT_DIR / "Input"
OUTPUT_FOLDER = SCRIPT_DIR / "Output"

EXTRACTION_SYSTEM_PROMPT = """
你是一个专业的售前需求分析专家。请从会议纪要中提取关键信息，并严格输出一个 JSON 对象。

输出时必须遵守以下要求：
1. 只输出 JSON，不要附带 Markdown 代码块或解释文字。
2. 顶层字段必须固定为：project_info、business、scene、requirements、risks、notes。
3. 若信息缺失，用 "待定"、空数组 [] 或空对象 {} 表示，不要编造事实。
4. requirements.functional 中每一项必须包含 id、title、description、priority。
5. project_info.change_log 中每一项必须包含 version、date、author、description、status。
6. project_info.stakeholders 中每一项尽量包含 role、name、organization。

JSON Schema 参考：
{
  "project_info": {
    "id": "RR-RIS-2026-001",
    "name": "项目名称",
    "customer": "客户名称",
    "meeting_topic": "会议主题",
    "request_date": "YYYY-MM-DD",
    "source": "会议纪要",
    "stage": "需求澄清 / 方案设计",
    "owner": "责任人",
    "participants": ["参与人A", "参与人B"],
    "confidentiality": "内部",
    "priority": "P1",
    "version": "V1.0",
    "stakeholders": [
      {"role": "客户负责人", "name": "张三", "organization": "客户方"}
    ],
    "change_log": [
      {
        "version": "V1.0",
        "date": "2026-04-16",
        "author": "Agent",
        "description": "初始需求生成",
        "status": "草案"
      }
    ]
  },
  "business": {
    "scenario": "业务场景概述",
    "motivation": "建设动因",
    "goals": ["目标1", "目标2"],
    "target_users": ["目标用户"],
    "value": ["业务价值"]
  },
  "scene": {
    "location": "建设地点",
    "type": "场景类型",
    "area": "覆盖面积",
    "ceiling_height": "层高",
    "materials": ["主要材质"],
    "target_zones": ["重点区域"],
    "existing_network": "现网站点情况",
    "transport_conditions": "传输条件",
    "power_supply": "供电条件",
    "constraints": ["安装约束"],
    "survey_status": "勘查状态",
    "attachments": ["相关附件"]
  },
  "requirements": {
    "summary": "需求摘要",
    "functional": [
      {
        "id": "FR-001",
        "title": "功能需求标题",
        "description": "功能需求说明",
        "priority": "P1"
      }
    ],
    "kpi": [
      {"metric": "指标项", "target": "目标值"}
    ],
    "interfaces": [
      {"name": "接口或资料", "details": "说明"}
    ],
    "acceptance": ["验收要求"],
    "timeline": "期望上线时间或里程碑",
    "next_steps": [
      {
        "owner": "责任人",
        "task": "下一步任务",
        "due": "截止时间",
        "notes": "补充说明"
      }
    ]
  },
  "risks": ["风险点"],
  "notes": ["补充说明"]
}
""".strip()


def normalize_date(date_text):
    """将会议纪要中的日期统一为 YYYY-MM-DD。"""
    if not date_text:
        return "待定"

    match = re.search(r"(20\d{2})\D+(\d{1,2})\D+(\d{1,2})", date_text)
    if not match:
        return "待定"

    year, month, day = match.groups()
    return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"


def extract_json_block(raw_content):
    """尽量从模型返回内容中截出 JSON 主体。"""
    cleaned = raw_content.strip()
    cleaned = cleaned.replace("```json", "").replace("```", "").strip()

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        return cleaned[start : end + 1]

    return cleaned


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


def split_participants(participants_line):
    """将参会人员文本拆成结构化人员列表。"""
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
        elif "处长" in item or "主任" in item:
            role = "客户负责人"
            organization = "客户方"
        elif "园长" in item:
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
    """从会议纪要里提取能稳定得到的元信息。"""
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
    """构造标准 JSON 的兜底骨架。"""
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
                    "author": "Agent",
                    "description": "初始需求生成",
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


def merge_with_defaults(default_value, actual_value):
    """用模型输出覆盖默认值，但保留兜底结构。"""
    if isinstance(default_value, dict):
        actual_value = actual_value if isinstance(actual_value, dict) else {}
        merged = {key: merge_with_defaults(value, actual_value.get(key)) for key, value in default_value.items()}
        for key, value in actual_value.items():
            if key not in merged:
                merged[key] = value
        return merged

    if isinstance(default_value, list):
        return actual_value if isinstance(actual_value, list) and actual_value else default_value

    if actual_value in (None, "", {}):
        return default_value

    return actual_value


def normalize_record(record, source_file, text_content):
    """确保最终输出与标准 schema 对齐。"""
    defaults = build_default_record(source_file, text_content)
    if not isinstance(record, dict):
        return defaults

    normalized = merge_with_defaults(defaults, record)
    normalized["project_info"]["participants"] = dedupe_list(normalized["project_info"].get("participants", []))
    normalized["project_info"]["stakeholders"] = dedupe_list(normalized["project_info"].get("stakeholders", []))
    normalized["scene"]["materials"] = dedupe_list(normalized["scene"].get("materials", []))
    normalized["scene"]["target_zones"] = dedupe_list(normalized["scene"].get("target_zones", []))
    normalized["scene"]["constraints"] = dedupe_list(normalized["scene"].get("constraints", []))
    normalized["scene"]["attachments"] = dedupe_list(normalized["scene"].get("attachments", []))
    normalized["business"]["goals"] = dedupe_list(normalized["business"].get("goals", []))
    normalized["business"]["target_users"] = dedupe_list(normalized["business"].get("target_users", []))
    normalized["business"]["value"] = dedupe_list(normalized["business"].get("value", []))
    normalized["requirements"]["acceptance"] = dedupe_list(normalized["requirements"].get("acceptance", []))
    normalized["risks"] = dedupe_list(normalized.get("risks", []))
    normalized["notes"] = dedupe_list(normalized.get("notes", []))
    return normalized


def extract_requirements_with_ai(text_content, source_file):
    """
    调用 DeepSeek API 分析文本并提取标准化 RIS 需求 JSON。
    """
    if not API_KEY or "这里填入你的密钥" in API_KEY:
        print("ERROR: 请在代码中配置有效的 DeepSeek API Key！")
        return None

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }

    messages = [
        {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"请分析以下会议纪要，并按约定 schema 输出结构化 JSON。\n"
                f"源文件名：{source_file.name}\n\n{text_content}"
            ),
        },
    ]

    payload = {
        "model": "deepseek-chat",
        "messages": messages,
        "temperature": 0.2,
    }

    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)

        if response.status_code != 200:
            print(f"ERROR: API 请求失败！状态码: {response.status_code}")
            print(f"DETAIL: {response.text}")
            return None

        result = response.json()
        content = result["choices"][0]["message"]["content"]
        cleaned = extract_json_block(content)
        parsed = json.loads(cleaned)
        return normalize_record(parsed, source_file, text_content)

    except json.JSONDecodeError as exc:
        print(f"ERROR: JSON 解析失败: {exc}")
        return normalize_record({}, source_file, text_content)
    except Exception as exc:
        print(f"ERROR: 程序异常: {exc}")
        return {
            "error": "程序异常",
            "details": str(exc),
            "source_file": source_file.name,
        }


def process_single_file(input_path):
    """处理单个会议纪要文件。"""
    output_filename = f"draft_{input_path.stem}.json"
    output_path = OUTPUT_FOLDER / output_filename

    print(f"INFO: 正在处理：{input_path.name} ...")

    with input_path.open("r", encoding="utf-8") as file_obj:
        content = file_obj.read()

    result_json = extract_requirements_with_ai(content, input_path)

    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file_obj:
        json.dump(result_json, file_obj, ensure_ascii=False, indent=4)

    print(f"INFO: 成功生成：{output_filename}")
    print("-" * 30)


if __name__ == "__main__":
    print("--- RIS 需求理解 Agent (API 真实版) 启动 ---")

    INPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    files = sorted(INPUT_FOLDER.glob("*.txt"))

    if not files:
        print(f"WARN: {INPUT_FOLDER} 中没有找到 txt 文件！")
    else:
        for file_path in files:
            process_single_file(file_path)

    print("INFO: 所有任务处理完毕！")
