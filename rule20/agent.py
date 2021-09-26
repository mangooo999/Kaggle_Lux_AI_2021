import math
import sys
import collections
import random

from game_state_info.game_state_info import GameStateInfo

random.seed(50)

from typing import Optional, List, Dict, Tuple

from lux.game import Game, Missions
from lux.game_map import Cell, Position
from lux.constants import Constants
from lux import annotate

from UnitInfo import UnitInfo
from GameInfo import GameInfo
from MoveHelper import MoveHelper
from lux.game_objects import CityTile, Unit, City, DIRECTIONS


# todo
# - optimise where create worker
# - do not create units in the night
# - optimise first move to go where most resources are within 2 cells
# optimise first move
# if moving to a city, remove move that move via another city?
# turn 200 seems to be a good turn to go and conquer wood unexplored wood clusters as it seems to make till 360

### Define helper functions

# this snippet finds all resources stored on the map and puts them into a list so we can search over them


def get_4_directions() -> [DIRECTIONS]:
    return [DIRECTIONS.SOUTH, DIRECTIONS.NORTH, DIRECTIONS.WEST, DIRECTIONS.EAST]


def directions_to(start_pos: 'Position', target_pos: 'Position') -> [DIRECTIONS]:
    """
    Return closest position to target_pos from this position
    """
    check_dirs = [
        DIRECTIONS.NORTH,
        DIRECTIONS.EAST,
        DIRECTIONS.SOUTH,
        DIRECTIONS.WEST,
    ]
    closest_dist = start_pos.distance_to(target_pos)
    closest_dirs = [DIRECTIONS.CENTER]
    for direction in check_dirs:
        newpos = start_pos.translate(direction, 1)
        dist = target_pos.distance_to(newpos)
        if dist < closest_dist:
            closest_dirs = [direction]
            closest_dist = dist
        elif dist == closest_dist:
            closest_dirs.append(direction)
            closest_dist = dist
    return closest_dirs


def find_all_resources(game_state, player) -> (List[Cell], List[Cell], List[Cell]):
    resource_tiles_all: List[Cell] = []
    resource_tiles_available: List[Cell] = []
    wood_tiles: List[Cell] = []
    width, height = game_state.map_width, game_state.map_height
    for y in range(height):
        for x in range(width):
            cell = game_state.map.get_cell(x, y)
            if cell.has_resource():
                resource_tiles_all.append(cell)
                if cell.resource.type == Constants.RESOURCE_TYPES.WOOD:
                    wood_tiles.append(cell)
                    resource_tiles_available.append(cell)
                if (cell.resource.type == Constants.RESOURCE_TYPES.COAL and player.researched_coal()) \
                        or (cell.resource.type == Constants.RESOURCE_TYPES.URANIUM and player.researched_uranium()):
                    resource_tiles_available.append(cell)

    return resource_tiles_all, resource_tiles_available, wood_tiles


# the next snippet all resources distance and return as sorted order.
def find_resources_distance(pos, player, resource_tiles, game_info: GameInfo) -> Dict[CityTile,
                                                                                      Tuple[int, int, DIRECTIONS]]:
    resources_distance = {}
    for resource_tile in resource_tiles:

        dist = resource_tile.pos.distance_to(pos)

        if resource_tile.resource.type == Constants.RESOURCE_TYPES.WOOD:
            resources_distance[resource_tile] = (dist, -resource_tile.resource.amount, resource_tile.resource.type)
        else:
            expected_resource_additional = (float(dist * 2.0) * float(game_info.get_research_rate(5)))
            expected_resource_at_distance = float(game_info.reseach_points) + expected_resource_additional
            # check if we are likely to have researched this by the time we arrive
            if resource_tile.resource.type == Constants.RESOURCE_TYPES.COAL and \
                    expected_resource_at_distance < 50.0:
                continue
            elif resource_tile.resource.type == Constants.RESOURCE_TYPES.URANIUM and \
                    expected_resource_at_distance < 200.0:
                continue
            else:
                # order by distance asc, resource asc
                resources_distance[resource_tile] = (dist, -resource_tile.resource.amount, resource_tile.resource.type)

    resources_distance = collections.OrderedDict(sorted(resources_distance.items(), key=lambda x: x[1]))
    return resources_distance


def find_closest_city_tile(pos, player) -> CityTile:
    closest_city_tile = None
    if len(player.cities) > 0:
        closest_dist = math.inf
        # the cities are stored as a dictionary mapping city id to the city object, which has a citytiles field that
        # contains the information of all citytiles in that city
        for k, city in player.cities.items():
            for city_tile in city.citytiles:
                dist = city_tile.pos.distance_to(pos)
                if dist < closest_dist:
                    closest_dist = dist
                    closest_city_tile = city_tile
    return closest_city_tile


def find_closest_adjacent_enemy_city_tile(pos, opponent) -> CityTile:
    closest_city_tile = None
    if len(opponent.cities) > 0:
        closest_dist = math.inf
        # the cities are stored as a dictionary mapping city id to the city object, which has a citytiles field that
        # contains the information of all citytiles in that city
        for k, city in opponent.cities.items():
            for city_tile in city.citytiles:
                dist = city_tile.pos.distance_to(pos)
                if dist < closest_dist:
                    closest_dist = dist
                    closest_city_tile = city_tile

    # and now one step back
    return closest_city_tile


def is_cell_empty(pos, game_state) -> bool:
    cell = game_state.map.get_cell(pos.x, pos.y)
    result = (not cell.has_resource()) and cell.citytile is None;
    # print("- ", pos, 'empty',result, file=sys.stderr)
    return result


# snippet to find the all city tiles distance and sort them.
def find_number_of_adjacent_city_tile(pos, player) -> int:
    number = 0
    for city in player.cities.values():
        for citytiles in city.citytiles:
            if citytiles.pos.is_adjacent(pos):
                number = number + 1

    return number


def find_all_adjacent_empty_tiles(game_state, pos) -> List[Position]:
    adjacent_positions = [Position(pos.x, pos.y + 1), Position(pos.x - 1, pos.y), Position(pos.x, pos.y - 1),
                          Position(pos.x + 1, pos.y)];
    empty_tiles = []
    for adjacent_position in adjacent_positions:
        if not is_position_valid(adjacent_position, game_state):
            continue
        try:
            if game_state.map.get_cell_by_pos(adjacent_position) is None:
                continue
            if not adjacent_position.is_adjacent(pos):
                # strangely the above return cell on the other side of the map
                continue
            if is_cell_empty(adjacent_position, game_state):
                empty_tiles.append(adjacent_position)
        except Exception:
            continue
    return empty_tiles


def is_position_valid(position, game_state) -> bool:
    return not (position.x < 0 or position.y < 0 \
                or position.x >= game_state.map_width or position.y >= game_state.map_height)


def adjacent_empty_tile_favor_close_to_city(empty_tyles, game_state, player) -> Optional[Cell]:
    if len(empty_tyles) == 0:
        return None
    elif len(empty_tyles) == 1:
        return game_state.map.get_cell_by_pos(empty_tyles[0])
    else:
        # print("Trying to solve which empty one is close to most cities tiles", file=sys.stderr)
        results = {}
        for adjacent_position in empty_tyles:
            number_of_adjacent = find_number_of_adjacent_city_tile(adjacent_position, player)
            results[number_of_adjacent] = adjacent_position
            # print("- ",adjacent_position,number_of_adjacent, file=sys.stderr)
        results = dict(sorted(results.items()))
        # ordered by number of tiles, so we take last element
        # print("results", results, file=sys.stderr)
        result = list(results.values())[-1]
        # print("Return", result, file=sys.stderr)
        return game_state.map.get_cell_by_pos(result)


def empty_tile_near_wood_and_city(empty_tiles, wood_tiles, game_state, player) -> Optional[Cell]:
    results = {}
    for adjacent_position in empty_tiles:
        number_of_adjacent = find_number_of_adjacent_city_tile(adjacent_position, player)
        if number_of_adjacent > 0 and is_position_adjacent_to_resource(wood_tiles, adjacent_position):
            results[number_of_adjacent] = adjacent_position
            # print("- ",adjacent_position,number_of_adjacent, file=sys.stderr)

    results = dict(sorted(results.items()))
    # ordered by number of tiles, so we take last element
    # print("results", results, file=sys.stderr)
    if len(results) == 0:
        # print("Return None", file=sys.stderr)
        return None
    else:
        result = list(results.values())[-1]

    # print("Return", result, file=sys.stderr)
    return game_state.map.get_cell_by_pos(result)


# snippet to find the all city tiles distance and sort them.
def find_city_tile_distance(pos: Position, player, unsafe_cities) -> Dict[CityTile, Tuple[int, int]]:
    city_tiles_distance: Dict[CityTile, Tuple[int, int]] = {}
    if len(player.cities) > 0:
        closest_dist = math.inf
        # the cities are stored as a dictionary mapping city id to the city object, which has a citytiles field that
        # contains the information of all citytiles in that city
        for k, city in player.cities.items():
            if city.cityid in unsafe_cities:
                for city_tile in city.citytiles:
                    dist = city_tile.pos.distance_to(pos)
                    # order by distance asc, autonomy desc
                    city_tiles_distance[city_tile] = (dist, get_autonomy_turns(city))
    city_tiles_distance = collections.OrderedDict(sorted(city_tiles_distance.items(), key=lambda x: x[1]))
    #     print(len(city_tiles_distance))
    return city_tiles_distance


def get_random_step() -> DIRECTIONS:
    return random.choice(get_4_directions())


def cargo_to_string(cargo) -> str:
    return_value = ''
    if cargo.wood > 0:
        return_value = return_value + f"Wood:{cargo.wood}"
    if cargo.coal > 0:
        return_value = return_value + f" Coal:{cargo.coal}"
    if cargo.uranium > 0:
        return_value = return_value + f" Uran:{cargo.uranium}"

    return return_value


def cargo_to_fuel(cargo) -> int:
    return cargo.wood + cargo.coal * 10 + cargo.uranium * 40


game_state = None
unit_info = {}
game_info = GameInfo()


def agent(observation, configuration):
    global game_state

    ### Do not edit ###
    if observation["step"] == 0:
        game_state = Game()
        game_state._initialize(observation["updates"])
        game_state._update(observation["updates"][2:])
        game_state.id = observation.player
    else:
        game_state._update(observation["updates"])

    actions = []

    ### AI Code goes down here! ###
    game_state_info: GameStateInfo = GameStateInfo(game_state.turn)
    game_state.calculate_features(Missions())
    player = game_state.players[observation.player]
    opponent = game_state.players[(observation.player + 1) % 2]
    move_mapper = MoveHelper(player, opponent)

    # add debug statements like so!
    if game_state.turn == 0:
        print("Agent is running!", file=sys.stderr)
    print("---------Turn number ", game_state.turn, file=sys.stderr)
    game_info.update(player, game_state)

    # current number of units
    units = len(player.units)
    unit_number = 0

    all_resources_tiles, available_resources_tiles, wood_tiles = find_all_resources(game_state, player)
    if game_state.turn == 0:
        # initial calculations
        initial_city_pos = list(player.cities.values())[0].citytiles[0].pos
        x3: list = get_resources_around(available_resources_tiles, initial_city_pos, 3)
        game_info.at_start_resources_within3 = len(x3)
        print("Resources within distance 3 of", initial_city_pos, "initial pos", len(x3), file=sys.stderr)

        first_best_position = None
        first_move = {}
        for direction in get_4_directions():
            next_pos = initial_city_pos.translate(direction, 1)
            if is_position_valid(next_pos, game_state) and not move_mapper.is_position_enemy_city(next_pos):
                res_2 = len(get_resources_around(wood_tiles, next_pos, 1))
                is_empty = is_cell_empty(next_pos, game_state)
                print('Resources within 2 of', direction, '=', res_2, ';empty', is_empty, file=sys.stderr)
                first_move[(next_pos.x, next_pos.y)] = res_2

        # END initial calculations

    # Spawn of new troops and assigment of roles below
    for unit in player.units:
        unit_number = unit_number + 1
        if not unit.id in unit_info:
            # new unit
            unit_info[unit.id] = UnitInfo(unit)
            if game_state.turn == 0 and first_best_position is not None:
                unit_info[unit.id].set_unit_role_traveler(first_best_position, 1)
            elif unit_number == 2 and units == 2:
                unit_info[unit.id].set_unit_role('expander')
            elif game_state.turn < 25 and unit_number == game_info.at_start_resources_within3:
                unit_info[unit.id].set_unit_role('explorer')
            # elif unit_number == 5 and units == 5:
            #    unit_info[unit.id].set_unit_role('hassler')
        else:
            unit_info[unit.id].update(unit, game_state.turn)

    # max number of units available
    units_cap = sum([len(x.citytiles) for x in player.cities.values()])

    unit_ceiling = int(min(float(units_cap), max(float(len(available_resources_tiles)) * 1.8, 5)))

    cities = list(player.cities.values())
    unsafe_cities = {}
    lowest_autonomy = 0
    available_city_actions = 0
    available_city_actions_now_and_next = 0;
    do_research_points = 0
    number_city_tiles = 0

    if len(cities) > 0:
        for city in cities:
            will_live = get_autonomy_turns(city) >= game_state_info.all_night_turns_lef
            # collect unsafe cities
            if not will_live:
                unsafe_cities[city.cityid] = (
                    len(city.citytiles),
                    (game_state_info.all_night_turns_lef - get_autonomy_turns(city)) * city.get_light_upkeep())

            # record how many research points we have now
            for city_tile in city.citytiles[::-1]:
                number_city_tiles = number_city_tiles + 1
                if city_tile.can_act():
                    available_city_actions += 1
                if city_tile.cooldown <= 1:
                    available_city_actions_now_and_next += 1

    # todo move print in  game_state_info class
    print(game_state.turn, 'resources', len(available_resources_tiles), 'units', units, 'unit_ceiling', unit_ceiling,
          'research', player.research_points, ' avail city points', available_city_actions, file=sys.stderr)

    if (not player.researched_uranium()) and player.research_points + available_city_actions >= 200:
        do_research_points = 200 - player.research_points
        print('We could complete uranium using', do_research_points, 'of', available_city_actions,
              file=sys.stderr)
    elif (not player.researched_coal()) and player.research_points + available_city_actions >= 50:
        do_research_points = 50 - player.research_points
        print('We could complete coal using', do_research_points, 'of', available_city_actions, file=sys.stderr)
    elif (not player.researched_uranium()) and player.research_points + available_city_actions >= 200:
        do_research_points = 200 - player.research_points
        print('We could complete NEXT uranium using', do_research_points, 'of',
              available_city_actions_now_and_next, file=sys.stderr)
    elif (not player.researched_coal()) and player.research_points + available_city_actions_now_and_next >= 50:
        do_research_points = 50 - player.research_points
        print('We could complete NEXT coal using', do_research_points, 'of', available_city_actions_now_and_next,
              file=sys.stderr)

    number_work_we_can_build = available_city_actions - do_research_points
    number_work_we_want_to_build = unit_ceiling - units

    if len(available_resources_tiles) == 0 and game_info.still_can_do_reseach():
        number_work_we_want_to_build = 0

    # last ten turn, just build in case it is a tie
    if game_state.turn > 350:
        number_work_we_want_to_build = number_work_we_can_build

    # Find how many and where to create builders

    print('number_work_we_can_build', number_work_we_can_build, 'number_work_we_want_to_build',
          number_work_we_want_to_build, file=sys.stderr)
    do_another_cycle = True
    while min(number_work_we_can_build, number_work_we_want_to_build) > 0 and do_another_cycle:
        do_another_cycle = False
        for city in reversed(cities):
            city_autonomy = get_autonomy_turns(city)
            will_live = city_autonomy >= game_state_info.all_night_turns_lef
            lowest_autonomy = min(lowest_autonomy, city_autonomy)
            for city_tile in city.citytiles[::-1]:
                # print("- C tile ", city_tile.pos, " CD=", city_tile.cooldown, file=sys.stderr)
                if city_tile.can_act():
                    if (not will_live) or len(unsafe_cities) == 0:
                        # let's create one more unit in the last created city tile if we can
                        actions.append(city_tile.build_worker())
                        print(city_tile.pos, "- created worker", file=sys.stderr)
                        number_work_we_can_build -= 1
                        number_work_we_want_to_build -= 1
                        do_another_cycle = True

    if len(cities) > 0:
        for city in reversed(cities):
            for city_tile in city.citytiles[::-1]:
                # print("- C tile ", city_tile.pos, " CD=", city_tile.cooldown, file=sys.stderr)
                if city_tile.can_act():
                    if game_info.still_can_do_reseach():
                        # let's do research
                        game_info.do_research(actions, city_tile, str(city_tile.pos) + " research")
                    # else:
                    # print("- - nothing", file=sys.stderr)

        print("Unsafe cities", unsafe_cities, file=sys.stderr)

    can_build = can_build_for_resources(game_state_info.all_night_turns_lef, lowest_autonomy, game_state_info.steps_until_night, player)
    print(game_state.turn, 'can_build: ', can_build, file=sys.stderr)

    # trace the agent move
    # store all unit current location on move tracker
    for unit in player.units:
        if not unit.can_act():
            move_mapper.add_position(unit.pos, unit)

    # map of resource to unit going for them
    resource_target_by_unit = {}

    for unit in player.units:
        info: UnitInfo = unit_info[unit.id]
        prefix: str = "T_" + game_state.turn.__str__() + str(unit.id)

        print(prefix, ";pos", unit.pos, 'CD=', unit.cooldown, cargo_to_string(unit.cargo), 'fuel=',
              cargo_to_fuel(unit.cargo), 'canBuildHere', unit.can_build(game_state.map), 'role', info.role,
              file=sys.stderr)
        if (move_mapper.is_position_city(unit.pos) and 2 < game_state.turn < 15 and number_city_tiles == 1 and len(
                player.units) == 1):
            print(prefix, ' NEEDS to become an expander', file=sys.stderr)
            info.set_unit_role('expander')

        if unit.is_worker() and unit.can_act():
            adjacent_empty_tiles = find_all_adjacent_empty_tiles(game_state, unit.pos)
            closest_empty_tile = adjacent_empty_tile_favor_close_to_city(adjacent_empty_tiles, game_state, player)
            resources_distance = find_resources_distance(unit.pos, player, all_resources_tiles, game_info)

            print(prefix, 'adjacent_empty_tiles', [x.__str__() for x in adjacent_empty_tiles],
                  'favoured', closest_empty_tile.pos if closest_empty_tile else '', file=sys.stderr)

            #   EXPLORER
            if info.is_role_city_explorer():
                print(prefix, ' is explorer', file=sys.stderr)
                if resources_distance is not None and len(resources_distance) > 0 and game_state_info.steps_until_night > 1:
                    # try to find the farwest resource we can find within reach before night
                    target_pos = None
                    for r in resources_distance:
                        if 3 < unit.pos.distance_to(r.pos) <= (game_state_info.steps_until_night + 1) / 2:
                            target_pos = r.pos

                    if target_pos is not None:
                        distance = unit.pos.distance_to(target_pos)
                        print(prefix, ' explorer will go to', target_pos, 'dist', distance, file=sys.stderr)
                        info.set_unit_role_traveler(target_pos, 2 * distance)

                if info.is_role_city_explorer():
                    print(prefix, ' failed to find resource for explorer, clearing role', file=sys.stderr)
                    info.clean_unit_role()

            #   EXPANDER
            if info.is_role_city_expander() and unit.get_cargo_space_left() > 0:
                print(prefix, ' is expander', file=sys.stderr)

                # all action expander are based on building next turn. We don't build at last day, so skip if day before
                if game_state_info.steps_until_night > 1:
                    if is_position_adjacent_city(player, unit.pos) and (not move_mapper.is_position_city(unit.pos)) \
                            and is_position_adjacent_to_resource(wood_tiles, unit.pos):
                        # if we are next to city and to wood, just stay here
                        print(prefix, ' expander we are between city and wood do not move', file=sys.stderr)
                        continue

                    # if we have the possibility of going in a tile that is like the  above
                    expander_perfect_spot = empty_tile_near_wood_and_city(adjacent_empty_tiles, wood_tiles,
                                                                          game_state, player)
                    if expander_perfect_spot is not None:
                        if try_to_move_to(actions, move_mapper, info, expander_perfect_spot.pos,
                                          " expander to perfect pos"):
                            continue

            #   EXPANDER ENDS

            # night rules
            if game_state_info.is_night_time() or game_state_info.is_night_tomorrow():
                time_to_dawn = 10 + game_state_info.steps_until_night
                print(prefix, ' it is night...', 'time_to_dawn', time_to_dawn,
                      'inCity', move_mapper.is_position_city(unit.pos), 'empty', is_cell_empty(unit.pos, game_state)
                      , 'nearwood', is_position_adjacent_to_resource(wood_tiles, unit.pos), file=sys.stderr)

                if is_position_adjacent_to_resource(wood_tiles, unit.pos) and is_cell_empty(unit.pos, game_state):
                    print(prefix, ' it is night, we are in a empty cell near resources', file=sys.stderr)
                    # empty near a resource, we can stay here, but we could even better go to same near city

                    # if we have the possibility of going in a tile that is like the  above
                    best_night_spot = empty_tile_near_wood_and_city(adjacent_empty_tiles, wood_tiles,
                                                                    game_state, player)
                    if best_night_spot is not None \
                            and try_to_move_to(actions, move_mapper, info, best_night_spot.pos, " best_night_spot"):
                        continue
                    else:
                        print(prefix, ' it is night, we will stay here', file=sys.stderr)
                        continue

                # if we have the possibility of going in a tile that is like the above,
                # go id not in a city, or if you are in a city, go just last 1 days of night (so we gather and covered)
                if (not move_mapper.is_position_city(unit.pos)) or time_to_dawn <= 1:
                    best_night_spot = empty_tile_near_wood_and_city(adjacent_empty_tiles, wood_tiles,
                                                                    game_state, player)
                    if best_night_spot is not None \
                            and try_to_move_to(actions, move_mapper, info, best_night_spot.pos, " best_night_spot"):
                        continue

                if game_state_info.is_night_time() and cargo_to_fuel(unit.cargo) > 0:
                    # if we have resources, next to a city that will die in this night,
                    # and we have enough resources to save it, then move
                    cities = adjacent_cities(player, unit.pos)
                    # order cities by decreasing size
                    cities = collections.OrderedDict(sorted(cities.items(), key=lambda x: x[-1]))
                    if len(cities) > 0:
                        is_any_city_in_danger = False
                        for city, city_payload in cities.items():
                            autonomy = city_payload[1]
                            if autonomy < time_to_dawn:
                                print(prefix, 'night, city in danger', city.cityid, 'sz/aut/dir', city_payload,
                                      file=sys.stderr)
                                is_any_city_in_danger = True
                                break

                        if is_any_city_in_danger:
                            # todo maybe we should choose a city that we can save by moving there?
                            print(prefix, 'try to save city', city.cityid, city_payload, file=sys.stderr)
                            move_unit_to(actions, city_payload[2], move_mapper, info, " try to save a city")
                            continue

                if move_mapper.is_position_city(unit.pos):
                    print(prefix, ' it is night, we are in city, do not move', file=sys.stderr)
                    continue

            # DAWN

            if game_state_info.is_dawn():
                print(prefix, "It's dawn", file=sys.stderr)
                if is_position_adjacent_to_resource(wood_tiles, unit.pos) and is_cell_empty(unit.pos, game_state) \
                        and 0 < unit.get_cargo_space_left() <= 21:
                    print(prefix, ' at dawn, can build next day', file=sys.stderr)
                    continue

            #   TRAVELER
            if info.is_role_traveler():
                print(prefix, ' is traveler to', info.target_position, file=sys.stderr)
                direction = get_direction_to_quick(game_state, unit, info.target_position, move_mapper)
                if direction != DIRECTIONS.CENTER and move_mapper.can_move_to_direction(info.unit.pos, direction):
                    move_unit_to(actions, direction, move_mapper, info, " move to traveler pos", info.target_position)
                    continue
                else:
                    print(prefix, ' traveller cannot move', file=sys.stderr)
                    if unit.pos.distance_to(info.target_position) <= 1:
                        info.clean_unit_role()

            #   HASSLER
            if info.is_role_hassler():
                print(prefix, ' is hassler', file=sys.stderr)
                if is_position_adjacent_city(opponent, unit.pos):
                    print(prefix, ' hassler arrived to enemy', file=sys.stderr)
                    if unit.can_build(game_state.map):
                        build_city(actions, info, 'hassler build next to city, and done!')
                        info.clean_unit_role()
                        continue
                    elif unit.get_cargo_space_left() == 0 and closest_empty_tile is not None:

                        print(prefix, " hassler full and close to empty, trying to move and build",
                              closest_empty_tile.pos, file=sys.stderr)
                        direction = unit.pos.direction_to(closest_empty_tile.pos)
                        next_pos = unit.pos.translate(direction, 1)
                        move_unit_to(actions, direction, move_mapper, info,
                                     " move to build nearby enemy",
                                     next_pos)
                        continue

                else:
                    enemy_surrounding = find_closest_adjacent_enemy_city_tile(unit.pos, opponent)
                    direction = unit.pos.direction_to(enemy_surrounding.pos)
                    # if nobody is already moving there
                    if not move_mapper.has_position(enemy_surrounding.pos):
                        move_unit_to(actions, direction, move_mapper, info, " move to enemy", enemy_surrounding.pos)
                        continue

                continue
            #   HASSLER ENDS

            # build city tiles adjacent of other tiles to make only one city.
            if unit.can_build(game_state.map):
                if is_position_adjacent_city(player, unit.pos):
                    build_city(actions, info, 'in adjacent city!')
                    continue
                else:
                    # if we can move to a tile where we are adjacent, do and it and build there
                    if closest_empty_tile is not None:
                        print(prefix, " check if adjacent empty is more interesting", closest_empty_tile.pos,
                              file=sys.stderr)
                        direction = unit.pos.direction_to(closest_empty_tile.pos)
                        next_pos = unit.pos.translate(direction, 1)
                        # if nobody is already moving there
                        if not move_mapper.has_position(next_pos):
                            print(prefix, " and nobody is moving here", file=sys.stderr)
                            # and if next pos is actually adjacent
                            if is_position_adjacent_city(player, next_pos):
                                move_unit_to(actions, direction, move_mapper, info,
                                             " we could have build here, but we move close to city instead", next_pos)
                                continue

                if game_state_info.steps_until_night > 1 or (
                        game_state_info.steps_until_night == 1 and is_position_adjacent_to_resource(available_resources_tiles,
                                                                                    unit.pos)):
                    build_city(actions, info, 'NOT in adjacent city')
                    continue

            # if unit cant make city tiles try to collect resource collection.
            city_tile_distance = find_city_tile_distance(unit.pos, player, unsafe_cities)

            if game_state_info.is_night_time():
                enough_fuel = 200
            elif game_state_info.turns_to_night < 4:
                enough_fuel = 300
            else:
                enough_fuel = 400

            if (not info.is_role_returner()) and unit.get_cargo_space_left() > 0 \
                    and (cargo_to_fuel(unit.cargo) < enough_fuel or len(unsafe_cities) == 0 or info.is_role_hassler()):
                if not is_position_resource(available_resources_tiles, unit.pos):
                    # find the closest resource if it exists to this unit

                    print(prefix, " Find resources", file=sys.stderr)

                    if resources_distance is not None and len(resources_distance) > 0:
                        # create a move action to the direction of the closest resource tile and add to our actions list
                        direction, pos, msg, resource_type = find_best_resource(move_mapper, resources_distance,
                                                                                resource_target_by_unit, unit, prefix)
                        if (resource_type == Constants.RESOURCE_TYPES.COAL and not player.researched_coal()) or \
                                (resource_type == Constants.RESOURCE_TYPES.URANIUM and not player.researched_uranium()):
                            # this is a not researched yet resource, force to go there, so there is no jitter
                            distance_to_res = pos.distance_to(unit.pos)
                            print(prefix, " Found resource not yet researched:", resource_type, "dist", distance_to_res,
                                  file=sys.stderr)
                            info.set_unit_role_traveler(pos, 2 * distance_to_res)

                        if pos is not None:
                            # append target to our map
                            resource_target_by_unit.setdefault((pos.x, pos.y), []).append(unit.id)
                        move_unit_to(actions, direction, move_mapper, info, msg, pos)
                        continue
                    else:
                        print(prefix, " resources_distance invalid (or empty?)", file=sys.stderr)
                else:
                    resource_type = game_state.map.get_cell(unit.pos.x, unit.pos.y).resource.type
                    print(prefix, " Already on resources:", resource_type, file=sys.stderr)
                    if resource_type != Constants.RESOURCE_TYPES.WOOD \
                            and get_friendly_unit(player, info.last_move_before_pos) is not None and \
                            move_mapper.can_move_to_direction(unit.pos, info.last_move_direction):
                        move_unit_to(actions, info.last_move_direction, move_mapper, info, 'move a bit further')
                    else:
                        resource_target_by_unit.setdefault((unit.pos.x, unit.pos.y), []).append(unit.id)
                        print(prefix, " Stay on resources", file=sys.stderr)
                    continue
            else:
                if game_state_info.steps_until_night > 10 and can_build and unit.get_cargo_space_left() <= 20 and is_position_resource(
                        available_resources_tiles, unit.pos) and closest_empty_tile is not None:
                    # if we are on a resource, and we can move to an empty tile,
                    # then it means we can at least collect 20 next turn on CD and then build
                    # find the closest empty tile it to build a city
                    direction = unit.pos.direction_to(closest_empty_tile.pos)
                    move_unit_to(actions, direction, move_mapper, info,
                                 " towards closest empty (anticipating getting resources)", closest_empty_tile.pos)
                elif game_state_info.steps_until_night > 10 and can_build and unit.get_cargo_space_left() == 0 \
                        and closest_empty_tile is not None:
                    # find the closest empty tile it to build a city
                    direction = unit.pos.direction_to(closest_empty_tile.pos)
                    move_unit_to(actions, direction, move_mapper, info, " towards closest empty ",
                                 closest_empty_tile.pos)
                else:
                    print(prefix, " Goto city", file=sys.stderr)
                    # find closest city tile and move towards it to drop resources to a it to fuel the city
                    if city_tile_distance is not None and len(city_tile_distance) > 0 and not info.is_role_hassler():
                        print(prefix, " Goto city2", file=sys.stderr)
                        direction, pos, msg = find_best_city(city_tile_distance, move_mapper, player, unit)
                        # check if anybody in the pos where we come from
                        friend_unit = get_friendly_unit(player, unit.pos.translate(direction, 1))
                        if friend_unit is not None \
                                and friend_unit.get_cargo_space_left() > 100 - unit.get_cargo_space_left():
                            print(prefix, " instead of going to city, do transfer to", friend_unit.id,
                                  ' in ', unit.pos.translate(direction, 1), file=sys.stderr)
                            transfer_all_resources(actions, info, friend_unit.id)
                            if unit_info[unit.id].is_role_traveler:
                                unit_info[unit.id].clean_unit_role();
                        else:
                            move_unit_to(actions, direction, move_mapper, info, msg, pos)
                            if cargo_to_fuel(unit.cargo) >= enough_fuel:
                                info.set_unit_role("returner")

    # if this unit didn't do any action, check if we can transfer his cargo back in the direction this come from
    for unit in player.units:
        info: UnitInfo = unit_info[unit.id]
        prefix: str = "T_" + game_state.turn.__str__() + str(unit.id)
        # print(prefix, "XXX check unit has worked", unit.can_act(), info.has_done_action_this_turn,file=sys.stderr)
        if unit.is_worker() and unit.can_act() and not info.has_done_action_this_turn:
            print(prefix, " this unit has not worked", file=sys.stderr)
            if unit.cargo.coal > 0 or unit.cargo.uranium > 0:
                # check if anybody in the pos where we come from
                friend_unit = get_friendly_unit(player, info.last_move_before_pos)
                if friend_unit is not None:
                    print(prefix, " Do transfer to", friend_unit.id, ' in ', info.last_move_before_pos,
                          file=sys.stderr)
                    transfer_all_resources(actions, info, friend_unit.id)
                    if unit_info[unit.id].is_role_traveler:
                        unit_info[unit.id].clean_unit_role();

    # for i,j in resource_target_by_unit.items():
    #    print("XXXX resources map ",game_info.turn,i,len(j), file=sys.stderr)

    return actions


def get_friendly_unit(player, pos) -> Unit:
    for unit in player.units:
        if unit.pos.equals(pos):
            return unit

    return None


def find_best_city(city_tile_distance, move_mapper: MoveHelper, player, unit) -> Tuple[
    DIRECTIONS, Optional[Position], str]:
    closest_city_tile = None
    moved = False
    for city_tile, dist in city_tile_distance.items():
        if not move_mapper.has_position(city_tile.pos):
            closest_city_tile = city_tile

            if closest_city_tile is not None:
                direction = get_direction_to_quick(game_state, unit, closest_city_tile.pos, move_mapper)
                if direction != DIRECTIONS.CENTER:
                    moved = True
                    return direction, closest_city_tile.pos, " towards closest city distancing and autonomy" + dist.__str__()

    if not moved:
        direction = get_random_step()
        return direction, None, "randomly (due to city)"


def find_best_resource(move_mapper: MoveHelper, resources_distance, resource_target_by_unit, unit, prefix) -> \
        Tuple[DIRECTIONS, Optional[Position], str, str]:
    closest_resource_tile, c_dist = None, None
    moved = False
    # print(prefix, " XXX Find resources dis", resources_distance.values(), file=sys.stderr)
    # print(prefix, " XXX Find resources pos", resources_distance.keys(), file=sys.stderr)
    # print(prefix, " XXX Move mapper", move_mapper.move_mapper.keys(), file=sys.stderr)

    for max_units_per_resource in range(6, 7):
        for resource, resource_dist_info in resources_distance.items():
            # print(prefix, " XXX - ", resource.pos, resource_dist_info, file=sys.stderr)
            if resource is not None and not resource.pos.equals(unit.pos):
                if len(resource_target_by_unit.setdefault((resource.pos.x, resource.pos.y),
                                                          [])) < max_units_per_resource:
                    direction = get_direction_to_quick(game_state, unit, resource.pos, move_mapper)
                    if direction != DIRECTIONS.CENTER:
                        return direction, resource.pos, " towards closest resource ", resource_dist_info[2]

    direction = get_random_step()
    return direction, None, "randomly (due to resource)", ""


def get_autonomy_turns(city) -> int:
    turns_city_can_live = city.fuel // city.get_light_upkeep()
    return turns_city_can_live


def build_city(actions, info: UnitInfo, msg=''):
    actions.append(info.unit.build_city())
    print("Unit", info.unit.id, '- build city', msg, file=sys.stderr)
    info.set_last_action_build()


def transfer_all_resources(actions, info: UnitInfo, to_unit_id, msg=''):
    if info.unit.cargo.uranium > 0:
        actions.append(info.unit.transfer(to_unit_id, Constants.RESOURCE_TYPES.URANIUM, info.unit.cargo.uranium))
        print("Unit", info.unit.id, '- transfer', info.unit.cargo.uranium, 'uranium to ', to_unit_id, file=sys.stderr)
        info.set_last_action_transfer()
    elif info.unit.cargo.coal > 0:
        actions.append(info.unit.transfer(to_unit_id, Constants.RESOURCE_TYPES.COAL, info.unit.cargo.coal))
        print("Unit", info.unit.id, '- transfer', info.unit.cargo.coal, 'coal to ', to_unit_id, file=sys.stderr)
        info.set_last_action_transfer()
    elif info.unit.cargo.wood > 0:
        actions.append(info.unit.transfer(to_unit_id, Constants.RESOURCE_TYPES.WOOD, info.unit.cargo.wood))
        print("Unit", info.unit.id, '- transfer', info.unit.cargo.wood, 'wood to ', to_unit_id, file=sys.stderr)
        info.set_last_action_transfer()


def can_build_for_resources(all_night_turns_lef, lowest_autonomy, steps_until_night, player) -> bool:
    if steps_until_night > 20:
        return True
    elif lowest_autonomy > 12 and steps_until_night > 10:
        return True

    can_build = True
    for city in player.cities.values():
        city_can_live = can_city_live(city, all_night_turns_lef)
        if not city_can_live:
            can_build = False
            break
    return can_build


def can_city_live(city, all_night_turns_lef) -> bool:
    return city.fuel / (city.get_light_upkeep() + 20) >= min(all_night_turns_lef, 30)


def move_unit_to(actions, direction, move_mapper: MoveHelper, info: UnitInfo, reason="", target_far_position=None):
    unit = info.unit
    next_state_pos = unit.pos.translate(direction, 1)
    # print("Unit", unit.id, 'XXX -', unit.pos, next_state_pos, direction, file=sys.stderr)
    if direction == DIRECTIONS.CENTER or next_state_pos.equals(unit.pos):
        # do not annotate
        print("Unit", unit.id, '- not moving "', '', '" ', reason, file=sys.stderr)
        move_mapper.add_position(unit.pos, unit)
    else:
        if target_far_position is not None:
            # target_far_position is only used for the annotation line
            actions.append(annotate.line(unit.pos.x, unit.pos.y, target_far_position.x, target_far_position.y))
            # actions.append(annotate.text(unit.pos.x, unit.pos.y, reason))

        actions.append(unit.move(direction))
        move_mapper.add_position(next_state_pos, unit)
        info.set_last_action_move(direction)
        print("Unit", unit.id, '- moving towards "', direction, next_state_pos, '" :', reason
              , str(target_far_position or ''), file=sys.stderr)


def is_position_adjacent_city(player, pos, do_log=False) -> bool:
    for city in player.cities.values():
        for city_tile in city.citytiles:
            if city_tile.pos.is_adjacent(pos):
                if do_log:
                    print(pos, "is_position_adjacent_city", city_tile.pos, file=sys.stderr)
                return True

    return False


def is_position_adjacent_to_resource(resource_tiles, pos) -> bool:
    for r in resource_tiles:
        if r.pos.is_adjacent(pos):
            return True
    return False


def is_position_resource(resource_tiles, pos) -> bool:
    for r in resource_tiles:
        if r.pos.equals(pos):
            return True
    return False


def try_to_move_to(actions, move_mapper, info: UnitInfo, pos: Position, msg: str) -> bool:
    direction = info.unit.pos.direction_to(pos)
    # if nobody is already moving there
    if not move_mapper.has_position(pos):
        move_unit_to(actions, direction, move_mapper, info, msg, pos)
        return True
    else:
        return False


def get_resources_around(resource_tiles: List[Cell], pos: Position, max_dist) -> List[Cell]:
    resources = []
    for r in resource_tiles:
        if pos.distance_to(r.pos) <= max_dist:
            resources.append(r)

    return resources


# return dist of cities, autonomy
def adjacent_cities(player, pos: Position, do_log=False) -> {City, Tuple[int, int, DIRECTIONS]}:
    cities = {}
    for city in player.cities.values():
        for city_tile in city.citytiles:
            if city_tile.pos.is_adjacent(pos):
                if do_log:
                    print(pos, "adjacent_cities", city_tile.pos, file=sys.stderr)
                cities[city] = (len(city.citytiles), get_autonomy_turns(city), directions_to(pos, city_tile.pos)[0])

    return cities


def get_direction_to_quick(game_state: Game, unit: Unit, target_pos: Position, move_mapper: MoveHelper) -> DIRECTIONS:
    from_pos = unit.pos
    if from_pos.equals(target_pos):
        return DIRECTIONS.CENTER

    directions = directions_to(from_pos, target_pos)
    for direction in directions:
        next_pos = from_pos.translate(direction, 1)

        # if we are trying to move on top of somebody else, skip
        # print(' XXX - try', direction, next_pos,'mapper', move_mapper.move_mapper.keys(),file=sys.stderr)
        if move_mapper.cannot_move_to(next_pos):
            # print(' XXX - skip', file=sys.stderr)
            continue
        else:
            return direction

    return DIRECTIONS.CENTER


def get_direction_to_smart(game_state: Game, unit: Unit, target_pos: Position, move_mapper: MoveHelper) -> DIRECTIONS:
    smallest_cost = [2, 2, 2, 2]
    closest_dir = DIRECTIONS.CENTER
    closest_pos = unit.pos

    for direction in game_state.dirs:
        newpos = unit.pos.translate(direction, 1)

        cost = [0, 0, 0, 0]

        # do not go out of map
        if tuple(newpos) in game_state.xy_out_of_map:
            continue

        # discourage if new position is occupied
        if tuple(newpos) in game_state.occupied_xy_set:
            if tuple(newpos) not in game_state.player_city_tile_xy_set:
                cost[0] = 2

        # discourage going into a city tile if you are carrying substantial wood
        if tuple(newpos) in game_state.player_city_tile_xy_set and unit.cargo.wood >= 60:
            cost[0] = 1

        # path distance as main differentiator
        path_dist = game_state.retrieve_distance(newpos.x, newpos.y, target_pos.x, target_pos.y)
        cost[1] = path_dist

        # manhattan distance to tie break
        manhattan_dist = (newpos - target_pos)
        cost[2] = manhattan_dist

        # prefer to walk on tiles with resources
        aux_cost = game_state.convolved_collectable_tiles_matrix[newpos.y, newpos.x]
        cost[3] = -aux_cost

        # if starting from the city, consider manhattan distance instead of path distance
        if tuple(unit.pos) in game_state.player_city_tile_xy_set:
            cost[1] = manhattan_dist

        # update decision
        if cost < smallest_cost:
            smallest_cost = cost
            closest_dir = direction
            closest_pos = newpos

    if closest_dir != DIRECTIONS.CENTER:
        game_state.occupied_xy_set.discard(tuple(unit.pos))
        if tuple(closest_pos) not in game_state.player_city_tile_xy_set:
            game_state.occupied_xy_set.add(tuple(closest_pos))
        unit.cooldown += 2

    return closest_dir
