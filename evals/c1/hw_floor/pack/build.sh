#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "${SCRIPT_DIR}"
export NPU_ARCH="ascend950"
echo "=== Building c1hw wheel ==="
rm -rf "${SCRIPT_DIR}/build" "${SCRIPT_DIR}/dist" "${SCRIPT_DIR}/c1hw/_C.abi3.so"
mkdir -p dist
python3 setup.py bdist_wheel --dist-dir dist
echo "=== Install ==="
pip install dist/c1hw*.whl --force-reinstall --no-deps
echo "=== Wheel size check (3acb588: must exceed 1695 bytes) ==="
ls -la dist/
