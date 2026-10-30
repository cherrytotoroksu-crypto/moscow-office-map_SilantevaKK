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

# --- STONE: JSON-API stone.ru/api/lots; корпус = поле housing (адреса страниц взяты из реестра Q3)
def _stone(pid, sub, project, corpus, page, projects, housing, **kw):
    add('stone', pid, sub, project, corpus, 'https://stone.ru/' + page, stone_projects=projects, stone_housing=housing, **kw)


_stone(177, '01', 'STONE Дмитровская', 'Офисная башня', 'catalog/offices/dmitrovskaya', '4', 'Офисная башня')
_stone(180, '01', 'STONE Калужская', 'Башня К1', 'catalog/offices/kaluzhskaya', '9,581', 'Башня К1')
_stone(180, '02', 'STONE Калужская', 'Башня К2', 'catalog/offices/kaluzhskaya', '9,581', 'Башня К2')
_stone(185, '01', 'STONE Мневники I', 'Башня M1', 'catalog/offices/mnyovniki-1-2', '617', 'Башня M1')
_stone(188, '01', 'STONE Мневники II', 'Башня M2.1', 'catalog/offices/mnyovniki-1-2', '617', 'Башня M2.1')
_stone(189, '01', 'STONE Мневники III', 'Башня M3.1', 'catalog/offices/mnyovniki-3', '616', 'Башня M3.1')
_stone(189, '02', 'STONE Мневники III', 'Башня M3.2', 'catalog/offices/mnyovniki-3', '616', 'Башня M3.2')
_stone(192, '01', 'STONE Римская', 'Башня R1', 'catalog/offices/rimskaya', '13', 'Башня R1')
_stone(192, '02', 'STONE Римская', 'Башня R2', 'catalog/offices/rimskaya', '13', 'Башня R2')
_stone(197, '01', 'STONE Ходынка II', 'Башня G1', 'catalog/offices/khodyinka-2', '7,583', 'Башня G1')
_stone(197, '03', 'STONE Ходынка II', 'Башня G3', 'catalog/offices/khodyinka-2', '7,583', 'Башня G3')
_stone(258, '01', 'STONE SKY Ходынка IV', 'Небоскреб F1', 'catalog/offices/sky-khodyinka', '7210', 'Небоскреб F1')
_stone(258, '02', 'STONE SKY Ходынка IV', 'Камерная башня F2', 'catalog/offices/sky-khodyinka', '7210', 'Камерная башня F2')
_stone(283, '01', 'STONE Tower E', 'Tower E', 'commercial/tower-e', '7139', 'Tower E', stone_direction='1,4,3')
_stone(289, '01', 'STONE Савеловская 2', 'Башня C1', 'catalog/offices/savelovskaya2', '7177,7216', 'Башня C1')

# --- Upside Останкино: Hydra commerce
_UO = 'https://upside-ostankino.ru'
add('hydra_commerce', 253, '02', 'Upside Останкино', 'Корпус 2', _UO + '/api/hydra/data/commerce', page=_UO + '/plans', hc_building=2)
add('hydra_commerce', 253, '01', 'Upside Останкино', 'Корпус 1', _UO + '/plans', page=_UO + '/plans', hc_whole='1')

# --- Level (business.level.ru), Мираполис (API gk-osnova), Twist
add('level', 144, '01', 'Level Воронцовская', 'Корпус 1', 'https://business.level.ru/filter/?project=wv', level_project='wv')
add('level', 267, '01', 'Level Нижегородская', 'Корпус 1', 'https://business.level.ru/filter/?project=wn&category=office', level_project='wn')
add('mirapolis', 284, '01', 'Мираполис', 'Мираполис', 'https://mirapolis.city/offices', mir_project=12)
add('twist', 205, '01', 'Twist', 'Корпус 1', 'https://twist-office.ru/vybor-pomeshcheniya/')
