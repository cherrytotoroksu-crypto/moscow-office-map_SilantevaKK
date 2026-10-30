"""tsetlin.moscow (Сумма Элементов, Цетлин): Bitrix ajax, HTML-страницы по PAGEN_1."""
import re
from bs4 import BeautifulSoup
from core import get, num, Result

URL = 'https://tsetlin.moscow/local/ajax/content/catalog_items.php'


def run(t):
    r = Result(t)
    seen = set()
    declared = None
    try:
        for page in range(1, 30):
            html = get(URL if page == 1 else f'{URL}?PAGEN_1={page}', timeout=30).text
            s = BeautifulSoup(html, 'lxml')
            if page == 1:
                m = re.search(r'(\d+)\s*помещ', s.get_text(' '))
                declared = int(m.group(1)) if m else None
            items = s.select('.catalog__list-item')
            new = 0
            for it in items:
                num_el = it.select_one('.catalog__item-img-num span')
                lot = num_el.get_text(strip=True) if num_el else it.get('id')
                if lot in seen:
                    continue
                seen.add(lot)
                new += 1
                params = {p.select_one('.ttl').get_text(strip=True): p.select_one('.desc').get_text(strip=True)
                          for p in it.select('.catalog__item-parameter')}
                price = it.select_one('.catalog__item-price')
                ppm = it.select_one('.catalog__item-price-alt')
                r.add(lot_id=lot, lot_name=f'Офис {lot}', area=num(params.get('Площадь, м²')),
                      floor=num(params.get('Этаж')), status='В продаже',
                      price_total=num(price.get_text()) if price else None,
                      price_m2=num(ppm.get_text()) if ppm else None, url='https://tsetlin.moscow/')
            if not new:
                break
    except Exception as e:
        r.error = f'{type(e).__name__}: {str(e)[:80]}'
        return r
    if declared and declared != len(r.lots):
        r.notes.append(f'сайт заявил {declared}, получено {len(r.lots)}')
    return r
