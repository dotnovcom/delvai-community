from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.casbin_enforcer import check_permission
from app.core.database import get_db
from app.models.user import User


def _is_super_admin(db: Session, current_user: User) -> bool:
    if (current_user.admin_role or "") == "super_admin":
        return True
    from app.models.admin_account import AdminAccount

    account = db.query(AdminAccount).filter(AdminAccount.user_id == current_user.id).first()
    return bool(account and account.role == "super_admin")


def require_super_admin(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_admin or not _is_super_admin(db, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅超级管理员可执行此操作")
    return current_user


def require_admin_permission(obj: str, act: str):
    def _dep(current_user: User = Depends(get_current_user)) -> User:
        if not current_user.is_admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")
        role = current_user.admin_role or "viewer"
        if not check_permission(role, obj, act):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"无权执行 {obj}:{act}")
        return current_user

    return _dep
