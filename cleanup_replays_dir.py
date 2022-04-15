"""
Deletes non-ladder games from the replays directory, specifically:
 - co-op maps
 - 1v1 games vs AI
 - games with more or fewer than 2 players
 - *.writeCacheBackup files
"""

import os
import argparse
from pathlib import Path

from .skill_tracker import replays_dir
from .replay_helpers import discover_players


files = iter(sorted(Path(replays_dir).iterdir(), key = lambda f: f.stat().st_ctime, reverse=True))
all_replay_count = len(os.listdir(replays_dir))

coop_maps = ["Void Thrashing", "Void Launch", "Oblivion Express", "Rifts to Korhal", "Temple of the Past",
             "Lock & Load", "Chain of Ascension", "The Vermillion Problem", "Mist Opportunities", "Miner Evacuation",
             "Dead of Night", "Scythe of Amon", "Part and Parcel", "Malwarfare", "Cradle of Death"]

def run(number_of_replays):
    for (i, f) in enumerate(files):
        if i >= number_of_replays:
            break

        abspath = str(f.resolve())

        # don't know where these come from
        if abspath.endswith('.writeCacheBackup'):
            os.remove(abspath)
            continue

        print(f"processing: {(i+1)/number_of_replays*100:.1f}%\r", end = "")

        if any([coop_name in abspath for coop_name in coop_maps]):
            os.remove(abspath)
            print("deleted coop:", f)
            continue

        players = discover_players(abspath)
        if len(players) != 2:
            print("deleted non 1v1:", f)
            os.remove(abspath)
            continue
        if any(player.name.startswith("A.I. 1") for player in players):
            print("deleted vs AI:", f)
            os.remove(abspath)
            continue

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-n', '--number-of-replays', type=int, default=all_replay_count, dest='number_of_replays', action='store', help='number of most recent replays to process')

    args = parser.parse_args()

    run(args.number_of_replays)
