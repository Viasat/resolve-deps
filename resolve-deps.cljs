#!/usr/bin/env nbb

;; Copyright (c) 2024, Viasat, Inc
;; Licensed under EPL 2.0

(ns resolve-deps
  (:require [promesa.core :as P]
            [clojure.string :as S]
            [clojure.walk :refer [keywordize-keys]]
            [cljs.pprint :refer [pprint]]
            [viasat.deps :refer [resolve-dep-order]]
            ["neodoc" :as neodoc]
            ["path" :as path]
            ["fs/promises" :as fs]))

(def usage "Usage:
    resolve-deps [options] <dep-str>...

Options:
     -p PATH, --path=PATH    Colon separated paths to dep dirs or files (JSON)
                             [default: ./] [env: RESOLVE_DEPS_PATH]
     --format=FORMAT         Output format (nodes, paths, json)
                             [default: nodes] [env: RESOLVE_DEPS_FORMAT]")

(defn parse-args [argv]
  (-> (neodoc/run usage (clj->js {:smartOptions true
                                  :optionsFirst true
                                  :argv argv}))
      js->clj))

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

(defn read-stream [stream]
  (P/create (fn [resolve reject]
              (P/let [chunks (atom [])]
                (doto stream
                  (.on "data" #(swap! chunks conj %))
                  (.on "error" reject)
                  (.on "end" #(resolve (apply str @chunks)))
                  (.resume))))))

(defn load-json
  [file]
  (P/->> (if (= "-" file)
           (read-stream js/process.stdin)
           (fs/readFile file "utf8"))
         js/JSON.parse
         js->clj))

(defn parse-dep-str
  "Parse a dependency string of whitespace separated dep strings into
  a sequence of deps. Alternation deps are specified as two or more
  dependencies delimited by a '|' and are returned as a sequences of
  the alternatives. Order only (weak) deps are prefixed with a '+' and
  are returned as a map {:after DEP}."
  [raw-str]
  (let [s (S/replace raw-str #"#[^\n]*" " ")]
    (if (empty? s)
      []
      (for [dep (S/split s #"[, \n]+")]
        (cond
          (re-seq #"[|]" dep) {:or (S/split dep #"[|]")}
          (re-seq #"^\+" dep) {:after (S/replace dep #"^\+" "")}
          :else               dep)))))

(defn load-deps-files
  "Takes a paths sequence and finds all files matching
  path/*/deps-file. Returns a map of dep nodes to node data. Each node
  data map contains:
    - node: name of the node
    - path: path to dep directory
    - dep-str: raw dependency string from path/*/deps-file (if it exists)
    - deps: parsed dependency string"
  [paths & [deps-file]]
  (P/let [deps-file (or deps-file "deps")
          deps (P/->>
                 (for [path paths]
                   (P/let [pfile? (or (= "-" path)
                                      (P/-> (fs/stat path) .isFile))]
                     (if pfile?
                       (P/->> (load-json path)
                                (map (fn [[k vs]]
                                       (if (and (not (nil? vs))
                                                (not (sequential? vs)))
                                         (throw (ex-info
                                                  (str "Dep value for " k
                                                       " must be an array") {})))
                                       {:node k
                                        :path path
                                        :deps (for [v vs]
                                                (if (sequential? v)
                                                  {:or v}
                                                  (keywordize-keys v)))})))
                       (P/->> (fs/readdir path #js {:withFileTypes true})
                              (filter #(.isDirectory %))
                              (map #(P/let [node (.-name %)
                                            npath (path/join path node)
                                            df (path/join npath deps-file)
                                            ds (P/catch (fs/readFile df "utf8")
                                                 (fn [] ""))]
                                      {:node    node
                                       :path    npath
                                       :dep-str ds
                                       :deps    (parse-dep-str ds)}))
                              P/all))))
                 P/all
                 (mapcat identity))
          errs (for [[n cnt] (frequencies (map :node deps))
                     :when (> cnt 1)]
                 (str "Node " n " appears in multiple places: "
                      (S/join
                        ", " (map :path (filter #(= n (:node %)) deps)))))]
    (when (seq errs)
      (throw (ex-info (S/join "; " errs) {})))
    (zipmap (map :node deps) deps)))

(defn print-deps
  "Print nodes using data from deps (in format)"
  [format nodes deps]
  (condp = format
    "nodes" (println (S/join " " nodes))
    "paths" (println (S/join "\n" (for [n nodes]
                                    (str n "=" (get-in deps [n :path])))))
    "json" (println (js/JSON.stringify
                      (clj->js (for [n nodes]
                                 (get deps n {:node n :deps []})))))))

(defn main
  "Load node directory deps files found under path (--path) and then
  print the best resolution and order that fulfills the <dep-str>
  strings. Output format is selected by --format."
  [argv]
  (P/catch
    (P/let [opts (parse-args argv)
            start-dep-str (S/join "," (get opts "<dep-str>"))
            deps (load-deps-files (S/split (get opts "--path") #":"))
            dep-graph (assoc (zipmap (keys deps) (map :deps (vals deps)))
                             :START (parse-dep-str start-dep-str))
            res-deps (->> (resolve-dep-order dep-graph :START)
                          (filter #(not= :START %)))]
      (print-deps (get opts "--format") res-deps deps))
    (fn [err]
      (binding [*print-fn* *print-err-fn*]
        (println "Error:" (or (.-message err) err)))
      (js/process.exit 1))))

(main *command-line-args*)
