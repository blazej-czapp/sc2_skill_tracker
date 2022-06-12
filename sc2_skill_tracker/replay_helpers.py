import os
import sc2reader

from stat import S_ISREG, ST_CTIME, ST_MODE

from sc2reader.events import PlayerStatsEvent

REPLAY_PATH_VAR = 'SC2_SKILL_TRACKER_REPLAY_PATH'

replays_dir = os.path.normpath(os.environ[REPLAY_PATH_VAR]) if REPLAY_PATH_VAR in os.environ else None

GAME_SPEED = 1.4


def real_seconds(game_seconds):
    """ converts from game seconds (faster speed) to wall clock seconds """
    return game_seconds / GAME_SPEED


def game_seconds(real_seconds):
    """ converts from wall clock seconds to game seconds """
    return real_seconds * GAME_SPEED


def timestamp(seconds):
    return "%02.i:%02.i" % (int(seconds) // 60, int(seconds) % 60)


def parse_timestamp(arg):
    """
    Parse string in format mm:ss in real time to game seconds
    """
    split = arg.split(":")
    if len(split) != 2:
        raise argparse.ArgumentTypeError("Invalid cutoff time format")
    return game_seconds(int(split[0]) * 60 + int(split[1]))


def discover_players(replay_file):
    rep = sc2reader.load_replay(replay_file)
    rep.load_tracker_events()
    players = set()
    for event in rep.tracker_events:
        if isinstance(event, PlayerStatsEvent):
            players.add(event.player)

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