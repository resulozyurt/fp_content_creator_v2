import os
import anthropic
from datetime import datetime
from typing import List, Dict, Any

def generate_ai_article(keyword: str, language: str, competitor_data: List[Dict[str, Any]]):
    anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    current_year = datetime.now().year

    combined_context = ""
    for item in competitor_data:
        combined_context += f"KAYNAK URL: {item['url']}\nİÇERİK: {item['content'][:3000]}\n\n---\n\n"

    if language.lower() == "en":
        lang_rules = "Write in Native US English. Use AP Style, active voice, and professional corporate idioms."
        brand_name = "FieldPie"
        faq_title = "Frequently Asked Questions (FAQ)"
    else:
        lang_rules = "Kusursuz, akıcı ve doğal bir Türkçe kullan. Çeviri kokmayan, dönüşüm odaklı (conversion-focused) bir dil benimse. Edilgen yapıları kullanma."
        brand_name = "FieldPie"
        faq_title = "Sıkça Sorulan Sorular (SSS)"

    system_prompt = f"""Sen dünya standartlarında bir SEO uzmanı, içerik stratejisti ve alanında otorite bir başdenetmensin.
Amacın, '{keyword}' anahtar kelimesi için Google'da 1. sıraya yerleşecek, yüksek CTR ve dönüşüm oranına sahip, kesintisiz ve tam kapsamlı bir makale yazmaktır.

Aşağıda rakiplerin içeriklerini ve onlara ait KAYNAK URL'leri (Bağlam) veriyorum. KESİN KURALLAR:

### 1. İÇERİK BÜTÜNLÜĞÜ VE YARIYDA KESİLMEME (KRİTİK)
- Makaleyi ASLA yarıda kesme. Eksiksiz bir başlangıç, gelişme ve 'Sonuç' bölümüyle tamamla.
- Konuyu gereksiz uzatmadan, ancak arama niyetini %100 doyuracak derinlikte işle.

### 2. ANAHTAR KELİME YOĞUNLUĞU VE DOĞALLIK
- '{keyword}' anahtar kelimesini ilk paragrafta (ilk 100 kelime içinde), H2 başlıklarının bazılarında ve sonuç bölümünde DOĞAL bir şekilde kullan. Okumayı zorlaştıran spam tekrarlardan kaçın. LSI kelimelerle metni zenginleştir.

### 3. BİLGİ YOĞUNLUĞU VE DERİNLİK
- Rakamlar, dereceler, kanun/yönetmelik isimleri, otorite kurumlar ve net standartlar ver. Yüzeysel ifadeler kullanma. Okuyucuya "Tam olarak nasıl, hangi standartta yapmalı?" sorusunun cevabını ver.

### 4. SEO VE BAŞLIK STRATEJİSİ
- **H1 Başlığı:** Tıklama oranını artıracak, '{keyword}' ve '{current_year}' içeren güçlü bir başlık.
- **H2 ve H3:** Hiyerarşik ve soru formatında (Nasıl yapılır?, Nedir?).
- **Formatlar:** Bullet listler, checklistler, blockquoteler ve en az 1 adet HTML Tablo KESİNLİKLE kullan. WordPress'e aktarılacağı için Markdown yapısı kusursuz olmalı.

### 5. DÖNÜŞÜM VE ÜRÜN ENTEGRASYONU
- Sorun-çözüm bölümünde '{brand_name}' yazılımını süreçleri dijitalleştiren teknolojik bir çözüm olarak konumlandır. İçeriği güçlü bir Call to Action (CTA) ile bitir.

### 6. KAYNAK GÖSTERİMİ (CITATION)
- Bağlamdaki verilerden faydalandığında, ait olduğu 'KAYNAK URL'yi metnin içine Markdown formatında backlink olarak yerleştir. Hayali link uydurma.

DİL VE TON KURALI: {lang_rules}
Sadece Markdown formatında makaleyi ver. Ön söz veya açıklama ekleme.

RAKİP VERİLERİ (BAĞLAM):
{combined_context}
"""
    # max_tokens limitini artırdık ki içerik yarıda kesilmesin.
    response = anthropic_client.messages.create(
        model="claude-sonnet-4-6", 
        max_tokens=6000, 
        temperature=0.75, 
        system=system_prompt,
        messages=[{"role": "user", "content": f"Lütfen '{keyword}' konulu SEO uyumlu makaleyi eksiksiz bir şekilde yaz."}]
    )
    return {"keyword": keyword, "language": language, "article_markdown": response.content[0].text}