#!/usr/bin/env python

import argparse
import matplotlib.pyplot as plt
import sc2reader
import os.path
import sys
import time

from replay_helpers import discover_zerg_names, find_last_replay, game_seconds
from sc2reader.events import PlayerStatsEvent
from trackers.DroneTracker import DroneTracker
from trackers.LarvaeVsResourcesTracker import LarvaeVsResourcesTracker
from trackers.InjectTracker import InjectTracker

replays_dir = os.path.normpath("C:/Users/blazej/Documents/StarCraft II/Accounts/139961577/2-S2-1-4777600/Replays/Multiplayer")

def parse_cutoff(arg):
    split = arg.split(":")
    if len(split) != 2:
        raise argparse.ArgumentTypeError("Invalid cutoff time format")
    return game_seconds(int(split[0]) * 60 + int(split[1]))

def plot_trackers(player_name, trackers, cutoff_time):
    # plotting every tracker in a separate Axes of the same Figure
    fig, axeses = plt.subplots(len(trackers), 1)
    fig.suptitle(player_name, fontsize=16)

    for i, tracker in enumerate(trackers):
        axes = axeses[i]
        tracker.plot(axes, cutoff_time)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=f'Default replay search path: {replays_dir}')
    # both optional
    parser.add_argument('-u', '--until', type=parse_cutoff, dest='cutoff', action='store', help='cutoff time in format 12:34')
    parser.add_argument("replay_file", nargs='?', help='Name of the replay file (absolute path or relative to replay search path). Latest replay if omitted.')
    args = parser.parse_args()

    if args.replay_file is None:
        replay_file = find_last_replay(replays_dir)
    else:
        replay_file = args.replay_file

    if not os.path.isfile(replay_file):
        print(f"Replay file not found: {replay_file}")
        replay_file = os.path.join(replays_dir, replay_file)
        print(f"Looking for it in replays directory: {replays_dir} as {replay_file}")
    if not os.path.isfile(replay_file):
        print("Replay file not found")
        sys.exit(1)

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
        plot_trackers(player, player_trackers[player], args.cutoff)
    plt.show()