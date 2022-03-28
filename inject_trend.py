"""
Plots percentage of time the main hatchery is injected in recent replays
(for visualisation of long and short term trends)
"""

import os
import argparse

import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import numpy as np
from numpy.polynomial import Polynomial

from pathlib import Path

from .skill_tracker import replays_dir, consume_replay, parse_timestamp
from .trackers.InjectTracker import InjectTracker

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=f'Default replay search path: {replays_dir}')
    parser.add_argument('-n', '--number-of-replays', type=int, default=100, dest='number_of_replays', action='store', help='number of replays to process')
    parser.add_argument('-r', '--recent-trend', type=int, default=20, dest='recent_trend', action='store', help='number of most recent replays to plot the short term trend over')
    parser.add_argument('-c', '--cutoff-time', type=parse_timestamp, default='15:00', dest='cutoff', action='store', help='cutoff time for each replay in format mm:ss (cutting off before late game should give a more useful signal)')
    parser.add_argument('-s', '--short-game-cutoff', type=parse_timestamp, default='5:00', dest='short_cutoff', action='store', help='ignore games shorter than this time (in format mm:ss)')

    args = parser.parse_args()

    root = Path(replays_dir)
    # reverse sort all replays by date
    files = iter(sorted(root.iterdir(), key = lambda f: f.stat().st_ctime, reverse=True))

    data_points = []
    processed = 0
    while processed < args.number_of_replays:
        tracker = InjectTracker('orastem')
        actual_cutoff = consume_replay(str(next(files).resolve()), [tracker], args.cutoff)

        if actual_cutoff < args.short_cutoff:
            continue

        inject_history = tracker.inject_history(0, actual_cutoff)
        assert(inject_history['hatch_cutoff'] <= actual_cutoff)
        # skip replays where the main hatchery died
        if inject_history['hatch_cutoff'] == actual_cutoff:
            data_points.append(inject_history['proportion_injected'] * 100)
            processed += 1

    # we processed the range of replays in reverse chronological order (newest to oldest) - now reverse the list
    # so the plot goes from oldest to newest
    x = range(len(data_points))
    y = list(reversed(data_points))

    fig, axes = plt.subplots(1, 1)
    axes.yaxis.set_major_formatter(FuncFormatter(lambda val, _: f'{val:.0f}%'))
    axes.plot(x, y)

    overall_trend = Polynomial.fit(x, y, deg=1) # fit the trend line (degree 1 polynomial)
    plt.plot(x, overall_trend(x))

    recent_trend = Polynomial.fit(x[-args.recent_trend:], y[-args.recent_trend:], deg=1)
    plt.plot(x[-args.recent_trend:], recent_trend(x[-args.recent_trend:]))

    plt.show()
