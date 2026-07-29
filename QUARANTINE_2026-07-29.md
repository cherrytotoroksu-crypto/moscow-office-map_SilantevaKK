# Quarantine / open items — 2026-07-29

Follow-up to `CODEX_CURRENT_ACCEPTANCE_AND_NEXT_STEPS_2026-07-29.md`. Verified independently by Claude Code; nothing here has been force-fixed without evidence.

## 6 known placeholder-coordinate rows (all historical, not live) — triaged

All six currently sit on the same placeholder point (55.755819, 37.617644 — Red Square area). Investigated each via WebSearch to decide fix vs. quarantine, per instruction "недоказанные строки оставить в карантине".

**Out of scope — QUARANTINE (not Moscow, do not force a Moscow coordinate):**
- `Европейский Берег (Новосибирск)` — `name_orig` itself says Novosibirsk; developer field is "Практик" (a multi-city coworking network). This is the network's Novosibirsk branch, mixed into the Moscow dataset by mistake.
- `Астана (Сыганак ул., 60/4)` — confirmed via WebSearch: this is "Практик" network's Astana, Kazakhstan branch (Сыганак ул., 60/4 is an exact address match to a Praktik Office location in Astana). Not Moscow.
- **✅ ACTIONED 2026-07-29** (was: "recommendation, not actioned yet"). Both are now genuinely out of the active Moscow set, not merely described here:
  - `classifier.html` RAW_DATA: each row tagged `"out_of_scope": true` + explicit `"city"` ("Новосибирск" / "Астана"); `lat`/`lng` set to `null` (the Red Square placeholder removed, no Moscow point substituted); fabricated Moscow geo-fields `ao`/`raion`/`zone`/`submarket`/`bizFormed` nulled — they had been derived from the placeholder coordinate and were polluting district-level aggregates.
  - Render path: added `const ACTIVE_DATA = RAW_DATA.filter(r => !r.out_of_scope);`. Both `render()` and `countColors()` now iterate `ACTIVE_DATA`, so the rows cannot appear in the table and no longer inflate the colour counters. Row totals: 279 in RAW_DATA → **277 active**.
  - `data/coworking_202503.json`: both records deleted outright (this is the only quarterly file that carried them), so they cannot be drawn on the index.html map for any quarter.
  - The rows stay in RAW_DATA on purpose, tagged, so the import error remains traceable rather than vanishing silently.
  - Guarded by `tests/test_moscow_scope_regression.py` — see below.

### Regression guard: Moscow bounds / city field
`tests/test_moscow_scope_regression.py` asserts that every active row with coordinates falls inside the Moscow bounding box (lat 55.10–56.05, lng 36.75–38.00, incl. TiNAO), that the two known non-Moscow entities stay tagged + coordinate-free, that no out-of-scope row ever keeps a coordinate, that the render path still filters on `out_of_scope`, and that neither entity reappears in any quarterly `buildings_*` / `coworking_*` file.

**It immediately caught a real pre-existing bug:** `Регус (Гринвуд)` sat on `55.078473, 37.764492` — about 87 km outside Moscow — in **8** historical coworking files (202403–202512). This is the already-diagnosed QA-005 error, which had been fixed only in the live quarter and explicitly left unfixed in the older ones. Corrected to the previously verified `55.868617, 37.403261` (the value already in `coworking_202606.json`, matching the recorded address "72 км МКАД, п/о Путилково, стр. 19"). This is propagation of an existing verified coordinate, **not** a new guess. `data/coworking_geocode_cache.json` still holds the stale value but is gitignored and does not feed the map.

**Confirmed Moscow, real address found, precise coordinate still pending (not yet geocoded to house-level):**
- `Мой Кабинет (Сириус Парк)` — Москва, Каширское шоссе, 3, стр. 12 (м. Нагатинская). Source: brightrich.moscow, m2data.net, co-working.moscow.
- `Атмосфера (Известия)` — Москва, Тверская ул., 18, стр. 1 (здание «Известий»). Source: kovorkingi.ru, officenavigator.ru.
- `Атмосфера (РИО на Ленинском)` — Москва, Ленинский просп., 109, ТРЦ «РИО» (6-й этаж). Source: 2ГИС, co-atmosphere.ru.
- `Атмосфера (Квартал Вэст)` — Аминьевское шоссе, 6, Москва. Source: co-atmosphere.ru.
- **Status (unchanged as of 2026-07-29):** addresses are solid (2+ independent listings agree per building), but none has been run through the Geocoder/Yandex Maps house-level lookup yet — do that before writing a new lat/lng, per project's coordinate-fix protocol (address+coordinate only change together). **These four were deliberately NOT touched in the 2026-07-29 pass** (explicit instruction: do not guess or accept unverified coordinates). They remain the 4 blocking errors reported by `scripts/validate_classifier.py`, down from 6 — the other 2 were the non-Moscow rows now excluded above. `tests/test_moscow_scope_regression.py` reports their count as `active_rows_still_on_placeholder: 4` but does **not** assert on them, so the quarantine stays visible without blocking.

## 12 name-collision warnings

Not attempted this pass. These are a structural issue (COLORMAP keys by display name, so one key colors every row sharing that name even when lat/lng/address differ) — same class of problem already flagged as QA-011's scope in `qa_handoff.json` (stable per-row IDs, not name-based keys). Fixing 12 of these one at a time without the underlying ID scheme risks the exact failure mode already caught once this project (Upside Кунцево silently losing a field to a later duplicate key). Recommend resolving the ID scheme first, then revisiting.

## Source manifest, 17 periods × 4 channels

Not attempted. Codex's own `qa_handoff.json` entry for this exact task already concluded it needs QA-010 (a `source_offer_id` schema decision) resolved first, or the manifest "would just create more ambiguous rows, not fewer." Agreeing with that reasoning rather than re-attempting it without a schema.

## Segment separation (sale / rent / coworking / construction starts)

No mixing found: `data/lots_202606.json` rows use scheme `area, block, floor, price, scheme, size, total` (sale); rent rows use a distinct schema (`area, block, finish, floor, nds, opex, rate, size`); coworking rows use `address, bc, district, id, lat, lng, name, network, rate, seats, vacancy`. Confirmed structurally separated, not commingled.

## Construction completion dates QA (2026-07-29, second pass) — Codex audit of all 86 "Строится" records

Source: `Q2_2026_construction_completion_dates_audit_ALL_86.xlsx` (Codex). Applied per the
stated rules (confidence=A auto-apply unless MIXED/BLOCKED/REVIEW; confidence=B re-verify
via source_url before applying; C/D never auto-changed; MIXED_PHASE needs corpus-level lot
attribution first, not touched this round). Full accounting of all 86 rows:

- **32 applied** (19 from clean A-tier, 13 from B-tier after independent WebFetch
  re-verification). Only `status`, `commission_q` (classifier.html) and `year`, `status`
  (data/buildings_202606.json) touched — no areas, prices, lot counts, or lot composition
  changed. Every applied row has source_url + evidence preserved in `classifier.html` NOTES.
- **3 B-tier skipped as unconfirmed** despite the audit recommending a change: QOOB (cited
  source actually says "not yet completed", contradicting the recommended Построен flip),
  Jois (cited source doesn't mention the project at all; independent search shows
  conflicting per-tower dates), Set (cited source gives two different, undisambiguated
  dates for the same project). Rule 2 requires confirmation before applying — none found.
- **6 MIXED_PHASE skipped** (ВАРСТ, А101 Прокшино, Upside Tech Сколково, Бизнес-хаб
  Потапово, Lavin, Light City) — per rule 4, these need lots attached to specific
  corpuses/phases before any single year can be assigned; not attempted this round.
- **9 C/D-tier rows left untouched, no automatic changes**: Север.Сити, БЦ Сколковский,
  Эйлер, Башня Рябов (explicitly named by the user to stay blocked) + МФК Юг, БЦ
  Варшавская, Cityzen, Level Нижегородская, Плэйн (бывший — Workplace Авиационная).
- **36 rows required no value change** (current state already matched the audit's
  recommendation) — left as-is, no NOTES noise added for these.

**Two corrections to the audit's own extraction, found during re-verification (not
blindly trusted):**
- **Twist** — audit cited novostroy-m.ru as saying "Q2 2026"; re-fetching that exact URL
  on 2026-07-29 shows "3 квартал 2026" with a 04.07.26 progress-update timestamp. Applied
  the independently-confirmed Q3, not the audit's claimed Q2 (also matches an existing,
  older NOTES entry for the same building from a different source).
- **Upside Останкино** — audit's source_url (`upside-yamskaya.ru`) is the developer's
  *other* project's site, not Upside Останkino's own domain. Verified independently via
  the real official site + cross-checked against Remain's independently-tracked dataset
  (`REMAIN_GAP_ANALYSIS_2026-07-29.md`) — both agree on Q4 2027. Applied 2027/Q4, not the
  stale 2028 that was in our data.

**One flagged identity concern, not resolved, left as an open question:** Бизнес-парк
Раменки (бывший — Огни)'s audit evidence mentions "Донстрой" as the developer to check
against — but that appears to be a *different* project by that name (Донстрой's own
"Раменки" on ул. Лобачевского, seen independently in Remain's dataset). Our building's
developer (Группа Аквилон) was confirmed correct by the actually-cited source
(wewall.ru); year updated to 2029, no quarter added (audit's own evidence calls Q4 a
"market rumor", not primary-sourced).

## ASPACE Никольская / ASPACE Хорошевская

Confirmed current state: `ASPACE Хорошевская` present in `data/buildings_202606.json` with `on_sale: "да"` (a real sale BC, not a serviced-office mislabel). Searched for `ASPACE Никольская` in `data/buildings_202606.json` and `data/lots_202606.json` — no match found, i.e. it has NOT been reintroduced to sale. No action needed, just confirmed.

## 97 technical records vs. 96 analytical projects

Confirmed: `data/buildings_202606.json` has 97 sale-side records; for an analytical project count, `Бадаевский Восточная лента` + `Бадаевский Западная лента` count as one project (Бадаевский), giving 96. Keeping this distinction explicit in any future count/table so the two numbers aren't conflated.
