import os
import anthropic
from datetime import datetime
from typing import List, Dict, Any

def generate_ai_article(keyword: str, language: str, competitor_data: List[Dict[str, Any]]):
    anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    current_year = datetime.now().year

    # Rakiplerin URL'lerini ve içeriklerini yapay zekanın anlayacağı şekilde birleştiriyoruz
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
Amacın, '{keyword}' anahtar kelimesi için Google'da 1. sıraya yerleşecek, yüksek CTR ve dönüşüm oranına sahip mükemmel bir makale yazmaktır.

Aşağıda rakiplerin içeriklerini ve onlara ait KAYNAK URL'leri (Bağlam) veriyorum. Aşağıdaki KESİN SEO ve İÇERİK KALİTESİ KURALLARINA harfiyen uymak zorundasın:

### 1. BİLGİ YOĞUNLUĞU VE DERİNLİK (EN KRİTİK KURAL)
- ASLA yüzeysel, jenerik ve yuvarlak ifadeler kullanma. (Örn: "Personel hijyeni çok önemlidir" gibi boş cümleler kurma.)
- Bunun yerine spesifik ol: Rakamlar, dereceler, kanun/yönetmelik isimleri, otorite kurumlar (Sağlık Bakanlığı, WHO, OSHA vb.) ve net standartlar ver. 
- Örnek Doğru Kullanım: "New York Şehri Sağlık Departmanı yönergelerine göre (Madde 4.1), çapraz bulaşmayı önlemek için çiğ et kesim tahtaları ile sebze kesim tahtaları farklı renklerde olmak zorundadır."
- Okuyucuya "Ne yapmalı?" sorusunun yanında "Tam olarak nasıl, hangi standartta yapmalı?" sorusunun cevabını ver.

### 2. SEO VE BAŞLIK STRATEJİSİ
- **H1 Başlığı:** Tıklama oranını (CTR) artıracak, dikkat çekici ve '{keyword}' ile birlikte '{current_year}', 'Kapsamlı Rehber' gibi fayda sinyalleri içeren güçlü bir başlık yaz.
- **H2 ve H3 Başlıkları:** Soru formatında (Nasıl yapılır?, Nedir?, Hangi standartlar geçerlidir?) kurgula.
- **Keyword Density:** Anahtar kelimeyi ('{keyword}') metin geneline LSI (Latent Semantic Indexing) mantığıyla doğalca dağıt.

### 3. ARAMA NİYETİ VE KULLANICI DENEYİMİ (UX)
- **Featured Snippet:** H1'den hemen sonra konunun en net tanımını yapan maksimum 45-50 kelimelik bir paragraf ekle.
- **Pratiklik:** Mutlaka uygulanabilir bir "Checklist" (Kontrol Listesi) barındır.
- **Okunabilirlik:** Paragrafları kısa tut. Bolca madde işareti ve karmaşık verileri özetleyen en az 1 adet HTML Tablo kullan.

### 4. GÖRSEL VE İÇ LİNK STRATEJİSİ
- **Görseller:** Spesifik diyagram veya tablo yer tutucuları ekle: `[Görsel Önerisi: XYZ Yönetmeliği Standartları İnfografiği]`
- **İç Linkler:** Bağlama uygun iç link yer tutucuları ekle.

### 5. DÖNÜŞÜM VE ÜRÜN ENTEGRASYONU
- Sorun-çözüm bölümünde '{brand_name}' yazılımını (saha yönetim / operasyon platformu) süreçleri dijitalleştiren ve hata payını sıfıra indiren bir teknolojik çözüm olarak konumlandır.
- İçeriğin en sonuna çok güçlü bir **Call to Action (CTA)** ekle.

### 6. KAYNAK GÖSTERİMİ VE DIŞ LİNKLEME (CITATION)
- Sana verilen bağlamdaki verilerden faydalandığında, o verinin ait olduğu 'KAYNAK URL'yi metnin içine Markdown formatında doğal bir backlink olarak yerleştir.
- Asla hayali (halüsinasyon) bir URL veya veri uydurma. Veriyi bağlamdan çek, otoriteyi bağlama daya.

### 7. SIKÇA SORULAN SORULAR (FAQ)
- Makalenin sonuna '{faq_title}' başlığı altında, PAA (People Also Ask) formatında 3 adet niş soru ve kısa cevaplarını ekle.

DİL VE TON KURALI: {lang_rules}
Sadece Markdown formatında makaleyi ver. Hiçbir açıklama veya ön söz ekleme.

RAKİP VERİLERİ (BAĞLAM):
{combined_context}
"""
    response = anthropic_client.messages.create(
        model="claude-sonnet-4-6", 
        max_tokens=4000, 
        temperature=0.75, 
        system=system_prompt,
        messages=[{"role": "user", "content": f"Lütfen '{keyword}' konulu SEO uyumlu makaleyi yazmaya başla."}]
    )
    return {"keyword": keyword, "language": language, "article_markdown": response.content[0].text}