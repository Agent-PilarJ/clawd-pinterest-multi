#!/usr/bin/env python3
"""
Pinterest Pin Poster — v2 with singleton cleanup
"""
import asyncio
from playwright.async_api import async_playwright
import os, json, time, glob
from pathlib import Path

OUTPUT_DIR = Path("/home/server/clawd-pinterest-multi/pins")
PROFILE_DIR = "/tmp/pinterest-profile"

PINS_TO_POST = [
    {"profile": "PohadkoveTipyCZ", "board": "Pohádkové tipy pro děti",
     "title": "Interaktivni robot pro deti 2026 - nejlepsi hracka roku",
     "link": "https://www.amazon.de/s?k=interaktivni+roboticka+hracka+deti&tag=pohadkove-21",
     "image": str(OUTPUT_DIR / "pin_pohadky_robot.jpg")},
    {"profile": "PohadkoveTipyCZ", "board": "Pohádkové tipy pro děti",
     "title": "Vzdelavaci drevene puzzle - rozviji mysleni od 2 let",
     "link": "https://www.amazon.de/s?k=vzdelavaci+drevene+puzzle+deti&tag=pohadkove-21",
     "image": str(OUTPUT_DIR / "pin_pohadky_puzzle.jpg")},
    {"profile": "PohadkoveTipyCZ", "board": "Pohádkové tipy pro děti",
     "title": "Pohadkovy stan pro deti - domecek snu do pokoje",
     "link": "https://www.amazon.de/s?k=detsky+pohladkovy+stan+tipi&tag=pohadkove-21",
     "image": str(OUTPUT_DIR / "pin_pohadky_stan.jpg")},
    {"profile": "HomeDekorCZ", "board": "Home Dekor CZ",
     "title": "Macrame zaves - boho dekorace na zed 2026",
     "link": "https://www.amazon.de/s?k=macrame+wandbehang+boho&tag=pohadkove-21",
     "image": str(OUTPUT_DIR / "pin_home_macrame.jpg")},
    {"profile": "HomeDekorCZ", "board": "Home Dekor CZ",
     "title": "Pokojove rostliny - oaza klidu ve vasem domove 2026",
     "link": "https://www.amazon.de/s?k=zimmerpflanzen+set+topfe&tag=pohadkove-21",
     "image": str(OUTPUT_DIR / "pin_home_rostliny.jpg")},
    {"profile": "HomeDekorCZ", "board": "Home Dekor CZ",
     "title": "LED zrcadlo do koupelny - luxus za dostupnou cenu",
     "link": "https://www.amazon.de/s?k=led+badspiegel+beleuchtung&tag=pohadkove-21",
     "image": str(OUTPUT_DIR / "pin_home_zrcadlo.jpg")},
    {"profile": "FitnessMotivaceCZ", "board": "Fitness Motivace CZ",
     "title": "Odporove gumy - kompletni sada pro trenink doma 2026",
     "link": "https://www.amazon.de/s?k=widerstandsbander+set+fitness&tag=pohadkove-21",
     "image": str(OUTPUT_DIR / "pin_fitness_gumy.jpg")},
    {"profile": "FitnessMotivaceCZ", "board": "Fitness Motivace CZ",
     "title": "Smart fitness tracker 2026 - sleduj zdravi kazdy den",
     "link": "https://www.amazon.de/s?k=smart+fitness+tracker+2026&tag=pohadkove-21",
     "image": str(OUTPUT_DIR / "pin_fitness_tracker.jpg")},
    {"profile": "FitnessMotivaceCZ", "board": "Fitness Motivace CZ",
     "title": "Protein shaker s orgranizerem - fitness essentials 2026",
     "link": "https://www.amazon.de/s?k=protein+shaker+flasche+sport&tag=pohadkove-21",
     "image": str(OUTPUT_DIR / "pin_fitness_shaker.jpg")},
    {"profile": "TechGadgetsCZ", "board": "Tech Gadgets CZ",
     "title": "Bezdratova sluchatka 2026 - nejlepsi zvuk roku CES",
     "link": "https://www.amazon.de/s?k=kabellose+kopfhorer+2026+premium&tag=pohadkove-21",
     "image": str(OUTPUT_DIR / "pin_tech_sluchatka.jpg")},
    {"profile": "TechGadgetsCZ", "board": "Tech Gadgets CZ",
     "title": "Solarni powerbanka - nabijej kdekoli bez proudu",
     "link": "https://www.amazon.de/s?k=solar+powerbank+tragbar+outdoor&tag=pohadkove-21",
     "image": str(OUTPUT_DIR / "pin_tech_powerbanka.jpg")},
    {"profile": "TechGadgetsCZ", "board": "Tech Gadgets CZ",
     "title": "Smart Home Hub 2026 - ovladej cely byt z jednoho mista",
     "link": "https://www.amazon.de/s?k=smart+home+hub+2026&tag=pohadkove-21",
     "image": str(OUTPUT_DIR / "pin_tech_smarthome.jpg")},
]


def cleanup_profile():
    """Remove singleton files"""
    for pattern in [f"{PROFILE_DIR}/Singleton*", f"{PROFILE_DIR}/.com.google*"]:
        for f in glob.glob(pattern):
            try:
                os.unlink(f) if os.path.islink(f) else os.remove(f)
            except:
                pass
    print("  Profile singletons cleaned")


async def screenshot(page, name):
    try:
        await page.screenshot(path=str(OUTPUT_DIR / f"ss_{name}.png"))
    except:
        pass


async def try_login(page):
    """Log in if needed"""
    await page.goto("https://www.pinterest.com", wait_until="domcontentloaded")
    await page.wait_for_timeout(4000)
    url = page.url
    print(f"  Start URL: {url[:80]}")
    
    if "login" in url.lower():
        print("  Logging in...")
        await page.goto("https://www.pinterest.com/login/")
        await page.wait_for_timeout(3000)
        
        for sel in ["input[id='email']", "input[type='email']", "input[name='email']"]:
            try:
                el = await page.query_selector(sel)
                if el:
                    await el.fill("agent@pilarj.cz")
                    break
            except: pass
        
        await page.wait_for_timeout(300)
        
        for sel in ["input[id='password']", "input[type='password']"]:
            try:
                el = await page.query_selector(sel)
                if el:
                    await el.fill("PohKral2026!")
                    break
            except: pass
        
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(8000)
        print(f"  Post-login: {page.url[:80]}")
    else:
        print(f"  Already logged in!")
    return "login" not in page.url.lower()


async def post_pin(ctx, pin, idx):
    print(f"\n[{idx+1}/{len(PINS_TO_POST)}] {pin['profile']} | {pin['title'][:50]}...")
    page = await ctx.new_page()
    status = "FAIL"
    error = None
    
    try:
        await page.goto("https://www.pinterest.com/pin-creation-tool/", wait_until="domcontentloaded")
        await page.wait_for_timeout(5000)
        await screenshot(page, f"{idx:02d}_a_loaded")
        
        # Upload
        fi = await page.query_selector('input[type="file"]')
        if not fi:
            error = "No file input"
            await page.close()
            return {"status": "FAIL", "error": error, **pin}
        
        await fi.set_input_files(pin["image"])
        await page.wait_for_timeout(7000)
        await screenshot(page, f"{idx:02d}_b_uploaded")
        
        # Title - try multiple selectors
        for sel in ["input[placeholder='Add a title']", "textarea[placeholder='Add a title']",
                    "[data-test-id='pin-draft-title'] input"]:
            try:
                t = await page.query_selector(sel)
                if t:
                    await t.click()
                    await t.fill(pin["title"])
                    break
            except: pass
        
        await page.wait_for_timeout(800)
        
        # Link
        for sel in ["input[placeholder='Add a link']", "input[placeholder*='ink']",
                    "[data-test-id='pin-draft-link'] input"]:
            try:
                l = await page.query_selector(sel)
                if l:
                    await l.click()
                    await l.fill(pin["link"])
                    await page.keyboard.press("Tab")
                    break
            except: pass
        
        await page.wait_for_timeout(1500)
        await screenshot(page, f"{idx:02d}_c_filled")
        
        # Board selection
        board = pin["board"]
        # Click "Choose a board"
        for sel in ["text=Choose a board", "[data-test-id='board-dropdown-select-button']",
                    "button[aria-label*='board']", "div[data-test-id='board-dropdown']"]:
            try:
                el = page.locator(sel).first
                if await el.count() > 0:
                    await el.click()
                    await page.wait_for_timeout(1500)
                    break
            except: pass
        
        await screenshot(page, f"{idx:02d}_d_boardopen")
        
        # Find board option
        for sel in [f"text={board}", f"[data-test-id='board-row']:has-text('{board}')",
                    f"li:has-text('{board}')", f"div:has-text('{board}')"]:
            try:
                el = page.locator(sel).first
                if await el.count() > 0:
                    await el.click()
                    await page.wait_for_timeout(1000)
                    break
            except: pass
        
        await screenshot(page, f"{idx:02d}_e_boardsel")
        
        # Try to search for board if not selected
        try:
            search = await page.query_selector("input[placeholder*='Search']")
            if search:
                short = board[:8]
                await search.fill(short)
                await page.wait_for_timeout(1000)
                opt = page.locator(f"text={board}").first
                if await opt.count() > 0:
                    await opt.click()
                    await page.wait_for_timeout(1000)
        except: pass
        
        await page.wait_for_timeout(1000)
        await screenshot(page, f"{idx:02d}_f_ready")
        
        # Publish
        published = False
        for sel in ["button[data-test-id='pin-draft-save-button']",
                    "button:has-text('Publish')", "button:has-text('Save')",
                    "[data-test-id='save-pin']"]:
            try:
                btn = page.locator(sel).first
                if await btn.count() > 0:
                    await btn.click()
                    published = True
                    break
            except: pass
        
        if published:
            await page.wait_for_timeout(8000)
            await screenshot(page, f"{idx:02d}_g_done")
            status = "OK"
            print(f"  ✅ Pin posted!")
        else:
            error = "Publish button not found"
            print(f"  ❌ {error}")
    
    except Exception as e:
        error = str(e)[:200]
        print(f"  ❌ Exception: {error}")
    
    await page.close()
    return {"status": status, "error": error, "title": pin["title"],
            "board": pin["board"], "profile": pin["profile"], "link": pin["link"]}


async def main():
    cleanup_profile()
    
    env = {"DISPLAY": ":0", "XAUTHORITY": "/run/user/1000/.mutter-Xwaylandauth.7UU4K3", "HOME": os.path.expanduser("~"),
           "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin")}
    
    print(f"🚀 Pinterest Auto-Poster | 12 pins to post")
    results = []
    
    async with async_playwright() as pw:
        ctx = await pw.chromium.launch_persistent_context(
            PROFILE_DIR,
            headless=False,
            args=["--no-sandbox", "--disable-dev-shm-usage", "--no-first-run",
                  "--disable-blink-features=AutomationControlled"],
            env=env,
            viewport={"width": 1280, "height": 900},
        )
        print("✓ Browser launched")
        
        # Login check
        p = await ctx.new_page()
        logged_in = await try_login(p)
        await p.close()
        
        if not logged_in:
            print("❌ Could not log in!")
            await ctx.close()
            return []
        
        print("✓ Logged in, starting pins...")
        
        for i, pin in enumerate(PINS_TO_POST):
            # Clean singleton before each pin
            cleanup_profile()
            r = await post_pin(ctx, pin, i)
            results.append(r)
            if i < len(PINS_TO_POST) - 1:
                print("  ⏳ 12s delay...")
                await asyncio.sleep(12)
        
        await ctx.close()
    
    # Save results
    with open(str(OUTPUT_DIR / "posting_results.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    ok = sum(1 for r in results if r.get("status") == "OK")
    fail = len(results) - ok
    print(f"\n📊 Done: {ok} OK, {fail} FAIL")
    for r in results:
        icon = "✅" if r["status"] == "OK" else "❌"
        print(f"  {icon} [{r['profile']}] {r['title'][:50]} — {r['status']}")
    
    return results


if __name__ == "__main__":
    asyncio.run(main())
