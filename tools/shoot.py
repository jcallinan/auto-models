"""Headless screenshots of a .glb via tools/preview. Usage: shoot.py file.glb out_prefix [name:px,py,pz,tx,ty,tz[,fov] ...]"""
import sys, asyncio, os, shutil, subprocess, socket
from playwright.async_api import async_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
glb, prefix = sys.argv[1], sys.argv[2]
views = sys.argv[3:] or [
    'f34:4.6,1.5,5.4,0,0.75,0', 'side:7.8,1.0,0,0,0.8,0', 'r34:-4.6,1.7,-5.4,0,0.8,0',
    'front:0,1.0,7.0,0,0.8,0', 'rear:0,1.1,-7.0,0,0.8,0', 'top:0.01,9,0.5,0,0,0']
root = os.path.join(HERE, 'preview')
shutil.copy(glb, os.path.join(root, 'model.glb'))
port = 8790
srv = subprocess.Popen(['python3', '-m', 'http.server', str(port)], cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome',
                                    args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
        pg = await b.new_page(viewport={'width': 1280, 'height': 720})
        pg.on('pageerror', lambda e: print('pageerror:', e))
        await pg.goto(f'http://localhost:{port}/index.html?f=model.glb')
        await pg.wait_for_function('window.__ready === true', timeout=300000)
        for v in views:
            name, nums = v.split(':'); n = [float(x) for x in nums.split(',')]
            fov = n[6] if len(n) > 6 else 30
            await pg.evaluate(f'window.__shot({n[:3]},{n[3:6]},{fov})')
            await pg.screenshot(path=f'{prefix}_{name}.png')
        await b.close()
try:
    asyncio.run(main())
finally:
    srv.terminate()
