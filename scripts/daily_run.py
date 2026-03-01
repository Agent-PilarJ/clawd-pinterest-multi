#!/usr/bin/env python3
"""
Daily runner — AliExpress Affiliate Pinterest Automation pro @PohadkoveTipyCZ

Spouštěno cron jobem každý den v 5:00 (nebo 8:00 pro lepší engagement).
Hledá produkty na AliExpress, generuje affiliate linky a pinuje na Pinterest.

Použití:
  python3 daily_run.py              # normální běh
  python3 daily_run.py --dry-run    # simulace bez postování
  python3 daily_run.py --keyword "puzzle pro děti"  # test jednoho keywordu
"""

import argparse
import json
import logging
import os
import sys
import time
import smtplib
import ssl
from datetime import datetime, date
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Dict, List, Optional

# Přidej scripts/ do path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aliexpress_api import search_products, generate_affiliate_link, download_image
from pinterest_poster import post_pin

# ── Konfigurace ────────────────────────────────────────────────────────────────

WORKSPACE = Path("/home/server/clawd-pinterest-multi")
DATA_DIR = WORKSPACE / "data"
MEDIA_DIR = Path("/home/server/media-data/pinterest/pohadkovetipycz")
CONFIG_FILE = DATA_DIR / "config.json"
PIN_LOG_FILE = DATA_DIR / "pin-log.json"
ENV_FILE = Path("~/.clawdbot/.env").expanduser()

# Keywords pro @PohadkoveTipyCZ niche (hračky, pohádky, děti)
DEFAULT_KEYWORDS = [
    "pohádková hračka",
    "dřevené hračky děti",
    "puzzle pro děti",
    "pohádkové kostýmy",
    "vzdělávací hračky",
    "fairy tale toys",
    "children puzzle",
    "kids educational toy",
    "princess dress up",
    "castle playhouse kids",
    "dětský stan hradní",
]

# ── Logging ────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(WORKSPACE / "memory" / f"daily-{date.today()}.log", mode="a"),
    ],
)
logger = logging.getLogger("daily_run")


# ── Helpers ────────────────────────────────────────────────────────────────────

def load_env() -> Dict[str, str]:
    """Načte .env soubor do slovníku."""
    env = {}
    try:
        with open(ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()
    except FileNotFoundError:
        logger.warning(f"ENV soubor nenalezen: {ENV_FILE}")
    return env


def load_config() -> Dict:
    """Načte config.json."""
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"Config nenalezen: {CONFIG_FILE}, používám výchozí")
        return {"profiles": []}


def load_pin_log() -> List[Dict]:
    """Načte log pinů."""
    try:
        with open(PIN_LOG_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_pin_log(log: List[Dict]):
    """Uloží log pinů."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(PIN_LOG_FILE, "w") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)


def already_pinned_today(product_id: str, log: List[Dict]) -> bool:
    """Zjistí, jestli byl produkt dnes už pinnován."""
    today = date.today().isoformat()
    return any(
        entry.get("product_id") == product_id and entry.get("date", "")[:10] == today
        for entry in log
    )


def count_pins_today(log: List[Dict]) -> int:
    """Počet pinů zveřejněných dnes."""
    today = date.today().isoformat()
    return sum(1 for e in log if e.get("date", "")[:10] == today and e.get("success"))


def send_report_email(subject: str, body: str, env: Dict):
    """Pošle report emailem přes SMTP."""
    try:
        smtp_host = env.get("SMTP_HOST", "")
        smtp_port = int(env.get("SMTP_PORT", 465))
        smtp_user = env.get("SMTP_USER", "")
        smtp_pass = env.get("SMTP_PASSWORD", "")
        smtp_from = env.get("SMTP_FROM", smtp_user)

        if not smtp_host or not smtp_user:
            logger.warning("SMTP není nakonfigurován, přeskakuji report")
            return

        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = smtp_from
        msg["To"] = smtp_user

        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context) as server:
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_from, [smtp_user], msg.as_string())
        logger.info(f"Report odeslán na {smtp_user}")
    except Exception as e:
        logger.error(f"Chyba při odesílání reportu: {e}")


def build_pin_title(product: Dict, keyword: str) -> str:
    """Sestaví titulek pinu z dat produktu."""
    title = product.get("product_title", "")
    if title and len(title) > 10:
        # Zkrať na 100 znaků
        return title[:97] + "..." if len(title) > 100 else title
    return f"{keyword.title()} — Skvělá cena na AliExpress"


def get_product_image_path(product_id: str) -> Path:
    """Vrátí cestu pro obrázek produktu."""
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    return MEDIA_DIR / f"product-{product_id}.jpg"


# ── Hlavní logika ──────────────────────────────────────────────────────────────

def run_for_profile(
    profile: Dict,
    env: Dict,
    pin_log: List[Dict],
    dry_run: bool = False,
) -> List[Dict]:
    """Spustí denní rutinu pro jeden Pinterest profil."""
    profile_id = profile.get("id", "unknown")
    board = profile.get("board", "Pohádkové tipy pro děti")
    max_pins = profile.get("max_pins_daily", 5)
    keywords = profile.get("keywords", DEFAULT_KEYWORDS)

    logger.info(f"▶ Profil: {profile.get('pinterest_username')} (board: {board})")
    logger.info(f"  Keywords: {keywords}")

    pinned_today = count_pins_today(pin_log)
    logger.info(f"  Piny dnes: {pinned_today}/{max_pins}")

    results = []

    for keyword in keywords:
        if pinned_today >= max_pins:
            logger.info(f"  Dosažen denní limit ({max_pins}), končím")
            break

        logger.info(f"\n🔍 Hledám: '{keyword}'")
        products = search_products(keyword, page_size=10, category_ids="6,1511", dry_run=dry_run)

        if not products:
            logger.warning(f"  Žádné produkty pro '{keyword}'")
            continue

        # Vyber top 1-2 produkty (nejlevnější — API vrátí seřazené SALE_PRICE_ASC)
        for product in products[:2]:
            if pinned_today >= max_pins:
                break

            product_id = str(product.get("product_id", ""))
            product_url = product.get("product_detail_url", "")
            image_url = product.get("product_main_image_url", "")
            price = product.get("target_sale_price", "?")
            title = build_pin_title(product, keyword)

            if not product_url:
                logger.warning(f"  Produkt {product_id} nemá URL, přeskakuji")
                continue

            if already_pinned_today(product_id, pin_log):
                logger.info(f"  Produkt {product_id} už byl pinován dnes, přeskakuji")
                continue

            logger.info(f"\n  📦 Produkt: {title[:60]}")
            logger.info(f"     Cena: {price} CZK | ID: {product_id}")

            # Generuj affiliate link
            aff_link = generate_affiliate_link(product_url, dry_run=dry_run)
            if not aff_link:
                logger.warning(f"  Nepodařilo se vygenerovat affiliate link, používám přímý URL")
                aff_link = product_url

            # Stáhni obrázek
            image_path = get_product_image_path(product_id)
            img_ok = False
            if image_url:
                img_ok = download_image(image_url, str(image_path), dry_run=dry_run)
            
            if not img_ok or not image_path.exists():
                logger.warning(f"  Obrázek nedostupný, přeskakuji produkt")
                continue

            # Postni pin
            logger.info(f"  📌 Pinuji: '{title[:50]}' → {aff_link[:60]}")
            success = post_pin(
                image_path=str(image_path),
                title=title,
                link=aff_link,
                board=board,
                dry_run=dry_run,
            )

            entry = {
                "date": datetime.now().isoformat(),
                "profile": profile_id,
                "keyword": keyword,
                "product_id": product_id,
                "product_title": title,
                "price_czk": str(price),
                "affiliate_link": aff_link,
                "image_path": str(image_path),
                "board": board,
                "success": success,
                "dry_run": dry_run,
            }
            pin_log.append(entry)
            results.append(entry)

            if success:
                pinned_today += 1
                logger.info(f"  ✅ Pin zveřejněn! ({pinned_today}/{max_pins})")
                time.sleep(5)  # Krátká pauza mezi piny
            else:
                logger.error(f"  ❌ Pin se nepodařilo zveřejnit")

    return results


def build_report(
    results: List[Dict],
    pin_log: List[Dict],
    dry_run: bool,
) -> str:
    """Sestaví textový report."""
    today = date.today().isoformat()
    today_pins = [e for e in pin_log if e.get("date", "")[:10] == today]
    success_pins = [e for e in today_pins if e.get("success")]

    lines = [
        f"📌 Pinterest Affiliate Report — {today}",
        f"{'[DRY-RUN MODE]' if dry_run else ''}",
        "",
        f"✅ Zveřejněno dnes: {len(success_pins)} pinů",
        f"📊 Celkem naplánováno: {len(results)}",
        "",
        "📦 Pinované produkty:",
    ]

    for e in today_pins:
        status = "✅" if e.get("success") else "❌"
        lines.append(
            f"  {status} [{e.get('keyword', '')}] {e.get('product_title', '')[:50]}"
            f" — {e.get('price_czk', '?')} CZK"
        )

    lines += [
        "",
        "🔗 Affiliate linky jsou přítomny ve všech pinech",
        f"💾 Log uložen: {PIN_LOG_FILE}",
    ]

    return "\n".join(lines)


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="AliExpress Pinterest Daily Runner")
    parser.add_argument("--dry-run", action="store_true", help="Simulace bez skutečného postování")
    parser.add_argument("--keyword", help="Testuj jen jeden keyword")
    parser.add_argument("--profile", help="ID profilu (výchozí: pohadkovetipycz)")
    args = parser.parse_args()

    dry_run = args.dry_run
    if dry_run:
        logger.info("🧪 DRY-RUN MODE — žádné skutečné piny nebudou zveřejněny")

    # Zajisti log adresář
    (WORKSPACE / "memory").mkdir(parents=True, exist_ok=True)

    # Načti prostředí a konfiguraci
    env = load_env()
    config = load_config()
    pin_log = load_pin_log()

    # Vyber profil(y)
    profiles = config.get("profiles", [])
    if not profiles:
        # Výchozí profil
        profiles = [{
            "id": "pohadkovetipycz",
            "pinterest_username": "@PohadkoveTipyCZ",
            "board": "Pohádkové tipy pro děti",
            "niche": "toys_fairytale",
            "keywords": DEFAULT_KEYWORDS,
            "affiliate": "aliexpress",
            "max_pins_daily": 5,
            "active": True,
        }]

    if args.profile:
        profiles = [p for p in profiles if p.get("id") == args.profile]
        if not profiles:
            logger.error(f"Profil '{args.profile}' nenalezen")
            sys.exit(1)

    # Pokud je zadán --keyword, testuj jen ten
    if args.keyword:
        for profile in profiles:
            profile["keywords"] = [args.keyword]

    all_results = []
    for profile in profiles:
        if not profile.get("active", True):
            logger.info(f"Profil {profile.get('id')} je neaktivní, přeskakuji")
            continue

        results = run_for_profile(profile, env, pin_log, dry_run=dry_run)
        all_results.extend(results)

    # Ulož log
    save_pin_log(pin_log)
    logger.info(f"📝 Log uložen: {PIN_LOG_FILE} ({len(pin_log)} záznamů)")

    # Report
    report = build_report(all_results, pin_log, dry_run)
    print("\n" + "="*60)
    print(report)
    print("="*60)

    # Pošli report emailem
    subject = f"{'[DRY-RUN] ' if dry_run else ''}Pinterest Report {date.today().isoformat()}"
    send_report_email(subject, report, env)

    success_count = sum(1 for r in all_results if r.get("success"))
    logger.info(f"\n🏁 Hotovo! Zveřejněno: {success_count}/{len(all_results)} pinů")
    return 0 if success_count > 0 or dry_run else 1


if __name__ == "__main__":
    sys.exit(main())
