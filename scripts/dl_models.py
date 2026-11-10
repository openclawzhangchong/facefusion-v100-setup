#!/usr/bin/env python3
"""FaceFusion 必需模型定向下载（V100/Volta 资产包专用）。

- 只下载换脸流水线真正需要的模型（FaceFusion 自带 force-download 会被
  fairface/hrffa 等可选模型的网络失败中断）。
- 下载源：hf-mirror.com 优先（大陆稳定），GitHub 兜底，逐文件重试。
- 校验：FaceFusion 的 hash 文件是 CRC32 的 8 位十六进制（不是 SHA256）。

用法：python dl_models.py [models_dir]
默认 models_dir = D:/FaceFusion/.assets/models
"""
import os
import sys
import time
import urllib.request
import zlib

BASE = sys.argv[1] if len(sys.argv) > 1 else 'D:/FaceFusion/.assets/models'
URL_TEMPLATES = [
    'https://hf-mirror.com/facefusion/{base}/resolve/main/{file}',
    'https://github.com/facefusion/facefusion-assets/releases/download/{base}/{file}',
]
MODELS = [
    ('models-3.0.0', 'yoloface_8n'),          # 人脸检测（默认）
    ('models-3.0.0', '2dfan4'),               # 68 点关键点（默认）
    ('models-3.0.0', 'fan_68_5'),             # 次级关键点（换脸精修对齐）
    ('models-3.0.0', 'arcface_w600k_r50'),    # 人脸识别（默认）
    ('models-3.0.0', 'gfpgan_1.4'),           # 脸部修复（默认）
    ('models-3.0.0', 'bisenet_resnet_34'),    # 区域蒙版解析（默认）
    ('models-3.0.0', 'kim_vocal_2'),          # 人声分离（输出视频含音轨时用）
    ('models-3.3.0', 'hyperswap_1a_256'),     # 换脸模型（默认）
    ('models-3.1.0', 'xseg_1'),               # 遮挡蒙版（默认）
]


def crc32_of(path):
    crc = 0
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            crc = zlib.crc32(chunk, crc)
    return format(crc & 0xFFFFFFFF, '08x')


def fetch(url, dest, retries=4):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=30) as r, open(dest + '.tmp', 'wb') as f:
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk:
                        break
                    f.write(chunk)
            os.replace(dest + '.tmp', dest)
            return True
        except Exception as e:
            print(f'    attempt {attempt + 1} failed: {type(e).__name__}: {str(e)[:120]}', flush=True)
            time.sleep(3)
    return False


def valid(name):
    onnx = os.path.join(BASE, name + '.onnx')
    hash_path = os.path.join(BASE, name + '.hash')
    if not (os.path.isfile(onnx) and os.path.isfile(hash_path)):
        return False
    with open(hash_path) as f:
        expected = f.read().strip()
    return crc32_of(onnx) == expected


def main():
    os.makedirs(BASE, exist_ok=True)
    for rnd in range(1, 6):
        todo = [name for _, name in MODELS if not valid(name)]
        if not todo:
            print(f'ALL MODELS OK (checked round {rnd})')
            break
        print(f'--- round {rnd}: {len(todo)} item(s) pending ---', flush=True)
        for base, name in MODELS:
            if name not in todo:
                continue
            for suffix in ('.hash', '.onnx'):
                dest = os.path.join(BASE, name + suffix)
                ok = False
                for tpl in URL_TEMPLATES:
                    url = tpl.format(base=base, file=name + suffix)
                    print(f'  {name}{suffix} <- {url.split("/")[2]}', flush=True)
                    if fetch(url, dest):
                        ok = True
                        break
                if not ok:
                    print(f'  ERR {name}{suffix}: all providers failed')
            if valid(name):
                print(f'  OK  {name} ({os.path.getsize(os.path.join(BASE, name + ".onnx")) / 1048576:.1f} MB)')
            elif os.path.isfile(os.path.join(BASE, name + '.onnx')):
                print(f'  BAD {name}: crc mismatch, removed')
                os.remove(os.path.join(BASE, name + '.onnx'))
    else:
        print('WARNING: some models still missing after 5 rounds')

    print()
    print('=== FINAL STATUS ===')
    failed = False
    for _, name in MODELS:
        if valid(name):
            print(f'PASS {name} ({os.path.getsize(os.path.join(BASE, name + ".onnx")) / 1048576:.1f} MB)')
        else:
            print(f'FAIL {name}')
            failed = True
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
