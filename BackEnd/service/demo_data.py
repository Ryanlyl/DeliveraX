from __future__ import annotations

STAGES = [
    {
        "id": "requirements-analysis",
        "name": "需求分析",
        "description": "上传会议纪要并生成结构化需求草稿。",
    },
    {
        "id": "solution-design",
        "name": "方案设计",
        "description": "基于结构化需求生成方案设计文档草稿。",
    },
    {
        "id": "implementation",
        "name": "研发实现",
        "description": "进入研发联调与接口落地阶段。",
    },
    {
        "id": "testing-review",
        "name": "测试评审",
        "description": "沉淀测试材料、报告和评审结论。",
    },
    {
        "id": "delivery-launch",
        "name": "交付上线",
        "description": "准备交付包、上线材料与归档产物。",
    },
]

STAGE_INDEX = {stage["id"]: stage for stage in STAGES}

PROJECTS = [
    {
        "id": "ris-garage-signal",
        "name": "RIS 地下车库信号增强原型",
        "industry": "通信硬件",
        "status": "进行中",
        "progress": 2,
        "current_stage_id": "solution-design",
        "summary": "围绕地下停车场 RIS 部署场景，持续推进需求、方案和交付材料。",
        "owner": "交付团队 A",
        "tags": ["RIS", "通信设备", "Demo"],
    },
    {
        "id": "edge-gateway-delivery",
        "name": "边缘网关批量交付流程",
        "industry": "工业互联网",
        "status": "进行中",
        "progress": 3,
        "current_stage_id": "implementation",
        "summary": "串联需求、方案、测试和交付文档，逐步接入真实 Agent 流程。",
        "owner": "平台团队",
        "tags": ["通用平台", "Agent Flow"],
    },
    {
        "id": "smart-campus-rollout",
        "name": "智慧园区设备上线项目",
        "industry": "园区网络",
        "status": "已完成",
        "progress": 5,
        "current_stage_id": "delivery-launch",
        "summary": "已完成端到端交付闭环，作为平台模板项目保留。",
        "owner": "交付团队 B",
        "tags": ["模板项目", "已归档"],
    },
]
