#!/usr/bin/env bash

die() { echo "${*}"; exit 1; }
RESOLVE_DEPS="${1}"; shift || die "Usage: ${0} resolve-deps-path"

test_rd() {
  local args="${1}" expected1="${2}" expected2="${3:-${expected1}}" res=
  res=$(${RESOLVE_DEPS} tests/resolve-deps/modes "${args}" 2>/dev/null)
  if [ "${res}" = "${expected1}" -o "${res}" = "${expected2}"  ]; then
      echo "PASS: ${args} => ${res}"
  else
      echo "FAIL: ${args} => ${res} (expected: ${expected1})"
  fi
}

test_rd "a"     "a"          # no deps file
test_rd "z"     "z"          # no mode directory at all
test_rd "b"     "a b"        # simple one level dep
test_rd "e"     "a b d e"    # pick first alternate
test_rd "e c"   "a b c e"    # force other alternate
test_rd "e c a" "a b c e"    # eliminate redundant start and deps
test_rd "e c z" "a b c z e" "a b c e z"  # include no deps files item
test_rd "cyc1"  ""           # should error and return empty
