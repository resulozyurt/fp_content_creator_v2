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

    # ÇÖZÜM (Madde 3 ve 4): Bold yasağı ve İç Link Artışı Eklendi
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

### 4. GÖRSEL VE İÇ LİNK STRATEJİSİ
- **Görseller (KRİTİK):** İçeriğin mantıklı yerlerine KESİNLİKLE sadece şu formatta yer tutucular ekle: `[IMAGE_1]`, `[IMAGE_2]`, `[IMAGE_3]`, `[IMAGE_4]` vb. Bu yer tutucuların yanına ASLA başka bir açıklama, alt metin veya prompt yazma.
- **İç Linkler (KRİTİK KURAL):** Makale geneline 5-7 adet İÇ LİNK yer tutucusu ekle. ASLA VE ASLA iç linkleri alt alta liste, madde işareti veya yan yana ekleme! Her bir iç linki farklı PARAGRAFLARIN İÇİNE, cümlenin doğal ve organik bir parçası olacak şekilde yedirerek yerleştir. Format: `[İç Link Önerisi: Hangi sayfaya gidilecek]`

### 5. DÖNÜŞÜM VE ÜRÜN ENTEGRASYONU
- Sorun-çözüm bölümünde '{brand_name}' yazılımını doğal bir teknolojik çözüm olarak konumlandır.
- İçeriğin en sonuna çok güçlü bir **Call to Action (CTA)** ekle.

### 6. KAYNAK GÖSTERİMİ VE DIŞ LİNKLEME (CITATION) - DİKKAT!
- Sana verilen bağlamdaki verilerden faydalandığında, o verinin ait olduğu 'KAYNAK URL'yi Markdown formatında metnin içine doğal bir backlink olarak yerleştir.
- KESİNLİKLE dış kaynak (backlink) verirken `[İç Link Önerisi: ...]` ETİKETİNİ KULLANMA! Dış linkler standart `[metin](url)` formatında olmalıdır.

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

async def process_internal_links(markdown_text: str) -> str:
    pattern = r'\[İç Link Önerisi:\s*(.*?)\]'
    matches = list(re.finditer(pattern, markdown_text))
    if not matches:
        return markdown_text
    print("\n-------------------------------------------")
    print("1. OTOMATİK İÇ LİNKLEME MOTORU BAŞLADI")
    urls = await get_all_sitemap_urls("https://www.fieldpie.com/sitemap_index.xml")
    print(f"2. Sitemap tarandı: Toplam {len(urls)} adet canlı URL havuzu oluşturuldu.")
    new_markdown = markdown_text
    for match in matches:
        full_text = match.group(0)
        suggestion = match.group(1)
        best_url = find_best_url(suggestion, urls)
        link_markdown = f"[{suggestion}]({best_url})"
        new_markdown = new_markdown.replace(full_text, link_markdown)
        print(f"   -> Link Eşleşti: '{suggestion}' => {best_url}")
    print("-------------------------------------------\n")
    return new_markdown