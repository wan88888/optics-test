#!/usr/bin/env bash
# Install the demo app, wait for Appium readiness, and preserve Optics' exit code.
set -euo pipefail
platform="$1"
suite_dir="$2"
app_path="$3"
device_udid="${OPTICS_CI_UDID:?OPTICS_CI_UDID must identify the CI device}"
appium_pid=""

cleanup() {
  local result=$?
  if [[ "$result" -ne 0 && -f "$suite_dir/appium.log" ]]; then
    echo '--- Appium log tail (full log is in the run artifact) ---' >&2
    tail -n 100 "$suite_dir/appium.log" >&2 || true
  fi
  # Optics captures the UI before closing the app. Also retain Android's crash
  # and system logs before android-emulator-runner shuts down the emulator.
  if [[ "$platform" == android ]]; then
    adb -s "$device_udid" logcat -d -t 2000 > "$suite_dir/logcat.txt" 2>&1 || true
    adb -s "$device_udid" shell dumpsys activity activities > "$suite_dir/activities.txt" 2>&1 || true
  fi
  if [[ -n "$appium_pid" ]]; then
    kill "$appium_pid" 2>/dev/null || true
    wait "$appium_pid" 2>/dev/null || true
  fi
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

case "$platform" in
  android) adb -s "$device_udid" install -r -g "$app_path" ;;
  ios) xcrun simctl install "$device_udid" "$app_path" ;;
  *) echo "Unsupported platform: $platform" >&2; exit 2 ;;
esac

appium --address 127.0.0.1 --port 4723 > "$suite_dir/appium.log" 2>&1 &
appium_pid=$!

ready=false
for ((attempt=0; attempt<90; attempt++)); do
  if ! kill -0 "$appium_pid" 2>/dev/null; then
    cat "$suite_dir/appium.log" >&2
    exit 1
  fi
  if curl --silent --fail --max-time 2 http://127.0.0.1:4723/status |
      python -c 'import json,sys; sys.exit(0 if json.load(sys.stdin)["value"]["ready"] else 1)' 2>/dev/null; then
    ready=true
    break
  fi
  sleep 1
done
if [[ "$ready" != true ]]; then
  cat "$suite_dir/appium.log" >&2
  echo 'Appium did not become ready within the startup deadline.' >&2
  exit 1
fi

cd "$suite_dir"
optics execute . --no-use-printer
