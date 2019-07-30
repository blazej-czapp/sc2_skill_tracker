import sys
import sc2reader
from sc2reader.events import PlayerStatsEvent, UnitTypeChangeEvent, UnitBornEvent, UnitDiedEvent

import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict

def timestamp(game_seconds):
    real_seconds = game_seconds / float(1.4) # convert from faster to wall clock
    return "%02.i:%02.i" % (int(real_seconds / 60), int(real_seconds % 60))

class Tracker(object):
    LARVA = 'Larva'
    DRONE = 'Drone'
    EGG = 'Egg'
    # these show up in some replays, we don't handle them yet and they don't behave the same as regular units so things break
    UNHANDLED = ('Hatchery', 'Extractor', 'SporeCrawler', 'SpawningPool', 'CreepTumorBurrowed', 'SpineCrawler', 'CreepTumor', 'CreepTumorQueen')

    def __init__(self):
        # larve and drones at the start of the game are 'born' just like any subsequent ones
        self.units = defaultdict(set)
        # self.odd_ones = set()

    def remove_unit(self, id, key):
        if key in Tracker.UNHANDLED:
            return
        # if id not in self.units[key]:
        #     self.odd_ones.add(key)
        #     return
        assert id in self.units[key]
        self.units[key].remove(id)

    def add_unit(self, id, key):
        if key in Tracker.UNHANDLED:
            return
        assert id not in self.units[key]
        if key not in self.units:
            self.units[key] = set()
        self.units[key].add(id)

    def events(self, filename):
        ME = 'orastem'

        rep = sc2reader.load_replay(filename)
        rep.load_tracker_events()

        res = []
        for event in rep.tracker_events:
            # print event
            if isinstance(event, PlayerStatsEvent) and event.player.name.startswith(ME):

                # smuggling in our counts alongside game's periodic stats
                res.append({'time' : event.second,
                            'minerals' : event.minerals_current,
                            'gas' : event.vespene_current,
                            'supply_used' : int(event.food_used + 0.5),
                            'supply_cap' : int(event.food_made),
                            'larvae' : len(self.units[Tracker.LARVA]),
                            'drones' : len(self.units[Tracker.DRONE])})
            elif isinstance(event, UnitTypeChangeEvent) and event.unit.owner.name.startswith(ME):
                # this seems to happen once the egg hatches - it changes type back to larva
                # and the larva then immediately dies but let's treat it as a new larva
                # here, we'll subtract it again in unit died event
                if str(event.unit_type_name).startswith(Tracker.LARVA):
                    unit_id = event.unit.id
                    assert event.unit.id == event.unit_id
                    # assuming only eggs can change into larva (assert within)
                    self.remove_unit(unit_id, Tracker.EGG)
                    self.add_unit(unit_id, Tracker.LARVA)
                # sometimes eggs change into eggs, don't know what it means - ignoring those events
                elif str(event.unit_type_name).startswith(Tracker.EGG) and not event.unit.name.startswith(Tracker.EGG):
                    unit_id = event.unit.id
                    assert event.unit.id == event.unit_id
                    # assuming only larva can change into egg (assert within)
                    self.remove_unit(unit_id, Tracker.LARVA)
                    self.add_unit(unit_id, Tracker.EGG)
            elif isinstance(event, UnitBornEvent) and event.unit.owner is not None and event.unit.owner.name.startswith(ME):
                self.add_unit(event.unit.id, event.unit.name)
            elif isinstance(event, UnitDiedEvent) and event.unit.owner is not None and event.unit.owner.name.startswith(ME):
                self.remove_unit(event.unit.id, event.unit.name)
            elif hasattr(event, 'unit') and event.unit.id == 124780557:
                print event

        return res


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("usage: %s filename.SC2replay" % sys.argv[0])

    t = Tracker()
    data = t.events(sys.argv[1])

    # print t.odd_ones

    mineral_history = [event['minerals'] for event in data]

    fig, ax1 = plt.subplots(2, 1)

    mineral_plot = ax1[0].bar(np.arange(len(data)), mineral_history, color='xkcd:sky blue')
    gas_plot = ax1[0].bar(np.arange(len(data)), [event['gas'] for event in data], bottom=mineral_history, color='xkcd:spring green')
    larvae_plot, = ax1[0].twinx().plot(np.arange(len(data)), [event['larvae'] for event in data], color='tab:red', label='larvae')
    plt.legend(handles=[larvae_plot])
    
    drone_plot, = ax1[1].twinx().plot(np.arange(len(data)), [event['drones'] for event in data], color='tab:red', label='drones')
    plt.legend(handles=[drone_plot])

    plt.show()
