# QClaw 进程优化部署脚本
# 请在外部 PowerShell 中执行此脚本

Write-Host "=== QClaw 进程优化部署 ===" -ForegroundColor Cyan

# 1. 复制 agent_supervisor.py
Write-Host "`n[1] 复制 agent_supervisor.py..."
$src = "C:\Users\dfhai\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a45044b9f3d6718577ed1f8\agent_supervisor.py"
$dst = "C:\Users\dfhai\.qclaw\workspace-hermes\agents\agent_supervisor.py"
Copy-Item $src $dst -Force
Write-Host "    已复制到: $dst" -ForegroundColor Green

# 2. 启动 agent_supervisor
Write-Host "`n[2] 启动 agent_supervisor..."
$pyw = "C:\Users\dfhai\AppData\Local\Programs\Python\Python313\pythonw.exe"
$script = "C:\Users\dfhai\.qclaw\workspace-hermes\agents\agent_supervisor.py"
Start-Process $pyw -ArgumentList "`"$script`"" -WindowStyle Hidden
Start-Sleep -Seconds 3
Write-Host "    已启动" -ForegroundColor Green

# 3. 检查进程
Write-Host "`n[3] 检查进程..."
$procs = Get-Process pythonw -ErrorAction SilentlyContinue | Where-Object { 
    (Get-CimInstance Win32_Process -Filter "ProcessId=$($_.Id)").CommandLine -like "*agent_supervisor*" 
}
if ($procs) {
    Write-Host "    agent_supervisor 正在运行 (PID: $($procs.Id))" -ForegroundColor Green
} else {
    Write-Host "    agent_supervisor 未启动，请检查日志" -ForegroundColor Yellow
}

Write-Host "`n=== 完成 ===" -ForegroundColor Cyan
Write-Host "如需禁用系统服务，请以管理员身份运行 PowerShell 并执行:"
Write-Host "  $services = @('WSearch', 'DiagTrack', 'SysMain', 'lfsvc', 'PcaSvc', 'CDPSvc', 'NcbService')"
Write-Host "  foreach ($svc in $services) { Stop-Service $svc -Force; Set-Service $svc -StartupType Disabled }"