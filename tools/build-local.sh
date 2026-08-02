#!/usr/bin/env bash
# Build both halves locally. Much faster than waiting on GitHub Actions:
# roughly 3s for a keymap-only change, against ~90s plus queue time in CI.
# CI still runs on push; this is for the edit/flash loop.
#
#   ./tools/build-local.sh              # build, output to ./firmware
#   ./tools/build-local.sh -p           # pristine (full rebuild)
#   ./tools/build-local.sh -o /tmp/fw   # choose the output directory
#
# One-time setup lives in tools/setup-local-build.md.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WS="$REPO/.zmk"
VENV="$WS/.venv"
OUT="$REPO/firmware"
PRISTINE=""

while getopts "po:" opt; do
    case $opt in
        p) PRISTINE="--pristine" ;;
        o) OUT="$OPTARG" ;;
        *) echo "usage: $0 [-p] [-o outdir]" >&2; exit 2 ;;
    esac
done

if [ ! -x "$VENV/bin/west" ]; then
    echo "No west in $VENV. See tools/setup-local-build.md." >&2
    exit 1
fi

# The venv's cmake (3.x) must win over the system one: Zephyr 3.5 does not
# build under CMake 4. The venv python must win too, for nanopb's generator.
export PATH="$VENV/bin:$PATH"

build() {
    local shield="$1" dir="$2"; shift 2
    if [ -d "$WS/build/$dir" ] && [ -z "$PRISTINE" ]; then
        # Already configured; skip the -D flags so cmake need not re-run.
        west build -s "$WS/zmk/app" -b nice_nano_v2 -d "$WS/build/$dir"
    else
        west build ${PRISTINE:+$PRISTINE} -s "$WS/zmk/app" -b nice_nano_v2 \
            -d "$WS/build/$dir" -- \
            -DSHIELD="$shield" -DZMK_CONFIG="$REPO/config" "$@"
    fi
}

cd "$WS"
echo "==> corne_left (studio)"
build corne_left left -DCONFIG_ZMK_STUDIO=y -DSNIPPET=studio-rpc-usb-uart
echo "==> corne_right"
build corne_right right

mkdir -p "$OUT"
cp "$WS/build/left/zephyr/zmk.uf2"  "$OUT/corne_left-nice_nano_v2-zmk.uf2"
cp "$WS/build/right/zephyr/zmk.uf2" "$OUT/corne_right-nice_nano_v2-zmk.uf2"

echo
ls -l "$OUT"/*.uf2 | awk '{printf "  %8d  %s\n", $5, $9}'
echo
echo "Flash the left half: double-tap reset, then"
echo "  cp $OUT/corne_left-nice_nano_v2-zmk.uf2 /run/media/\$USER/NICENANO/"
