"""
Простой сканер секретов и служебных путей по файлам, отслеживаемым git
(т.е. по тому, что реально может попасть в публичный репозиторий).

Использование:
    python scripts/scan_secrets.py

Возвращает код выхода 1 и печатает найденные строки, если что-то похоже на
секрет/токен/приватный ключ/локальный путь конкретного пользователя.
Не заменяет специализированные инструменты (gitleaks/truffleHog) — эвристика
на основе регулярных выражений, может давать ложные срабатывания и не ловит
всё. Проверяет только ТЕКУЩЕЕ состояние отслеживаемых файлов, не историю git.
"""
import re
import subprocess
import sys

PATTERNS = {
    "AWS Access Key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "AWS Secret-looking assignment": re.compile(r"aws_secret_access_key\s*=\s*['\"][^'\"]+['\"]", re.I),
    "GitHub token": re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
    "GitHub fine-grained PAT": re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    "Google API key": re.compile(r"AIza[0-9A-Za-z_\-]{35}"),
    "Slack token": re.compile(r"xox[baprs]-[0-9A-Za-z-]{10,}"),
    "Stripe live key": re.compile(r"(sk|pk)_live_[0-9A-Za-z]{16,}"),
    "Private key block": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "Generic secret/token/password assignment": re.compile(
        r"(?:secret|token|api[_-]?key|password|passwd)\s*[:=]\s*['\"][A-Za-z0-9+/_\-]{12,}['\"]", re.I
    ),
    "Bearer header": re.compile(r"Bearer\s+[A-Za-z0-9_\-\.]{20,}"),
    "Windows user path": re.compile(r"[A-Za-z]:\\\\?[Uu]sers\\\\?[^\\\\/\"'\s]+"),
    "Personal email (project owner)": re.compile(r"aksaclaude@gmail\.com"),
}

# Раз-источники (сырые Excel/GPKG) — по .gitignore не должны попадать в git
# вообще; если появились, это или уже отслеживались до правки .gitignore,
# или кто-то явно сделал `git add -f`. Не сканируем построчно (бинарь), просто
# сигналим о самом факте. Легитимные бинарные веб-ассеты (лого и т.п.) сюда
# не входят — их наличие в git нормально.
DISALLOWED_TRACKED_EXTENSIONS = {".gpkg", ".xlsx", ".xls"}


def tracked_files():
    out = subprocess.run(
        ["git", "-c", "core.quotepath=false", "ls-files"],
        capture_output=True, check=True,
    )
    return [l for l in out.stdout.decode("utf-8").splitlines() if l.strip()]


def main():
    findings = []
    disallowed = []
    skip_scan_exts = DISALLOWED_TRACKED_EXTENSIONS | {".png", ".ico", ".jpg", ".jpeg", ".gif", ".woff", ".woff2"}
    for path in tracked_files():
        ext = "." + path.rsplit(".", 1)[-1].lower() if "." in path else ""
        if ext in DISALLOWED_TRACKED_EXTENSIONS:
            disallowed.append(path)
            continue
        if ext in skip_scan_exts:
            continue
        try:
            with open(path, encoding="utf-8", errors="ignore") as f:
                text = f.read()
        except (IsADirectoryError, PermissionError):
            continue
        for label, pattern in PATTERNS.items():
            for m in pattern.finditer(text):
                line_no = text.count("\n", 0, m.start()) + 1
                findings.append(f"{path}:{line_no}: [{label}] {m.group(0)[:60]}")

    if disallowed:
        print("⚠️  Сырые исходники (.xlsx/.gpkg) всё ещё отслеживаются git — не должны быть в публичном репозитории:")
        for p in disallowed:
            print(f"  - {p}")
        print()

    if findings:
        print(f"НАЙДЕНО {len(findings)} потенциальных секретов/служебных путей:")
        for line in findings:
            print(f"  {line}")
        sys.exit(1)

    if disallowed:
        sys.exit(1)

    print("Секретов и служебных путей не найдено в отслеживаемых файлах.")
    sys.exit(0)


if __name__ == "__main__":
    main()
