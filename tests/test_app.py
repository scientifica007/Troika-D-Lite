import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from troika_d_lite.app import collision_safe_output_path


class OutputPathTests(unittest.TestCase):
    def test_default_name_matches_product_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = collision_safe_output_path(
                Path(tmp),
                datetime(2026, 9, 24, 14, 32, 18),
            )
            self.assertEqual(
                result.name,
                "TroikaD-Lite_2026-09-24_14-32-18.mp4",
            )

    def test_existing_file_is_never_silently_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            first = directory / "TroikaD-Lite_2026-09-24_14-32-18.mp4"
            first.touch()
            result = collision_safe_output_path(
                directory,
                datetime(2026, 9, 24, 14, 32, 18),
            )
            self.assertEqual(
                result.name,
                "TroikaD-Lite_2026-09-24_14-32-18_01.mp4",
            )


if __name__ == "__main__":
    unittest.main()
