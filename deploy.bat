@echo off
echo InstaSmart Framework GitHub Guncelleme Araci
echo --------------------------------------------
echo.

echo 1. Git durumu kontrol ediliyor...
git status

echo.
echo 2. Degisiklikler ekleniyor...
git add .

echo.
echo 3. Commit olusturuluyor...
git commit -m "feat: Upgrade to modular framework with Plugin system and Dry-Run mode"

echo.
echo 4. GitHub'a gonderiliyor...
git push origin main

echo.
echo --------------------------------------------
echo Islem tamamlandi. Eger hata gorduyseniz lutfen kontrol edin.
echo Pencereyi kapatmak icin bir tusa basin.
pause
