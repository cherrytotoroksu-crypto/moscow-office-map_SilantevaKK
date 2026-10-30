@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Запуск выгрузки лотов. Окно не закрывай, пока идёт работа.
python lot_scraper\server.py 3457
pause
