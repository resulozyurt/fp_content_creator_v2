import os
import anthropic
from datetime import datetime
from typing import List, Dict, Any
import httpx
import re
import asyncio

from services.nlp import extract_target_keywords

def generate_ai_article(keyword: str, language: str, competitor_data: List[Dict[str, Any]]):
    anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    current_year = datetime.now().year

    target_keywords = extract_target_keywords(competitor_data, top_n=15)
    if language.lower() == "en":
        keywords_str = ", ".join([f"{kw['keyword']} (Target: {kw['target_freq']} times)" for kw in target_keywords])
    else:
        keywords_str = ", ".join([f"{kw['keyword']} (Hedef: {kw['target_freq']} kez)" for kw in target_keywords])

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

    # ÇÖZÜM: Bold yasağı, Dış Link Zorunluluğu ve Doğal İç Link (Anchor Text) Formatı
    system_prompt = f"""Sen dünya standartlarında bir SEO uzmanı, içerik stratejisti ve metin yazarısın.
Amacın, '{keyword}' anahtar kelimesi için Google'da 1. sıraya yerleşecek, yüksek CTR ve dönüşüm oranına sahip mükemmel bir makale yazmaktır.

Aşağıda rakiplerin içeriklerini ve onlara ait KAYNAK URL'leri (Bağlam) veriyorum. Aşağıdaki KESİN SEO KURALLARINA harfiyen uymak zorundasın:

### 1. SEO VE BAŞLIK STRATEJİSİ
- **H1 Başlığı:** Tıklama oranını (CTR) artıracak, dikkat çekici ve '{keyword}' ile birlikte '{current_year}', 'Kapsamlı Rehber', 'Checklist' gibi fayda sinyalleri içeren güçlü bir başlık yaz.
- **H2 ve H3 Başlıkları:** Soru formatında (Nasıl yapılır?, Nedir?) kurgula.
- **Keyword Bolding:** Anahtar kelimeyi ('{keyword}') metin geneline en fazla 2-3 kez kalın (bold) yaparak dağıt. ASLA LSI kelimeleri veya diğer normal metinleri kalın (bold) yapma!
- **LSI Kelimeler:** Şu kelimeleri metin geneline belirtilen hedeflere yakın sayılarda doğalca dağıt: {keywords_str}

### 2. İÇERİK DERİNLİĞİ VE UZUNLUK (KRİTİK)
- Makaleyi GEREKSİZ YERE UZATMA. Yuvarlak, jenerik ve yüzeysel laf kalabalığı yapma. 
- Az ama öz, kanıtlara ve net standartlara dayalı, spesifik bilgiler (rakamlar, kurumlar, kanunlar) kullan.
- Makale KESİNLİKLE 'Sonuç' bölümü ile net bir şekilde tamamlanmalı, asla yarıda kesilmemelidir.

### 3. ARAMA NİYETİ VE KULLANICI DENEYİMİ (UX)
- **Featured Snippet:** H1'den hemen sonra, 'What is [Keyword]?' sorusuna yanıt veren maksimum 45-50 kelimelik net bir tanım paragrafı ekle.
- **Pratiklik:** Mutlaka uygulanabilir bir "Checklist" (Kontrol Listesi) veya adım adım rehber bölümü barındır.
- **Okunabilirlik:** Paragrafları kısa tut. Bolca madde işareti ve en az 1 adet HTML Tablo kullan.

### 4. GÖRSEL VE İÇ LİNK STRATEJİSİ (KRİTİK KURAL)
- **Görseller:** İçeriğin mantıklı yerlerine KESİNLİKLE sadece şu formatta yer tutucular ekle: `[IMAGE_1]`, `[IMAGE_2]`, `[IMAGE_3]`, `[IMAGE_4]` vb. Bu yer tutucuların yanına ASLA başka bir açıklama, alt metin veya prompt yazma.
- **İç Linkler:** Makale geneline 5-7 adet İÇ LİNK yer tutucusu ekle. ASLA VE ASLA iç linkleri alt alta liste, madde işareti veya yan yana ekleme! Her bir iç linki farklı PARAGRAFLARIN İÇİNE, cümlenin doğal ve organik bir parçası olacak şekilde yedirerek yerleştir. 
- **İç Link Formatı:** Kesinlikle `[Doğal ve Harekete Geçirici Metin](INTERNAL: Sitemap'te Aranacak Konu)` şeklinde olmalıdır. 
- **Doğru Örnek:** "Ekiplerinizin günlük performansını ölçmek için [kapsamlı bir saha takip yazılımı](INTERNAL: saha operasyon takibi) kullanmanız önerilir."

### 5. DÖNÜŞÜM VE ÜRÜN ENTEGRASYONU
- Sorun-çözüm bölümünde '{brand_name}' yazılımını doğal bir teknolojik çözüm olarak konumlandır.
- İçeriğin en sonuna çok güçlü bir **Call to Action (CTA)** ekle.

### 6. DIŞ KAYNAK (BACKLINK) VE REFERANSLAR (EN KRİTİK KURAL)
- Sana sağlanan RAKİP VERİLERİ (Bağlam) içindeki 'KAYNAK URL'leri, makale içerisinde bir veriyi, istatistiği veya teknik bir detayı açıklarken EN AZ 3 KEZ doğal bir referans backlink'i olarak kullanmak ZORUNDASIN.
- ÖRNEK KULLANIM: "Sektör araştırmalarına göre pazarın büyüyeceği [öngörülmektedir](https://www.rakip-ornek-url.com/arastirma)."
- Dış linkleri KESİNLİKLE standart Markdown formatında `[tıklanabilir metin](KAYNAK URL)` olarak yaz.
- Dış kaynak linklerini verirken ASLA VE ASLA `(INTERNAL: ...)` etiketini kullanma. Bu etiket sadece iç linkler içindir! Kaynaklar doğrudan URL içermelidir.

### 7. SIKÇA SORULAN SORULAR (FAQ)
- Makalenin sonuna '{faq_title}' başlığı altında, PAA formatında 3 adet soru ve kısa cevaplarını ekle.

DİL VE TON KURALI: {lang_rules}
Sadece Markdown formatında makaleyi ver. Ön söz, açıklama veya not ekleme.

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
    
    return {
        "keyword": keyword, 
        "language": language, 
        "article_markdown": response.content[0].text,
        "nlp_matrix": target_keywords
    }

async def get_all_sitemap_urls(index_url: str) -> list:
    urls = []
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.get(index_url)
            if res.status_code != 200: return urls
            locs = re.findall(r'<loc>(.*?)</loc>', res.text)
            sub_sitemaps = [loc for loc in locs if loc.endswith('.xml')]
            direct_urls = [loc for loc in locs if not loc.endswith('.xml')]
            urls.extend(direct_urls)
            if sub_sitemaps:
                tasks = [client.get(sub) for sub in sub_sitemaps]
                responses = await asyncio.gather(*tasks, return_exceptions=True)
                for r in responses:
                    if isinstance(r, httpx.Response) and r.status_code == 200:
                        sub_locs = re.findall(r'<loc>(.*?)</loc>', r.text)
                        urls.extend(sub_locs)
    except Exception as e:
        print(f"[!] Sitemap okuma hatası: {e}")
    return list(set(urls))

def find_best_url(suggestion: str, urls: list) -> str:
    def normalize_text(text: str) -> str:
        replacements = {'ç': 'c', 'ğ': 'g', 'ı': 'i', 'i': 'i', 'ö': 'o', 'ş': 's', 'ü': 'u'}
        text = text.lower()
        for k, v in replacements.items():
            text = text.replace(k, v)
        return re.sub(r'[^a-z0-9\s]', '', text)
    suggestion_words = normalize_text(suggestion).split()
    best_url = "https://www.fieldpie.com"
    max_score = 0
    for url in urls:
        slug = url.rstrip('/').split('/')[-1]
        normalized_slug = normalize_text(slug.replace('-', ' '))
        score = sum(1 for word in suggestion_words if word in normalized_slug and len(word) > 2)
        if score > max_score:
            max_score = score
            best_url = url
    return best_url

async def process_internal_links(markdown_text: str, language: str = "tr") -> str:
    """
    Parses the custom [Anchor Text](INTERNAL: Target Topic) markdown tag.
    Filters the sitemap URLs based on the language slug to prevent cross-language linking,
    and replaces the tag with a real URL fetched from the Sitemap.
    """
    pattern = r'\[([^\]]+)\]\(INTERNAL:\s*(.*?)\)'
    matches = list(re.finditer(pattern, markdown_text))
    
    if not matches:
        return markdown_text
        
    print("\n-------------------------------------------")
    print("1. AUTOMATIC INTERNAL LINKING ENGINE STARTED")
    urls = await get_all_sitemap_urls("https://www.fieldpie.com/sitemap_index.xml")
    
    # --- NEW: LANGUAGE ISOLATION FILTER ---
    # English is main directory (no /tr/), Turkish is /tr/
    target_urls = []
    for url in urls:
        if language.lower() == "tr":
            if "/tr/" in url:
                target_urls.append(url)
        elif language.lower() == "en":
            if "/tr/" not in url:
                target_urls.append(url)
                
    # Failsafe: If filtering returns empty for some reason, use all URLs
    if not target_urls:
        target_urls = urls
        
    print(f"2. Sitemap scanned and filtered for '{language.upper()}': {len(target_urls)} valid URLs found.")
    
    new_markdown = markdown_text
    for match in matches:
        full_text = match.group(0)
        anchor_text = match.group(1) # Actionable visible text
        suggestion = match.group(2)  # Invisible topic to search in sitemap
        
        # We now pass the filtered 'target_urls' list instead of all 'urls'
        best_url = find_best_url(suggestion, target_urls)
        link_markdown = f"[{anchor_text}]({best_url})"
        
        new_markdown = new_markdown.replace(full_text, link_markdown)
        print(f"   -> Link Matched: Topic '{suggestion}' => {best_url} (Anchor Text: '{anchor_text}')")
        
    print("-------------------------------------------\n")
    return new_markdown