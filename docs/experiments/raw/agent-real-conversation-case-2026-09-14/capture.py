import json,urllib.request
from pathlib import Path
OUT=Path(__file__).parent
rows=json.load(urllib.request.urlopen('http://127.0.0.1:8016/api/agent/sessions/sess_592bede94f5b/messages',timeout=8))
(OUT/'conversation.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
for row in rows:
 if row['role']=='assistant':print(row.get('message_id'),row.get('grounded'),row['content'][:6000])
