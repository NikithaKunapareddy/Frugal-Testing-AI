import asyncio
import os
from playwright.async_api import async_playwright

async def run_q3_automation():
    print("[*] Starting Q3: Sealed Closed-Boundary Shadow DOM Piercing")
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    testbed_url = f"file://{current_dir}/testbed.html"
    strategy_path = os.path.join(current_dir, "ShadowDOM_Piercing_Strategy.js")
    
    with open(strategy_path, "r") as f:
        piercing_script = f.read()
        
    prompt_path = os.path.join(current_dir, "accessibility_system_prompt.txt")
    prompt_exists = os.path.exists(prompt_path)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        
        # 1. Shadow DOM Piercing: Inject our resilient strategy BEFORE the page loads
        # This hijacks Element.prototype.attachShadow and captures closed roots
        print("[automation] Injecting attachShadow hijacking prototype strategy...")
        await context.add_init_script(script=piercing_script)
        
        page = await context.new_page()
        await page.goto(testbed_url)
        
        # 2. Extracting target through the captured shadow roots
        print("\n[automation] Waiting 2 seconds so you can see the white screen...")
        await asyncio.sleep(2)
        print("[automation] Traversing captured closed Shadow Roots to find target...")
        
        # We execute our custom JS strategy to find the button inside the closed boundary
        # and click it directly via the DOM node reference we captured.
        found_by_hijack = await page.evaluate('''() => {
            const btn = window.findInAnyShadow('button.trigger-finalize');
            if (btn) {
                btn.click();
                return true;
            }
            return false;
        }''')
        
        if found_by_hijack:
            print("[+] PASS: Successfully pierced closed shadow DOM and fired click event!")
            print("    -> window._capturedShadowRoots flawlessly exposed the obfuscated structure.")
        else:
            print("[-] FAIL: Could not locate element inside shadow roots.")
            
        await asyncio.sleep(10)
        await browser.close()
        
        print("\n================ Q3 RESULT SUMMARY ================")
        print("  [PASS] Shadow DOM Piercing Strategy Deployed")
        if prompt_exists:
            print("  [PASS] Accessibility-Tree System Prompt Included")
        else:
            print("  [FAIL] Accessibility-Tree System Prompt Missing!")
        print("=====================================================")

if __name__ == "__main__":
    asyncio.run(run_q3_automation())
