#!/usr/bin/env bash

die() { echo "${*}"; exit 1; }
RESOLVE_DEPS="${1}"; shift || die "Usage: ${0} resolve-deps-path"
PATH_MODE="${1:-dir}"; shift
passes=0 fails=0

test_rd() {
  local res= args="${1}" expected=; shift
  res=$(${RESOLVE_DEPS} "${args}" 2>&1)
  for expected in "${@}"; do
    if [[ "${res}" =~ ${expected} ]]; then
        echo "PASS: ${args} => ${res}"
        passes=$(( passes + 1 ))
        return
    fi
  done
  echo "FAIL: ${args} => ${res} (expected: ${expected})"
  fails=$(( fails + 1 ))
}

case "${PATH_MODE}" in
  dir)  ext="" ;;
  json) ext=".json" ;;
  *) die "Unknown PATH_MODE ${PATH_MODE}" ;;
esac

export RESOLVE_DEPS_PATH=tests/basic${ext}
test_rd "a"     "^a$"               # no deps file
test_rd "z"     "^z$"               # no mode directory at all
test_rd "b"     "^a b$"             # simple one level dep
test_rd "c"     "^a b c$"           # two level deps
test_rd "e"     "^a b d e$"         # pick first alternate
test_rd "e c"   "^a b c e$"         # force other alternate
test_rd "e c a" "^a b c e$"         # eliminate redundant start and deps
test_rd "e c z" "^a b c z e$" "^a b c e z$" "^a z b c e$" "^a b z c e$"  # include no deps files item

export RESOLVE_DEPS_PATH=tests/order${ext}
test_rd "o1"    "^o1$"              # order/weak dep on o3 should be ignored
test_rd "o1 o2" "^o1 o2$" "^o2 o1$" # no ordering
test_rd "o2 o1" "^o1 o2$" "^o2 o1$" # no ordering
test_rd "o4"    "^o4$"              # order/weak dep on o5 should be ignored
test_rd "o3"    "^o5 o4 o3$"        # mix of ordering types
test_rd "o2 o3" "^o5 o4 o3 o2$"     # mix of ordering types
test_rd "o1 o3" "^o5 o4 o3 o1$"     # mix of ordering types

export RESOLVE_DEPS_PATH=tests/cycle${ext}
test_rd "cyc1"  "^Error:.*cycle"    # should error and return empty

export RESOLVE_DEPS_PATH=tests/basic${ext}:tests/dupes${ext}
test_rd "a"  "^Error:.*multiple"    # should error and return empty
test_rd "c"  "^Error:.*multiple"    # should error and return empty

echo "FINAL RESULT: ${passes}/$(( passes + fails )) passed ($fails failures)"
[ "${fails}" -eq 0 ]
