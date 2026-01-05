@echo off
echo ===================================================
echo Instagram Bot Baslatiliyor...
echo ===================================================
echo.

echo 1. Gerekli kutuphaneler kontrol ediliyor...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo HATA: Kutuphaneler yuklenirken bir sorun olustu.
    echo Lutfen Python'un yuklu oldugundan ve PATH'e eklendiginden emin olun.
    pause
    exit /b
)

echo.
echo 2. Bot calistiriliyor...
echo.
python main.py

echo.
echo ===================================================
echo Islem tamamlandi veya bot kapandi.
echo ===================================================
pause
