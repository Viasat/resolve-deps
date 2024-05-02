# resolve-deps

Dependency resolver with support for alternate dependencies (OR) and
weak dependencies (order only).

Equivalent implmentations of resolve-deps are provided in both
ClojureScript and Python. The resolution algorithm is very
inefficient when resolving alternate resolution paths.

## Guide / Examples

In the following examples, you can use `./resolve-deps.py`
interchangeably with `./resolve-deps`.

### Example 1 - Simple Dependency

Let's say that we have two tasks "a" and "b". Task "a" has to be
completed before "b" therefore "b" has a dependency on "a". We
can represent this in JSON like this:

```json example1.json:
{
    "b": ["a"]
}
```

We can now use resolve-deps to answer the question "What tasks (and in
what order) do we need to complete in order to complete "b":

```
$ ./resolve-deps --path=tests/example1.json b
a b
```

This shows that we need to resolve "a" and then "b".

If we ask the same question of "a" then only "a" will be returned
because it has no dependencies:

```
$ ./resolve-deps --path=tests/example1.json a
a
```

### Example 2 - Multiple Dependencies (AND)

Let's add new task "c" that requires both "a" and "b":

```json example2.json:
{
    "b": ["a"],
    "c": ["a", "b"]
}
```

Now we can find the resolution for "c":

```
$ ./resolve-deps --path=tests/example2.json c
a b c
```

The resolutions for "a" and "b" are unchanged.

### Example 3 - Alternate Dependencies (OR)

Let's add task "d" that requires "a" and add task "e" that requires
"a" and also requires either "d" or "c" (or both "d" and "c"):

```json example3.json:
{
    "b": ["a"],
    "c": ["a", "b"],
    "d": ["a"],
    "e": ["a", {"or": ["d", "c"]}]
}
```

When there are alternate depedencies, this means there may be multiple
resolutions. resolve-deps will return the shortest valid resolution
(shortest by number of dep nodes):

```
$ ./resolve-deps --path=tests/example3.json e
a d e
```

If we specify that "c" must also be part of the resolution, then
resolve-deps will find the shortest alternate path/resolution that
includes "d":

```
$ ./resolve-deps --path=tests/example3.json e c
a b c e
```

Since alternates represent inclusive "or" dependencies, if we also
include "d", then resolve-deps will return the full set of
dependencies:

```
$ ./resolve-deps --path=tests/example3.json e c d
a b c d e
```

Since "d" does not have a dependency relationship with either "b" or
"c", this means that there are two other valid resolution orders
possible for the above command:

```
a b d c e
a d b c e
```

### Example 4 - Order (weak) Dependencies

We can extend example 3 in order to force "d" to resolve before "b"
by using an order (weak) dependency:

```json example4.json:
{
    "b": ["a", {"after": "d"}],
    "c": ["a", "b"],
    "d": ["a"],
    "e": ["a", {"or": ["d", "c"]}]
}
```

```
$ ./resolve-deps --path=tests/example4.json d b
a d b
```

Note that because the the relationship between "b" and "d" is an order
(weak) dependency, "b" will not force "d" to be included in the
result. However, if "d" is included due to some other dependency (or
explicitly by the user), then "d" will always appear before "b":

```
$ ./resolve-deps --path=tests/example4.json b
a b
$ ./resolve-deps --path=tests/example4.json b d
a d b
$ ./resolve-deps --path=tests/example4.json e
a d b
$ ./resolve-deps --path=tests/example4.json e c d
a d b c e
```

### Example 5 - Multiple Dependency Files

If we have related groups of dependencies (or they come from different
sources) then we can load them from multiple dependency files. For
example, we can split the example 4 file into two files:

```json example5a.json:
{
    "b": ["a", {"after": "d"}],
    "c": ["a", "b"]
}
```
```json example5b.json:
{
    "d": ["a"],
    "e": ["a", {"or": ["d", "c"]}]
}
```

Multiple dependency files can then be loaded by using a colon
separator:

```
$ ./resolve-deps --path=tests/example5a.json:tests/example5b.json e c d
a d b c e
```

### Example 6 - Dependency Directories

In addition to JSON dependency files, resolve-deps can also load
dependencies from deps files within a sub-directories of the search
paths.

Consider the following files and their content:

```
$ grep '.' tests/basic/*/deps
tests/basic/b/deps:a
tests/basic/c/deps:a b
tests/basic/d/deps:a b
tests/basic/e/deps:a d|c
tests/basic/f/deps:a b c|d
```

The dependencies defined by the `tests/basic` directory are equivalent
to the following JSON file:

```json tests/basic.json
{
    "a": null,
    "b": ["a"],
    "c": ["a", "b"],
    "d": ["a", "b"],
    "e": ["a", ["d", "c"]],
    "f": ["a", "b", ["c", "d"]]
}
```

We can use this directory structure to resolve dependencies for "f"
like this:

```
$ ./resolve-deps --path=tests/basic f
a b c f
```

In the above resolution, you might get "d" instead of "c" since they
are alternates and the resolutions are the same length.

### Example 7 - Reading from Standard Input (stdin)

If a component of the paths is equal to "-" then resolve-deps will
read JSON data from stdin:

```
$ echo '{"b":["a"]}' | ./resolve-deps --path=- b
a b
```

```
$ cat tests/basic.json | ./resolve-deps --path=- f
a b c f
```

### Example 8 - Cycle Detection

The dependency structure must be free of dependency loops (cycles) in
order for resolve-deps to come up with a dependency solution.
Dependency cycles are detected and will throw an error.

We can use JSON from stdin to show dependency loop detection:

```
$ echo '{"b":["a"],"a":["b"]}' | ./resolve-deps --path=- b
Error: Graph contains a cycle

$ echo '{"b":["a"],"c":["b"],"a":["c"]}' | ./resolve-deps --path=- c
Error: Graph contains a cycle
```

### Example 9 - Output Formats

The default output mode is the "nodes" format which prints resolved
ependency nodes names (space separated). All modes print the nodes in
resolution order.

The are two other output modes: "paths" and "json".

The "paths" output mode will show each dependency node on a separate
line with an `=` symbol and then the path to the directory (or path)
where the node is defined:

```
$ ./resolve-deps --path=tests/basic --format=paths f
a=tests/basic/a
b=tests/basic/b
c=tests/basic/c
f=tests/basic/f
```

The "json" output mode will print a JSON list of nodes where each node
is a map containing:
- `node`: the node name
- `path`: the path to the node directory or file
- `deps`  the dependencies of this node
- `dep-str`: the original dep string read from the `deps` file (dep
  directory mode only) .

```
$ ./resolve-deps --path=tests/basic --format=json f | jq '.'
[
  {
    "node": "a",
    "path": "tests/basic/a",
    "dep-str": "",
    "deps": []
  },
  {
    "node": "b",
    "path": "tests/basic/b",
    "dep-str": "a\n",
    "deps": [
      "a"
    ]
  },
  {
    "node": "c",
    "path": "tests/basic/c",
    "dep-str": "a b\n",
    "deps": [
      "a",
      "b"
    ]
  },
  {
    "node": "f",
    "path": "tests/basic/f",
    "dep-str": "a b c|d\n",
    "deps": [
      "a",
      "b",
      {
        "or": [
          "c",
          "d"
        ]
      }
    ]
  }
]
```


## Library Functions

The following shows how to use `viasat.deps` library functions. Unless
there are important differences, most of these example are shown in
Clojure. There are equivalent python functions with underscores in the
names instead of dashses.

Require/import the resolve-deps library, the pprint function,  and
define an example depdency graph:

```clojure Clojure
(require '[viasat.deps]
         '[clojure.pprint :refer [pprint]])

(def g {:a [:b :c]
        :b [:c {:or [:x :y]}]
        :c [:d]
        :d [{:after :e} :f]
        :e []
        :f []
        :x []
        :y [{:or [:z :e]}]
        :z []})
```

```python Python
import viasat.deps
from pprint import pprint

g = {
    "a": ["b", "c"],
    "b": ["c", {"or": ["x", "y"]}],
    "c": ["d"],
    "d": [{"after": "e"}, "f"],
    "e": [],
    "f": [],
    "x": [],
    "y": [{"or": ["z", "e"]}],
    "z": []
}
```

### resolve-dep-order: full dependency and order resolution

Do a full dependency resolution of graph `g` start from `:a`:

```clojure
user=> (viasat.deps/resolve-dep-order g :a)
(:f :d :x :c :b :a)
```

The starting point can also be specified as a sequence of starting
nodes:

```clojure
user=> (viasat.deps/resolve-dep-order g [:a :y])
(:f :z :d :y :c :b :a)
```

### alt-set-covers: all resolutions

The following examples use a simpler form of the dependency graph
where there are no weak nodes and alternates are specified as a simple
sequence (no maps). You can convert the full graph into the simpler
form using `full-to-alt-graph`. The second argument specifies whether to
keep the weak/order dependencies and convert them into full
dependencies (:weak) or to omit them entirely (:strong).

```clojure
user=> (def g1 (viasat.deps/full-to-alt-graph g :strong))
user=> (def g2 (viasat.deps/full-to-alt-graph g :weak))
```

Show the possible resolutions for `:a` for each normalized graph:

```clojure
user=> (viasat.deps/alt-set-covers g1 :a)
([:a :b :c :x :d :f] [:a :b :c :y :d :f :z] [:a :b :c :y :d :f :e])
user=> (viasat.deps/alt-set-covers g2 :a)
([:a :b :c :x :d :e :f] [:a :b :c :y :d :e :f :z] [:a :b :c :y :d :e :f])
```

Note: this function returns resolutions that are in arbitrary order.

### min-alt-set-cover: shortest resolution

The `min-alt-set-cover` is similar to `alt-set-covers` but it will
return only the shortest resolution (count of nodes in the
resolution). If there is a tie it will arbitrarily pick one of the
shortest ones:

```clojure
user=> (viasat.deps/min-alt-set-cover g1 :a)
(:a :b :c :x :d :f)
user=> (viasat.deps/min-alt-set-cover g2 :a)
(:a :b :c :x :d :e :f)
```

### kahn-sort: sort a dependency graph

The `kahn-sort` function takes a dependency graph and returns
a sequence in dependency order using Kahn's algorithm. It takes an
even simpler dependency graph with no alternates and the dependency
values are sets.

```clojure
user=> (viasat.deps/kahn-sort {:a [:b :c] :c [:d :e] :b [:f :g]})
[:a :b :f :g :c :d :e]
```

To sort a set-cover result, you need to convert full dep graph to the
simpler form and then prune it to only contain the set-cover nodes.
The `alt-to-kahn-graph` will do this conversion and pruning:

```clojure
user=> (def nodes (viasat.deps/min-alt-set-cover g1 :a))
user=> (def kahn-dep-graph (viasat.deps/alt-to-kahn-graph g1 nodes))
user=> kahn-dep-graph
{:a #{:b :c}, :b #{:c :x}, :c #{:d}, :x #{}, :d #{:f}, :f #{}}
```

This can now be sorted with `kahn-sort` to return a valid sorting of
the nodes (in latest to earliest order):

```clojure
user=> (viasat.deps/kahn-sort kahn-dep-graph)
[:a :b :c :x :d :f]
```

If you reverse the result you will have the same result as you would
get from `resolve-dep-order` (because it implements the steps
dewscribed above).


## Run Tests

The `./tests/runtests.sh` script will run tests against the
several different dependency directories in the `tests/` directory.

Run the tests using the ClojureScript version of resolve-deps:

```
$ ./tests/runtests.sh ./resolve-deps
PASS: a => a
PASS: z => z
...
FINAL RESULT: 18/18 passed (0 failures)
```

Run the tests using the Python version of resolve-deps and using JSON
depdendency files rather than dep dir definitions:

```
$ ./tests/runtests.sh ./resolve-deps.py json
PASS: a => a
PASS: z => z
...
FINAL RESULT: 18/18 passed (0 failures)
```

## Copyright & License

This software is copyright Viasat, Inc and Equinix, Inc and is
released under the terms of the Eclipse Public License version 2.0
(EPL.20). A copy of the license is located at in the LICENSE file at
the top of the repository.

