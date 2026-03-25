from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# Railway ortam değişkenlerindeki URL'i yakalar. Bulamazsa lokalde SQLite kullanır.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./content_engine.db")

# Kritik Düzeltme: SQLAlchemy 1.4+, "postgres://" ön ekini kabul etmez, "postgresql://" bekler.
# Railway bazen eski formatta URL verebildiği için bunu otomatik düzeltiyoruz.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# SQLite ve PostgreSQL için motor (engine) ayarları farklıdır
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    # PostgreSQL bağlantısı
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class ArticleHistory(Base):
    __tablename__ = "article_history"

    id = Column(Integer, primary_key=True, index=True)
    keyword = Column(String, index=True)
    language = Column(String)
    country = Column(String)
    process_summary = Column(Text) # JSON string olarak
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