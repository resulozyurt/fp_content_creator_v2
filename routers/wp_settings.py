from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from services.db import get_db, WPSettings, User
from middleware.auth import get_current_user
from models import WPSettingsCreate, WPSettingsResponse

router = APIRouter(prefix="/api/wp-settings", tags=["WP Settings"])

@router.get("/", response_model=WPSettingsResponse)
def get_wp_settings(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Kullanıcının aktif WP ayarlarını getirir."""
    settings = db.query(WPSettings).filter(WPSettings.user_id == current_user.id).first()
    if not settings:
        raise HTTPException(status_code=404, detail="WP ayarları bulunamadı.")
    return settings

@router.post("/", response_model=WPSettingsResponse)
def save_wp_settings(request: WPSettingsCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Kullanıcının WP ayarlarını veritabanına kaydeder veya günceller."""
    settings = db.query(WPSettings).filter(WPSettings.user_id == current_user.id).first()
    
    if settings:
        settings.website_name = request.website_name
        settings.wp_url = request.wp_url
        settings.wp_username = request.wp_username
        settings.wp_app_password = request.wp_app_password
    else:
        settings = WPSettings(
            user_id=current_user.id,
            website_name=request.website_name,
            wp_url=request.wp_url,
            wp_username=request.wp_username,
            wp_app_password=request.wp_app_password
        )
        db.add(settings)
    
    db.commit()
    db.refresh(settings)
    return settings