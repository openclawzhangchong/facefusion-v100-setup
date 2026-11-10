# 端到端验证：CUDA 探活 → 真实模型推理 → 完整换脸冒烟测试
# 用法：powershell -ExecutionPolicy Bypass -File .\verify.ps1 [-InstallRoot D:\FaceFusion]
param(
    [string]$InstallRoot = 'D:\FaceFusion'
)

$RepoRoot = $PSScriptRoot
$VenvPython = Join-Path $InstallRoot '.venv\Scripts\python.exe'
$sp = Join-Path $InstallRoot '.venv\Lib\site-packages\nvidia'
$WinGetLinks = Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Links'
$env:Path = "$VenvPython;$sp\cublas\bin;$sp\cudnn\bin;$sp\cufft\bin;$sp\cuda_runtime\bin;$sp\nvjitlink\bin;$sp\cuda_nvrtc\bin;$WinGetLinks;" + $env:Path

$failures = @()

Write-Host '=== [1/3] CUDA ExecutionProvider 探活 ===' -ForegroundColor Cyan
& $VenvPython (Join-Path $RepoRoot 'scripts\test_cuda.py')
if ($LASTEXITCODE -ne 0) { $failures += 'CUDA EP 探活失败（PITFALLS #3）' }

Write-Host '=== [2/3] 真实模型推理（Volta 内核兼容性） ===' -ForegroundColor Cyan
& $VenvPython (Join-Path $RepoRoot 'scripts\test_cudnn.py') (Join-Path $InstallRoot '.assets\models\yoloface_8n.onnx')
if ($LASTEXITCODE -ne 0) { $failures += '模型推理失败（PITFALLS #1/#2）' }

Write-Host '=== [3/3] 完整换脸冒烟测试 ===' -ForegroundColor Cyan
& $VenvPython (Join-Path $RepoRoot 'scripts\dl_examples.py') (Join-Path $InstallRoot '.assets\examples')
Set-Location $InstallRoot
$smokeOut = Join-Path $env:TEMP 'facefusion_smoke.mp4'
if (Test-Path $smokeOut) { Remove-Item $smokeOut -Force }
python facefusion.py headless-run -s .assets\examples\source.jpg -t .assets\examples\target-240p.mp4 -o $smokeOut --processors face_swapper --execution-providers cuda --download-providers huggingface
$smokeOk = (Test-Path $smokeOut) -and ((Get-Item $smokeOut).Length -gt 100KB)
if ($smokeOk) {
    $size = [math]::Round((Get-Item $smokeOut).Length / 1KB)
    Write-Host "  [OK] 冒烟测试产出 $smokeOut（${size} KB）"
} else {
    $failures += '冒烟测试未产出视频（PITFALLS #8：exit code 不算数，以文件为准）'
}

Write-Host ''
if ($failures.Count -eq 0) {
    Write-Host '=== 验证全部通过：FaceFusion 在本机可正常进行 GPU 换脸 ===' -ForegroundColor Green
    exit 0
} else {
    Write-Host '=== 验证失败 ===' -ForegroundColor Red
    $failures | ForEach-Object { Write-Host "  - $_" }
    exit 1
}
