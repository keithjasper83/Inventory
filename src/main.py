from fastapi import FastAPI, Request, status, Depends
from sqlalchemy.orm import Session
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
import os

from src.config import settings, validate_production_config
from src.database import get_db
from src.models import Item
from src.dependencies import templates, get_current_user
from src.routers import auth, items, search, locations, categories, admin, health, counting
from src.ai import ai_client

# Validate production configuration on startup
if os.environ.get("ENVIRONMENT") == "production" or settings.ENVIRONMENT == "production":
    try:
        validate_production_config()
    except ValueError as e:
        import sys
        print(f"FATAL: Production configuration validation failed:\n{e}", file=sys.stderr)
        sys.exit(1)

app = FastAPI(title=settings.APP_NAME)

# Middleware
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Static Files
app.mount("/static", StaticFiles(directory="src/static"), name="static")

# Routers
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(counting.router)
app.include_router(items.router)
app.include_router(search.router)
app.include_router(locations.router)
app.include_router(categories.router)
app.include_router(admin.router)

# Root
@app.get("/", response_class=HTMLResponse)
async def home(request: Request, user=Depends(get_current_user), db: Session = Depends(get_db)):
    if not user:
        return RedirectResponse(url="/login")

    total_items = db.query(Item).count()

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "request": request,
            "user": user,
            "total_items": total_items
        }
    )

# Catch-all / 404 Handler
@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        # Catch-all URL resolver
        path = request.url.path

        # 1. Deterministic (handled by routers mostly, but if we missed something)
        # 2. Search Intent / Jarvis
        intent = await ai_client.resolve_url_intent(path)

        if intent and intent.get('action') == 'redirect' and intent.get('confidence', 0) > 0.8:
            return RedirectResponse(url=intent['url'])

        # If no resolution, show search/404 page
        return templates.TemplateResponse(
            request=request,
            name="404.html",
            context={"request": request, "path": path},
            status_code=404
        )

    return HTMLResponse(content=str(exc.detail), status_code=exc.status_code)
