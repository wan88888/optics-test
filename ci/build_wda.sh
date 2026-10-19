#!/usr/bin/env bash
# Compile the pinned driver's WDA before Optics starts its session timeout.
set -euo pipefail
suite_dir="$1"
: "${APPIUM_HOME:?APPIUM_HOME must point to the CI Appium installation}"
device_udid="${OPTICS_CI_UDID:?OPTICS_CI_UDID must identify the CI simulator}"

# Resolve through the driver so npm's nested or hoisted dependency layouts work.
wda_package=$(node -p 'require.resolve("appium-webdriveragent/package.json", {paths: [process.env.APPIUM_HOME + "/node_modules/appium-xcuitest-driver"]})')
wda_dir=$(dirname "$wda_package")
derived_data=$(python - "$suite_dir/config.yaml" <<'PY'
import sys
import yaml
with open(sys.argv[1]) as stream:
    config = yaml.safe_load(stream)
print(config["driver_sources"][0]["appium"]["capabilities"]["derivedDataPath"])
PY
)

xcrun xcodebuild build-for-testing \
  -project "$wda_dir/WebDriverAgent.xcodeproj" \
  -scheme WebDriverAgentRunner \
  -configuration Debug \
  -sdk iphonesimulator \
  -destination "id=$device_udid" \
  -derivedDataPath "$derived_data" \
  -resultBundlePath "$suite_dir/wda-build.xcresult" \
  CODE_SIGNING_ALLOWED=NO GCC_TREAT_WARNINGS_AS_ERRORS=0 COMPILER_INDEX_STORE_ENABLE=NO \
  2>&1 | tee "$suite_dir/wda-build.log"
