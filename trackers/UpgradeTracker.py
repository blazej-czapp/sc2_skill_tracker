import numpy as np

from matplotlib.ticker import FuncFormatter
from ..replay_helpers import Entity, timestamp, real_seconds

from sc2reader.events import UpgradeCompleteEvent
from .DroneTracker import DroneTracker

#                            sc2reader name            display name
UPGRADES_OF_INTEREST = {'ZergMissileWeaponsLevel1' : 'Ground Range 1',
                        'ZergMissileWeaponsLevel2' : 'Ground Range 2',
                        'ZergMissileWeaponsLevel3' : 'Ground Range 3',
                        'ZergMeleeWeaponsLevel1'   : 'Melee 1',
                        'ZergMeleeWeaponsLevel2'   : 'Melee 2',
                        'ZergMeleeWeaponsLevel3'   : 'Melee 3',
                        'ZergGroundArmorsLevel1'   : 'Ground Carapace 1',
                        'ZergGroundArmorsLevel2'   : 'Ground Carapace 2',
                        'ZergGroundArmorsLevel3'   : 'Ground Carapace 3',
                        'ZergFlyerWeaponsLevel1'   : 'Air Attack 1',
                        'ZergFlyerWeaponsLevel2'   : 'Air Attack 2',
                        'ZergFlyerWeaponsLevel3'   : 'Air Attack 3',
                        'ZergFlyerArmorsLevel1'    : 'Air Carapace 1',
                        'ZergFlyerArmorsLevel2'    : 'Air Carapace 2',
                        'ZergFlyerArmorsLevel3'    : 'Air Carapace 3'}

class UpgradeTracker(object):
    def __init__(self, player_name):
        self.player_name = player_name
        self.upgrades = []


    def consume_event(self, event):
        if (isinstance(event, UpgradeCompleteEvent)
            and event.player.name.startswith(self.player_name)
            and event.upgrade_type_name in UPGRADES_OF_INTEREST):
            self.upgrades.append({'time' : event.second,
                                  'name' : event.upgrade_type_name})


    def plot(self, axes, cutoff_time):
        """ :param cutoff_time: end time for the plot x-axis (so that all plots are aligned)
        """
        # we should not have consumed events past the requested cutoff_time point
        assert(len(self.upgrades) == 0 or self.upgrades[-1]['time'] <= cutoff_time)

        for upgrade in self.upgrades:
            axes.axvline(x=upgrade['time'])
            axes.text(upgrade['time'] + 1, 1, UPGRADES_OF_INTEREST[upgrade['name']], rotation=90, va='bottom')


    def can_share_plot_with(self, tracker):
        return isinstance(tracker, DroneTracker)
