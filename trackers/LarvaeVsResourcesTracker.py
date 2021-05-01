import matplotlib.patches as mpatches
import numpy as np

from matplotlib.ticker import FuncFormatter
from ..replay_helpers import Entity, timestamp, real_seconds
from sc2reader.events import PlayerStatsEvent, UnitTypeChangeEvent, UnitBornEvent, UnitDiedEvent

class LarvaeVsResourcesTracker(object):
    # larve and drones at the start of the game are 'born' just like any subsequent ones

    def __init__(self, player_name):
        self.player_name = player_name
        self.data = []
        self.larva_count = 0
        self.total_larvae = 0
        self.title = "Resources vs larvae"

    def consume_event(self, event):
        if isinstance(event, PlayerStatsEvent) and event.player.name.startswith(self.player_name):
            # including our counts alongside game's periodic stats
            self.data.append({
                              'supply_used' : int(event.food_used + 0.5),
                              'supply_cap' : int(event.food_made),
                              'time' : event.second,
                              'minerals' : event.minerals_current,
                              'gas' : event.vespene_current,
                              'larvae' : self.larva_count
                             })
        elif isinstance(event, UnitTypeChangeEvent) and event.unit.owner.name.startswith(self.player_name):
            # event.unit_type_name is what the unit changed into; event.unit is the unit itself;
            # Notionally, the unit referenced by 'event.unit' doesn't change with these events, but in case of
            # larva it can be a bit confusing. The chain of events when making a unit is:
            #  1. the larva unit changes type to Egg (but unit ID remains the same, event.unit will claim it's a Larva)
            #  2. when the unit hatches (or the egg is killed), the type changes back to Larva
            #  3. immediately after that, the larva unit dies
            #
            # I don't know if it's possible for a PlayerStatsEvent to occur between steps 2 and 3 - if so, it would
            # overcount the larvae by 1.
            if str(event.unit_type_name).startswith(Entity.LARVA):
                unit_id = event.unit.id
                assert event.unit.name == Entity.LARVA
                # presumably a unit just hatched - this larva should die immediately after this
                self.larva_count += 1
                self.total_larvae += 1
            # sometimes eggs change into eggs, don't know what it means - ignoring those events
            elif str(event.unit_type_name).startswith(Entity.EGG) and not event.unit.name.startswith(Entity.EGG):
                # assuming only larva can change into egg
                assert event.unit.name == Entity.LARVA
                self.larva_count -= 1
        elif (isinstance(event, UnitBornEvent)
                and event.unit.owner is not None
                and event.unit.owner.name.startswith(self.player_name)
                and str(event.unit.name).startswith(Entity.LARVA)):
            self.larva_count += 1
            self.total_larvae += 1
        elif (isinstance(event, UnitDiedEvent)
                and event.unit.owner is not None
                and event.unit.owner.name.startswith(self.player_name)
                and str(event.unit.name).startswith(Entity.LARVA)):
            self.larva_count -= 1

    def plot(self, axes, cutoff_time):
        """ cutoff_time - end time for the plot x-axis (so that all plots are aligned)
        """
        def x_to_timestamp(x, pos):
            if x >= 0 and x < len(self.data):
                return timestamp(real_seconds(self.data[int(x)]['time']))

        axes.xaxis.set_major_formatter(FuncFormatter(x_to_timestamp))
        # the bar plot doesn't use time for x, but ordinals of PlayerStatEvents (otherwise bars come out very thin and
        # far apart, i.e. one bar every 7 seconds, and nothing in between)
        # in the effort for all plots to have their x-axis timestamps aligned, we scale the number of data points up
        # fractionally, so that it corresponds to the same number of seconds as in the requested cutoff_time
        # it's not pixel-perfect, not sure why
        xmax = (cutoff_time / self.data[-1]['time']) * len(self.data)
        axes.set_xlim(right=xmax, auto=True)

        # we should not have consumed events past the requested cutoff_time point
        assert(self.data[-1]['time'] <= cutoff_time)
        x_axis = np.arange(len(self.data))

        mineral_history = [event['minerals'] for event in self.data]
        avg_unspent_minerals = int(sum(mineral_history) / len(self.data))
        mineral_plot = axes.bar(x_axis, mineral_history, color='xkcd:sky blue', label='minerals (avg. {:d})'.format(avg_unspent_minerals))

        gas_history = [event['gas'] for event in self.data]
        avg_unspent_gas = int(sum(gas_history) / len(self.data))
        gas_plot = axes.bar(x_axis, gas_history, bottom=mineral_history, color='xkcd:spring green', label='gas (avg. {:d})'.format(avg_unspent_gas))

        larvae_history = [event['larvae'] for event in self.data]
        avg_unspent_larvae = sum(larvae_history) / len(self.data)

        larvae_plot, = axes.twinx().plot(x_axis, larvae_history, color='tab:red', label='larvae (avg. {:.2f}, tot. {:d})'.format(avg_unspent_larvae, self.total_larvae))

        # shade the periods the player is supply blocked (has less than 2 supply available)
        # note that we're working with 10s granularity here (game-time), so the shaded regions are generally too wide
        # so we're not summing and printing them
        for i, event in enumerate(self.data):
            if i == 0:
                continue

            capped_cap = min(200, event['supply_cap'])
            if capped_cap - event['supply_used'] < 2:
                if capped_cap < 200:
                    axes.axvspan(i-1, i, color='red', alpha=0.1, lw=0)
                else:
                    axes.axvspan(i-1, i, color='blue', alpha=0.1, lw=0)

        supply_blocked_legend = mpatches.Patch(color='red', alpha=0.1, label='supply blocked')
        supply_capped_legend = mpatches.Patch(color='blue', alpha=0.1, label='supply capped')

        axes.legend(handles=[mineral_plot, gas_plot, larvae_plot, supply_blocked_legend, supply_capped_legend], loc='upper left')
