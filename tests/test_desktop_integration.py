import configparser
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_ID = "io.github.scientifica007.TroikaDLite"
DESKTOP = ROOT / "data" / f"{APP_ID}.desktop"
METAINFO = ROOT / "data" / f"{APP_ID}.metainfo.xml"
ICON = (
    ROOT
    / "data"
    / "icons"
    / "hicolor"
    / "scalable"
    / "apps"
    / f"{APP_ID}.svg"
)


class DesktopIntegrationTests(unittest.TestCase):
    def test_desktop_entry_matches_application_id(self):
        parser = configparser.ConfigParser(interpolation=None)
        parser.optionxform = str
        parser.read(DESKTOP, encoding="utf-8")
        entry = parser["Desktop Entry"]

        self.assertEqual(entry["Type"], "Application")
        self.assertEqual(entry["Name"], "Troika D Lite")
        self.assertEqual(entry["Exec"], "troika-d-lite")
        self.assertEqual(entry["Icon"], APP_ID)
        self.assertEqual(entry["Terminal"], "false")

    def test_appstream_component_matches_desktop_entry(self):
        root = ET.parse(METAINFO).getroot()
        self.assertEqual(root.findtext("id"), APP_ID)
        self.assertEqual(
            root.find("launchable").text.strip(),
            f"{APP_ID}.desktop",
        )
        self.assertEqual(
            root.find("launchable").attrib["type"],
            "desktop-id",
        )

    def test_icon_is_valid_svg_with_matching_filename(self):
        root = ET.parse(ICON).getroot()
        self.assertTrue(root.tag.endswith("svg"))
        self.assertEqual(ICON.stem, APP_ID)


if __name__ == "__main__":
    unittest.main()
