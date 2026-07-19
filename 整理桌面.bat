@echo off
chcp 65001 >nul
echo ========================================
echo    桌面整理工具
echo ========================================
echo.

set "DESKTOP=%USERPROFILE%\Desktop"
set "TEMP_DIR=%DESKTOP%\临时脚本"

if not exist "%TEMP_DIR%" mkdir "%TEMP_DIR%"

echo 正在整理以下类型的文件：
echo   - Python 脚本 (*.py)
echo   - 批处理脚本 (*.bat, *.cmd)
echo   - PowerShell 脚本 (*.ps1)
echo   - Markdown 文档 (*.md)
echo   - 文本文件 (*.txt)
echo   - CSV 文件 (*.csv)
echo.

set count=0

for %%f in ("%DESKTOP%\*.py" "%DESKTOP%\*.bat" "%DESKTOP%\*.cmd" "%DESKTOP%\*.ps1" "%DESKTOP%\*.md" "%DESKTOP%\*.txt" "%DESKTOP%\*.csv") do (
    if /i not "%%~nxf"=="desktop.ini" (
        move "%%f" "%TEMP_DIR%\" >nul 2>&1
        if exist "%TEMP_DIR%\%%~nxf" (
            echo   移动: %%~nxf
            set /a count+=1
        )
    )
)

echo.
echo ========================================
echo  完成！共移动了 %count% 个文件到 "临时脚本" 文件夹
echo ========================================
echo.
pause
