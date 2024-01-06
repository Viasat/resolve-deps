#!/usr/bin/env bash

test_rd() {
  local args="${1}" expected_res="${2}" res=
  res=$(./resolve-deps tests/resolve-deps/modes "${args}")
  if [ "${res}" = "${expected_res}" ]; then
      echo "PASS: ${args} => ${res}"
  else
      echo "FAIL: ${args} => ${res} (expected: ${expected_res})"
  fi
}

test_rd "a"     "a"          # no deps file
test_rd "z"     "z"          # no mode directory at all
test_rd "b"     "a b"        # simple one level dep
test_rd "e"     "a b d e"    # pick first alternate
test_rd "e c"   "a b c e"    # force other alternate
test_rd "e c a" "a b c e"    # eliminate redundant start and deps
test_rd "e c z" "a b c z e"  # include no deps files item
