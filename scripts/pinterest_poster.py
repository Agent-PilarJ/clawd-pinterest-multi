#!/usr/bin/env python3
"""
Pinterest Poster — postuje piny přes chrome-devtools MCP (mcporter).
Používá izolovaný kontext 'pinterest-agent' v chrome-devtools profilu.
NIKDY nepoužívat Playwright (způsobuje hromadění draftů a selhání).
Fix 2026-03-03: opravena detekce session (CZ UI), izolovaný kontext, fallback selektory.
"""

import subprocess
import logging
import time
import json
import re
import os
from pathlib import Path

logger = logging.getLogger(__name__)

PIN_BUILDER_URL = "https://www.pinterest.com/pin-creation-tool/"
LOGIN_URL = "https://www.pinterest.com/login/"
ISOLATED_CONTEXT = "pinterest-agent"


def _mcporter(tool: str, args: dict, timeout: int = 30) -> str:
    """Zavolá mcporter tool a vrátí stdout."""
    cmd = ["mcporter", "call", f"chrome-devtools.{tool}", "--args", json.dumps(args)]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        logger.error(f"mcporter timeout: {tool}")
        return ""


def _snapshot() -> str:
    return _mcporter("take_snapshot", {})


def _find_uid(snapshot: str, pattern: str) -> str | None:
    """Najde první uid řádek obsahující pattern."""
    for line in snapshot.splitlines():
        if pattern.lower() in line.lower():
            m = re.search(r'uid=(\S+)', line)
            if m:
                return m.group(1)
    return None


def _load_env():
    env_path = Path.home() / ".clawdbot" / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip())


def _ensure_pinterest_tab() -> bool:
    """
    Zajistí, že existuje záložka s isolatedContext=pinterest-agent a přepne na ni.
    """
    pages_out = _mcporter("list_pages", {})
    
    # Zjisti, jestli pinterest-agent tab existuje
    if "pinterest-agent" in pages_out:
        # Najdi pageId
        for line in pages_out.splitlines():
            if "pinterest-agent" in line:
                m = re.search(r'pageId[=:]?\s*(\d+)|^(\d+):', line)
                if not m:
                    # zkus najít číslo na začátku řádku
                    m2 = re.match(r'\s*(\d+)[:\s]', line)
                    if m2:
                        page_id = int(m2.group(1))
                        _mcporter("select_page", {"pageId": page_id})
                        logger.info(f"Přepnuto na pinterest-agent tab (pageId={page_id})")
                        return True
        # Fallback — tab existuje, přepni přes navigaci (not ideal)
        return True
    else:
        # Vytvoř novou záložku
        logger.info("Vytvářím novou pinterest-agent záložku...")
        result = _mcporter("new_page", {"url": "about:blank", "background": False, "isolatedContext": ISOLATED_CONTEXT})
        logger.debug(f"new_page result: {result[:200]}")
        return True


def _get_pinterest_page_id() -> int | None:
    """Vrátí pageId pinterest-agent záložky."""
    pages_out = _mcporter("list_pages", {})
    for line in pages_out.splitlines():
        if "pinterest-agent" in line:
            m = re.match(r'\s*(\d+)[:\s]', line)
            if m:
                return int(m.group(1))
    return None


def ensure_pinterest_session() -> bool:
    """
    Ensure we are logged into Pinterest (izolovaný kontext pinterest-agent).
    Detekuje CZ i EN Pinterest UI.
    """
    _load_env()
    email = os.environ.get("PINTEREST_EMAIL", "").strip()
    password = os.environ.get("PINTEREST_PASSWORD", "").strip()

    if not email or not password:
        logger.error("❌ PINTEREST_EMAIL / PINTEREST_PASSWORD not set in ~/.clawdbot/.env")
        return False

    # Zajisti záložku
    _ensure_pinterest_tab()
    time.sleep(1)

    # Naviguj na Pinterest homepage
    logger.info("🔐 Kontroluji Pinterest session...")
    _mcporter("navigate_page", {"type": "url", "url": "https://www.pinterest.com"})
    time.sleep(3)
    snap = _snapshot()

    # Detekce přihlášení: účet je přítomen, nebo není login/přihlásit tlačítko
    logged_in_signals = [
        "Pohádkové Tipy CZ" in snap,
        "pohadkovetipycz" in snap.lower(),
        "PohadkoveTipyCZ" in snap,
        "business/hub" in snap,
        "Your profile" in snap,
    ]
    
    not_logged_in_signals = [
        "Přihlásit se" in snap and "Registrace" in snap,
        "Log in" in snap and "Sign up" in snap,
    ]
    
    is_logged_in = any(logged_in_signals) and not any(not_logged_in_signals)

    if is_logged_in:
        logger.info("✅ Pinterest already logged in")
        return True

    logger.info("🔑 Pinterest not logged in — přihlašuji se...")

    # Naviguj na login stránku
    _mcporter("navigate_page", {"type": "url", "url": LOGIN_URL})
    time.sleep(3)
    snap = _snapshot()

    # Najdi email field — CZ Pinterest: "E-mail E-mail" nebo "textbox"
    email_uid = None
    for pattern in ["textbox \"E-mail", "textbox \"Email", "E-mail"]:
        email_uid = _find_uid(snap, pattern)
        if email_uid:
            break
    if not email_uid:
        # Fallback: první textbox
        for line in snap.splitlines():
            if "textbox" in line and "heslo" not in line.lower() and "password" not in line.lower():
                m = re.search(r'uid=(\S+)', line)
                if m:
                    email_uid = m.group(1)
                    break

    if email_uid:
        _mcporter("fill", {"uid": email_uid, "value": email})
        time.sleep(0.5)
    else:
        logger.error("❌ Email field not found na login stránce")
        logger.debug(f"Snapshot: {snap[:500]}")
        return False

    # Najdi password field — CZ: "Heslo", EN: "Password"
    pw_uid = _find_uid(snap, "Heslo")
    if not pw_uid:
        pw_uid = _find_uid(snap, "password")
    if not pw_uid:
        for line in snap.splitlines():
            if "textbox" in line and ("heslo" in line.lower() or "password" in line.lower()):
                m = re.search(r'uid=(\S+)', line)
                if m:
                    pw_uid = m.group(1)
                    break

    if pw_uid:
        _mcporter("fill", {"uid": pw_uid, "value": password})
        time.sleep(0.5)
    else:
        logger.warning("⚠️  Password field nenalezen")

    # Klikni Login button — CZ: "Přihlásit se", EN: "Log in"
    login_uid = _find_uid(snap, "Přihlásit se")
    if not login_uid:
        login_uid = _find_uid(snap, "Log in")
    if login_uid:
        _mcporter("click", {"uid": login_uid})
        time.sleep(5)
    else:
        logger.warning("⚠️  Login button nenalezen, zkouším Enter")
        _mcporter("evaluate_script", {"function": "function(){document.querySelector('form button[type=submit]')?.click()}"})
        time.sleep(5)

    # Ověř přihlášení
    snap3 = _snapshot()
    if any([
        "Pohádkové Tipy CZ" in snap3,
        "pohadkovetipycz" in snap3.lower(),
        "business/hub" in snap3,
        "Your profile" in snap3,
    ]):
        logger.info("✅ Pinterest login successful")
        return True

    logger.warning("⚠️  Pinterest login may have failed")
    logger.debug(f"Snapshot po loginu: {snap3[:500]}")
    return False


def _delete_drafts_if_needed() -> bool:
    """Smaže všechny drafty pokud je limit dosažen."""
    snap = _snapshot()
    if "50 drafts" not in snap and "limit of 50" not in snap:
        return False

    logger.warning("Limit 50 draftů dosažen — mažu drafty!")
    # Vyber všechny checkboxy
    _mcporter("evaluate_script", {"function": "function(){var cbs=document.querySelectorAll('input[type=checkbox]');cbs.forEach(function(cb){if(!cb.checked)cb.click();});return cbs.length}"})
    time.sleep(1)

    snap = _snapshot()
    del_uid = _find_uid(snap, "Delete Pins")
    if del_uid:
        _mcporter("click", {"uid": del_uid})
        time.sleep(2)
        snap = _snapshot()
        confirm_uid = _find_uid(snap, "Delete")
        if confirm_uid:
            _mcporter("click", {"uid": confirm_uid})
            time.sleep(3)
            logger.info("Drafty smazány")
            return True
    return False


def post_pin(
    image_path: str,
    title: str,
    link: str,
    board: str = "České pohádky pro děti",
    dry_run: bool = False,
) -> bool:
    """
    Postne pin na Pinterest přes chrome-devtools MCP.
    """
    if dry_run:
        logger.info(f"[DRY-RUN] post_pin: '{title[:50]}' → {link[:60]}")
        logger.info(f"[DRY-RUN] image: {image_path}")
        logger.info(f"[DRY-RUN] board: {board}")
        return True

    # Ensure Pinterest session first
    if not ensure_pinterest_session():
        logger.error("❌ Nepodařilo se přihlásit na Pinterest")
        return False

    # Naviguj na pin creation
    logger.info(f"Naviguju na {PIN_BUILDER_URL}")
    _mcporter("navigate_page", {"type": "url", "url": PIN_BUILDER_URL})
    time.sleep(4)

    snap = _snapshot()

    # Zkontroluj draft limit
    if "limit of 50" in snap or "50 drafts" in snap:
        _delete_drafts_if_needed()
        time.sleep(2)
        _mcporter("navigate_page", {"type": "url", "url": PIN_BUILDER_URL})
        time.sleep(4)
        snap = _snapshot()

    # Najdi File Upload button — fallback selektory pro případ změny Pinterest UI
    upload_uid = None
    for pattern in ["File Upload", "file upload", "Upload", "Choose a file", "drag and drop", "Soubor"]:
        upload_uid = _find_uid(snap, pattern)
        if upload_uid:
            logger.info(f"Upload button nalezen přes pattern: '{pattern}' (uid={upload_uid})")
            break
    
    # Ještě fallback: button s file input atributy
    if not upload_uid:
        for line in snap.splitlines():
            if "button" in line and ("upload" in line.lower() or "file" in line.lower() or "soubor" in line.lower()):
                m = re.search(r'uid=(\S+)', line)
                if m:
                    upload_uid = m.group(1)
                    logger.info(f"Upload button nalezen fallbackem (uid={upload_uid})")
                    break

    if not upload_uid:
        logger.error("❌ File Upload button nenalezen")
        logger.debug(f"Snapshot (první 1000 znaků): {snap[:1000]}")
        return False

    # Upload obrázku
    logger.info(f"Uploaduji obrázek: {image_path}")
    _mcporter("upload_file", {"uid": upload_uid, "filePath": image_path})
    time.sleep(7)  # Pinterest potřebuje čas na zpracování

    snap = _snapshot()

    # Vyplň titulek — různé varianty selektoru
    title_uid = None
    for pattern in ['textbox "Title"', "Title"]:
        title_uid = _find_uid(snap, pattern)
        if title_uid:
            break
    if not title_uid:
        for line in snap.splitlines():
            if "textbox" in line and "Title" in line and "disabled" not in line:
                m = re.search(r'uid=(\S+)', line)
                if m:
                    title_uid = m.group(1)
                    break

    if title_uid:
        logger.info(f"Vyplňuji titulek: {title[:50]}")
        _mcporter("fill", {"uid": title_uid, "value": title[:100]})
        time.sleep(0.5)
    else:
        logger.warning("⚠️  Title input nenalezen")

    # Vyplň link
    link_uid = None
    for pattern in ['textbox "Link"', "Link"]:
        link_uid = _find_uid(snap, pattern)
        if link_uid:
            break
    if not link_uid:
        for line in snap.splitlines():
            if "textbox" in line and "Link" in line and "disabled" not in line:
                m = re.search(r'uid=(\S+)', line)
                if m:
                    link_uid = m.group(1)
                    break

    if link_uid:
        logger.info(f"Vyplňuji link: {link[:80]}")
        _mcporter("fill", {"uid": link_uid, "value": link})
        time.sleep(1)
    else:
        logger.warning("⚠️  Link input nenalezen")

    # Vyber board
    logger.info(f"Vybírám board: {board}")
    board_btn_uid = _find_uid(snap, "Choose a board")
    if not board_btn_uid:
        board_btn_uid = _find_uid(snap, "board")
    if board_btn_uid:
        _mcporter("click", {"uid": board_btn_uid})
        time.sleep(2)
        snap2 = _snapshot()
        board_uid = _find_uid(snap2, board)
        if board_uid:
            _mcporter("click", {"uid": board_uid})
            time.sleep(1)
            logger.info(f"Board '{board}' vybrán")
        else:
            logger.warning(f"⚠️  Board '{board}' nenalezen, vybírám první dostupný")
            for line in snap2.splitlines():
                if 'button "' in line and "Create board" not in line and "All boards" not in line:
                    m = re.search(r'uid=(\S+)', line)
                    if m:
                        _mcporter("click", {"uid": m.group(1)})
                        time.sleep(1)
                        break
    else:
        logger.warning("⚠️  Board button nenalezen")

    # Publish
    logger.info("Klikám Publish...")
    snap3 = _snapshot()
    pub_uid = None
    for pattern in ['button "Publish"', "Publish"]:
        pub_uid = _find_uid(snap3, pattern)
        if pub_uid:
            break

    if not pub_uid:
        logger.error("❌ Publish button nenalezen")
        logger.debug(f"Snapshot: {snap3[:1000]}")
        return False

    _mcporter("click", {"uid": pub_uid})
    time.sleep(5)

    snap4 = _snapshot()
    if "published" in snap4.lower() or "Your Pin" in snap4 or "pin" in snap4.lower():
        logger.info(f"✅ Pin zveřejněn: '{title[:50]}'")
        return True
    else:
        logger.warning(f"⚠️  Pin status neznámý po publish")
        logger.debug(f"Snapshot po publish: {snap4[:500]}")
        # Vrátíme True pokud se přesměrovalo (pin byl vytvořen)
        current_snap = _snapshot()
        if "pin-creation-tool" not in current_snap:
            logger.info("✅ Přesměrování detekováno — pin zřejmě vytvořen")
            return True
        return False


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    dry = "--dry-run" in sys.argv
    result = post_pin(
        image_path="/home/server/media-data/pinterest/pohadkovetipycz/product-1005009753016637.jpg",
        title="Test Pin — Pohádkové hračky pro děti",
        link="https://www.aliexpress.com/item/1234567890.html",
        dry_run=dry,
    )
    print(f"Výsledek: {'✅ OK' if result else '❌ FAIL'}")
