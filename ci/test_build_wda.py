"""Check the build/session path contract and propagate xcodebuild failures."""

import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest

from prepare_suite import ROOT, prepare_suite


class BuildWDATests(unittest.TestCase):
    def run_build(self, status):
        with tempfile.TemporaryDirectory(prefix="wda test ") as temporary:
            root = Path(temporary)
            suite = prepare_suite("ios", root / "suite", udid="CI-SIMULATOR", platform_version="18.5")
            commands = root / "bin"
            commands.mkdir()
            python = commands / "python"
            python.write_text(f'#!/bin/sh\nexec {shlex.quote(sys.executable)} "$@"\n')
            python.chmod(0o755)
            for name, source in {
                "node": 'import os; print(os.environ["WDA_PACKAGE"])',
                "xcrun": ('import json,os,sys; print(json.dumps(sys.argv[1:])); '
                          'sys.exit(int(os.environ["XCODE_STATUS"]))'),
            }.items():
                command = commands / name
                command.write_text(f"#!{sys.executable}\n{source}\n")
                command.chmod(0o755)
            env = {**os.environ, "PATH": str(commands) + os.pathsep + os.environ["PATH"],
                   "APPIUM_HOME": str(root / "appium"), "OPTICS_CI_UDID": "CI-SIMULATOR",
                   "WDA_PACKAGE": str(root / "WDA source" / "package.json"),
                   "XCODE_STATUS": str(status)}
            result = subprocess.run(["bash", str(ROOT / "ci/build_wda.sh"), str(suite)],
                                    env=env, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, status, result.stderr)
            log = (suite / "wda-build.log").read_text()
            args = json.loads(log)
            self.assertEqual(args[:2], ["xcodebuild", "build-for-testing"])
            self.assertEqual(args[args.index("-derivedDataPath") + 1], str(suite.parent / "wda-derived-data"))
            self.assertEqual(args[args.index("-destination") + 1], "id=CI-SIMULATOR")
            self.assertEqual(args[args.index("-project") + 1], str(root / "WDA source/WebDriverAgent.xcodeproj"))
            self.assertIn("CODE_SIGNING_ALLOWED=NO", args)
            self.assertIn("GCC_TREAT_WARNINGS_AS_ERRORS=0", args)

    def test_build_uses_session_paths_and_handles_spaces(self):
        self.run_build(0)

    def test_failed_build_is_not_hidden_by_successful_tee(self):
        self.run_build(65)


if __name__ == "__main__":
    unittest.main()
