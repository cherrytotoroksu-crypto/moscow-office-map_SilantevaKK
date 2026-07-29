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

**✅ RESOLVED 2026-07-29 (second pass, same day) — Codex `COORDINATE_PLACEHOLDER_RECHECK_2026-07-29.md`:**
- `Мой Кабинет (Сириус Парк)` — Каширское шоссе, 3с1к2. House-level candidate `55.671676, 37.630203` (`ACCEPT_CANDIDATE_HIGH`, Яндекс.Карты). Applied to `classifier.html` and every quarterly `data/coworking_*.json` row matching `id=7 + address` (202403, 202407 — the id does not appear in later quarters). Geo-fields recomputed via `scripts/recompute_geo.py` and verified bit-for-bit against the deterministic point-in-polygon output: Южный/Нагатино-Садовники/ТТК-МКАД/ТТК-МКАД Юг.
- `Атмосфера (Известия) (БЦ Известия)` — Тверская ул., 18. Candidate `55.766101, 37.604315` (`ACCEPT_CANDIDATE_MEDIUM` — two independent map points disagree by ~40 m, kept at medium confidence rather than green). Applied to `classifier.html` and `data/coworking_*.json` id=42 (202403–202506). Geo recompute verified: zone БК-СК, submarket СК Север (ao/raion/bizFormed unchanged, already correct).
- `Атмосфера (РИО на Ленинском) (ТЦ РИО на Ленинском)` — Ленинский пр-т, 109. Candidate `55.663843, 37.511445` (`ACCEPT_CANDIDATE_HIGH`). Applied to `classifier.html` and id=43 (202403–202506). Geo recompute verified: Юго-Западный/Обручевский/ТТК-МКАД/ТТК-МКАД Юго-Запад.
- `Атмосфера (Квартал Вэст) (Квартал Вэст)` — Аминьевское шоссе, 6. Candidate `55.707299, 37.456828` (`ACCEPT_CANDIDATE_HIGH`). Applied to `classifier.html` and id=44 (202403–202506). Geo recompute verified: Западный/Очаково-Матвеевское/ТТК-МКАД/ТТК-МКАД Запад.
- Rule followed exactly per Codex handoff: matched by `id + quarter + address` together, never by display name alone; all four now carry `COLORMAP` yellow entries + `NOTES` source citations (see classifier.html).
- `scripts/validate_classifier.py`: 0 blocking errors (was 4). `tests/test_moscow_scope_regression.py` now reports and **asserts** `active_rows_still_on_placeholder: 0` (was 4) — the docstring/assertion were updated the same pass so a future data refresh cannot silently regress these back onto the placeholder.

**Also checked in the same pass (not placeholder rows, but flagged in the same Codex document):**
- `Регус (Домников) (Домников)` — already at `55.772168, 37.648465` in `classifier.html`, matching Codex's own independently-verified candidate exactly (`ACCEPT_CANDIDATE_MEDIUM`, building centroid, not entrance/floor precision). No `classifier.html` change needed; only propagated to `data/coworking_*.json` rows for id=93 that still carried the old placeholder (202407, 202410, 202412, 202503, 202506, 202512).
- `Регус (Ситидел) (Citydel)` — address was stale/wrong (`Земляной Вал ул., 7`); corrected to `ул. Земляной Вал, 9` with coordinate `55.761691, 37.658536` (`ACCEPT_CANDIDATE_HIGH`, operator site + Яндекс.Карты agree on house 9). Applied to `classifier.html` and **all 10** quarterly `coworking_*.json` files including the live quarters (202603, 202606) — this bug had persisted into the live data. ao/raion/zone/submarket unchanged (new point ~80 m away, same district — confirmed via `recompute_geo.py`).
- `Север.Сити` (QA-007) — explicitly **left untouched**, stays `BLOCKED_BY_EVIDENCE`. Its `55.793481, 37.632511` reference point (Рижская площадь, 3) is recorded only as evidence in Codex's document, never written into `classifier.html` as a canonical coordinate — per direct instruction, the address of a neighbouring building must not stand in for the unconfirmed site of the future tower complex.

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
