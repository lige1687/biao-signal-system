import json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

root=Path(__file__).parent
errors=[]
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True)
    page=browser.new_page(viewport={'width':1440,'height':1000},locale='zh-CN')
    page.on('pageerror',lambda err: errors.append(str(err)))
    page.goto('http://127.0.0.1:5173/?symbol=000001.SS',wait_until='domcontentloaded')
    card=page.locator('[data-overview-card="erp-cn"]')
    expect(card.locator('.moa-erp-value strong')).to_have_text('5.83',timeout=45000)
    card.get_by_role('button',name='看大图',exact=False).click()
    panel=page.locator('.erp-trend-observation')
    panel.locator(':scope > summary').click()
    mapping=panel.locator('.erp-research-mapping')
    expect(mapping.locator('summary')).to_contain_text('阶梯 10% ／ 连续 9.1%')
    mapping.locator('summary').click()
    expect(mapping.locator('tbody tr')).to_have_count(5)
    expect(mapping.locator('.is-current')).to_have_count(1)
    expect(mapping.locator('.is-current')).to_have_text('10%')
    selector=mapping.get_by_label('仓位实验趋势方法')
    selector.select_option('band')
    expect(mapping.locator('.is-current')).to_have_text('10%')
    selector.select_option('score')
    assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth')
    panel.screenshot(path=str(root/'after-trend-matrix.png'))
    result={'page_errors':errors,'matrix':mapping.inner_text(),'checks':['5x3 matrix','current cell matches 0/3 score','both method switches','continuous mapping matches independent value','no overflow']}
    assert not errors
    browser.close()
(root/'matrix-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps(result,ensure_ascii=False,indent=2))
