import os
from fastapi import APIRouter, Depends, Request, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from src.database import get_db
from src.models import SystemSetting
from src.dependencies import templates, require_user, require_admin
from src.settings_manager import settings_manager
from src.config import settings as app_settings
from fastapi.concurrency import run_in_threadpool
import redis
from rq import Queue

router = APIRouter()

def fetch_admin_data():
    current_settings = settings_manager.get_all()
    stats = {}
    try:
        if os.environ.get("TEST_MODE"):
            import fakeredis
            r = fakeredis.FakeRedis()
        else:
            r = redis.from_url(app_settings.REDIS_URL)

        q = Queue(connection=r)
        stats['queue_length'] = len(q)
        stats['failed_jobs'] = len(Queue('failed', connection=r))

        from rq import Worker
        workers = Worker.all(connection=r)
        stats['workers_count'] = len(workers)
        stats['workers_names'] = [w.name for w in workers]

    except Exception as e:
        stats['error'] = str(e)

    return current_settings, stats

@router.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request, db: Session = Depends(get_db), user=Depends(require_admin)):
    # Offload blocking synchronous I/O (database, redis queries)
    current_settings, stats = await run_in_threadpool(fetch_admin_data)

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
    user=Depends(require_admin)
):
    settings_manager.set("ai_confidence_threshold", ai_confidence_threshold)
    settings_manager.set("scrape_timeout", scrape_timeout)
    settings_manager.set("presigned_url_expiry", presigned_url_expiry)
    settings_manager.set("rq_retry_max", rq_retry_max)

    return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)
