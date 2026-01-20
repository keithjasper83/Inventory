from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from src.database import get_db
from src.dependencies import templates, require_user
from src.domain.services import LocationService

router = APIRouter()

@router.get("/locations", response_class=HTMLResponse)
async def list_locations(request: Request, db: Session = Depends(get_db), user=Depends(require_user)):
    """List all locations."""
    location_service = LocationService(db)
    locations = location_service.get_all_locations()
    return templates.TemplateResponse(request=request, name="locations.html", context={"request": request, "locations": locations})

@router.post("/locations")
async def create_location(request: Request, name: str = Form(...), parent_id: int = Form(None), db: Session = Depends(get_db), user=Depends(require_user)):
    """Create a new location."""
    location_service = LocationService(db)
    location_service.create_location(name, parent_id)
    return RedirectResponse(url="/locations", status_code=303)
