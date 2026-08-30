import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP_PATH = ROOT / "tools" / "bootstrap_oceanengine_only.py"


def load_bootstrap_module():
    spec = importlib.util.spec_from_file_location("bootstrap_for_test", BOOTSTRAP_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BootstrapTests(unittest.TestCase):
    def test_initial_config_is_created_once_and_never_overwrites_existing_file(self):
        module = load_bootstrap_module()
        original_root = module.ROOT
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                (root / "config.example.json").write_text('{"main_accounts": []}', encoding="utf-8")
                module.ROOT = root

                self.assertTrue(module.ensure_initial_config())
                config = root / "自动关推广" / "config.json"
                self.assertEqual(config.read_text(encoding="utf-8"), '{"main_accounts": []}')

                config.write_text('{"keep": true}', encoding="utf-8")
                self.assertFalse(module.ensure_initial_config())
                self.assertEqual(config.read_text(encoding="utf-8"), '{"keep": true}')
        finally:
            module.ROOT = original_root
