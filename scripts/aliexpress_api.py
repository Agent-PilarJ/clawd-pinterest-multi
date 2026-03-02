#!/usr/bin/env python3
"""
AliExpress Affiliate API module.
Hledá produkty a generuje affiliate linky pro AliExpress Portals.
"""

import hashlib
import time
import os
import requests
import json
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# Kategorie dětských produktů pro filtraci
# Viz AliExpress kategorie: https://portals.aliexpress.com
ALLOWED_CATEGORY_IDS = [
    "6",      # Toys & Hobbies
    "1511",   # Mother & Kids
    "36",     # Baby & Kids Fashion
    "4",      # Sports & Entertainment (pro děti)
    "15",     # Luggage & Bags - NE, ale ponecháme jen dětské
]

# Klíčová slova pro filtraci nerelevantních produktů (blacklist)
PRODUCT_BLACKLIST_KEYWORDS = [
    # Tech / phone
    "phone case", "iphone", "samsung", "phone holder", "screen protector",
    "usb hub", "laptop", "keyboard", "mouse pad", "earphone", "headphone",
    # Auto
    "car sticker", "car accessories", "steering wheel", "rearview mirror",
    "tire valve", "valve cap", "wheel cap", "car wheel",
    # Módní doplňky pro dospělé (jen jednoznačně nepatřičné)
    "bag organizer", "handbag", "purse", "wallet",
    "women bag", "women\'s bag", "loewe",
    "organizer insert", "luggage tag",
    # Dámská móda pro dospělé
    "lingerie", "bra ", "underwear",
    # Jiné nerelevantní
    "nail art", "false nail", "wig", "hair extension", "eyelash",
    "sex toy", "adult toy",
    # Obsahuje "bag" + "women" nebo "lady" v titulku → filtruj v kódu
]

# Kombinace slov pro filtraci (oba výrazy musí být v titulku)
PRODUCT_BLACKLIST_COMBOS = [
    ("shoulder bag", "women"),
    ("shoulder bag", "lady"),
    ("leather bag", "women"),
    ("leather bag", "lady"),
    ("faux leather", "bag"),
    ("braided", "bag"),
    ("tote", "women"),
    ("crossbody", "women"),
    ("clutch", "women"),
]

# Minimální skóre relevance (podíl slov z dotazu v názvu produktu)
MIN_RELEVANCE_SCORE = 0.0  # 0 = nepřísné, zvýšit na 0.3 pro přísnější filtr


def _load_credentials() -> tuple[str, str, str]:
    """Načte credentials z .env souboru."""
    env_path = os.path.expanduser("~/.clawdbot/.env")
    app_key = ""
    app_secret = ""
    tracking_id = "default"
    try:
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("ALIEXPRESS_APP_KEY="):
                    app_key = line.split("=", 1)[1]
                elif line.startswith("ALIEXPRESS_APP_SECRET="):
                    app_secret = line.split("=", 1)[1]
                elif line.startswith("ALIEXPRESS_TRACKING_ID="):
                    tracking_id = line.split("=", 1)[1]
    except FileNotFoundError:
        pass
    app_key = os.environ.get("ALIEXPRESS_APP_KEY", app_key)
    app_secret = os.environ.get("ALIEXPRESS_APP_SECRET", app_secret)
    tracking_id = os.environ.get("ALIEXPRESS_TRACKING_ID", tracking_id)
    return app_key, app_secret, tracking_id


def _sign_params(params: Dict[str, str], app_secret: str) -> str:
    """Generuje MD5 podpis pro AliExpress API."""
    sorted_params = sorted(params.items())
    sign_str = app_secret + "".join(f"{k}{v}" for k, v in sorted_params) + app_secret
    return hashlib.md5(sign_str.encode("utf-8")).hexdigest().upper()


def _is_relevant_product(product: Dict[str, Any], keyword: str) -> bool:
    """
    Filtruje produkt podle relevance.
    Vrátí True pokud je produkt relevantní pro dětský Pinterest profil.
    """
    title = (product.get("product_title") or "").lower()

    # Blacklist check — jednoduchá klíčová slova
    for bad_kw in PRODUCT_BLACKLIST_KEYWORDS:
        if bad_kw.lower() in title:
            logger.debug(f"Filtrováno (blacklist '{bad_kw}'): {title[:60]}")
            return False

    # Blacklist combos — oba výrazy musí být v titulku
    for (kw1, kw2) in PRODUCT_BLACKLIST_COMBOS:
        if kw1.lower() in title and kw2.lower() in title:
            logger.debug(f"Filtrováno (combo '{kw1}'+'{kw2}'): {title[:60]}")
            return False

    return True


def generate_affiliate_link(
    original_url: str,
    tracking_id: str = "default",
    dry_run: bool = False,
) -> Optional[str]:
    """Vygeneruje AliExpress affiliate link pro danou URL."""
    if dry_run:
        logger.info(f"[DRY-RUN] generate_affiliate_link({original_url})")
        return f"https://s.click.aliexpress.com/dry-run-link?url={original_url}"

    app_key, app_secret, env_tracking_id = _load_credentials()
    if not app_key or not app_secret:
        logger.error("Chybí ALIEXPRESS_APP_KEY nebo ALIEXPRESS_APP_SECRET")
        return None
    # Použij tracking_id z env pokud není explicitně zadán jiný
    if tracking_id == "default":
        tracking_id = env_tracking_id

    params = {
        "method": "aliexpress.affiliate.link.generate",
        "app_key": app_key,
        "timestamp": str(int(time.time() * 1000)),
        "sign_method": "md5",
        "format": "json",
        "v": "2.0",
        "promotion_link_type": "0",
        "source_values": original_url,
        "tracking_id": tracking_id,
    }
    params["sign"] = _sign_params(params, app_secret)

    try:
        resp = requests.post(
            "https://api-sg.aliexpress.com/sync",
            data=params,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        logger.debug(f"affiliate link response: {json.dumps(data)[:500]}")

        result = data.get("aliexpress_affiliate_link_generate_response", {})
        result = result.get("resp_result", {})
        result = result.get("result", {})
        links = result.get("promotion_links", {}).get("promotion_link", [])
        if links:
            return links[0].get("promotion_link")
        # Fallback: return original URL with basic tracking
        logger.warning(f"Žádný affiliate link v odpovědi, používám fallback: {data}")
        return original_url
    except Exception as e:
        logger.error(f"Chyba při generování affiliate linku: {e}")
    return original_url  # fallback


def search_products(
    keyword: str,
    page_size: int = 10,
    category_ids: Optional[str] = None,
    dry_run: bool = False,
) -> List[Dict[str, Any]]:
    """
    Hledá produkty na AliExpress pro daný keyword.
    Aplikuje filtraci nerelevantních produktů.

    Args:
        keyword: Hledaný výraz
        page_size: Počet výsledků k načtení (víc = lepší šance po filtraci)
        category_ids: Čárkou oddělená ID kategorií (např. "6,1511" pro hračky+děti)
        dry_run: Testovací mód

    Vrací seznam produktů s klíči:
      - product_id
      - product_title
      - target_sale_price (CZK)
      - product_main_image_url
      - product_detail_url
      - evaluate_rate (hodnocení)
      - lastest_volume (prodeje)
    """
    if dry_run:
        logger.info(f"[DRY-RUN] search_products('{keyword}')")
        return [
            {
                "product_id": f"dry-run-{keyword[:8].replace(chr(32), chr(45))}-{i}",
                "product_title": f"[DRY-RUN] {keyword} Produkt {i+1}",
                "target_sale_price": f"{(i+1)*99:.2f}",
                "target_sale_price_currency": "CZK",
                "product_main_image_url": "https://via.placeholder.com/500x500.jpg",
                "product_detail_url": f"https://www.aliexpress.com/item/{1000000000+i}.html",
                "evaluate_rate": "95%",
                "lastest_volume": 1000,
            }
            for i in range(min(page_size, 3))
        ]

    app_key, app_secret, _ = _load_credentials()
    if not app_key or not app_secret:
        logger.error("Chybí ALIEXPRESS_APP_KEY nebo ALIEXPRESS_APP_SECRET")
        return []

    params = {
        "method": "aliexpress.affiliate.product.query",
        "app_key": app_key,
        "timestamp": str(int(time.time() * 1000)),
        "sign_method": "md5",
        "format": "json",
        "v": "2.0",
        "keywords": keyword,
        "page_size": str(page_size),
        "page_no": "1",
        "sort": "SALE_PRICE_ASC",
        "target_currency": "CZK",
        "target_language": "CS",
        "ship_to_country": "CZ",
    }

    # Přidat category_ids filtr pokud je zadán
    if category_ids:
        params["category_ids"] = category_ids
        logger.info(f"Filtrování podle kategorií: {category_ids}")

    params["sign"] = _sign_params(params, app_secret)

    try:
        resp = requests.post(
            "https://api-sg.aliexpress.com/sync",
            data=params,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        logger.debug(f"search_products response: {json.dumps(data)[:800]}")

        result = data.get("aliexpress_affiliate_product_query_response", {})
        result = result.get("resp_result", {})

        if result.get("resp_code") not in (200, None) and "result" not in result:
            logger.warning(f"API chyba: {result.get('resp_msg')} (kód {result.get('resp_code')})")
            logger.debug(f"Full response: {json.dumps(data)}")
            return []

        products = result.get("result", {}).get("products", {}).get("product", [])
        logger.info(f"Nalezeno {len(products)} produktů pro '{keyword}' (před filtrací)")

        # Aplikuj filtraci relevance
        filtered = [p for p in products if _is_relevant_product(p, keyword)]
        if len(filtered) < len(products):
            logger.info(f"Po filtraci: {len(filtered)} produktů (odfiltrováno {len(products)-len(filtered)})")

        return filtered

    except Exception as e:
        logger.error(f"Chyba při vyhledávání produktů: {e}")
    return []


def download_image(url: str, dest_path: str, dry_run: bool = False) -> bool:
    """Stáhne obrázek z URL do dest_path."""
    if dry_run:
        logger.info(f"[DRY-RUN] download_image({url} → {dest_path})")
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        with open(dest_path, "wb") as f:
            f.write(b"DRY-RUN-PLACEHOLDER")
        return True
    try:
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        resp = requests.get(url, timeout=20, stream=True)
        resp.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        logger.info(f"Stažen obrázek: {dest_path}")
        return True
    except Exception as e:
        logger.error(f"Chyba při stahování obrázku {url}: {e}")
        return False


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.DEBUG)

    dry = "--dry-run" in sys.argv
    keyword = next((a for a in sys.argv[1:] if not a.startswith("-")), "puzzle pro děti")

    print(f"\n=== Test: search_products('{keyword}') s category_ids=6,1511 ===")
    products = search_products(keyword, page_size=10, category_ids="6,1511,100003070", dry_run=dry)
    for p in products:
        print(f"  [{p.get('product_id')}] {p.get('product_title', '')[:60]}")
        print(f"    Cena: {p.get('target_sale_price')} | URL: {p.get('product_detail_url', '')[:70]}")

    if products:
        print(f"\n=== Test: generate_affiliate_link (tracking_id=default) ===")
        url = products[0].get("product_detail_url", "https://www.aliexpress.com/item/1234567890.html")
        aff_link = generate_affiliate_link(url, tracking_id="default", dry_run=dry)
        print(f"  Affiliate link: {aff_link}")
