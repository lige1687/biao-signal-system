"""Download only identified public research sources; no market data or account access."""
import concurrent.futures,hashlib,json,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parent
SOURCES=[
('jeon2025','https://media.researchaffiliates.com/1099_stop_the_losses_e389db6127.pdf','pdf'),
('joubert2024','https://www.hillsdaleinv.com/uploads/The_Three_Types_of_Backtests.pdf','pdf'),
('rink2023','https://www.econstor.eu/bitstream/10419/312389/1/s11408-023-00433-2.pdf','pdf'),
('sepp2026','https://arxiv.org/html/2607.19497v1','html'),
('kang2026','https://www.mdpi.com/1911-8074/19/8/554/xml','xml'),
('anarkulova2025_march','https://www.icpmnetwork.com/wp-content/uploads/2025/09/1.Beyond-the-Status-Quo-A-Critical-Assessment-of-Lifecycle-Investment-Advice.pdf','pdf')]
def fetch(row):
    key,url,ext=row
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Research source reading'}),timeout=25) as r: body=r.read();ctype=r.headers.get('Content-Type','')
        if ext=='pdf' and not body.startswith(b'%PDF'):raise ValueError('Response is not a PDF')
        p=ROOT/(key+'.'+ext);p.write_bytes(body)
        return {'id':key,'url':url,'path':str(p),'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest(),'content_type':ctype,'status':'downloaded'}
    except Exception as e:return {'id':key,'url':url,'status':'unavailable','reason':str(e)}
if __name__=='__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(fetch,SOURCES))
    (ROOT/'source-files.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(results,ensure_ascii=False,indent=2))
