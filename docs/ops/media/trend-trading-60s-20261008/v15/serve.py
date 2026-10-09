import http.server,functools,json,re,sys
from pathlib import Path
v=Path(__file__).resolve().parent
root=Path(json.loads((v/'storage-plan.json').read_text())['out'])
class Handler(http.server.SimpleHTTPRequestHandler):
    def send_head(self):
        target=Path(self.translate_path(self.path))
        if not target.is_file() or 'Range' not in self.headers:
            return super().send_head()
        size=target.stat().st_size
        match=re.fullmatch(r'bytes=(\d+)-(\d*)',self.headers['Range'])
        if not match:
            self.send_error(416);return None
        start=int(match.group(1));end=min(int(match.group(2)) if match.group(2) else size-1,size-1)
        if start>end:
            self.send_error(416);return None
        f=target.open('rb');f.seek(start)
        self.send_response(206);self.send_header('Content-Type',self.guess_type(str(target)))
        self.send_header('Content-Length',str(end-start+1));self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
        self.send_header('Accept-Ranges','bytes');self.end_headers();self.remaining=end-start+1
        return f
    def copyfile(self,source,outputfile):
        remaining=getattr(self,'remaining',None)
        if remaining is None:return super().copyfile(source,outputfile)
        try:
            while remaining>0:
                chunk=source.read(min(65536,remaining))
                if not chunk:break
                outputfile.write(chunk);remaining-=len(chunk)
        except (BrokenPipeError,ConnectionResetError):pass
http.server.ThreadingHTTPServer(('127.0.0.1',8783),functools.partial(Handler,directory=str(root))).serve_forever()
