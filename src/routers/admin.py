"""
Admin Dashboard Router
Provides system settings management and RQ job statistics
"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from src.dependencies import get_db, templates
from src.settings_manager import SettingsManager
from src.models import SystemSetting

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    """Admin dashboard showing system settings and RQ stats"""
    settings = SettingsManager.get_all(db)
    
    # Try to get RQ stats (may not be available if Redis isn't running)
    rq_stats = {
        "available": False,
        "queues": [],
        "workers": 0,
        "jobs_pending": 0,
        "jobs_failed": 0
    }
    
    try:
        from redis import Redis
        from rq import Queue
        from src.config import settings as config_settings
        
        redis_conn = Redis.from_url(config_settings.REDIS_URL)
        redis_conn.ping()  # Test connection
        
        # Get queue stats
        queue = Queue(connection=redis_conn)
        rq_stats["available"] = True
        rq_stats["jobs_pending"] = len(queue)
        rq_stats["jobs_failed"] = queue.failed_job_registry.count
        rq_stats["workers"] = len(queue.workers)
        rq_stats["queues"] = [{"name": "default", "length": len(queue)}]
    except Exception as e:
        # Redis not available or RQ not configured
        pass
    
    return templates.TemplateResponse(
        "admin_dashboard.html",
        {
            "request": request,
            "settings": settings,
            "rq_stats": rq_stats
        }
    )


@router.post("/settings/{setting_id}")
async def update_setting(
    setting_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Update a system setting"""
    form_data = await request.form()
    value = form_data.get("value", "")
    
    setting = db.query(SystemSetting).filter(SystemSetting.id == setting_id).first()
    if setting:
        setting.value = value
        db.commit()
    
    return RedirectResponse(url="/admin", status_code=303)
