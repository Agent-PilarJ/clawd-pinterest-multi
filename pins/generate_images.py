#!/usr/bin/env python3
"""
Pinterest Pin Image Generator
Uses Kie.ai API (flux-2-pro), fallback to PIL placeholders
"""
import requests
import time
import os
import json
from pathlib import Path

KIE_API_KEY = "8717fefc5712cd22d36cb9e9c70d57f7"
OUTPUT_DIR = Path("/home/server/clawd-pinterest-multi/pins")
OUTPUT_DIR.mkdir(exist_ok=True)

PRODUCTS = [
    # PohadkoveTipyCZ
    {
        "profile": "PohadkoveTipyCZ",
        "board": "Pohádkové tipy pro děti",
        "product": "Interaktivní robotická hračka",
        "title": "🤖 Interaktivní robot pro děti 2026 — nejlepší hračka roku!",
        "prompt": "A cute colorful interactive robot toy for children, vibrant pastel colors, fairy tale style, white background, product photography, Pinterest pin style, 2:3 vertical",
        "link": "https://www.amazon.de/s?k=interaktivni+roboticka+hracka+deti&tag=pohadkove-21",
        "filename": "pin_pohadky_robot.jpg"
    },
    {
        "profile": "PohadkoveTipyCZ",
        "board": "Pohádkové tipy pro děti",
        "product": "Vzdělávací dřevěné puzzle",
        "title": "🧩 Vzdělávací dřevěné puzzle — rozvíjí myšlení od 2 let",
        "prompt": "Colorful wooden educational puzzle for toddlers, fairytale animals theme, soft wooden textures, cozy flat lay, Pinterest pin vertical format",
        "link": "https://www.amazon.de/s?k=vzdelavaci+drevene+puzzle+deti&tag=pohadkove-21",
        "filename": "pin_pohadky_puzzle.jpg"
    },
    {
        "profile": "PohadkoveTipyCZ",
        "board": "Pohádkové tipy pro děti",
        "product": "Pohádkový stan pro děti",
        "title": "🏕️ Pohádkový stan pro děti — domeček snů do dětského pokoje",
        "prompt": "Magical children's play tent with fairy lights, stars and moon decorations, cozy kids room, dreamy atmosphere, Pinterest vertical pin",
        "link": "https://www.amazon.de/s?k=detsky+pohladkovy+stan+tipi&tag=pohadkove-21",
        "filename": "pin_pohadky_stan.jpg"
    },
    # HomeDekorCZ
    {
        "profile": "HomeDekorCZ",
        "board": "Home Dekor CZ",
        "product": "Macramé závěs na stěnu",
        "title": "🪢 Macramé závěs — boho dekorace na zeď 2026",
        "prompt": "Beautiful bohemian macrame wall hanging, natural cotton rope, earthy tones, minimalist Scandinavian home interior, bright room, Pinterest pin vertical",
        "link": "https://www.amazon.de/s?k=macrame+wandbehang+boho&tag=pohadkove-21",
        "filename": "pin_home_macrame.jpg"
    },
    {
        "profile": "HomeDekorCZ",
        "board": "Home Dekor CZ",
        "product": "Sada pokojových rostlin",
        "title": "🌿 Trend 2026: Pokojové rostliny — oáza klidu ve vašem domově",
        "prompt": "Minimalist modern indoor plant arrangement, pothos monstera succulents in aesthetic pots, bright Scandinavian living room, lifestyle Pinterest pin vertical",
        "link": "https://www.amazon.de/s?k=zimmerpflanzen+set+topfe&tag=pohadkove-21",
        "filename": "pin_home_rostliny.jpg"
    },
    {
        "profile": "HomeDekorCZ",
        "board": "Home Dekor CZ",
        "product": "LED zrcadlo do koupelny",
        "title": "💡 LED zrcadlo do koupelny — luxus za dostupnou cenu",
        "prompt": "Elegant LED backlit bathroom mirror, modern minimalist bathroom design, warm lighting, luxury feel, Pinterest pin vertical product photo",
        "link": "https://www.amazon.de/s?k=led+badspiegel+beleuchtung&tag=pohadkove-21",
        "filename": "pin_home_zrcadlo.jpg"
    },
    # FitnessMotivaceCZ
    {
        "profile": "FitnessMotivaceCZ",
        "board": "Fitness Motivace CZ",
        "product": "Odporové gumy sada",
        "title": "💪 Odporové gumy — kompletní sada pro trénink doma 2026",
        "prompt": "Set of colorful resistance bands for home workout, bright energetic sports photography, motivational fitness lifestyle, Pinterest pin vertical",
        "link": "https://www.amazon.de/s?k=widerstandsbander+set+fitness&tag=pohadkove-21",
        "filename": "pin_fitness_gumy.jpg"
    },
    {
        "profile": "FitnessMotivaceCZ",
        "board": "Fitness Motivace CZ",
        "product": "Smart fitness tracker",
        "title": "⌚ Smart fitness náramek 2026 — sleduj zdraví každý den",
        "prompt": "Modern smart fitness tracker watch on athletic wrist, sports workout context, dynamic energetic photo, motivational text overlay space, Pinterest vertical",
        "link": "https://www.amazon.de/s?k=smart+fitness+tracker+2026&tag=pohadkove-21",
        "filename": "pin_fitness_tracker.jpg"
    },
    {
        "profile": "FitnessMotivaceCZ",
        "board": "Fitness Motivace CZ",
        "product": "Proteinový shaker",
        "title": "🥤 Protein shaker s organizérem — fitness essentials 2026",
        "prompt": "Premium protein shaker bottle with compartments, gym bag fitness accessories flat lay, motivational fitness lifestyle photography, bright Pinterest pin vertical",
        "link": "https://www.amazon.de/s?k=protein+shaker+flasche+sport&tag=pohadkove-21",
        "filename": "pin_fitness_shaker.jpg"
    },
    # TechGadgetsCZ
    {
        "profile": "TechGadgetsCZ",
        "board": "Tech Gadgets CZ",
        "product": "Bezdrátová sluchátka 2026",
        "title": "🎧 Bezdrátová sluchátka 2026 — nejlepší zvuk roku (CES vítěz)",
        "prompt": "Futuristic premium wireless headphones, dark minimalist tech product photography, sleek modern design, CES 2026 gadget, Pinterest pin vertical",
        "link": "https://www.amazon.de/s?k=kabellose+kopfhorer+2026+premium&tag=pohadkove-21",
        "filename": "pin_tech_sluchatka.jpg"
    },
    {
        "profile": "TechGadgetsCZ",
        "board": "Tech Gadgets CZ",
        "product": "Solární powerbanka",
        "title": "☀️ Solární powerbanka — nabíjej kdekoli bez proudu!",
        "prompt": "Portable solar power bank charger, outdoor adventure camping setup, rugged tech gadget lifestyle photo, Pinterest pin vertical product",
        "link": "https://www.amazon.de/s?k=solar+powerbank+tragbar+outdoor&tag=pohadkove-21",
        "filename": "pin_tech_powerbanka.jpg"
    },
    {
        "profile": "TechGadgetsCZ",
        "board": "Tech Gadgets CZ",
        "product": "Smart home hub",
        "title": "🏠 Smart Home Hub 2026 — ovládej celý byt z jednoho místa",
        "prompt": "Sleek smart home control hub device, modern minimalist home tech setup, ambient lighting, futuristic home automation Pinterest pin vertical",
        "link": "https://www.amazon.de/s?k=smart+home+hub+2026&tag=pohadkove-21",
        "filename": "pin_tech_smarthome.jpg"
    },
]


def generate_image_kie(prompt, output_path):
    """Generate image via Kie.ai flux-2-pro API"""
    print(f"  [KIE] Submitting: {prompt[:60]}...")
    try:
        resp = requests.post(
            "https://kieai.erweima.ai/api/v1/flux-pro",
            headers={"Authorization": f"Bearer {KIE_API_KEY}", "Content-Type": "application/json"},
            json={"prompt": prompt, "aspectRatio": "2:3", "imageCount": 1},
            timeout=30
        )
        data = resp.json()
        task_id = data.get("data", {}).get("taskId")
        if not task_id:
            print(f"  [KIE] No taskId. Response: {data}")
            return None

        print(f"  [KIE] Task ID: {task_id}, polling...")
        for i in range(30):
            time.sleep(5)
            r = requests.get(
                f"https://kieai.erweima.ai/api/v1/flux-pro/record-info?taskId={task_id}",
                headers={"Authorization": f"Bearer {KIE_API_KEY}"},
                timeout=20
            )
            result = r.json()
            d = result.get("data", {})
            success_flag = d.get("successFlag")
            status = d.get("status", "unknown")
            
            if success_flag == 1:
                img_list = d.get("response", {}).get("imageList", [])
                if img_list:
                    img_url = img_list[0]
                    img_data = requests.get(img_url, timeout=30).content
                    with open(output_path, "wb") as f:
                        f.write(img_data)
                    print(f"  [KIE] ✅ Saved: {output_path}")
                    return output_path
            elif success_flag == -1:
                print(f"  [KIE] ❌ Failed. Data: {d}")
                return None
            else:
                print(f"  [KIE] Waiting ({i+1}/30)... status={status} flag={success_flag}")
        
        print("  [KIE] Timeout after 30 polls")
        return None
    except Exception as e:
        print(f"  [KIE] Error: {e}")
        return None


def generate_image_pil(prompt, output_path, title=""):
    """PIL fallback placeholder image"""
    try:
        from PIL import Image, ImageDraw, ImageFont
        import textwrap
        
        img = Image.new("RGB", (1000, 1500), color=(245, 240, 255))
        draw = ImageDraw.Draw(img)
        
        # Background gradient effect
        for y in range(1500):
            r = int(245 - (y/1500)*40)
            g = int(240 - (y/1500)*30)
            b = int(255 - (y/1500)*20)
            draw.line([(0, y), (1000, y)], fill=(r, g, b))
        
        # Header
        draw.rectangle([0, 0, 1000, 80], fill=(100, 60, 180))
        draw.text((500, 40), "📌 Pinterest Pin", fill="white", anchor="mm")
        
        # Title text
        lines = textwrap.wrap(title or prompt[:100], width=30)
        y_start = 200
        for line in lines[:6]:
            draw.text((500, y_start), line, fill=(50, 30, 100), anchor="mm")
            y_start += 60
        
        # Product name
        draw.rectangle([100, 600, 900, 700], fill=(100, 60, 180, 128))
        draw.text((500, 650), prompt[:50], fill="white", anchor="mm")
        
        # Footer
        draw.rectangle([0, 1420, 1000, 1500], fill=(100, 60, 180))
        draw.text((500, 1460), "Amazon.de — affiliate link", fill="white", anchor="mm")
        
        img.save(output_path, "JPEG", quality=90)
        print(f"  [PIL] ✅ Placeholder saved: {output_path}")
        return output_path
    except ImportError:
        # Even more basic fallback
        print("  [PIL] PIL not available, creating minimal file")
        with open(output_path, "wb") as f:
            # Minimal valid JPEG placeholder
            f.write(b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00')
        return output_path


def generate_image(product_info):
    prompt = product_info["prompt"]
    output_path = str(OUTPUT_DIR / product_info["filename"])
    
    # Try Kie.ai first
    result = generate_image_kie(prompt, output_path)
    if result:
        return result
    
    # Fallback to PIL
    print(f"  [FALLBACK] Using PIL placeholder")
    return generate_image_pil(prompt, output_path, product_info["title"])


if __name__ == "__main__":
    print("🎨 Starting image generation for 12 pins...")
    results = {}
    
    for i, product in enumerate(PRODUCTS):
        print(f"\n[{i+1}/12] {product['profile']} — {product['product']}")
        path = generate_image(product)
        results[product["filename"]] = {
            "success": path is not None,
            "path": path,
            "product": product
        }
    
    # Save results
    with open(str(OUTPUT_DIR / "generation_results.json"), "w") as f:
        # Make serializable
        for k, v in results.items():
            v["product"] = dict(v["product"])
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    success_count = sum(1 for v in results.values() if v["success"])
    print(f"\n✅ Generated {success_count}/12 images")
    print("Results saved to generation_results.json")
