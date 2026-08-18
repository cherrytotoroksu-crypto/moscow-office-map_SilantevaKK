# Аудит интеграции Remain/Remapp, 2026-08-18

## Ограничение источника

Полного дампа Remain DataLens (336 объектов) в репозитории нет. Решение
пользователя (2026-08-18): работать по уже собранному
`REMAIN_GAP_ANALYSIS_2026-07-29.md` (153 продажных объекта, частичный охват —
не эквивалент полного сопоставления). `only_local` не оценён — требует
полного дампа Remain, иначе счётчик будет ложно занижен.

## Счётчики

| Категория | Кол-во |
|---|---|
| exact_match | 7 |
| probable_match | 6 |
| only_remain (добавлены) | 4 |
| only_local | n/a — недоступно без полного дампа Remain |
| conflict | 3 |

## Конфликты (требуют разбора вручную)

| Remain | Наш объект | Проблема |
|---|---|---|
| Botanica Plaza | Plaza Botanica | координаты расходятся на 0.65 км |
| Rail.A | Rail.A | координаты расходятся на 0.34 км |
| Бизнес-квартал Прокшино Башни 1/2/3 | А101 Прокшино | наши GBA 42000 vs сумма Remain 113029 — вероятно, у нас учтена только одна башня |

## Добавленные only_remain записи (external_only=true)

`remain-only-0001..0004`: МФК Центральный Телеграф, ЗИЛАРТ GRAND (Дом 18),
Sydney City, Moscow Towers. Все — `public_visibility=internal_only`,
`qa_status=quarantine`, `verification_status=under_review`,
`quarter_offer_exists=false`, `quarter_offer_refs=[]`, `market_channel=[]`.
Лоты на продажу/аренду не подтверждены вживую — решение пользователя: не
выводить публично и не включать в квартальные объёмы до проверки.

## PRJ-* реестр

Требование 3 (единый реестр с PRJ-*) не выполнено. Реального PRJ-* в коде
нет — только `outputs/unified_codifier_blueprint_2026-08-18.md` (draft,
миграция не выполнена). `canonical_project_id` для новых записей —
`remain-only-000N` в текущей схеме `proj-N`, чтобы не создавать
самопровозглашённые PRJ-ID и не нарушать запрет blueprint'а на ручную
перенумерацию до QA. Решение пользователя: не создавать PRJ-* сейчас.

## Классификатор / карточки (требования 1, 4, 5)

- Записи попали в общий слой (`data/all_projects_layer.json`) — требование 1 выполнено.
- Классификатор (`classifier.html`) не тронут — записи `internal_only`, отдельного UI-шага для показа source="Remain/Remapp" в карточке не добавлено (нет действующей PRJ-логики карточек под external-only записи; для public-показа нужно сначала подтвердить лоты).
- Фильтр по статусу/предложению: поле `offer_status="Ещё не вышел в продажу"` уже входит в существующий enum `OFFER_STATUSES`, значит существующий фильтр подхватит эти записи без правок кода.

## Тесты

`tests/test_audit_remain_integration.py` — классификация, флаги
external_only/quarter_offer_exists=false, regression на потерю Remain-записей
при пересборке слоя. `python -m unittest tests.test_audit_remain_integration
tests.test_validate_remain_layer` — 10/10 OK.

`python scripts/validate_all_projects_layer.py data/all_projects_layer.json` — PASS: 281 record(s).

## Не тронуто (по требованиям 1, 8, 10)

- PRJ-логика / архитектура — не менялась.
- `data/building_dates.json` — не менялся.
- Квартальные объёмы продаж/аренды/коворкингов — новые записи имеют
  `quarter_offer_refs=[]`, в квартальные агрегаты не попадают.

## Следующий шаг перед публичным показом

Подтвердить наличие реальных лотов по 4 only_remain объектам (см.
`qa_notes` каждой записи), затем вручную сменить
`public_visibility` → `public` и `verification_status` → `accepted`.
