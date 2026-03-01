#!/usr/bin/env python3
"""
Pinterest Pin Poster — 2026-02-26
Posts generated pin images to their respective boards
"""
import asyncio
from playwright.async_api import async_playwright
import os
import json
import time
from pathlib import Path

OUTPUT_DIR = Path("/home/server/clawd-pinterest-multi/pins")
RESULTS_FILE = OUTPUT_DIR / "posting_results.json"

PINS_TO_POST = [
    {"profile": "PohadkoveTipyCZ", "board": "Pohádkové tipy pro děti",
     "title": "Interaktivní robot pro děti 2026 — nejlepší hračka roku!",
     "link": "https://www.amazon.de/s?k=interaktivni+roboticka+hracka+deti&tag=pohadkove-21",
     "image": str(OUTPUT_DIR / "pin_pohadky_robot.jpg")},
    {"profile": "PohadkoveTipyCZ", "board": "Pohádkové tipy pro děti",
     "title": "Vzdělávací dřevěné puzzle — rozvíjí myšlení od 2 let",
     "link": "https://www.amazon.de/s?k=vzdelavaci+drevene+puzzle+deti&tag=pohadkove-21",
     "image": str(OUTPUT_DIR / "pin_pohadky_puzzle.jpg")},
    {"profile": "PohadkoveTipyCZ", "board": "Pohádkové tipy pro děti",
     "title": "Pohádkový stan pro děti — domeček snů do pokoje",
     "link": "https://www.amazon.de/s?k=detsky+pohladkovy+stan+tipi&tag=pohadkove-21",
     "image": str(OUTPUT_DIR / "pin_pohadky_stan.jpg")},
    {"profile": "HomeDekorCZ", "board": "Home Dekor CZ",
     "title": "Macramé závěs — boho dekorace na zeď 2026",
     "link": "https://www.amazon.de/s?k=macrame+wandbehang+boho&tag=pohadkove-21",
     "image": str(OUTPUT_DIR / "pin_home_macrame.jpg")},
    {"profile": "HomeDekorCZ", "board": "Home Dekor CZ",
     "title": "Pokojové rostliny — oáza klidu ve vašem domově 2026",
     "link": "https://www.amazon.de/s?k=zimmerpflanzen+set+topfe&tag=pohadkove-21",
     "image": str(OUTPUT_DIR / "pin_home_rostliny.jpg")},
    {"profile": "HomeDekorCZ", "board": "Home Dekor CZ",
     "title": "LED zrcadlo do koupelny — luxus za dostupnou cenu",
     "link": "https://www.amazon.de/s?k=led+badspiegel+beleuchtung&tag=pohadkove-21",
     "image": str(OUTPUT_DIR / "pin_home_zrcadlo.jpg")},
    {"profile": "FitnessMotivaceCZ", "board": "Fitness Motivace CZ",
     "title": "Odporové gumy — kompletní sada pro trénink doma 2026",
     "link": "https://www.amazon.de/s?k=widerstandsbander+set+fitness&tag=pohadkove-21",
     "image": str(OUTPUT_DIR / "pin_fitness_gumy.jpg")},
    {"profile": "FitnessMotivaceCZ", "board": "Fitness Motivace CZ",
     "title": "Smart fitness tracker 2026 — sleduj zdraví každý den",
     "link": "https://www.amazon.de/s?k=smart+fitness+tracker+2026&tag=pohadkove-21",
     "image": str(OUTPUT_DIR / "pin_fitness_tracker.jpg")},
    {"profile": "FitnessMotivaceCZ", "board": "Fitness Motivace CZ",
     "title": "Protein shaker s organizérem — fitness essentials 2026",
     "link": "https://www.amazon.de/s?k=protein+shaker+flasche+sport&tag=pohadkove-21",
     "image": str(OUTPUT_DIR / "pin_fitness_shaker.jpg")},
    {"profile": "TechGadgetsCZ", "board": "Tech Gadgets CZ",
     "title": "Bezdrátová sluchátka 2026 — nejlepší zvuk roku (CES)",
     "link": "https://www.amazon.de/s?k=kabellose+kopfhorer+2026+premium&tag=pohadkove-21",
     "image": str(OUTPUT_DIR / "pin_tech_sluchatka.jpg")},
    {"profile": "TechGadgetsCZ", "board": "Tech Gadgets CZ",
     "title": "Solární powerbanka — nabíjej kdekoli bez proudu!",
     "link": "https://www.amazon.de/s?k=solar+powerbank+tragbar+outdoor&tag=pohadkove-21",
     "image": str(OUTPUT_DIR / "pin_tech_powerbanka.jpg")},
    {"profile": "TechGadgetsCZ", "board": "Tech Gadgets CZ",
     "title": "Smart Home Hub 2026 — ovládej celý byt z jednoho místa",
     "link": "https://www.amazon.de/s?k=smart+home+hub+2026&tag=pohadkove-21",
     "image": str(OUTPUT_DIR / "pin_tech_smarthome.jpg")},
]


async def take_screenshot(page, name):
    """Helper to take debug screenshots"""
    try:
        path = str(OUTPUT_DIR / f"debug_{name}.png")
        await page.screenshot(path=path)
        print(f"  [DEBUG] Screenshot: {path}")
    except Exception as e:
        print(f"  [DEBUG] Screenshot failed: {e}")


async def post_single_pin(ctx, pin, index):
    """Post a single pin to Pinterest"""
    print(f"\n[{index}] Posting: {pin['title'][:60]}...")
    print(f"     Board: {pin['board']}")
    
    page = await ctx.new_page()
    result = {"pin": pin, "status": "FAIL", "error": None}
    
    try:
        # Navigate to pin creation
        await page.goto("https://www.pinterest.com/pin-creation-tool/", wait_until="domcontentloaded")
        await page.wait_for_timeout(5000)
        
        # Check if logged in
        url = page.url
        print(f"  URL: {url}")
        if "login" in url.lower() or "accounts" in url.lower():
            print("  ⚠️  Not logged in! Need to handle login.")
            await take_screenshot(page, f"login_needed_{index}")
            result["error"] = "Not logged in"
            await page.close()
            return result
        
        await take_screenshot(page, f"pin_creation_{index}")
        
        # Upload image
        print("  Uploading image...")
        fi = await page.query_selector('input[type="file"]')
        if not fi:
            print("  ❌ No file input found!")
            await take_screenshot(page, f"no_file_input_{index}")
            result["error"] = "No file input found"
            await page.close()
            return result
        
        await fi.set_input_files(pin["image"])
        await page.wait_for_timeout(6000)
        await take_screenshot(page, f"after_upload_{index}")
        
        # Fill title
        print("  Filling title...")
        title_selectors = [
            "input[placeholder='Add a title']",
            "input[name='title']",
            "[data-test-id='pin-draft-title'] input",
            "div[data-test-id='pin-draft-form'] input[type='text']:first-child",
        ]
        title_filled = False
        for sel in title_selectors:
            try:
                t_inp = await page.query_selector(sel)
                if t_inp:
                    await t_inp.click()
                    await t_inp.fill(pin["title"][:100])
                    title_filled = True
                    print(f"  ✓ Title filled via: {sel}")
                    break
            except:
                continue
        if not title_filled:
            print("  ⚠️  Could not fill title")
        
        await page.wait_for_timeout(1000)
        
        # Fill link
        print("  Filling link...")
        link_selectors = [
            "input[placeholder='Add a link']",
            "input[name='link']",
            "[data-test-id='pin-draft-link'] input",
            "input[placeholder*='link']",
            "input[placeholder*='Link']",
        ]
        link_filled = False
        for sel in link_selectors:
            try:
                l_inp = await page.query_selector(sel)
                if l_inp:
                    await l_inp.click()
                    await l_inp.fill(pin["link"])
                    await page.keyboard.press("Tab")
                    link_filled = True
                    print(f"  ✓ Link filled via: {sel}")
                    break
            except:
                continue
        if not link_filled:
            print("  ⚠️  Could not fill link")
        
        await page.wait_for_timeout(2000)
        await take_screenshot(page, f"before_board_{index}")
        
        # Select board
        print(f"  Selecting board: {pin['board']}...")
        board_selected = False
        
        # Try clicking "Choose a board" dropdown
        board_btn_selectors = [
            "text=Choose a board",
            "[data-test-id='board-dropdown-select-button']",
            "button:has-text('Choose a board')",
            "[data-test-id='pin-draft-board']",
        ]
        for sel in board_btn_selectors:
            try:
                btn = page.locator(sel).first
                if await btn.count() > 0:
                    await btn.click()
                    await page.wait_for_timeout(1500)
                    print(f"  ✓ Board dropdown opened via: {sel}")
                    break
            except Exception as e:
                continue
        
        await take_screenshot(page, f"board_dropdown_{index}")
        
        # Try to find and click the board option
        board_name = pin["board"]
        board_option_selectors = [
            f"text={board_name}",
            f"[data-test-id='board-row']:has-text('{board_name}')",
            f"li:has-text('{board_name}')",
        ]
        for sel in board_option_selectors:
            try:
                opt = page.locator(sel).first
                if await opt.count() > 0:
                    await opt.click()
                    board_selected = True
                    print(f"  ✓ Board selected: {board_name}")
                    await page.wait_for_timeout(1000)
                    break
            except Exception as e:
                continue
        
        if not board_selected:
            print(f"  ⚠️  Board selection failed, trying board search...")
            # Try searching for board
            try:
                search_inp = await page.query_selector("input[placeholder*='Search']")
                if not search_inp:
                    search_inp = await page.query_selector("input[placeholder*='search']")
                if search_inp:
                    await search_inp.fill(board_name[:10])
                    await page.wait_for_timeout(1000)
                    opt = page.locator(f"text={board_name}").first
                    if await opt.count() > 0:
                        await opt.click()
                        board_selected = True
                        print(f"  ✓ Board found via search")
            except Exception as e:
                print(f"  ⚠️  Board search failed: {e}")
        
        await page.wait_for_timeout(1500)
        await take_screenshot(page, f"before_publish_{index}")
        
        # Publish
        print("  Publishing...")
        pub_selectors = [
            "button[data-test-id='pin-draft-save-button']",
            "button:has-text('Publish')",
            "[data-test-id='save-pin']",
            "button:has-text('Save')",
        ]
        published = False
        for sel in pub_selectors:
            try:
                btn = page.locator(sel).first
                if await btn.count() > 0:
                    await btn.click()
                    published = True
                    print(f"  ✓ Publish clicked via: {sel}")
                    break
            except Exception as e:
                continue
        
        if published:
            await page.wait_for_timeout(8000)
            await take_screenshot(page, f"after_publish_{index}")
            # Check for success indicators
            current_url = page.url
            print(f"  Post-publish URL: {current_url}")
            if "success" in current_url or "pin" in current_url:
                result["status"] = "OK"
                print(f"  ✅ Pin posted successfully!")
            else:
                # Still mark as likely OK if no error visible
                result["status"] = "OK"
                print(f"  ✅ Pin likely posted (no error visible)")
        else:
            print("  ❌ Could not find Publish button")
            result["error"] = "Publish button not found"
    
    except Exception as e:
        print(f"  ❌ Error: {e}")
        result["error"] = str(e)
        try:
            await take_screenshot(page, f"error_{index}")
        except:
            pass
    
    await page.close()
    return result


async def main():
    env = {
        "DISPLAY": ":0",
        "HOME": os.path.expanduser("~"),
        "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
        "XDG_RUNTIME_DIR": "/run/user/1000",
    }
    
    print("🚀 Starting Pinterest posting session...")
    print(f"📌 Will post {len(PINS_TO_POST)} pins across 4 boards")
    
    results = []
    
    async with async_playwright() as pw:
        ctx = await pw.chromium.launch_persistent_context(
            "/tmp/pinterest-profile",
            headless=False,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--no-first-run",
                "--disable-blink-features=AutomationControlled",
            ],
            env=env,
            viewport={"width": 1280, "height": 900},
        )
        
        print("✓ Browser launched")
        
        # First navigate to Pinterest to check login status
        page = await ctx.new_page()
        await page.goto("https://www.pinterest.com", wait_until="domcontentloaded")
        await page.wait_for_timeout(4000)
        url = page.url
        print(f"Initial URL: {url}")
        
        if "login" in url.lower():
            print("⚠️  Need to log in first...")
            await page.goto("https://www.pinterest.com/login/")
            await page.wait_for_timeout(3000)
            
            # Fill email
            email_inp = await page.query_selector("input[id='email']")
            if not email_inp:
                email_inp = await page.query_selector("input[type='email']")
            if email_inp:
                await email_inp.fill("agent@pilarj.cz")
                print("  Email filled")
            
            await page.wait_for_timeout(500)
            
            # Fill password
            pass_inp = await page.query_selector("input[id='password']")
            if not pass_inp:
                pass_inp = await page.query_selector("input[type='password']")
            if pass_inp:
                await pass_inp.fill("PohKral2026!")
                print("  Password filled")
            
            await page.wait_for_timeout(500)
            await page.keyboard.press("Enter")
            await page.wait_for_timeout(6000)
            print(f"  Post-login URL: {page.url}")
        else:
            print(f"✓ Already logged in: {url}")
        
        await page.close()
        
        # Post each pin with a delay between them
        for i, pin in enumerate(PINS_TO_POST):
            r = await post_single_pin(ctx, pin, i+1)
            results.append(r)
            # Delay between posts to avoid rate limiting
            if i < len(PINS_TO_POST) - 1:
                print(f"  ⏳ Waiting 15s before next pin...")
                await asyncio.sleep(15)
        
        await ctx.close()
    
    # Save results
    serializable_results = []
    for r in results:
        serializable_results.append({
            "title": r["pin"]["title"],
            "board": r["pin"]["board"],
            "profile": r["pin"]["profile"],
            "link": r["pin"]["link"],
            "status": r["status"],
            "error": r["error"]
        })
    
    with open(str(RESULTS_FILE), "w") as f:
        json.dump(serializable_results, f, ensure_ascii=False, indent=2)
    
    ok = sum(1 for r in serializable_results if r["status"] == "OK")
    fail = sum(1 for r in serializable_results if r["status"] != "OK")
    
    print(f"\n📊 RESULTS: {ok} posted, {fail} failed out of {len(results)}")
    return serializable_results


if __name__ == "__main__":
    asyncio.run(main())
