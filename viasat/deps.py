#!/usr/bin/env python3

# Ported from src/viasat/deps.cljc

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
    """
    Perform a topological sort on a directed graph using Kahn's algorithm.
    If the graph is cyclic, returns None.
    """
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

def alt_set_covers(graph, result=None, visited=None, pending=None):
    """Find all set covers of a graph containing alternation nodes."""
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
    """Find the minimum alternative set cover."""
    if isinstance(start, list):
        graph = {**graph, ':-BEGIN-': start}
    else:
        graph = {**graph, ':-BEGIN-': [start]}

    covers = alt_set_covers(graph, pending=[':-BEGIN-'])
    shortest_cover = min(covers, key=len)
    return shortest_cover[1:]  # Exclude ':-BEGIN-' node

def resolve_dep_order(graph, start):
    """Finds the shortest dependency resolution order."""
    # Find the shortest set cover of dependencies
    min_cover = set(min_alt_set_cover(graph, start))

    # Construct a new graph where each node points to its dependencies
    dep_graph = {dep: set() for dep in min_cover}  # Nodes with no dependencies
    for k, vs in graph.items():
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
