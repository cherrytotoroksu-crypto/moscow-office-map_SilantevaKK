"""Отрисовка страниц обычным Chromium (Playwright) для сайтов, где лоты строит JS.
Ничего не обходим: открываем страницу как обычный посетитель, ждём карточки, листаем вниз."""
import os, threading
from playwright.sync_api import sync_playwright

_lock = threading.Lock()
_cache = {}


def render(url, selector, scroll=True, timeout=45000, wait_ms=2500, click=None):
    """Вернуть HTML после появления selector и дозагрузки прокруткой. Результат кешируется на запуск."""
    key = (url, selector, click)
    with _lock:
        if key in _cache:
            return _cache[key]
        with sync_playwright() as p:
            proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
            b = p.chromium.launch(proxy={'server': proxy} if proxy else None)
            pg = b.new_page()
            try:
                pg.goto(url, wait_until='domcontentloaded', timeout=timeout)
                pg.wait_for_selector(selector, timeout=30000)
                if click:
                    for _ in range(60):
                        btn = pg.query_selector(click)
                        if not btn or not btn.is_visible():
                            break
                        try:
                            btn.click(timeout=4000)
                        except Exception:
                            btn.evaluate('e => e.click()')
                        pg.wait_for_timeout(wait_ms)
                if scroll:
                    prev = -1
                    for _ in range(40):
                        n = len(pg.query_selector_all(selector))
                        if n == prev:
                            break
                        prev = n
                        pg.mouse.wheel(0, 20000)
                        pg.wait_for_timeout(wait_ms)
                html = pg.content()
            finally:
                b.close()
        _cache[key] = html
        return html
