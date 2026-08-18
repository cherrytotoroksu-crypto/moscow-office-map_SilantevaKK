# Аудит интеграции Remain/Remapp, 2026-08-18

## Ограничение источника

Полного дампа Remain DataLens (336 объектов) в репозитории нет. Решение
пользователя (2026-08-18): работать по уже собранному
`REMAIN_GAP_ANALYSIS_2026-07-29.md` (153 продажных объекта, частичный охват —
не эквивалент полного сопоставления). `only_local` не оценён — требует
полного дампа Remain, иначе счётчик будет ложно занижен.

## Счётчики (обновлено 2026-08-18, после разбора конфликтов)

| Категория | Кол-во |
|---|---|
| exact_match | 9 |
| probable_match | 4 |
| only_remain (в слое) | 4 |
| only_local | n/a — недоступно без полного дампа Remain |
| conflict | 1 (resolved_scope_difference, не ошибка данных) |

## Конфликты — разобраны вручную (без полного дампа, точечно по 3 объектам)

Полного табличного дампа Remain (координаты/GLA/GBA по всем 336 объектам) на
момент разбора нет — см. переписку 2026-08-18. Эти 3 конфликта из аудита
`24fc171` перепроверены индивидуально через официальные сайты застройщиков
(WebSearch/WebFetch), не через Remain-датасет:

| Remain | Наш объект | Было | Стало |
|---|---|---|---|
| Botanica Plaza | Plaza Botanica (proj-170) | адрес "1-я ул. Леонова, д. 1" (не существует), координаты 55.842236/37.646247 | **exact_match**: адрес исправлен на офиц. "ул. Вильгельма Пика, д. 11" (botanicaplaza.moscow, м. Ботанический сад), координаты 55.839861/37.6365. GBA/GLA не менялись. |
| Rail.A | Rail.A (proj-173) | координаты 55.778947/37.686671 (~0.34 км от Remain) | **exact_match**: координаты уточнены по rail-a.ru — 55.779406/37.687831. Адрес и девелопер (ORTIGA Development) совпадали изначально. |
| Бизнес-квартал Прокшино Башни 1/2/3 | А101 Прокшино (proj-216) | GBA 42000 vs Remain-сумма 113029 | **conflict, resolved_scope_difference**: официальные материалы А101 (commercial.a101.ru/bk-prokshino) подтверждают весь квартал — 5 корпусов, >177 тыс. кв. м совокупно; наша запись — один корпус (квартал №35). Это разница масштаба, не ошибка. GBA/GLA **не менялись** — нужна разбивка по building, вне рамок этой задачи. |

Источники: [botanicaplaza.moscow](https://botanicaplaza.moscow/), [rail-a.ru](https://rail-a.ru/), [commercial.a101.ru/bk-prokshino](https://commercial.a101.ru/bk-prokshino/).

## Добавленные only_remain записи (external_only=true) — web-проверка 2026-08-18

`remain-only-0001..0004`. Проверены по офиц. сайтам девелоперов (WebSearch/
WebFetch) — это НЕ NF-подтверждение лотов, только сигнал "объект/лоты
реально существуют или нет":

| ID | Объект | Итог web-проверки | verification_status |
|---|---|---|---|
| remain-only-0001 | МФК Центральный Телеграф | **REJECTED**: здание целиком куплено Т-Банком под корп. университет (voshodmoscow.ru/projects/tsentralnyy-telegraf), план 22 лотов отменён | `blocked`, `offer_status=Не применяется`, `project_status=Заморожен` |
| remain-only-0002 | ЗИЛАРТ GRAND (Дом 18) | лоты подтверждены (lsr.ru/msk/kommercheskaya-nedvizhimost/zilart) | `under_review`, confidence medium |
| remain-only-0003 | Sydney City | лоты подтверждены (fsk.ru/kommercheskaya-nedvizhimost/sydney-city/sale) | `under_review`, confidence medium |
| remain-only-0004 | Moscow Towers | лоты подтверждены (moscow-city-towers.ru/sale) | `under_review`, confidence medium |

Все 4 остаются `public_visibility=internal_only`, `quarter_offer_exists=false`,
`quarter_offer_refs=[]`, `market_channel=[]` — web-подтверждение не заменяет
NF-подтверждение конкретного лота в квартальном срезе, поэтому public/accepted
не проставлял.

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
external_only/quarter_offer_exists=false, разрешённые конфликты
(координаты Botanica Plaza/Rail.A, неизменность GBA/GLA Прокшино),
regression на потерю Remain-записей при пересборке слоя. Полный набор:
`python -m unittest discover -s tests -p "test_*.py"` — 164/164 OK.

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
