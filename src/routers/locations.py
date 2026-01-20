from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from src.database import get_db
from src.models import Location
from src.dependencies import templates, require_user

router = APIRouter()

@router.get("/locations", response_class=HTMLResponse)
async def list_locations(request: Request, db: Session = Depends(get_db), user=Depends(require_user)):
    locations = db.query(Location).all()
    return templates.TemplateResponse(request=request, name="locations.html", context={"request": request, "locations": locations})

@router.post("/locations")
async def create_location(request: Request, name: str = Form(...), parent_id: int = Form(None), db: Session = Depends(get_db), user=Depends(require_user)):
    slug = name.lower().replace(" ", "-") # Simple slugify
    # Ensure unique slug
    if db.query(Location).filter(Location.slug == slug).first():
        import uuid
        slug = f"{slug}-{uuid.uuid4().hex[:4]}"

    loc = Location(name=name, slug=slug, parent_id=parent_id)
    db.add(loc)
    db.commit()
    return RedirectResponse(url="/locations", status_code=303)
