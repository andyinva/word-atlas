#!/usr/bin/env python3
"""
export_context_strips.py

Plan step 8, last part: hand the contexts to the heat reports.

discover_contexts.py finds the contexts on windows of verses; the heat
reports (atlas_heat.py, in the folder above) work on windows of any size
and need no extra packages.  So this script fits the contexts once and
writes each verse's own mix of them to one file:

    Eval_data/results/context_strips.json.gz

atlas_heat.py --contexts reads it and scores a window as the average of
its verses' mixes, weighted by how many words each verse has.  That
average follows the mix discover_contexts.py measures on the whole
window closely (checked on the Old Testament at 10 verses: a correlation
of 0.95 to 0.99 for the content contexts, 0.87 to 0.96 for the voices),
and it works for any window size the heat report is asked for.

The names come from name_contexts.py (metadata.db, or context_names.txt),
matched by marking words, so the file carries the reader's names; a
context with no name keeps its marking words as its label.

Run it again after naming more contexts, or after any change to the
vocabulary (export_vocab.py):

    python3 Eval_data/export_context_strips.py
    python3 Eval_data/export_context_strips.py --resamples 0     faster, no steadiness

Needs numpy, scipy and scikit-learn (like discover_contexts.py).
"""

import argparse
import gzip
import json
import sys
from argparse import Namespace
from datetime import datetime
from pathlib import Path

import numpy as np

# This script lives in word_atlas/Eval_data, beside discover_contexts.py.
EVAL_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(EVAL_DIR))

from discover_contexts import ContextModel, STEADY      # noqa: E402

# How many contexts each layer and testament is split into: the same
# numbers discover_contexts.py uses by default, so the names fit.
CONTEXTS = {("content", "Old"): 20, ("content", "New"): 16,
            ("orientation", "Old"): 10, ("orientation", "New"): 8}

# A context with steadiness below STEADY (discover_contexts.py, the same
# line the contexts reports draw) is marked unsteady; the heat report
# says so beside its strip.


class StripExporter:
    """Fits the contexts of each layer and testament and writes every verse's mix."""

    def __init__(self, resamples: int, seed: int):
        self.resamples = resamples
        self.seed = seed

    def layer(self, layer: str, testament: str) -> dict:
        """One layer of one testament: its contexts and every verse's mix."""
        k = CONTEXTS[(layer, testament)]
        model = ContextModel(Namespace(testament=testament, contexts=k, size=10, step=5,
                                       min_windows=5, strongs_only=False,
                                       resamples=self.resamples, seed=self.seed,
                                       keep_aramaic=False, layer=layer))
        model.fit()
        # Each verse on its own: its words counted, then its mix.
        V = model.voc.verse_matrix()
        mix = model.mix_of(V)
        # The words of the layer in each verse, the weight of its mix in
        # a window's average (a verse with none of them has no say).
        weight = np.asarray(V[:, model.keep].sum(axis=1)).ravel().astype(int)
        contexts = []
        for c in range(k):
            name = model.names.get(c) if hasattr(model, "names") else None
            contexts.append({
                "number": c + 1,
                "name": name,
                "words": model.word_label(c),
                "label": name or model.word_label(c),
                "steadiness": round(float(model.steadiness[c]), 3),
                "steady": bool(model.steadiness[c] >= STEADY or self.resamples == 0),
            })
        named = sum(1 for c in contexts if c["name"])
        print(f"  {layer}, {testament}: {k} contexts ({named} named), "
              f"{len(weight):,} verses")
        return {
            "contexts": contexts,
            "verse_id": [int(v) for v in model.voc.verses["verse_id"]],
            "weight": weight.tolist(),
            # Each verse's share of each context in thousandths, to keep
            # the file small: one list per context, in verse order.
            "mix": [np.rint(mix[:, c] * 1000).astype(int).tolist() for c in range(k)],
        }

    def run(self, out: Path) -> None:
        data = {"made": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "note": "Each verse's mix of the contexts, in thousandths "
                        "(export_context_strips.py; read by atlas_heat.py --contexts).",
                "layers": {}}
        for layer in ("content", "orientation"):
            for testament in ("Old", "New"):
                data["layers"][f"{layer} {testament}"] = self.layer(layer, testament)
        out.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(out, "wt", encoding="utf-8") as f:
            json.dump(data, f, separators=(",", ":"))
        print(f"Written to {out} ({out.stat().st_size / 1e6:.1f} MB)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Every verse's mix of the contexts, for atlas_heat.py")
    parser.add_argument("--resamples", type=int, default=6,
                        help="reruns for steadiness (default 6; 0 = skip, faster)")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--out", type=Path, default=EVAL_DIR / "results" / "context_strips.json.gz")
    args = parser.parse_args()
    StripExporter(args.resamples, args.seed).run(args.out)


if __name__ == "__main__":
    main()
