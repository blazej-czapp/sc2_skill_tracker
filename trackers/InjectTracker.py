import matplotlib.patches as mpatches

from .Tracker import Tracker
from matplotlib.ticker import FuncFormatter
from replay_helpers import Entity, timestamp, real_seconds
from sc2reader.events.tracker import UnitBornEvent, UnitDoneEvent
from sc2reader.events.game import TargetUnitCommandEvent, PlayerLeaveEvent

class InjectTracker(Tracker):
    INJECT_TIME = 40 # in game seconds, according to https://github.com/dsjoerg/ggpyjobs/blob/master/sc2parse/plugins.py

    def __init__(self, player_name):
        Tracker.__init__(self, player_name)
        self.hatchery_ids = [] # to store order and time of creation
        self.hatchery_injects = {} # list of tuples of (inject_start, inject_end)

    def consume_event(self, event):
        # the initial hatchery is "born", subsequent ones are "done"
        # TODO handle hatcheries dying (truncate their inject time)
        if isinstance(event, UnitBornEvent) \
           and event.unit.owner is not None \
           and event.unit.owner.name.startswith(self.player_name) \
           and (event.unit.name == "Hatchery" or event.unit.name == "Lair" or event.unit.name == "Hive"):
            self.hatchery_ids.append((event.unit_id, event.second))
            self.hatchery_injects[event.unit_id] = []

        elif isinstance(event, UnitDoneEvent) \
             and event.unit.owner is not None \
             and event.unit.owner.name.startswith(self.player_name) \
             and (event.unit.name == "Hatchery" or event.unit.name == "Lair" or event.unit.name == "Hive"):
            self.hatchery_ids.append((event.unit_id, event.second))
            self.hatchery_injects[event.unit_id] = []

        elif type(event) == TargetUnitCommandEvent \
             and hasattr(event, "ability") \
             and event.ability_name == "SpawnLarva":
            # TODO using isinstance() gives false positives on some Right Click events - fix in sc2reader?
            inject_intervals = self.hatchery_injects[event.target_unit_id]
            if inject_intervals and event.second < inject_intervals[-1][1]:
                # queueing inject, starts after the latest one finishes (may be queued itself)
                current_inject_end = inject_intervals[-1][1]
                inject_intervals.append((current_inject_end, current_inject_end+InjectTracker.INJECT_TIME))
            else:
                # fresh inject, starts now
                # XXX if the queen has to travel, this will be inaccurate; the total time should
                #     be right, though - the idle time will just be shifted from before to after the inject
                inject_intervals.append((event.second, event.second+InjectTracker.INJECT_TIME))
        elif isinstance(event, PlayerLeaveEvent):
            self.game_end = event.second

    def plot(self, axes):
        def x_to_timestamp(x, pos):
            if x >= 0:
                return timestamp(real_seconds(x))

        axes.xaxis.set_major_formatter(FuncFormatter(x_to_timestamp))

        h = 1
        for (hatch, creation) in self.hatchery_ids:
            injects = self.hatchery_injects[hatch]

            # all injected intervals
            axes.broken_barh([(interval[0], interval[1]-interval[0]) for interval in injects], (5*h, 2), facecolors='tab:green', alpha=0.9)

            if injects:
                # idle time from creation until first inject
                axes.broken_barh([(creation, injects[0][0] - creation)], (5*h, 2), facecolors='tab:red', alpha=0.75)
                # idle time from last inject until game end
                axes.broken_barh([(injects[-1][1], self.game_end-injects[-1][1])], (5*h, 2), facecolors='tab:red', alpha=0.75)
            else:
                # never injected - plot idle time from creation until game end
                axes.broken_barh([(creation, self.game_end-creation)], (5*h, 2), facecolors='tab:red', alpha=0.75)

            if len(injects) > 1:
                # idle time between injects
                axes.broken_barh([(injects[i-1][1], injects[i][0]-injects[i-1][1]) for i in range(1, len(injects))], (5 * h, 2), facecolors='tab:red', alpha=0.75)
            h += 1

        idle_legend = mpatches.Patch(color='tab:red', label='idle', alpha=0.75)
        injected_legend = mpatches.Patch(color='tab:green', label='injected', alpha=0.9)

        axes.set_yticks([5*i+1 for i in range(1, h+1)])
        axes.set_yticklabels(['Hatch %d' % i for i in range(1, len(self.hatchery_ids)+1)])
        
        axes.legend(handles=[injected_legend, idle_legend], loc='upper left')
