from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.admin import FeedbackCreate, LaunchSplashPublicResponse
from app.schemas.platform import PaginatedPublicArticles, PublicArticleDetail
from app.services import cms_service

router = APIRouter()


@router.get("/launch-splash", response_model=LaunchSplashPublicResponse)
def get_launch_splash(platform: str = Query(..., description="mp-weixin|mp-toutiao|h5|wechat_h5|app-android|app-ios|app-harmony"), db: Session = Depends(get_db)):
    data = cms_service.get_active_launch_splash(db, platform)
    return LaunchSplashPublicResponse(
        platform=data["platform"],
        version=data["version"],
        items=data["items"],
    )


@router.get("/articles", response_model=PaginatedPublicArticles)
def list_articles(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=50),
    category: str | None = None,
    db: Session = Depends(get_db),
):
    data = cms_service.list_published_articles(db, page, size, category)
    return {"total": data["total"], "items": data["items"]}


@router.get("/articles/{article_id}", response_model=PublicArticleDetail)
def get_article(article_id: int, db: Session = Depends(get_db)):
    article = cms_service.get_published_article(db, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    return article


@router.post("/feedback")
def submit_feedback(
    body: FeedbackCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    fb = cms_service.create_feedback(
        db,
        current_user.id if current_user else None,
        body.model_dump(),
    )
    return {"id": fb.id, "message": "反馈已提交，感谢您的意见"}
