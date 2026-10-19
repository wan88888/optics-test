#!/usr/bin/env bash
# Install the demo app, wait for Appium readiness, and preserve Optics' exit code.
set -euo pipefail
platform="$1"
suite_dir="$2"
app_path="$3"
device_udid="${OPTICS_CI_UDID:?OPTICS_CI_UDID must identify the CI device}"

case "$platform" in
  android) adb -s "$device_udid" install -r -g "$app_path" ;;
  ios) xcrun simctl install "$device_udid" "$app_path" ;;
  *) echo "Unsupported platform: $platform" >&2; exit 2 ;;
esac

appium --address 127.0.0.1 --port 4723 > "$suite_dir/appium.log" 2>&1 &
appium_pid=$!
cleanup() {
  kill "$appium_pid" 2>/dev/null || true
  wait "$appium_pid" 2>/dev/null || true
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

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
