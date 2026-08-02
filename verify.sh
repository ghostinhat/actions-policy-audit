#!/usr/bin/env bash
set -Eeuo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHONPATH="$root" python3 -m unittest discover -s "$root/tests" -p 'test_*.py'
python3 "$root/actions_policy_audit.py" "$root" --fail-on none >/dev/null
