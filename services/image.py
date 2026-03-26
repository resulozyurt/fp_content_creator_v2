import os
import json
import asyncio
import anthropic
from openai import AsyncOpenAI
import re

def get_prompts_from_article(article_markdown: str, keyword: str, language: str) -> dict:
    anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    
    # Makale diline göre SEO etiketlerinin dilini dinamik belirliyoruz
    if language.lower() == "en":
        lang_instruction = "Write the 'alt', 'title', and 'caption' fields in Native English."
    else:
        lang_instruction = "Write the 'alt', 'title', and 'caption' fields in fluent Turkish."

    prompt = f"""You are an expert art director and SEO specialist. Read the article below and generate DALL-E 3 image prompts for the placeholders [IMAGE_1], [IMAGE_2], etc.
Keyword: {keyword}

CRITICAL IMAGE STYLE (MUST OBEY):
- We need ULTRA-REALISTIC, raw, unedited photography.
- Authentic human models with natural expressions. Real-world corporate or retail environments.
- Shot on 35mm lens, cinematic natural lighting, DSLR quality.
- ABSOLUTELY NO 3D renders, NO illustrations, NO plastic/artificial AI look.
- ABSOLUTELY NO text, letters, or typography in the images.

CRITICAL SEO TEXT:
- {lang_instruction}
- 'alt': SEO optimized alt text describing the image.
- 'title': A short, catchy title for the WP Media Library.
- 'caption': A helpful 1-sentence caption to display under the image in the blog post.

OUTPUT EXACTLY IN THIS JSON FORMAT:
{{
    "[IMAGE_1]": {{
        "prompt": "A highly photorealistic shot of...",
        "alt": "...",
        "title": "...",
        "caption": "..."
    }}
}}

ARTICLE TEXT:
{article_markdown[:4000]}
"""
    try:
        response = anthropic_client.messages.create(
            model="claude-sonnet-4-6", 
            max_tokens=1500,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}]
        )
        json_match = re.search(r'\{.*\}', response.content[0].text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
    except Exception as e:
        print(f"Prompt üretim hatası (Anthropic API): {e}")
    return {}

async def generate_openai_base64(prompt: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY") 
    if not api_key: return ""
    client = AsyncOpenAI(api_key=api_key)
    try:
        enhanced_prompt = prompt + " Must be ultra-photorealistic, raw photography, real humans, authentic lighting, no text, no illustration."
        response = await client.images.generate(
            model="dall-e-3",
            prompt=enhanced_prompt[:4000],
            size="1792x1024", 
            quality="standard",
            response_format="b64_json", 
            n=1,
        )
        return response.data[0].b64_json
    except Exception as e:
        print(f"OpenAI API hatası: {e}")
    return ""

async def process_images_in_article(markdown_text: str, keyword: str, language: str) -> str:
    if "[IMAGE_" not in markdown_text:
        return markdown_text

    prompts_data = get_prompts_from_article(markdown_text, keyword, language)
    if not prompts_data: return markdown_text
        
    tasks = []
    tags = []
    meta_list = []
    
    for tag, data in prompts_data.items():
        if tag in markdown_text:
            tasks.append(generate_openai_base64(data["prompt"]))
            tags.append(tag)
            meta_list.append(data)

    results_base64 = await asyncio.gather(*tasks)

    for tag, b64, meta in zip(tags, results_base64, meta_list):
        if b64:
            # FORMAT DÜZELTİLDİ: "image/jpeg" yerine "image/png"
            meta_json = json.dumps({"alt": meta["alt"], "title": meta["title"], "caption": meta["caption"]})
            markdown_img = f"\n![{meta['alt']}](data:image/png;base64,{b64})"
            markdown_text = markdown_text.replace(tag, markdown_img)
            
    return markdown_text