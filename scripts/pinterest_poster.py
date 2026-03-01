#!/usr/bin/env python3
"""
Pinterest Poster — postuje piny přes chrome-devtools MCP (mcporter).
Používá živou Jana Horáková session v chrome-devtools profilu.
NIKDY nepoužívat Playwright (způsobuje hromadění draftů a selhání).
Fix 2026-03-01: přepsáno na mcporter/chrome-devtools API.
"""

import subprocess
import logging
import time
import json
import re

logger = logging.getLogger(__name__)

PIN_BUILDER_URL = "https://www.pinterest.com/pin-creation-tool/"


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
        return True

    # Ensure Pinterest session first
    ensure_pinterest_session()

    # Naviguj na pin creation
    logger.info(f"Naviguju na {PIN_BUILDER_URL}")
    _mcporter("navigate_page", {"type": "url", "url": PIN_BUILDER_URL})
    time.sleep(3)

    snap = _snapshot()

    # Zkontroluj draft limit
    if "limit of 50" in snap or "50 drafts" in snap:
        _delete_drafts_if_needed()
        time.sleep(2)
        _mcporter("navigate_page", {"type": "url", "url": PIN_BUILDER_URL})
        time.sleep(3)
        snap = _snapshot()

    # Najdi File Upload button
    upload_uid = _find_uid(snap, "File Upload")
    if not upload_uid:
        logger.error("File Upload button nenalezen")
        logger.debug(f"Snapshot: {snap[:500]}")
        return False

    # Upload obrázku
    logger.info(f"Uploaduji obrázek: {image_path}")
    _mcporter("upload_file", {"uid": upload_uid, "filePath": image_path})
    time.sleep(6)  # Pinterest potřebuje čas na zpracování

    snap = _snapshot()

    # Vyplň titulek
    title_uid = _find_uid(snap, "textbox \"Title\"")
    if not title_uid:
        # Fallback hledání
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
        logger.warning("Title input nenalezen")

    # Vyplň link
    link_uid = _find_uid(snap, "textbox \"Link\"")
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
        logger.warning("Link input nenalezen")

    # Vyber board
    logger.info(f"Vybírám board: {board}")
    board_btn_uid = _find_uid(snap, "Choose a board")
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
            logger.warning(f"Board '{board}' nenalezen, vybírám první dostupný")
            # Vyber první board
            for line in snap2.splitlines():
                if 'button "' in line and "Create board" not in line and "All boards" not in line:
                    m = re.search(r'uid=(\S+)', line)
                    if m:
                        _mcporter("click", {"uid": m.group(1)})
                        time.sleep(1)
                        break
    else:
        logger.warning("Board button nenalezen")

    # Publish
    logger.info("Klikám Publish...")
    snap3 = _snapshot()
    pub_uid = _find_uid(snap3, "button \"Publish\"")
    if not pub_uid:
        logger.error("Publish button nenalezen")
        logger.debug(f"Snapshot: {snap3[:1000]}")
        return False

    _mcporter("click", {"uid": pub_uid})
    time.sleep(4)

    snap4 = _snapshot()
    if "published" in snap4.lower() or "Your Pin" in snap4:
        logger.info(f"✅ Pin zveřejněn: '{title[:50]}'")
        return True
    else:
        logger.error(f"Pin pravděpodobně nezveřejněn")
        logger.debug(f"Snapshot po publish: {snap4[:500]}")
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


def ensure_pinterest_session() -> bool:
    """
    Ensure we are logged into Pinterest.
    Checks for 'Pohádkové Tipy CZ' in page or profile icon.
    If not logged in, fills credentials from .env and submits.
    """
    import os
    from pathlib import Path

    def load_env():
        env_path = Path.home() / ".clawdbot" / ".env"
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, _, v = line.partition("=")
                        os.environ.setdefault(k.strip(), v.strip())

    load_env()

    logger.info("🔐 Ensuring Pinterest session...")

    _mcporter("navigate_page", {"type": "url", "url": "https://www.pinterest.com"})
    time.sleep(3)
    snap = _snapshot()

    # Check if logged in: look for profile/avatar or our account name
    logged_in = (
        "Pohádkové Tipy CZ" in snap or
        "pohadkovetipycz" in snap.lower() or
        "log in" not in snap.lower()
    )

    if logged_in:
        logger.info("✅ Pinterest already logged in")
        return True

    logger.info("🔑 Pinterest not logged in — attempting login...")

    email = os.environ.get("PINTEREST_EMAIL", "").strip()
    password = os.environ.get("PINTEREST_PASSWORD", "").strip()

    if not email or not password:
        logger.error("❌ PINTEREST_EMAIL / PINTEREST_PASSWORD not set in ~/.clawdbot/.env")
        return False

    _mcporter("navigate_page", {"type": "url", "url": "https://www.pinterest.com/login/"})
    time.sleep(3)
    snap = _snapshot()

    # Fill email
    email_uid = _find_uid(snap, "email")
    if not email_uid:
        for line in snap.splitlines():
            if "textbox" in line.lower() and ("email" in line.lower() or "id" in line.lower()):
                m = re.search(r'uid=(\S+)', line)
                if m:
                    email_uid = m.group(1)
                    break
    if email_uid:
        _mcporter("fill", {"uid": email_uid, "value": email})
        time.sleep(0.5)
    else:
        logger.warning("Email field not found")

    # Fill password
    pw_uid = _find_uid(snap, "password")
    if pw_uid:
        _mcporter("fill", {"uid": pw_uid, "value": password})
        time.sleep(0.5)

    # Submit
    snap2 = _snapshot()
    login_uid = _find_uid(snap2, "Log in")
    if not login_uid:
        login_uid = _find_uid(snap2, "button")
    if login_uid:
        _mcporter("click", {"uid": login_uid})
        time.sleep(4)

    # Verify
    snap3 = _snapshot()
    if "Pohádkové Tipy CZ" in snap3 or "pohadkovetipycz" in snap3.lower():
        logger.info("✅ Pinterest login successful")
        return True

    logger.warning("⚠️  Pinterest login may have failed — check manually")
    return False
