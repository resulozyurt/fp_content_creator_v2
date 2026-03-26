import os
import json
import asyncio
import anthropic
from openai import AsyncOpenAI
import re

def get_prompts_from_article(article_markdown: str, keyword: str, language: str) -> dict:
    anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    if language.lower() == "en":
        lang_instruction = "Write the 'alt', 'title', and 'caption' fields in Native English."
    else:
        lang_instruction = "Write the 'alt', 'title', and 'caption' fields in fluent Turkish."

    prompt = f"""You are an expert art director and SEO specialist. Read the article below and generate DALL-E 3 image prompts for the placeholders [IMAGE_1], [IMAGE_2], etc.
Keyword: {keyword}

CRITICAL IMAGE STYLE:
- We need ULTRA-REALISTIC, raw, unedited photography. Authentic human models.
- Shot on 35mm lens, cinematic natural lighting.
- ABSOLUTELY NO 3D renders, NO illustrations, NO text.

CRITICAL SEO TEXT:
- {lang_instruction}
- 'alt': SEO optimized alt text describing the image.
- 'title': A short title.
- 'caption': A helpful 1-sentence caption.

OUTPUT EXACTLY IN THIS JSON FORMAT:
{{
    "[IMAGE_1]": {{"prompt": "...", "alt": "...", "title": "...", "caption": "..."}}
}}

ARTICLE TEXT:
{article_markdown[:4000]}
"""
    try:
        response = anthropic_client.messages.create(
            model="claude-sonnet-4-6", max_tokens=1500, temperature=0.3,
            messages=[{"role": "user", "content": prompt}]
        )
        json_match = re.search(r'\{.*\}', response.content[0].text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
    except Exception as e:
        print(f"Prompt üretim hatası: {e}")
    return {}

async def generate_openai_url(prompt: str) -> str:
    """Base64 YERİNE SADECE GÖRSELİN URL'SİNİ DÖNDÜRÜR. Veri yükünü sıfırlar."""
    api_key = os.getenv("OPENAI_API_KEY") 
    if not api_key: return ""
    client = AsyncOpenAI(api_key=api_key)
    try:
        enhanced_prompt = prompt + " Must be ultra-photorealistic, raw photography, real humans, authentic lighting, no text."
        response = await client.images.generate(
            model="dall-e-3",
            prompt=enhanced_prompt[:4000],
            size="1792x1024", 
            quality="standard",
            response_format="url", # DEĞİŞTİRİLDİ: Artık devasa metin yerine sade URL dönüyor!
            n=1,
        )
        return response.data[0].url
    except Exception as e:
        print(f"OpenAI API hatası: {e}")
    return ""

async def process_images_in_article(markdown_text: str, keyword: str, language: str) -> str:
    if "[IMAGE_" not in markdown_text:
        return markdown_text

    prompts_data = get_prompts_from_article(markdown_text, keyword, language)
    if not prompts_data: return markdown_text
        
    tasks, tags, meta_list = [], [], []
    for tag, data in prompts_data.items():
        if tag in markdown_text:
            tasks.append(generate_openai_url(data["prompt"]))
            tags.append(tag)
            meta_list.append(data)

    results_url = await asyncio.gather(*tasks)

    for tag, img_url, meta in zip(tags, results_url, meta_list):
        if img_url:
            meta_json = json.dumps({"alt": meta["alt"], "title": meta["title"], "caption": meta["caption"]})
            # Base64 yerine doğrudan OpenAI linkini gömüyoruz
            markdown_img = f"\n![{meta['alt']}]({img_url})"
            markdown_text = markdown_text.replace(tag, markdown_img)
            
    return markdown_text