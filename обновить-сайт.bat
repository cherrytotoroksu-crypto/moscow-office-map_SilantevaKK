@echo off
cd /d "%~dp0"
echo === Publishing changes to the site ===
git add -A
git commit -m "Update site %date% %time%"
git push
echo.
echo Done. The site will update in about 1 minute.
pause
