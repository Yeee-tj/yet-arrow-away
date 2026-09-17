@echo off
chcp 65001 >nul
echo ============================================
echo   一箭又一箭 —— 打包成免安装 exe
echo ============================================
echo.

cd /d "%~dp0"

set PY=D:\Users\14566\anaconda3\envs\Yet_myenv\python.exe

if not exist "%PY%" (
    echo [错误] 找不到 Python 环境：%PY%
    echo 请确认 Anaconda 的 Yet_myenv 环境还在。
    pause
    exit /b 1
)

echo [1/4] 生成 exe 图标 ...
"%PY%" make_icon.py
if errorlevel 1 goto failed

echo.
echo [2/4] 打包中（第一次会比较慢，请耐心等待）...
"%PY%" -m PyInstaller ^
    --onefile ^
    --windowed ^
    --name yet-arrow-away ^
    --icon game_icon.ico ^
    --add-data "resources;resources" ^
    --clean ^
    --noconfirm ^
    --exclude-module numpy ^
    --exclude-module mkl ^
    --exclude-module mkl_fft ^
    --exclude-module mkl_random ^
    --exclude-module psutil ^
    --exclude-module setuptools ^
    --exclude-module pkg_resources ^
    --exclude-module unittest ^
    --exclude-module pdb ^
    --exclude-module doctest ^
    --exclude-module asyncio ^
    --exclude-module curses ^
    --exclude-module yaml ^
    --exclude-module wheel ^
    --exclude-module tomli ^
    --exclude-module threadpoolctl ^
    --exclude-module test ^
    --exclude-module lib2to3 ^
    --exclude-module distutils ^
    game.py
if errorlevel 1 goto failed

echo.
echo [3/4] 用打好的 exe 跑一次自检（验证资源和字体都在）...
if exist "dist_smoke" rd /s /q "dist_smoke"
"dist\yet-arrow-away.exe" --smoke "dist_smoke"
if not exist "dist_smoke\自检结果.txt" (
    echo [警告] 自检没有生成结果，请手动双击 dist\yet-arrow-away.exe 试试。
) else (
    echo       自检通过，截图在 dist_smoke\
)

echo.
echo [4/4] 打成一个压缩包，方便直接发给别人 ...
copy /y "怎么玩.txt" "dist\怎么玩.txt" >nul
if exist "yet-arrow-away_免安装版.zip" del /q "yet-arrow-away_免安装版.zip"
powershell -NoProfile -Command "Compress-Archive -Path 'dist\yet-arrow-away.exe','dist\怎么玩.txt' -DestinationPath 'yet-arrow-away_免安装版.zip' -Force"

echo.
echo ============================================
echo   完成！
echo.
echo   单个 exe ：dist\yet-arrow-away.exe
echo   分享压缩包：yet-arrow-away_免安装版.zip
echo ============================================
echo.
pause
exit /b 0

:failed
echo.
echo [失败] 打包过程出错，请把上面的信息发我看一下。
pause
exit /b 1
