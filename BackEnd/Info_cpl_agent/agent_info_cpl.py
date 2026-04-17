import json
import os
import time
from datetime import datetime
from pathlib import Path

from openai import OpenAI

# ================= 配置区域 =================
# 请填入你的 DeepSeek API Key
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
MODEL_NAME = "deepseek-chat"

AGENT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = AGENT_DIR.parent
MEETING_OUTPUT_DIR = BACKEND_DIR / "meeting_agent" / "Output"
TEMPLATE_PATH = AGENT_DIR / "template.tex"
AGENT_OUTPUT_DIR = AGENT_DIR / "Output"
AGENT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)

SCHEMA_REFERENCE = """
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

SYSTEM_PROMPT = (
    r"""你是一个专业的 LaTeX 需求文档生成助手。你的任务是接收一个包含“注释型占位符”的 LaTeX 模板和一份 JSON 格式的数据源，生成一份格式规范、内容准确的需求记录表。

### 核心规则
1. **保持结构**：严禁修改 LaTeX 的表格结构（如列宽 `p{...}`、表头 `\textbf{}`、分页符 `\endhead` 等）。
2. **注释处理**：模板中所有的 `% FILL_ME: ...` 都是你的操作指令。一旦你填入了内容，必须删除该行注释。
3. **数据匹配**：优先按照标准 JSON 路径提取数据；如果信息缺失，请填入“待定”或“暂无数据”，不要编造事实。
4. **内容保守**：可以做轻微归纳和重述，但不能添加会议纪要里没有依据的具体指标、数值或结论。

### 填充策略
1. 单元格占位：用最匹配的字段直接替换 `% FILL_ME`。
2. 列表型占位：根据数组数据生成多行内容，每行必须以 `\\ \hline` 结尾。
3. 混合型表格：保留固定文本，只替换占位内容。
4. 日期字段：如果需要“当前日期”，使用用户消息里给出的当前日期。
5. 输出内容只能是完整的 LaTeX 代码，不要额外解释。

### 数据源结构参考 (JSON Schema)
"""
    + SCHEMA_REFERENCE
)


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


def merge_with_defaults(default_value, actual_value):
    """递归合并标准 schema 的默认值。"""
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


def build_default_record(source_name):
    """为 LaTeX 生成环节准备兜底 schema。"""
    today = datetime.now().strftime("%Y-%m-%d")
    year = today[:4]
    stem = Path(source_name).stem.upper().replace(" ", "-")

    return {
        "project_info": {
            "id": f"RR-RIS-{year}-{stem}",
            "name": Path(source_name).stem,
            "customer": "待定",
            "meeting_topic": Path(source_name).stem,
            "request_date": today,
            "source": "会议纪要",
            "stage": "需求澄清 / 方案设计",
            "owner": "待定",
            "participants": [],
            "confidentiality": "内部",
            "priority": "P1",
            "version": "V1.0",
            "stakeholders": [],
            "change_log": [
                {
                    "version": "V1.0",
                    "date": today,
                    "author": "Agent",
                    "description": "初始需求生成",
                    "status": "草案",
                }
            ],
        },
        "business": {
            "scenario": "待定",
            "motivation": "待定",
            "goals": [],
            "target_users": [],
            "value": [],
        },
        "scene": {
            "location": "待定",
            "type": "待定",
            "area": "待定",
            "ceiling_height": "待定",
            "materials": [],
            "target_zones": [],
            "existing_network": "待定",
            "transport_conditions": "待定",
            "power_supply": "待定",
            "constraints": [],
            "survey_status": "待定",
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
        "notes": [f"源文件: {source_name}"],
    }


def normalize_legacy_flat_record(raw_data):
    """兼容早期 meeting_agent 输出的扁平中文 JSON。"""
    customer_needs = raw_data.get("客户需求", {})
    need_items = []
    notes = []

    if isinstance(customer_needs, dict):
        for index, (title, description) in enumerate(customer_needs.items(), start=1):
            if description:
                need_items.append(
                    {
                        "id": f"FR-{index:03d}",
                        "title": title,
                        "description": description,
                        "priority": "P1",
                    }
                )
        if customer_needs.get("技术兴趣"):
            notes.append(f"客户对 {customer_needs['技术兴趣']} 感兴趣")
        if customer_needs.get("关注点"):
            notes.append(f"客户关注点：{customer_needs['关注点']}")

    stakeholders = []
    if raw_data.get("客户联系人"):
        stakeholders.append({"role": "客户负责人", "name": raw_data["客户联系人"], "organization": "客户方"})
    if raw_data.get("我方联系人"):
        stakeholders.append({"role": "客户经理", "name": raw_data["我方联系人"], "organization": "我方"})

    return {
        "project_info": {
            "name": raw_data.get("项目名称", "待定"),
            "customer": raw_data.get("客户名称", "待定"),
            "request_date": raw_data.get("会议时间", "待定"),
            "source": "客户会议纪要",
            "stage": "需求澄清 / 方案设计",
            "owner": raw_data.get("我方联系人", "待定"),
            "participants": dedupe_list(
                [raw_data.get("客户联系人"), raw_data.get("我方联系人")]
            ),
            "stakeholders": stakeholders,
        },
        "business": {
            "scenario": raw_data.get("项目名称", "待定"),
            "motivation": raw_data.get("核心问题", "待定"),
            "goals": dedupe_list(
                [customer_needs.get("覆盖目标"), customer_needs.get("预算范围"), customer_needs.get("美观要求")]
            ),
            "target_users": [],
            "value": [],
        },
        "scene": {
            "location": raw_data.get("客户名称", "待定"),
            "type": "室内图书馆" if "图书馆" in raw_data.get("项目名称", "") else "待定",
            "constraints": dedupe_list(
                [customer_needs.get("美观要求"), customer_needs.get("关注点")]
            ),
            "target_zones": [],
            "attachments": [],
        },
        "requirements": {
            "summary": raw_data.get("核心问题", "待补充"),
            "functional": need_items,
            "timeline": raw_data.get("下一步计划", "待定"),
            "next_steps": [
                {
                    "owner": raw_data.get("我方联系人", "待定"),
                    "task": raw_data.get("下一步计划", "待定"),
                    "due": "待定",
                    "notes": "",
                }
            ]
            if raw_data.get("下一步计划")
            else [],
        },
        "notes": notes,
    }


def normalize_legacy_mock_record(raw_data):
    """兼容旧版本地 mock 输出。"""
    basic_info = raw_data.get("项目基本信息", {})
    core_needs = raw_data.get("客户核心需求", {})
    need_items = []

    if core_needs.get("覆盖痛点"):
        need_items.append(
            {
                "id": "FR-001",
                "title": "重点区域覆盖优化",
                "description": core_needs["覆盖痛点"],
                "priority": "P1",
            }
        )
    if core_needs.get("特殊要求"):
        need_items.append(
            {
                "id": "FR-002",
                "title": "安装与环境约束",
                "description": core_needs["特殊要求"],
                "priority": "P1",
            }
        )

    return {
        "project_info": {
            "name": Path(str(basic_info.get("原始文件来源", "项目"))).stem,
            "source": basic_info.get("原始文件来源", "会议纪要"),
        },
        "business": {
            "scenario": basic_info.get("场景类型", "待定"),
            "goals": dedupe_list([core_needs.get("覆盖痛点"), core_needs.get("预算范围")]),
        },
        "scene": {
            "type": basic_info.get("场景类型", "待定"),
            "constraints": dedupe_list([core_needs.get("特殊要求")]),
        },
        "requirements": {
            "summary": core_needs.get("覆盖痛点", "待补充"),
            "functional": need_items,
            "timeline": raw_data.get("下一步计划", "待定"),
        },
    }


def normalize_input_record(raw_data, source_name):
    """把输入 JSON 统一收敛到标准 schema。"""
    defaults = build_default_record(source_name)

    if not isinstance(raw_data, dict):
        return defaults

    if "project_info" in raw_data:
        normalized = merge_with_defaults(defaults, raw_data)
    elif "项目名称" in raw_data or "客户需求" in raw_data:
        normalized = merge_with_defaults(defaults, normalize_legacy_flat_record(raw_data))
    elif "项目基本信息" in raw_data or "客户核心需求" in raw_data:
        normalized = merge_with_defaults(defaults, normalize_legacy_mock_record(raw_data))
    else:
        normalized = defaults

    normalized["project_info"]["participants"] = dedupe_list(normalized["project_info"].get("participants", []))
    normalized["project_info"]["stakeholders"] = dedupe_list(normalized["project_info"].get("stakeholders", []))
    normalized["business"]["goals"] = dedupe_list(normalized["business"].get("goals", []))
    normalized["business"]["target_users"] = dedupe_list(normalized["business"].get("target_users", []))
    normalized["business"]["value"] = dedupe_list(normalized["business"].get("value", []))
    normalized["scene"]["materials"] = dedupe_list(normalized["scene"].get("materials", []))
    normalized["scene"]["target_zones"] = dedupe_list(normalized["scene"].get("target_zones", []))
    normalized["scene"]["constraints"] = dedupe_list(normalized["scene"].get("constraints", []))
    normalized["scene"]["attachments"] = dedupe_list(normalized["scene"].get("attachments", []))
    normalized["requirements"]["acceptance"] = dedupe_list(normalized["requirements"].get("acceptance", []))
    normalized["risks"] = dedupe_list(normalized.get("risks", []))
    normalized["notes"] = dedupe_list(normalized.get("notes", []))
    return normalized


def extract_payload_block(raw_content, block_type):
    """从模型返回中提取 JSON 或 LaTeX 主体。"""
    cleaned = raw_content.strip()
    cleaned = cleaned.replace(f"```{block_type}", "").replace("```", "").strip()

    if block_type == "json":
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            return cleaned[start : end + 1]

    return cleaned


def load_json_file(filepath):
    """读取 JSON 文件。"""
    with filepath.open("r", encoding="utf-8") as file_obj:
        return json.load(file_obj)


def load_template(filepath):
    """读取 LaTeX 模板。"""
    with filepath.open("r", encoding="utf-8") as file_obj:
        return file_obj.read()


def save_latex_file(content, filename):
    """保存生成的 LaTeX 文件。"""
    filepath = AGENT_OUTPUT_DIR / filename
    with filepath.open("w", encoding="utf-8") as file_obj:
        file_obj.write(content)
    print(f"INFO: 成功生成: {filepath}")


    return filepath


def escape_latex(value):
    text = "待定" if value in (None, "") else str(value)
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    return text


def join_values(values):
    if not values:
        return "待定"
    return "、".join(escape_latex(item) for item in values if item)


def build_enumerate(items):
    if not items:
        return "\\begin{itemize}\n\\item 暂无数据\n\\end{itemize}"
    return "\\begin{itemize}\n" + "\n".join(f"\\item {escape_latex(item)}" for item in items) + "\n\\end{itemize}"


def build_function_rows(functional_items):
    if not functional_items:
        return "\\item 暂无功能需求"

    rows = []
    for item in functional_items:
        rows.append(
            "\\item "
            + escape_latex(item.get("id", "FR-000"))
            + " "
            + escape_latex(item.get("title", "未命名需求"))
            + "（"
            + escape_latex(item.get("priority", "P1"))
            + "）"
            + "\n\n"
            + escape_latex(item.get("description", "暂无说明"))
        )
    return "\n".join(rows)


def build_object_rows(items, *, title_key, detail_key):
    if not items:
        return "\\item 暂无数据"

    rows = []
    for item in items:
        title = escape_latex(item.get(title_key, "未命名"))
        detail = escape_latex(item.get(detail_key, "暂无说明"))
        rows.append(f"\\item {title}: {detail}")
    return "\n".join(rows)


def build_next_step_rows(items):
    if not items:
        return "\\item 暂无后续动作"

    rows = []
    for item in items:
        rows.append(
            "\\item "
            + escape_latex(item.get("task", "待确认"))
            + "；负责人："
            + escape_latex(item.get("owner", "待定"))
            + "；截止："
            + escape_latex(item.get("due", "待定"))
            + ("；备注：" + escape_latex(item.get("notes")) if item.get("notes") else "")
        )
    return "\n".join(rows)


def generate_local_latex(final_data, original_filename):
    project_info = final_data.get("project_info", {})
    business = final_data.get("business", {})
    scene = final_data.get("scene", {})
    requirements = final_data.get("requirements", {})
    risks = final_data.get("risks", [])
    notes = final_data.get("notes", [])
    stakeholders = project_info.get("stakeholders", [])

    stakeholder_rows = []
    for stakeholder in stakeholders:
        stakeholder_rows.append(
            "\\item "
            + escape_latex(stakeholder.get("role", "角色"))
            + "："
            + escape_latex(stakeholder.get("name", "待定"))
            + "（"
            + escape_latex(stakeholder.get("organization", "待定"))
            + "）"
        )
    stakeholder_block = "\n".join(stakeholder_rows) if stakeholder_rows else "\\item 暂无干系人信息"

    latex_content = f"""\\documentclass[12pt,a4paper]{{ctexart}}
\\usepackage[a4paper,margin=1.8cm]{{geometry}}
\\usepackage{{hyperref}}
\\usepackage{{enumitem}}
\\setlength{{\\parindent}}{{0pt}}
\\setlength{{\\parskip}}{{6pt}}

\\begin{{document}}

\\begin{{center}}
{{\\LARGE \\textbf{{DeliveraX RIS 需求文档草稿}}}}\\\\[0.5em]
{{\\large 本地模式生成，可直接用于前后端联调验证}}\\\\[0.8em]
\\end{{center}}

\\section*{{基础信息}}
\\begin{{itemize}}[leftmargin=2em]
\\item 文档编号：{escape_latex(project_info.get("id", original_filename))}
\\item 项目名称：{escape_latex(project_info.get("name", original_filename))}
\\item 客户名称：{escape_latex(project_info.get("customer", "待定"))}
\\item 会议主题：{escape_latex(project_info.get("meeting_topic", original_filename))}
\\item 当前阶段：{escape_latex(project_info.get("stage", "需求澄清 / 方案设计"))}
\\item 责任人：{escape_latex(project_info.get("owner", "待定"))}
\\item 参与人员：{join_values(project_info.get("participants", []))}
\\end{{itemize}}

\\section*{{业务背景}}
\\begin{{itemize}}[leftmargin=2em]
\\item 业务场景：{escape_latex(business.get("scenario", "待定"))}
\\item 建设动因：{escape_latex(business.get("motivation", "待定"))}
\\item 建设目标：
{build_enumerate(business.get("goals", []))}
\\item 目标用户：
{build_enumerate(business.get("target_users", []))}
\\item 业务价值：
{build_enumerate(business.get("value", []))}
\\end{{itemize}}

\\section*{{场景信息}}
\\begin{{itemize}}[leftmargin=2em]
\\item 建设地点：{escape_latex(scene.get("location", "待定"))}
\\item 场景类型：{escape_latex(scene.get("type", "待定"))}
\\item 覆盖面积：{escape_latex(scene.get("area", "待定"))}
\\item 层高：{escape_latex(scene.get("ceiling_height", "待定"))}
\\item 主要材质：{join_values(scene.get("materials", []))}
\\item 重点区域：{join_values(scene.get("target_zones", []))}
\\item 现网情况：{escape_latex(scene.get("existing_network", "待定"))}
\\item 供电条件：{escape_latex(scene.get("power_supply", "待定"))}
\\item 安装约束：
{build_enumerate(scene.get("constraints", []))}
\\item 相关附件：{join_values(scene.get("attachments", []))}
\\end{{itemize}}

\\section*{{干系人与职责}}
\\begin{{itemize}}[leftmargin=2em]
{stakeholder_block}
\\end{{itemize}}

\\section*{{需求摘要}}
{escape_latex(requirements.get("summary", "待补充"))}

\\section*{{功能需求}}
\\begin{{itemize}}[leftmargin=2em]
{build_function_rows(requirements.get("functional", []))}
\\end{{itemize}}

\\section*{{KPI 与接口}}
\\subsection*{{KPI}}
\\begin{{itemize}}[leftmargin=2em]
{build_object_rows(requirements.get("kpi", []), title_key="metric", detail_key="target")}
\\end{{itemize}}

\\subsection*{{接口 / 输入资料}}
\\begin{{itemize}}[leftmargin=2em]
{build_object_rows(requirements.get("interfaces", []), title_key="name", detail_key="details")}
\\end{{itemize}}

\\section*{{验收与计划}}
\\begin{{itemize}}[leftmargin=2em]
\\item 时间计划：{escape_latex(requirements.get("timeline", "待定"))}
\\item 验收要求：
{build_enumerate(requirements.get("acceptance", []))}
\\item 下一步动作：
\\begin{{itemize}}[leftmargin=2em]
{build_next_step_rows(requirements.get("next_steps", []))}
\\end{{itemize}}
\\end{{itemize}}

\\section*{{风险与备注}}
\\subsection*{{风险}}
{build_enumerate(risks)}

\\subsection*{{备注}}
{build_enumerate(notes)}

\\end{{document}}
"""

    output_filename = f"RIS_{original_filename}.tex"
    return save_latex_file(latex_content, output_filename)


def call_deepseek(messages):
    """调用 DeepSeek 模型。"""
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.1,
        )
        return response.choices[0].message.content
    except Exception as exc:
        print(f"ERROR: 调用 DeepSeek 失败: {exc}")
        return None


def step_1_enhance_data(raw_data):
    """
    第一步：在不改变 schema 的前提下，保守补全缺失字段。
    """
    print("INFO: 正在调用 DeepSeek 进行数据推理补全...")

    prompt = f"""
你会收到一份符合标准 schema 的需求 JSON。请在不新增顶层字段、不改变字段名的前提下做保守补全。

要求：
1. 只补全根据现有上下文可以合理推断的字段。
2. 如果缺少依据，就保留原值或填“待定”。
3. 输出必须仍然是标准 JSON，不能包含 Markdown 代码块。
4. 不要凭空添加具体数值、面积、KPI 阈值、电话号码等事实。

标准 schema:
{SCHEMA_REFERENCE}
"""

    messages = [
        {"role": "system", "content": "你是一个数据清洗和结构化补全专家。"},
        {"role": "user", "content": f"{prompt}\n\n原始数据:\n{json.dumps(raw_data, ensure_ascii=False, indent=2)}"},
    ]

    result = call_deepseek(messages)
    if result:
        try:
            cleaned = extract_payload_block(result, "json")
            return json.loads(cleaned)
        except json.JSONDecodeError:
            print("WARN: 数据补全阶段 JSON 解析失败，将使用原始数据。")
            return raw_data
    return raw_data


def step_2_generate_latex(template_content, final_data, original_filename):
    """
    第二步：使用标准 schema 数据生成 LaTeX。
    """
    print("INFO: 正在生成 LaTeX 文档...")

    user_prompt = f"""
请根据以下标准 JSON 数据源填充 LaTeX 模板。

### JSON 数据源
{json.dumps(final_data, ensure_ascii=False, indent=2)}

### LaTeX 模板
{template_content}

### 指令
1. 严格按照 system prompt 的规则填充。
2. 当前日期是 {datetime.now().strftime("%Y-%m-%d")}。
3. 输出结果只能是完整的 LaTeX 代码，不要包含任何解释性文字。
"""

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    latex_code = call_deepseek(messages)
    if not latex_code:
        print("ERROR: LaTeX 生成失败。")
        return

    cleaned_latex = extract_payload_block(latex_code, "latex")
    output_filename = f"RIS_{original_filename}.tex"
    save_latex_file(cleaned_latex, output_filename)

    if "FILL_ME" in cleaned_latex:
        print("WARN: 生成结果中仍包含 FILL_ME 占位符，请检查模型返回内容。")


    return AGENT_OUTPUT_DIR / output_filename


def process_single_json_file(json_file, mode="api"):
    json_path = Path(json_file)
    if not json_path.exists():
        print(f"ERROR: Missing JSON file: {json_path}")
        return None

    raw_data = load_json_file(json_path)
    normalized_data = normalize_input_record(raw_data, json_path.name)

    if mode == "local":
        return generate_local_latex(normalized_data, json_path.stem)

    if not TEMPLATE_PATH.exists():
        print(f"ERROR: Missing LaTeX template: {TEMPLATE_PATH}")
        return None

    if not DEEPSEEK_API_KEY:
        raise ValueError("DEEPSEEK_API_KEY is required when running Info CPL Agent in api mode.")

    template_content = load_template(TEMPLATE_PATH)
    enhanced_data = step_1_enhance_data(normalized_data)
    final_data = normalize_input_record(enhanced_data, json_path.name)
    return step_2_generate_latex(template_content, final_data, json_path.stem)


def main():
    if not MEETING_OUTPUT_DIR.exists():
        print(f"ERROR: 未找到 meeting_agent 输出目录: {MEETING_OUTPUT_DIR}")
        return

    json_files = sorted(MEETING_OUTPUT_DIR.glob("*.json"))
    if not json_files:
        print(f"ERROR: 在 {MEETING_OUTPUT_DIR} 中未找到 JSON 文件")
        return

    print(f"INFO: 发现 {len(json_files)} 个 JSON 文件，开始处理...")

    if not TEMPLATE_PATH.exists():
        print(f"ERROR: 未找到模板文件: {TEMPLATE_PATH}")
        return

    template_content = load_template(TEMPLATE_PATH)

    for json_file in json_files:
        print(f"\n--- 正在处理: {json_file.name} ---")
        raw_data = load_json_file(json_file)
        normalized_data = normalize_input_record(raw_data, json_file.name)
        enhanced_data = step_1_enhance_data(normalized_data)
        final_data = normalize_input_record(enhanced_data, json_file.name)
        step_2_generate_latex(template_content, final_data, json_file.stem)
        time.sleep(1)


if __name__ == "__main__":
    main()
