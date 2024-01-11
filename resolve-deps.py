#!/usr/bin/env python3

# Ported from resolve-deps.cljs

from viasat.deps import resolve_dep_order
import os
import re
import sys

def parse_dep_str(s):
    """Parse a dependency string into a sequence of dependencies."""
    if not s:
        return []

    return [dep.split('|') if '|' in dep else dep
            for dep in re.split(r'[, \n]+', s) if dep]


def load_dep_file_graph(path, dep_file_name="deps"):
    """Load dependency files from a directory and return a dependency graph."""
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
