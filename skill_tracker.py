import sys
import sc2reader
from sc2reader.events import PlayerStatsEvent, UnitTypeChangeEvent, UnitBornEvent, UnitDiedEvent

import numpy as np
import matplotlib.pyplot as plt

def timestamp(game_seconds):
	real_seconds = game_seconds / float(1.4)
	return "%02.i:%02.i" % (int(real_seconds / 60), int(real_seconds % 60))

def events(filename):
	ME = 'orastem'

	rep = sc2reader.load_replay(filename)
	rep.load_tracker_events()

	eggs = set()
	larvae = set() # larve at the start of the game are 'born' just like any subsequent ones

	res = []
	for event in rep.tracker_events:
		if isinstance(event, PlayerStatsEvent) and event.player.name.startswith(ME):
			# print timestamp(event.second), ':', 'minerals:', event.minerals_current, 'gas:', event.vespene_current, 'larvae:', len(larvae), 'supply:', int(event.food_used + 0.5), '/', int(event.food_made)
			res.append({'time' : event.second, 'larvae' : len(larvae),
				        'minerals' : event.minerals_current,
				        'gas' : event.vespene_current,
				        'supply_used' : int(event.food_used + 0.5),
				        'supply_cap' : int(event.food_made)})
		elif isinstance(event, UnitTypeChangeEvent) and event.unit.owner.name.startswith(ME):
			# print event, event.unit_type_name

			# this seems to happen once the egg hatches - it changes back to larva
			# and the larva then immediately dies but let's treat it as a new larva
			# here, we'll subtract it again in unit died event
			if str(event.unit_type_name).startswith("Larva"):
				unit_id = event.unit.id
				assert event.unit.id == event.unit_id
				assert unit_id in eggs
				eggs.remove(unit_id)
				larvae.add(unit_id)
			if str(event.unit_type_name).startswith("Egg"):
				unit_id = event.unit.id
				assert event.unit.id == event.unit_id
				assert unit_id in larvae
				eggs.add(unit_id)
				larvae.remove(unit_id)
		elif isinstance(event, UnitBornEvent) and event.unit.owner is not None and event.unit.owner.name.startswith(ME) and event.unit_type_name.startswith("Larva"):
			assert event.unit.id not in larvae
			larvae.add(event.unit.id)
			# print event
		elif isinstance(event, UnitDiedEvent) and event.unit.owner is not None and event.unit.owner.name.startswith(ME) and event.unit.name.startswith("Larva"):
			assert event.unit.id in larvae
			larvae.remove(event.unit.id)
			# print event

	return res


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("usage: %s filename.SC2replay" % sys.argv[0])
    else:
        print(sys.argv[1])
        data = events(sys.argv[1])

        mineral_history = [event['minerals'] for event in data]


        fig, ax1 = plt.subplots()

        mineral_plot = ax1.bar(np.arange(len(data)), mineral_history, color='xkcd:sky blue')
        gas_plot = ax1.bar(np.arange(len(data)), [event['gas'] for event in data], bottom=mineral_history, color='xkcd:spring green')
        larvae_plot = ax1.twinx().plot(np.arange(len(data)), [event['larvae'] for event in data], color='tab:red')

        plt.show()