"""
Plots average unspent larvae for most recent LONG_TERM_COUNT and SHORT_TERM_COUNT replays (the idea being visualisation
of long and short term trends)
"""

import os

import matplotlib.pyplot as plt
import numpy as np
from numpy.polynomial import Polynomial

from pathlib import Path

from .skill_tracker import replays_dir, consume_replay, parse_timestamp
from .trackers.LarvaeVsResourcesTracker import LarvaeVsResourcesTracker

LONG_TERM_COUNT = 100
SHORT_TERM_COUNT = 15
CUTOFF = '7:30' # cut off games before mid-game starts to get a more stable signal

if __name__ == '__main__':
    root = Path(replays_dir)
    # reverse sort all replays by date
    files = sorted(root.iterdir(), key = lambda f: f.stat().st_ctime, reverse=True)

    averages = []
    for file in files[:LONG_TERM_COUNT]:
        cutoff = parse_timestamp(CUTOFF)
        tracker = LarvaeVsResourcesTracker('orastem')
        true_cutoff = consume_replay(str(file.resolve()), [tracker], cutoff)
        if true_cutoff >= cutoff: # skip replays shorter than cutoff
            larvae_history = [event['larvae'] for event in tracker.data]
            avg_unspent_larvae = sum(larvae_history) / len(tracker.data)
            averages.append(avg_unspent_larvae)

    # we processed the range of replays in reverse chronological order (newest to oldest) - now reverse the list
    # so the plot goes from oldest to newest
    x = range(len(averages))
    y = list(reversed(averages))
    plt.plot(x, y)

    overall_trend = Polynomial.fit(x, y, deg=1) # fit the trend line (degree 1 polynomial)
    plt.plot(x, overall_trend(x))

    recent_trend = Polynomial.fit(x[-SHORT_TERM_COUNT:], y[-SHORT_TERM_COUNT:], deg=1)
    plt.plot(x[-SHORT_TERM_COUNT:], recent_trend(x[-SHORT_TERM_COUNT:]))

    plt.show()
