#!/usr/bin/env python3
"""
Pinterest Poster — postuje piny přes Playwright s Chrome profilem.
Fix 2026-03-01: Locatory místo ElementHandle, wait for interactive elements.
"""

import asyncio
import os
import shutil
import logging

logger = logging.getLogger(__name__)

CHROME_PROFILE_SRC = os.path.expanduser("~/.cache/chrome-devtools-mcp/chrome-profile")
CHROME_PROFILE_TMP = "/tmp/pinterest-poster-profile"
PIN_BUILDER_URL = "https://www.pinterest.com/pin-creation-tool/"
TARGET_BOARD = "Pohádkové tipy pro děti"


def _get_xauthority() -> str:
    xauth_dir = "/run/user/1000"
    if os.path.exists(xauth_dir):
        for fname in os.listdir(xauth_dir):
            if "mutter" in fname or "Xwayland" in fname:
                return os.path.join(xauth_dir, fname)
    return os.environ.get("XAUTHORITY", "")


def _prepare_profile() -> str:
    if os.path.exists(CHROME_PROFILE_TMP):
        shutil.rmtree(CHROME_PROFILE_TMP)
    shutil.copytree(CHROME_PROFILE_SRC, CHROME_PROFILE_TMP,
                    ignore_dangling_symlinks=True,
                    ignore=shutil.ignore_patterns("SingletonSocket", "SingletonCookie", "SingletonLock"))
    for f in ["SingletonLock", "SingletonCookie", "SingletonSocket"]:
        p = os.path.join(CHROME_PROFILE_TMP, f)
        try:
            if os.path.lexists(p):
                os.remove(p)
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
            await page.wait_for_load_state("networkidle", timeout=10000)
            await page.wait_for_timeout(2000)

            # Upload obrázku
            logger.info(f"Uploaduji obrázek: {image_path}")
            file_input = page.locator('input[type="file"]').first
            await file_input.set_input_files(image_path)
            await page.wait_for_timeout(4000)

            # Titulek
            logger.info(f"Vyplňuji titulek: {title[:50]}")
            title_loc = page.locator("input[placeholder='Add a title']").first
            await title_loc.wait_for(state="visible", timeout=10000)
            await title_loc.click()
            await title_loc.fill(title[:100])
            await page.wait_for_timeout(500)

            # Link
            logger.info(f"Vyplňuji link: {link[:80]}")
            link_loc = page.locator("input[placeholder='Add a link']").first
            try:
                await link_loc.wait_for(state="visible", timeout=5000)
                await link_loc.click()
                await link_loc.fill(link)
                await page.keyboard.press("Tab")
                await page.wait_for_timeout(1500)
            except Exception as e:
                logger.warning(f"Link input nedostupný: {e}")

            # Board selection
            logger.info(f"Vybírám board: {board}")
            try:
                # Zkus různé selektory pro board dropdown
                board_btn = None
                for sel in [
                    "[data-test-id='board-dropdown-select-button']",
                    "button[aria-label*='oard']",
                    "div[data-test-id*='board'] button",
                ]:
                    loc = page.locator(sel).first
                    try:
                        await loc.wait_for(state="visible", timeout=3000)
                        board_btn = loc
                        logger.info(f"Board button nalezen: {sel}")
                        break
                    except Exception:
                        continue

                if board_btn:
                    await board_btn.click()
                    await page.wait_for_timeout(1500)
                    # Hledej board v dropdown
                    board_item = page.get_by_text(board, exact=True).first
                    try:
                        await board_item.wait_for(state="visible", timeout=3000)
                        await board_item.click()
                        await page.wait_for_timeout(1000)
                        logger.info(f"Board '{board}' vybrán")
                    except Exception:
                        logger.warning(f"Board '{board}' nenalezen v dropdown")
                else:
                    logger.warning("Board button nenalezen — pokračuji bez výběru")
            except Exception as e:
                logger.warning(f"Chyba při výběru board: {e}")

            # Čekej na Publish button (max 10s)
            logger.info("Čekám na aktivaci Publish button...")
            pub = page.get_by_role("button", name="Publish")
            await pub.wait_for(state="visible", timeout=10000)

            # Zkontroluj zda je button disabled
            for i in range(10):
                disabled = await pub.get_attribute("disabled")
                aria_disabled = await pub.get_attribute("aria-disabled")
                if disabled is None and aria_disabled != "true":
                    logger.info("Publish button aktivní!")
                    break
                logger.debug(f"Publish button disabled ({i+1}/10), čekám 1s...")
                await page.wait_for_timeout(1000)

            logger.info("Klikám Publish...")
            await pub.click(timeout=10000)
            await page.wait_for_timeout(5000)

            logger.info(f"✅ Pin zveřejněn: '{title[:50]}'")
            return True

        except Exception as e:
            logger.error(f"Chyba při postování pinu: {e}")
            # Screenshot pro debug
            try:
                snap_path = f"/tmp/pinterest_debug_{int(__import__('time').time())}.png"
                await page.screenshot(path=snap_path)
                logger.info(f"Screenshot uložen: {snap_path}")
            except Exception:
                pass
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
