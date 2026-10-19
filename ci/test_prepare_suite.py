"""Regression checks for the local-to-CI configuration boundary."""

from pathlib import Path
import csv
import tempfile
import unittest

import yaml

from prepare_suite import ROOT, prepare_suite


class PrepareSuiteTests(unittest.TestCase):
    def test_ci_profiles_do_not_change_local_configuration(self):
        originals = {p: (ROOT / p / "config.yaml").read_bytes()
                     for p in ("web", "android", "ios")}
        with tempfile.TemporaryDirectory() as temporary:
            for platform in originals:
                with self.subTest(platform=platform):
                    options = ({"udid": "CI-SIMULATOR", "platform_version": "18.5"}
                               if platform == "ios" else {})
                    dest = prepare_suite(platform, Path(temporary) / platform, **options)
                    config = yaml.safe_load((dest / "config.yaml").read_text())
                    driver = next(iter(config["driver_sources"][0].values()))
                    caps = driver["capabilities"]
                    if platform == "web":
                        self.assertIs(caps["headless"], True)
                        self.assertNotIn("maximize", caps)
                        self.assertNotIn("slow_mo", caps)
                    else:
                        self.assertEqual(driver["url"], "http://127.0.0.1:4723")
                        self.assertEqual(caps["udid"], "CI-SIMULATOR" if platform == "ios"
                                         else "emulator-5554")
                    if platform == "ios":
                        self.assertTrue(caps["isHeadless"])
                        self.assertTrue(caps["usePrebuiltWDA"])
                        self.assertTrue(caps["showXcodeLog"])
                        self.assertEqual(caps["derivedDataPath"], str(dest.parent / "wda-derived-data"))
                        self.assertEqual(caps["wdaStartupRetries"], 1)
                        self.assertLess(caps["wdaLaunchTimeout"], 300000)
                        self.assertFalse(caps["connectHardwareKeyboard"])
                        self.assertTrue(caps["forceSimulatorSoftwareKeyboardPresence"])
                        self.assertEqual(caps["maxTypingFrequency"], 10)
                    else:
                        self.assertNotIn("usePrebuiltWDA", caps)
                        self.assertNotIn("maxTypingFrequency", caps)
                    self.assertFalse((dest / "execution_output").exists())
                    self.assertFalse((dest / "logs").exists())
                    for folder in ("test_cases", "modules", "test_data"):
                        for source in (ROOT / platform / folder).rglob("*.csv"):
                            copied = dest / source.relative_to(ROOT / platform)
                            if platform != "web" and folder == "modules":
                                with copied.open(newline="") as stream:
                                    rows = list(csv.DictReader(stream))
                                # Capture must run while the failed screen and session still exist.
                                self.assertEqual([r["module_step"] for r in rows[-3:]],
                                                 ["Capture Screenshot", "Capture Pagesource",
                                                  "Close And Terminate App"])
                                login = next(r for r in rows if r["param_1"] == "${Username_Input}")
                                self.assertEqual(login["param_2"], "120" if platform == "android" else "30")
                                # Only the initial wait and diagnostic steps may differ.
                                if platform == "android":
                                    login["param_2"] = "30"
                                with source.open(newline="") as stream:
                                    self.assertEqual(rows[:-3] + rows[-1:], list(csv.DictReader(stream)))
                            else:
                                self.assertEqual(source.read_bytes(), copied.read_bytes())
        for platform, content in originals.items():
            self.assertEqual((ROOT / platform / "config.yaml").read_bytes(), content)

    def test_rejects_existing_output_instead_of_reusing_stale_reports(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(ValueError):
                prepare_suite("web", Path(temporary))

    def test_ios_requires_ci_device_information_before_creating_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            dest = Path(temporary) / "ios"
            with self.assertRaises(ValueError):
                prepare_suite("ios", dest)
            self.assertFalse(dest.exists())


if __name__ == "__main__":
    unittest.main()
