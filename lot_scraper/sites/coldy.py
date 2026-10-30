"""coldy.city (Солид, Таллер): карточки article.offices-card, рендер в браузере.
Цена берётся без скидки «-8% при 100% оплате» (опубликованная прайсовая)."""
import re
from bs4 import BeautifulSoup
from core import num, Result
from browser import render


def run(t):
    r = Result(t)
    try:
        html = render('https://coldy.city/offices', 'article.offices-card')
    except Exception as e:
        r.error = f'{type(e).__name__}: {str(e)[:80]}'
        return r
    cards = BeautifulSoup(html, 'lxml').select('article.offices-card')
    reserved = 0
    for c in cards:
        txt = c.get_text(' | ', strip=True)
        if t['coldy_project'] not in txt:
            continue
        if t.get('coldy_corpus') and t['coldy_corpus'] not in txt:
            continue
        if 'offices-card--reserved' in (c.get('class') or []) or 'Бронь' in txt:
            reserved += 1
            continue
        m_a = re.search(r'(?:Офис|Этаж),\s*([\d.,]+)\s*м²', txt)
        m_f = re.search(r'Этаж\s*\|\s*([\d–-]+)', txt)
        m_n = re.search(r'из\s*\d+\s*\|\s*([\d.]+)', txt)
        prices = [num(x) for x in re.findall(r'[\d ]{6,}\s*₽(?!\s*/)', txt.replace('\xa0', ' '))]
        ppm = re.search(r'([\d ]+)\s*₽\s*/\s*м²', txt.replace('\xa0', ' '))
        fin = 'Готовая отделка' if 'отделк' in txt.lower() else None
        flags = None
        disc = re.search(r'-\d+(?:\.\d+)?%', txt)
        if len(prices) >= 2:
            total = max(prices)          # цена без скидки за 100% оплату
            flags = f'на сайте есть цена со скидкой {min(prices):,.0f}'.replace(',', ' ')
        else:
            total = prices[0] if prices else None
        a = c.find('a', href=True)
        r.add(lot_id=m_n.group(1) if m_n else ('этаж ' + m_f.group(1) if m_f else None), lot_name=re.search(r'(?:Офис|Этаж),[^|]*', txt).group(0) if m_a else None,
              area=num(m_a.group(1)) if m_a else None, floor=(int(m_f.group(1)) if m_f.group(1).isdigit() else m_f.group(1)) if m_f else None, finish=fin,
              status='В продаже', price_total=total, price_m2=num(ppm.group(1)) if ppm else None,
              url=('https://coldy.city' + a['href']) if a and a['href'].startswith('/') else t['url'], flags=flags)
    if reserved:
        r.notes.append(f'бронь, не взято: {reserved}')
    if not cards:
        r.notes.append('карточки не появились')
    return r
