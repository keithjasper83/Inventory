from fastapi import FastAPI, Request, status, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse

from src.config import settings
from src.dependencies import templates, get_current_user
from src.routers import auth, items, search, locations, categories
from src.ai import ai_client
from src.logging_config import setup_logging, get_logger

# Setup structured logging
setup_logging()
logger = get_logger(__name__)

app = FastAPI(title=settings.APP_NAME)

# Middleware
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Static Files
app.mount("/static", StaticFiles(directory="src/static"), name="static")

# Routers
app.include_router(auth.router)
app.include_router(items.router)
app.include_router(search.router)
app.include_router(locations.router)
app.include_router(categories.router)

# Root
@app.get("/", response_class=HTMLResponse)
async def home(request: Request, user=Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse(request=request, name="index.html", context={"request": request, "user": user})

# Catch-all / 404 Handler
@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        # Catch-all URL resolver
        path = request.url.path
        logger.info(f"404 handler attempting to resolve: {path}")

        # 1. Deterministic (handled by routers mostly, but if we missed something)
        # 2. Search Intent / Jarvis
        intent = await ai_client.resolve_url_intent(path)

        if intent and intent.get('action') == 'redirect' and intent.get('confidence', 0) > 0.8:
            logger.info(f"AI resolved 404 path '{path}' to: {intent['url']}")
            return RedirectResponse(url=intent['url'])

        # If no resolution, show search/404 page
        logger.warning(f"404 path not resolved: {path}")
        return templates.TemplateResponse(
            request=request,
            name="404.html",
            context={"request": request, "path": path},
            status_code=404
        )

    return HTMLResponse(content=str(exc.detail), status_code=exc.status_code)
