import argparse
import matplotlib.pyplot as plt
import sc2reader
import os.path
import sys
import time

from matplotlib.figure import Figure
from sc2reader.events import PlayerStatsEvent

from .replay_helpers import discover_zerg_names, find_last_replay, game_seconds
from .trackers.DroneTracker import DroneTracker
from .trackers.LarvaeVsResourcesTracker import LarvaeVsResourcesTracker
from .trackers.InjectTracker import InjectTracker
from .SC2SkillTrackerException import SC2SkillTrackerException

REPLAY_PATH_VAR = 'SC2_SKILL_TRACKER_REPLAY_PATH'

replays_dir = os.path.normpath(os.environ[REPLAY_PATH_VAR]) if REPLAY_PATH_VAR in os.environ else None

def parse_cutoff(arg):
    """parse string in format mm:ss in real time to game seconds
    """
    split = arg.split(":")
    if len(split) != 2:
        raise argparse.ArgumentTypeError("Invalid cutoff time format")
    return game_seconds(int(split[0]) * 60 + int(split[1]))

def plot_trackers(player_name, trackers, cutoff_time, figure, axeses):
    # plotting every tracker in a separate Axes of the same Figure
    figure.suptitle(player_name, fontsize=16)

    for i, tracker in enumerate(trackers):
        axes = axeses[i]
        axes.set_title(tracker.title)
        tracker.plot(axes, cutoff_time)

def generate_plots(replay_file, cutoff=None, use_pyplot=False):
    """cutoff - plot only until this time in game seconds
    """
    zerg_names = discover_zerg_names(replay_file)

    if len(zerg_names) == 0:
        raise SC2SkillTrackerException("No Zerg players found")
    elif (len(zerg_names) > 2):
        raise SC2SkillTrackerException(f"Too many Zerg players found {len(zerg_names)}, only 1v1 games supported")

    rep = sc2reader.load_replay(replay_file)

    all_trackers = [LarvaeVsResourcesTracker, DroneTracker, InjectTracker]

    # instantiate and associate all trackers for each player
    player_trackers = { player_name:[tracker(player_name) for tracker in all_trackers] for player_name in zerg_names }
    for event in rep.events:
        for player in player_trackers:
            for tracker in player_trackers[player]:
                tracker.consume_event(event)

    figures = []
    for player in player_trackers:
        # this split is awkward, but I couldn't find a way to create a figure without pyplot and then display it with it
        # (which would allow to just return the figure and let the caller decide how to display it)
        if use_pyplot:
            fig, axeses = plt.subplots(len(player_trackers[player]), 1)
        else:
            # Generate the figure without using pyplot (useful for embedding graphs, e.g. on the web)
            fig = Figure(figsize=(18, 12))
            axeses = fig.subplots(len(player_trackers[player]), 1)

        plot_trackers(player, player_trackers[player], cutoff, fig, axeses)
        figures.append(fig)

    return figures

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=f'Default replay search path: {replays_dir}')
    # both optional
    parser.add_argument('-u', '--until', type=parse_cutoff, dest='cutoff', action='store', help='cutoff time in format mm:ss')
    parser.add_argument("replay_file", nargs='?', help='Name of the replay file (absolute path or relative to replay search path). Latest replay if omitted.')
    args = parser.parse_args()

    if args.replay_file is None:
        if replays_dir:
            replay_file = find_last_replay(replays_dir)
        else:
            print("Error: No replay file provided. I can't look for the latest replay because SC2_SKILL_TRACKER_REPLAY_PATH is not set.")
            sys.exit(1)
    else:
        replay_file = args.replay_file

    if not os.path.isfile(replay_file):
        print(f"Replay file not found: {replay_file}")
        replay_file = os.path.join(replays_dir, replay_file)
        print(f"Looking for it in replays directory: {replays_dir} as {replay_file}")
    if not os.path.isfile(replay_file):
        print("Replay file not found")
        sys.exit(1)

    try:
        generate_plots(replay_file, args.cutoff, use_pyplot=True)
        plt.show()
    except SC2SkillTrackerException as e:
        print("Error: " + str(e))
        sys.exit(1)
