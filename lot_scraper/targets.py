"""Что выгружаем: корпус -> сайт/парсер. ID проекта и SubID из свода Q3 2026."""
T = []


def add(site, pid, sub, project, corpus, url, **kw):
    T.append(dict(site=site, project_id=pid, sub_id=sub, project=project, corpus=corpus, url=url, **kw))


add('avium', 115, '02', 'Avium', 'Корпус 2', 'https://avium.ru/parametric-choose/?type=office', avium_building=2)

add('hydra', 165, '01', 'Opus', 'Opus', 'https://opus-bc.ru/api/hydra/data', page='https://opus-bc.ru/plans')
add('hydra', 136, '01', 'K-city', 'Корпус 1', 'https://kobzon.city/api/hydra/data', page='https://kobzon.city/search')

add('coldy', 158, '01', 'Солид', 'Солид', 'https://coldy.city/offices', coldy_project='Солид')
add('coldy', 201, '01', 'Taller', 'Корпус Восток', 'https://coldy.city/offices', coldy_project='Таллер', coldy_corpus='Корпус Восток')
add('coldy', 201, '02', 'Taller', 'Корпус Запад', 'https://coldy.city/offices', coldy_project='Таллер', coldy_corpus='Корпус Запад')

add('ahead', 109, '01', 'Ahead', 'Ahead', 'https://aheadmoscow.ru/shop/apartments/?type=office')
add('peredelkino_offices', 297, '01', 'Родина Переделкино', 'Корпус 6 (офисы)', 'https://peredelkino-offices.ru/offices/')
add('air', 112, '01', 'Air', 'Корпус 1', 'https://air.pro/offices', air_corpus='Корпус 1')
add('air', 112, '02', 'Air', 'Корпус 2', 'https://air.pro/offices', air_corpus='Корпус 2')
add('geolog', 128, '01', 'Geolog 2', 'GEOLOG 2', 'https://geolog2.moscow/')

add('donstroy', 252, '01', 'Бизнес-парк Раменки', 'Корпус 1', 'https://donstroy.moscow/offices/?projects%5B%5D=2820&view_type=offices', donstroy_project=2820)

for _sub, _b in (('02', 7), ('03', 12), ('04', 14)):
    add('riverpark', 279, _sub, 'River Park Коломенское', f'Корпус {_b}', 'https://river-park.ru/lots/table/', river_building=_b)

add('chalet', 272, '01', 'CHALET Пятницкая 40', 'Корпус «Пятницкая»', 'https://chalet40.moscow/office/pyatnitskaya', chalet_section='pyatnitskaya')
add('chalet', 272, '02', 'CHALET Пятницкая 40', 'Корпус «Голиковский»', 'https://chalet40.moscow/office/golikovsky', chalet_section='golikovsky')

_P = 'https://a101.ru/commercial/pomeshheniya-i-uchastki/?deal=sell&project='
add('a101', 216, '04', 'А101 Прокшино', 'Корпус 3.1', _P + 'bk-prokshino', a101_project='bk-prokshino', a101_building='3.1', a101_types=['Офис'])
add('a101', 216, '02', 'А101 Прокшино', 'Корпус 2.1', _P + 'bk-prokshino', a101_project='bk-prokshino', a101_building='2.1', a101_types=['Офис'])
add('a101', 278, '01', 'Бизнес-хаб Потапово', 'Корпус В (1.1)', _P + 'biznes-hab-potapovo', a101_project='biznes-hab-potapovo', a101_building='В')
add('a101', 278, '02', 'Бизнес-хаб Потапово', 'Корпус С (1.2)', _P + 'biznes-hab-potapovo', a101_project='biznes-hab-potapovo', a101_building='С')
add('a101', 278, '03', 'Бизнес-хаб Потапово', 'Корпус Д (1.3)', _P + 'biznes-hab-potapovo', a101_project='biznes-hab-potapovo', a101_building='Д')

add('tsetlin', 249, '01', 'Цетлин', 'Цетлин', 'https://tsetlin.moscow/')

add('granelle', 97, '01', 'Звенигородская от Гранель', 'БЦ «Звенигородская от Гранель»', 'https://granelle.ru/offices/?project=zvenigorodskaya', granelle_name='Звенигородская от Гранель')
