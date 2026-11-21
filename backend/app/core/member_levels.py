from enum import IntEnum


class MemberLevel(IntEnum):
    FREE = 0
    VIP = 1
    SVIP = 2
    ENTERPRISE = 3


LEVEL_NAMES = {0: "free", 1: "vip", 2: "svip", 3: "enterprise"}

LEVEL_DISPLAY = {
    0: "免费版",
    1: "个人 VIP",
    2: "个人 SVIP",
    3: "企业版",
}

FEATURE_MIN_LEVEL: dict[str, MemberLevel] = {
    "chat": MemberLevel.FREE,
    "search": MemberLevel.FREE,
    "documents": MemberLevel.VIP,
    "contract_review": MemberLevel.VIP,
    "analysis": MemberLevel.VIP,
    "voice": MemberLevel.VIP,
    "video": MemberLevel.SVIP,
    "enterprise": MemberLevel.ENTERPRISE,
}
