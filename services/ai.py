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

    # İlk baştaki o kusursuz, dengeli ve net prompt yapısına dönüyoruz.
    # Ekstra uzatmaması ve net tamamlaması için kısıtlamalar eklendi.
    system_prompt = f"""Sen dünya standartlarında bir SEO uzmanı, içerik stratejisti ve metin yazarısın.
Amacın, '{keyword}' anahtar kelimesi için Google'da 1. sıraya yerleşecek, yüksek CTR ve dönüşüm oranına sahip mükemmel bir makale yazmaktır.

Aşağıda rakiplerin içeriklerini ve onlara ait KAYNAK URL'leri (Bağlam) veriyorum. Aşağıdaki KESİN SEO KURALLARINA harfiyen uymak zorundasın:

### 1. SEO VE BAŞLIK STRATEJİSİ
- **H1 Başlığı:** Tıklama oranını (CTR) artıracak, dikkat çekici ve '{keyword}' ile birlikte '{current_year}', 'Kapsamlı Rehber', 'Checklist' gibi fayda sinyalleri içeren güçlü bir başlık yaz.
- **H2 ve H3 Başlıkları:** Soru formatında (Nasıl yapılır?, Nedir?) kurgula.
- **Keyword Density:** Anahtar kelimeyi ('{keyword}') metin geneline %1-1.5 oranında doğalca (bold yaparak) dağıt.

### 2. İÇERİK DERİNLİĞİ VE UZUNLUK (KRİTİK)
- Makaleyi GEREKSİZ YERE UZATMA. Yuvarlak, jenerik ve yüzeysel laf kalabalığı yapma. 
- Az ama öz, kanıtlara ve net standartlara dayalı, spesifik bilgiler (rakamlar, kurumlar, kanunlar) kullan.
- Makale KESİNLİKLE 'Sonuç' bölümü ile net bir şekilde tamamlanmalı, asla yarıda kesilmemelidir.

### 3. ARAMA NİYETİ VE KULLANICI DENEYİMİ (UX)
- **Featured Snippet:** H1'den hemen sonra, 'What is [Keyword]?' sorusuna yanıt veren maksimum 45-50 kelimelik net bir tanım paragrafı ekle.
- **Pratiklik:** Mutlaka uygulanabilir bir "Checklist" (Kontrol Listesi) veya adım adım rehber bölümü barındır.
- **Okunabilirlik:** Paragrafları kısa tut. Bolca madde işareti ve en az 1 adet HTML Tablo kullan. (Gutenberg/WordPress uyumlu olacak).

### 4. GÖRSEL VE İÇ LİNK STRATEJİSİ
- **Görseller:** En az 2-3 adet görsel yer tutucusu ekle: `[Görsel Önerisi: Alt Text ve başlık]`
- **İç Linkler:** En az 2 yere iç link yer tutucusu ekle: `[İç Link Önerisi: Hangi sayfaya gidilecek]`

### 5. DÖNÜŞÜM VE ÜRÜN ENTEGRASYONU
- Sorun-çözüm bölümünde '{brand_name}' yazılımını (saha yönetim / operasyon platformu) doğal bir teknolojik çözüm olarak konumlandır.
- İçeriğin en sonuna çok güçlü bir **Call to Action (CTA)** ekle.

### 6. KAYNAK GÖSTERİMİ VE DIŞ LİNKLEME (CITATION) - KRİTİK KURAL!
- Sana verilen bağlamdaki verilerden (özellikle istatistikler, araştırmalar, yüzdelik dilimler veya sektörel iddialar) faydalandığında, o verinin ait olduğu 'KAYNAK URL'yi Markdown formatında metnin içine doğal bir backlink olarak yerleştir.
- Örnek Kullanım: "Sektör raporlarına göre saha ekiplerinin verimliliği [mobil yazılımlar sayesinde %30 artmaktadır](https://kaynak-sitenin-urlsi.com/rapor)."
- Asla hayali (halüsinasyon) bir URL uydurma. Sadece aşağıda verilen kaynakları kullan. Eğer veri yoksa linkleme yapma.

### 7. SIKÇA SORULAN SORULAR (FAQ)
- Makalenin sonuna '{faq_title}' başlığı altında, PAA formatında 3 adet soru ve kısa cevaplarını ekle.

DİL VE TON KURALI: {lang_rules}
Sadece Markdown formatında makaleyi ver. Ön söz, açıklama veya not ekleme.

RAKİP VERİLERİ (BAĞLAM):
{combined_context}
"""
    
    # Token limitini eski haline (4000) çektik. 
    response = anthropic_client.messages.create(
        model="claude-sonnet-4-6", 
        max_tokens=4000, 
        temperature=0.75, 
        system=system_prompt,
        messages=[{"role": "user", "content": f"Lütfen '{keyword}' konulu SEO uyumlu makaleyi yazmaya başla."}]
    )
    return {"keyword": keyword, "language": language, "article_markdown": response.content[0].text}