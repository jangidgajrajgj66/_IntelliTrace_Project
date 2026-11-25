#!/usr/bin/env bash
set -e

PYTHON_BIN="${PYTHON_BIN:-python3}"

case "${1:-}" in
  --all)
    "$PYTHON_BIN" main.py --all
    ;;
  --api)
    "$PYTHON_BIN" main.py --api
    ;;
  --dashboard)
    "$PYTHON_BIN" main.py --dashboard
    ;;
  --test)
    "$PYTHON_BIN" main.py --test
    ;;
  --traffic)
    "$PYTHON_BIN" main.py --traffic
    ;;
  --scenario)
    "$PYTHON_BIN" main.py --scenario "${2:-queue}"
    ;;
  *)
    echo "IntelliTrace — Autonomous SRE & Incident Intelligence Platform (by Gajraj Jangid)"
    echo "Usage: ./run.sh [--all | --api | --dashboard | --test | --traffic | --scenario <name>]"
    "$PYTHON_BIN" main.py --all
    ;;
esac

