#!/usr/bin/env python3
r"""向 facefusion.ini 幂等写入 V100 专用默认配置。

- [execution] execution_providers = cuda      （TCC 卡只有 CUDA 一条路）
- [download]  download_providers = huggingface（其内置 hf-mirror.com，大陆可达）

用法：python patch_facefusion_ini.py [ini_path]
默认 D:\FaceFusion\facefusion.ini
"""
import sys

ini_path = sys.argv[1] if len(sys.argv) > 1 else r'D:\FaceFusion\facefusion.ini'
PATCHES = {
    'execution': {'execution_providers': 'cuda'},
    'download': {'download_providers': 'huggingface'},
}

with open(ini_path, encoding='utf-8') as f:
    lines = f.readlines()

section = None
report = []  # (key, status)
out = []
for line in lines:
    stripped = line.strip()
    if stripped.startswith('[') and stripped.endswith(']'):
        section = stripped[1:-1]
    patched = False
    if section in PATCHES and '=' in stripped:
        key = stripped.split('=')[0].strip()
        if key in PATCHES[section]:
            value = PATCHES[section][key]
            if stripped == f'{key} = {value}':
                report.append((key, 'already set'))
            else:
                report.append((key, f'set -> {value}'))
            out.append(f'{key} = {value}\n')
            patched = True
    if not patched:
        out.append(line)

with open(ini_path, 'w', encoding='utf-8') as f:
    f.writelines(out)

for key, status in report:
    print(f'{ini_path}: {key}: {status}')
