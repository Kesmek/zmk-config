# Local build setup

Reproduces the GitHub Actions build on this machine. CI still runs on every
push; this exists so the edit/flash loop does not wait on it.

Everything lands in `.zmk/` (gitignored) or `~/.local/share`. No `sudo`, and
no system packages are installed.

## Why the versions are pinned the way they are

Arch ships far newer tooling than Zephyr 3.5 expects, so three things need
pinning. Each of these was a hard build failure, not a warning:

| Pin | Reason |
|---|---|
| `cmake<4` in the venv | Zephyr 3.5 predates CMake 4. `FindZephyr-sdk.cmake` fails to parse under 4.x with "Unknown arguments specified". The venv copy must precede `/usr/bin/cmake` on `PATH`. |
| `setuptools<81` | nanopb's `protoc` wrapper imports `pkg_resources`, removed in setuptools 81. Only matters because the Studio build pulls in nanopb. |
| `protobuf` installed | nanopb's generator imports `google.protobuf`. Not in Zephyr's `requirements-base.txt`. |

Python 3.14 works otherwise. Zephyr SDK 0.16.3 is the pairing for Zephyr
3.5.0, which is what `config/west.yml` pins via `v3.5.0+zmk-fixes`.

## Steps

```fish
cd ~/zmk-config/.zmk

# west, in a venv so nothing touches the system python
python3 -m venv .venv
.venv/bin/pip install --upgrade pip west

# Zephyr and its modules (~2GB)
.venv/bin/west update
.venv/bin/west zephyr-export
.venv/bin/pip install -r zephyr/scripts/requirements-base.txt

# the pins from the table above
.venv/bin/pip install "cmake<4" "setuptools<81" protobuf

# ARM toolchain, ~400MB
cd ~/.local/share
curl -fsSLO https://github.com/zephyrproject-rtos/sdk-ng/releases/download/v0.16.3/zephyr-sdk-0.16.3_linux-x86_64_minimal.tar.xz
tar xf zephyr-sdk-0.16.3_linux-x86_64_minimal.tar.xz
cd zephyr-sdk-0.16.3
./setup.sh -t arm-zephyr-eabi -c
```

Then `./tools/build-local.sh`.

## A note on .west/config

The workspace originally carried these filters:

```
group-filter = -hal
project-filter = -lvgl,-nanopb,-zephyr,-zmk-studio-messages
```

That excludes Zephyr itself, the Nordic HAL, and the nanopb /
zmk-studio-messages pair the Studio build needs, so it could fetch sources
for editor navigation but never compile. Replaced with `group-filter = +hal`
and no project filter, matching CI. The original is at `.west/config.bak`.

## Verifying against CI

Local and CI artifacts come out the same size but not byte-identical, because
Zephyr embeds build paths and timestamps. Matching sizes plus a matching
`Memory region` report is the practical check.
