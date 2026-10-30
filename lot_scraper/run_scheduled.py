"""Плановая выгрузка без интерфейса: все корпуса с парсером -> xlsx в out/, итог в out/last_run.txt и уведомление Windows.
    python lot_scraper/run_scheduled.py            все корпуса
    python lot_scraper/run_scheduled.py 115|02     только указанные (для проверки)
Ставится в планировщик Windows скриптом install_schedule.ps1."""
import sys, subprocess, datetime
sys.stdout.reconfigure(encoding='utf-8')
import engine


def notify(title, text):
    """Всплывающее уведомление Windows без сторонних модулей. Ошибки уведомления не должны ронять выгрузку."""
    ps = ("Add-Type -AssemblyName System.Windows.Forms; $n = New-Object System.Windows.Forms.NotifyIcon; "
          "$n.Icon = [System.Drawing.SystemIcons]::Information; $n.Visible = $true; "
          f"$n.ShowBalloonTip(10000, '{title}', '{text}', 'Info'); Start-Sleep -Seconds 11; $n.Dispose()")
    try:
        subprocess.Popen(['powershell', '-NoProfile', '-WindowStyle', 'Hidden', '-Command', ps])
    except OSError:
        pass


def main():
    keys = sys.argv[1:]
    chosen = engine.T if not keys else [t for t in engine.T if engine.key_of(t['project_id'], t['sub_id']) in keys]
    if not chosen:
        sys.exit('Нет парсеров для указанных корпусов')
    res = engine.run_targets(chosen)
    raw, table, st = engine.export(res, '' if not keys else '_выборка')
    sm = engine.summary(res)
    pr = st.get('prev_run')
    lines = [f'Выгрузка {datetime.datetime.now():%d.%m.%Y %H:%M}',
             f'Корпусов {sm["buildings"]}: успешно {sm["ok"]}, ошибка {sm["errors"]}, устаревшие данные {sm["stale"]}. Лотов {sm["lots"]}.',
             f'Без цены {sm["no_price"]}, без площади {sm["no_area"]}.']
    if pr:
        lines.append(f'С прошлой выгрузки ({pr["date"]}): новых {pr["новый"]}, цена изменилась {pr["цена изменилась"]}, ушло {pr["ушёл из продажи"]}.')
    lines.append(f'Файл: {engine.OUT / table}')
    for r in res:
        if r.error or r.stale or r.notes:
            lines.append(f'  {r.t["project"]} / {r.t["corpus"]}: ' + (r.error or '; '.join(r.notes))[:200])
    text = '\n'.join(lines)
    (engine.OUT / 'last_run.txt').write_text(text, encoding='utf-8')
    print(text)
    short = f'{sm["lots"]} лотов, ошибок {sm["errors"]}' + (f', новых {pr["новый"]}, цен {pr["цена изменилась"]}' if pr else '')
    notify('Выгрузка лотов готова', short)


if __name__ == '__main__':
    main()
