from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from dotenv import load_dotenv
import os
import json
import re # Boşta kalan görsel taglerini silmek için eklendi

from models import SerpRequest, ScrapeRequest, GenerateArticleRequest, AutoGenerateRequest, WPPublishRequest
from services.serp import fetch_serp_data
from services.scraper import fetch_scraped_data
from services.ai import generate_ai_article, process_internal_links
from services.wp import publish_to_wordpress
from services.db import get_db, ArticleHistory
from services.image import process_images_in_article

load_dotenv()

app = FastAPI(
    title=os.getenv("PROJECT_NAME", "SEO AI API"),
    description="Modüler SEO ve WP İçerik Motoru",
    version="2.4.1"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/css", StaticFiles(directory="frontend/css"), name="css")
app.mount("/js", StaticFiles(directory="frontend/js"), name="js")

@app.get("/")
async def root():
    return FileResponse("frontend/index.html")

@app.get("/history")
async def history_page():
    return FileResponse("frontend/history.html")

@app.get("/wp-settings")
async def wp_settings_page():
    return FileResponse("frontend/wp-settings.html")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "architecture": "modular"}

@app.post("/api/v1/auto-create-article")
async def auto_create_article_endpoint(request: AutoGenerateRequest, db: Session = Depends(get_db)):
    try:
        serp_data = await fetch_serp_data(request.keyword, request.language, request.country)
        blacklist = ['youtube.com', 'facebook.com', 'instagram.com', 'pinterest.com', 'twitter.com', 'tiktok.com', 'linkedin.com', 'amazon.com', 'hepsiburada.com', 'trendyol.com', 'sahibinden.com', 'eksi']
        
        all_competitors = serp_data.get("competitors", [])
        valid_competitors = []
        ignored_competitors = []

        for comp in all_competitors:
            if any(blocked in comp["link"].lower() for blocked in blacklist):
                ignored_competitors.append(comp)
            else:
                valid_competitors.append(comp)
        
        if not valid_competitors:
             raise HTTPException(status_code=404, detail="Google'da taranabilir uygun rakip bulunamadı.")

        top_competitors = valid_competitors[:10]
        urls_to_scrape = [comp["link"] for comp in top_competitors]

        scrape_data = await fetch_scraped_data(urls_to_scrape)
        competitor_data = [{"url": item["url"], "content": item["content"]} for item in scrape_data.get("data", [])]
        
        if not competitor_data:
             raise HTTPException(status_code=500, detail="İçerikler kazınamadı.")

        # AI Üretimi ve NLP Verisi Yakalama
        article_data = generate_ai_article(request.keyword, request.language, competitor_data)
        final_markdown = article_data.get("article_markdown", "")
        nlp_matrix = article_data.get("nlp_matrix", []) # EKSİK OLAN SATIR EKLENDİ

        final_markdown = await process_internal_links(final_markdown)
        final_markdown = await process_images_in_article(final_markdown, request.keyword, request.language)

        # ÇÖZÜM (Madde 6): Görsel üretilemeyen yerlerdeki [IMAGE_X] taglerini temizle
        final_markdown = re.sub(r'\[IMAGE_[^\]]+\]', '', final_markdown)

        process_summary = {
            "keyword": request.keyword,
            "total_found": len(all_competitors),
            "analyzed": len(top_competitors),
            "ignored": len(ignored_competitors),
            "successful_scrapes": scrape_data.get("success_count", 0),
            "competitor_details": top_competitors,
            "ignored_details": ignored_competitors
        }

        db_record = ArticleHistory(
            keyword=request.keyword,
            language=request.language,
            country=request.country,
            process_summary=json.dumps(process_summary),
            article_markdown=final_markdown
        )
        db.add(db_record)
        db.commit()
        db.refresh(db_record)

        return {
            "status": "success",
            "history_id": db_record.id,
            "process_summary": process_summary,
            "final_article": final_markdown,
            "nlp_matrix": nlp_matrix # FRONTEND'E GÖNDERİLİYOR
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Otomasyon Hatası: {str(e)}")

@app.get("/api/v1/history")
def get_history(db: Session = Depends(get_db)):
    records = db.query(ArticleHistory).order_by(ArticleHistory.created_at.desc()).all()
    result = []
    for r in records:
        try:
            summary = json.loads(r.process_summary) if r.process_summary else {}
        except Exception:
            summary = {}
            
        result.append({
            "id": r.id,
            "keyword": r.keyword,
            "language": r.language,
            "created_at": r.created_at,
            "process_summary": summary,
            "article_markdown": r.article_markdown
        })
    return result

@app.post("/api/v1/publish-to-wp")
async def publish_to_wp_endpoint(request: WPPublishRequest):
    try:
        result = await publish_to_wordpress(request)
        return {
            "status": "success", 
            "message": "İçerik başarıyla WordPress'e aktarıldı.",
            "post_id": result.get("id"),
            "post_url": result.get("link")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))