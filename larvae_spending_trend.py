"""
Plots average unspent larvae for most recent LONG_TERM_COUNT and SHORT_TERM_COUNT replays (the idea being visualisation
of long and short term trends)
"""

import os
import argparse

import matplotlib.pyplot as plt
import numpy as np
from numpy.polynomial import Polynomial

from pathlib import Path

from .skill_tracker import replays_dir, consume_replay, parse_timestamp
from .trackers.LarvaeVsResourcesTracker import LarvaeVsResourcesTracker


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=f'Default replay search path: {replays_dir}')
    parser.add_argument('-n', '--number-of-replays', type=int, default=50, dest='number_of_replays', action='store', help='number of replays to process')
    parser.add_argument('-r', '--recent-trend', type=int, default=15, dest='recent_trend', action='store', help='number of most recent replays to plot the short term trend over')
    parser.add_argument('-c', '--cutoff-time', type=parse_timestamp, default='12:00', dest='cutoff', action='store', help='cutoff time for each replay in format mm:ss (cutting off before late game should give a more useful signal)')
    parser.add_argument('-s', '--short-game-cutoff', type=parse_timestamp, default='4:00', dest='short_cutoff', action='store', help='ignore games shorter than this time (in format mm:ss)')

    args = parser.parse_args()
    root = Path(replays_dir)
    # reverse sort all replays by date
    files = iter(sorted(root.iterdir(), key = lambda f: f.stat().st_ctime, reverse=True))

    averages = []
    processed = 0
    while processed < args.number_of_replays:
        tracker = LarvaeVsResourcesTracker('orastem')
        file = str(next(files).resolve())
        actual_cutoff = consume_replay(file, [tracker], args.cutoff)
        if actual_cutoff >= args.cutoff: # skip replays shorter than cutoff
            larvae_history = [event['larvae'] for event in tracker.data]
            avg_unspent_larvae = sum(larvae_history) / len(tracker.data)
            averages.append(avg_unspent_larvae)
            processed += 1

    # we processed the range of replays in reverse chronological order (newest to oldest) - now reverse the list
    # so the plot goes from oldest to newest
    x = range(len(averages))
    y = list(reversed(averages))
    plt.plot(x, y)

    overall_trend = Polynomial.fit(x, y, deg=1) # fit the trend line (degree 1 polynomial)
    plt.plot(x, overall_trend(x))

    recent_trend = Polynomial.fit(x[-args.recent_trend:], y[-args.recent_trend:], deg=1)
    plt.plot(x[-args.recent_trend:], recent_trend(x[-args.recent_trend:]))

    plt.show()
