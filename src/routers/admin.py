import os
from fastapi import APIRouter, Depends, Request, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from src.database import get_db
from src.models import SystemSetting
from src.dependencies import templates, require_user
from src.settings_manager import settings_manager
from src.config import settings as app_settings
import redis
from rq import Queue

router = APIRouter()

@router.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request, db: Session = Depends(get_db), user=Depends(require_user)):
    # 1. Fetch Settings
    # We want to show all defaults + overrides
    current_settings = {}
    for key, default_val in settings_manager._defaults.items():
        current_settings[key] = settings_manager.get(key)

    # 2. Fetch Stats
    stats = {}
    try:
        # Mock redis if needed
        if os.environ.get("TEST_MODE"):
            import fakeredis
            r = fakeredis.FakeRedis()
        else:
            r = redis.from_url(app_settings.REDIS_URL)

        q = Queue(connection=r)
        stats['queue_length'] = len(q)
        stats['failed_jobs'] = len(Queue('failed', connection=r))

        # Worker stats could be fetched via Worker.all(connection=r)
        from rq import Worker
        workers = Worker.all(connection=r)
        stats['workers_count'] = len(workers)
        stats['workers_names'] = [w.name for w in workers]

    except Exception as e:
        stats['error'] = str(e)

    return templates.TemplateResponse(
        request=request,
        name="admin_dashboard.html",
        context={
            "request": request,
            "settings": current_settings,
            "stats": stats,
            "user": user
        }
    )

@router.post("/admin/settings")
async def update_settings(
    request: Request,
    ai_confidence_threshold: float = Form(...),
    scrape_timeout: int = Form(...),
    presigned_url_expiry: int = Form(...),
    rq_retry_max: int = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_user)
):
    settings_manager.set("ai_confidence_threshold", ai_confidence_threshold)
    settings_manager.set("scrape_timeout", scrape_timeout)
    settings_manager.set("presigned_url_expiry", presigned_url_expiry)
    settings_manager.set("rq_retry_max", rq_retry_max)

    return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)
