import os
import sys

import numpy as np
import torch
import maps.map_analysis as MapAnalysis
from MoveHelper import MoveHelper
from UnitInfo import UnitInfo
from LazyWrapper import LazyWrapper as Lazy

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

def distance(x1,y1,x2,y2) -> int:
    return abs(x1 - x2) + abs(y1 - y2)

unit_actions = [('move', 'n'), ('move', 's'), ('move', 'w'), ('move', 'e'),
                ('build_city',),
                ('transfer', 'n'), ('transfer', 's'), ('transfer', 'w'), ('transfer', 'e'),
                ('stay',)]

MAX_DAYS = 360
DAY_LENGTH = 30
NIGHT_LENGTH = 10

class ML_Agent:
    def __init__(self, model_name='model', model_map_size=32, model_type=1):
        self.include_coal = False
        self.include_uranium = False
        self.model_map_size = model_map_size
        self.model_type =  model_type

        path = '/kaggle_simulations/agent' if os.path.exists('/kaggle_simulations') else '.'
        self.model = torch.jit.load(f'{path}/{model_name}.pth')
        self.model.eval()

    def update_include_resources(self, t_prefix, include_coal, include_uranium):
        # only switches from False to True (no way back)
        if (not self.include_coal) and include_coal:
            pr(t_prefix, "ML Agent include_coal to", include_coal)
            self.include_coal = include_coal
        if (not self.include_uranium) and include_uranium:
            pr(t_prefix, "ML Agent include_uranium to", include_uranium)
            self.include_uranium = include_uranium

    # Input for Neural Network
    def make_input2(self, obs, unit, size=32):
        unit_id = unit.id
        CHANNELS = 25

        width, height = obs['width'], obs['height']
        x_shift = (size - width) // 2
        y_shift = (size - height) // 2
        cities = {}

        turn = obs['step']

        FULL_LENTH = DAY_LENGTH + NIGHT_LENGTH
        all_night_turns_lef = ((MAX_DAYS - 1 - turn) // FULL_LENTH + 1) * NIGHT_LENGTH

        turns_to_night = (DAY_LENGTH - turn) % FULL_LENTH
        turns_to_night = 0 if turns_to_night > 30 else turns_to_night

        turns_to_dawn = FULL_LENTH - turn % FULL_LENTH
        turns_to_dawn = 0 if turns_to_dawn > 10 else turns_to_dawn

        if turns_to_night == 0:
            all_night_turns_lef -= (10 - turns_to_dawn)

        steps_until_night = 30 - turn % 40
        next_night_number_turn = min(10, 10 + steps_until_night)

        b = np.zeros((CHANNELS, size, size), dtype=np.float32)


        for update in obs['updates']:
            strs = update.split(' ')
            input_identifier = strs[0]

            if input_identifier == 'u':
                x = int(strs[4]) + x_shift
                y = int(strs[5]) + y_shift
                wood = int(strs[7])
                coal = int(strs[8])
                uranium = int(strs[9])
                fuel = wood + coal * 10 + uranium * 40
                if unit_id == strs[3]:
                    # Position and Cargo
                    b[:3, x, y] = (
                        1,
                        (wood + coal + uranium) / 100,
                        fuel / 4000
                    )
                else:
                    # Units
                    team = int(strs[2])
                    cooldown = float(strs[6])
                    idx = 3 + (team - obs['player']) % 2 * 3
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
                idx = 9 + (team - obs['player']) % 2 * 4
                b[idx:idx + 4, x, y] = (
                    1,
                    cities[city_id][0],
                    cities[city_id][1],
                    cities[city_id][2]
                )
            elif input_identifier == 'r':
                # Resources
                r_type = strs[1]
                r_x = int(strs[2])
                r_y = int(strs[3])
                if (r_type == 'coal' and not self.include_coal) \
                        or (r_type == 'uranium' and not self.include_uranium):
                    dist = distance(unit.pos.x, unit.pos.y, r_x, r_y)
                    if dist > 1:
                        continue
                x = r_x + x_shift
                y = r_y + y_shift
                amt = int(float(strs[4]))
                b[{'wood': 17, 'coal': 18, 'uranium': 19}[r_type], x, y] = amt / 800
            elif input_identifier == 'rp':
                # Research Points
                team = int(strs[1])
                rp = int(strs[2])
                b[20 + (team - obs['player']) % 2, :] = min(rp, 200) / 200
            elif input_identifier == 'c':
                # Cities
                city_id = strs[2]
                fuel = float(strs[3])
                lightupkeep = float(strs[4])
                autonomy = int(fuel) // int(lightupkeep)
                will_live = autonomy >= all_night_turns_lef
                will_live_next_night = autonomy >= next_night_number_turn
                cities[city_id] = (
                    int(will_live_next_night),
                    int(will_live),
                    min(autonomy, 10) / 10)


        # Day/Night Cycle
        b[22, :] = obs['step'] % 40 / 40
        # Turns
        b[23, :] = obs['step'] / 360
        # Map Size
        b[24, x_shift:size - x_shift, y_shift:size - y_shift] = 1

        return b

    def make_input(self, obs, unit_id, size=32):
        width, height = obs['width'], obs['height']
        x_shift = (size - width) // 2
        y_shift = (size - height) // 2
        cities = {}

        b = np.zeros((20, size, size), dtype=np.float32)

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
        b[19, x_shift:size - x_shift, y_shift:size - y_shift] = 1

        return b

    def get_actions_unit(self, observation, game_state, actions: [], move_mapper: MoveHelper, unit_info,
                         resources, transfer_to_direction= None, exclude=[]) -> []:
        player = game_state.players[observation.player]

        # Worker Actions
        destinations = []

        for unit in player.units:
            if not unit.can_act():
                destinations.append(unit.pos)

        for unit in player.units:
            if unit.can_build(game_state.map) and unit.can_act() and unit not in exclude:
                self.get_action_unit(observation, game_state, unit_info[unit.id], move_mapper, actions, resources,
                                     can_transfer=True, transfer_to_direction= transfer_to_direction)

        for unit in player.units:
             if (not unit.can_build(game_state.map)) and unit.can_act() and unit not in exclude:
                self.get_action_unit(observation, game_state, unit_info[unit.id], move_mapper, actions, resources,
                                     can_transfer=True, transfer_to_direction= transfer_to_direction)

    def call_func(obj, method, args=[]):
        return getattr(obj, method)(*args)

    def get_action_unit(self, observation, game_state, info: UnitInfo,
                        move_mapper: MoveHelper, actions: [],
                        resources,
                        allow_build=True,
                        stay_in_case_no_found=True,
                        allow_move_to_outside_hull=True,
                        can_transfer = False,
                        log='',
                        transfer_to_direction= None, adjacent_units= None
                        ) \
            -> bool:
        unit = info.unit
        player = game_state.players[observation.player]

        if len(resources.all_resources_tiles)==0 and in_city(unit.pos, game_state):
            # performance shortcut
            return True

        if adjacent_units is None:
            adjacent_units = Lazy(lambda: player.get_units_around_pos(unit.pos, 1))

        is_day = game_state.turn % 40 < 30
        is_night = not is_day

        turn = game_state.turn
        FULL_LENTH = DAY_LENGTH + NIGHT_LENGTH
        all_night_turns_lef = ((MAX_DAYS - 1 - turn) // FULL_LENTH + 1) * NIGHT_LENGTH

        turns_to_night = (DAY_LENGTH - turn) % FULL_LENTH
        turns_to_night = 0 if turns_to_night > 30 else turns_to_night

        turns_to_dawn = FULL_LENTH - turn % FULL_LENTH
        turns_to_dawn = 0 if turns_to_dawn > 10 else turns_to_dawn

        if turns_to_night == 0:
            all_night_turns_lef -= (10 - turns_to_dawn)

        steps_until_night = 30 - turn % 40
        next_night_number_turn = min(10, 10 + steps_until_night)
        number_turns_stuck_in_night = min(4,turns_to_dawn)

        # ML magic
        policy = self.get_policy(observation, unit)

        log_string = 'ML'+log
        action_order=0
        # check in order of attractiveness
        for label in np.argsort(policy)[::-1]:
            action_order += 1

            act = unit_actions[label]
            type_action = act[0]
            if type_action == 'stay':
                if action_order == 1: # if this was very high in the list of action
                    move_mapper.stay(unit, log_string)
                    return True

            # if (not (is_day and steps_until_night > 1)) and \
            #         (unit.night_turn_survivable > number_turns_stuck_in_night):
            #     prx(unit.id,"XXXX Not in city and won't day next turn", unit.cargo.to_string(),"->",unit.night_turn_survivable)


            next_pos = unit.pos.translate(act[-1], 1) or unit.pos
            if type_action == 'move' and move_mapper.can_move_to_pos(next_pos, game_state):
                # MOVE ACTIONS
                if (is_day and steps_until_night > 1) or \
                        (unit.night_turn_survivable>number_turns_stuck_in_night):
                    #DAY RULES (or night outside the city, with resources, move where you want)
                    if allow_move_to_outside_hull:
                        move_mapper.move_unit_to_pos(actions, info, log_string, next_pos)
                        return True
                    else:
                        if move_mapper.is_moving_to_resource_hull(unit, next_pos):
                            move_mapper.move_unit_to_pos(actions, info, log_string, next_pos)
                            return True
                else:
                    # NIGHT, in the city, (so no resources)
                    # or
                    # NIGHT outside, without enough resource to live until the end of cooldown after move
                    # ->
                    #    move only near resource or in cities
                    if in_city(next_pos, game_state):
                        # move to another city, ok
                        move_mapper.move_unit_to_pos(actions, info, log_string, next_pos)
                        return True
                    else:
                        next_in_resource, next_near_resource = MapAnalysis.is_position_in_X_adjacent_to_resource(
                            resources.available_resources_tiles, next_pos)
                        if next_in_resource or next_near_resource:
                            # move to near_resource, also ok
                            move_mapper.move_unit_to_pos(actions, info, log_string, next_pos)
                            return True

            elif allow_build and type_action == 'build_city' and unit.can_build(game_state.map):
                # BUILD CITY
                # TODO id steps_until_night <= 2, then it should build only if...?
                if is_day:
                    move_mapper.build_city(actions, info, log_string)
                    return True

            elif can_transfer and type_action == 'transfer' and transfer_to_direction is not None:
                u_prefix = move_mapper.log_prefix + info.unit.id + " " + log_string
                if transfer_to_direction(actions, adjacent_units, info, u_prefix, act[-1]):
                    return True

        # FOUND NOTHING
        if stay_in_case_no_found:
            move_mapper.stay(unit, log_string)
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
        if self.model_type==1:
            state = self.make_input(observation, unit.id, size=self.model_map_size)
        elif self.model_type == 2:
            state = self.make_input2(observation, unit, size=self.model_map_size)

        with torch.no_grad():
            p = self.model(torch.from_numpy(state).unsqueeze(0))
        policy = p.squeeze(0).numpy()
        return policy
