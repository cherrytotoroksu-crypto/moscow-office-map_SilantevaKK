# Селекторы из Web Scraper (прислала пользователь, 14.09.2026)

Рабочие карты сайтов (Chrome-расширение Web Scraper). Селекторы = подсказки для своих парсеров. Проверять перед использованием: вёрстка могла измениться.

## Платформы с одним набором селекторов
- **workplace.forma.ru/list?projects=ID** (Frame 2157, Gustav 2120, Jenga 2194, Lakes2 2227, Lavin 2125, Minto 2079, Mount 2178): строка `tr[class*="ListItem_row"]`; площадь `div[itemprop="area"]`; этаж `div[itemprop="floorsCount"]`; цена `div[itemprop="price"]`; пагинация кнопкой (номер кнопки разный: 4-7).
- **novostroy-m.ru/commerce/novostroyka/<slug>/sale** (Бизнес-парк Переделкино `biznespark_peredelkino`, Строгино `biznestsentr_strogino_strogino`, Light City `biznestsentr_light_city_layt`, Omni `biznestsentr_omni_tower`, Solo `jk_na_soljenitsyna_27`): карточка `.new_list_item`; цена `span.def_black`; имя `.title_link`; корпус `div.flat_line_item:contains("Корпус") div.fl_r`; ссылка `a.layout`; этаж на странице лота `.data_card_row:contains("Этаж") .data_card_item`; подгрузка `button.js-pager-load-grid`.
- **brightrich.moscow/biznes-centry/<slug>/** (ASPACE `aspace-horoshevskaya`, Ольховая SKY `olhovaya-sky`, Рябов `bashnya-ryabov`, Север.Сити `sever-siti`, SEZAR `sezar-tower`, Цетлин `cetlin`): строка `div.commerce-var-item`; площадь `p.vbig:nth-of-type(1)`; цена `p[data-period-group='price_sale_all']`; этаж `li:nth-of-type(1) span`; пагинация `.tab-content button.btn-primary`.
- **kf.expert/office/...** (Ahead `mnogofunkcionalnyy-kompleks/kutuzovskij-os38039`, Деловой Дуэт `business-center/delovoj-duet-os47891`, Октябрьское поле `business-center/oktyabrskoe-pole-os47929`): строка `div.detail-filter__result-table-row-content`; поля `span.detail-filter__result-table-row-text--area|floor|price`; пагинация `button.shared-pagination__button--next`.
- **d-a.ru/projects/offices/<noon|qoob>/choose/#/list/offices/** (NOON, QOOB): строка `div.table-row-content-list`; площадь `div.w-cell-sq`; цена `div.flat-card__price`; этаж `div.w-cell-floor`; корпус `.w_35 div:nth-of-type(2)`.
- **mr-group.ru** (One, Set; хэшированные CSS-классы, ломаются при обновлении): карточка `a._wrapper_le5xd_1217`, имя `span._productTitle_le5xd_1342`, цена `div._value_1wksr_1217`, детали `div._hoverable_le5xd_1239`, «ещё» `button._showMore_1jzy0_117`. URL: `/offices/pomeshcheniya/one-offices/area-from-103-to-2051/?grid=card`, `/set-offices/?grid=card&tabs=0`. Для остальных MR (Bell, Cityzen, Mind, iCITY, Top Tower, Jois): API `/api/realty/objects?category=offices&project[]=...&limit=200` (см. память, Cityzen).

## Одиночные сайты
- AFI2B Тагильская `https://afi2b.ru/#` и AFI Воронцовский `https://bc.afi-v-park.ru/`: карточка `.found-cnt-flex a`, имя `h4`, этаж/площадь `div.found-cnt-href:nth-of-type(1|2) span`, цена `.found-cnt-price > span`, кнопка `button.shoMoreAction`.
- Aurus `https://of.ru/bc/stranasiti/prodaja`: карточка `div.large`.
- Avium `https://avium.ru/parametric-choose/`: строка `div.table-row-content`, колонки `div.w-cell-building|floor|area|price`.
- Emotion `https://gk-osnova.ru/emotion/office-premises`: карточка `div.project-plan-card`, цена `h4.project-plan-card__price`, детали `h5.project-plan-card__number`.
- Эйлер `https://euler.moscow/search`: строка `div.results-table__row`, ячейки `.tr_n .f .sq .ter .tc_sq .tc`.
- Geolog2 `https://geolog2.moscow/`: строка `div.offices__row`, `.offices__col-size|price-meter|price`.
- KORP Молодёжная `https://msk.group-akvilon.ru/project/korpmolodezhnaya/commercial/...`: хэшированные классы.
- Nevsky Plaza `https://krost.ru/commercial/objects/?complex=82&ordering=ppm&deal=1`: карточка `a.LotCard_isL6E`.
- Родина Парк `https://rodinapark.ru/commerce?...`: карточка `a.comm__card`.
- Бизнес-парк Переделкино (Абсолют) в Web Scraper шёл через novostroy-m, наш каталог в реестре — peredelkino-park.ru.

# Готовые скрипты пользователя (Downloads/Telegram Desktop), API
- **A101** (`fetch_a101_potapovo.py`): GET `https://a101.ru/api/commercial/?deal=sell&order=actual_price&project=<slug>&limit=100&offset=0`, без куки; поля article, building, floor, area, actual_price, actual_ppm, status (1 свободно, 2-3 продано, 4-5 бронь), stage_key_transfer_date. Slug: biznes-hab-potapovo, bk-prokshino.
- **Upside** (Ямская, Tech/Сколково; Кунцево/Останкино вероятно так же): POST `https://<сайт>/api/realty-filter/custom/real-estates`, заголовок `X-Host`, тело `{project_id, filters:[{id:status,type:system,filter_type:select,value:[free]}], limit:50, offset}`; нужна кука `session` (протухает, брать из браузера, в код не вшивать). project_id Ямская 3c8fc3b8-ea20-4162-913f-9a704692f66f, Tech 92f7d09e-1881-4aad-9369-10211aff55df. Поля number, building_number, floor_number, total_area, price, ppm, finishing_type.
- **Донстрой/Раменки** (`fetch_donstroy.py`): POST `https://donstroy.moscow/api/v1/offices/choose_params_api_flats/`, куки PHPSESSID, фильтры price/area/floor, page; ответ flats[], total_flats.
- **STONE**: PDF-прайсы (`parse_stone_offices*.py`, pdfplumber, имена `STONE_<проект>___<башня>.pdf`), лоты `SD-304`, `G1-500`; колонки Лот/Площадь/Цена за м²/Цена лота/Статус. Сайт stone.ru недоступен с этой сети, берём PDF.
- `parse_offices.py`: JSON Remapp (реестр офисных зданий, не лоты).

# Диагностика сети (30.10.2026)
`curl`: TCP-соединение (connect=0) с workplace.forma.ru, a101.ru, stone.ru не устанавливается; coldy.city открывается (200). Chrome пользователя на forma тоже даёт страницу ошибки. Значит блок на уровне сети/IP (VPN, провайдер, гео), а не защита от ботов.
