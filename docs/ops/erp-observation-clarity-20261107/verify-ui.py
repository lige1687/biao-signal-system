import json, urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
ROOT=Path(__file__).parent
BASE='http://127.0.0.1:5173'
def get(path):
 with urllib.request.urlopen('http://127.0.0.1:8000'+path) as r: return json.load(r)
cn=get('/api/fundamentals/erp-cn-reference')
us=get('/api/fundamentals/rates-history?lookback_days=7300')['series']['erp_us']
expected={'cn':{'date':cn['points'][-1]['date'],'value':cn['points'][-1]['value']},'us':{'date':us['dates'][-1],'value':us['values'][-1]}}
result={'expected':expected,'checks':[],'pageErrors':[]}
with sync_playwright() as p:
 b=p.chromium.launch(channel='chrome',headless=True)
 c=b.new_context(viewport={'width':1440,'height':1000},locale='zh-CN',timezone_id='Asia/Shanghai')
 page=c.new_page()
 page.on('pageerror',lambda e:result['pageErrors'].append(str(e)))
 page.goto(BASE+'/?symbol=000001.SS',wait_until='domcontentloaded')
 for market,e in expected.items():
  card=page.locator(f'[data-overview-card="erp-{market}"]')
  expect(card.locator('.moa-erp-value strong')).to_have_text(f"{e['value']:.2f}",timeout=45000)
  expect(card.locator('.moa-erp-value time')).to_have_text(e['date'])
  before=card.locator('.moa-conclusion').inner_text()
  if market=='us':
   card.locator('.us-erp-thresholds button').first.click()
   expect(card.locator('.moa-conclusion')).to_have_text(before)
   card.locator('.us-erp-thresholds button').first.click()
  card.get_by_role('button',name='看大图',exact=False).click()
  dialog=page.get_by_role('dialog')
  expect(dialog.locator('.erp-cross-reading')).to_contain_text(f"{e['value']:.2f}")
  expect(dialog.locator('.erp-cross-reading')).to_contain_text(e['date'])
  expect(dialog.locator('.erp-cross-method')).to_contain_text('滚动3个自然年')
  dialog.get_by_role('button',name='1年',exact=True).click()
  expect(dialog.locator('.erp-cross-reading')).to_contain_text(f"{e['value']:.2f}")
  expect(dialog.locator('.erp-cross-chart svg').first).to_be_visible(timeout=30000)
  if market=='cn':
   dialog.get_by_label('查看穿轨日期').select_option('2:2024-09-13:upper')
   expect(dialog.locator('.erp-cross-reading')).to_contain_text('2024-09-13')
   expect(dialog.locator('.erp-cross-reading')).to_contain_text('7.21')
  page.screenshot(path=str(ROOT/f'after-detail-{market}.png'))
  if market=='cn':
   dialog.locator('.erp-trend-observation > summary').click()
   dialog.locator('.erp-trend-observation').screenshot(path=str(ROOT/'after-trend-comparison.png'))
   result['trendObservation']=dialog.locator('.erp-trend-observation').inner_text()
  page.keyboard.press('Escape')
  expect(dialog).to_have_count(0)
  result['checks'].append(f'{market} home, date, detail, display range, close checked')
 summary=page.locator('.moa-context')
 summary.locator('summary').first.click()
 facts=summary.locator('.moa-combination').first.locator('.moa-connection-facts li').all_text_contents()
 assert len(facts)==len(set(facts))
 summary.locator('summary').first.click()
 card=page.locator('[data-overview-card="erp-cn"]')
 card.get_by_role('button',name='收起',exact=True).click()
 expect(card).to_have_count(0)
 page.locator('[data-shelf-restore="erp-cn"]').click()
 expect(card).to_be_visible()
 result['checks'].append('combination evidence is unique; collapse/restore works')
 page.goto(BASE+'/fundamentals#fund-sec-rates',wait_until='domcontentloaded')
 for market,e in expected.items():
  label='沪深300' if market=='cn' else '标普500'
  card=page.locator('.macro-card').filter(has=page.locator('.macro-name',has_text=label+'股债利差'))
  expect(card.locator('.macro-value')).to_contain_text(f"{e['value']:.2f}",timeout=45000)
  expect(card).to_contain_text(e['date'])
  expect(card).to_contain_text('个百分点')
  card.screenshot(path=str(ROOT/f'after-rates-{market}.png'))
  card.click()
  dialog=page.get_by_role('dialog')
  expect(dialog.locator('.erp-cross-reading')).to_contain_text(f"{e['value']:.2f}")
  page.keyboard.press('Escape')
  result['checks'].append(f'{market} rates card/date/detail match home canonical observation')
 page.get_by_role('button',name='长周期叠加',exact=True).click()
 expect(page.locator('.overlay-card').first).to_contain_text(expected['cn']['date'],timeout=45000)
 for market in ['cn','us']:
  if market=='us': page.get_by_role('button',name='美股 × 10Y',exact=True).click()
  page.wait_for_function("document.querySelectorAll('.overlay-card [_echarts_instance_]').length>=1")
  chart=page.evaluate('''async()=>{
   const url=performance.getEntriesByType('resource').map(e=>e.name).find(x=>x.includes('/echarts.js?'));
   const echarts=await import(url);
   const el=document.querySelector('.overlay-card [_echarts_instance_]');
   const o=echarts.getInstanceByDom(el).getOption();
   const s=o.series.find(s=>s.name.includes('股债差'));
   return {name:s.name,connectNulls:s.connectNulls,showSymbol:s.showSymbol,showAllSymbol:s.showAllSymbol,priceAxes:[...new Set(o.series.filter(s=>['上证指数','沪深300'].includes(s.name)).map(s=>s.yAxisIndex))].length,values:s.data,dates:o.xAxis[0].data};
  }''')
  pairs=list(zip(chart['dates'],chart['values']))
  lookup=dict(pairs)
  e=expected[market]
  assert abs(lookup[e['date']]-e['value'])<1e-10, (market,lookup[e['date']],e)
  assert chart['connectNulls']==False
  assert chart['showSymbol']==True
  assert chart['showAllSymbol']==True
  if market=='cn': assert chart['priceAxes']==1
  if market=='cn':
   canonical={point['date']:point['value'] for point in cn['points']}
   assert all(v==canonical.get(d) for d,v in pairs)
   assert any(v is None for _,v in pairs)
  result['checks'].append(f'{market} overlay dates/values match canonical data with null gaps and visible points')
  page.wait_for_timeout(1200)  # let the chart's enter animation finish before visual evidence
  page.locator('.overlay-card').first.screenshot(path=str(ROOT/f'after-overlay-{market}.png'))
 assert not result['pageErrors'],result['pageErrors']
 # Isolated source failure must not display the incompatible snapshot ERP.
 failed=b.new_context(viewport={'width':1440,'height':1000},locale='zh-CN')
 failed.route('**/api/fundamentals/erp-cn-reference',lambda route:route.fulfill(status=503,content_type='application/json',body='{"detail":"verification source unavailable"}'))
 f=failed.new_page()
 f.goto(BASE+'/fundamentals#fund-sec-rates',wait_until='domcontentloaded')
 unavailable=f.locator('.macro-card').filter(has=f.locator('.macro-name',has_text='沪深300股债利差'))
 expect(unavailable.locator('.macro-value')).to_have_text('暂不可用',timeout=45000)
 expect(unavailable).to_contain_text('来源读取失败')
 assert '6.30' not in unavailable.inner_text()
 f.goto(BASE+'/',wait_until='domcontentloaded')
 expect(f.locator('[data-overview-card="erp-cn"] .moa-erp-value strong')).to_have_text('—',timeout=45000)
 result['checks'].append('CN source 503: no competing snapshot fallback in rates/home')
 failed.close()
 # Desktop width and actual usable summary position.
 page.goto(BASE+'/',wait_until='domcontentloaded')
 expect(page.locator('[data-overview-card="erp-us"] .moa-erp-value strong')).to_have_text(f"{expected['us']['value']:.2f}",timeout=45000)
 for width in [1280,1440,1920]:
  page.set_viewport_size({'width':width,'height':1000})
  assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth')
 result['checks'].append('desktop 1280/1440/1920 no page horizontal overflow')
 b.close()
(ROOT/'ui-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps(result,ensure_ascii=False,indent=2))
