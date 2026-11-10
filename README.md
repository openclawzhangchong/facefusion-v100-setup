# FaceFusion V100/Volta 安装资产包

> 目的：在**同配置电脑**上，让任何 AI agent（或人）拉取本仓库后，按文档+脚本一键复现 FaceFusion 的完整安装与 GPU 验证，**不再踩我们已经踩过的坑**。

## 实测环境（本仓库的"同配置"基准）

| 组件 | 配置 |
|---|---|
| GPU | NVIDIA Tesla V100-PCIE-32GB（Volta，sm_70，**TCC 模式**） |
| CPU / 内存 | i5-12400 / 16 GB |
| 系统 | Windows 10 专业版，C 盘空间小（模型、环境一律装 D 盘） |
| 网络 | 中国大陆，GitHub 直连**时通时断**，huggingface.co 不通，**hf-mirror.com 稳定** |

## 给 AI agent 的快速指引

```powershell
# 1. 克隆本仓库到任意目录
git clone https://github.com/openclawzhangchong/facefusion-v100-setup.git
cd facefusion-v100-setup

# 2. 一键安装（幂等，可重复执行；默认装到 D:\FaceFusion）
powershell -ExecutionPolicy Bypass -File .\install.ps1

# 3. 端到端验证（CUDA 推理 + 真实换脸冒烟测试）
powershell -ExecutionPolicy Bypass -File .\verify.ps1
```

两条铁律：

1. **版本锁定不可违反**（见 [pins.txt](pins.txt) 与 [PITFALLS.md](PITFALLS.md)）：Volta 架构下 `onnxruntime-gpu` 必须 ≤1.20.2，`nvidia-cudnn-cu12` 必须 ≤9.5.x。装错版本的典型报错是 `no kernel image is available for execution on the device`。
2. **判断成功与否要看事实（artifact），不要只看 exit code**：PowerShell 会把 pip/tqdm 写到 stderr 的进度信息当成"错误"，导致明明成功却显示 `Exited with code 1`。

## 安装流程总览（install.ps1 实际做的事）

| # | 步骤 | 幂等条件 |
|---|---|---|
| 1 | 检查 Python（3.10–3.12）与 git，缺则用 winget 装 Python 3.12 | 检测命令存在 |
| 2 | `pip install uv`（Python 版本管理） | `uv --version` 可用 |
| 3 | `winget install Gyan.FFmpeg` | `ffmpeg` 可寻址 |
| 4 | `git clone --depth 1 https://github.com/facefusion/facefusion` 到 `D:\FaceFusion` | 目录已存在则跳过 |
| 5 | `uv venv .venv --python 3.12`（**不要用系统 Python 3.13**） | `.venv` 已存在 |
| 6 | `uv pip install -r requirements.txt`，再 `uv pip install onnxruntime-gpu==1.20.2`（顺序重要：gpu 包后装，覆盖同名 capi 文件），再装 NVIDIA 运行库（见 pins.txt） | 按锁定版本核对 |
| 7 | 运行 `scripts/dl_models.py` 定向下载 9 个必需模型（走 hf-mirror，CRC32 校验） | 模型齐全且校验通过 |
| 8 | `scripts/patch_facefusion_ini.py` 写入 `execution_providers=cuda`、`download_providers=huggingface` | 幂等改写 |
| 9 | 生成 `StartFaceFusion.bat` 启动器（PATH 注入 venv + NVIDIA DLL + ffmpeg） | 生成即含正确路径 |
| 10 | 验证：CUDA EP 探活 → 真实模型推理 → 示例素材换脸冒烟测试 | 见 verify.ps1 |

**注意：全程不需要运行 FaceFusion 自带的 `install.py`**（它默认要求 conda、且会把 onnxruntime-gpu 升回不兼容的 1.24.4）。依赖完全由本仓库的脚本安装。

## 日常使用

双击 `D:\FaceFusion\StartFaceFusion.bat` → 浏览器打开 `http://127.0.0.1:7860`。

**界面中文化**（install.ps1 已自动部署）：`scripts/zh_ui/sitecustomize.py`
作为运行时补丁放进 venv 的 site-packages，中文优先、缺失词条自动回退英文，
不改上游文件。补丁若异常会写入 `.venv\Lib\site-packages\sitecustomize_err.log`。

换脸要点（详细见 FaceFusion 仓库内的 `使用说明.md`，安装脚本会生成）：

- SOURCE 传目标人物照片（选头部角度与视频里相近的），TARGET 传口播视频
- 换脸只替换**脸部椭圆区域，不含头发**
- 开 `face_enhancer`（gfpgan）修复画质；手挡脸时开 `occlusion` 蒙版
- 实测速度：240p 视频 ~30 帧/秒

## 目录结构

```
├── README.md                  # 本文件
├── PITFALLS.md                # 坑速查表：错误签名 → 原因 → 解法（agent 可 grep）
├── pins.txt                   # 实测锁定的版本清单
├── install.ps1                # 一键幂等安装
├── verify.ps1                 # 端到端验证
├── StartFaceFusion.bat        # 启动器模板（安装时会按实际路径重生成）
├── LICENSE
└── scripts/
    ├── dl_models.py           # 必需模型定向下载（双源重试 + CRC32 校验）
    ├── dl_examples.py         # 官方示例素材下载（冒烟测试用）
    ├── test_cuda.py           # onnxruntime CUDA EP 基础探活
    ├── test_cudnn.py          # 真实人脸检测模型推理验证
    ├── patch_facefusion_ini.py# facefusion.ini 写入 cuda + 镜像源
    └── zh_ui/                 # 界面中文化：sitecustomize 运行时补丁 + zh_*.json 语言包
```

## 经验总结（一段话版）

这台 V100 的所有坑都源于三点：**Volta 架构太老**（新 onnxruntime/cuDNN 删了它的内核）、**TCC 数据中心卡模式**（只有 CUDA 一条路，且无显示输出）、**国内网络到 GitHub/HuggingFace 不稳**（模型下载必须走 hf-mirror 且要带重试）。每一条的具体症状与解法都在 [PITFALLS.md](PITFALLS.md)。
