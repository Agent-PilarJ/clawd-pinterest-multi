#!/usr/bin/env python3
"""
Pinterest Poster — postuje piny přes Playwright s Chrome profilem.
Využívá uloženou session pro Janu Horákovou (@PohadkoveTipyCZ).
Selektory ověřeny 2026-02-24 (viz PINTEREST_NOTES.md).
Fix 2026-03-01: přidána selekce board + wait pro Publish button.
"""

import asyncio
import os
import shutil
import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)

# Chrome profil kde je Jana přihlášena
CHROME_PROFILE_SRC = os.path.expanduser("~/.cache/chrome-devtools-mcp/chrome-profile")
CHROME_PROFILE_TMP = "/tmp/pinterest-poster-profile"

# Pinterest URL
PIN_BUILDER_URL = "https://www.pinterest.com/pin-creation-tool/"
TARGET_BOARD = "Pohádkové tipy pro děti"


def _get_xauthority() -> str:
    xauth_dir = "/run/user/1000"
    if os.path.exists(xauth_dir):
        for fname in os.listdir(xauth_dir):
            if "mutter" in fname or "Xwayland" in fname:
                path = os.path.join(xauth_dir, fname)
                logger.debug(f"XAUTHORITY: {path}")
                return path
    return os.environ.get("XAUTHORITY", "")


def _prepare_profile() -> str:
    if os.path.exists(CHROME_PROFILE_TMP):
        shutil.rmtree(CHROME_PROFILE_TMP)
    shutil.copytree(CHROME_PROFILE_SRC, CHROME_PROFILE_TMP, ignore_dangling_symlinks=True,
                    ignore=shutil.ignore_patterns("SingletonSocket", "SingletonCookie", "SingletonLock"))
    for lock_file in ["SingletonLock", "SingletonCookie", "SingletonSocket"]:
        path = os.path.join(CHROME_PROFILE_TMP, lock_file)
        try:
            if os.path.lexists(path):
                os.remove(path)
        except OSError:
            pass
    logger.info(f"Chrome profil připraven: {CHROME_PROFILE_TMP}")
    return CHROME_PROFILE_TMP


async def post_pin_async(
    image_path: str,
    title: str,
    link: str,
    board: str = TARGET_BOARD,
    dry_run: bool = False,
) -> bool:
    if dry_run:
        logger.info(f"[DRY-RUN] post_pin: '{title[:50]}' → {link[:60]}")
        return True

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        logger.error("Playwright není nainstalován.")
        return False

    profile_path = _prepare_profile()
    xauth = _get_xauthority()

    env = {
        "DISPLAY": os.environ.get("DISPLAY", ":0"),
        "XAUTHORITY": xauth,
        "HOME": os.path.expanduser("~"),
        "PATH": os.environ.get("PATH", ""),
    }
    logger.info(f"Browser env: DISPLAY={env['DISPLAY']}, XAUTHORITY={env['XAUTHORITY']}")

    async with async_playwright() as pw:
        ctx = await pw.chromium.launch_persistent_context(
            profile_path,
            headless=False,
            args=["--no-sandbox", "--disable-dev-shm-usage", "--no-first-run"],
            env=env,
        )
        try:
            page = ctx.pages[0] if ctx.pages else await ctx.new_page()

            logger.info(f"Naviguju na {PIN_BUILDER_URL}")
            await page.goto(PIN_BUILDER_URL)
            await page.wait_for_timeout(3000)

            # Upload obrázku
            logger.info(f"Uploaduji obrázek: {image_path}")
            file_input = await page.query_selector('input[type="file"]')
            if not file_input:
                logger.error("Nenalezen file input na stránce")
                return False
            await file_input.set_input_files(image_path)
            await page.wait_for_timeout(4000)

            # Vyplň titulek
            logger.info(f"Vyplňuji titulek: {title[:50]}")
            title_inp = await page.query_selector("input[placeholder='Add a title']")
            if title_inp:
                await title_inp.click()
                await title_inp.fill(title[:100])
            else:
                logger.warning("Titulek input nenalezen")

            # Vyplň link
            logger.info(f"Vyplňuji link: {link[:80]}")
            link_inp = await page.query_selector("input[placeholder='Add a link']")
            if link_inp:
                await link_inp.click()
                await link_inp.fill(link)
                await page.keyboard.press("Tab")
                await page.wait_for_timeout(1500)
            else:
                logger.warning("Link input nenalezen")

            # Vyber board (klíčové pro aktivaci Publish button!)
            logger.info(f"Vybírám board: {board}")
            try:
                board_selector = await page.query_selector("[data-test-id='board-dropdown-select-button']")
                if not board_selector:
                    # Zkus alternativní selektor
                    board_selector = await page.query_selector("button[aria-label*='board'], button[aria-label*='Board']")
                if board_selector:
                    await board_selector.click()
                    await page.wait_for_timeout(1000)
                    # Hledej board v dropdown
                    board_opt = await page.query_selector(f"[data-test-id*='board-row'] >> text={board}")
                    if not board_opt:
                        board_opt = await page.get_by_text(board, exact=True).first.element_handle()
                    if board_opt:
                        await board_opt.click()
                        await page.wait_for_timeout(1000)
                        logger.info(f"Board '{board}' vybrán")
                    else:
                        logger.warning(f"Board '{board}' nenalezen v dropdown")
                else:
                    logger.warning("Board selector nenalezen — zkouším pokračovat bez něj")
            except Exception as e:
                logger.warning(f"Chyba při výběru board: {e} — pokračuji")

            # Počkej až bude Publish button enabled (max 10s)
            logger.info("Čekám na aktivaci Publish button...")
            pub = page.get_by_role("button", name="Publish")
            try:
                await pub.wait_for(state="visible", timeout=5000)
                # Zkus počkat až nebude disabled
                for _ in range(10):
                    is_disabled = await pub.get_attribute("disabled")
                    aria_disabled = await pub.get_attribute("aria-disabled")
                    if is_disabled is None and aria_disabled != "true":
                        break
                    await page.wait_for_timeout(1000)
                    logger.debug("Publish button stále disabled, čekám...")
            except Exception:
                pass

            logger.info("Klikám Publish...")
            await pub.click()
            await page.wait_for_timeout(5000)

            logger.info(f"✅ Pin zveřejněn: '{title[:50]}'")
            return True

        except Exception as e:
            logger.error(f"Chyba při postování pinu: {e}")
            return False
        finally:
            await ctx.close()


def post_pin(
    image_path: str,
    title: str,
    link: str,
    board: str = TARGET_BOARD,
    dry_run: bool = False,
) -> bool:
    return asyncio.run(post_pin_async(image_path, title, link, board, dry_run))


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    dry = "--dry-run" in sys.argv
    test_image = "/home/server/media-data/pinterest/test.jpg"
    if not os.path.exists(test_image):
        os.makedirs(os.path.dirname(test_image), exist_ok=True)
        import urllib.request
        try:
            urllib.request.urlretrieve("https://via.placeholder.com/1000x1500.jpg", test_image)
        except Exception:
            with open(test_image, "wb") as f:
                f.write(b"")
    result = post_pin(
        image_path=test_image,
        title="Test Pin — Pohádkové hračky pro děti",
        link="https://www.aliexpress.com/item/1234567890.html",
        dry_run=dry,
    )
    print(f"Výsledek: {'✅ OK' if result else '❌ FAIL'}")
