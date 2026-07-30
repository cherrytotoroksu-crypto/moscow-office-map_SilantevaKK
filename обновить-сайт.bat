@echo off
cd /d "%~dp0"
echo === Publishing changes to the site ===
echo.
echo ВНИМАНИЕ: этот скрипт добавляет только известные безопасные пути
echo (data/*.json, data/*.geojson, index.html, classifier.html и .md-файлы
echo репозитория), а не "git add -A" — чтобы случайный файл (Excel, экспорт
echo GPKG, скриншот и т.п.), оказавшийся в этой папке, не улетел в публичный
echo репозиторий по ошибке. Если нужно добавить что-то ещё — сделай это
echo вручную через git add и проверь git status перед коммитом.
echo.
git add data/*.json data/*.geojson index.html classifier.html *.md
echo.
echo === Что будет закоммичено: ===
git status --short
echo.
set /p CONFIRM="Всё верно? Коммитить и пушить? (y/n): "
if /i not "%CONFIRM%"=="y" (
  echo Отменено.
  pause
  exit /b
)
git commit -m "Update site %date% %time%"
git push
echo.
echo Done. The site will update in about 1 minute.
pause
