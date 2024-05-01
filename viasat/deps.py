#!/usr/bin/env python3

# Copyright (c) 2024, Viasat, Inc
# Licensed under EPL 2.0

# Ported from src/viasat/deps.cljc

############################################################
## Kahn topology sort algorithm
## Based on: https://gist.github.com/alandipert/1263783

def no_incoming(g):
    """Find nodes in the graph with no incoming edges."""
    all_nodes = set(g.keys())
    connected_nodes = set().union(*g.values())
    return all_nodes - connected_nodes

def normalize(g):
    """Normalize the graph by ensuring all nodes appear as keys."""
    all_nodes = set().union(*map(set, g.values()), g.keys())
    return {node: g.get(node, set()) for node in all_nodes}

def kahn_sort(g):
    """Return a topological sort for directed graph g using Kahn's
    algorithm, where g is a map of nodes to sets of nodes. If g is
    cyclic, returns nil."""
    g = normalize(g)
    l = []
    s = no_incoming(g)

    while s:
        n = s.pop()
        l.append(n)
        for m in list(g[n]):  # List is used to avoid modifying the set during iteration
            g[n].remove(m)
            if not any(m in g[k] for k in g):
                s.add(m)

    if any(g.values()):
        return None  # Graph has at least one cycle
    else:
        return l

############################################################
## Graph dep resolution using modified set cover algorithm

def alt_set_covers(graph, result=None, visited=None, pending=None):
    """Return all set covers of a graph containing alternation nodes.
    Alternation nodes are expressed as a list of alternate nodes. Each
    alternative dependency node in the graph effectively duplicates
    the paths up to that point and continues the paths for each
    alternative."""
    if result is None:
        result = []
    if visited is None:
        visited = set()
    if pending is None:
        pending = []

    if not pending:
        return [result]

    node, *pending_rest = pending
    if isinstance(node, list):
        covers = []
        for alt_node in node:
            if alt_node in visited:
                new_result = result
                new_visited = visited
            else:
                new_result = result + [alt_node]
                new_visited = visited | {alt_node}
            new_pending = [alt_node] + pending_rest
            covers.extend(alt_set_covers(graph, new_result, new_visited, new_pending))
        return covers
    else:
        new_result = result + [node] if node not in visited else result
        new_visited = visited | {node}
        children = [n for n in graph.get(node, []) if isinstance(n, list) or n not in new_visited]
        return alt_set_covers(graph, new_result, new_visited, pending_rest + children)

def min_alt_set_cover(graph, start):
    """Call alt_set_covers and then return shortest path (if a tie
    then return the first)."""
    if isinstance(start, list):
        graph = {**graph, ':-BEGIN-': start}
    else:
        graph = {**graph, ':-BEGIN-': [start]}

    covers = alt_set_covers(graph, pending=[':-BEGIN-'])
    shortest_cover = min(covers, key=len)
    return shortest_cover[1:]  # Exclude ':-BEGIN-' node

###

def list_add(obj, key, val):
    if not obj.__contains__(key): obj[key] = []
    obj[key].append(val)

def resolve_dep_order(graph, start):
    """Takes a dependency graph and a starting node, find shortest
    dependency resolution, and returns it in the order that the deps
    need to be applied (reversed topological sort order).
    The dependency graph is a map of node keys to a sequence of
    dependencies. Each dependency can be one of the following:
    - SCALAR:              the key requires this node
    - SEQUENCE:            the key requires at least one node from the SEQUENCE
    - {"or": SEQUENCE}:    same as plain SEQUENCE
    - {"after": SEQUENCE}: key is after nodes in the SEQUENCE (if required)"""
    strong_graph = {}
    order_graph = {}
    for k, v in [(k, v) for k, vs in graph.items() for v in vs]:
        if isinstance(v, dict) and v.__contains__("after"):
            list_add(order_graph, k, v["after"])
        else:
            rv = v.get("or", v.get("after")) if isinstance(v, dict) else v
            list_add(strong_graph, k, rv)
            list_add(order_graph, k, rv)

    # Find the shortest set cover of dependencies
    min_cover = set(min_alt_set_cover(strong_graph, start))

    # Construct a new graph where each node points to its dependencies
    dep_graph = {dep: set() for dep in min_cover}  # Nodes with no dependencies
    for k, vs in order_graph.items():
        if k in min_cover:
            # Flatten lists and keep only those in min_cover
            dep_graph[k] = set(v for v in vs for v in (v if isinstance(v, list) else [v]) if v in min_cover)

    # Perform topological sort on the new graph
    sorted_deps = kahn_sort(dep_graph)

    # Check for cycles
    if sorted_deps is None:
        raise ValueError("Graph contains a cycle")

    # Return dependencies in reverse topological order
    return sorted_deps[::-1]

def run_examples():
    # Test 0
    graph0 = {
        'a': ['b', 'c'],
        'b': ['c', 'd'],
        'c': ['e'],
        'e': ['f']
    }
    print("results0:", min_alt_set_cover(graph0, 'a'))
    print("results0.1:", resolve_dep_order(graph0, 'a'))

    # Test 1
    graph1 = {
        'A': ['B', ['C', 'D']],
        'B': ['E', 'F'],
        'C': ['G'],
        'D': ['G', 'H'],
        'E': [],
        'F': [],
        'G': [],
        'H': []
    }
    print("result1:", min_alt_set_cover(graph1, 'A'))
    print("result1.1:", resolve_dep_order(graph1, 'A'))

    # Test 2
    graph2 = {
        'A': ['B', 'C'],
        'B': [['C', 'D']],
        'C': ['E'],
        'D': ['E']
    }
    print("result2:", min_alt_set_cover(graph2, 'A'))
    print("result2.1:", resolve_dep_order(graph2, 'A'))

    # Test 3
    graph3 = {
        'accel': ['base', ['mach3', 'ab']],
        'mach3': ['base'],
        'ab': ['base']
    }
    print("result3.1:", min_alt_set_cover(graph3, ['accel', 'ab']))
    print("result3.1.1:", resolve_dep_order(graph3, ['accel', 'ab']))
    print("result3.2:", min_alt_set_cover(graph3, ['accel', 'mach3']))
    print("result3.2.1:", resolve_dep_order(graph3, ['accel', 'mach3']))

    # Test 4
    graph4 = {
        'A': ['B', 'C'],
        'B': [['D', 'C']]
    }
    print("result4-all:", alt_set_covers(graph4, pending=['A']))
    print("result4-min:", min_alt_set_cover(graph4, 'A'))
    print("result4-min.1:", resolve_dep_order(graph4, 'A'))

#run_examples()
