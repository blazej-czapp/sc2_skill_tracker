"""Inject tracking is approximate - it tracks inject commands issued, not actual incjets. If a queen
  was diverted (or killed), the inject will still be counted. If a queen has to walk, timing will be off.
"""

import matplotlib.patches as mpatches

from matplotlib.ticker import FuncFormatter
from ..replay_helpers import Entity, timestamp, real_seconds
from sc2reader.events.tracker import UnitBornEvent, UnitDoneEvent, UnitDiedEvent
from sc2reader.events.game import TargetUnitCommandEvent, PlayerLeaveEvent


def earliest_possible_inject(hatch_creation, first_queen_creation, hatch_cutoff):
    if first_queen_creation is None or first_queen_creation > hatch_cutoff:
        return None

    return max(hatch_creation, first_queen_creation)


def no_queen_period(hatch_creation, hatch_cutoff, first_queen_creation):
    """Compute the duration of the overlap of the period (start_of_game; first_queen_creation) and
    (hatch_creation; hatch_cutoff).
    Hatch creation is implicitly the start of the overlap, so only return duration.

    Arguments:
        first_queen_creation: may be None
    """
    if first_queen_creation is None:
        return hatch_cutoff - hatch_creation
    else:
        return min(hatch_cutoff, first_queen_creation) - min(hatch_creation, first_queen_creation)


def missed_injects(injects, first_queen_creation, hatch_creation, hatch_cutoff):
    """
    Arguments:
        injects: list of (start, end) pairs, clamped to hatch_cutoff
    Returns:
        pairs (start, end) of missed inject periods
    """
    earliest_possible = earliest_possible_inject(hatch_creation, first_queen_creation, hatch_cutoff)
    if earliest_possible is None:
        return []

    missed = []
    if injects:
        # idle time from earliest_possible_inject until first inject (must be >= 0, inject must happen after a queen
        # is born)
        missed.append((earliest_possible, injects[0][0]))

        # idle time from last inject until game end or death
        missed.append((injects[-1][1], hatch_cutoff))
    else:
        # never injected - plot idle time from earliest possible inject (hatch_creation or queen born) until hatch_cutoff
        # watch out in case hatchery died before the first queen was born
        if first_queen_creation is not None:
            missed.append((max(first_queen_creation, hatch_creation), hatch_cutoff))
        # no missed injects if there was never any queen

    if len(injects) > 1:
        # idle time between injects
        missed += [(injects[i-1][1], injects[i][0]) for i in range(1, len(injects))]

    return missed


class InjectTracker(object):
    INJECT_TIME = 40 # in game seconds, according to https://github.com/dsjoerg/ggpyjobs/blob/master/sc2parse/plugins.py

    def __init__(self, player_name):
        self.player_name = player_name
        self.first_queen_time = None
        self.hatchery_history = {}
        self.title = "Injects"

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

        elif isinstance(event, UnitBornEvent) \
             and event.unit.name == "Queen" \
             and event.unit.owner.name.startswith(self.player_name) \
             and self.first_queen_time is None:
            self.first_queen_time = event.second


    def inject_history(self, hatchery_index, cutoff_time):
        sorted_hatcheries = sorted(self.hatchery_history.values(), key=lambda value: value['created'])

        hatchery = sorted_hatcheries[hatchery_index]
        injects = hatchery['injects']
        hatch_creation = hatchery['created']

        # we should not have consumed events past the requested cutoff_time point
        assert(hatch_creation <= cutoff_time)
        assert(hatchery['destroyed'] is None or hatchery['destroyed'] <= cutoff_time)

        hatch_cutoff = cutoff_time if hatchery['destroyed'] is None else hatchery['destroyed']

        # clamp inject intervals to cutoff time or hatchery death - late or stacked injects could
        # be computed to finish after the cutoff or even game end
        clamped_injects = [(interval[0], min(hatch_cutoff, interval[1])) for interval in injects if interval[0] < hatch_cutoff]

        # don't count time before the first queen is born as missed inject time
        inject_possible_time = earliest_possible_inject(hatch_creation, self.first_queen_time, hatch_cutoff)
        if inject_possible_time is None or hatch_cutoff - inject_possible_time == 0:
            proportion_injected = 0
        else:
            total_injected = sum([interval[1] - interval[0] for interval in clamped_injects])
            proportion_injected = total_injected / (hatch_cutoff - inject_possible_time)

        return {'injects' : clamped_injects,
                'proportion_injected': proportion_injected, # for convenience - could be inferred from others (mostly)
                'hatch_creation': hatch_creation,
                'hatch_cutoff': hatch_cutoff} # death or cutoff_time, whichever is earlier


    def plot(self, axes, cutoff_time):
        """ cutoff_time - end time for the plot x-axis (so that all plots are aligned)
        """
        def x_to_timestamp(x, pos):
            if x >= 0:
                return timestamp(real_seconds(x))

        axes.xaxis.set_major_formatter(FuncFormatter(x_to_timestamp))
        axes.set_xlim(right=cutoff_time, auto=True)

        proportion_injected = []
        # plot hatcheries sorted by hatch_creation time
        for hatch_index in range(len(self.hatchery_history)):
            history = self.inject_history(hatch_index, cutoff_time)

            # plot all injected intervals
            axes.broken_barh([(interval[0], interval[1]-interval[0]) for interval in history['injects']],
                             (5*hatch_index, 2), facecolors='tab:green', alpha=0.9)

            # outside of injected intervals, we need to plot times when the hatchery existed but:
            #  1. first queen wasn't born yet (when injects were not possible) - greyed out "no inject possible" period
            #  2. queens (had) existed, but hatchery wasn't injected - red "missed inject" periods

            # greyed-out time from hatch_creation until the first queen is born
            # if hatch_creation is after the first queen, no_queen will be zero so nothing should be plotted
            no_queen = no_queen_period(history['hatch_creation'], history['hatch_cutoff'], self.first_queen_time)
            axes.broken_barh([(history['hatch_creation'], no_queen)], (5*hatch_index, 2), facecolors='tab:grey', alpha=0.75)

            missed = missed_injects(history['injects'], self.first_queen_time, history['hatch_creation'], history['hatch_cutoff'])
            axes.broken_barh([(m[0], m[1] - m[0]) for m in missed], (5*hatch_index, 2), facecolors='tab:red', alpha=0.75)

            proportion_injected.append(history['proportion_injected'])

        axes.set_yticks([5*i+1 for i in range(len(proportion_injected))])
        axes.set_yticklabels([f"{p*100:.0f}%" for p in proportion_injected])

        idle_legend = mpatches.Patch(color='tab:red', label='idle', alpha=0.75)
        injected_legend = mpatches.Patch(color='tab:green', label='injected', alpha=0.9)
        no_queen_legend = mpatches.Patch(color='tab:grey', label='no queen', alpha=0.9)

        axes.legend(handles=[injected_legend, idle_legend, no_queen_legend], loc='upper left')
