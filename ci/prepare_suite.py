"""Create a clean CI suite without changing local device/browser settings."""

import argparse
from pathlib import Path
import shutil

import yaml

ROOT = Path(__file__).resolve().parents[1]


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
            caps["wdaLaunchTimeout"] = 180000

    destination.mkdir(parents=True)
    for directory in ("test_cases", "modules", "test_data"):
        shutil.copytree(source / directory, destination / directory)
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
