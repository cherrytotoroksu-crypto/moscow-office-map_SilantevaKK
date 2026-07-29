# Quarantine / open items — 2026-07-29

Follow-up to `CODEX_CURRENT_ACCEPTANCE_AND_NEXT_STEPS_2026-07-29.md`. Verified independently by Claude Code; nothing here has been force-fixed without evidence.

## 6 known placeholder-coordinate rows (all historical, not live) — triaged

All six currently sit on the same placeholder point (55.755819, 37.617644 — Red Square area). Investigated each via WebSearch to decide fix vs. quarantine, per instruction "недоказанные строки оставить в карантине".

**Out of scope — QUARANTINE (not Moscow, do not force a Moscow coordinate):**
- `Европейский Берег (Новосибирск)` — `name_orig` itself says Novosibirsk; developer field is "Практик" (a multi-city coworking network). This is the network's Novosibirsk branch, mixed into the Moscow dataset by mistake.
- `Астана (Сыганак ул., 60/4)` — confirmed via WebSearch: this is "Практик" network's Astana, Kazakhstan branch (Сыганак ул., 60/4 is an exact address match to a Praktik Office location in Astana). Not Moscow.
- **Recommendation:** exclude both from the live Moscow classifier (or tag with an explicit `out_of_scope: true` / city field) rather than assign them any Moscow point. Not actioned yet — needs a decision on removal vs. tagging convention.

**Confirmed Moscow, real address found, precise coordinate still pending (not yet geocoded to house-level):**
- `Мой Кабинет (Сириус Парк)` — Москва, Каширское шоссе, 3, стр. 12 (м. Нагатинская). Source: brightrich.moscow, m2data.net, co-working.moscow.
- `Атмосфера (Известия)` — Москва, Тверская ул., 18, стр. 1 (здание «Известий»). Source: kovorkingi.ru, officenavigator.ru.
- `Атмосфера (РИО на Ленинском)` — Москва, Ленинский просп., 109, ТРЦ «РИО» (6-й этаж). Source: 2ГИС, co-atmosphere.ru.
- `Атмосфера (Квартал Вэст)` — Аминьевское шоссе, 6, Москва. Source: co-atmosphere.ru.
- **Status:** addresses are solid (2+ independent listings agree per building), but none has been run through the Geocoder/Yandex Maps house-level lookup yet — do that before writing a new lat/lng, per project's coordinate-fix protocol (address+coordinate only change together).

## 12 name-collision warnings

Not attempted this pass. These are a structural issue (COLORMAP keys by display name, so one key colors every row sharing that name even when lat/lng/address differ) — same class of problem already flagged as QA-011's scope in `qa_handoff.json` (stable per-row IDs, not name-based keys). Fixing 12 of these one at a time without the underlying ID scheme risks the exact failure mode already caught once this project (Upside Кунцево silently losing a field to a later duplicate key). Recommend resolving the ID scheme first, then revisiting.

## Source manifest, 17 periods × 4 channels

Not attempted. Codex's own `qa_handoff.json` entry for this exact task already concluded it needs QA-010 (a `source_offer_id` schema decision) resolved first, or the manifest "would just create more ambiguous rows, not fewer." Agreeing with that reasoning rather than re-attempting it without a schema.

## Segment separation (sale / rent / coworking / construction starts)

No mixing found: `data/lots_202606.json` rows use scheme `area, block, floor, price, scheme, size, total` (sale); rent rows use a distinct schema (`area, block, finish, floor, nds, opex, rate, size`); coworking rows use `address, bc, district, id, lat, lng, name, network, rate, seats, vacancy`. Confirmed structurally separated, not commingled.

## ASPACE Никольская / ASPACE Хорошевская

Confirmed current state: `ASPACE Хорошевская` present in `data/buildings_202606.json` with `on_sale: "да"` (a real sale BC, not a serviced-office mislabel). Searched for `ASPACE Никольская` in `data/buildings_202606.json` and `data/lots_202606.json` — no match found, i.e. it has NOT been reintroduced to sale. No action needed, just confirmed.

## 97 technical records vs. 96 analytical projects

Confirmed: `data/buildings_202606.json` has 97 sale-side records; for an analytical project count, `Бадаевский Восточная лента` + `Бадаевский Западная лента` count as one project (Бадаевский), giving 96. Keeping this distinction explicit in any future count/table so the two numbers aren't conflated.
