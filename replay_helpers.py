import os
import sc2reader

from stat import S_ISREG, ST_CTIME, ST_MODE

from sc2reader.events import PlayerStatsEvent

GAME_SPEED = 1.4

def real_seconds(game_seconds):
    """ converts from game seconds (faster speed) to wall clock seconds """
    return game_seconds / GAME_SPEED

def game_seconds(real_seconds):
    """ converts from wall clock seconds to game seconds """
    return real_seconds * GAME_SPEED

def timestamp(seconds):
    return "%02.i:%02.i" % (int(seconds) // 60, int(seconds) % 60)

def discover_players(replay_file):
    rep = sc2reader.load_replay(replay_file)
    rep.load_tracker_events()
    players = set()
    for event in rep.tracker_events:
        if isinstance(event, PlayerStatsEvent):
            players.add(event.player)
            if len(players) == 2: # read as long as it takes to find both players
                break

    if (len(players) != 2):
        print(replay_file)
    #assert len(players) == 2

    return players

def find_last_replay(base_dir):
    all_replays = (os.path.join(base_dir, replay) for replay in os.listdir(base_dir))
    all_replays = ((os.stat(path), path) for path in all_replays)

    # leave only regular files, insert creation date
    all_replays = ((stat[ST_CTIME], path) for stat, path in all_replays if S_ISREG(stat[ST_MODE]))

    return max(all_replays, key = lambda f: f[0])[1]        

class Entity(object):
	LARVA = 'Larva'
	DRONE = 'Drone'
	EGG = 'Egg'