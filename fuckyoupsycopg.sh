#!/usr/bin/env bash
set -euo pipefail

echo "🔨 Fixing psycopg2 leakage & verifying clean build"
echo "--------------------------------------------------"

# -----------------------------
# CONFIG
# -----------------------------
PACKAGE_NAME="abstract_flask"
PYTHON_BIN="${PYTHON_BIN:-python}"
WORKDIR="$(pwd)"
TMP_VENV="/tmp/${PACKAGE_NAME}_pypi_test"

# -----------------------------
# STEP 1: uninstall anything psycopg-related
# -----------------------------
echo "🧹 Removing psycopg / psycopg2 from current env"
pip uninstall -y psycopg psycopg2 psycopg2-binary || true

# -----------------------------
# STEP 2: clean pip cache (VERY IMPORTANT)
# -----------------------------
echo "🧽 Purging pip cache"
pip cache purge || true

# -----------------------------
# STEP 3: hard clean build artifacts
# -----------------------------
echo "🧨 Removing build artifacts"
rm -rf build dist *.egg-info

# -----------------------------
# STEP 4: show declared dependencies (sanity check)
# -----------------------------
echo "🔍 Declared install_requires:"
${PYTHON_BIN} setup.py --requires || true

echo
echo "⚠️  If psycopg2 appears above, STOP and fix setup.py"
echo

# -----------------------------
# STEP 5: build wheel + sdist
# -----------------------------
echo "📦 Building package"
${PYTHON_BIN} -m build

# -----------------------------
# STEP 6: create clean venv
# -----------------------------
echo "🐍 Creating isolated test venv"
rm -rf "${TMP_VENV}"
${PYTHON_BIN} -m venv "${TMP_VENV}"
source "${TMP_VENV}/bin/activate"

pip install --upgrade pip setuptools wheel

# -----------------------------
# STEP 7: install built wheel ONLY
# -----------------------------
echo "🧪 Installing built wheel in clean env"
pip install dist/*.whl

# -----------------------------
# STEP 8: assert psycopg2 is NOT installed
# -----------------------------
echo "🔎 Checking installed packages"
if pip list | grep -E "psycopg2"; then
  echo "❌ ERROR: psycopg2 is STILL being pulled in"
  pip list
  exit 1
fi

echo "✅ SUCCESS: psycopg2 is NOT present"
echo
echo "🎉 Package is safe to upload to PyPI"
