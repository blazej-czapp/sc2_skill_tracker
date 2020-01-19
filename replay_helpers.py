import os
import sc2reader

from stat import S_ISREG, ST_CTIME, ST_MODE

from sc2reader.events import PlayerStatsEvent

def real_seconds(game_seconds):
    """ converts from game seconds (faster speed) to wall clock seconds """
    return game_seconds / 1.4

def timestamp(seconds):
    return "%02.i:%02.i" % (int(seconds) // 60, int(seconds) % 60)

def discover_zerg_names(replay_file):
    rep = sc2reader.load_replay(replay_file)
    rep.load_tracker_events()
    zergs = set()
    players = set()
    for event in rep.tracker_events:
        if isinstance(event, PlayerStatsEvent):
            players.add(event.player.name)
            if event.player.play_race == 'Zerg':
                zergs.add(event.player.name)
            if len(players) == 2: # read as long as it takes to find both players
                break

    assert len(players) == 2

    return zergs

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