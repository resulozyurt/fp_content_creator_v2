from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
import os

# Veritabanı dosyamız proje ana dizininde oluşacak
SQLALCHEMY_DATABASE_URL = "sqlite:///./content_engine.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class ArticleHistory(Base):
    __tablename__ = "article_history"

    id = Column(Integer, primary_key=True, index=True)
    keyword = Column(String, index=True)
    language = Column(String)
    country = Column(String)
    process_summary = Column(Text) # JSON string olarak saklayacağız
    article_markdown = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

# Tabloları oluştur
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()