import numpy as np

from matplotlib.ticker import FuncFormatter
from ..replay_helpers import Entity, timestamp, real_seconds, game_seconds

from sc2reader.events import UnitBornEvent, UnitDiedEvent

# just a heuristic - the target is number of (real) minutes * 10 (interpolated)
def target_drone_count(time_axis):
    for time in time_axis:
        min_sec = [int(x) for x in timestamp(real_seconds(time)).split(':')]
        if min_sec[0] >= 8:
            yield 80
        elif real_seconds(time) < 133:
            # 13 drones at second 0 (including the one immediately queued) and it seems like
            # 22 drones are normally hit at 2:12 (real seconds)
            yield 13 + time/game_seconds(132) * 9
        else:
            yield min_sec[0] * 10 + (min_sec[1] / 60) * 10

class DroneTracker(object):
    def __init__(self, player_name):
        self.player_name = player_name
        self.drone_count = 0
        self.data = []
        self.title = "Drones"

    # larvae and drones at the start of the game are 'born' just like any subsequent ones

    def consume_event(self, event):
        # TODO when a drone morphs into a building, it 'dies' only once the building is complete (which makes sense,
        # the building can always be cancelled). But, its supply should be subtracted at the start of the morph,
        # which we don't do here (only once it dies). The event triggered at the start has type UnitInitEvent.
        if (isinstance(event, UnitBornEvent)
             and event.unit.owner is not None
             and event.unit.owner.name.startswith(self.player_name)
             and event.unit.name == Entity.DRONE):
            self.drone_count += 1
            self.data.append({'time' : event.second,
                              'drones' : self.drone_count})
        elif (isinstance(event, UnitDiedEvent)
             and event.unit.owner is not None
             and event.unit.owner.name.startswith(self.player_name)
             and event.unit.name == Entity.DRONE):
            self.drone_count -= 1
            self.data.append({'time' : event.second,
                              'drones' : self.drone_count})


    def plot(self, axes, cutoff_time):
        """ :param cutoff_time: end time for the plot x-axis (so that all plots are aligned)
        """
        def x_to_timestamp(x, pos):
            """ Converts time (in game seconds) into timestamp string (in real minutes and seconds)
                :param x: appears to be the position alongside respective Axis (could be y-axis)
                          IN DATA SPACE (i.e. interpolated from actual data, not pixel values);
                          can include some negative numbers if there's a margin
                :param pos: appears to be the index of tick being drawn (None otherwise
                            e.g. when moving mouse cursor around - x is still updated)
            """
            if x >= 0:
                return timestamp(real_seconds(x))

        axes.xaxis.set_major_formatter(FuncFormatter(x_to_timestamp))
        axes.set_xlim(right=cutoff_time, auto=True)

        actual_x_axis = [event['time'] for event in self.data]

        # we should not have consumed events past the requested cutoff_time point
        assert(self.data[-1]['time'] <= cutoff_time)

        # extend until the requested time so that all graphs align
        actual_x_axis.append(cutoff_time)

        # repeat last recorded drone count at plot end
        drone_plot, = axes.step(actual_x_axis, [event['drones'] for event in self.data] + [self.data[-1]['drones']], color='tab:red', label='drones actual')
        target_sub = axes.twinx() # Create a twin Axes sharing the xaxis

        # set the same limits so both graphs are scaled the same, i.e. we can visually
        # compare the actual and target drone counts
        target_sub.set_ylim(axes.get_ylim())

        # using denser x-axis data to get the inflection point exactly right, otherwise, if no drone was
        # built or killed at that moment, we won't plot it and the target plot will have too many segments
        target_x_axis = np.arange(cutoff_time)
        drone_target_plot, = target_sub.plot(target_x_axis, [x for x in target_drone_count(target_x_axis)], color='tab:blue', label='drones target')

        axes.legend(handles=[drone_plot, drone_target_plot], loc='upper left')
