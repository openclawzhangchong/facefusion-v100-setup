# 坑速查表（PITFALLS）

> 给 AI agent：遇到报错先用本文的错误签名 grep 定位。每条含【症状 / 原因 / 解法】。

---

## 1. onnxruntime / Volta 内核缺失（最核心的坑）

【症状 / 错误签名】
```
cudaErrorNoKernelImageForDevice : no kernel image is available for execution on the device
```
出现在 `QuickGelu`、`Conv` 等节点上。

【原因】V100 是 Volta 架构（sm_70）。**onnxruntime-gpu ≥1.21 官方编译的 CUDA 内核不再包含 sm_70**。1.24.4 必现。

【解法】锁定 `onnxruntime-gpu==1.20.2`（1.20.2 实测通过，见 pins.txt）。

【验证方法】用 `scripts/test_cudnn.py` 对真实模型（yoloface_8n.onnx）推理，不能只看 providers 列表——见第 3 条。

---

## 2. cuDNN 9.x 卷积前端不支持 Volta

【症状 / 错误签名】
```
CUDNN_FE failure 11: CUDNN_BACKEND_API_FAILED
err 209 no kernel image is available for execution on the device
```
出现在 Conv 节点（如 `/model.0/conv/Conv`），即使 ORT 版本正确也会出现（若 cuDNN 太新）。

【原因】新版 cuDNN（实测 9.28）的 graph frontend 已无 Volta 内核。

【解法】锁定 `nvidia-cudnn-cu12==9.3.0.75`（9.5.1.17 也实测可用）。

---

## 3. onnxruntime-gpu 静默回退 CPU（性能陷阱）

【症状】无报错，但处理速度慢 20 倍以上。启动时若看到 DLL 缺失警告：
```
Error loading "onnxruntime_providers_cuda.dll" which depends on "cublasLt64_12.dll" which is missing
```
【原因】PyPI 的 onnxruntime-gpu wheel **不自带** CUDA 运行库（cublas/cudnn/cufft）；缺失时 ORT 静默用 CPU 继续，FaceFusion 照常出结果——极易误以为装好了。

【解法】pip 安装 NVIDIA 运行库（见 pins.txt），并把
`<venv>\Lib\site-packages\nvidia\{cublas,cudnn,cufft,cuda_runtime,nvjitlink,cuda_nvrtc}\bin`
加入 PATH（StartFaceFusion.bat 已内置）。

【验证方法】`sess.get_providers()[0]` 必须是 `CUDAExecutionProvider`；`get_available_providers()` **不算数**（DLL 缺失时它照样列出 CUDA）。

---

## 4. FaceFusion install.py 的三个坑

- 【症状】`conda is not activated` → 【解法】加 `--skip-conda`，或者干脆**不用 install.py**（本仓库方案）。
- 【症状】依赖被装进**系统 Python**（路径出现 `Python313\Lib\site-packages`）→【原因】`uv venv` 默认不装 pip，install.py 里 `shutil.which('pip')` 落到系统 pip →【解法】用 `uv pip install` 直装 venv（本仓库方案），顺带把系统 Python 被降级的包恢复（pillow/pydantic/starlette/pydantic-core）。
- 【症状】脚本静默失败 → install.py 会把 onnxruntime-gpu 升到 1.24.4 → 触发第 1 条坑。

【结论】**不要运行 install.py**，用本仓库 install.ps1。

---

## 5. FaceFusion 模型下载失败（网络 + 上游连环坑）

【症状 / 错误签名】
```
[FACEFUSION.DOWNLOAD] validating hash for fairface failed
[FACEFUSION.DOWNLOAD] validating source for hrffa failed
```
【原因】三个因素叠加：
1. GitHub 直连不稳（超时、connection reset、curl 000）；
2. huggingface.co 在大陆不可达，但 FaceFusion 的 huggingface 源**内置了 hf-mirror.com 备选**（`facefusion/choices.py` 的 `download_provider_set`）；
3. `force-download` 顺序下载全部模型，**fairface / hrffa 这类可选模型失败会中断后续全部下载**，且它们失败≠换脸必需模型有问题（换脸真正需要的只有 9 个模型）。

【解法】
- `facefusion.ini` 写 `download_providers = huggingface`（自动用 hf-mirror）；
- 用 `scripts/dl_models.py` 定向下载必需模型（hf-mirror 优先、GitHub 兜底、逐文件重试）。

---

## 6. 哈希校验用 CRC32，不是 SHA256

【症状】自己写的校验逻辑对所有文件都报 hash mismatch。
【原因】FaceFusion 的 hash 文件内容是 `zlib.crc32` 的 8 位十六进制（见 `facefusion/hash_helper.py`），不是完整 SHA256。
【解法】校验代码用：`format(zlib.crc32(content) & 0xFFFFFFFF, '08x')`（scripts/dl_models.py 已实现）。

---

## 7. TCC 模式（Tesla 数据中心卡）

【事实】`nvidia-smi --query-gpu=driver_model.current` 返回 `TCC`。
【影响】
- DirectML / DirectX 不可用 → `--execution-providers directml` 方案不可行，只能 CUDA；
- 无显示输出，显示器走核显——正常现象，不是故障。

---

## 8. PowerShell 的假错误（agent 特别注意）

【症状】命令输出 `Exited with code 1` + `NativeCommandError`，但实际成功。
【原因】pip/tqdm 把进度和升级提示写 **stderr**，PowerShell 5.1 的 `2>&1 |` 管道把它当错误记录。
【解法】判断成败看产物（文件存在、内容正确、`get_providers()`），不要只看 exit code。

---

## 9. 环境杂项

- Python 3.13 不被 FaceFusion 支持（CI 只测 3.12）→ 用 `uv venv --python 3.12`（uv 会自动下载 3.12 独立解释器；若因 GitHub 网络下载失败，重试即可）。
- C 盘空间小（<25GB）→ 一切装 D 盘。
- 内存 16 GB 刚够，重度任务前关闭吃内存的程序。
- ffmpeg 用 winget 装（`Gyan.FFmpeg`），装完的命令行别名在 `%LOCALAPPDATA%\Microsoft\WinGet\Links`，**已开的进程 PATH 里没有它**，新 shell/脚本里要显式加入。

---

## 10. sitecustomize 里 import facefusion 失败（界面中文化补丁静默失效）

【症状 / 错误签名】
`sitecustomize` 已随解释器加载（`'sitecustomize' in sys.modules` 为 `True`），
但补丁未生效（`translator.get` 仍返回英文），且 `except: pass` 吞掉了真实异常。

【原因】sitecustomize 在 **site 初始化阶段**执行；Python 3.11+ 在 site 初始化
**之后**才把脚本目录/cwd 加入 sys.path。所以即使启动命令的 cwd 就是
FaceFusion 根目录，此刻 `import facefusion` 也必然 `ImportError`。

【解法】不要依赖 cwd：sitecustomize 固定部署在
`<FaceFusion根>\.venv\Lib\site-packages\`，从 `__file__` 向上三级就是
FaceFusion 根目录，自行 `sys.path.insert` 后再 import。
另外：补丁的异常处理务必把 `traceback.format_exc()` 写入日志文件，
不要静默 pass（本仓库的 sitecustomize.py 会写 sitecustomize_err.log）。

---

## 11. 补丁包装 gradio 组件构造器后，label/choices 从界面消失

【症状 / 错误签名】
给 `gradio.Dropdown/CheckboxGroup/Radio.__init__` 打补丁（例如把 choices
包装成 (中文标签, 值) 二元组）后，界面里**带选项的组件整块变空**：
`/config` 里这些组件没有 `label`、没有 `choices`，只有 `name`/`proxy_url`。
滑块、按钮等未打补丁的组件正常。

【原因】gradio 的 `Block.get_config()`（blocks.py）用
`inspect.signature(self.__class__.__init__)` 的**参数名**决定把哪些实例属性
序列化进 /config。包装函数若定义成 `def patched(self, *args, **kwargs)`，
签名只剩 args/kwargs，gradio 认不出 label/choices 等参数名 → 全部不序列化。

【解法】包装函数必须用 `@functools.wraps(original_init)` 装饰——
`inspect.signature` 默认顺着 `__wrapped__` 还原真实签名，get_config 即恢复。
（另注意循环里给多个类打补丁时要用工厂函数绑定各自的 original_init，
否则闭包共享变量会让所有类调到最后一个类的构造器，报
`super(type, obj): obj must be an instance or subtype of type`。）
