from collections import defaultdict

class Tracker(object):
    """ Base class for trackers. Each tracker tracks some aspect of a player's game.
        Trackers should implement consume_event() (event from sc2reader) and store a list
        of dicts with relevant data in self.data.
        The dict must contain a "time" field with timestamp for each event.
    """

    # these don't behave the same as regular units so things break (e.g. they die, but are not born)
    UNHANDLED = ('Hatchery', 'Extractor', 'BanelingNest', 'SporeCrawler', 'SpawningPool',\
                 'CreepTumorBurrowed', 'SpineCrawler', 'CreepTumor', 'CreepTumorQueen',  \
                 'UltraliskCavern', 'NydusWorm', 'EvolutionChamber', 'RoachWarren', 'Spire',
                 'Hive', 'LurkerDen', 'HydraliskDen', 'InfestationPit', 'ExtractorRich',
                 'NydusNetwork', 'GreaterSpire')

    def __init__(self, player_name):
        self.player_name = player_name
        self.units = defaultdict(set)
        self.data = [] # data of interest extracted from sc2reader events

    # counting units is common, let's handle it in the base class

    def remove_unit(self, id, key):
        if key in Tracker.UNHANDLED:
            return
        if id not in self.units[key]:
            print(key)
        assert id in self.units[key]
        self.units[key].remove(id)

    def add_unit(self, id, key):
        if key in Tracker.UNHANDLED:
            return
        assert id not in self.units[key]
        if key not in self.units:
            self.units[key] = set()
        self.units[key].add(id)
