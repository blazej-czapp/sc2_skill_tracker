"""
Deletes non-ladder games from the replays directory, specifically:
 - co-op maps
 - 1v1 games vs AI
 - games with more or fewer than 2 players
"""

import sc2reader

import os
import sys

from .skill_tracker import replays_dir
from .replay_helpers import discover_players

files = os.listdir(replays_dir)

coop_maps = ["Void Thrashing", "Void Launch", "Oblivion Express", "Rifts to Korhal", "Temple of the Past",
             "Lock & Load", "Chain of Ascension", "The Vermillion Problem", "Mist Opportunities", "Miner Evacuation",
             "Dead of Night", "Scythe of Amon", "Part and Parcel", "Malwarfare", "Cradle of Death"]

def run():
    for (i, f) in enumerate(files):
        abspath = os.path.join(replays_dir, f)
        print(f"processing: {(i+1)/len(files)*100:.1f}%\r", end = "")

        if any([coop_name in abspath for coop_name in coop_maps]):
            os.remove(abspath)
            print("deleted coop: ", f)
            continue

        players = discover_players(abspath)
        if len(players) != 2:
            print("deleted non 1v1: ", f)
            os.remove(abspath)
            continue
        if any(player.name.startswith("A.I. 1") for player in players):
            print("deleted vs AI: ", f)
            os.remove(abspath)
            continue

if __name__ == '__main__':
    run()
