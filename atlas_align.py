#!/usr/bin/env python3
"""
atlas_align.py  -  word alignment between two texts of the same verses

The standard alignment method of machine translation (IBM Model 1: a
few rounds of expectation-maximisation over every verse the two texts
share) learns, for every word of one text, which words of the other
render it and how often.  It began in Eval_data/hebrew_greek_map.py,
where it learns the Septuagint's renderings of the Hebrew; it is shared
here so that atlas_renderings.py can learn each English translation's
renderings of the King James with the same code and the same rules.

THE RULES, as the quotation work settled them (IMPROVEMENTS.md, the
quotation readings, 2026-10-17):

    read both ways   the map is learned in both directions, and a pairing
                     is trusted only when it holds in both: the source
                     word goes to the target word with at least a set
                     share, and the target word comes back to the source
                     word with at least that share
    two verses       a pairing must be made in at least two verses: one
                     verse's peculiar rendering (Kiyyun to Rephan, Amos
                     5:26) is not a habit
    proper names     a proper name cannot stand behind a common word, nor
                     a common word behind a name

    pairs = [(source words, target words), ...]        one entry per shared verse
    model = WordMap(pairs); model.train(5)             t(target | source)
    trust = TwoWayMap(pairs, rounds=5)                 both directions, the verses behind each pairing
    trust.trusted(source, target)                      True when the pairing passes all three rules

Words may be any hashable values (strings, or integers for speed).
Standard library only; runs the same on Ubuntu and Windows 11.

Author: Andrew Hopkins (with Claude)
"""

from collections import defaultdict

# The empty word: a target word the translator added with nothing behind
# it (an article, a particle) is aligned to it rather than forced onto a
# source word
NULL = "NULL"

# Renderings kept by renderings(): a share of at least this much
KEEP_SHARE = 0.02

# A verse "makes" a pairing when the target word goes to the source word
# with at least this much of its alignment there
SUPPORT_SHARE = 0.1


class WordMap:
    """
    IBM Model 1 from source words to target words: t[(target, source)] is
    the share of the source word's renderings that went to the target
    word, learned over every pair of verses.
    """

    def __init__(self, pairs, keep_share=KEEP_SHARE, support_share=SUPPORT_SHARE, log=None):
        self.pairs = pairs                       # [(source words, target words)]
        self.t = {}                              # (target, source) -> share
        self.keep_share = keep_share
        self.support_share = support_share
        self.log = log if log is not None else print

    def train(self, rounds):
        """Learn t by expectation-maximisation, starting even: every target word equally likely from every source word it shares a verse with."""
        for r in range(rounds):
            count = defaultdict(float)
            total = defaultdict(float)
            t = self.t
            for src, tgt in self.pairs:
                hs = list(src) + [NULL]
                for g in tgt:
                    if r == 0:
                        ps = [1.0] * len(hs)
                    else:
                        ps = [t.get((g, h), 0.0) for h in hs]
                    z = sum(ps) or 1.0
                    for h, p in zip(hs, ps):
                        if p:
                            c = p / z
                            count[(g, h)] += c
                            total[h] += c
            self.t = {k: v / total[k[1]] for k, v in count.items()}
            self.log(f"  round {r + 1} of {rounds}")

    def share(self, target, source):
        """t(target | source): the share of the source word's renderings that went to the target word."""
        return self.t.get((target, source), 0.0)

    def both_ways(self):
        """
        source -> {target: [reverse share, verses]}: for each target word,
        the share of its occurrences that render the source word, and the
        verses in which the pairing is made.  Kept for pairings made in a
        verse at all.
        """
        count = defaultdict(float)
        g_total = defaultdict(float)
        support = defaultdict(int)
        for src, tgt in self.pairs:
            hs = list(dict.fromkeys(src)) + [NULL]
            for g in tgt:
                ps = [self.t.get((g, h), 0.0) for h in hs]
                z = sum(ps) or 1.0
                g_total[g] += 1
                for h, p in zip(hs, ps):
                    if h != NULL and p:
                        count[(g, h)] += p / z
                        if p / z >= self.support_share:
                            support[(g, h)] += 1
        out = defaultdict(dict)
        for (g, h), c in count.items():
            rev = c / g_total[g]
            if support[(g, h)] and (rev >= self.keep_share * 5 or self.t.get((g, h), 0.0) >= self.keep_share):
                out[h][g] = [round(rev, 3), support[(g, h)]]
        return dict(out)

    def renderings(self):
        """source -> [[target, share], ...], largest first, shares of keep_share or more."""
        out = defaultdict(list)
        for (g, h), v in self.t.items():
            if h != NULL and v >= self.keep_share:
                out[h].append([g, round(v, 3)])
        for h in out:
            out[h].sort(key=lambda x: -x[1])
        return dict(out)


class TwoWayMap:
    """
    The map read both ways, with the verses behind each pairing.  A
    pairing (source, target) is trusted when t(target | source) and
    t(source | target) both reach trust_share, it is made in at least
    min_verses verses, and the proper-name rule allows it.

        both = TwoWayMap(pairs, rounds=5, trust_share=0.05, min_verses=2,
                         source_names=set(), target_names=set())
        both.best(source_words, target_word)   the trusted source word behind a target word in a verse, or None
    """

    def __init__(self, pairs, rounds=5, trust_share=0.05, min_verses=2, source_names=None, target_names=None,
                 log=None):
        self.log = log if log is not None else print
        self.trust_share = trust_share
        self.min_verses = min_verses
        self.source_names = source_names or set()
        self.target_names = target_names or set()
        self.log("  source to target")
        self.forward = WordMap(pairs, log=self.log)
        self.forward.train(rounds)
        self.log("  target to source")
        self.backward = WordMap([(tgt, src) for src, tgt in pairs], log=self.log)
        self.backward.train(rounds)
        # The verses in which each pairing is made: the target word's best
        # source word in the verse, by the two directions together
        self.verses = defaultdict(int)
        for src, tgt in pairs:
            made = set()
            for g in tgt:
                h = self._best_any(src, g)
                if h is not None:
                    made.add((h, g))
            for pair in made:
                self.verses[pair] += 1

    def allowed(self, source, target):
        """The proper-name rule: a name only with a name, a common word only with a common word."""
        return (source in self.source_names) == (target in self.target_names)

    def score(self, source, target):
        """How strongly the two directions agree on a pairing: the product of the two shares."""
        return self.forward.share(target, source) * self.backward.share(source, target)

    def _best_any(self, src, g):
        """The source word of the verse the target word goes to best, by both directions (before the trust floors)."""
        best, best_score = None, 0.0
        for h in src:
            s = self.score(h, g)
            if s > best_score:
                best, best_score = h, s
        return best

    def trusted(self, source, target):
        """True when the pairing holds both ways, in at least min_verses verses, and the name rule allows it."""
        return (self.forward.share(target, source) >= self.trust_share
                and self.backward.share(source, target) >= self.trust_share
                and self.verses.get((source, target), 0) >= self.min_verses
                and self.allowed(source, target))

    def best(self, src, g):
        """The trusted source word behind a target word in one verse, or None when no pairing is trusted."""
        best, best_score = None, 0.0
        for h in src:
            if self.trusted(h, g):
                s = self.score(h, g)
                if s > best_score:
                    best, best_score = h, s
        return best
