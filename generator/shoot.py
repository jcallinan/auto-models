import sys, asyncio, subprocess, time, os
from playwright.async_api import async_playwright

shots = sys.argv[1:] or ["rav4:front34", "rav4:side", "rav4:rear34", "e90:front34", "e90:side", "e90:rear34"]

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/bin/google-chrome",
                                    args=["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
        pg = await b.new_page(viewport={"width": 1200, "height": 700})
        pg.on("console", lambda m: print("console:", m.text) if m.type in ("error", "warning") else None)
        pg.on("pageerror", lambda e: print("pageerror:", e))
        await pg.goto("http://localhost:8765/index.html")
        await pg.wait_for_function("window.__ready === true", timeout=120000)
        await pg.evaluate("document.querySelectorAll('.bar,#info,#toggle').forEach(e=>e.style.display='none')")
        for s in shots:
            c, v = s.split(":", 1)
            if v.startswith("cam"):
                nums = [float(n) for n in v[3:].split(",")]
                await pg.evaluate(f"window.__cam('{c}',{nums[:3]},{nums[3:]})")
                v = "cam" + "_".join(str(int(n*10)) for n in nums[:3])
            else:
                await pg.evaluate(f"window.__view('{c}','{v}')")
            await pg.wait_for_timeout(600)
            await pg.screenshot(path=f"shots/{c}_{v}.png")
            print("shot", c, v)
        await b.close()

asyncio.run(main())
