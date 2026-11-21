import os
from functools import lru_cache

import casbin
from casbin.persist.adapters import FileAdapter

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
_MODEL_PATH = os.path.join(_BASE_DIR, "casbin_model.conf")
_POLICY_PATH = os.path.join(_BASE_DIR, "casbin_policy.csv")


@lru_cache
def get_enforcer() -> casbin.Enforcer:
    adapter = FileAdapter(_POLICY_PATH)
    enforcer = casbin.Enforcer(_MODEL_PATH, adapter)
    enforcer.enable_auto_save(True)
    return enforcer


def check_permission(role: str, obj: str, act: str) -> bool:
    if not role:
        return False
    return get_enforcer().enforce(role, obj, act)


def reload_policies() -> None:
    get_enforcer().load_policy()


def clear_enforcer_cache() -> None:
    get_enforcer.cache_clear()
