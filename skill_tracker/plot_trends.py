"""
Plots values and trends for various statistics over a number of replays
"""

import os
import argparse

import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

import numpy as np
from numpy.polynomial import Polynomial

from pathlib import Path

from .plotter import consume_replay
from .replay_helpers import replays_dir, parse_timestamp
from .trackers.LarvaeVsResourcesTracker import LarvaeVsResourcesTracker
from .trackers.InjectTracker import InjectTracker


def plot_data_with_trends(axes, data):
        x = range(len(data))
        y = list(data)
        axes.plot(x, y)

        overall_trend = Polynomial.fit(x, y, deg=1) # fit the trend line (degree 1 polynomial)
        axes.plot(x, overall_trend(x))

        recent_trend = Polynomial.fit(x[-args.recent_trend:], y[-args.recent_trend:], deg=1)
        axes.plot(x[-args.recent_trend:], recent_trend(x[-args.recent_trend:]))


class LarvaSpendingTrend(object):
    def __init__(self, cutoff, player):
        self.cutoff = cutoff
        self.averages = []
        self.player = player


    def consume_replay(self, replay):
        tracker = LarvaeVsResourcesTracker(self.player)
        actual_cutoff = consume_replay(replay, [tracker], self.cutoff)

        # skip replays shorter than cutoff
        if actual_cutoff >= self.cutoff:
            larvae_history = [event['larvae'] for event in tracker.data]
            avg_unspent_larvae = sum(larvae_history) / len(tracker.data)
            self.averages.append(avg_unspent_larvae)
            return True
        else:
            return False


    def plot(self, axes, reverse):
        plot_data_with_trends(axes, list(reversed(self.averages)) if reverse else self.averages)


class InjectTrend(object):
    def __init__(self, cutoff, player):
        self.cutoff = cutoff
        self.data_points = []
        self.player = player


    def consume_replay(self, replay):
        tracker = InjectTracker(self.player)
        actual_cutoff = consume_replay(replay, [tracker], self.cutoff)

        if actual_cutoff >= self.cutoff:
            inject_history = tracker.inject_history(0, actual_cutoff)
            assert(inject_history['hatch_cutoff'] <= actual_cutoff)
            # skip replays where the main hatchery died
            if inject_history['hatch_cutoff'] == actual_cutoff:
                self.data_points.append(inject_history['proportion_injected'] * 100)
                return True
            else:
                return False
        else:
            return False


    def plot(self, axes, reverse):
        axes.yaxis.set_major_formatter(FuncFormatter(lambda val, _: f'{val:.0f}%'))
        plot_data_with_trends(axes, list(reversed(self.data_points)) if reverse else self.data_points)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=f'Default replay search path: {replays_dir}')
    parser.add_argument('-n', '--number-of-replays', type=int, default=50, dest='number_of_replays', action='store', help='number of replays to process')
    parser.add_argument('-r', '--recent-trend', type=int, default=15, dest='recent_trend', action='store', help='number of most recent replays to plot the short term trend over')
    parser.add_argument('-c', '--cutoff-time', type=parse_timestamp, default='7:00', dest='cutoff', action='store', help='cutoff time for each replay in format mm:ss (cutting off before mid game should give a more useful signal)')
    parser.add_argument('-d', '--replays-dir', type=str, default=replays_dir, dest='replays_dir', action='store', help='replay search path')
    parser.add_argument('-p', '--player', type=str, default='orastem', dest='player', action='store', help='player to plot trends for')

    args = parser.parse_args()

    root = Path(args.replays_dir)
    # reverse sort all replays by date
    files = iter(sorted(root.iterdir(), key = lambda f: f.stat().st_ctime, reverse=True))

    processed = 0
    trends = [LarvaSpendingTrend(args.cutoff, args.player), InjectTrend(args.cutoff, args.player)]
    while processed < args.number_of_replays:
        try:
            replay = str(next(files).resolve())
            if all([trend.consume_replay(replay) for trend in trends]):
                # a replay only counts towards the total if all trends consumed it successfully
                # (could do it with any(), let's see how it goes)
                processed += 1
                print(f"processing: {(processed)/args.number_of_replays*100:.1f}%\r", end = "")

        except StopIteration:
            break # ran out of replays, that's fine


    if processed > 1:
        fig, axeses = plt.subplots(len(trends), 1)
        for i, trend in enumerate(trends):
            # we processed the range of replays in reverse chronological order (newest to oldest) - plot them
            # in reverse of that (oldest to newest)
            trend.plot(axeses[i], reverse=True)

        plt.show()
    else:
        print(f"At least two usable replays are required to plot trends, found: {processed}")


