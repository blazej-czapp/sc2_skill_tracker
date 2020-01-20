import matplotlib.patches as mpatches
import numpy as np

from .Tracker import Tracker
from matplotlib.ticker import FuncFormatter
from replay_helpers import Entity, timestamp, real_seconds
from sc2reader.events import PlayerStatsEvent, UnitTypeChangeEvent, UnitBornEvent, UnitDiedEvent

class LarvaeVsResourcesTracker(Tracker):
    # larve and drones at the start of the game are 'born' just like any subsequent ones

    def __init__(self, player_name):
        Tracker.__init__(self, player_name)

    def consume_event(self, event):
        if isinstance(event, PlayerStatsEvent) and event.player.name.startswith(self.player_name):
            # Using PlayerStatsEvent as clock - could be more principled but it's good enough.
            # Loggin events alone means they are spread unevenly in time so graphs end up warped
            # (they are plotted as if events were uniformly distributed in time i.e. by event index)
            # Could either introduce a separate clock or use event time when plotting x-axis

            # including our counts alongside game's periodic stats
            self.data.append({
                              'supply_used' : int(event.food_used + 0.5),
                              'supply_cap' : int(event.food_made),
                              'time' : event.second,
                              'minerals' : event.minerals_current,
                              'gas' : event.vespene_current,
                              'larvae' : len(self.units[Entity.LARVA])
                             })

        elif isinstance(event, UnitTypeChangeEvent) and event.unit.owner.name.startswith(self.player_name):
            # this seems to happen once the egg hatches - it changes type back to larva
            # and the larva then immediately dies but let's treat it as a new larva
            # here, we'll subtract it again in unit died event
            if str(event.unit_type_name).startswith(Entity.LARVA):
                unit_id = event.unit.id
                assert event.unit.id == event.unit_id
                # assuming only eggs can change into larva (assert within)
                self.remove_unit(unit_id, Entity.EGG)
                self.add_unit(unit_id, Entity.LARVA)
            # sometimes eggs change into eggs, don't know what it means - ignoring those events
            elif str(event.unit_type_name).startswith(Entity.EGG) and not event.unit.name.startswith(Entity.EGG):
                unit_id = event.unit.id
                assert event.unit.id == event.unit_id
                # assuming only larva can change into egg (assert within)
                self.remove_unit(unit_id, Entity.LARVA)
                self.add_unit(unit_id, Entity.EGG)
        elif isinstance(event, UnitBornEvent) and event.unit.owner is not None and event.unit.owner.name.startswith(self.player_name):
            # print(event.unit.owner.name)
            self.add_unit(event.unit.id, event.unit.name)
        elif isinstance(event, UnitDiedEvent) and event.unit.owner is not None and event.unit.owner.name.startswith(self.player_name):
            self.remove_unit(event.unit.id, event.unit.name)

    def plot(self, axes):
        # has to be contiguous, otherwise bars are separated and thin (i.e. one bar per 10 "seconds")
        x_axis = np.arange(len(self.data))

        def x_to_timestamp(x, pos):
            if x >= 0 and x < len(self.data):
                return timestamp(real_seconds(self.data[int(x)]['time']))

        axes.xaxis.set_major_formatter(FuncFormatter(x_to_timestamp))

        mineral_history = [event['minerals'] for event in self.data]
        mineral_plot = axes.bar(x_axis, mineral_history, color='xkcd:sky blue', label='minerals')
        gas_plot = axes.bar(x_axis, [event['gas'] for event in self.data], bottom=mineral_history, color='xkcd:spring green', label='gas')
        larvae_plot, = axes.twinx().plot(x_axis, [event['larvae'] for event in self.data], color='tab:red', label='larvae')

        # shade the periods the player is supply blocked (has less than 2 supply available)
        for i, event in enumerate(self.data):
            if i == 0:
                continue
            if event['supply_cap'] < 200 and event['supply_cap'] - event['supply_used'] < 2:
                axes.axvspan(i-1, i, color='r', alpha=0.1, lw=0)

        supply_legend = mpatches.Patch(color='red', alpha=0.1, label='available supply < 2')

        axes.legend(handles=[mineral_plot, gas_plot, larvae_plot, supply_legend], loc='upper left')
