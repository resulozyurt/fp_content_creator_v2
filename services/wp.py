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
                
                # SİLİNEN GUTENBERG BLOKLARI GERİ GETİRİLDİ
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
    unique_name = f"fieldpie-seo-{uuid.uuid4().hex[:8]}.png"
    
    # KİNSTA WAF ÇÖZÜMÜ: Form-Data (Tarayıcı Simülasyonu) kullanıyoruz.
    files = {
        'file': (unique_name, image_bytes, 'image/png')
    }
    headers = {
        "Authorization": f"Basic {token}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }
    
    print(f"   -> WP Medya yükleniyor (Multipart Form): {unique_name}...")
    try:
        res = await client.post(media_url, headers=headers, files=files, timeout=60.0)
        if res.status_code in (200, 201):
            print("   -> Medya Yüklendi! Meta etiketler ekleniyor...")
            data = res.json()
            media_id = data.get("id")
            
            # GÜNCELLEME 1: Description alanı buraya dahil edildi
            update_payload = {
                "title": meta.get("title", ""),
                "alt_text": meta.get("alt", ""),
                "caption": meta.get("caption", ""),
                "description": meta.get("description", "")
            }
            # Meta güncellemeleri JSON olarak gider
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
    print("1. WP GÖNDERİM SÜRECİ BAŞLADI (YENİ MİMARİ)")
    markdown_content = data.content_markdown
    credentials = f"{data.wp_username}:{data.wp_app_password}"
    token = base64.b64encode(credentials.encode()).decode('utf-8')
    base_url = data.wp_url.rstrip('/')
    image_meta_map = {}
    
    # GÜNCELLEME 2: Regex'in WP_META JSON'ını ESNEK olarak okuması (okuyunca çökmemesi) sağlandı
    b64_pattern = r'(?:\s*)?!\[(?P<alt>[^\]]*)\]\(data:image\/[^;]+;base64,(?P<b64>[^\)]+)\)'
    b64_matches = list(re.finditer(b64_pattern, markdown_content, flags=re.DOTALL))
    
    print(f"2. Analiz: {len(b64_matches)} Adet Base64 Resim bulundu.")

    async with httpx.AsyncClient(limits=httpx.Limits(max_connections=5)) as client:
        print("3. Resim Yükleme Başlıyor...")
        
        for match in b64_matches:
            try:
                full_match_text = match.group(0)
                match_data = match.groupdict()
                
                meta_str = match_data.get('meta')
                alt_text = match_data.get('alt', '')
                b64_data = match_data.get('b64')
                
                # GÜNCELLEME 3: Description json okumasına eklendi
                meta = json.loads(meta_str) if meta_str else {"alt": alt_text, "title": "", "caption": "", "description": ""}
                
                if b64_data:
                    image_bytes = base64.b64decode(b64_data)
                    wp_image_url = await upload_bytes_to_wp(client, base_url, token, image_bytes, meta)
                else:
                    wp_image_url = None
                
                if wp_image_url:
                    image_meta_map[wp_image_url] = meta
                    markdown_content = markdown_content.replace(full_match_text, f"![{alt_text}]({wp_image_url})")
                else:
                    markdown_content = markdown_content.replace(full_match_text, "")
            except Exception as e:
                print(f"   [!] Resim atlandı (Hata Yakalandı): {e}")
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
                print("6. İŞLEM BAŞARILI! Makale ve Görseller Yayınlandı.")
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