from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from src.database import get_db
from src.models import Item
from src.dependencies import templates, get_current_user
from src.ai import ai_client
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/s/{query}", response_class=HTMLResponse)
async def search_slug(query: str, request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    return await search_handler(query, request, db, user)

@router.get("/search", response_class=HTMLResponse)
async def search_query(request: Request, q: str = "", db: Session = Depends(get_db), user=Depends(get_current_user)):
    if not q:
        return templates.TemplateResponse(request=request, name="search.html", context={"request": request, "items": [], "query": ""})
    return await search_handler(q, request, db, user)

async def search_handler(query: str, request: Request, db: Session, user):
    # 1. Deterministic Resolution (Exact Slug)
    exact_slug = db.query(Item).filter(Item.slug == query).first()
    if exact_slug:
        return RedirectResponse(url=f"/i/{exact_slug.slug}")

    # 2. FTS Search
    try:
        # Using plainto_tsquery or phraseto_tsquery
        search_query = text("search_vector @@ plainto_tsquery('english', :q)")
        items = db.query(Item).filter(search_query).params(q=query).all()
    except Exception as e:
        # Fallback for SQLite or error
        logger.warning(f"Search error (falling back to LIKE): {e}")
        items = db.query(Item).filter(Item.name.ilike(f"%{query}%")).all()

    # 3. Jarvis Intent Resolver (if ambiguous/no results - for now just UI indication)
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
