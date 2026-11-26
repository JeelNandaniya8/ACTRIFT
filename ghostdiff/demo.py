"""Disposable demonstration apps: a redesign with three planted regressions."""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
import base64


def pdf_bytes():
    stream=b'BT /F1 18 Tf 50 720 Td (Ghostdiff sample report) Tj ET'
    objects=[b'<< /Type /Catalog /Pages 2 0 R >>',b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',b'<< /Length '+str(len(stream)).encode()+b' >>\nstream\n'+stream+b'\nendstream']
    out=b'%PDF-1.4\n'; offsets=[0]
    for i,obj in enumerate(objects,1):
        offsets.append(len(out)); out+=f'{i} 0 obj\n'.encode()+obj+b'\nendobj\n'
    x=len(out); out+=f'xref\n0 {len(offsets)}\n0000000000 65535 f \n'.encode()
    for offset in offsets[1:]: out+=f'{offset:010} 00000 n \n'.encode()
    return out+f'trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{x}\n%%EOF\n'.encode()


def app(broken=False, redesign=False):
    history='' if broken else '<button id="history">Search history</button>'
    extra='<button id="help">Help</button>' if broken else ''
    controls='<button id="export">Export PDF</button>'+history+'<button id="save">Save note</button><button id="theme">Toggle theme</button>'+extra
    if redesign or broken: controls='<button id="theme">Toggle theme</button><button id="save">Save note</button>'+history+'<button id="export">Export PDF</button>'+extra
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Notes demo</title>
<style>body{{font:16px system-ui;max-width:760px;margin:60px auto;padding:24px;background:{'#e5edff' if redesign or broken else '#f5f3ee'};color:#212634}} button{{padding:12px;margin:8px;border:1px solid #9ba6b6;border-radius:8px;background:white}} .dark{{background:#172338;color:white}}</style></head><body><h1>Notes workspace</h1><main>{controls}</main><p id="themeState">Theme: light</p><p id="note">Note: unsaved</p><p id="historyState"></p><p id="helpState"></p>
<script>
const broken={str(broken).lower()}; const $=id=>document.getElementById(id);
let dark=!broken && localStorage.getItem('theme')==='dark';
function paint(){{document.body.classList.toggle('dark',dark);$('themeState').textContent='Theme: '+(dark?'dark':'light');}}
paint(); if(localStorage.getItem('note')==='saved')$('note').textContent='Note: saved';
$('theme').onclick=()=>{{dark=!dark;if(!broken)localStorage.setItem('theme',dark?'dark':'light');paint();}};
$('save').onclick=()=>{{localStorage.setItem('note','saved');$('note').textContent='Note: saved';}};
if($('history'))$('history').onclick=()=>{{$('historyState').textContent='Last search: logic';}};
if($('help'))$('help').onclick=()=>{{$('helpState').textContent='Help opened';}};
$('export').onclick=()=>{{if(broken)return;const raw=atob('{base64.b64encode(pdf_bytes()).decode()}');const blob=new Blob([Uint8Array.from(raw,x=>x.charCodeAt(0))],{{type:'application/pdf'}});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='report.pdf';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);}};
</script></body></html>'''.encode()


@contextmanager
def serve(content):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path != '/':
                self.send_error(404);return
            self.send_response(200); self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(content)));self.end_headers();self.wfile.write(content)
        def log_message(self,*args): pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    try: yield f'http://127.0.0.1:{server.server_port}/'
    finally: server.shutdown();server.server_close();thread.join()
