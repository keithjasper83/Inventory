from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from src.database import get_db
from src.dependencies import templates, require_user
from src.domain.services import CategoryService
import json

router = APIRouter()

@router.get("/categories", response_class=HTMLResponse)
async def list_categories(request: Request, db: Session = Depends(get_db), user=Depends(require_user)):
    """List all categories."""
    category_service = CategoryService(db)
    categories = category_service.get_all_categories()
    return templates.TemplateResponse(request=request, name="categories.html", context={"request": request, "categories": categories})

@router.get("/categories/{id}/schema")
async def get_category_schema(id: int, db: Session = Depends(get_db), user=Depends(require_user)):
    """Get category schema by ID."""
    category_service = CategoryService(db)
    category = category_service.get_category_by_id(id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return JSONResponse(content=category.schema)

@router.post("/categories")
async def create_category(request: Request, name: str = Form(...), schema_json: str = Form("{}"), db: Session = Depends(get_db), user=Depends(require_user)):
    """Create a new category."""
    try:
        schema = json.loads(schema_json)
    except json.JSONDecodeError:
        schema = {}
    
    category_service = CategoryService(db)
    category_service.create_category(name, schema)
    return RedirectResponse(url="/categories", status_code=303)
