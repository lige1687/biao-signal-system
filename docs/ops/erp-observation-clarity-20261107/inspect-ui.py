import json
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).parent
with sync_playwright() as p:
 b=p.chromium.launch(channel="chrome", headless=True)
 c=b.new_context(viewport={"width":1440,"height":1000},locale="zh-CN",timezone_id="Asia/Shanghai")
 page=c.new_page()
 errors=[]
 page.on("pageerror",lambda err:errors.append(str(err)))
 page.goto("http://127.0.0.1:5173/?symbol=000001.SS",wait_until="domcontentloaded")
 page.locator('[data-overview-card="erp-cn"] .moa-erp-value strong').filter(has_text="5.83").wait_for(timeout=45000)
 page.locator('[data-overview-card="erp-us"] .moa-erp-value strong').filter(has_text="-0.90").wait_for(timeout=45000)
 board=page.locator("#market-overview")
 board.scroll_into_view_if_needed()
 page.screenshot(path=str(ROOT/"after-home.png"))
 metrics=board.evaluate("""el=>({height:el.getBoundingClientRect().height,summaryOffset:el.querySelector('.moa-context').getBoundingClientRect().top-el.getBoundingClientRect().top,summaryHeight:el.querySelector('.moa-context').getBoundingClientRect().height,cardCount:el.querySelectorAll('[data-overview-card]').length,cn:el.querySelector('[data-overview-card=erp-cn]').innerText,us:el.querySelector('[data-overview-card=erp-us]').innerText,summary:el.querySelector('.moa-context').innerText})""")
 metrics['errors']=errors
 print(json.dumps(metrics,ensure_ascii=False,indent=2))
 (ROOT/'after-home-metrics.json').write_text(json.dumps(metrics,ensure_ascii=False,indent=2))
 b.close()
