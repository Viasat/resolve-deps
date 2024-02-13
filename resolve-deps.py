#!/usr/bin/env python3

# Ported from resolve-deps.cljs

from viasat.deps import resolve_dep_order
import os
import re
import sys

def parse_one_dep(dep):
    if '|' in dep:      return dep.split('|')
    elif dep[0] == '+': return {"after": dep[1:]}
    else:               return dep

def parse_dep_str(raw_str):
    """Parse a dependency string of whitespace separated dep strings into
    a sequence of deps. Alternation deps are specified as two or more
    dependencies delimited by a '|' and are returned as a sequences of
    the alternatives. Order only (weak) deps are prefixed with a '+' and
    are returned as a map {:after DEP}."""
    s = re.sub(r'#[^\n]*', " ", raw_str)
    if not s:
        return []

    return [parse_one_dep(dep) for dep in re.split(r'[, \n]+', s) if dep]


def load_dep_file_graph(path, dep_file_name="deps"):
    """Takes path (a directory path) and dep-file-name (defaults to
    'deps') and finds all files matching path/*/dep-file-name. Returns
    a map of directory names to parsed dependencies from the dep file
    in that directory."""
    dep_graph = {}
    for dname in os.listdir(path):
        dpath = os.path.join(path, dname, dep_file_name)
        if os.path.isdir(os.path.join(path, dname)) and os.path.isfile(dpath):
            with open(dpath, 'r') as file:
                dep_graph[dname] = parse_dep_str(file.read())
        else:
            dep_graph[dname] = []
    return dep_graph

def main(path, *start_dep_strs):
    start_dep_str = ",".join(start_dep_strs)
    file_graph = load_dep_file_graph(path)
    dep_graph = file_graph
    dep_graph[':START'] = parse_dep_str(start_dep_str)
    deps = [d for d in resolve_dep_order(dep_graph, ':START') if d != ':START']
    print(" ".join(deps))

main(sys.argv[1], *sys.argv[2:])
