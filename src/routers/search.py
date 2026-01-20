from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from src.database import get_db
from src.dependencies import templates, get_current_user
from src.domain.services import SearchService
from src.ai import ai_client

router = APIRouter()

@router.get("/s/{query}", response_class=HTMLResponse)
async def search_slug(query: str, request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Search by slug format."""
    return await search_handler(query, request, db, user)

@router.get("/search", response_class=HTMLResponse)
async def search_query(request: Request, q: str = "", db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Search by query parameter."""
    if not q:
        return templates.TemplateResponse(request=request, name="search.html", context={"request": request, "items": [], "query": ""})
    return await search_handler(q, request, db, user)

async def search_handler(query: str, request: Request, db: Session, user):
    """Handle search requests with deterministic resolution and FTS fallback."""
    search_service = SearchService(db)
    
    # 1. Deterministic Resolution (Exact Slug)
    exact_slug = search_service.find_exact_slug(query)
    if exact_slug:
        return RedirectResponse(url=f"/i/{exact_slug.slug}")

    # 2. FTS Search
    items = search_service.search_items(query)

    # 3. Jarvis Intent Resolver (if ambiguous/no results)
    ai_selected = False
    ai_confidence = 0.0

    if not items:
        intent = await ai_client.resolve_url_intent(query)
        if intent and intent.get('action') == 'redirect' and intent.get('confidence', 0) > 0.8:
            return RedirectResponse(url=intent['url'])

    return templates.TemplateResponse(
        request=request,
        name="search.html",
        context={
            "request": request,
            "items": items,
            "query": query,
            "user": user,
            "ai_selected": ai_selected,
            "ai_confidence": ai_confidence
        }
    )
