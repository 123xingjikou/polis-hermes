$ErrorActionPreference = "Stop"

Write-Host "========================================"
Write-Host "    配置美团龙猫为默认模型"
Write-Host "========================================"
Write-Host ""

$configPath = "$env:USERPROFILE\.qclaw\openclaw.json"

if (-not (Test-Path $configPath)) {
    Write-Host "❌ 配置文件不存在: $configPath"
    pause
    exit 1
}

Write-Host "🔍 读取配置文件..."
$config = Get-Content $configPath -Raw -Encoding UTF8
$json = $config | ConvertFrom-Json

Write-Host "✅ 正在配置 LongCat-2.0 为默认模型..."

$longcatProvider = @{
    baseUrl = "https://api.longcat.chat/openai"
    apiKey = "ak_2jE4hw6aX3S54Yu0QR2j926U94R1X"
    api = "openai-chat-completions"
    models = @(
        @{
            id = "LongCat-2.0"
            name = "美团龙猫 2.0"
            reasoning = $true
            input = @("text", "image")
            contextWindow = 1000000
            maxTokens = 384000
        }
    )
}

if ($json.models.providers.PSObject.Properties.Name -notcontains "longcat") {
    $json.models.providers | Add-Member -MemberType NoteProperty -Name "longcat" -Value $longcatProvider
} else {
    $json.models.providers.longcat = $longcatProvider
}

$json.agents.defaults.model.primary = "longcat/LongCat-2.0"
$json.agents.defaults.model.fallbacks = @("qclaw/modelroute")

foreach ($agent in $json.agents.list) {
    if ($agent.model) {
        $agent.model.primary = "longcat/LongCat-2.0"
        $agent.model.fallbacks = @("qclaw/modelroute")
    }
    if ($agent.heartbeat -and $agent.heartbeat.model) {
        $agent.heartbeat.model = "longcat/LongCat-2.0"
    }
}

$newConfig = $json | ConvertTo-Json -Depth 100
[System.IO.File]::WriteAllText($configPath, $newConfig, [System.Text.UTF8Encoding]::new($false))

Write-Host ""
Write-Host "✅ 配置完成！"
Write-Host ""
Write-Host "📋 当前配置："
Write-Host "   - 主模型: longcat/LongCat-2.0"
Write-Host "   - 备用模型: qclaw/modelroute"
Write-Host "   - Base URL: https://api.longcat.chat/openai"
Write-Host "   - API: openai-chat-completions"
Write-Host ""
Write-Host "💡 请重启 QClaw 使配置生效"
Write-Host ""

pause
