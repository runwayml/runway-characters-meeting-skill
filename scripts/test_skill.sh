#!/usr/bin/env bash
# ============================================================================
# test_skill.sh — End-to-end smoke tests for runway_meeting.py
#
# Usage:
#   export RUNWAYML_API_SECRET=key_...
#   bash scripts/test_skill.sh [--live]
#
# Without --live: only tests argument parsing, --help, and validation (no API calls).
# With --live:    also tests real API calls (creates a voice, character, etc.).
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PY="python3 ${SCRIPT_DIR}/runway_meeting.py"
PASS=0
FAIL=0
LIVE=false

[[ "${1:-}" == "--live" ]] && LIVE=true

green()  { printf "\033[32m✓ %s\033[0m\n" "$1"; }
red()    { printf "\033[31m✗ %s\033[0m\n" "$1"; }
yellow() { printf "\033[33m⚠ %s\033[0m\n" "$1"; }

pass() { green "$1"; PASS=$((PASS + 1)); }
fail() { red "$1"; FAIL=$((FAIL + 1)); }

# Helper: expect exit code
expect_exit() {
    local label="$1" expected="$2"
    shift 2
    set +e
    "$@" >/dev/null 2>&1
    local got=$?
    set -e
    if [[ "$got" == "$expected" ]]; then
        pass "$label (exit $got)"
    else
        fail "$label (expected exit $expected, got $got)"
    fi
}

# Helper: expect output contains string
expect_contains() {
    local label="$1" needle="$2"
    shift 2
    set +e
    local output
    output=$("$@" 2>&1)
    local rc=$?
    set -e
    if echo "$output" | grep -qi "$needle"; then
        pass "$label"
    else
        fail "$label — expected '$needle' in output"
    fi
}

echo ""
echo "=============================="
echo " Runway Meeting Skill Tests"
echo "=============================="
echo ""

# ------------------------------------------------------------------
# 1. Help flags
# ------------------------------------------------------------------
echo "--- 1. Help & usage ---"

expect_exit "Main --help" 0  $PY --help
expect_exit "clone-yourself --help" 0  $PY clone-yourself --help
expect_exit "create-character --help" 0  $PY create-character --help
expect_exit "clone-voice --help" 0  $PY clone-voice --help
expect_exit "join --help" 0  $PY join --help
expect_exit "leave --help" 0  $PY leave --help
expect_exit "status --help" 0  $PY status --help
expect_exit "transcript --help" 0  $PY transcript --help
expect_exit "list --help" 0  $PY list --help

# ------------------------------------------------------------------
# 2. Argument validation (should fail with proper messages)
# ------------------------------------------------------------------
echo ""
echo "--- 2. Argument validation ---"

# Missing required args
expect_exit "clone-yourself: missing --name" 2  $PY clone-yourself --personality "hi"
expect_exit "clone-yourself: missing --personality" 2  $PY clone-yourself --name "Test"
expect_exit "join: missing --meeting-url" 2  $PY join --avatar-id abc
expect_exit "leave: missing --session-id" 2  $PY leave
expect_exit "status: missing --session-id" 2  $PY status
expect_exit "transcript: missing --avatar-id" 2  $PY transcript --session-id abc
expect_exit "transcript: missing --session-id" 2  $PY transcript --avatar-id abc

# Invalid subcommand
expect_exit "Invalid subcommand" 2  $PY bogus-command

# ------------------------------------------------------------------
# 3. API key validation
# ------------------------------------------------------------------
echo ""
echo "--- 3. API key validation ---"

# Unset API key and check commands that require it
(
    unset RUNWAYML_API_SECRET
    expect_contains "clone-yourself: no API key" "RUNWAYML_API_SECRET" \
        python3 "${SCRIPT_DIR}/runway_meeting.py" clone-yourself \
            --name "Test" --personality "test" --selfie /tmp/fake.jpg

    expect_contains "create-character --list: no API key" "RUNWAYML_API_SECRET" \
        python3 "${SCRIPT_DIR}/runway_meeting.py" create-character --list

    expect_contains "clone-voice --list: no API key" "RUNWAYML_API_SECRET" \
        python3 "${SCRIPT_DIR}/runway_meeting.py" clone-voice --list

    expect_contains "list: no API key" "RUNWAYML_API_SECRET" \
        python3 "${SCRIPT_DIR}/runway_meeting.py" list
)

# ------------------------------------------------------------------
# 4. clone-voice validation
# ------------------------------------------------------------------
echo ""
echo "--- 4. clone-voice argument validation ---"

# clone-voice with no args requires API key first, then validates args
# Test with API key set (if available)
if [[ -n "${RUNWAYML_API_SECRET:-}" ]]; then
    expect_contains "clone-voice: missing --name and --audio/--description" "required" \
        $PY clone-voice
    expect_contains "clone-voice: --preview without --description" "description" \
        $PY clone-voice --preview
else
    # Without API key, clone-voice exits on key check before arg validation
    expect_contains "clone-voice: no args → API key check" "RUNWAYML_API_SECRET" \
        $PY clone-voice
    expect_contains "clone-voice: --preview → API key check" "RUNWAYML_API_SECRET" \
        $PY clone-voice --preview
fi

# ------------------------------------------------------------------
# 5. File structure checks
# ------------------------------------------------------------------
echo ""
echo "--- 5. File structure ---"

check_file() {
    if [[ -f "$1" ]]; then
        pass "Exists: $(basename "$1")"
    else
        fail "Missing: $1"
    fi
}

check_file "${SCRIPT_DIR}/../SKILL.md"
check_file "${SCRIPT_DIR}/../README.md"
check_file "${SCRIPT_DIR}/../requirements.txt"
check_file "${SCRIPT_DIR}/../assets/monster.png"
check_file "${SCRIPT_DIR}/../assets/cat.png"
check_file "${SCRIPT_DIR}/../assets/warrior.png"
check_file "${SCRIPT_DIR}/../assets/boy.png"
check_file "${SCRIPT_DIR}/runway_meeting.py"

# ------------------------------------------------------------------
# 6. Python import check
# ------------------------------------------------------------------
echo ""
echo "--- 6. Python import ---"

expect_exit "Import runway_meeting module" 0 \
    python3 -c "import importlib.util; spec = importlib.util.spec_from_file_location('m', '${SCRIPT_DIR}/runway_meeting.py'); m = importlib.util.module_from_spec(spec)"

# Check requests is installed
expect_exit "requests package installed" 0 \
    python3 -c "import requests"

# ------------------------------------------------------------------
# 7. LIVE TESTS (only with --live flag + valid API key)
# ------------------------------------------------------------------
if $LIVE; then
    echo ""
    echo "--- 7. Live API tests ---"

    if [[ -z "${RUNWAYML_API_SECRET:-}" ]]; then
        yellow "Skipping live tests: RUNWAYML_API_SECRET not set"
    else
        # List characters
        echo "  Testing create-character --list..."
        set +e
        OUTPUT=$($PY create-character --list 2>/dev/null)
        RC=$?
        set -e
        if [[ $RC -eq 0 ]]; then
            pass "create-character --list"
        else
            fail "create-character --list (exit $RC)"
        fi

        # List voices
        echo "  Testing clone-voice --list..."
        set +e
        OUTPUT=$($PY clone-voice --list 2>/dev/null)
        RC=$?
        set -e
        if [[ $RC -eq 0 ]]; then
            pass "clone-voice --list"
        else
            fail "clone-voice --list (exit $RC)"
        fi

        # List all
        echo "  Testing list..."
        set +e
        OUTPUT=$($PY list 2>/dev/null)
        RC=$?
        set -e
        if [[ $RC -eq 0 ]]; then
            pass "list"
        else
            fail "list (exit $RC)"
        fi

        # Create character with bundled face + preset voice
        echo "  Testing create-character (bundled face + preset voice)..."
        set +e
        OUTPUT=$($PY create-character \
            --name "Test Bot $(date +%s)" \
            --voice luna \
            --personality "You are a test bot. Say hello and nothing else." 2>/dev/null)
        RC=$?
        set -e
        if [[ $RC -eq 0 ]]; then
            AVATAR_ID=$(echo "$OUTPUT" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])" 2>/dev/null || true)
            if [[ -n "$AVATAR_ID" ]]; then
                pass "create-character → $AVATAR_ID"
                echo ""
                echo "  Created test character: $AVATAR_ID"
                echo "  To test join, run:"
                echo "    $PY join --meeting-url '<YOUR_MEET_URL>' --avatar-id $AVATAR_ID"
                echo ""
                echo "  To clean up, delete via Runway dashboard."
            else
                fail "create-character — no ID in output"
            fi
        else
            fail "create-character (exit $RC)"
        fi
    fi
else
    echo ""
    yellow "Live API tests skipped. Run with --live to test against real API."
fi

# ------------------------------------------------------------------
# Summary
# ------------------------------------------------------------------
echo ""
echo "=============================="
TOTAL=$((PASS + FAIL))
echo " Results: $PASS/$TOTAL passed"
if [[ $FAIL -gt 0 ]]; then
    red " $FAIL test(s) failed"
    exit 1
else
    green " All tests passed!"
    exit 0
fi
