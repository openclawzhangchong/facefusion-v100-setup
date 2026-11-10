#!/usr/bin/env python3
"""onnxruntime CUDA EP 基础探活（V100 资产包）。

验证两件事：
1. CUDAExecutionProvider 能否真正加载（DLL 齐全，不会静默回退 CPU）；
2. CUDA 上算子能跑且结果正确（Gemm）。

注意：必须先把 NVIDIA 运行库 DLL 目录加入 PATH（见 StartFaceFusion.bat），
否则本脚本会看到 "available providers 里有 CUDA" 但实际回退 CPU——这正是
第 3 号坑。本脚本用 get_providers()[0]（实际启用者）做判定。
"""
import os
import sys
import tempfile

import numpy as np
import onnx
import onnxruntime as ort
from onnx import TensorProto, helper

MODEL_PATH = os.path.join(tempfile.gettempdir(), 'ffv100_test_gemm.onnx')

if not os.path.isfile(MODEL_PATH):
    A = helper.make_tensor_value_info('A', TensorProto.FLOAT, [4, 4])
    B = helper.make_tensor_value_info('B', TensorProto.FLOAT, [4, 4])
    C = helper.make_tensor_value_info('C', TensorProto.FLOAT, [4, 4])
    node = helper.make_node('Gemm', ['A', 'B', 'C'], ['D'])
    out = helper.make_tensor_value_info('D', TensorProto.FLOAT, [4, 4])
    graph = helper.make_graph([node], 'test', [A, B, C], [out])
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid('', 13)])
    model.ir_version = 8
    onnx.save(model, MODEL_PATH)

try:
    sess = ort.InferenceSession(
        MODEL_PATH,
        providers=['CUDAExecutionProvider', 'CPUExecutionProvider'],
    )
    active = sess.get_providers()[0]
    print('available providers:', ort.get_available_providers())
    print('active provider:', active)
    a = np.random.rand(4, 4).astype(np.float32)
    b = np.random.rand(4, 4).astype(np.float32)
    c = np.random.rand(4, 4).astype(np.float32)
    d = sess.run(None, {'A': a, 'B': b, 'C': c})[0]
    assert np.allclose(d, a @ b + c, atol=1e-4), 'result mismatch'
    print('CUDA inference OK, result correct')
    if active != 'CUDAExecutionProvider':
        print('FAIL: CUDA provider listed but NOT active (DLL missing? see PITFALLS.md #3)')
        sys.exit(1)
except Exception as e:
    print('CUDA FAILED:', type(e).__name__, str(e)[:500])
    sys.exit(1)
