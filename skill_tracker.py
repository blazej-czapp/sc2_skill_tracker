#!/usr/bin/env python

import matplotlib.pyplot as plt
import sc2reader
import sys
import time

from replay_helpers import discover_zerg_names, find_last_replay
from sc2reader.events import PlayerStatsEvent
from trackers.DroneTracker import DroneTracker
from trackers.LarvaeVsResourcesTracker import LarvaeVsResourcesTracker
from trackers.InjectTracker import InjectTracker

replays_dir = "C:/Users/blazej/Documents/StarCraft II/Accounts/139961577/2-S2-1-4777600/Replays/Multiplayer"

def plot_trackers(player_name, trackers):
    # plotting every tracker in a separate Axes of the same Figure
    fig, axeses = plt.subplots(len(trackers), 1)
    fig.suptitle(player_name, fontsize=16)

    for i, tracker in enumerate(trackers):
        axes = axeses[i]
        tracker.plot(axes)

if __name__ == '__main__':
    if len(sys.argv) == 1:
        replay_file = find_last_replay(replays_dir)
    elif len(sys.argv) == 2:
        replay_file = sys.argv[1]
    else:
        print("usage: %s filename.SC2replay OR %s" % (sys.argv[0], sys.argv[0]))
        sys.exit(1)

    print("Loading replay from file: " + replay_file)

    zerg_names = discover_zerg_names(replay_file)
    if len(zerg_names) == 0:
        print("No Zerg players found")
        sys.exit(2)
    elif (len(zerg_names) > 2):
        print("Too many Zerg players found (%d), only 1v1 games supported" % len(zerg_names))
        sys.exit(3)

    rep = sc2reader.load_replay(replay_file)

    all_trackers = [LarvaeVsResourcesTracker, DroneTracker, InjectTracker]

    # instantiate and associate all trackers for each player
    player_trackers = { player_name:[tracker(player_name) for tracker in all_trackers] for player_name in zerg_names }
    for event in rep.events:
        for player in player_trackers:
            for tracker in player_trackers[player]:
                tracker.consume_event(event)

    for player in player_trackers:
        plot_trackers(player, player_trackers[player])
    plt.show()