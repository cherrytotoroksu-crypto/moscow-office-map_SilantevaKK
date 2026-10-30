import sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.sync_api import sync_playwright
u=sys.argv[1]; sel=sys.argv[2] if len(sys.argv)>2 else 'body'
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(); got=[]
    def on(r):
        q=r.request
        if q.resource_type in('xhr','fetch') and 'yandex' not in r.url and 'rutube' not in r.url:
            try: n=len(r.body())
            except Exception: n=-1
            got.append((q.method,r.url[:700],(q.post_data or '')[:300],n))
    pg.on('response',on)
    try: pg.goto(u,wait_until='domcontentloaded',timeout=45000)
    except Exception as e: print('NAV',str(e)[:80])
    pg.wait_for_selector(sel,timeout=30000)
    for _ in range(6):
        pg.mouse.wheel(0,3000); pg.wait_for_timeout(1500)
    print('rows',len(pg.query_selector_all(sel)))
    for g in got: print(g)
    b.close()
