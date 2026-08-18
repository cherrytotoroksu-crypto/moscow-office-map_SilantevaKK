# QA-backlog: offer_status / geometry_quality / source / confidence, 11 записей classifier.html

Отдельный backlog общей карты — **не Remain-интеграция**. Не смешивать с
`outputs/remain_integration_audit_2026-08-18.md`. Источник списка:
проверка «все объекты подтверждены?» 2026-08-19 — эти 11 записей
`verification_status=under_review`, `confidence=low`, `qa_status=ok`,
все несут одну и ту же типовую заметку сборщика («offer_status и
geometry_quality — эвристика конвертации, не подтверждены отдельно»,
`scripts/build_all_projects_layer.py`), то есть НИ ОДНА не проверена
вручную по существу — только механически сконвертирована.

**Правила по этому backlog:**
- НЕ менять PRJ-архитектуру / `canonical_project_id` / `canonical_building_id`.
- НЕ объединять проекты автоматически (никаких новых `duplicate_of`/merge без
  отдельного подтверждения, как это было сделано для 14 технических дублей
  в `outputs/unified_codifier_review_decisions_2026-08-18.md`).
- `data/building_dates.json` не менять.
- Каждая строка закрывается только когда все 4 колонки (offer_status /
  geometry_quality / источник / confidence) отдельно проверены и
  `qa_notes` содержит конкретное обоснование, а не общую эвристическую фразу.

## Текущее состояние (снимок 2026-08-19)

| ID | Название | Девелопер | offer_status | geometry_quality | GBA/GLA | confidence |
|---|---|---|---|---|---|---|
| proj-1 | STONE Пресня | Stonehedge | Ещё не вышел в продажу | geocoded_approx | 15000 / 15000 | low |
| proj-13 | Fly Tower | KR Properties | Ещё не вышел в продажу | geocoded_approx | 30000 / — | low |
| proj-72 | Бизнес-центр SEZAR | Sezar Group | Ещё не вышел в продажу | geocoded_approx | 15862 / 11246 | low |
| proj-168 | Orbital-2 | Ultima Development | В продаже | geocoded_approx | 57967 / 39667 | low |
| proj-200 | STONE Ходынка III | STONE | В продаже | geocoded_approx | 70500 / 50100 | low |
| proj-227 | БЦ Сколковский | **«Пожарная охрана»** ⚠️ | В продаже | geocoded_approx | 8500 / — | low |
| proj-240 | Ольховая SKY | ГК Гранель | В продаже | geocoded_approx | 22750 / 18113 | low |
| proj-251 | KORP. Молодежная | Группа Аквилон | В продаже | geocoded_approx | 15541 / **0** ⚠️ | low |
| proj-258 | STONE Ходынка IV | STONE | В продаже | geocoded_approx | 160000 / 129536 | low |
| proj-264 | Энтузиаст | Объект Гарант | В продаже | geocoded_approx | 37300 / 30198 | low |
| proj-269 | DIUS | СтройМир | В продаже | geocoded_approx | 19025 / 12500 | low |

⚠️ Замечено при снятии снимка (не проверено дальше, только зафиксировано):
- **proj-227**: `developer="Пожарная охрана"` — похоже на артефакт парсинга
  classifier.html, а не реальное имя девелопера. Приоритет на проверку источника.
- **proj-251**: `gla=0`, при этом `offer_status="В продаже"` — по общему
  инварианту слоя (`tests/test_online_tables_invariants.py`, "empty values
  are not silently turned into 0") площадь должна быть `null`, если
  неизвестна, а не `0`. Похоже на ту же категорию бага, отдельно от GBA/GLA
  общего инварианта (тот инвариант проверяет только записи с
  `project_status="Не установлен"`, этот случай не покрыт).

## Чеклист на каждую из 11 записей

Для каждого `canonical_project_id` закрыть все 4 пункта:

1. **offer_status** — сверить с живым источником (сайт девелопера / ЦИАН /
   агрегатор), подтвердить «В продаже» / «Ещё не вышел в продажу» реальным
   наличием лотов, а не эвристикой из `derive_offer_status()`.
2. **geometry_quality** — все 11 сейчас `geocoded_approx`; проверить
   координаты по адресу (2GIS/Яндекс.Карты), поднять до `house_exact`, если
   подтверждено, либо оставить `geocoded_approx`/`unverified` с обоснованием.
3. **источник** — подтвердить `classifier.html` как источник или заменить/
   дополнить на более авторитетный (офиц. сайт девелопера, дата снятия) —
   записать в `qa_notes` с датой и ссылкой, как это сделано для Botanica
   Plaza / Rail.A в Remain-конфликтах.
4. **confidence** — поднять с `low` только после того, как 1–3 пройдены;
   не поднимать по одному признаку.

## Статус

Ничего не проверено. Ни один пункт не закрыт, никаких изменений в
`data/all_projects_layer.json` в рамках этого backlog ещё не вносилось —
только зафиксирован список задач.
