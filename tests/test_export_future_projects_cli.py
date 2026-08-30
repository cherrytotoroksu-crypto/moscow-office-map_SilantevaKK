import contextlib
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'export_future_projects.py'


def load_module():
    spec = importlib.util.spec_from_file_location('export_future_projects', SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ExportFutureProjectsCliTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_source_is_required(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                self.module.parse_args([])

    def test_source_and_stats_are_explicit_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'source.xlsx'
            stats = root / 'stats.json'
            args = self.module.parse_args([
                '--source', str(source),
                '--stats', str(stats),
            ])

        self.assertEqual(args.source, source)
        self.assertEqual(args.stats, stats)

    def test_main_rejects_missing_source_before_loading_workbook(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / 'missing.xlsx'
            with self.assertRaisesRegex(FileNotFoundError, 'не найдена'):
                self.module.main(['--source', str(missing)])


if __name__ == '__main__':
    unittest.main()
