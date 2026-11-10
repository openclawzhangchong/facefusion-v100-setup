---
name: facefusion-face-swap
description: 给口播视频换脸（把视频里的人脸换成指定照片的人脸）。本机为 Tesla V100（Volta sm_70/TCC）+ Windows + FaceFusion（全中文界面）。当用户给出视频+照片并要求换脸时使用本技能；覆盖环境自检、V100 专用一键安装、命令行换脸、产物校验、报错速查。
---

# 任务：口播视频换脸

用户只提供两样东西，缺哪个就先向用户要哪个，**不要猜路径**：

- **照片** = 要换上去的脸（FaceFusion 的 SOURCE / 素材人脸）
- **视频** = 口播原片（TARGET / 目标）

## 本机硬性事实（不可违反）

- FaceFusion 安装于 `D:\FaceFusion`，venv 解释器 `D:\FaceFusion\.venv\Scripts\python.exe`
- 显卡 Tesla V100（Volta sm_70，TCC 模式）：版本**锁定**为 `onnxruntime-gpu==1.20.2` + `nvidia-cudnn-cu12==9.3.0.75`，任何升级/重装都会触发 `no kernel image is available for execution on the device`
- 9 个模型已下载齐全（`D:\FaceFusion\.assets\models`），不需要联网下载
- 资产仓库（文档与脚本）：https://github.com/openclawzhangchong/facefusion-v100-setup —— 遇到任何报错，先按仓库里 **PITFALLS.md** 的错误签名 grep 定位，**禁止**盲目重装环境

## 步骤 0：环境自检

- `D:\FaceFusion\facefusion.py` 存在 → 跳到步骤 2
- 不存在（新机器）→ 执行：
  ```powershell
  git clone https://github.com/openclawzhangchong/facefusion-v100-setup.git D:\ff-setup
  powershell -ExecutionPolicy Bypass -File D:\ff-setup\install.ps1      # 幂等一键安装
  powershell -ExecutionPolicy Bypass -File D:\ff-setup\verify.ps1       # 端到端验证
  ```
- 红线：不要运行 FaceFusion 自带的 `install.py`；不要升级 onnxruntime/cuDNN；不要用 conda

## 步骤 1：检查素材

- 照片：单张、清晰、脸部角度与视频里的人接近
- 视频：确认文件能读取、格式为常见视频（mp4/mov/mkv 等）

## 步骤 2：命令行换脸（不要开浏览器 GUI）

PowerShell 执行（PATH 三件事缺一不可：venv、NVIDIA 运行库 DLL、WinGet Links——否则 ffmpeg 报未安装或 onnxruntime 静默回退 CPU 慢 20 倍）：

```powershell
$sp = 'D:\FaceFusion\.venv\Lib\site-packages\nvidia'
$env:Path = "D:\FaceFusion\.venv\Scripts;$sp\cublas\bin;$sp\cudnn\bin;$sp\cufft\bin;$sp\cuda_runtime\bin;$sp\nvjitlink\bin;$sp\cuda_nvrtc\bin;$env:LOCALAPPDATA\Microsoft\WinGet\Links;" + $env:Path
Set-Location D:\FaceFusion
D:\FaceFusion\.venv\Scripts\python.exe facefusion.py headless-run `
  -s "<照片路径>" `
  -t "<视频路径>" `
  -o "<输出路径，建议与原视频同目录、文件名加_换脸.mp4>" `
  --processors face_swapper face_enhancer `
  --face-swapper-model hyperswap_1a_256 `
  --face-mask-types box occlusion `
  --execution-providers cuda --download-providers huggingface
```

参数说明（用户视角）：`face_swapper` 换脸 + `face_enhancer` 脸部修复（顺序固定：先换后修）；`box occlusion` 蒙版防止手挡脸时穿帮。

- 处理速度：240p 实测约 30 帧/秒（几分钟出片）；1080p 长视频可能 10 分钟以上
- **超时给足，不要中途杀进程**，以输出文件为准

## 步骤 3：校验产物

1. 输出文件存在且 >100KB（PowerShell 会把 tqdm/pip 的 stderr 进度当错误显示 `Exited with code 1`——**exit code 不算数，看文件**，见 PITFALLS.md #8）
2. 对比时长与原视频一致：
   ```powershell
   ffprobe -v error -show_entries format=duration -of default=nw=1 "<输出路径>"
   ```

## 步骤 4：用中文向用户汇报

- 输出文件的完整路径
- 处理耗时；若画质不理想，提示可加画面增强（frame_enhancer）或提高脸修混合度再跑一次
- 提醒：换脸只替换脸部，**不含头发**

## 报错速查

所有已知坑（Volta 内核缺失、cuDNN 前端、静默回退 CPU、模型下载失败、PowerShell 假错误等）都在仓库 PITFALLS.md，每条含【症状/错误签名/原因/解法】，拿报错文本去 grep 即可。`sitecustomize_err.log` 只关系到界面语言，与本任务无关。
