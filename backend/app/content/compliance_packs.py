"""企业合规行业包：checklist 与政策模板。"""

from __future__ import annotations

from copy import deepcopy

DEFAULT_PACK = {
    "key": "general",
    "label": "通用企业",
    "aliases": ["通用", "default", "其他"],
    "checklist": [
        {"id": 1, "item": "营业执照及经营范围合规", "status": "pending", "priority": "high"},
        {"id": 2, "item": "劳动用工合同与社保缴纳", "status": "pending", "priority": "high"},
        {"id": 3, "item": "数据安全与个人信息保护", "status": "pending", "priority": "medium"},
        {"id": 4, "item": "广告宣传合规审查", "status": "pending", "priority": "medium"},
        {"id": 5, "item": "税务申报与发票管理", "status": "pending", "priority": "high"},
        {"id": 6, "item": "安全生产与消防制度", "status": "pending", "priority": "medium"},
    ],
    "policies": [
        {"title": "企业合规管理通用指引", "summary": "建议建立合规负责人制度，定期开展自查并留存记录。", "date": ""},
    ],
}

INDUSTRY_PACKS: list[dict] = [
    DEFAULT_PACK,
    {
        "key": "internet",
        "label": "互联网/科技",
        "aliases": ["互联网", "科技", "软件", "IT", "平台"],
        "checklist": [
            {"id": 1, "item": "ICP/EDI 等电信业务许可", "status": "pending", "priority": "high"},
            {"id": 2, "item": "用户协议与隐私政策公示", "status": "pending", "priority": "high"},
            {"id": 3, "item": "个人信息保护法合规（同意、删除、跨境）", "status": "pending", "priority": "high"},
            {"id": 4, "item": "算法推荐与内容审核机制", "status": "pending", "priority": "medium"},
            {"id": 5, "item": "网络安全等级保护与日志留存", "status": "pending", "priority": "high"},
            {"id": 6, "item": "未成年人保护与防沉迷", "status": "pending", "priority": "medium"},
        ],
        "policies": [
            {"title": "《个人信息保护法》要点", "summary": "处理个人信息须具有合法基础，显著告知并保障用户权利。", "date": ""},
            {"title": "《网络安全法》合规要求", "summary": "关键信息基础设施运营者须履行安全保护义务。", "date": ""},
        ],
    },
    {
        "key": "manufacturing",
        "label": "制造业",
        "aliases": ["制造", "制造业", "工业", "生产"],
        "checklist": [
            {"id": 1, "item": "生产许可与产品强制性认证", "status": "pending", "priority": "high"},
            {"id": 2, "item": "环保排污许可与环评验收", "status": "pending", "priority": "high"},
            {"id": 3, "item": "安全生产标准化与特种作业持证", "status": "pending", "priority": "high"},
            {"id": 4, "item": "供应链合同与质量追溯", "status": "pending", "priority": "medium"},
            {"id": 5, "item": "职业病防治与劳动防护", "status": "pending", "priority": "medium"},
        ],
        "policies": [
            {"title": "安全生产法合规要点", "summary": "建立健全全员安全生产责任制，定期开展隐患排查。", "date": ""},
        ],
    },
    {
        "key": "finance",
        "label": "金融/类金融",
        "aliases": ["金融", "finance", "银行", "保险", "证券", "支付"],
        "checklist": [
            {"id": 1, "item": "金融业务许可与经营范围", "status": "pending", "priority": "high"},
            {"id": 2, "item": "反洗钱客户身份识别（KYC）", "status": "pending", "priority": "high"},
            {"id": 3, "item": "消费者权益保护与适当性管理", "status": "pending", "priority": "high"},
            {"id": 4, "item": "数据安全与金融信息保护", "status": "pending", "priority": "high"},
            {"id": 5, "item": "关联交易与信息披露", "status": "pending", "priority": "medium"},
        ],
        "policies": [
            {"title": "反洗钱合规义务", "summary": "建立客户尽职调查、可疑交易报告等内控制度。", "date": ""},
        ],
    },
    {
        "key": "retail",
        "label": "零售/电商",
        "aliases": ["零售", "电商", "商贸", "连锁"],
        "checklist": [
            {"id": 1, "item": "商品质量与标签标识合规", "status": "pending", "priority": "high"},
            {"id": 2, "item": "消费者权益保护法（退换货、三包）", "status": "pending", "priority": "high"},
            {"id": 3, "item": "价格促销与广告合规", "status": "pending", "priority": "medium"},
            {"id": 4, "item": "食品/特殊商品许可（如适用）", "status": "pending", "priority": "high"},
            {"id": 5, "item": "平台入驻协议与供应商管理", "status": "pending", "priority": "medium"},
        ],
        "policies": [
            {"title": "电子商务法平台义务", "summary": "平台须核验经营者身份，保存交易信息并配合监管。", "date": ""},
        ],
    },
]


def list_industry_options() -> list[dict]:
    from app.content.enterprise_industries import list_enterprise_industries

    return list_enterprise_industries()


def resolve_compliance_pack(industry: str) -> dict:
    raw = (industry or "").strip().lower()
    for pack in INDUSTRY_PACKS:
        if pack["key"] == "general":
            continue
        if raw == pack["key"] or raw == pack["label"].lower():
            return pack
        for alias in pack.get("aliases", []):
            if raw == alias.lower() or alias.lower() in raw or raw in alias.lower():
                return pack
    return DEFAULT_PACK


def build_checklist_for_industry(industry: str) -> list[dict]:
    pack = resolve_compliance_pack(industry)
    return deepcopy(pack["checklist"])


def build_policies_for_industry(industry: str, keywords: list[str] | None = None) -> list[dict]:
    from datetime import date

    pack = resolve_compliance_pack(industry)
    kw = keywords or [industry]
    policies = deepcopy(pack.get("policies", []))
    today = str(date.today())
    for p in policies:
        p["date"] = today
        if kw:
            p["summary"] = f"{p['summary']}（关键词：{', '.join(kw)}）"
    policies.append({
        "title": f"{pack['label']}最新法规动态",
        "summary": "请关注行业主管部门发布的最新规范性文件，并同步更新内部制度。",
        "date": today,
    })
    return policies
