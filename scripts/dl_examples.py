#!/usr/bin/env python3
"""下载 FaceFusion 官方示例素材（verify.ps1 冒烟测试用）。

用法：python dl_examples.py [examples_dir]
默认 examples_dir = D:/FaceFusion/.assets/examples
"""
import os
import sys
import urllib.request

DEST = sys.argv[1] if len(sys.argv) > 1 else r'D:\FaceFusion\.assets\examples'
URLS = [
    'https://hf-mirror.com/facefusion/examples-3.0.0/resolve/main/{f}',
    'https://github.com/facefusion/facefusion-assets/releases/download/examples-3.0.0/{f}',
]
FILES = ['source.jpg', 'target-240p.mp4']

os.makedirs(DEST, exist_ok=True)
failed = False
for f in FILES:
    dest = os.path.join(DEST, f)
    if os.path.isfile(dest) and os.path.getsize(dest) > 0:
        print('exists', f)
        continue
    ok = False
    for u in URLS:
        try:
            req = urllib.request.Request(u.format(f=f), headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=30) as r, open(dest + '.tmp', 'wb') as o:
                while True:
                    c = r.read(1 << 20)
                    if not c:
                        break
                    o.write(c)
            os.replace(dest + '.tmp', dest)
            print('OK', f, os.path.getsize(dest), 'bytes')
            ok = True
            break
        except Exception as e:
            print('fail', u.split('/')[2], type(e).__name__)
    if not ok:
        failed = True

sys.exit(1 if failed else 0)
