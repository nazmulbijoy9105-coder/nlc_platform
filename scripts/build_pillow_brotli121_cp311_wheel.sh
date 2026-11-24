#!/usr/bin/env bash
# Rebuild the Pillow 13.0.0 CPython 3.11 manylinux wheel with Brotli 1.2.1.
# Uses Pillow's own cibuildwheel recipe and test command. Run on Linux with Docker.
set -euo pipefail

readonly PILLOW_COMMIT="293218ad059d994baf1777d882911bed6a49704a"
readonly PILLOW_VERSION="13.0.0"
readonly BROTLI_OLD="1.2.0"
readonly BROTLI_FIXED="1.2.1"
readonly BUILD_TAG="1brotli121"
readonly ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly WORK="${ROOT}/.build/pillow-brotli121"
readonly SOURCE="${WORK}/Pillow"
readonly VENV="${WORK}/venv"
readonly WHEELHOUSE="${WORK}/wheelhouse"
readonly DIST="${ROOT}/dist/pillow-brotli121"

rm -rf "${WORK}" "${DIST}"
mkdir -p "${WORK}" "${WHEELHOUSE}" "${DIST}"

git clone --quiet --no-checkout --filter=blob:none https://github.com/python-pillow/Pillow.git "${SOURCE}"
git -C "${SOURCE}" checkout --quiet "${PILLOW_COMMIT}"
git -C "${SOURCE}" submodule update --init --recursive --depth 1

python3 - "${SOURCE}/.github/dependencies.json" "${BROTLI_OLD}" "${BROTLI_FIXED}" <<'PY'
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
old, fixed = sys.argv[2:]
data = json.loads(path.read_text(encoding="utf-8"))
if data.get("brotli") != old:
    raise SystemExit(
        f"Refusing unexpected Pillow dependency baseline: brotli={data.get('brotli')!r}"
    )
data["brotli"] = fixed
path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
PY

git -C "${SOURCE}" diff --check
git -C "${SOURCE}" diff -- .github/dependencies.json

python3 -m venv "${VENV}"
"${VENV}/bin/python" -m pip install --disable-pip-version-check -r "${SOURCE}/.ci/requirements-cibw.txt" wheel

(
  cd "${SOURCE}"
  CIBW_PLATFORM=linux \
  CIBW_ARCHS=x86_64 \
  CIBW_BUILD="cp311-manylinux*" \
  "${VENV}/bin/python" -m cibuildwheel --output-dir "${WHEELHOUSE}"
)

shopt -s nullglob
wheels=("${WHEELHOUSE}"/*.whl)
if (( ${#wheels[@]} != 1 )); then
  printf 'Expected exactly one CPython 3.11 Linux wheel; found %s\n' "${#wheels[@]}" >&2
  printf '%s\n' "${wheels[@]}" >&2
  exit 1
fi

"${VENV}/bin/wheel" tags --remove --build "${BUILD_TAG}" "${wheels[0]}"
mv "${WHEELHOUSE}"/*.whl "${DIST}/"
wheel_file=("${DIST}"/*.whl)
if [[ "${#wheel_file[@]}" -ne 1 ]]; then
  echo "Expected exactly one tagged wheel after build-tagging" >&2
  exit 1
fi

# Independently inspect the installed wheel and the actual decoder API version.
VERIFY_VENV="${WORK}/verify-venv"
python3 -m venv "${VERIFY_VENV}"
"${VERIFY_VENV}/bin/python" -m pip install --disable-pip-version-check --no-deps "${wheel_file[0]}"
"${VERIFY_VENV}/bin/python" - <<'PY'
import ctypes
import pathlib
import re
import PIL

libdir = pathlib.Path(PIL.__file__).resolve().parent.parent / "pillow.libs"
libs = sorted(
    p for p in libdir.glob("libbrotli*")
    if "brotlidec" in p.name or "brotlicommon" in p.name
)
if not libs:
    raise SystemExit(f"No bundled Brotli decoder/common libraries in {libdir}")

required = {"brotlidec", "brotlicommon"}
found = set()
for path in libs:
    match = re.search(r"\.so\.(\d+)\.(\d+)\.(\d+)$", path.name)
    if not match:
        raise SystemExit(f"Unrecognized bundled Brotli SONAME: {path.name}")
    version = tuple(map(int, match.groups()))
    if version < (1, 2, 1):
        raise SystemExit(f"Vulnerable bundled Brotli library: {path.name}")
    for kind in required:
        if kind in path.name:
            found.add(kind)

if found != required:
    raise SystemExit(f"Missing bundled Brotli libraries: {sorted(required - found)}")

decoder = next(path for path in libs if "brotlidec" in path.name)
api = ctypes.CDLL(str(decoder))
api.BrotliDecoderVersion.restype = ctypes.c_int
api_version = api.BrotliDecoderVersion()
if api_version < 10201:
    raise SystemExit(f"BrotliDecoderVersion()={api_version}; expected >= 10201")

print(f"Pillow {PIL.__version__}: {PIL.__file__}")
print(f"Bundled libraries: {[path.name for path in libs]}")
print(f"BrotliDecoderVersion(): {api_version}")
PY

(
  cd "${DIST}"
  sha256sum *.whl > SHA256SUMS
  {
    echo "Pillow version: ${PILLOW_VERSION}"
    echo "Pillow source commit: ${PILLOW_COMMIT}"
    echo "Pillow source tag: ${PILLOW_VERSION}"
    echo "Only source change: .github/dependencies.json brotli ${BROTLI_OLD} -> ${BROTLI_FIXED}"
    echo "Build tag: ${BUILD_TAG}"
    echo "Target: CPython 3.11, Linux x86_64, manylinux"
    echo "Wheel test suite: cibuildwheel ran Pillow's pyproject.toml test-command"
    echo "Independent validation: installed wheel, verified both bundled Brotli SONAMEs and BrotliDecoderVersion() >= 10201"
    echo
    cat SHA256SUMS
  } > BUILD_PROVENANCE.txt
)
printf 'Built and validated wheel: %s\n' "${wheel_file[0]}"
cat "${DIST}/SHA256SUMS"
