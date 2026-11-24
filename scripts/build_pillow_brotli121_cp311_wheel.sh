#!/usr/bin/env bash
# Build Pillow 13.0.0 from its hash-verified PyPI sdist with Brotli 1.2.1.
# Restore only Pillow's wheel recipe and pinned test fixtures from its exact source tag.
set -euo pipefail

readonly PILLOW_COMMIT="293218ad059d994baf1777d882911bed6a49704a"
readonly TEST_IMAGES_COMMIT="073ab5ff1895abf8cf5c8d797c1066ed394ce207"
readonly PILLOW_VERSION="13.0.0"
readonly PILLOW_SDIST_SHA256="cdcd1ba258178f7356d74170c9a81ba4eab6a5d55748bc402a5a2a6fe6be3510"
readonly PILLOW_SDIST_URL="https://files.pythonhosted.org/packages/ce/a4/9cc30690a394a8305e8be4c9036aa16d0dfddadd09079860b582f562496d/pillow-13.0.0.tar.gz"
readonly BROTLI_OLD="1.2.0"
readonly BROTLI_FIXED="1.2.1"
readonly BUILD_TAG="1brotli121"
readonly WHEEL_TOOL_VERSION="0.48.0"
readonly ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly NLC_REPO_COMMIT="$(git -C "${ROOT}" rev-parse HEAD)"
readonly WORK="${ROOT}/.build/pillow-brotli121"
readonly RECIPE="${WORK}/Pillow-wheel-recipe"
readonly SOURCE="${WORK}/sdist/pillow-13.0.0"
readonly VENV="${WORK}/venv"
readonly WHEELHOUSE="${WORK}/wheelhouse"
readonly DIST="${ROOT}/dist/pillow-brotli121"

rm -rf "${WORK}" "${DIST}"
mkdir -p "${WORK}/sdist" "${WHEELHOUSE}" "${DIST}"

# Download the official sdist and verify PyPI's published SHA-256.
curl --fail --location --silent --show-error "${PILLOW_SDIST_URL}" \
  --output "${WORK}/pillow-${PILLOW_VERSION}.tar.gz"
printf '%s  %s\n' "${PILLOW_SDIST_SHA256}" "${WORK}/pillow-${PILLOW_VERSION}.tar.gz" \
  | sha256sum --check --status
tar -xzf "${WORK}/pillow-${PILLOW_VERSION}.tar.gz" -C "${WORK}/sdist"

# The sdist intentionally prunes .ci and wheels. Restore the exact 13.0.0
# wheel-building recipe and its pinned test-image submodule, not package source.
git clone --quiet --no-checkout --filter=blob:none https://github.com/python-pillow/Pillow.git "${RECIPE}"
git -C "${RECIPE}" checkout --quiet "${PILLOW_COMMIT}"
git -C "${RECIPE}" submodule update --init --recursive --depth 1
cp -a "${RECIPE}/.github" "${SOURCE}/.github"
cp -a "${RECIPE}/.ci" "${SOURCE}/.ci"
cp -a "${RECIPE}/wheels" "${SOURCE}/wheels"
git clone --quiet --no-checkout --filter=blob:none https://github.com/python-pillow/test-images.git "${WORK}/test-images"
git -C "${WORK}/test-images" fetch --quiet --depth 1 origin "${TEST_IMAGES_COMMIT}"
git -C "${WORK}/test-images" checkout --quiet "${TEST_IMAGES_COMMIT}"
cp -a "${WORK}/test-images" "${SOURCE}/test-images-main"

# The only package build input changed from the released source is Brotli's
# dependency version in Pillow's wheel manifest; refuse any other baseline.
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
print("Patched wheel dependency manifest:", json.dumps(data, sort_keys=True))
PY

python3 -m venv "${VENV}"
"${VENV}/bin/python" -m pip install --disable-pip-version-check -r "${SOURCE}/.ci/requirements-cibw.txt" "wheel==${WHEEL_TOOL_VERSION}"
actual_wheel_tool_version="$("${VENV}/bin/python" -c 'import wheel; print(wheel.__version__)')"
if [[ "${actual_wheel_tool_version}" != "${WHEEL_TOOL_VERSION}" ]]; then
  printf 'Expected wheel tool %s; found %s\n' "${WHEEL_TOOL_VERSION}" "${actual_wheel_tool_version}" >&2
  exit 1
fi

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

# Inspect the installed wheel and call the decoder's version API. Brotli encodes
# versions as (major << 24) | (minor << 12) | patch.
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
api.BrotliDecoderVersion.restype = ctypes.c_uint32
encoded = api.BrotliDecoderVersion()
decoded = (encoded >> 24, (encoded >> 12) & 0xFFF, encoded & 0xFFF)
if decoded < (1, 2, 1):
    raise SystemExit(f"BrotliDecoderVersion()={decoded}; expected >= (1, 2, 1)")

print(f"Pillow {PIL.__version__}: {PIL.__file__}")
print(f"Bundled libraries: {[path.name for path in libs]}")
print(f"BrotliDecoderVersion(): {decoded}")
PY

(
  cd "${DIST}"
  sha256sum *.whl > SHA256SUMS
  {
    echo "NLC build recipe commit: ${NLC_REPO_COMMIT}"
    echo "Pillow version: ${PILLOW_VERSION}"
    echo "Pillow source: verified PyPI sdist"
    echo "Pillow sdist SHA-256: ${PILLOW_SDIST_SHA256}"
    echo "Pillow wheel-recipe source commit: ${PILLOW_COMMIT}"
    echo "Pillow test-images commit: ${TEST_IMAGES_COMMIT}"
    echo "Only package build input changed: Brotli ${BROTLI_OLD} -> ${BROTLI_FIXED}"
    echo "Build tag: ${BUILD_TAG}"
    echo "Wheel tag-rewriting tool: wheel ${WHEEL_TOOL_VERSION}"
    echo "Target: CPython 3.11, Linux x86_64, manylinux"
    echo "Wheel test suite: cibuildwheel ran Pillow's pyproject.toml test-command"
    echo "Independent validation: bundled decoder/common SONAMEs >= 1.2.1 and BrotliDecoderVersion() >= (1, 2, 1)"
    echo
    cat SHA256SUMS
  } > BUILD_PROVENANCE.txt
)
printf 'Built and validated wheel: %s\n' "${wheel_file[0]}"
cat "${DIST}/SHA256SUMS"
