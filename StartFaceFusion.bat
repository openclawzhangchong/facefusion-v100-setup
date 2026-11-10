@echo off
rem FaceFusion launcher - V100 CUDA version
rem 说明：PATH 必须注入 NVIDIA 运行库 DLL 目录，否则 onnxruntime 静默回退 CPU
setlocal
set FF_ROOT=D:\FaceFusion
set VENV=%FF_ROOT%\.venv\Scripts
set NVIDIA=%FF_ROOT%\.venv\Lib\site-packages\nvidia

set PATH=%VENV%;%NVIDIA%\cublas\bin;%NVIDIA%\cudnn\bin;%NVIDIA%\cufft\bin;%NVIDIA%\cuda_runtime\bin;%NVIDIA%\nvjitlink\bin;%NVIDIA%\cuda_nvrtc\bin;%LOCALAPPDATA%\Microsoft\WinGet\Links;%PATH%

cd /d %FF_ROOT%
python facefusion.py run
pause
