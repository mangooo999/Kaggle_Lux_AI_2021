import random

from lux.game import Game
from lux.game_map import Cell, RESOURCE_TYPES, Position, DIRECTIONS
from lux.constants import Constants
from lux.game_constants import GAME_CONSTANTS
from lux import annotate
import math
import sys
import collections
from UnitInfo import UnitInfo
from GameInfo import GameInfo
from MoveHelper import MoveHelper


# todo
# - optimise where create worker
# - do not create units in the night

### Define helper functions

# this snippet finds all resources stored on the map and puts them into a list so we can search over them


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


def find_all_resources(game_state, player):
    resource_tiles_all: list[Cell] = []
    resource_tiles_available: list[Cell] = []
    wood_tiles: list[Cell] = []
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
def find_resources_distance(pos, player, resource_tiles, game_info: GameInfo) -> dict:
    resources_distance = {}
    for resource_tile in resource_tiles:

        dist = resource_tile.pos.distance_to(pos)

        if resource_tile.resource.type == Constants.RESOURCE_TYPES.WOOD:
            resources_distance[resource_tile] = (dist, -resource_tile.resource.amount, resource_tile.resource.type)
        else:
            expected_resource_additional = (float(dist * 2.0) * float (game_info.get_research_rate(5)))
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


def find_closest_city_tile(pos, player):
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


def find_closest_adjacent_enemy_city_tile(pos, opponent):
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


def is_cell_empty(pos, game_state):
    cell = game_state.map.get_cell(pos.x, pos.y)
    result = (not cell.has_resource()) and cell.citytile is None;
    # print("- ", pos, 'empty',result, file=sys.stderr)
    return result


# snippet to find the all citytiles distance and sort them.
def find_number_of_adjacent_city_tile(pos, player):
    number = 0
    for city in player.cities.values():
        for citytiles in city.citytiles:
            if citytiles.pos.is_adjacent(pos):
                number = number + 1

    return number


def find_all_adjacent_empty_tiles(game_state, pos):
    adjacent_positions = [Position(pos.x, pos.y + 1), Position(pos.x - 1, pos.y), Position(pos.x, pos.y - 1),
                          Position(pos.x + 1, pos.y)];
    empty_tiles = []
    for adjacent_position in adjacent_positions:
        if adjacent_position.x < 0 or adjacent_position.y < 0 \
                or adjacent_position.x >= game_state.map_width or adjacent_position.y >= game_state.map_height:
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


def adjacent_empty_tile_favor_close_to_city(empty_tyles, game_state, player):
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


def empty_tile_near_wood_and_city(empty_tiles, wood_tiles, game_state, player) -> Cell:
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
def find_city_tile_distance(pos, player, unsafe_cities):
    city_tiles_distance = {}
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


def get_random_step():
    return random.choice(['s', 'n', 'w', 'e'])


def cargo_to_string(cargo):
    return_value = ''
    if cargo.wood > 0:
        return_value = return_value + f"Wood:{cargo.wood}"
    if cargo.coal > 0:
        return_value = return_value + f" Coal:{cargo.coal}"
    if cargo.uranium > 0:
        return_value = return_value + f" Uran:{cargo.uranium}"

    return return_value


def cargo_to_fuel(cargo):
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
    player = game_state.players[observation.player]
    opponent = game_state.players[(observation.player + 1) % 2]

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
        initial_city_pos = list(player.cities.values())[0].citytiles[0].pos
        x3:list= get_resources_around(available_resources_tiles,initial_city_pos,3)
        game_info.at_start_resources_within3 = len(x3)
        print("Resources within distance 3 of", initial_city_pos,"initial pos", len(x3), file=sys.stderr)

    for unit in player.units:
        unit_number = unit_number + 1
        if not unit.id in unit_info:
            # new unit
            unit_info[unit.id] = UnitInfo(unit)
            if unit_number == 2 and units == 2:
                unit_info[unit.id].set_unit_role('expander')
            elif game_state.turn < 25 and unit_number == game_info.at_start_resources_within3:
                unit_info[unit.id].set_unit_role('explorer')
			# elif unit_number == 5 and units == 5:
            #    unit_info[unit.id].set_unit_role('hassler')
        else:
            unit_info[unit.id].update(unit)


    # max number of units available
    units_cap = sum([len(x.citytiles) for x in player.cities.values()])

    night_steps_left = ((359 - game_state.turn) // 40 + 1) * 10
    steps_until_night = 30 - game_state.turn % 40

    if steps_until_night < 0:
        night_steps_left = night_steps_left + steps_until_night

    # we want to build new tiless only if we have a lot of fuel in all cities
    is_night = steps_until_night <= 0
    is_night_tomorrow = -8 <= steps_until_night <= 1
    unit_ceiling = int(min(float(units_cap), max(float(len(available_resources_tiles)) * 1.8, 5)))

    cities = list(player.cities.values())
    unsafe_cities = {}
    lowest_autonomy = 0
    available_city_actions = 0
    available_city_actions_now_and_next = 0;
    do_research_points = 0

    if len(cities) > 0:
        for city in cities:
            will_live = get_autonomy_turns(city) >= night_steps_left
            # collect unsafe cities
            if not will_live:
                unsafe_cities[city.cityid] = (
                    len(city.citytiles), (night_steps_left - get_autonomy_turns(city)) * city.get_light_upkeep())

            # record how many research points we have now
            for city_tile in city.citytiles[::-1]:
                if city_tile.can_act(): available_city_actions += 1
                if city_tile.cooldown <= 1: available_city_actions_now_and_next += 1

    print(game_state.turn, "night_step_left ", night_steps_left, "steps_until_night ", steps_until_night,
          'resources', len(available_resources_tiles), 'units', units, 'unit_ceiling', unit_ceiling, 'research',
          player.research_points,
          ' avail city points', available_city_actions, file=sys.stderr)

    if (not player.researched_uranium()) and player.research_points + available_city_actions >= 200:
        do_research_points = 200 - player.research_points
        print('We could complete uranium using', do_research_points, 'of avail', available_city_actions,
              file=sys.stderr)
    elif (not player.researched_coal()) and player.research_points + available_city_actions >= 50:
        do_research_points = 50 - player.research_points
        print('We could complete coal using', do_research_points, 'of avail', available_city_actions, file=sys.stderr)
    elif (not player.researched_uranium()) and player.research_points + available_city_actions >= 200:
        do_research_points = 200 - player.research_points
        print('We could complete NEXT uranium using', do_research_points, 'of avail',
              available_city_actions_now_and_next, file=sys.stderr)
    elif (not player.researched_coal()) and player.research_points + available_city_actions_now_and_next >= 50:
        do_research_points = 50 - player.research_points
        print('We could complete NEXT coal using', do_research_points, 'of avail', available_city_actions_now_and_next,
              file=sys.stderr)

    number_city_tiles = 0
    if len(cities) > 0:
        for city in reversed(cities):
            can_create_worker = (units < unit_ceiling)
            city_autonomy = get_autonomy_turns(city)
            lowest_autonomy = min(lowest_autonomy, city_autonomy)
            will_live = city_autonomy >= night_steps_left
            print("City ", city.cityid, 'size=', len(city.citytiles), ' fuel=', city.fuel, ' upkeep=',
                  city.get_light_upkeep(), 'autonomy=', city_autonomy, 'safe=', will_live, file=sys.stderr)

            for city_tile in city.citytiles[::-1]:
                number_city_tiles = number_city_tiles + 1
                print("- C tile ", city_tile.pos, " CD=", city_tile.cooldown, file=sys.stderr)
                if city_tile.can_act():
                    if do_research_points > 0:
                        # we can complete something this turn, let's do research
                        actions.append(city_tile.research())
                        print("- - research (rushed)", file=sys.stderr)
                    if len(available_resources_tiles) == 0 and not player.researched_uranium():
                        # let's do research
                        actions.append(city_tile.research())
                        print("- - research (no resources)", file=sys.stderr)
                    elif can_create_worker and ((not will_live) or len(unsafe_cities) == 0):
                        # let's create one more unit in the last created city tile if we can
                        actions.append(city_tile.build_worker())
                        units = units + 1
                        print("- - created worker", file=sys.stderr)
                    elif not player.researched_uranium():
                        # let's do research
                        actions.append(city_tile.research())
                        print("- - research", file=sys.stderr)
                    else:
                        print("- - nothing", file=sys.stderr)

        print("Unsafe cities", unsafe_cities, file=sys.stderr)

    can_build = can_build_for_resources(night_steps_left, lowest_autonomy, steps_until_night, player)
    print(game_state.turn, 'can_build: ', can_build, file=sys.stderr)

    # trace the agent move
    move_mapper = MoveHelper(player, opponent)
    # store all unit current location on move tracker
    for unit in player.units:
        if not unit.can_act():
            move_mapper.add_position(unit.pos, unit)

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

            print(prefix, 'adjacent_empty_tiles', [x.__str__() for x in adjacent_empty_tiles],
                  'favoured', closest_empty_tile.pos if closest_empty_tile else '', file=sys.stderr)

            #   EXPLORER
            if info.is_role_city_explorer():
                print(prefix, ' is explorer', file=sys.stderr)
                if resources_distance is not None and len(resources_distance) > 0 and steps_until_night > 1:
                        #try to find the farwest resource we can find within reach before night
                        target_pos = None
                        for r in resources_distance:
                            if 3<unit.pos.distance_to(r.pos) <= (steps_until_night+1)/2:
                                target_pos = r.pos

                        if target_pos is not None:
                            distance = unit.pos.distance_to(target_pos)
                            print(prefix, ' explorer will go to',target_pos, 'dist',distance, file=sys.stderr)
                            info.set_unit_role_traveler(target_pos, 2 * distance)

                if info.is_role_city_explorer():
                    print(prefix, ' failed to find resource for explorer, clearing role', file=sys.stderr)
                    info.clean_unit_role()

            #   EXPANDER
            if info.is_role_city_expander() and unit.get_cargo_space_left() > 0:
                print(prefix, ' is expander', file=sys.stderr)

                # all action expander are based on building next turn. We don't build at last day, so skip if day before
                if steps_until_night > 1:
                    if is_position_adjacent_city(player, unit.pos) and (not move_mapper.is_position_city(unit.pos)) \
                            and is_position_adjacent_to_resource(wood_tiles, unit.pos):
                        # if we are next to city and to wood, just stay here
                        print(prefix, ' expander we are between city and wood do not move', file=sys.stderr)
                        continue

                    # if we have the possibility of going in a tile that is like the  above
                    expander_perfect_spot = empty_tile_near_wood_and_city(adjacent_empty_tiles, wood_tiles,
                                                                          game_state, player)
                    if expander_perfect_spot is not None:
                        if try_to_move_to(actions, move_mapper, unit, expander_perfect_spot.pos,
                                          " expander to perfect pos"):
                            continue

            #   EXPANDER ENDS

            # night rules
            if (is_night or is_night_tomorrow):
                time_to_dawn = 10 + steps_until_night
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
                            and try_to_move_to(actions, move_mapper, unit, best_night_spot.pos, " best_night_spot"):
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
                            and try_to_move_to(actions, move_mapper, unit, best_night_spot.pos, " best_night_spot"):
                        continue

                if is_night and cargo_to_fuel(unit.cargo)>0:
                    # if we have resources, next to a city that will die in this night,
                    # and we have enough resources to save it, then move
                    cities = adjacent_cities(player,unit.pos)
                    # order cities by decreasing size
                    cities = collections.OrderedDict(sorted(cities.items(), key=lambda x: x[-1]))
                    if len(cities)>0:
                        is_any_city_in_danger = False
                        for city,city_payload in cities.items():
                            autonomy = city_payload[1]
                            if autonomy<time_to_dawn:
                                print(prefix, 'night, city in danger',city.cityid,'sz/aut/dir',city_payload, file=sys.stderr)
                                is_any_city_in_danger=True
                                break

                        if is_any_city_in_danger:
                            #todo maybe we should choose a city that we can save by moving there?
                            print(prefix, 'try to save city', city.cityid, city_payload, file=sys.stderr)
                            move_unit_to(actions, city_payload[2], move_mapper, unit, " try to save")
                            continue

                if move_mapper.is_position_city(unit.pos):
                    print(prefix, ' it is night, we are in city, do not move', file=sys.stderr)
                    continue

            #DAWN

            if steps_until_night==30:
                print(prefix, "It's dawn", steps_until_night, file=sys.stderr)
                if is_position_adjacent_to_resource(wood_tiles, unit.pos) and is_cell_empty(unit.pos, game_state)\
                        and 0<unit.get_cargo_space_left()<=21:
                    print(prefix, ' at dawn, can build next day', file=sys.stderr)
                    continue

            #   TRAVELER
            if info.is_role_traveler():
                print(prefix, ' is traveler to', info.target_position, file=sys.stderr)
                direction = get_direction_to(move_mapper, player, unit.pos, info.target_position)
                if direction is not None:
                    move_unit_to(actions, direction, move_mapper, unit, " move to traveler pos", info.target_position)
                    continue

            #   HASSLER
            if info.is_role_hassler():
                print(prefix, ' is hassler', file=sys.stderr)
                if is_position_adjacent_city(opponent, unit.pos):
                    print(prefix, ' hassler arrived to enemy', file=sys.stderr)
                    if unit.can_build(game_state.map):
                        build_city(actions, unit, 'hassler build next to city, and done!')
                        info.clean_unit_role()
                        continue
                    elif unit.get_cargo_space_left() == 0 and closest_empty_tile is not None:

                        print(prefix, " hassler full and close to empty, trying to move and build",
                              closest_empty_tile.pos, file=sys.stderr)
                        direction = unit.pos.direction_to(closest_empty_tile.pos)
                        next_pos = unit.pos.translate(direction, 1)
                        move_unit_to(actions, direction, move_mapper, unit,
                                     " move to build nearby enemy",
                                     next_pos)
                        continue

                else:
                    enemy_surrounding = find_closest_adjacent_enemy_city_tile(unit.pos, opponent)
                    direction = unit.pos.direction_to(enemy_surrounding.pos)
                    # if nobody is already moving there
                    if not move_mapper.has_position(enemy_surrounding.pos):
                        move_unit_to(actions, direction, move_mapper, unit, " move to enemy", enemy_surrounding.pos)
                        continue

                continue
            #   HASSLER ENDS

            # build city tiles adjacent of other tiles to make only one city.
            if unit.can_build(game_state.map):
                if is_position_adjacent_city(player, unit.pos):
                    build_city(actions, unit, 'in adjacent city!')
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
                                move_unit_to(actions, direction, move_mapper, unit,
                                             " we could have build here, but we move close to city instead", next_pos)
                                continue

                if steps_until_night > 1 or (
                        steps_until_night == 1 and is_position_adjacent_to_resource(available_resources_tiles,
                                                                                    unit.pos)):
                    build_city(actions, unit, 'NOT in adjacent city')
                    continue
            #
            resources_distance = find_resources_distance(unit.pos, player, all_resources_tiles, game_info)

            # if unit cant make city tiles try to collect resource collection.
            city_tile_distance = find_city_tile_distance(unit.pos, player, unsafe_cities)

            enough_fuel = 600
            if steps_until_night<4:
                enough_fuel = 400
            if is_night:
                enough_fuel = 300

            if unit.get_cargo_space_left() > 0 \
                    and (cargo_to_fuel(unit.cargo) < enough_fuel or len(unsafe_cities) == 0 or info.is_role_hassler()):
                if not is_position_resource(available_resources_tiles, unit.pos):
                    # find the closest resource if it exists to this unit

                    print(prefix, " Find resources", file=sys.stderr)

                    if resources_distance is not None and len(resources_distance) > 0:
                        # create a move action to the direction of the closest resource tile and add to our actions list
                        direction, pos, msg, resource_type = find_best_resource(move_mapper, player, resources_distance,
                                                                                unit)
                        if (resource_type == Constants.RESOURCE_TYPES.COAL and not player.researched_coal()) \
                                or (resource_type == Constants.RESOURCE_TYPES.URANIUM and not player.researched_uranium()):
                            distance_to_res=pos.distance_to(unit.pos)
                            print(prefix, " Found resource not yet researched:", resource_type,"dist",distance_to_res, file=sys.stderr)
                            info.set_unit_role_traveler(pos, 2 * distance_to_res)
                        move_unit_to(actions, direction, move_mapper, unit, msg, pos)
                        continue
                else:
                    print(prefix, " Stay on resources", file=sys.stderr)
                    continue
            else:
                if steps_until_night > 10 and can_build and unit.get_cargo_space_left() <= 20 and is_position_resource(
                        available_resources_tiles, unit.pos) and closest_empty_tile is not None:
                    # if we are on a resource, and we can move to an empty tile,
                    # then it means we can at least collect 20 next turn on CD and then build
                    # find the closest empty tile it to build a city
                    direction = unit.pos.direction_to(closest_empty_tile.pos)
                    move_unit_to(actions, direction, move_mapper, unit,
                                 " towards closest empty (anticipating getting resources)", closest_empty_tile.pos)
                elif steps_until_night > 10 and can_build and unit.get_cargo_space_left() == 0 and closest_empty_tile is not None:
                    # find the closest empty tile it to build a city
                    direction = unit.pos.direction_to(closest_empty_tile.pos)
                    move_unit_to(actions, direction, move_mapper, unit, " towards closest empty ",
                                 closest_empty_tile.pos)
                else:
                    print(prefix, " Goto city", file=sys.stderr)
                    # find closest city tile and move towards it to drop resources to a it to fuel the city
                    if city_tile_distance is not None and len(city_tile_distance) > 0 and not info.is_role_hassler():
                        print(prefix, " Goto city2", file=sys.stderr)
                        direction, pos, msg = find_best_city(city_tile_distance, move_mapper, player, unit)
                        move_unit_to(actions, direction, move_mapper, unit, msg, pos)

    #     print(move_mapper)
    #     print('')
    return actions


def get_direction_to(move_mapper, player, from_pos, to_pos):
    if from_pos.equals(to_pos):
        return DIRECTIONS.CENTER

    directions = directions_to(from_pos, to_pos)
    for direction in directions:
        next_pos = from_pos.translate(direction, 1)

        # if we are trying to move on top of somebody else, abort
        # print(prefix, ' XXX - try', direction, next_pos, file=sys.stderr)
        if move_mapper.cannot_move_to(next_pos):
            # print(prefix, ' XXX - skip', file=sys.stderr)
            continue
        else:
            return direction

    return None


def find_best_city(city_tile_distance, move_mapper: MoveHelper, player, unit):
    closest_city_tile = None
    moved = False
    for city_tile, dist in city_tile_distance.items():
        if not move_mapper.has_position(city_tile.pos):
            closest_city_tile = city_tile

            if closest_city_tile is not None:
                direction = get_direction_to(move_mapper, player, unit.pos, closest_city_tile.pos)
                if direction is not None:
                    moved = True
                    return direction, closest_city_tile.pos, " towards closest city distancing and autonomy" + dist.__str__()

    if not moved:
        direction = get_random_step()
        return direction, None, "randomly (due to city)"


def find_best_resource(move_mapper: MoveHelper, player, resources_distance, unit):
    closest_resource_tile, c_dist = None, None
    moved = False
    # print(prefix, " XXX Find resources dis", resources_distance.values(), file=sys.stderr)
    # print(prefix, " XXX Find resources pos", resources_distance.keys(), file=sys.stderr)
    # print(prefix, " XXX Move mapper", move_mapper.keys(), file=sys.stderr)
    for resource, resource_dist_info in resources_distance.items():

        # print(prefix, " XXX - ", resource.pos, resourse_dist_info, file=sys.stderr)
        if resource is not None and not resource.pos.equals(unit.pos):
            direction = get_direction_to(move_mapper, player, unit.pos, resource.pos)
            if direction is not None:
                moved = True
                return direction, resource.pos, " towards closest resource ", resource_dist_info[2]

    if not moved:
        direction = get_random_step()
        return direction, None, "randomly (due to resource)", ""


def get_autonomy_turns(city):
    turns_city_can_live = city.fuel // city.get_light_upkeep()
    return turns_city_can_live


def build_city(actions, unit, msg=''):
    action = unit.build_city()
    actions.append(action)
    print("Unit", unit.id, '- build city', msg, file=sys.stderr)


def can_build_for_resources(night_steps_left, lowest_autonomy, steps_until_night, player):
    if steps_until_night > 20:
        return True
    elif lowest_autonomy > 12 and steps_until_night > 10:
        return True

    can_build = True
    for city in player.cities.values():
        city_can_live = can_city_live(city, night_steps_left)
        if not city_can_live:
            can_build = False
            break
    return can_build


def can_city_live(city, night_steps_left):
    return city.fuel / (city.get_light_upkeep() + 20) >= min(night_steps_left, 30)


def move_unit_to(actions, direction, move_mapper: MoveHelper, unit, reason="", target_far_position=None):
    next_state_pos = unit.pos.translate(direction, 1)

    if direction == DIRECTIONS.CENTER or next_state_pos.equals(unit.pos):
        # do not annotate
        print("Unit", unit.id, '- not moving "', '', '" ', reason, file=sys.stderr)
        move_mapper.add_position(unit.pos, unit)
    else:
        if target_far_position is not None:
            # target_far_position is only used for the annotation line
            actions.append(annotate.line(unit.pos.x, unit.pos.y, target_far_position.x, target_far_position.y))
            # actions.append(annotate.text(unit.pos.x, unit.pos.y, reason))

        action = unit.move(direction)
        actions.append(action)
        move_mapper.add_position(next_state_pos, unit)
        print("Unit", unit.id, '- moving towards "', direction, '" :', reason, str(target_far_position or '') , file=sys.stderr)


def is_position_adjacent_city(player, pos, do_log=False):
    for city in player.cities.values():
        for city_tile in city.citytiles:
            if city_tile.pos.is_adjacent(pos):
                if do_log:
                    print(pos, "is_position_adjacent_city", city_tile.pos, file=sys.stderr)
                return True

    return False


def is_position_adjacent_to_resource(resource_tiles, pos):
    for r in resource_tiles:
        if r.pos.is_adjacent(pos):
            return True
    return False


def is_position_resource(resource_tiles, pos):
    for r in resource_tiles:
        if r.pos.equals(pos):
            return True
    return False


def try_to_move_to(actions, move_mapper, unit, pos: Position, msg: str):
    direction = unit.pos.direction_to(pos)
    # if nobody is already moving there
    if not move_mapper.has_position(pos):
        move_unit_to(actions, direction, move_mapper, unit, msg, pos)
        return True
    else:
        return False

def get_resources_around(resource_tiles, pos, max_dist):
    resources=[]
    for r in resource_tiles:
        if pos.distance_to(r.pos)<=max_dist:
            resources.append(r)

    return resources

#return dist of cities, autonomy
def adjacent_cities(player, pos, do_log=False):
    cities={}
    for city in player.cities.values():
        for city_tile in city.citytiles:
            if city_tile.pos.is_adjacent(pos):
                if do_log:
                    print(pos, "adjacent_cities", city_tile.pos, file=sys.stderr)
                cities[city] = (len(city.citytiles),get_autonomy_turns(city),directions_to(pos,city_tile.pos)[0])

    return cities
