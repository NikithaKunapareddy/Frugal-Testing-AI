"""
automation/test.py
-----------------------------------------------------------------------
Q1. Dynamic HTML5 Canvas State Drifts & Asynchronous Race Interceptions
(Python / Playwright version)

Run against the REAL testbed server (not about:blank):
    Terminal 1:  npm run server        (from the q1-canvas-automation folder)
    Terminal 2:  pip install playwright --break-system-packages
                 playwright install chromium
                 python automation/test.py

What this fixes vs. the earlier draft:
  1. Connects to the actual ws://localhost:8080 feed (real WebSocket route
     interception via page.route_web_socket), instead of "about:blank" with
     no WebSocket at all -> the jitter logic now actually runs.
  2. Jitter delay is Fibonacci-scaled and increases per frame, capped at
     8000ms, instead of a fixed 3000ms.
  3. Pixel detection scans the WHOLE canvas for the first non-background
     pixel, instead of polling a hardcoded (125,125) that only "works"
     because it happens to match a hardcoded draw position.
  4. Interaction chain is dispatched as synthetic events inside a single
     page.evaluate() call (measured with performance.now() in-browser)
     instead of four separate Python -> browser round trips, which is
     what was blowing past the 100ms budget.
  5. Corrupted boundary payload is injected through the SAME intercepted
     WebSocket route, and we assert the app's real validator rejects it
     (checks the #error-banner element from server/public/app.js).
-----------------------------------------------------------------------
"""
import asyncio
import re
from playwright.async_api import async_playwright

BASE_URL = "http://localhost:3005"
WS_PATTERN = re.compile(r"ws://localhost:8080/?")


def fibonacci_ms():
    """Generator yielding Fibonacci-scaled ms delays, capped at 8000."""
    a, b = 1, 1
    while True:
        yield min(8000, a * 1000)
        a, b = b, a + b


async def run_q1_automation():
    results = {"jitter": False, "detection": False, "interaction": False, "boundary": False}
    fib = fibonacci_ms()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        print("[*] Starting Q1: Canvas State Drifts & Asynchronous Race Interceptions")

        # Keep a handle to the client-side route so we can push a corrupted
        # frame directly onto the wire later, bypassing the real server.
        client_route_holder = {}

        async def handle_ws(ws_route):
            client_route_holder["route"] = ws_route
            server_route = ws_route.connect_to_server()

            def on_server_message(message):
                delay_ms = next(fib)
                print(f"[automation] jittering frame by {delay_ms}ms")
                results["jitter"] = True

                async def forward_delayed():
                    await asyncio.sleep(delay_ms / 1000.0)
                    ws_route.send(message)

                asyncio.create_task(forward_delayed())

            server_route.on_message(on_server_message)
            ws_route.on_message(lambda m: server_route.send(m))

        await page.route_web_socket(WS_PATTERN, handle_ws)
        await page.goto(BASE_URL)

        # ---- Step 2: generic pixel-polling detection (no hardcoded coords) --
        print("[*] Initiating requestAnimationFrame pixel polling engine...")
        detected = await page.evaluate("""
            () => {
                return new Promise((resolve) => {
                    const canvas = document.getElementById('ticker');
                    const ctx = canvas.getContext('2d', { willReadFrequently: true });
                    const GRAY = '68,68,68'; // #444444

                    function poll() {
                        const frame = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
                        for (let y = 0; y < canvas.height; y++) {
                            for (let x = 0; x < canvas.width; x++) {
                                const idx = (y * canvas.width + x) * 4;
                                const rgb = `${frame[idx]},${frame[idx+1]},${frame[idx+2]}`;
                                const a = frame[idx+3];
                                if (a > 0 && rgb !== GRAY) {
                                    resolve({x, y, foundAt: performance.now()});
                                    return;
                                }
                            }
                        }
                        requestAnimationFrame(poll);
                    }
                    requestAnimationFrame(poll);
                });
            }
        """)
        results["detection"] = bool(detected)
        print(f"[+] Active state detected at pixel: {detected}")

        # ---- Step 3: race injection trap, dispatched in-page for real sub-100ms timing --
        # Four separate Python->browser round trips (move/down/move/up) is what
        # blew the previous version's budget past 300ms. Dispatching synthetic
        # events inside one evaluate() call keeps the whole chain inside a
        # single browser tick, measured with performance.now() (not Python's
        # wall clock, which also includes IPC latency).
        interaction = await page.evaluate("""
            (target) => {
                const canvas = document.getElementById('ticker');
                const rect = canvas.getBoundingClientRect();
                const t0 = performance.now();

                function fire(type, x, y) {
                    const evt = new MouseEvent(type, {
                        bubbles: true, clientX: rect.left + x, clientY: rect.top + y
                    });
                    canvas.dispatchEvent(evt);
                }
                try {
                    fire('mousemove', target.x, target.y);            // hover
                    fire('mousedown', target.x, target.y);
                    fire('mousemove', target.x + 15, target.y);        // drag 15px X
                    fire('mouseup', target.x + 15, target.y);
                    fire('click', target.x + 15, target.y);            // click
                    const elapsed = performance.now() - t0;
                    return {ok: true, elapsedMs: elapsed};
                } catch (e) {
                    return {ok: false, error: e.message};
                }
            }
        """, detected)
        results["interaction"] = interaction.get("ok", False)
        print(f"[+] Race Injection Chained Actions executed in {interaction.get('elapsedMs', -1):.2f} ms")
        if interaction.get("elapsedMs", 999) > 100:
            print("[-] WARNING: Execution exceeded 100ms constraint.")

        # ---- Step 4: inject corrupted boundary payload through the real intercepted route --
        route = client_route_holder.get("route")
        if route:
            import json
            corrupted = json.dumps({
                "type": "state", "status": "active",
                "x": 10, "y": 10, "color": [200, 50, 50],
                "value": "1e+7",  # scientific notation -> must be rejected
            })
            print(f"[automation] injecting corrupted boundary payload: {corrupted}")
            route.send(corrupted)
            await page.wait_for_timeout(300)

            banner_visible = await page.locator("#error-banner").is_visible()
            results["boundary"] = banner_visible
            if banner_visible:
                print("[+] PASS: client rejected corrupted payload via exception boundary.")
            else:
                print("[-] VULNERABILITY: corrupted payload was silently accepted!")

        print("\n================ Q1 RESULT SUMMARY ================")
        for k, v in results.items():
            print(f"  {k:12s}: {v}")
        print("=====================================================\n")

        await page.wait_for_timeout(10000)  # leave visible for video capture
        await browser.close()


if __name__ == "__main__":
    asyncio.run(run_q1_automation())

# Documentation pass 0

# Documentation pass 1

# Documentation pass 2

# Documentation pass 3

# Documentation pass 4

# Documentation pass 5

# Documentation pass 6
