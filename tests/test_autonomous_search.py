import numpy as np
import pandas as pd
from crypto_quant.autonomous_search import _folds, _mutate, _population, _wilson_lower
from crypto_quant.search_engine import Strategy

def test_walk_forward_folds_are_chronological_and_non_overlapping():
    folds=_folds(10000)
    assert len(folds)==4
    assert all(a<b for a,b in folds)
    assert all(folds[i][1]<=folds[i+1][0] for i in range(3))
    assert folds[0][0]>=3000 and folds[-1][1]<=9000

def test_wilson_lower_is_below_observed_rate():
    assert _wilson_lower(70,100)<70
    assert _wilson_lower(0,100)==0

def test_mutation_keeps_valid_fast_slow_order():
    p=Strategy("trend_pullback",13,55,45,55,20,.8,1.5,3.,48,20)
    import random
    for seed in range(100):
        q=_mutate(p,random.Random(seed))
        assert q.fast<q.slow
        assert q.target_r>=3

def test_population_has_requested_size_and_unique_candidates():
    p=_population([],100,20261110)
    assert len(p)==100
    assert len(set(p))==100
