import matplotlib.patches as mpatches

from .Tracker import Tracker
from matplotlib.ticker import FuncFormatter
from replay_helpers import Entity, timestamp, real_seconds
from sc2reader.events.tracker import UnitBornEvent, UnitDoneEvent, UnitDiedEvent
from sc2reader.events.game import TargetUnitCommandEvent, PlayerLeaveEvent

print(
"""NOTE:
  Inject tracking is approximate, it tracks inject commands issued, not actual incjets. If a queen
  was diverted, the inject will still be counted. If a queen has to walk, timing will be off.
  Treat it more like "inject intention".
""")

class InjectTracker(Tracker):
    INJECT_TIME = 40 # in game seconds, according to https://github.com/dsjoerg/ggpyjobs/blob/master/sc2parse/plugins.py

    def __init__(self, player_name):
        Tracker.__init__(self, player_name)
        self.first_queen_time = None
        self.hatchery_history = {}

    def consume_event(self, event):
        # the initial hatchery is "born", subsequent ones are "done"
        # As a Hatchery becomes a Lair and Hive, its ID doesn't change so events can show e.g. a Hive
        # right at the start of the game.
        if isinstance(event, UnitBornEvent) \
           and event.unit.owner is not None \
           and event.unit.owner.name.startswith(self.player_name) \
           and (event.unit.name == "Hatchery" or event.unit.name == "Lair" or event.unit.name == "Hive"):
            self.hatchery_history[event.unit_id] = {'injects': [], 'created': event.second, 'destroyed': None}

        elif isinstance(event, UnitDoneEvent) \
             and event.unit.owner is not None \
             and event.unit.owner.name.startswith(self.player_name) \
             and (event.unit.name == "Hatchery" or event.unit.name == "Lair" or event.unit.name == "Hive"):
            self.hatchery_history[event.unit_id] = {'injects': [], 'created': event.second, 'destroyed': None}

        elif isinstance(event, UnitDiedEvent) \
             and event.unit.owner is not None \
             and event.unit.owner.name.startswith(self.player_name) \
             and (event.unit.name == "Hatchery" or event.unit.name == "Lair" or event.unit.name == "Hive"):
            try:
                self.hatchery_history[event.unit_id]['destroyed'] = event.second
            except KeyError:
                # if the hatchery never finished, we don't record its death
                pass

        elif isinstance(event, TargetUnitCommandEvent) \
             and event.player.name is not None \
             and event.player.name.startswith(self.player_name) \
             and hasattr(event, "ability") \
             and event.ability_name == "SpawnLarva" \
             and event.target_unit_id in self.hatchery_history:

            inject_intervals = self.hatchery_history[event.target_unit_id]['injects']

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

        elif isinstance(event, UnitBornEvent) \
             and event.unit.name == "Queen" \
             and event.unit.owner.name.startswith(self.player_name) \
             and self.first_queen_time is None:
            self.first_queen_time = event.second

    def plot(self, axes, cutoff):
        """
        cutoff: only plot until this time (in in-game seconds)
        """
        def x_to_timestamp(x, pos):
            if x >= 0:
                return timestamp(real_seconds(x))

        axes.xaxis.set_major_formatter(FuncFormatter(x_to_timestamp))

        h = 1
        # plot hatcheries sorted by creation time
        sorted_hatcheries = sorted(self.hatchery_history.items(), key=lambda item: item[1]['created'])
        percentage_injected = []
        for hatch in [item[1] for item in sorted_hatcheries]:
            injects = hatch['injects']
            creation = hatch['created']

            if cutoff is not None and creation >= cutoff:
              break # hatcheries sorted by creation so nothing else will qualify

            if cutoff is None:
              life_end = self.game_end if hatch['destroyed'] is None else hatch['destroyed']
            else:
              life_end = min(cutoff, self.game_end) if hatch['destroyed'] is None else min(cutoff, hatch['destroyed'])

            # clamp all intervals to game-duration/cutoff or hatchery life time
            injects = [(min(life_end, interval[0]), min(life_end, interval[1])) for interval in injects]

            # all injected intervals
            for interval in injects:
                axes.broken_barh([(interval[0], interval[1]-interval[0]) for interval in injects], (5*h, 2), facecolors='tab:green', alpha=0.9)

            no_queen_time = max(0, min(life_end, self.first_queen_time) - creation)
            # greyed-out time from creation until the first queen is born (and earliest inject is possible)
            # if creation is after the first queen, no_queen_time will be zero so nothing should be plotted
            axes.broken_barh([(creation, no_queen_time)], (5*h, 2), facecolors='tab:grey', alpha=0.75)

            earliest_possible_inject = max(creation, min(life_end, self.first_queen_time))

            if injects:
                # idle time from earliest_possible_inject until first inject (must be >= 0, inject must happen after a queen is born)
                axes.broken_barh([(earliest_possible_inject, injects[0][0] - earliest_possible_inject)], (5*h, 2), facecolors='tab:red', alpha=0.75)
                # idle time from last inject until game end or death
                axes.broken_barh([(injects[-1][1], life_end-injects[-1][1])], (5*h, 2), facecolors='tab:red', alpha=0.75)
            else:
                # never injected - plot idle time from earliest possible inject (creation or queen born) until destruction or game end
                # thresholding duration in case hatchery died before the first queen was born
                axes.broken_barh([(earliest_possible_inject, max(0, life_end-earliest_possible_inject))], (5*h, 2), facecolors='tab:red', alpha=0.75)

            if len(injects) > 1:
                # idle time between injects
                axes.broken_barh([(injects[i-1][1], injects[i][0]-injects[i-1][1]) for i in range(1, len(injects))], (5 * h, 2), facecolors='tab:red', alpha=0.75)

            total_injected = sum([interval[1] - interval[0] for interval in injects])
            percentage_injected.append(0 if total_injected == 0.0 else total_injected / (life_end - earliest_possible_inject) * 100)
            h += 1

        axes.set_yticks([5*i+1 for i in range(1, h+1)])
        axes.set_yticklabels(["%d%%" % p for p in percentage_injected])

        idle_legend = mpatches.Patch(color='tab:red', label='idle', alpha=0.75)
        injected_legend = mpatches.Patch(color='tab:green', label='injected', alpha=0.9)
        no_queen_legend = mpatches.Patch(color='tab:grey', label='no queen', alpha=0.9)
        
        axes.legend(handles=[injected_legend, idle_legend, no_queen_legend], loc='upper left')
