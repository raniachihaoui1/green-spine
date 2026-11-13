#!/usr/bin/env bash
# Creates the gsenv environment with the exact tested versions (macOS / Linux).
# Usage:  bash setup_gsenv.sh
set -e
cd "$(dirname "$0")"
python3.13 -m venv gsenv
gsenv/bin/python -m pip install --upgrade pip
gsenv/bin/python -m pip install -r requirements-lock.txt
echo
echo "gsenv is ready. Activate it with:  source gsenv/bin/activate"
echo "Then run the app with:            streamlit run app.py"
