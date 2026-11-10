#!/usr/bin/env python3
"""真实模型推理验证（V100 资产包）——Volta 兼容性的终极判据。

对 FaceFusion 默认人脸检测模型 yoloface_8n.onnx 在 CUDA EP 上做一次
640x640 前向推理。它会同时踩到：
- onnxruntime 自带内核（QuickGelu 融合节点，ORT ≥1.21 无 sm_70 会炸）；
- cuDNN 卷积前端（cuDNN ≥9.28 在 Volta 上炸）。
两者任一不兼容都会在本脚本暴露。

用法：python test_cudnn.py [yoloface_onnx_path]
默认 D:\FaceFusion\.assets\models\yoloface_8n.onnx（须已由 dl_models.py 下载）
"""
import sys

import numpy as np
import onnxruntime as ort

model_path = sys.argv[1] if len(sys.argv) > 1 else r'D:\FaceFusion\.assets\models\yoloface_8n.onnx'
try:
    sess = ort.InferenceSession(model_path, providers=['CUDAExecutionProvider'])
    inp = {i.name: np.random.rand(1, 3, 640, 640).astype(np.float32) for i in sess.get_inputs()}
    outs = sess.run(None, inp)
    print('CUDNN OK:', sess.get_providers()[0], '| outputs:', [o.shape for o in outs][:3])
except Exception as e:
    print('CUDNN FAIL:', str(e)[:300])
    sys.exit(1)
