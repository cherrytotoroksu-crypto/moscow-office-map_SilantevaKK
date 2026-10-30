import sys, unittest, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lot_scraper'))
import engine                       # noqa: E402
from core import Result             # noqa: E402

T = {'project_id': 999, 'sub_id': '01', 'project': 'Тест', 'corpus': 'К1', 'url': 'https://example.invalid/x', 'site': 'x'}


def make(lots):
    r = Result(T)
    for a, p in lots:
        r.add(lot_id=str(a), area=a, price_total=p, price_m2=round(p / a) if a and p else None)
    return r


class EngineSafetyTests(unittest.TestCase):
    def setUp(self):
        self._h = engine.HISTORY
        self._tmp = tempfile.TemporaryDirectory()
        engine.HISTORY = Path(self._tmp.name)

    def tearDown(self):
        engine.HISTORY = self._h
        self._tmp.cleanup()

    def test_stale_fallback_uses_last_good_run(self):
        engine.save_last(make([(50, 15_000_000), (60, 18_000_000)]))
        bad = Result(T)
        bad.error = 'ConnectTimeout'
        r = engine.stale_fallback(bad)
        self.assertIsNone(r.error)
        self.assertEqual(len(r.lots), 2)
        self.assertTrue(r.stale)
        self.assertIn('УСТАРЕВШИЕ ДАННЫЕ', r.lots[0]['flags'])

    def test_no_history_keeps_error(self):
        bad = Result(T)
        bad.error = 'x'
        self.assertEqual(engine.stale_fallback(bad).error, 'x')

    def test_failed_run_is_not_saved(self):
        bad = make([(50, 15_000_000)])
        bad.error = 'x'
        engine.save_last(bad)
        self.assertIsNone(engine.load_last(T))

    def test_anomalies(self):
        prev = {'date': '2026-10-01', 'lots': make([(50, 15_000_000)] * 10).lots}
        r = make([(50, 15_000_000)] * 3 + [(50, 500_000)])          # лотов -60%, один ₽/м² вне коридора
        engine.check_anomalies(r, prev)
        text = ' '.join(r.notes)
        self.assertIn('вне разумного коридора', text)
        self.assertIn('изменилось сильно', text)
        self.assertIn('вне коридора', r.lots[-1]['flags'])

    def test_zero_lots_flagged(self):
        r = Result(T)
        engine.check_anomalies(r, None)
        self.assertIn('0 лотов', r.notes[0])


if __name__ == '__main__':
    unittest.main()
