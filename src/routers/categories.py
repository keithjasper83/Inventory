from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from src.database import get_db
from src.models import Category
from src.dependencies import templates, require_user

router = APIRouter()

@router.get("/categories", response_class=HTMLResponse)
async def list_categories(request: Request, db: Session = Depends(get_db), user=Depends(require_user)):
    categories = db.query(Category).all()
    return templates.TemplateResponse(request=request, name="categories.html", context={"request": request, "categories": categories})

@router.get("/categories/{id}/schema")
async def get_category_schema(id: int, db: Session = Depends(get_db), user=Depends(require_user)):
    category = db.query(Category).filter(Category.id == id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return JSONResponse(content=category.schema)

@router.post("/categories")
async def create_category(request: Request, name: str = Form(...), schema_json: str = Form("{}"), db: Session = Depends(get_db), user=Depends(require_user)):
    slug = name.lower().replace(" ", "-")
    if db.query(Category).filter(Category.slug == slug).first():
        import uuid
        slug = f"{slug}-{uuid.uuid4().hex[:4]}"

    import json
    try:
        schema = json.loads(schema_json)
    except:
        schema = {}

    cat = Category(name=name, slug=slug, schema=schema)
    db.add(cat)
    db.commit()
    return RedirectResponse(url="/categories", status_code=303)
