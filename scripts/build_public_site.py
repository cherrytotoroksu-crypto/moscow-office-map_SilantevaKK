"""
Собирает публичный артефакт сайта в _site/ — только то, что нужно карте
для работы по прямой ссылке без авторизации. Не копирует: classifier.html,
любые QA/аудит .md и .json файлы, scripts/, tests/, сырые .xlsx/.gpkg,
.bat, CLAUDE.md, README.md.

Используется workflow'ом .github/workflows/deploy.yml вместо публикации
всего репозитория (path: '.'). Можно запускать и локально для проверки
перед пушем:

    python scripts/build_public_site.py

Тогда _site/ можно поднять локально (например `python -m http.server`
из _site/) и убедиться, что карта работает и внутренних файлов там нет.
"""
import json
import os
import re
import shutil

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(REPO_ROOT, "_site")

# Поля building_dates.json, которые реально использует карта.
# "source"/"last_checked" — внутренние QA-заметки, в паблик не идут.
BUILDING_DATES_PUBLIC_FIELDS = {
    "construction_start_q", "start_q", "commission_q", "stage", "stage_as_of",
}

# Регексы имён файлов в data/, которые нужны карте (см. index.html: QUARTERS,
# LAYER_CFG, fetchJSON('data/building_dates.json'), <img src="data/nf_group_logo.png">).
DATA_ALLOW_PATTERNS = [
    re.compile(r"^buildings_\d{6}\.json$"),
    re.compile(r"^lots_\d{6}\.json$"),
    re.compile(r"^rent_lots_\d{6}\.json$"),
    re.compile(r"^coworking_\d{6}\.json$"),
    re.compile(r"^.+\.geojson$"),
    re.compile(r"^nf_group_logo\.png$"),
]

# Строка в index.html, ведущая на внутренний QA-инструмент — вырезается
# только из публичной копии (в рабочем index.html для локальной разработки
# кнопка остаётся).
CLASSIFIER_LINK_RE = re.compile(
    r'<a class="upload-btn" href="classifier\.html"[\s\S]*?</a>\n?'
)


def clean_dir(path):
    # На Windows/OneDrive удаление сразу после предыдущего запуска иногда
    # падает с PermissionError из-за файлового индексатора/синхронизации —
    # не проблема самого скрипта (в CI на ubuntu-latest такого нет), просто
    # даём пару попыток с паузой для локальной разработки.
    import time
    if os.path.exists(path):
        for attempt in range(5):
            try:
                shutil.rmtree(path)
                break
            except PermissionError:
                if attempt == 4:
                    raise
                time.sleep(0.5)
    os.makedirs(path, exist_ok=True)


def build_index_html():
    with open(os.path.join(REPO_ROOT, "index.html"), encoding="utf-8") as f:
        html = f.read()
    new_html, n = CLASSIFIER_LINK_RE.subn("", html)
    if n != 1:
        raise SystemExit(
            f"ОШИБКА: ожидалась ровно 1 ссылка на classifier.html в index.html, найдено {n}. "
            "Проверь CLASSIFIER_LINK_RE — публичная сборка не должна ссылаться на внутренний инструмент."
        )
    with open(os.path.join(OUT_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(new_html)


def build_data_dir():
    src_data = os.path.join(REPO_ROOT, "data")
    out_data = os.path.join(OUT_DIR, "data")
    os.makedirs(out_data, exist_ok=True)
    copied = 0
    for name in sorted(os.listdir(src_data)):
        if any(p.match(name) for p in DATA_ALLOW_PATTERNS):
            shutil.copy2(os.path.join(src_data, name), os.path.join(out_data, name))
            copied += 1
    print(f"  data/: скопировано {copied} файлов (geojson + квартальные json + логотип)")

    # building_dates.json — с транформацией, без source/last_checked
    src_bd = os.path.join(src_data, "building_dates.json")
    if os.path.exists(src_bd):
        with open(src_bd, encoding="utf-8") as f:
            raw = json.load(f)
        cleaned = {
            k: {fk: fv for fk, fv in v.items() if fk in BUILDING_DATES_PUBLIC_FIELDS}
            for k, v in raw.items()
        }
        with open(os.path.join(out_data, "building_dates.json"), "w", encoding="utf-8") as f:
            json.dump(cleaned, f, ensure_ascii=False)
        print(f"  data/building_dates.json: {len(cleaned)} записей, поля source/last_checked удалены")


def build_robots_txt():
    with open(os.path.join(OUT_DIR, "robots.txt"), "w", encoding="utf-8") as f:
        f.write("User-agent: *\nAllow: /\n")


def main():
    clean_dir(OUT_DIR)
    build_index_html()
    build_data_dir()
    build_robots_txt()

    # Явный список того, что НЕ попало в сборку, для наглядности при проверке.
    excluded = [
        "classifier.html", "README.md", "CLAUDE.md",
        "*.md (QA/аудит)", "*.json (qa_*, classifier_audit_baseline_*)",
        "scripts/ (кроме этого сборочного скрипта, он не копируется тоже)",
        "tests/", "*.xlsx", "*.gpkg", "*.bat", ".claude/", ".github/",
    ]
    print("\nНЕ включено в _site/ (осталось только в репозитории):")
    for e in excluded:
        print(f"  - {e}")
    print(f"\nГотово: {OUT_DIR}")


if __name__ == "__main__":
    main()
