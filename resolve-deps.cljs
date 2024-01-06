#!/usr/bin/env nbb

(ns resolve-deps
  (:require [promesa.core :as P]
            [clojure.string :as S]
            [viasat.deps :refer [resolve-dep-order]]
            ["path" :as path]
            ["fs/promises" :as fs]))

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

(defn parse-dep-str
  "Parse a dependency string of whitespace separated dep strings into
  a sequence of deps. Alternation deps are specified as two or more
  dependencies delimited by a '|' and are returned as a sequences of
  the alternatives."
  [s]
  (if (empty? s)
    []
    (for [dep (S/split s #"[, \n]+")]
      (if (re-seq #"[|]" dep)
        (S/split dep #"[|]")
        dep))))

(defn load-dep-file-graph
  "Takes path (a directory path) and dep-file-name (defaults to
  'deps') and finds all files matching path/*/dep-file-name. Returns
  a map of directory names to parsed dependencies from the dep file in
  that directory."
  [path & [dep-file-name]]
  (P/let [dep-file-name (or dep-file-name "deps")
          path-dirs (P/->> (fs/readdir path #js {:withFileTypes true})
                           (filter #(.isDirectory %))
                           (map #(.-name %)))
          dep-list (P/all (for [dname path-dirs
                                :let [dpath (path/join path dname "deps")]]
                            (P/catch (P/->> (fs/readFile dpath "utf8")
                                            parse-dep-str
                                            (vector dname))
                              #(vector dname nil))))]
    (into {} dep-list)))

;; First argument is path to deps directory and the rest are dep
;; strings. Load all dep definitions under path and then return the
;; best resolution and order that fulfills the dep strings.
(P/let [[path & start-dep-strs] *command-line-args*
        start-dep-str (S/join "," start-dep-strs)
        file-graph (load-dep-file-graph path)
        dep-graph (assoc file-graph :START (parse-dep-str start-dep-str))
        deps (resolve-dep-order dep-graph :START)]
    (println (S/join " " deps)))

