"""全国法院名称索引（最高院 + 高院 + 中院 + 基层 + 专门法院），供文书「受理法院」检索。"""

from __future__ import annotations

import json
from pathlib import Path

DIRECT_MUNICIPALITIES = frozenset({"北京市", "天津市", "上海市", "重庆市"})

MUNICIPALITY_INTERMEDIATE = {
    "北京市": ("第一", "第二", "第三", "第四"),
    "上海市": ("第一", "第二", "第三"),
    "天津市": ("第一", "第二", "第三"),
    "重庆市": ("第一", "第二", "第三", "第四", "第五"),
}

SPECIAL_COURTS: tuple[str, ...] = (
    "最高人民法院",
    # 知识产权法院
    "北京知识产权法院",
    "上海知识产权法院",
    "广州知识产权法院",
    "海南自由贸易港知识产权法院",
    # 互联网法院
    "北京互联网法院",
    "杭州互联网法院",
    "广州互联网法院",
    "成都互联网法院",
    "厦门互联网法院",
    # 金融法院
    "上海金融法院",
    # 海事法院
    "天津海事法院",
    "大连海事法院",
    "上海海事法院",
    "宁波海事法院",
    "厦门海事法院",
    "青岛海事法院",
    "武汉海事法院",
    "广州海事法院",
    "北海海事法院",
    "海口海事法院",
    "南京海事法院",
    # 铁路运输中级法院（主要枢纽）
    "北京铁路运输中级法院",
    "上海铁路运输中级法院",
    "广州铁路运输中级法院",
    "武汉铁路运输中级法院",
    "成都铁路运输中级法院",
    "西安铁路运输中级法院",
    "哈尔滨铁路运输中级法院",
    "沈阳铁路运输中级法院",
    "济南铁路运输中级法院",
    "南昌铁路运输中级法院",
    "兰州铁路运输中级法院",
    "乌鲁木齐铁路运输中级法院",
    # 兵团
    "新疆生产建设兵团中级人民法院",
    "新疆生产建设兵团第一中级人民法院",
    "新疆生产建设兵团第二中级人民法院",
    "新疆生产建设兵团第三中级人民法院",
    "新疆生产建设兵团第四中级人民法院",
    "新疆生产建设兵团第五中级人民法院",
    "新疆生产建设兵团第六中级人民法院",
    "新疆生产建设兵团第七中级人民法院",
    "新疆生产建设兵团第八中级人民法院",
    "新疆生产建设兵团第九中级人民法院",
    "新疆生产建设兵团第十中级人民法院",
    "新疆生产建设兵团第十二中级人民法院",
    "新疆生产建设兵团第十三中级人民法院",
    "新疆生产建设兵团第十四中级人民法院",
)


def _load_pca() -> dict[str, dict[str, list[str]]]:
    path = Path(__file__).with_name("admin_divisions_pca.json")
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _basic_court_name(province: str, city: str, area: str) -> str:
    """基层人民法院命名：直辖市用「省+区」；地级市的区用「市+区」；县/旗等用「县名+人民法院」。"""
    if province in DIRECT_MUNICIPALITIES:
        return f"{province}{area}人民法院"
    if area.endswith("区"):
        return f"{city}{area}人民法院"
    if area.endswith("市") and city != area:
        return f"{area}人民法院"
    if area.endswith(("县", "旗", "林区", "特区", "自治县")):
        return f"{area}人民法院"
    return f"{city}{area}人民法院"


def _intermediate_court_names(province: str, city: str) -> list[str]:
    if province in DIRECT_MUNICIPALITIES:
        return [f"{province}{n}中级人民法院" for n in MUNICIPALITY_INTERMEDIATE[province]]
    short = f"{city}中级人民法院"
    long = f"{province}{city}中级人民法院"
    if short == long:
        return [short]
    return [short, long]


def build_court_options() -> list[str]:
    pca = _load_pca()
    names: set[str] = set(SPECIAL_COURTS)

    for province, cities in pca.items():
        names.add(f"{province}高级人民法院")

        if province in DIRECT_MUNICIPALITIES:
            for n in MUNICIPALITY_INTERMEDIATE[province]:
                names.add(f"{province}{n}中级人民法院")
            for areas in cities.values():
                for area in areas:
                    names.add(_basic_court_name(province, province, area))
            continue

        for city, areas in cities.items():
            names.update(_intermediate_court_names(province, city))
            for area in areas:
                names.add(_basic_court_name(province, city, area))

    return sorted(names)


COURT_OPTIONS: list[str] = build_court_options()
