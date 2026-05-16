"""
Brauer configuration analysis for a musical score JSON.

Usage:
  python brauer_analysis.py Partituras/super_thema_regium.json --out results.json --plot out.png --crab

Generates:
 - M0 (vertices) and M1 (polygons per measure)
 - valence and multiplicity μ
 - algebraic dimensions
 - geometric coordinates and optional PNG plot
 - supports analysis of the retrograded sequence when --crab is given

Dependencies: numpy, networkx, matplotlib
"""
import argparse
import json
import math
from collections import defaultdict, Counter
from copy import deepcopy

import numpy as np

# Optional plotting
try:
    import matplotlib.pyplot as plt
except Exception:
    plt = None


# Duration mapping: figure -> k (2^t), e.g. quarter -> 4, eighth -> 8, 16th -> 16
DURATION_MAP = {
    "doubleWhole": 0.5,
    "whole": 1,
    "half": 2,
    "quarter": 4,
    "eighth": 8,
    "16th": 16,
    "32nd": 32,
    "64th": 64
}


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_alteration(a):
    # Input: numeric accidental (semitone offset) or None
    # Output: sigma operator integer: -1 for flat, 0 for natural, 1 for sharp
    if a is None:
        return 0
    try:
        ai = int(a)
    except Exception:
        # if string names like 'flat' or 'sharp'
        s = str(a).lower()
        if "flat" in s:
            return -1
        if "sharp" in s:
            return 1
        return 0
    if ai < 0:
        return -1
    if ai > 0:
        return 1
    return 0


def duration_to_k(fig, duration_val=None):
    # Prefer figure mapping; fallback to duration in quarter lengths
    if fig in DURATION_MAP:
        return DURATION_MAP[fig]
    if isinstance(duration_val, (int, float)) and duration_val > 0:
        # infer: quarterLength=1 -> map to 4
        # k = 4 / quarterLength * 4? Simpler: k = 4 / quarterLength * 4 ???
        # Use proportion: quarter -> 4 so k = 4 / quarterLength
        k = int(round(4 / duration_val))
        # snap to nearest power of two
        p = 1
        while p < k:
            p *= 2
        return p
    return 4


def vertex_id(note_name, alteration, k):
    # vertex unique identifier as tuple
    return (note_name, int(alteration), int(k))


def build_M0_M1(score_json):
    M0_set = set()
    M1 = []  # list of polygons (per measure) as list of vertex ids or chord-subblocks

    # create sequence index across whole piece
    global_position = 1

    for part in score_json:
        for measure in part.get("measures", []):
            poly = []
            for ev in measure.get("notes", []):
                # handle rest
                if ev.get("type") == "rest":
                    v = ("REST", 0, duration_to_k(ev.get("figure"), ev.get("duration")))
                    M0_set.add(v)
                    poly.append({"vertex": v, "pos": ev.get("position"), "type": "rest"})
                elif ev.get("type") == "chord":
                    # chord as sub-block: list of vertices
                    sub = []
                    for i, p in enumerate(ev.get("notes", [])):
                        # we don't have individual alteration per pitch here, use alterations list if present
                        alterations = ev.get("alterations") or []
                        alt = alterations[i] if i < len(alterations) else 0
                        k = duration_to_k(ev.get("figure"), ev.get("duration"))
                        v = vertex_id(p, normalize_alteration(alt), k)
                        M0_set.add(v)
                        sub.append(v)
                    poly.append({"vertex": tuple(sub), "pos": ev.get("position"), "type": "chord"})
                else:
                    # normal note
                    note_name = ev.get("note")
                    alt = ev.get("alteration", 0)
                    k = duration_to_k(ev.get("figure"), ev.get("duration"))
                    v = vertex_id(note_name, normalize_alteration(alt), k)
                    M0_set.add(v)
                    poly.append({"vertex": v, "pos": ev.get("position"), "type": "note"})
                global_position += 1
            M1.append(poly)
    return M0_set, M1


def compute_valence_and_mu(M0_set, M1):
    # valence val(m): count total occurrences across all polygons
    val = Counter()

    for poly in M1:
        for item in poly:
            v = item["vertex"]
            if isinstance(v, tuple) and all(isinstance(x, tuple) for x in v):
                # nested tuple of tuples? treat chord
                # but in our representation chord is tuple of vertex tuples OR tuple of strings
                # if chord contains vertex tuples -> increase count for each
                for sub in v:
                    val[sub] += 1
            elif isinstance(v, tuple) and isinstance(v[0], tuple):
                for sub in v:
                    val[sub] += 1
            elif isinstance(v, tuple) and isinstance(v[0], str) and len(v) == 3:
                val[v] += 1
            elif isinstance(v, tuple):
                # chord stored as tuple of vertex tuples
                try:
                    for sub in v:
                        val[sub] += 1
                except Exception:
                    val[v] += 1
            else:
                val[v] += 1

    mu = {}
    for m in M0_set:
        if val[m] == 1:
            mu[m] = 2
        else:
            mu[m] = 1
    return val, mu


def orientation_and_successors(M1):
    # orientation is order of polygons w1<w2<... circular
    # successors: for each vertex occurrence, successor is next in the polygon (circular)
    successors = defaultdict(list)
    for pi, poly in enumerate(M1):
        n = len(poly)
        for i, item in enumerate(poly):
            v = item["vertex"]
            # next index circular
            if n == 0:
                continue
            next_idx = (i + 1) % n
            next_v = poly[next_idx]["vertex"]
            # expand chords: define successors between vertex units
            # For chords we link the chord-block as a single unit
            successors[v].append(next_v)
    return successors


def count_loops(M0_set, M1):
    # #Loops(Q_M): a loop occurs when a vertex appears more than once within same polygon
    loops = Counter()
    for poly in M1:
        occ = Counter()
        for item in poly:
            v = item["vertex"]
            # if chord tuple, break into components
            if isinstance(v, tuple) and all(isinstance(x, tuple) or (isinstance(x, str) and len(v) == 3) for x in v):
                # treat chords as multiple vertices
                if isinstance(v[0], tuple):
                    for sub in v:
                        occ[sub] += 1
                else:
                    occ[v] += 1
            else:
                occ[v] += 1
        for m, c in occ.items():
            if c > 1:
                loops[m] += (c - 1)
    return loops


def dimension_algebra(M0_set, M1, val, mu):
    # dim_k Λ_M = 2|M1| + sum_{m in M0} [ val(m) * ( val(m) * mu(m) - 1 ) ]
    sum_term = 0
    for m in M0_set:
        sum_term += val[m] * (val[m] * mu[m] - 1)
    dim = 2 * len(M1) + sum_term
    return int(dim)


def dimension_center(M0_set, M1, mu, loops):
    # dim_k Z(Λ_M) = 1 + |M1| - |M0| + sum_{m in M0} mu(m) + #(Loops(QM)) - |{m in M0 | val(m)=1}|
    count_val1 = sum(1 for m in M0_set if mu[m] == 2)
    sum_term = sum(mu[m] for m in M0_set)
    dimZ = 1 + len(M1) - len(M0_set) + sum_term + sum(loops.values()) - count_val1
    return int(dimZ)


def geometric_mapping(score_json, filter_repeats=True):
    # Generate coordinates (x,y) across whole piece
    points = []  # list of dicts {x,y,vertex}
    x = 1
    last_repr = None
    for part in score_json:
        for measure in part.get("measures", []):
            for ev in measure.get("notes", []):

                #---ignorar los silencios---
                if ev.get("type") == "rest": 
                    continue

                #---filtro---
                #if ev.get("note") != "D":
                #    continue

                # get y coordinate
                sp = ev.get("staff_position")
                if isinstance(sp, list):
                    y = float(np.mean(sp))
                else:
                    y = sp if sp is not None else 0.0

                note_repr = (ev.get("note"), ev.get("alteration"), ev.get("duration"))
                if ev.get("type") == "chord":
                    note_repr = (tuple(ev.get("notes")), tuple(ev.get("alterations", [])), ev.get("duration"))

                if filter_repeats and last_repr is not None and note_repr == last_repr:
                    # skip repeated identical class-consecutive
                    x += 1
                    last_repr = note_repr
                    continue

                points.append({"x": x, "y": y, "repr": note_repr})
                last_repr = note_repr
                x += 1
    return points


def plot_points(points, outpath):
    if plt is None:
        print("matplotlib not available; skipping plot")
        return
    xs = [p["x"] for p in points]
    ys = [p["y"] for p in points]
    plt.figure(figsize=(10, 4))

    #---con linea---
    plt.plot(xs, ys, marker="o", linestyle="-", color="k")

    #---sin linea---
    #plt.plot(xs, ys, marker="o", linestyle="", color="k", markersize=4, alpha=0.6)

    plt.xlabel("Index (x)")
    plt.ylabel("Staff distance to clef reference (y)")
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(outpath, dpi=200)
    plt.close()


def analyze(json_path, out_json=None, plot_path=None, crab=False):
    score = load_json(json_path)

    M0, M1 = build_M0_M1(score)
    val, mu = compute_valence_and_mu(M0, M1)
    loops = count_loops(M0, M1)
    successors = orientation_and_successors(M1)

    dim = dimension_algebra(M0, M1, val, mu)
    dimZ = dimension_center(M0, M1, mu, loops)

    points = geometric_mapping(score)

    result = {
        "M0_size": len(M0),
        "M1_size": len(M1),
        "M0": [list(m) for m in M0],
        "valence": {str(m): int(val[m]) for m in M0},
        "mu": {str(m): int(mu[m]) for m in M0},
        "loops": {str(k): int(v) for k, v in loops.items()},
        "successors_sample": {str(k): [str(s) for s in v[:3]] for k, v in list(successors.items())[:10]},
        "dim_algebra": dim,
        "dim_center": dimZ,
        "points_count": len(points)
    }

    if out_json:
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

    if plot_path:
        plot_points(points, plot_path)

    # Crab canon: analyze retrograded sequence
    if crab:
        M1_rev = list(reversed(M1))
        # Recompute val/loops/dim for reversed polygon order
        val_r, mu_r = compute_valence_and_mu(M0, M1_rev)
        loops_r = count_loops(M0, M1_rev)
        dim_r = dimension_algebra(M0, M1_rev, val_r, mu_r)
        dimZ_r = dimension_center(M0, M1_rev, mu_r, loops_r)
        result["crab"] = {"dim_algebra": dim_r, "dim_center": dimZ_r}
        if out_json:
            with open(out_json, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)

    # Bloque para visualizar el Brauer Quiver (LIMPIO)
    if plot_path: 
        import networkx as nx
        G = nx.DiGraph()
        
        # Definimos la función de etiquetas fuera de los bucles por eficiencia
        def get_label(vertex):
            if not isinstance(vertex, (list, tuple)): return str(vertex)
            if isinstance(vertex[0], tuple): return "Chord"
            note = str(vertex[0])
            alt = "#" if vertex[1] > 0 else ("b" if vertex[1] < 0 else "")
            return f"{note}{alt}"

        for v, succs in successors.items():
            u_label = get_label(v)
            for s in succs:
                v_label = get_label(s)
                
                # --- AQUÍ ESTÁ EL TRUCO PARA QUITAR BUCLES ---
                if u_label == v_label:
                    continue  # Si la nota va a sí misma, se ignora
                # ---------------------------------------------

                G.add_edge(u_label, v_label)
        
        # Limpieza extra por seguridad (elimina cualquier loop residual)
        G.remove_edges_from(nx.selfloop_edges(G))

        plt.figure(figsize=(12, 12))
        
        # Layout circular: resalta la estructura cíclica de Bach
        pos = nx.circular_layout(G) 
        
        nx.draw(G, pos, 
                with_labels=True, 
                node_color='lavender', 
                edge_color='steelblue', 
                node_size=2500, 
                font_size=10, 
                font_weight='bold',
                arrows=True, 
                arrowsize=20,
                connectionstyle='arc3, rad = 0.1') # Flechas curvas para que no se encimen

        plt.title("Brauer Quiver (Q_M) - Sin Bucles")
        
        quiver_path = plot_path.replace(".png", "_quiver.png")
        plt.savefig(quiver_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"¡Grafo limpio guardado en: {quiver_path}!")

    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("json", help="Path to parsed score JSON")
    p.add_argument("--out", help="Output JSON summary path")
    p.add_argument("--plot", help="Output PNG plot path")
    p.add_argument("--crab", action="store_true", help="Also analyze retrograded (crab canon) sequence")
    args = p.parse_args()

    res = analyze(args.json, out_json=args.out, plot_path=args.plot, crab=args.crab)
    print("Analysis complete. Summary:\n", json.dumps(res, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
