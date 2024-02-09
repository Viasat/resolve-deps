#!/usr/bin/env bash

die() { echo "${*}"; exit 1; }
RESOLVE_DEPS="${1}"; shift || die "Usage: ${0} resolve-deps-path"
fails=0

test_rd() {
  local res= args="${1}" expected=; shift
  res=$(${RESOLVE_DEPS} tests/resolve-deps/modes "${args}" 2>/dev/null)
  for expected in "${@}"; do
    if [ "${res}" = "${expected}" ]; then
        echo "PASS: ${args} => ${res}"
        return
    fi
  done
  echo "FAIL: ${args} => ${res} (expected: ${expected})"
  fails=$(( fails + 1 ))
}

test_rd "a"     "a"             # no deps file
test_rd "z"     "z"             # no mode directory at all
test_rd "b"     "a b"           # simple one level dep
test_rd "c"     "a b c"         # two level deps
test_rd "e"     "a b d e"       # pick first alternate
test_rd "e c"   "a b c e"       # force other alternate
test_rd "e c a" "a b c e"       # eliminate redundant start and deps
test_rd "e c z" "a b c z e" "a b c e z" "a z b c e" "a b z c e"  # include no deps files item

test_rd "cyc1"  ""              # should error and return empty

[ "${fails}" -eq 0 ]
