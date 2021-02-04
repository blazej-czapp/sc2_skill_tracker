import argparse
import matplotlib.pyplot as plt
import numpy as np
import sc2reader
import os.path
import sys
import time

from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D
from matplotlib import cm
from sc2reader.events import PlayerStatsEvent

from .replay_helpers import discover_players, find_last_replay, game_seconds
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
    zerg_names = [player.name for player in discover_players(replay_file) if player.play_race == "Zerg"]

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

def plot_trends(count, player):
    """ Plots how how certain per-game statistics evolve over time for the player

        param: count number of most recent replays to look at
    """
    files = [os.path.join(replays_dir, f) for f in os.listdir(replays_dir)]
    files.sort(key=os.path.getmtime)
    files = files[-count:] # take count most recent

    # 2D array of unspent larvae history for all replays
    # Say we have 3 replays of length 3,2,3 and the following unspent larvae counts:
    # 4 2 6
    # 3 1
    # 6 4 2
    unspent_larvae = []

    for f in files:
        rep = sc2reader.load_replay(f)
        tracker = LarvaeVsResourcesTracker(player)

        for event in rep.events:
            tracker.consume_event(event)

        # append the entire history for this replay as a list
        unspent_larvae.append([tick['larvae'] for tick in tracker.data])

    #print(unspent_larvae)

    # To what length do we need to pad?
    max_len = np.array([len(array) for array in unspent_larvae]).max()

    # What value do we want to fill it with?
    default_value = -1

    # pad missing entries (from shorter replays) with -1 so we know not to count them, the example becomes:
    # 4 2 6
    # 3 1 -1
    # 6 4 2
    padded_histories = np.array([np.pad(array, (0, max_len - len(array)), mode='constant', constant_values=default_value) for array in unspent_larvae])
#    print(padded_histories)

    # window example (first one):
    # _
    #|4| 2 6
    #|3| 1 -1
    # -
    # 6  4 2
    window = 10
    averages = []
    for i in range(max_len):
        averages.append([])
        for j in range(len(padded_histories)-window):
            # take a vertical slice of size window and average non -1 values
            avg_window = padded_histories[j:j+window, i]
            valid = [x for x in avg_window if x != -1]
            avg = np.average(valid) if valid else 0 # zero if the entire window is missing data
            averages[i].append(avg)

    #print(averages)
    averages = np.array(averages)
    X = np.arange(0, len(padded_histories) - window)
    Y = np.arange(0, max_len)
    X, Y = np.meshgrid(X, Y)

    fig = plt.figure()
    ax = fig.gca(projection='3d')
    surf = ax.plot_surface(X, Y, averages, cmap=cm.coolwarm, linewidth=0, antialiased=False)
    #surf = ax.plot_surface(X, Y, averages, color='b')

    #too noisy, plot trends instead
    plt.show()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=f'Default replay search path: {replays_dir}')
    # both optional
    parser.add_argument('-u', '--until', type=parse_cutoff, dest='cutoff', action='store', help='cutoff time in format mm:ss')
    parser.add_argument("replay_file", nargs='?', help='Name of the replay file (absolute path or relative to replay search path). Latest replay if omitted.')
    args = parser.parse_args()

#    plot_trends(100, 'orastem')

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
