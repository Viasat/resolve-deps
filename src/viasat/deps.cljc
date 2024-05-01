#!/usr/bin/env nbb

;; Copyright (c) 2024, Viasat, Inc
;; Licensed under EPL 2.0

(ns viasat.deps
  (:require [clojure.set :refer [union intersection]]))

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;; Kahn topology sort algorithm
;; Based on: https://gist.github.com/alandipert/1263783

(defn no-incoming [g]
  (apply disj (set (keys g)) (apply union (vals g))))

(defn normalize [g]
  (reduce #(if (contains? % %2) % (assoc % %2 #{}))
          (reduce-kv #(assoc %1 %2 (set %3)) g g)
          (apply union (map set (vals g)))))

(defn kahn-sort
  "Return a topological sort for directed graph g using Kahn's
   algorithm, where g is a map of nodes to sets of nodes. If g is
   cyclic, returns nil."
  [g]
  (loop [g (normalize g) l [] s (no-incoming g)]
    (if (empty? s)
      (when (every? empty? (vals g)) l)
      (let [[n s'] (let [n (first s)] [n (disj s n)]) ;; pop
            m (g n)
            g' (reduce #(update % n disj %2) g m)]
        (recur g' (conj l n) (union s' (intersection (no-incoming g') m)))))))


;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;; Graph dep resolution using modified set cover algorithm

(defn alt-set-covers
  "Return all the set covers of a graph containing alternation nodes.
  Alternation nodes are expressed as a collection (coll?) of alternate
  nodes. Each alternative dependency node in the graph effectively
  duplicates the paths up to that point and continues the paths for
  each alternative."
  ([graph start] (alt-set-covers graph [] #{} [start]))
  ([graph result visited pending]
   (loop [result result  visited visited  pending pending]
     (let [[node & pending] pending]
       (if (sequential? node)
         (mapcat
           (fn [node]
             (let [[result visited] (if (contains? visited node)
                                      [result visited]
                                      [(conj result node) (conj visited node)])
                   pending (into (vec pending) [node])]
               (alt-set-covers graph result visited pending)))
           node)
         (let [[result visited] (if (contains? visited node)
                                  [result visited]
                                  [(conj result node) (conj visited node)])
               children (filter #(not (contains? visited %)) (graph node))
               pending (into (vec pending) (vec children))]
           (if (empty? pending)
             [result]
             (recur result visited pending))))))))

(defn min-alt-set-cover
  "Call alt-set-covers and then return shortest path (if a tie then
  return the first)."
  [graph start]
  (let [graph (if (coll? start)
                (merge graph {:-BEGIN- (set start)})
                (merge graph {:-BEGIN- #{start}}))
        covers (alt-set-covers graph :-BEGIN-)
        counts (group-by count covers)
        smallest (apply min (keys counts))]
    (-> (get counts smallest) first next)))

;;;

(defn resolve-dep-order
  "Takes a dependency graph and a starting node, find shortest
  dependency resolution, and returns it in the order that the deps
  need to be applied (reversed topological sort order).
  The dependency graph is a map of node keys to a sequence of
  dependencies. Each dependency can be one of the following:
  - SCALAR:            the key requires this node
  - SEQUENCE:          the key requires at least one node from the SEQUENCE
  - {:or SEQUENCE}:    same as plain SEQUENCE
  - {:after SEQUENCE}: key is afer nodes in the SEQUENCE (if required)"
  [graph start]
  (let [regroup #(reduce (fn [g [k v]] (update g k (fnil conj []) v)) {} %)
        strong-graph (regroup (for [[k v] (for [[k vs] graph v vs] [k v])
                                    :when (or (not (map? v)) (contains? v :or))]
                                [k (if (map? v) (:or v) v)]))
        order-graph (regroup
                      (for [[k v] (for [[k vs] graph v vs] [k v])]
                        [k (if (map? v) (get v :or (get v :after)) v)]))
        min-cover (set (min-alt-set-cover strong-graph start))
        dep-graph (into (zipmap min-cover (repeat #{})) ;; nodes with no deps
                        (for [[k vs] order-graph
                              :when (min-cover k)]
                          [k (set (keep min-cover (flatten vs)))]))
        sorted (kahn-sort dep-graph)]
    (when (empty? sorted) (throw (ex-info "Graph contains a cycle" {})))
    (reverse sorted)))


(defn run-examples []
  (let [graph0 {:a [:b :c]
                :b [:c :d]
                :c [:e]
                :e [:f]}]
    (prn :results0 (min-alt-set-cover graph0 :a))
    (prn :results0.1 (resolve-dep-order graph0 :a)))

  (let [graph1 {:A [:B [:C :D]]  ; A requires B AND (C OR D)
                :B [:E :F]       ; B requires E AND F
                :C [:G]          ; C requires G
                :D [:G :H]       ; D requires G AND H
                :E []            ; E has no deps
                :F []            ; F has no deps
                :G []            ; G has no deps
                :H []}]          ; H has no deps
    (prn :result1 (min-alt-set-cover graph1 :A))
    (prn :result1.1 (resolve-dep-order graph1 :A)))

  (let [graph2 {:A     [:B :C]
                :B     [[:C :D]]
                :C     [:E]
                :D     [:E]}]
    (prn :result2 (min-alt-set-cover graph2 :A))
    (prn :result2.1 (resolve-dep-order graph2 :A)))

  (let [graph3 {:accel [:base [:mach3 :ab]]
                :mach3 [:base]
                :ab    [:base]}]
    (prn :result3.1 (min-alt-set-cover graph3 [:accel :ab]))
    (prn :result3.1.1 (resolve-dep-order graph3 [:accel :ab]))
    (prn :result3.2 (min-alt-set-cover graph3 [:accel :mach3]))
    (prn :result3.2.1 (resolve-dep-order graph3 [:accel :mach3])))

  (let [graph4 {:A     [:B :C]
                :B     [[:D :C]]}]
    (prn :result4-all (alt-set-covers graph4 :A))
    (prn :result4-min (min-alt-set-cover graph4 :A))
    (prn :result4-min.1 (resolve-dep-order graph4 :A)))
)

#_(run-examples)
