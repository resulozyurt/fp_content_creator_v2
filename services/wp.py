import httpx
import markdown
import base64
import re
import uuid
import json
from bs4 import BeautifulSoup

def convert_html_to_gutenberg(html_content, image_meta_map):
    soup = BeautifulSoup(html_content, 'html.parser')
    gutenberg_blocks = []
    
    for element in soup.contents:
        if element.name is None or element.name == '\n':
            continue
            
        if element.name == 'p':
            if element.find('img'):
                img = element.find('img')
                img_src = img.get("src", "")
                alt_text = img.get("alt", "")
                
                meta = image_meta_map.get(img_src, {})
                caption = meta.get("caption", "")
                
                caption_html = f'<figcaption class="wp-element-caption">{caption}</figcaption>' if caption else ""
                
                block = f'\n'
                block += f'<figure class="wp-block-image aligncenter size-large"><img src="{img_src}" alt="{alt_text}"/>{caption_html}</figure>\n'
                block += ''
                gutenberg_blocks.append(block)
            else:
                gutenberg_blocks.append(f'\n{str(element)}\n')
        elif element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            level = element.name[1]
            gutenberg_blocks.append(f'\n{str(element)}\n')
        elif element.name in ['ul', 'ol']:
            gutenberg_blocks.append(f'\n{str(element)}\n')
        elif element.name == 'blockquote':
            inner_html = element.encode_contents().decode('utf-8')
            gutenberg_blocks.append(f'\n<blockquote class="wp-block-quote">{inner_html}</blockquote>\n')
        elif element.name == 'table':
            gutenberg_blocks.append(f'\n<figure class="wp-block-table">{str(element)}</figure>\n')
        else:
            gutenberg_blocks.append(f'\n{str(element)}\n')
            
    return "\n\n".join(gutenberg_blocks)

async def upload_bytes_to_wp(client, base_url, token, image_bytes, meta):
    media_url = f"{base_url}/wp-json/wp/v2/media"
    
    # İŞTE BURASI DÜZELTİLDİ: Tekrar PNG formatına çekildi.
    unique_name = f"fieldpie-seo-{uuid.uuid4().hex[:8]}.png"
    
    headers = {
        "Authorization": f"Basic {token}",
        "Content-Disposition": f'attachment; filename="{unique_name}"',
        "Content-Type": "image/png", # JPG hatası giderildi
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36"
    }
    print(f"   -> WP Medya yükleniyor: {unique_name}...")
    try:
        res = await client.post(media_url, headers=headers, content=image_bytes, timeout=60.0)
        if res.status_code in (200, 201):
            print("   -> Medya Yüklendi! Meta etiketler ekleniyor...")
            data = res.json()
            media_id = data.get("id")
            
            update_payload = {
                "title": meta.get("title", ""),
                "alt_text": meta.get("alt", ""),
                "caption": meta.get("caption", "")
            }
            await client.post(f"{media_url}/{media_id}", headers=headers, json=update_payload, timeout=30.0)
            return data.get("source_url")
        else:
            print(f"   [!] MEDYA REDDEDİLDİ. Kodu: {res.status_code} - Hata: {res.text[:150]}")
            return None
    except Exception as e:
        print(f"   [!] MEDYA BAĞLANTI HATASI: {e}")
        return None

async def process_and_publish(data):
    print("\n===========================================")
    print("1. WP GÖNDERİM SÜRECİ BAŞLADI")
    markdown_content = data.content_markdown
    credentials = f"{data.wp_username}:{data.wp_app_password}"
    token = base64.b64encode(credentials.encode()).decode('utf-8')
    base_url = data.wp_url.rstrip('/')
    image_meta_map = {}
    
    b64_pattern = r'(?:\n?)?!\[(?P<alt>[^\]]*)\]\(data:image\/[^;]+;base64,(?P<b64>[^\)]+)\)'
    url_pattern = r'(?:\n?)?!\[(?P<alt>[^\]]*)\]\((?P<url>https?:\/\/[^\)]+)\)'
    
    b64_matches = list(re.finditer(b64_pattern, markdown_content))
    url_matches = list(re.finditer(url_pattern, markdown_content))
    
    print(f"2. Analiz: {len(b64_matches)} Base64 Resim, {len(url_matches)} URL Resim bulundu.")

    async with httpx.AsyncClient(limits=httpx.Limits(max_connections=5)) as client:
        print("3. Resim İşlemleri (İndirme/Yükleme) Başlıyor...")
        
        # Yeni URL görselleri işle
        for match in url_matches:
            try:
                full_match_text = match.group(0)
                meta_str = match.group('meta')
                alt_text = match.group('alt')
                img_url = match.group('url')
                
                meta = json.loads(meta_str) if meta_str else {"alt": alt_text, "title": "", "caption": ""}
                print(f"   -> OpenAI'dan resim indiriliyor: {img_url[:30]}...")
                
                img_res = await client.get(img_url, timeout=30.0)
                if img_res.status_code == 200:
                    wp_image_url = await upload_bytes_to_wp(client, base_url, token, img_res.content, meta)
                else:
                    print(f"   [!] OpenAI İndirme Hatası: {img_res.status_code}")
                    wp_image_url = None
                    
                if wp_image_url:
                    image_meta_map[wp_image_url] = meta
                    markdown_content = markdown_content.replace(full_match_text, f"![{alt_text}]({wp_image_url})")
                else:
                    markdown_content = markdown_content.replace(full_match_text, "")
            except Exception as e:
                print(f"   [!] Resim atlandı (Güvenlik Kalkanı): {e}")
                markdown_content = markdown_content.replace(match.group(0), "")

        # Eski Base64 görselleri işle
        for match in b64_matches:
            try:
                full_match_text = match.group(0)
                meta_str = match.group('meta')
                alt_text = match.group('alt')
                b64_data = match.group('b64')
                
                meta = json.loads(meta_str) if meta_str else {"alt": alt_text, "title": "", "caption": ""}
                wp_image_url = await upload_bytes_to_wp(client, base_url, token, base64.b64decode(b64_data), meta)
                
                if wp_image_url:
                    image_meta_map[wp_image_url] = meta
                    markdown_content = markdown_content.replace(full_match_text, f"![{alt_text}]({wp_image_url})")
                else:
                    markdown_content = markdown_content.replace(full_match_text, "")
            except Exception as e:
                print(f"   [!] Base64 Resim atlandı (Güvenlik Kalkanı): {e}")
                markdown_content = markdown_content.replace(match.group(0), "")

        markdown_content = re.sub(r'!\[.*?\]\(data:image\/.*?;base64,.*?\)', '', markdown_content)

        print("4. Markdown HTML'e, HTML Gutenberg'e çevriliyor...")
        raw_html = markdown.markdown(markdown_content, extensions=['tables', 'fenced_code', 'sane_lists'])
        gutenberg_content = convert_html_to_gutenberg(raw_html, image_meta_map)
        
        print("5. Kinsta (WordPress) Sunucusuna Makale Gönderiliyor...")
        api_url = f"{base_url}/wp-json/wp/v2/posts"
        headers = {
            "Authorization": f"Basic {token}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36"
        }
        payload = {"title": data.title, "content": gutenberg_content, "status": data.status}
        
        try:
            response = await client.post(api_url, headers=headers, json=payload, timeout=60.0)
            if response.status_code in (200, 201):
                print("6. İŞLEM BAŞARILI! Makale Yayınlandı.")
                print("===========================================\n")
                return response.json()
            else:
                print(f"[KRİTİK HATA] WP Makaleyi Reddetti! Kod: {response.status_code} - Yanıt: {response.text[:200]}")
                raise ValueError(f"WP Sunucu Hatası: {response.text[:200]}")
        except Exception as e:
            print(f"[KRİTİK HATA] WP Bağlantısı Koptu: {e}")
            raise ValueError(f"Ağ hatası: {str(e)}")

async def publish_to_wordpress(data):
    return await process_and_publish(data)