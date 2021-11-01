import os
import sys

import numpy as np
import torch
import maps.map_analysis as MapAnalysis
from MoveHelper import MoveHelper
from UnitInfo import UnitInfo

path = '/kaggle_simulations/agent' if os.path.exists('/kaggle_simulations') else '.'
model = torch.jit.load(f'{path}/model.pth')
model.eval()


def pr(*args, sep=' ', end='\n', f=False):  # known special case of print
    if True:
        print(*args, sep=sep, file=sys.stderr)
    elif f:
        print(*args, sep=sep, file=sys.stderr)


def prx(*args): pr(*args, f=True)

def in_city(pos, game_state):
    try:
        city = game_state.map.get_cell_by_pos(pos).citytile
        return city is not None and city.team == game_state.id
    except:
        return False

unit_actions = [('move', 'n'), ('move', 's'), ('move', 'w'), ('move', 'e'), ('build_city',)]



class ML_Agent:
    def __init__(self):
        self.include_coal = False
        self.include_uranium = False

    def update_include_resources(self, t_prefix, include_coal, include_uranium):
        # only switches from False to True (no way back)
        if (not self.include_coal) and include_coal:
            pr(t_prefix,"ML Agent changing include_coal to",include_coal)
            self.include_coal = include_coal
        if (not self.include_uranium) and include_uranium:
            pr(t_prefix,"ML Agent changing include_uranium to", include_uranium)
            self.include_uranium = include_uranium

    def make_input(self, obs, unit_id):
        width, height = obs['width'], obs['height']
        x_shift = (32 - width) // 2
        y_shift = (32 - height) // 2
        cities = {}

        b = np.zeros((20, 32, 32), dtype=np.float32)

        for update in obs['updates']:
            strs = update.split(' ')
            input_identifier = strs[0]

            if input_identifier == 'u':
                x = int(strs[4]) + x_shift
                y = int(strs[5]) + y_shift
                wood = int(strs[7])
                coal = int(strs[8])
                uranium = int(strs[9])
                if unit_id == strs[3]:
                    # Position and Cargo
                    b[:2, x, y] = (
                        1,
                        (wood + coal + uranium) / 100
                    )
                else:
                    # Units
                    team = int(strs[2])
                    cooldown = float(strs[6])
                    idx = 2 + (team - obs['player']) % 2 * 3
                    b[idx:idx + 3, x, y] = (
                        1,
                        cooldown / 6,
                        (wood + coal + uranium) / 100
                    )
            elif input_identifier == 'ct':
                # CityTiles
                team = int(strs[1])
                city_id = strs[2]
                x = int(strs[3]) + x_shift
                y = int(strs[4]) + y_shift
                idx = 8 + (team - obs['player']) % 2 * 2
                b[idx:idx + 2, x, y] = (
                    1,
                    cities[city_id]
                )
            elif input_identifier == 'r':
                # Resources
                r_type = strs[1]
                if (r_type == 'coal' and not self.include_coal) \
                        or (r_type == 'uranium' and not self.include_uranium):
                    continue
                x = int(strs[2]) + x_shift
                y = int(strs[3]) + y_shift
                amt = int(float(strs[4]))
                b[{'wood': 12, 'coal': 13, 'uranium': 14}[r_type], x, y] = amt / 800
                # pr("ML XXX res:", obs['step'], r_type, x, y, amt)
            elif input_identifier == 'rp':
                # Research Points
                team = int(strs[1])
                rp = int(strs[2])
                b[15 + (team - obs['player']) % 2, :] = min(rp, 200) / 200
            elif input_identifier == 'c':
                # Cities
                city_id = strs[2]
                fuel = float(strs[3])
                lightupkeep = float(strs[4])
                cities[city_id] = min(fuel / lightupkeep, 10) / 10

        # Day/Night Cycle
        b[17, :] = obs['step'] % 40 / 40
        # Turns
        b[18, :] = obs['step'] / 360
        # Map Size
        b[19, x_shift:32 - x_shift, y_shift:32 - y_shift] = 1

        return b

    def get_actions_unit(self, observation, game_state, actions: [], move_mapper: MoveHelper, unit_info, resources) -> []:
        player = game_state.players[observation.player]

        # Worker Actions
        destinations = []

        for unit in player.units:
            if not unit.can_act():
                destinations.append(unit.pos)

        for unit in player.units:
            if unit.can_build(game_state.map) and unit.can_act():
                self.get_action_unit(observation, game_state, unit_info[unit.id], move_mapper, actions, resources)

        for unit in player.units:
            if (not unit.can_build(game_state.map)) and unit.can_act():
                self.get_action_unit(observation, game_state, unit_info[unit.id], move_mapper, actions, resources)


    def call_func(obj, method, args=[]):
        return getattr(obj, method)(*args)



    def get_action_unit(self, observation, game_state, info: UnitInfo,
                        move_mapper: MoveHelper, actions: [],
                        resources,
                        can_build=True,
                        stay_in_case_no_found=True) \
            -> bool:
        unit = info.unit

        is_day = game_state.turn % 40 < 30
        is_night = not is_day

        # ML magic
        policy = self.get_policy(observation, unit)

        # check in order of attractiveness
        for label in np.argsort(policy)[::-1]:
            act = unit_actions[label]
            type_action = act[0]
            pos = unit.pos.translate(act[-1], 1) or unit.pos
            if type_action == 'move' and move_mapper.can_move_to_pos(pos, game_state):
                if is_day or not in_city(unit.pos, game_state):
                    move_mapper.move_unit_to_pos(actions, info, 'ML', pos)
                    return True
                elif is_night and in_city(unit.pos, game_state):
                    # night, in the city
                    if in_city(pos, game_state):
                        # move to another city, ok
                        move_mapper.move_unit_to_pos(actions, info, 'ML', pos)
                        return True
                    else:
                        in_resource, near_resource = MapAnalysis.is_position_in_X_adjacent_to_resource(
                            resources.available_resources_tiles, pos)
                        if near_resource:
                            # move to near_resource, also ok
                            move_mapper.move_unit_to_pos(actions, info, 'ML', pos)
                            return True
            elif can_build and type_action == 'build_city':
                if is_day:
                    move_mapper.build_city(actions, info, 'ML')
                    return True

        if stay_in_case_no_found:
            move_mapper.stay(unit, 'ML')
        return False


    def get_movement_directions(self, observation, info: UnitInfo):
        directions = []
        # ML magic
        policy = self.get_policy(observation, info.unit)
        for label in np.argsort(policy)[::-1]:
            act = unit_actions[label]
            type_action = act[0]
            if type_action == 'move':
                directions.append(act[-1])

        return directions


    def get_policy(self, observation, unit):
        state = self.make_input(observation, unit.id)
        with torch.no_grad():
            p = model(torch.from_numpy(state).unsqueeze(0))
        policy = p.squeeze(0).numpy()
        return policy
