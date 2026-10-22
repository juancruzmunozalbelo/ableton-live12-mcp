#!/usr/bin/env bash
# ==============================================================================
# Ableton Live 12 MCP Automated Verification Test Runner
# ==============================================================================
# Usage:
#   ./scripts/run_live_tests.sh [OPTIONS]
#
# Options:
#   --mock        Force offline mock mode (simulates Ableton Live 12 LOM)
#   --live        Force live mode (requires running Ableton Live 12 + Remote Script)
#   --tier <tier> Run specific tier: tier1, tier2, tier3, tier4 (default: all)
#   -v, --verbose Verbose output
#   -h, --help    Show this help message
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

# Default parameters
TEST_MODE="auto"
TARGET_TIER=""
VERBOSE_FLAG="-v"

# Parse CLI arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --mock)
      TEST_MODE="mock"
      shift
      ;;
    --live)
      TEST_MODE="live"
      shift
      ;;
    --manual)
      TARGET_TIER="manual"
      shift
      ;;
    --tier)
      TARGET_TIER="$2"
      shift 2
      ;;
    -v|--verbose)
      VERBOSE_FLAG="-vv"
      shift
      ;;
    -h|--help)
      echo "Ableton Live 12 MCP Test Runner"
      echo "Usage: ./scripts/run_live_tests.sh [--mock|--live] [--manual|--tier <tier1|tier2|tier3|tier4|tier5|manual>] [-v]"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

export ABLETON_TEST_MODE="${TEST_MODE}"
export PYTHONPATH="${PROJECT_ROOT}:${PROJECT_ROOT}/src:${PROJECT_ROOT}/tests:${PYTHONPATH:-}"

TEST_MODE_UPPER=$(echo "${TEST_MODE}" | tr '[:lower:]' '[:upper:]')
echo "======================================================================"
echo "  Ableton Live 12 MCP Automated Verification Test Suite"
echo "======================================================================"
echo "  Project Root : ${PROJECT_ROOT}"
echo "  Target Mode  : ${TEST_MODE_UPPER}"
echo "  Target Tier  : ${TARGET_TIER:-All Tiers}"
echo "======================================================================"

# Determine Python / pytest executable
if command -v pytest >/dev/null 2>&1; then
  PYTEST_CMD="pytest"
elif command -v python3 >/dev/null 2>&1; then
  PYTEST_CMD="python3 -m pytest"
else
  echo "Error: Neither pytest nor python3 found in PATH"
  exit 1
fi

# Build test target argument
TEST_TARGETS="tests/test_tier1_feature_isolation.py tests/test_tier2_boundaries_corners.py tests/test_tier3_pairwise_combos.py tests/test_tier4_production_flow.py tests/test_tier5_adversarial_hardening.py tests/test_tier5_domain_boundaries.py tests/test_ableton12_manual_20_chapters.py"
if [[ -n "${TARGET_TIER}" ]]; then
  case "${TARGET_TIER}" in
    tier1) TEST_TARGETS="tests/test_tier1_feature_isolation.py" ;;
    tier2) TEST_TARGETS="tests/test_tier2_boundaries_corners.py" ;;
    tier3) TEST_TARGETS="tests/test_tier3_pairwise_combos.py" ;;
    tier4) TEST_TARGETS="tests/test_tier4_production_flow.py" ;;
    tier5) TEST_TARGETS="tests/test_tier5_adversarial_hardening.py tests/test_tier5_domain_boundaries.py" ;;
    manual) TEST_TARGETS="tests/test_ableton12_manual_20_chapters.py" ;;
    *)
      echo "Unknown tier: ${TARGET_TIER} (choose: tier1, tier2, tier3, tier4, tier5, manual)"
      exit 1
      ;;
  esac
fi

echo ""
echo "Executing test target: ${TEST_TARGETS}"
echo "----------------------------------------------------------------------"

# Run tests
set +e
${PYTEST_CMD} ${TEST_TARGETS} ${VERBOSE_FLAG} --color=yes
TEST_EXIT_CODE=$?
set -e

echo ""
echo "======================================================================"
if [ ${TEST_EXIT_CODE} -eq 0 ]; then
  echo "  RESULT: ALL TESTS PASSED SUCCESSFULLY (100% Pass Rate)"
else
  echo "  RESULT: TEST SUITE REPORTED FAILURES (Exit code: ${TEST_EXIT_CODE})"
fi
echo "======================================================================"

exit ${TEST_EXIT_CODE}
