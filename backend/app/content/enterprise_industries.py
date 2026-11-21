"""企业所属行业选项（创建企业、合规检查等统一数据源）。"""

from __future__ import annotations

# key 存入 enterprises.industry；合规清单仍通过 compliance_packs.resolve_compliance_pack 映射
ENTERPRISE_INDUSTRIES: list[dict] = [
    {"key": "general", "label": "通用企业", "aliases": ["通用", "其他", "default"]},
    {"key": "internet", "label": "互联网/科技", "aliases": ["互联网", "科技", "IT", "平台"]},
    {"key": "software", "label": "软件和信息技术服务业", "aliases": ["软件", "信息技术", "SaaS"]},
    {"key": "telecom", "label": "电信/通信", "aliases": ["电信", "通信", "运营商"]},
    {"key": "manufacturing", "label": "制造业", "aliases": ["制造", "工业", "生产"]},
    {"key": "electronics", "label": "电子/半导体", "aliases": ["电子", "半导体", "芯片"]},
    {"key": "automotive", "label": "汽车及零部件", "aliases": ["汽车", "新能源车", "零部件"]},
    {"key": "chemical", "label": "化工", "aliases": ["化学", "化工材料"]},
    {"key": "textile", "label": "纺织/服装", "aliases": ["纺织", "服装", "服饰"]},
    {"key": "food", "label": "食品/饮料", "aliases": ["食品", "饮料", "餐饮供应链"]},
    {"key": "pharma", "label": "医药/生物", "aliases": ["医药", "生物", "医疗器械"]},
    {"key": "finance", "label": "金融/类金融", "aliases": ["金融", "finance", "支付"]},
    {"key": "banking", "label": "银行", "aliases": ["商业银行", "银行机构"]},
    {"key": "insurance", "label": "保险", "aliases": ["保险公司", "保险经纪"]},
    {"key": "securities", "label": "证券/投资", "aliases": ["证券", "基金", "投资", "资管"]},
    {"key": "retail", "label": "零售/电商", "aliases": ["零售", "电商", "商贸", "连锁"]},
    {"key": "wholesale", "label": "批发和贸易", "aliases": ["批发", "贸易", "进出口"]},
    {"key": "logistics", "label": "交通运输/物流", "aliases": ["物流", "运输", "快递", "仓储"]},
    {"key": "construction", "label": "建筑业", "aliases": ["建筑", "工程", "施工"]},
    {"key": "real_estate", "label": "房地产业", "aliases": ["房地产", "地产", "物业"]},
    {"key": "energy", "label": "能源/采矿", "aliases": ["能源", "采矿", "石油", "煤炭"]},
    {"key": "utilities", "label": "公用事业", "aliases": ["电力", "水务", "燃气"]},
    {"key": "environmental", "label": "环保", "aliases": ["环境保护", "节能环保"]},
    {"key": "agriculture", "label": "农/林/牧/渔", "aliases": ["农业", "林业", "牧业", "渔业"]},
    {"key": "education", "label": "教育", "aliases": ["学校", "培训", "教培"]},
    {"key": "healthcare", "label": "医疗卫生", "aliases": ["医疗", "卫生", "医院", "诊所"]},
    {"key": "culture_media", "label": "文化/传媒/娱乐", "aliases": ["传媒", "文化", "娱乐", "广告"]},
    {"key": "tourism", "label": "旅游", "aliases": ["旅行社", "景区", "酒店旅游"]},
    {"key": "hospitality", "label": "住宿和餐饮", "aliases": ["酒店", "餐饮", "饭店"]},
    {"key": "sports", "label": "体育", "aliases": ["体育赛事", "健身"]},
    {"key": "research", "label": "科学研究和技术服务", "aliases": ["科研", "技术服务", "检测认证"]},
    {"key": "professional", "label": "专业咨询服务", "aliases": ["咨询", "会计", "审计", "人力资源"]},
    {"key": "legal", "label": "法律服务", "aliases": ["律所", "律师", "法律服务机构"]},
    {"key": "leasing", "label": "租赁和商务服务", "aliases": ["商务服务", "租赁", "会展"]},
    {"key": "international", "label": "国际贸易", "aliases": ["外贸", "跨境", "国际业务"]},
    {"key": "public_admin", "label": "公共管理/社会组织", "aliases": ["事业单位", "社会组织", "协会"]},
    {"key": "charity", "label": "非营利/公益", "aliases": ["公益", "慈善", "基金会"]},
]

_INDUSTRY_BY_KEY = {item["key"]: item for item in ENTERPRISE_INDUSTRIES}


def list_enterprise_industries() -> list[dict]:
    return [
        {"key": item["key"], "label": item["label"], "aliases": list(item.get("aliases", []))}
        for item in ENTERPRISE_INDUSTRIES
    ]


def get_industry_label(key: str | None) -> str:
    if not key:
        return "通用企业"
    item = _INDUSTRY_BY_KEY.get(key)
    if item:
        return item["label"]
    return key


def normalize_industry_key(value: str | None) -> str:
    raw = (value or "").strip()
    if not raw:
        raise ValueError("请选择所属行业")

    if raw in _INDUSTRY_BY_KEY:
        return raw

    lower = raw.lower()
    for item in ENTERPRISE_INDUSTRIES:
        if item["label"].lower() == lower or item["label"] == raw:
            return item["key"]
        for alias in item.get("aliases", []):
            alias_l = alias.lower()
            if lower == alias_l or raw == alias or alias_l in lower or lower in alias_l:
                return item["key"]

    raise ValueError("无效的行业选项")
