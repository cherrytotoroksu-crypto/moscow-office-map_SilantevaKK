"""
Собирает публичный артефакт сайта в _site/ — то, что нужно карте для работы
по прямой ссылке без авторизации, плюс (по прямой просьбе пользователя,
2026-07-30) classifier.html и все QA/аудит .md и .json файлы — их снова
можно открыть по ссылке. НЕ копирует: SECURITY_AUDIT.md (сам документ
перечисляет непочиненные риски — публиковать такой список не стоит),
scripts/, tests/, сырые .xlsx/.gpkg, .bat, .claude/, .github/.

Используется workflow'ом .github/workflows/deploy.yml вместо публикации
всего репозитория (path: '.'). Можно запускать и локально для проверки
перед пушем:

    python scripts/build_public_site.py

Тогда _site/ можно поднять локально (например `python -m http.server`
из _site/) и убедиться, что карта и classifier.html работают.
"""
import json
import os
import re
import shutil

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(REPO_ROOT, "_site")

# Поля building_dates.json, которые реально использует карта.
# "source"/"last_checked" — внутренние QA-заметки, в паблик не идут
# (это про одно поле одного файла данных, отдельно от вопроса про
# classifier.html/QA-документы ниже — пользователь про это не просил).
BUILDING_DATES_PUBLIC_FIELDS = {
    "construction_start_q", "start_q", "commission_q", "stage", "stage_as_of",
}

# Регексы имён файлов в data/, которые нужны карте (см. index.html: QUARTERS,
# LAYER_CFG, fetchJSON('data/building_dates.json'), <img src="data/nf_group_logo.png">)
# плюс data/all_projects_layer.json — читает codifier.html (см. ниже).
DATA_ALLOW_PATTERNS = [
    re.compile(r"^buildings_\d{6}\.json$"),
    re.compile(r"^lots_\d{6}\.json$"),
    re.compile(r"^rent_lots_\d{6}\.json$"),
    re.compile(r"^coworking_\d{6}\.json$"),
    re.compile(r"^.+\.geojson$"),
    re.compile(r"^nf_group_logo\.png$"),
    re.compile(r"^all_projects_layer\.json$"),
]

# Корневые файлы, которые тоже публикуются по прямой просьбе пользователя
# (classifier.html + все QA/аудит .md и .json). SECURITY_AUDIT.md намеренно
# не в списке — см. docstring выше. codifier.html добавлен 2026-07-31 (по
# просьбе пользователя — таблицы должны открываться по прямой ссылке, не
# только локально) — не содержит внутренних QA-заметок, безопасно публиковать
# как есть, без строк/трансформаций (в отличие от building_dates.json ниже).
ROOT_ALLOW_PATTERNS = [
    re.compile(r"^classifier\.html$"),
    re.compile(r"^codifier\.html$"),
    re.compile(r"^.+\.md$"),
    re.compile(r"^qa_.+\.json$"),
    re.compile(r"^classifier_audit_baseline.*\.json$"),
]
ROOT_DENY_NAMES = {"SECURITY_AUDIT.md"}


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
    # classifier.html теперь тоже публикуется (см. ROOT_ALLOW_PATTERNS), поэтому
    # ссылка на него в index.html больше не вырезается — иначе получилось бы,
    # что страница доступна по прямому URL, но кнопки на неё нигде нет.
    shutil.copy2(os.path.join(REPO_ROOT, "index.html"), os.path.join(OUT_DIR, "index.html"))


def build_root_files():
    copied = []
    for name in sorted(os.listdir(REPO_ROOT)):
        full = os.path.join(REPO_ROOT, name)
        if not os.path.isfile(full) or name in ROOT_DENY_NAMES:
            continue
        if any(p.match(name) for p in ROOT_ALLOW_PATTERNS):
            shutil.copy2(full, os.path.join(OUT_DIR, name))
            copied.append(name)
    print(f"  корень: скопировано {len(copied)} файлов (classifier.html + QA .md/.json): {', '.join(copied)}")


def build_data_dir():
    src_data = os.path.join(REPO_ROOT, "data")
    out_data = os.path.join(OUT_DIR, "data")
    os.makedirs(out_data, exist_ok=True)
    copied = 0
    for name in sorted(os.listdir(src_data)):
        if name == "all_projects_layer.json":
            continue  # копируется отдельно, с фильтром по public_visibility — см. ниже
        if any(p.match(name) for p in DATA_ALLOW_PATTERNS):
            shutil.copy2(os.path.join(src_data, name), os.path.join(out_data, name))
            copied += 1
    print(f"  data/: скопировано {copied} файлов (geojson + квартальные json + логотип)")

    # all_projects_layer.json — только public_visibility='public'. Сейчас (2026-07-31)
    # все 277 записей публичные, но фильтр защищает на будущее: если реестр
    # пополнится внешними/неподтверждёнными Remain-кандидатами с
    # public_visibility='internal_only', они не должны утечь в сыром JSON,
    # даже если UI codifier.html их не показывает.
    src_registry = os.path.join(src_data, "all_projects_layer.json")
    if os.path.exists(src_registry):
        with open(src_registry, encoding="utf-8") as f:
            records = json.load(f)
        public_records = [r for r in records if r.get("public_visibility") == "public"]
        with open(os.path.join(out_data, "all_projects_layer.json"), "w", encoding="utf-8") as f:
            json.dump(public_records, f, ensure_ascii=False)
        hidden = len(records) - len(public_records)
        print(f"  data/all_projects_layer.json: {len(public_records)} публичных записей"
              + (f" ({hidden} internal_only скрыто)" if hidden else ""))

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
    # По просьбе пользователя (2026-07-30): сайт должен быть сложно найти без
    # точной ссылки — поисковики не должны его индексировать вообще.
    # Основная защита — <meta name="robots" content="noindex, nofollow">
    # в index.html (работает даже если краулер проигнорирует robots.txt);
    # это — вторая линия, явный запрет на обход.
    with open(os.path.join(OUT_DIR, "robots.txt"), "w", encoding="utf-8") as f:
        f.write("User-agent: *\nDisallow: /\n")


def main():
    clean_dir(OUT_DIR)
    build_index_html()
    build_data_dir()
    build_root_files()
    build_robots_txt()

    # Явный список того, что НЕ попало в сборку, для наглядности при проверке.
    excluded = [
        "SECURITY_AUDIT.md (сам документ описывает непочиненные риски)",
        "scripts/ (кроме этого сборочного скрипта, он не копируется тоже)",
        "tests/", "*.xlsx", "*.gpkg", "*.bat", ".claude/", ".github/",
    ]
    print("\nНЕ включено в _site/ (осталось только в репозитории):")
    for e in excluded:
        print(f"  - {e}")
    print(f"\nГотово: {OUT_DIR}")


if __name__ == "__main__":
    main()
