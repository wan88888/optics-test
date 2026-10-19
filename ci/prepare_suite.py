"""Create a clean CI suite without changing local device/browser settings."""

import argparse
import csv
from pathlib import Path
import shutil

import yaml

ROOT = Path(__file__).resolve().parents[1]


def prepare_mobile_modules(path, platform):
    """Allow a cold emulator to start and capture the screen before teardown."""
    with path.open(newline="") as source:
        reader = csv.DictReader(source)
        fields = reader.fieldnames
        rows = list(reader)
    prepared = []
    for row in rows:
        if (platform == "android" and row["module_name"] == "Verify Login Page"
                and row["module_step"] == "Assert Visibility"
                and row["param_1"] == "${Username_Input}"):
            # Optics 1.11.0 divides this budget between native lookup and OCR.
            # 120 gives the native lookup up to 60 seconds on a cold CI emulator.
            row["param_2"] = "120"
        if row["module_step"] == "Close And Terminate App":
            for keyword in ("Capture Screenshot", "Capture Pagesource"):
                prepared.append({**dict.fromkeys(fields, ""),
                                 "module_name": row["module_name"],
                                 "module_step": keyword})
        prepared.append(row)
    with path.open("w", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(prepared)


def prepare_suite(platform, destination, *, udid=None, device_name=None, platform_version=None):
    destination = Path(destination).resolve()
    if destination.exists():
        raise ValueError(f"CI output must be a new directory: {destination}")
    if platform == "ios" and not (udid and platform_version):
        raise ValueError("iOS requires the CI simulator UDID and platform version")

    source = ROOT / platform
    config = yaml.safe_load((source / "config.yaml").read_text())
    driver = next(iter(config["driver_sources"][0].values()))
    caps = driver["capabilities"]
    if platform == "web":
        # Optics 1.11.0 supports headless; the desktop maximization wrapper is unnecessary.
        caps.update(headless=True, viewport={"width": 1280, "height": 900})
        caps.pop("maximize", None)
        caps.pop("slow_mo", None)
    else:
        # Jobs have isolated runners, so both may use the normal Appium port.
        driver["url"] = "http://127.0.0.1:4723"
        caps["udid"] = udid or "emulator-5554"
        caps["deviceName"] = device_name or caps["udid"]
        caps.update(noReset=True, forceAppLaunch=True, shouldTerminateApp=True)
        if platform == "ios":
            caps["platformVersion"] = platform_version
            caps["derivedDataPath"] = str(destination.parent / "wda-derived-data")
            # simctl already booted this simulator without a UI. Otherwise
            # XCUITest restarts it to display Simulator during session creation.
            caps["isHeadless"] = True
            # ci/build_wda.sh compiles separately, outside Optics' 300s request.
            caps["usePrebuiltWDA"] = True
            caps["showXcodeLog"] = True
            caps["wdaLaunchTimeout"] = 120000
            caps["wdaStartupRetries"] = 1

    destination.mkdir(parents=True)
    for directory in ("test_cases", "modules", "test_data"):
        shutil.copytree(source / directory, destination / directory)
    if platform != "web":
        prepare_mobile_modules(destination / "modules" / "modules.csv", platform)
    (destination / "config.yaml").write_text(yaml.safe_dump(config, sort_keys=False))
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("platform", choices=("web", "android", "ios"))
    parser.add_argument("destination", type=Path)
    parser.add_argument("--udid")
    parser.add_argument("--device-name")
    parser.add_argument("--platform-version")
    args = parser.parse_args()
    print(prepare_suite(args.platform, args.destination, udid=args.udid,
                        device_name=args.device_name, platform_version=args.platform_version))


if __name__ == "__main__":
    main()
