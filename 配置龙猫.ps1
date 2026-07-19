$ErrorActionPreference = "Stop"

Write-Host "========================================"
Write-Host "    配置美团龙猫 LongCat-2.0"
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

Write-Host "✅ 正在配置 LongCat-2.0..."

$longcatProvider = @'
      "longcat": {
        "baseUrl": "https://api.longcat.chat/openai",
        "apiKey": "ak_2jE4hw6aX3S54Yu0QR2j926U94R1X",
        "api": "openai-chat-completions",
        "models": [
          {
            "id": "LongCat-2.0",
            "name": "美团龙猫 2.0",
            "reasoning": true,
            "input": [
              "text",
              "image"
            ],
            "contextWindow": 1000000,
            "maxTokens": 384000
          }
        ]
      },
'@

$config = $config -replace '(\"providers\": \{)', "`$1`n$longcatProvider"

$config = $config -replace '"api": "openai-completions",', '"api": "openai-chat-completions",'

$config = $config -replace '"deepseek-v4-flash"', '"deepseek-v4-flash", "longcat/LongCat-2.0"'

[System.IO.File]::WriteAllText($configPath, $config, [System.Text.UTF8Encoding]::new($false))

Write-Host ""
Write-Host "✅ 配置完成！美团龙猫 LongCat-2.0 已添加到 QClaw"
Write-Host ""
Write-Host "📋 配置信息："
Write-Host "   - Base URL: https://api.longcat.chat/openai"
Write-Host "   - 模型名称: LongCat-2.0"
Write-Host "   - API: openai-chat-completions"
Write-Host ""
Write-Host "💡 使用方式：重启 QClaw 后，在模型选择中可以选择 'longcat/LongCat-2.0'"
Write-Host ""

pause
