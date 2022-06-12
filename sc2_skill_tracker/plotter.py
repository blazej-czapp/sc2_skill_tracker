import argparse
import itertools
import os.path
import sys
import time

import matplotlib.pyplot as plt
import sc2reader
from matplotlib.figure import Figure
from sc2reader.events import PlayerLeaveEvent

from .replay_helpers import replays_dir, discover_players, find_last_replay, game_seconds, real_seconds, parse_timestamp
from .SC2SkillTrackerException import SC2SkillTrackerException
from .trackers.DroneTracker import DroneTracker
from .trackers.InjectTracker import InjectTracker
from .trackers.LarvaeVsResourcesTracker import LarvaeVsResourcesTracker
from .trackers.UpgradeTracker import UpgradeTracker


def plot_trackers(player_name, trackers, subsidiary_trackers, cutoff_time, figure, axeses):
    # plotting every tracker in a separate Axes of the same Figure, except subsidiary trackers,
    # which share plots with other trackers
    figure.suptitle(player_name, fontsize=16)

    assert(len(axeses) == len(trackers))
    for i, tracker in enumerate(trackers):
        axes = axeses[i]
        axes.set_title(tracker.title)
        tracker.plot(axes, cutoff_time)

        for sub_tracker in subsidiary_trackers:
            if sub_tracker.can_share_plot_with(tracker):
                sub_tracker.plot(axes, cutoff_time)


def consume_replay(replay_file, trackers, requested_cutoff=None):
    """ Returns the lesser of requested_cutoff and game end (replay end or a player leaving, presumably always the
        latter even if all buildings are destroyed?)
    """
    rep = sc2reader.load_replay(replay_file)
    true_cutoff = None
    for event in rep.events:
        if isinstance(event, PlayerLeaveEvent):
            # we consider the game to be over as soon as either player leaves
            true_cutoff = min(event.second, requested_cutoff) if requested_cutoff is not None else event.second
            break
        elif requested_cutoff is None or event.second <= requested_cutoff:
            for tracker in trackers:
                tracker.consume_event(event)
            true_cutoff = event.second # track last event seen
        else:
            break

    assert(true_cutoff is not None)
    return true_cutoff


def generate_plots(replay_file, requested_cutoff=None, use_pyplot=False):
    """ Returns a list of matplotlib Figures, one per player, with trackers plotted thereon
        :param requested_cutoff: - plot at most until this time in game seconds
    """
    zerg_names = [player.name for player in discover_players(replay_file) if player.play_race == "Zerg"]

    if len(zerg_names) == 0:
        raise SC2SkillTrackerException("No Zerg players found")

    all_trackers = [LarvaeVsResourcesTracker, DroneTracker, InjectTracker]

    # instantiate and associate all trackers for each player
    player_trackers = { player_name:[tracker(player_name) for tracker in all_trackers] for player_name in zerg_names }
    # subsidiary trackers expose can_share_plot_with() method which tell us which other trackers they're happy to share
    # axes with (e.g. upgrades can be plotted on any timeline, they don't need their dedicated plot)
    subsidiary_trackers = { player_name:[UpgradeTracker(player_name)] for player_name in zerg_names }

    # TODO check that this actually lines up with player stat events
    clamped_cutoff = requested_cutoff // 10 * 10 if requested_cutoff is not None else requested_cutoff #TODO check corner cases, e.g. clamping to zero
    # provide a flat list of all trackers to consume_replay()
    true_cutoff = consume_replay(replay_file, list(itertools.chain(*player_trackers.values())) + list(itertools.chain(*subsidiary_trackers.values())), clamped_cutoff)

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

        plot_trackers(player, player_trackers[player], subsidiary_trackers[player], true_cutoff, fig, axeses)
        figures.append(fig)

    return figures


def run():
    parser = argparse.ArgumentParser(description=f'Default replay search path: {replays_dir}')
    # both optional
    parser.add_argument('-u', '--until', type=parse_timestamp, dest='cutoff', action='store', help='cutoff time in format mm:ss')
    parser.add_argument('-b', '--build-order', type=str, dest='build_order', action='store', help='path to build order json file')
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


if __name__ == '__main__':
    run()
