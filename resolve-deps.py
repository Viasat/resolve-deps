#!/usr/bin/env python3

# Copyright (c) 2024, Viasat, Inc
# Licensed under EPL 2.0

# Ported from resolve-deps.cljs

from viasat.deps import resolve_dep_order
from collections import Counter
from argparse import ArgumentParser
import json
import os
import re
import sys

def parse_args(argv):
    parser = ArgumentParser(description='resolve deps from dep dirs')
    parser.add_argument('dep_str', nargs='+',
                        help='one or more dep strings')
    parser.add_argument('-p', '--path', help='Colon separated paths to dep dir or file (JSON)',
                        default=os.environ.get('RESOLVE_DEPS_PATH', './'))
    parser.add_argument('--format', help='Output format (nodes, paths, json)',
                        default=os.environ.get('RESOLVE_DEPS_FORMAT', 'nodes'))
    return parser.parse_args(argv)

#########################################

def load_json(file):
    data = ""
    if file == "-":
        data = sys.stdin.read()
    else:
        data = open(file).read()
    return json.loads(data)

def parse_one_dep(dep):
    if '|' in dep:      return {'or': dep.split('|')}
    elif dep[0] == '+': return {'after': dep[1:]}
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


def load_deps_files(paths, deps_file="deps"):
    """Takes a paths list and finds all files matching
    path/*/deps-file. Returns a map of dep nodes to node data. Each
    node data map contains:
      - node: name of the node
      - path: path to dep directory
      - dep-str: raw dependency string from path/*/deps-file (if it exists)
      - deps: parsed dependency string"""
    deps = []
    for path in paths:
        if path == "-" or os.path.isfile(path):
            for k, vs in load_json(path).items():
                vs = [] if vs == None else vs
                if not isinstance(vs, list):
                    raise Exception("Dep value for " + k + " must be an array")
                deps.append({'node': k,
                             'path': path,
                             "deps": [{"or": v} if isinstance(v, list) else v
                                      for v in vs]})
        else:
            for node in os.listdir(path):
                npath = os.path.join(path, node)
                if not os.path.isdir(npath): continue
                df = os.path.join(npath, deps_file)
                dep_str = ""
                if os.path.isfile(df):
                    with open(df, 'r') as file:
                        dep_str = file.read()
                deps.append({'node':    node,
                             'path':    npath,
                             'dep-str': dep_str,
                             'deps':    parse_dep_str(dep_str)})
    counts = Counter(dep['node'] for dep in deps)
    errs = []
    for node, count in counts.items():
        if count <= 1: continue
        dupes = [dep['path'] for dep in deps if dep['node'] == node]
        errs.append(f"Node {node} appears in multiple places: "
                    + ", ".join(dupes))
    if errs:
        raise Exception("; ".join(errs))
    return {dep['node']: dep for dep in deps}

def print_deps(format, nodes, deps):
    """Print nodes using data from deps (in format)"""
    if format == "nodes":
        print(" ".join(nodes))
    elif format == "paths":
        print("\n".join([f"{n}={deps[n]['path'] if n in deps else ''}"
                         for n in nodes]))
    elif format == "json":
        print(json.dumps([deps[n] if n in deps else {'node': n, 'deps': []}
                          for n in nodes]))

def main(argv):
    """Load node directory deps files found under path (--path) and
    then print the best resolution and order that fulfills the
    <dep_str> strings. Output format is selected by --format."""
    try:
        opts = parse_args(argv)
        start_dep_str = ",".join(opts.dep_str)
        deps = load_deps_files(opts.path.split(":"))
        dep_graph = {dep['node']: dep['deps'] for dep in deps.values()}
        dep_graph[':START'] = parse_dep_str(start_dep_str)
        res_deps = [d for d in resolve_dep_order(dep_graph, ':START')
                    if d != ':START']
        print_deps(opts.format, res_deps, deps)
    except Exception as e:
        print("Error:", e, file=sys.stderr)
        sys.exit(1)

main(sys.argv[1:])
