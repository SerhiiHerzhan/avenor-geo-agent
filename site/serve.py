#!/usr/bin/env python3
"""Local static development server with real 404 responses."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

class Handler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','strict-origin-when-cross-origin')
        super().end_headers()

    def do_GET(self):
        if urlsplit(self.path).path in ['/ua','/pl']:
            self.send_response(301)
            self.send_header('Location',urlsplit(self.path).path+'/')
            self.send_header('Content-Length','0')
            self.end_headers()
            return
        return super().do_GET()

    def send_error(self,code,message=None,explain=None):
        file=Path(self.directory)/'404.html'
        if code!=404 or not file.is_file():
            return super().send_error(code,message,explain)
        payload=file.read_bytes()
        self.send_response(404)
        self.send_header('Content-Type','text/html; charset=utf-8')
        self.send_header('Content-Length',str(len(payload)))
        self.end_headers()
        if self.command!='HEAD':
            self.wfile.write(payload)

    def list_directory(self,path):
        self.send_error(404)
        return None

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--port',type=int,default=8000)
    p.add_argument('--host',default='127.0.0.1')
    p.add_argument('--directory',default=str(Path(__file__).parent/'dist'))
    args=p.parse_args()
    server=ThreadingHTTPServer((args.host,args.port),partial(Handler,directory=args.directory))
    print(f'Avenor local static server on port {args.port}',flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()
