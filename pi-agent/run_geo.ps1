# GEO Pi agent 运行器
# 用法:
#   .\run_geo.ps1                                  # 交互模式
#   .\run_geo.ps1 -Task "诊断 https://www.mzyai.com 并给出 SHEEP 评分"   # print 一次性任务
#   .\run_geo.ps1 -Model mzyai/glm-5.2 -Task "..."
param(
	[string]$Task = "",
	[string]$Model = "mzyai/deepseek-v4-pro",
	[int]$Port = 8060
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot          # geo-platform 目录
$ext = Join-Path $PSScriptRoot "geo-extension.ts"
$base = "http://localhost:$Port"

function Test-GeoHealth {
	try {
		$r = Invoke-WebRequest -Uri "$base/health" -UseBasicParsing -TimeoutSec 5
		return ($r.StatusCode -eq 200)
	} catch { return $false }
}

# 1. 确保 GEO 服务在线，未在线则后台拉起 app.py
if (-not (Test-GeoHealth)) {
	Write-Host "[run_geo] GEO 服务未在线，正在启动 app.py ..." -ForegroundColor Yellow
	$py = Join-Path $root ".venv\Scripts\python.exe"
	if (-not (Test-Path $py)) { $py = "python" }
	$logDir = Join-Path $root "logs"
	New-Item -ItemType Directory -Force -Path $logDir | Out-Null
	Start-Process -FilePath $py -ArgumentList "app.py" -WorkingDirectory $root -WindowStyle Hidden `
		-RedirectStandardOutput (Join-Path $logDir "pi_geo_server.log") `
		-RedirectStandardError (Join-Path $logDir "pi_geo_server.err.log")
	$ok = $false
	for ($i = 0; $i -lt 30; $i++) {
		Start-Sleep -Seconds 1
		if (Test-GeoHealth) { $ok = $true; break }
	}
	if (-not $ok) {
		Write-Host "[run_geo] GEO 服务启动失败，请查看 logs\pi_geo_server.err.log" -ForegroundColor Red
		exit 1
	}
	Write-Host "[run_geo] GEO 服务已上线 ($base)" -ForegroundColor Green
} else {
	Write-Host "[run_geo] GEO 服务已在线 ($base)" -ForegroundColor Green
}

# 2. 启动 Pi
$env:GEO_PLATFORM_URL = $base
if ($Task) {
	Write-Host "[run_geo] print 模式 | model=$Model" -ForegroundColor Cyan
	Write-Host "[run_geo] 任务: $Task" -ForegroundColor Cyan
	& pi -e $ext --model $Model -p $Task
} else {
	Write-Host "[run_geo] 交互模式 | model=$Model" -ForegroundColor Cyan
	& pi -e $ext --model $Model
}
