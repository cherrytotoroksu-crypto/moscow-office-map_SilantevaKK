# Ставит еженедельную выгрузку лотов в планировщик Windows (понедельник 09:00, текущий пользователь, без прав администратора).
# Запуск: powershell -ExecutionPolicy Bypass -File lot_scraper\install_schedule.ps1
# Убрать:  schtasks /Delete /TN "Выгрузка лотов офисов" /F
param([string]$Day = 'MON', [string]$Time = '09:00')
$py = (Get-Command python).Source
$script = Join-Path $PSScriptRoot 'run_scheduled.py'
$name = 'Выгрузка лотов офисов'
$cmd = "`"$py`" `"$script`""
schtasks /Create /TN $name /TR $cmd /SC WEEKLY /D $Day /ST $Time /F
Write-Host "Готово: $name, каждый $Day в $Time. Результат: lot_scraper\out\last_run.txt"
