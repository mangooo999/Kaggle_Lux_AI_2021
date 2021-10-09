import math
import os
import sys
import collections
import random
import time

random.seed(50)

from game_state_info.game_state_info import GameStateInfo

from typing import Optional, List, Dict, Tuple, DefaultDict, Sequence

from lux.game import Game
from lux.game_map import Cell, Position, RESOURCE_TYPES
from lux import annotate

from UnitInfo import UnitInfo
from GameInfo import GameInfo
from MoveHelper import MoveHelper
from lux.game_objects import CityTile, Unit, City, DIRECTIONS

from cluster.cluster import Cluster
import resources.resource_helper as ResourceService
from cluster.cluster_controller import ClusterControl
import maps.map_analysis as MapAnalysis

# todo
# in the night if staying in a city that is dyng, get out
# we need to be more aggressive in building from more than one dirction in maps as this, 389382500, https://www.kaggle.com/c/lux-ai-2021/submissions?dialog=episodes-episode-27529561
# create worker after researched evrything? https://www.kaggle.com/c/lux-ai-2021/submissions?dialog=episodes-episode-27515124
# avoid initially (use time to night?) to bring too much resources to city, try to build first 665769394 https://www.kaggle.com/c/lux-ai-2021/submissions?dialog=episodes-episode-27514151
# fix logic of early rush to non researched resource, we seem to rush too early
# extend isolated city logic from <20 turn to < 28
# if you are stuck near resources, near a lot of enemy, do not backoff, either stay near resource or move to resource, or build!!! -> 259 433371401 https://www.kaggle.com/c/lux-ai-2021/submissions?dialog=episodes-episode-27510931
# could try to extend city towards resources coal see turn 23-> 489695875
# optimise more first move in case enemy is just adjacent (586755628)
# extend first move logic to any movement from city to resource
# if moving to a city, remove move that move via another city, we can use a similar approach to cluster and have returner pointing to a city in role, and avoid others
# turn 200 seems to be a good turn to go and conquer unexplored wood cluster as it seems to make till 360
# remove from resources guarded cluster
# for path as a traveller favour tiles with resources
# for path as a resource seek favour tiles with cities
# try to build the city in the right direction (that is in the direction of other resources rather than towards the hedges) 308000419  https://www.kaggle.com/c/lux-ai-2021/submissions?dialog=episodes-episode-27481418
# we seem to have a very week logic if numerous units in the same area are without a cluster at the same time, we need to reuse here the logic we use in cluster move
# we seem to go to un-researched resources too early https://www.kaggle.com/c/lux-ai-2021/submissions?dialog=episodes-episode-27483344
# if there are good clusters at more than 15 resources away, stock up and travel far

### Define helper functions

import builtins as __builtin__


# this snippet finds all resources stored on the map and puts them into a list so we can search over them
def pr(*args, sep=' ', end='\n', f=False):  # known special case of print
    if False:
        print(*args, sep=sep)
    elif f:
        print(*args, sep=sep, file=sys.stderr)


def adjacent_empty_tile_favor_close_to_city_and_res(empty_tyles, game_state, player, resource_tiles, prefix) -> \
        Optional[Cell]:
    if len(empty_tyles) == 0:
        return None
    elif len(empty_tyles) == 1:
        return game_state.map.get_cell_by_pos(empty_tyles[0])
    else:
        # pr(prefix,"Trying to solve which empty one is close to most cities tiles")
        results = {}
        # pr(prefix,"XXXX1 adjacent_empty_tile_favor_close_to_city empty_tyles" , empty_tyles)

        for adjacent_position in empty_tyles:
            adjacent_city_tiles, adjacent_city = MapAnalysis.find_number_of_adjacent_city_tile(adjacent_position,
                                                                                               player)
            adjacent_res = len(MapAnalysis.get_resources_around(resource_tiles, adjacent_position, 1))
            adjacent_res2 = len(MapAnalysis.get_resources_around(resource_tiles, adjacent_position, 2))
            # results[adjacent_position] = (adjacent_city,adjacent_city_tiles, adjacent_res,adjacent_res2)
            results[adjacent_position] = (adjacent_city, adjacent_city_tiles, adjacent_res)

            # pr(prefix,"- XXXX1b",adjacent_position,results[adjacent_position])

        # pr(prefix,"XXXX2 adjacent_empty_tile_favor_close_to_city", results)
        # ordered by number of tiles, so we take last element
        results = dict(collections.OrderedDict(sorted(results.items(), key=lambda x: x[1], reverse=True)))
        # pr(prefix,"XXXX3 adjacent_empty_tile_favor_close_to_city", results)
        result = next(iter(results.keys()))

        # pr("Return", result)
        return game_state.map.get_cell_by_pos(result)


def empty_tile_near_wood_and_city(empty_tiles, wood_tiles, game_state, player) -> Optional[Cell]:
    results = {}
    for adjacent_position in empty_tiles:
        number_of_adjacent, cities = MapAnalysis.find_number_of_adjacent_city_tile(adjacent_position, player)
        if number_of_adjacent > 0 and MapAnalysis.is_position_adjacent_to_resource(wood_tiles, adjacent_position):
            results[number_of_adjacent] = adjacent_position
            # pr("- ",adjacent_position,number_of_adjacent)

    results = dict(sorted(results.items()))
    # ordered by number of tiles, so we take last element
    # pr("results", results)
    if len(results) == 0:
        # pr("Return None")
        return None
    else:
        result = list(results.values())[-1]

    # pr("Return", result)
    return game_state.map.get_cell_by_pos(result)


# snippet to find the all city tiles distance and sort them.
def find_city_tile_distance(pos: Position, player, unsafe_cities) -> Dict[CityTile, Tuple[int, int, int, str]]:
    city_tiles_distance: Dict[CityTile, Tuple[int, int, int, str]] = {}
    if len(player.cities) > 0:
        closest_dist = math.inf
        # the cities are stored as a dictionary mapping city id to the city object, which has a citytiles field that
        # contains the information of all citytiles in that city
        for k, city in player.cities.items():
            if city.cityid in unsafe_cities:
                for city_tile in city.citytiles:
                    dist = city_tile.pos.distance_to(pos)
                    # order by distance asc, autonomy desc
                    city_tiles_distance[city_tile] = (dist, get_autonomy_turns(city), -len(city.citytiles), city.cityid)
    # order by
    # - increasing distance (closest city first),
    # - increasing autonomy (smallest autonomy first)
    # - decreasing size (biggest cities first)

    city_tiles_distance = collections.OrderedDict(sorted(city_tiles_distance.items(), key=lambda x: x[1]))
    #     pr(len(city_tiles_distance))
    return city_tiles_distance


def get_random_step(from_pos: Position, move_mapper: MoveHelper) -> DIRECTIONS:
    random_sequence = random.choice([0, 1, 2, 3])
    # randomly choose which sequence to start with, so not to have a rotational probailistic skew
    if random_sequence == 0:
        directions = [DIRECTIONS.SOUTH, DIRECTIONS.NORTH, DIRECTIONS.WEST, DIRECTIONS.EAST]
    elif random_sequence == 1:
        directions = [DIRECTIONS.EAST, DIRECTIONS.SOUTH, DIRECTIONS.NORTH, DIRECTIONS.WEST]
    elif random_sequence == 2:
        directions = [DIRECTIONS.WEST, DIRECTIONS.EAST, DIRECTIONS.SOUTH, DIRECTIONS.NORTH]
    else:
        directions = [DIRECTIONS.NORTH, DIRECTIONS.WEST, DIRECTIONS.EAST, DIRECTIONS.SOUTH]

    for direction in directions:
        if move_mapper.can_move_to_direction(from_pos, direction, game_state):
            return direction
    # otherwise
    return DIRECTIONS.CENTER


def cargo_to_string(cargo) -> str:
    return_value = ''
    if cargo.wood > 0:
        return_value = return_value + f"Wood:{cargo.wood}"
    if cargo.coal > 0:
        return_value = return_value + f" Coal:{cargo.coal}"
    if cargo.uranium > 0:
        return_value = return_value + f" Uran:{cargo.uranium}"

    return return_value


game_state = None
unit_info: DefaultDict[str, UnitInfo] = {}
game_info = GameInfo(pr)
clusters: ClusterControl
start_time = 0


def agent(observation, configuration):
    global game_state
    global clusters
    global start_time

    ### Do not edit ###
    if observation["step"] == 0:
        game_state = Game()
        game_state._initialize(observation["updates"])
        game_state._update(observation["updates"][2:])
        game_state.id = observation.player

        # This is the start of the game
        clusters = ClusterControl(game_state,pr)
        start_time = time.time()

    else:
        game_state._update(observation["updates"])

    actions = []

    ### AI Code goes down here! ###
    game_state_info: GameStateInfo = GameStateInfo(game_state.turn,pr)

    # the below is very expensive and at the moment is only used to get_direction_to_smart
    # game_state.calculate_features(Missions())
    player = game_state.players[observation.player]
    opponent = game_state.players[(observation.player + 1) % 2]
    move_mapper = MoveHelper(player, opponent, game_state.turn,pr)

    # add debug statements like so!
    if game_state.turn == 0:
        pr("Agent is running!")
    pr("---------Turn number ", game_state.turn)
    t_prefix = "T_" + str(game_state.turn)
    game_info.update(player, game_state)

    # The first thing we do is updating the cluster.
    # Refer to the cluster class for its attributes.
    clusters.update(game_state, player, opponent, unit_info)

    # current number of units
    units = len(player.units)
    unit_number = 0

    all_resources_tiles, available_resources_tiles, wood_tiles = ResourceService.find_all_resources(game_state, player)
    if game_state.turn == 0:
        # initial calculations
        initial_city_pos = list(player.cities.values())[0].citytiles[0].pos
        initial_cluster: Cluster = None
        for cluster in clusters.get_clusters():
            if len(cluster.units) > 0:
                initial_cluster = cluster
                pr(t_prefix, "initial cluster", initial_cluster.to_string_light())

        x3: list = MapAnalysis.get_resources_around(available_resources_tiles, initial_city_pos, 3)
        game_info.at_start_resources_within3 = len(x3)
        pr(t_prefix, "Resources within distance 3 of", initial_city_pos, "initial pos", len(x3))

        possible_positions = MapAnalysis.get_12_positions(initial_city_pos, game_state)
        good_pos_around_city = get_best_first_move(t_prefix, game_state, initial_city_pos, move_mapper,
                                                   possible_positions, wood_tiles)

        # check if we should move very quickly to another cluster
        distance = math.inf
        better_cluster_pos = None
        for cluster in clusters.get_clusters():
            if cluster.res_type == RESOURCE_TYPES.WOOD and cluster.has_no_units_no_enemy():
                r_pos, r_distance = MapAnalysis.get_closest_position_cells(initial_city_pos, cluster.resource_cells)
                res = cluster.resource_cells.__len__()
                if res > 2 * len(initial_cluster.resource_cells) and r_distance < 12 and r_distance < distance:
                    pr(t_prefix, 'There seems to be a better cluster', cluster.to_string_light())
                    better_cluster_pos = r_pos
                    distance = r_distance

        if better_cluster_pos is not None:
            good_pos_around_city = better_cluster_pos

        # END initial calculations

    # Spawn of new troops and assigment of roles below
    for unit in player.units:
        unit_number = unit_number + 1
        if not unit.id in unit_info:
            # new unit
            unit_info[unit.id] = UnitInfo(unit,pr)
            # first move exist
            if game_state.turn == 0 and good_pos_around_city is not None:
                unit_info[unit.id].set_unit_role_traveler(good_pos_around_city,
                                                          2 * initial_city_pos.distance_to(good_pos_around_city))
                unit_info[unit.id].set_build_if_you_can()
            elif unit_number == 2 and units == 2:
                unit_info[unit.id].set_unit_role('expander')
            # elif unit_number == 5 and units == 5:
            #    unit_info[unit.id].set_unit_role('hassler')
        else:
            unit_info[unit.id].update(unit, game_state.turn)

    # clusters management
    clust_analyses: dict[str, Sequence[Tuple]] = {}
    for cluster in clusters.get_clusters():
        pr(t_prefix, 'cluster', cluster.to_string_light())
        clust_analyses[cluster.id] = []
        if len(cluster.units) == 0:
            continue

        for next_clust in clusters.get_clusters():
            # we olny consider wood cluster
            # we olny consider uncontended and empty cluster
            if next_clust.id != cluster.id \
                    and is_resource_minable(player, next_clust.res_type, game_info.get_research_rate(5), 4) \
                    and next_clust.has_no_units():
                for unitid in cluster.units:
                    unit = player.units_by_id[unitid]

                    info = None
                    if unitid in unit_info:
                        info = unit_info[unitid]

                    if unit.get_cargo_space_left() == 0:
                        # do not consider units that can build
                        continue

                    # the distance to reach it
                    r_pos, distance = MapAnalysis.get_closest_position_cells(unit.pos, next_clust.resource_cells)
                    time_distance = 2 * (distance - 1) + unit.cooldown

                    # TODO we could try to add here the resources if we are sure it doesn't pass from a city
                    # # we only consider reachable clusters before the night
                    if time_distance > game_state_info.steps_until_night:
                        continue
                    if info is None:
                        continue
                    if not info.is_role_none():
                        continue

                    clust_analyses[cluster.id].append(
                        (distance,
                         unit,
                         next_clust,
                         r_pos,
                         time_distance + next_clust.score,
                         time_distance))

        # sort on distance
        clust_analyses[cluster.id].sort(key=lambda x: (x[4]))  # score

    for cluster in clusters.get_clusters():
        if len(clust_analyses[cluster.id]) == 0:
            continue
        # else:

        # first element of sequence associated to this cluster analyses is the closest cluster
        closest_cluster = next(iter(clust_analyses[cluster.id]), None)
        # find the closest unit of cluster to next cluster
        closest_cluster_dist: int = closest_cluster[0]
        closest_cluster_unit: Unit = closest_cluster[1]
        closest_cluster_cluster: Cluster = closest_cluster[2]
        closest_cluster_pos: Position = closest_cluster[3]

        move_to_closest_cluster: bool = False
        if cluster.res_type == RESOURCE_TYPES.WOOD and cluster.has_eq_gr_units_than_res() and cluster.num_units() > 1:
            pr(t_prefix, 'cluster', cluster.id, ' is overcrowded u=r, u=', cluster.units)
            move_to_closest_cluster = True

        if cluster.res_type == RESOURCE_TYPES.WOOD and cluster.num_units() > 6:
            pr(t_prefix, 'cluster', cluster.id, ' is overcrowded u>6, u=', cluster.units)
            move_to_closest_cluster = True

        if cluster.res_type == RESOURCE_TYPES.WOOD and cluster.num_units() > 1 and closest_cluster_dist < 4:
            pr(t_prefix, 'There is a very near uncontested cluster', closest_cluster_cluster.id,
               'next to this cluster', cluster.id, 'at dist ', closest_cluster_dist)
            move_to_closest_cluster = True

        # if enemy is very far away from this cluster, and closest cluster is interesting, be more aggressive
        if cluster.num_units() > 3 \
                and cluster.closest_enemy_distance > 7 \
                and closest_cluster_cluster.get_equivalent_resources() > cluster.get_equivalent_resources():
            pr(t_prefix, 'Enemy is far away, move quickly ', closest_cluster_cluster.id,
               'next to this cluster', cluster.id, 'at dist ', closest_cluster_dist)
            move_to_closest_cluster = True

        if move_to_closest_cluster:
            pr(t_prefix, 'try_move_units_cluster closest_cluster ', closest_cluster_cluster.id)

            # the time in turns to reach it
            time_distance = 2 * (closest_cluster_dist - 1) + closest_cluster_unit.cooldown
            # pr(t_prefix, "XXX",target_cluster.id,
            #       'dist',target_dist,
            #       'time dist ',time_distance, 'with turns to night', game_state_info.steps_until_night,
            #       target_unit.pos, target_pos)
            if time_distance > game_state_info.steps_until_night:
                # unreachable before night
                pr(t_prefix, closest_cluster_cluster.id, 'is unreachble at a time distance ',
                   time_distance, 'with turns to night', game_state_info.steps_until_night,
                   closest_cluster_unit.pos, closest_cluster_pos)
            else:
                pr(t_prefix, ' repurposing', closest_cluster_unit.id, ' to explore closest_cluster',
                   closest_cluster_cluster.id, closest_cluster_cluster.get_centroid())
                unit_info[closest_cluster_unit.id].set_unit_role_explorer(
                    closest_cluster_cluster.get_centroid())

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

    # set unsafe cities, record how many available city actions we have
    if len(cities) > 0:
        for city in cities:
            will_live = get_autonomy_turns(city) >= game_state_info.all_night_turns_lef
            # collect unsafe cities
            if not will_live:
                unsafe_cities[city.cityid] = (
                    len(city.citytiles),
                    (game_state_info.all_night_turns_lef - get_autonomy_turns(city)) * city.get_light_upkeep())

            # record how many available city actions we have now
            for city_tile in city.citytiles[::-1]:
                number_city_tiles = number_city_tiles + 1
                if city_tile.can_act():
                    available_city_actions += 1
                if city_tile.cooldown <= 1:
                    available_city_actions_now_and_next += 1

    # logging
    if game_state.turn == 360:
        pr(t_prefix, "END C=", number_city_tiles, 'u=', len(player.units), 't=', str(time.time() - start_time), f=True)
    else:
        pr(t_prefix, "INT Cities", number_city_tiles, 'units', len(player.units))

    # todo move print in game_state_info class
    pr(t_prefix, 'resources', len(available_resources_tiles), 'units', units, 'unit_ceiling', unit_ceiling,
       'research', player.research_points, ' avail city points', available_city_actions)

    if (not player.researched_uranium()) and player.research_points + available_city_actions >= 200:
        do_research_points = 200 - player.research_points
        pr(t_prefix, 'We could complete uranium using', do_research_points, 'of', available_city_actions)
    elif (not player.researched_coal()) and player.research_points + available_city_actions >= 50:
        do_research_points = 50 - player.research_points
        pr(t_prefix, 'We could complete coal using', do_research_points, 'of', available_city_actions)
    elif (not player.researched_uranium()) and player.research_points + available_city_actions >= 200:
        do_research_points = 200 - player.research_points
        pr(t_prefix, 'We could complete NEXT uranium using', do_research_points, 'of',
           available_city_actions_now_and_next)
    elif (not player.researched_coal()) and player.research_points + available_city_actions_now_and_next >= 50:
        do_research_points = 50 - player.research_points
        pr(t_prefix, 'We could complete NEXT coal using', do_research_points, 'of',
           available_city_actions_now_and_next)

    number_work_we_can_build = available_city_actions - do_research_points
    number_work_we_want_to_build = unit_ceiling - units

    if len(available_resources_tiles) == 0 and game_info.still_can_do_reseach():
        number_work_we_want_to_build = 0

    # last ten turn, just build in case it is a tie
    if game_state.turn > 350:
        number_work_we_want_to_build = number_work_we_can_build

    # Find how many and where to create builders

    pr(t_prefix, 'number_work_we_can_build', number_work_we_can_build, 'number_work_we_want_to_build',
       number_work_we_want_to_build)

    ordered_tyles = {}
    if min(number_work_we_can_build, number_work_we_want_to_build) > 0:

        # choose in which tiles we want to create workers
        for city in cities:
            city_autonomy = get_autonomy_turns(city)
            will_live = city_autonomy >= game_state_info.all_night_turns_lef
            for city_tile in city.citytiles[::-1]:
                if city_tile.can_act():
                    units_around = MapAnalysis.get_units_around(player, city_tile.pos, 2)
                    res_around = len(MapAnalysis.get_resources_around(available_resources_tiles, city_tile.pos, 3))
                    dummy, closest_resource = MapAnalysis.get_closest_position_cells(city_tile.pos,
                                                                                     available_resources_tiles)
                    ordered_tyles[
                        (closest_resource, int(will_live), float(units_around) / float(res_around + 1))] = city_tile

        ordered_tyles = collections.OrderedDict(sorted(ordered_tyles.items(), key=lambda x: x[0]))
        # pr(t_prefix, "XXXX2 ", ordered_tyles)

    while min(number_work_we_can_build, number_work_we_want_to_build) > 0:
        for city_tile in ordered_tyles.values():
            # let's create one more unit in the last created city tile if we can
            actions.append(city_tile.build_worker())
            pr(t_prefix, city_tile.pos, "- created worker")
            number_work_we_can_build -= 1
            number_work_we_want_to_build -= 1

    if len(cities) > 0:
        for city in cities:
            for city_tile in city.citytiles[::-1]:
                # pr(t_prefix, "- C tile ", city_tile.pos, " CD=", city_tile.cooldown)
                if city_tile.can_act():
                    if game_state.turn < 30:  # TODO maybe this should be based on how close is the unit to build
                        # we are turn<30, we need to prioritise spawning in the right city rather than research
                        # if we have resources around here, but no units, do not research
                        near_resource = MapAnalysis.is_position_adjacent_to_resource(available_resources_tiles,
                                                                                     city_tile.pos)
                        near_units = len(get_units_around_pos(player, city_tile.pos, 2))
                        if near_resource and near_units == 0:
                            pr(t_prefix,
                               "- this city tile could do research, but better to wait till it can create a worker")
                            continue
                        # else:
                        # pr(t_prefix, "- - nothing")
                    if game_info.still_can_do_reseach():
                        # let's do research
                        game_info.do_research(actions, city_tile, str(city_tile.pos) + " research")

    pr(t_prefix, "Unsafe cities", unsafe_cities)

    # trace the agent move
    # store all unit current location on move tracker
    for unit in player.units:
        if not unit.can_act():
            move_mapper.add_position(unit.pos, unit)

    # map of resource to unit going for them
    resource_target_by_unit = {}

    for unit in player.units:
        info: UnitInfo = unit_info[unit.id]
        u_prefix: str = "T_" + game_state.turn.__str__() + str(unit.id)

        pr(u_prefix, ";pos", unit.pos, 'CD=', unit.cooldown, cargo_to_string(unit.cargo), 'fuel=',
           unit.cargo.fuel(), 'canBuildHere', unit.can_build(game_state.map), 'role', info.role)

        if (move_mapper.is_position_city(unit.pos) and 2 < game_state.turn < 15 and number_city_tiles == 1
                and len(player.units) == 1):
            pr(u_prefix, ' NEEDS to become an expander')
            info.set_unit_role('expander', u_prefix)

        if unit.is_worker() and unit.can_act():
            # SHORTCUTS
            # in SHORTCUTS
            in_city = move_mapper.is_position_city(unit.pos)
            in_empty = MapAnalysis.is_cell_empty(unit.pos, game_state)
            in_resource, near_resource = MapAnalysis.is_position_in_X_adjacent_to_resource(available_resources_tiles,
                                                                                           unit.pos)

            # near SHORTCUTS
            near_wood = MapAnalysis.is_position_adjacent_to_resource(wood_tiles, unit.pos)
            near_city = MapAnalysis.is_position_adjacent_city(player, unit.pos)

            # adjacent SHORTCUTS
            adjacent_empty_tiles = MapAnalysis.find_all_adjacent_empty_tiles(game_state, unit.pos)
            best_adjacent_empty_tile = adjacent_empty_tile_favor_close_to_city_and_res(
                adjacent_empty_tiles, game_state, player, available_resources_tiles, u_prefix)
            resources_distance, adjacent_resources = ResourceService.find_resources_distance(
                unit.pos, player, all_resources_tiles, game_info)
            city_tile_distance = find_city_tile_distance(unit.pos, player, unsafe_cities)
            adjacent_next_to_resources = get_walkable_that_are_near_resources(
                u_prefix, move_mapper, MapAnalysis.get_4_positions(unit.pos, game_state), available_resources_tiles)
            adjacent_units = get_units_around_pos(player, unit.pos, 1)

            # enemy SHORTCUTS
            num_adjacent_enemy_unit = get_units_number_around_pos(opponent, unit.pos, 1)
            num_hostiles_within2 = get_units_and_city_number_around_pos(opponent, unit.pos, 2)
            is_in_highly_hostile_area = num_hostiles_within2 > 5

            pr(u_prefix, 'adjacent_empty_tiles', [x.__str__() for x in adjacent_empty_tiles],
               'favoured', best_adjacent_empty_tile.pos if best_adjacent_empty_tile else '')

            #   EXPLORER
            if info.is_role_explorer():
                pr(u_prefix, ' is explorer ', info.target_position)
                if game_state_info.turns_to_night <= 2:
                    pr(u_prefix, ' explorer failed as too close to night')
                else:
                    # check if the target position is achievable
                    cluster = clusters.get_cluster_from_centroid(info.target_position)
                    if cluster is not None:
                        target_pos, distance = cluster.get_closest_distance_to_perimeter(unit.pos)
                        pr(u_prefix, ' explorer is to cluster', cluster.id)
                    else:
                        target_pos = info.target_position
                        distance = unit.pos.distance_to(info.target_position)

                    if distance <= (game_state_info.turns_to_night + 1) / 2:
                        pr(u_prefix, ' explorer will go to', target_pos, 'dist', distance)
                        info.set_unit_role_traveler(target_pos, 2 * distance)
                    else:
                        pr(u_prefix, ' dist', distance, ' to ', target_pos, 'not compatible with autonomy')

                if info.is_role_explorer():
                    pr(u_prefix, ' failed to find resource for explorer, clearing role')
                    info.clean_unit_role()

            #   EXPANDER
            if info.is_role_city_expander() and unit.get_cargo_space_left() > 0 and num_adjacent_enemy_unit == 0:
                pr(u_prefix, ' is expander')

                # all action expander are based on building next turn. We don't build at last day, so skip if day before
                if game_state_info.turns_to_night > 1:
                    if near_city and (not in_city) and near_wood:
                        # if we are next to city and to wood, just stay here
                        pr(u_prefix, ' expander we are between city and wood do not move')
                        continue

                    # if we have the possibility of going in a tile that is like the  above
                    expander_spot = empty_tile_near_wood_and_city(adjacent_empty_tiles, wood_tiles,
                                                                  game_state, player)
                    if expander_spot is not None:
                        if try_to_move_to(actions, move_mapper, info, expander_spot.pos, " expander to perfect pos"):
                            continue

            #   EXPANDER ENDS

            # night rules
            if game_state_info.is_night_time() or game_state_info.is_night_tomorrow():
                # time_to_dawn differs from game_state_info.turns_to_dawn as it could be even 11 on turn before night
                time_to_dawn = 10 + game_state_info.steps_until_night

                pr(u_prefix, ' it is night...', 'time_to_dawn', time_to_dawn,
                   'inCity:', in_city, 'empty:', in_empty, 'nearwood:', near_wood)

                # search for adjacent cities in danger
                if game_state_info.is_night_time() and unit.cargo.fuel() > 0 and not in_city:
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
                                pr(u_prefix, 'night, city in danger', city.cityid, 'sz/aut/dir', city_payload)
                                is_any_city_in_danger = True
                                break

                        if is_any_city_in_danger:
                            # todo maybe we should choose a city that we can save by moving there?
                            pr(u_prefix, 'try to save city', city.cityid, city_payload)
                            move_unit_to(actions, city_payload[2], move_mapper, info, " try to save a city")
                            continue

                if near_wood and in_empty:
                    pr(u_prefix, ' it is night, we are in a empty cell near resources')
                    # empty near a resource, we can stay here, but we could even better go to same near city

                    # if we have the possibility of going in a tile that is empty_tile_near_wood_and_city, then go
                    best_night_spot = empty_tile_near_wood_and_city(adjacent_empty_tiles, wood_tiles,
                                                                    game_state, player)
                    if best_night_spot is not None \
                            and try_to_move_to(actions, move_mapper, info, best_night_spot.pos, " best_night_spot"):
                        continue
                    else:
                        pr(u_prefix, ' it is night, we will stay here')
                        continue

                # if we have the possibility of going in a tile that is empty_tile_near_wood_and_city
                # go if not in a city, or if you are in a city, go just last 1 days of night (so we gather and covered)
                if (not in_city) or time_to_dawn <= 1:
                    best_night_spot = empty_tile_near_wood_and_city(adjacent_empty_tiles, wood_tiles,
                                                                    game_state, player)
                    if best_night_spot is not None \
                            and try_to_move_to(actions, move_mapper, info, best_night_spot.pos, " best_night_spot"):
                        continue

                if in_city:
                    if near_resource:
                        pr(u_prefix, ' it is night, we are in city, next resource, do not move')
                    else:
                        # not near resource
                        pr(u_prefix, ' it is night, we are in city, not next resource, do not move')
                        for pos in adjacent_next_to_resources.keys():
                            if move_mapper.can_move_to_pos(pos, game_state) and not move_mapper.has_position(pos):
                                direction = unit.pos.direction_to(pos)
                                move_unit_to(actions, direction, move_mapper, info, "night, next to resource")
                                break
                    continue

            # DAWN

            if game_state_info.is_dawn():
                pr(u_prefix, "It's dawn")
                if near_wood \
                        and in_empty \
                        and 0 < unit.get_cargo_space_left() <= 21:
                    pr(u_prefix, ' at dawn, can build next day')
                    continue

            # ALARM, we tried too many times the same move
            if info.alarm >= 4 and len(unsafe_cities) > 0:
                pr(u_prefix, ' has tried too many times to go to ', info.last_move_direction)
                if unit.can_build(game_state.map):
                    build_city(actions, info, u_prefix, ':we tried too many times to go to' + info.last_move_direction)
                else:
                    direction = get_random_step(unit.pos, move_mapper)
                    move_unit_to(actions, direction, move_mapper, info,
                                 "randomly, too many try to " + info.last_move_direction)
                continue

            #   TRAVELER
            if info.is_role_traveler():
                pr(u_prefix, ' is traveler to', info.target_position)
                if unit.can_build(game_state.map) and info.build_if_you_can:
                    pr(u_prefix, ' traveler build')
                    build_city(actions, info, u_prefix, 'traveler build')
                    continue

                direction = get_direction_to_quick(game_state, info, info.target_position, move_mapper,
                                                   available_resources_tiles, unsafe_cities)
                if direction != DIRECTIONS.CENTER and move_mapper.can_move_to_direction(info.unit.pos, direction,
                                                                                        game_state):
                    move_unit_to(actions, direction, move_mapper, info, " move to traveler pos", info.target_position)
                    continue
                else:
                    pr(u_prefix, ' traveller cannot move')
                    if unit.pos.distance_to(info.target_position) <= 1:
                        info.clean_unit_role()

            #   RETURNER
            if info.is_role_returner():
                pr(u_prefix, ' is returner to', info.target_position)

                if len(unsafe_cities) == 0:
                    info.clean_unit_role()
                else:
                    if city_tile_distance is not None and len(city_tile_distance) > 0:
                        pr(u_prefix, " Returner city2")
                        direction, better_cluster_pos, msg = find_best_city(game_state, city_tile_distance, move_mapper,
                                                                            unsafe_cities, info)
                        move_unit_to_or_transfer(actions, direction, info, move_mapper, player, u_prefix, unit,
                                                 'returner')

            #   HASSLER
            if info.is_role_hassler():
                pr(u_prefix, ' is hassler')
                if MapAnalysis.is_position_adjacent_city(opponent, unit.pos):
                    pr(u_prefix, ' hassler arrived to enemy')
                    if unit.can_build(game_state.map):
                        build_city(actions, info, u_prefix, 'hassler build next to city, and done!')
                        info.clean_unit_role()
                        continue
                    elif unit.get_cargo_space_left() == 0 and best_adjacent_empty_tile is not None:

                        pr(u_prefix, " hassler full and close to empty, trying to move and build",
                           best_adjacent_empty_tile.pos)
                        direction = unit.pos.direction_to(best_adjacent_empty_tile.pos)
                        next_pos = unit.pos.translate(direction, 1)
                        move_unit_to(actions, direction, move_mapper, info,
                                     " move to build nearby enemy",
                                     next_pos)
                        continue

                else:
                    enemy_surrounding = MapAnalysis.find_closest_adjacent_enemy_city_tile(unit.pos, opponent)
                    direction = unit.pos.direction_to(enemy_surrounding.pos)
                    # if nobody is already moving there
                    if not move_mapper.has_position(enemy_surrounding.pos):
                        move_unit_to(actions, direction, move_mapper, info, " move to enemy", enemy_surrounding.pos)
                        continue

                continue
            #   HASSLER ENDS

            # build city tiles adjacent of other tiles to make only one city.
            if unit.can_build(game_state.map):
                if (num_adjacent_enemy_unit > 0 or is_in_highly_hostile_area) and unit.cargo.fuel() < 150:
                    build_city(actions, info, u_prefix, 'because we are close to enemy')
                    continue
                if near_city:
                    moved = False

                    # this is an excellent spot, but is there even a better one, one that join two different cities?
                    if game_state_info.turns_to_night > 2:
                        # only if we have then time to build after 2 turns cooldown
                        dummy, num_adjacent_here = MapAnalysis.find_number_of_adjacent_city_tile(unit.pos, player)
                        for adjacent_position in adjacent_empty_tiles:
                            # pr(u_prefix, "XXXXXXX ", num_adjacent_here)
                            dummy, num_adjacent_city = MapAnalysis.find_number_of_adjacent_city_tile(adjacent_position,
                                                                                                     player)
                            # pr(u_prefix, "XXXXXXX ", num_adjacent_city, adjacent_position)
                            if num_adjacent_city > num_adjacent_here and move_mapper.can_move_to_pos(adjacent_position,
                                                                                                     game_state):
                                move_unit_to_pos(actions, move_mapper, info,
                                                 " moved to a place where we can build{0} instead".format(
                                                     str(num_adjacent_city))
                                                 , adjacent_position)
                                moved = True
                                break
                    if not moved:
                        build_city(actions, info, u_prefix, 'in adjacent city!')
                    continue

                else:  # if can build but we are not near city

                    # if we can move to a tile where we are adjacent, do and it and build there
                    if best_adjacent_empty_tile is not None:
                        pr(u_prefix, " check if adjacent empty is more interesting", best_adjacent_empty_tile.pos)
                        direction = unit.pos.direction_to(best_adjacent_empty_tile.pos)
                        next_pos = unit.pos.translate(direction, 1)
                        # if nobody is already moving there
                        if not move_mapper.has_position(next_pos):
                            pr(u_prefix, " and nobody is moving here")
                            # and if next pos is actually adjacent
                            if MapAnalysis.is_position_adjacent_city(player, next_pos):
                                move_unit_to(actions, direction, move_mapper, info,
                                             " we could have build here, but we move close to city instead", next_pos)
                                continue

                do_stop = False

                if game_state_info.turns_to_night > 1 or \
                        (game_state_info.turns_to_night == 1 and near_resource):
                    unit_fuel = unit.cargo.fuel()
                    if unit_fuel < 200:
                        build_city(actions, info, u_prefix,
                                   'NOT in adjacent city, we have not so much fuel ' + str(unit_fuel))
                        continue
                    else:
                        do_build = True
                        # check if there are cities next to us that are better served with our fuel
                        for city_tile, dist in city_tile_distance.items():
                            distance = dist[0]
                            city_size = abs(dist[2])
                            if city_size >= 5 and distance < 6:
                                do_build = False
                                pr(u_prefix, " we could have built NOT in adjacent city, but there is a need city close"
                               , city_tile.cityid)
                                break

                        if adjacent_resources:
                            # move away from resource
                            for empty in adjacent_empty_tiles:
                                if move_mapper.can_move_to_pos(empty, game_state):
                                    if not MapAnalysis.is_position_adjacent_to_resource(available_resources_tiles,
                                                                                        empty):
                                        direction = unit.pos.direction_to(empty)
                                        move_unit_to_or_transfer(actions, direction, info, move_mapper, player,
                                                                 u_prefix, unit, 'high resources')
                                        pr(u_prefix,
                                           " we could have built, but better moving far away from resurces")
                                        do_stop = True
                                        do_build = False

                        if do_build:
                            build_city(actions, info, u_prefix,
                                       'NOT in adjacent city, we have lot of fuel, but no city needs saving')
                            continue

                        if do_stop:
                            continue


            # IF WE CANNOT BUILD, or we could and have decided not to

            if in_empty and near_city and near_wood:
                # stay here, so we can build
                pr(u_prefix, " empty, near city, near wood, stay here")
                continue

            if is_in_highly_hostile_area:
                done = False
                pr(u_prefix, "hostile area;nearW=", near_wood, "inRes=", in_resource, 'inEmp=', in_empty)
                # we are in wood in a highly hostile area, rule for building already implemented,
                # here we try try to penetrate and not backoff
                if near_wood and in_empty:
                    pr(u_prefix, "hostile area, empty, near wood, stay here, so we can build")
                    continue
                if near_wood and not in_resource:
                    # only try to move near wood
                    for r in adjacent_resources:
                        if move_mapper.can_move_to_pos(r.pos, game_state):
                            move_unit_to_pos(actions, move_mapper, info, 'hostile area, from near to res', r.pos)
                            done = True
                            break
                if in_resource:
                    pr(u_prefix, "hostile area, in resource")
                    for friend in adjacent_units:
                        if MapAnalysis.is_cell_empty(friend.pos, game_state) and friend.get_cargo_space_left() > 0:
                            # pass the cargo on
                            transfer_all_resources(actions, info, friend.id)
                            done = True
                            break

                    if not done:
                        # if we didn't pass to somebody in empty, see if there is something empty
                        for empty in MapAnalysis.find_all_adjacent_empty_tiles(game_state, unit.pos):
                            if move_mapper.can_move_to_pos(empty, game_state):
                                move_unit_to_pos(actions, move_mapper, info, 'hostile area, from res to near', empty)
                                done = True
                                break

                if done:
                    continue

            if len(unsafe_cities) == 0:
                enough_fuel = math.inf
            else:
                if game_state_info.is_night_time():
                    enough_fuel = 500
                elif game_state_info.turns_to_night < 4:
                    enough_fuel = 300
                else:
                    enough_fuel = 400

            if (not info.is_role_returner()) and unit.get_cargo_space_left() > 0 \
                    and (unit.cargo.fuel() < enough_fuel or len(unsafe_cities) == 0 or info.is_role_hassler()):
                if not in_resource:
                    # find the closest resource if it exists to this unit

                    pr(u_prefix, " Find resources")

                    if resources_distance is not None and len(resources_distance) > 0:

                        # create a move action to the direction of the closest resource tile and add to our actions list
                        direction, better_cluster_pos, msg, resource_type = \
                            find_best_resource(game_state, move_mapper, resources_distance, resource_target_by_unit,
                                               info, available_resources_tiles, u_prefix, unsafe_cities)
                        if direction == DIRECTIONS.CENTER and len(unsafe_cities) == 0:
                            for empty in adjacent_empty_tiles:
                                friend = get_unit_in_pos(player, empty)
                                if friend is not None:
                                    if not MapAnalysis.is_position_adjacent_to_resource(available_resources_tiles,
                                                                                        empty):
                                        if near_resource:
                                            # if frien not near res and we are, transfer
                                            transfer_all_resources(actions, info, friend.id)
                                            break
                                        else:
                                            # if both near resourse, transfer to who has more
                                            if friend.get_cargo_space_left() > 0 and \
                                                    friend.get_cargo_space_left() < unit.get_cargo_space_left():
                                                transfer_all_resources(actions, info, friend.id)
                                                break

                        if (resource_type == RESOURCE_TYPES.COAL and not player.researched_coal()) or \
                                (resource_type == RESOURCE_TYPES.URANIUM and not player.researched_uranium()):
                            # this is a not researched yet resource, force to go there, so there is no jitter
                            distance_to_res = better_cluster_pos.distance_to(unit.pos)
                            pr(u_prefix, " Found resource not yet researched:", resource_type, "dist",
                               distance_to_res)
                            info.set_unit_role_traveler(better_cluster_pos, 2 * distance_to_res)

                        if better_cluster_pos is not None:
                            # append target to our map
                            resource_target_by_unit.setdefault((better_cluster_pos.x, better_cluster_pos.y), []).append(
                                unit.id)
                        move_unit_to(actions, direction, move_mapper, info, msg, better_cluster_pos)
                        continue
                    else:
                        pr(u_prefix, " resources_distance invalid (or empty?)")
                else:
                    resource_type = game_state.map.get_cell(unit.pos.x, unit.pos.y).resource.type
                    pr(u_prefix, " Already on resources:", resource_type)
                    if resource_type != RESOURCE_TYPES.WOOD \
                            and get_unit_in_pos(player, info.last_move_before_pos) is not None and \
                            move_mapper.can_move_to_direction(unit.pos, info.last_move_direction, game_state):
                        move_unit_to(actions, info.last_move_direction, move_mapper, info, 'move a bit further')
                    else:
                        resource_target_by_unit.setdefault((unit.pos.x, unit.pos.y), []).append(unit.id)
                        pr(u_prefix, " Stay on resources")
                    continue
            else:
                if game_state_info.turns_to_night > 10 and unit.get_cargo_space_left() <= info.gathered_last_turn \
                        and in_resource and best_adjacent_empty_tile is not None:
                    # if we are on a resource, and we can move to an empty tile,
                    # then it means we can at least collect 20 next turn on CD and then build
                    # find the closest empty tile it to build a city
                    move_unit_to_pos(actions, move_mapper, info,
                                     " towards closest empty (anticipating getting resources)",
                                     best_adjacent_empty_tile.pos)
                elif game_state_info.turns_to_night > 6 and unit.get_cargo_space_left() == 0 \
                        and best_adjacent_empty_tile is not None:
                    # find the closest empty tile it to build a city
                    move_unit_to_pos(actions, move_mapper, info, " towards closest empty ",
                                     best_adjacent_empty_tile.pos)
                elif unit.get_cargo_space_left() == 0 and unit.cargo.fuel() < 120 and game_state_info.turns_to_night > 10:
                    # we are full mostly with woods, we should try to build
                    for next_pos in MapAnalysis.get_4_positions(unit.pos, game_state):
                        # pr(t_prefix, 'XXXX',next_pos)
                        if move_mapper.can_move_to_pos(next_pos, game_state) and not move_mapper.is_position_city(
                                next_pos):
                            is_empty, has_empty_next = MapAnalysis.is_cell_empty_or_empty_next(next_pos, game_state)
                            potential_ok = (is_empty or has_empty_next)
                            # todo find the best, not only a possible one
                            if potential_ok:
                                move_unit_to_pos(actions, move_mapper, info, " towards closest next-best-empty ",
                                                 next_pos)
                                break

                elif not info.is_role_hassler():
                    pr(u_prefix, " Goto city; fuel=", unit.cargo.fuel())
                    # find closest city tile and move towards it to drop resources to a it to fuel the city
                    if city_tile_distance is not None and len(city_tile_distance) > 0:
                        pr(u_prefix, " Goto city2")
                        direction, better_cluster_pos, msg = find_best_city(game_state, city_tile_distance, move_mapper,
                                                                            unsafe_cities, info)
                        move_unit_to_or_transfer(actions, direction, info, move_mapper, player, u_prefix, unit, 'city')
                        if unit.cargo.fuel() >= 200 and info.is_role_none():
                            info.set_unit_role_returner(u_prefix)
                        continue

    # if this unit didn't do any action, check if we can transfer his cargo back in the direction this come from
    for unit in player.units:
        info: UnitInfo = unit_info[unit.id]
        u_prefix: str = "T_" + game_state.turn.__str__() + str(unit.id)
        # pr(prefix, "XXX check unit has worked", unit.can_act(), info.has_done_action_this_turn)
        if unit.is_worker() and unit.can_act() and not info.has_done_action_this_turn:
            pr(u_prefix, " this unit has not worked")
            if unit.cargo.coal > 0 or unit.cargo.uranium > 0:
                # check if anybody in the pos where we come from
                friend_unit = get_unit_in_pos(player, info.last_move_before_pos)
                if friend_unit is not None:
                    pr(u_prefix, " Do transfer to", friend_unit.id, ' in ', info.last_move_before_pos)
                    transfer_all_resources(actions, info, friend_unit.id)
                    if unit_info[unit.id].is_role_traveler:
                        unit_info[unit.id].clean_unit_role();

    # for i,j in resource_target_by_unit.items():
    #    pr("XXXX resources map ",game_info.turn,i,len(j))

    return actions


def get_best_first_move(t_prefix, game_state, initial_city_pos, move_mapper, possible_positions, resource_tiles):
    first_best_position = None
    first_move = {}

    result = get_walkable_that_are_near_resources(t_prefix, move_mapper, possible_positions, resource_tiles)
    for next_pos, res_2 in result.items():
        pr(t_prefix, next_pos, res_2)
        is_empty, has_empty_next = MapAnalysis.is_cell_empty_or_empty_next(next_pos, game_state)
        pr(t_prefix, 'Resources within 2 of', res_2, ';empty', is_empty,
           ';emptyNext', has_empty_next)

        res_4 = len(MapAnalysis.get_resources_around(resource_tiles, next_pos, 4))
        dist = initial_city_pos.distance_to(next_pos)

        if dist == 1 and is_empty and res_2 == 3:
            score = 1  # best as we can build in 2
        elif dist == 1 and is_empty and res_2 == 3:
            score = 2  # second best as we can build in 3
        elif is_empty or has_empty_next:
            score = 3  # everything that is either empty or
        else:
            score = 9

        first_move[next_pos] = (score, dist, -res_2, -res_4)
    pr(t_prefix, 'Not Ordered Resources within 2', first_move)
    if len(first_move.keys()) > 0:
        result = collections.OrderedDict(sorted(first_move.items(), key=lambda x: x[1]))
        pr(t_prefix, 'Ordered Resources within 2', result)
        first_best_position = next(iter(result.keys()))
        pr(t_prefix, 'first_best_position', first_best_position)
    return first_best_position


def get_walkable_that_are_near_resources(t_prefix, move_mapper, possible_positions, resources):
    possible_moves = {}

    for next_pos in possible_positions:
        # pr(t_prefix, 'XXXX',next_pos)
        if not move_mapper.is_position_enemy_city(next_pos):
            res_2 = len(MapAnalysis.get_resources_around(resources, next_pos, 1))
            # pr(t_prefix, 'YYYY', next_pos,res_2)
            if res_2 > 0:
                possible_moves[next_pos] = res_2
    # pr(t_prefix, 'XXXX Not Ordered Resources within 2', possible_moves)
    if len(possible_moves.keys()) > 0:
        possible_moves = dict(collections.OrderedDict(sorted(possible_moves.items(), key=lambda x: x[1], reverse=True)))
        # pr(t_prefix, 'XXXX Ordered Resources within 2', possible_moves)

    return possible_moves


def move_unit_to_or_transfer(actions, direction, info, move_mapper, player, prefix, unit, msg):
    if direction != DIRECTIONS.CENTER and move_mapper.can_move_to_direction(info.unit.pos, direction, game_state):
        move_unit_to(actions, direction, move_mapper, info, " move to " + msg + " pos", info.target_position)
        # continue
    else:
        if unit.get_cargo_space_left() < 100:
            # check if anybody in the pos we want to go
            friend_unit = get_unit_in_pos(player, unit.pos.translate(direction, 1))
            if friend_unit is not None:
                if unit_info[friend_unit.id].is_role_none() or unit_info[friend_unit.id].is_role_returner() \
                        and friend_unit.get_cargo_space_left() > 100 - unit.get_cargo_space_left():
                    pr(prefix, msg, "instead of going to city, do transfer to", friend_unit.id,
                       ' in ', unit.pos.translate(direction, 1))
                    transfer_all_resources(actions, info, friend_unit.id)
                    if unit_info[unit.id].is_role_returner():
                        unit_info[unit.id].clean_unit_role('Transfered resources')
                        unit_info[friend_unit.id].set_unit_role_returner(friend_unit.id)
        else:
            direction = get_random_step(unit.pos, move_mapper)
            move_unit_to(actions, direction, move_mapper, info, "randomly (due to " + msg + ")")
            # continue


def get_units_and_city_number_around_pos(actor, pos: Position, distance=1) -> int:
    results = 0
    for city in actor.cities.values():
        for city_tile in city.citytiles:
            if city_tile.pos.distance_to(pos) <= distance:
                results += 1

    for unit in actor.units:
        if unit.pos.distance_to(pos) <= distance:
            results += 1

    return results


def get_unit_in_pos(actor, pos) -> Unit:
    for unit in actor.units:
        if unit.pos.equals(pos):
            return unit

    return None


def get_units_number_around_pos(actor, pos, distance) -> int:
    return get_units_around_pos(actor, pos, distance).__len__()


def get_units_around_pos(actor, pos, distance) -> [Unit]:
    units: [Unit] = []
    for unit in actor.units:
        if unit.pos.distance_to(pos) <= distance:
            units.append(unit)

    return units


def find_best_city(game_state, city_tile_distance, move_mapper: MoveHelper, unsafe_cities, info: UnitInfo) -> Tuple[
    DIRECTIONS, Optional[Position], str]:
    unit = info.unit

    moved = False
    for city_tile, dist in city_tile_distance.items():
        if not move_mapper.has_position(city_tile.pos):
            closest_city_tile = city_tile
            if closest_city_tile is not None:
                direction = get_direction_to_city(game_state, info, closest_city_tile.pos, unsafe_cities, move_mapper,
                                                  True)
                if direction != DIRECTIONS.CENTER:
                    moved = True
                    return direction, closest_city_tile.pos, " towards closest city distancing and autonomy, size" \
                           + dist.__str__()

    if not moved:
        direction = get_random_step(unit.pos, move_mapper)
        return direction, None, "randomly (due to city)"


def find_best_resource(game_state, move_mapper: MoveHelper, resources_distance, resource_target_by_unit, info,
                       resources, prefix, unsafe_cities) -> \
        Tuple[DIRECTIONS, Optional[Position], str, str]:
    unit = info.unit
    closest_resource_tile, c_dist = None, None
    moved = False
    # pr(prefix, " XXX Find resources dis", resources_distance.values())
    # pr(prefix, " XXX Find resources pos", resources_distance.keys())
    # pr(prefix, " XXX Move mapper", move_mapper.move_mapper.keys())

    # we try not to allocate x units to same resource, but we are happy to go up to y in range (x,y)
    for max_units_per_resource in range(6, 7):
        for resource, resource_dist_info in resources_distance.items():
            # pr(prefix, " XXX - ", resource.pos, resource_dist_info)
            if resource is not None and not resource.pos.equals(unit.pos):
                if len(resource_target_by_unit.setdefault((resource.pos.x, resource.pos.y),
                                                          [])) < max_units_per_resource:
                    direction = get_direction_to_quick(game_state, info, resource.pos, move_mapper, resources,
                                                       unsafe_cities, False)
                    if direction != DIRECTIONS.CENTER:
                        return direction, resource.pos, " towards closest resource ", resource_dist_info[2]

    if len(unsafe_cities) == 0:
        return DIRECTIONS.CENTER, None, "stay where we are as we cannot go to resources, but no unsafe cities", ""
    else:
        direction = get_random_step(unit.pos, move_mapper)
        return direction, None, "randomly (due to resource)", ""


def get_autonomy_turns(city) -> int:
    turns_city_can_live = city.fuel // city.get_light_upkeep()
    return turns_city_can_live


def build_city(actions, info: UnitInfo, u_prefix, msg=''):
    actions.append(info.unit.build_city())
    pr(u_prefix, '- build city', msg)
    info.set_last_action_build()


def transfer_all_resources(actions, info: UnitInfo, to_unit_id):
    if info.unit.cargo.uranium > 0:
        actions.append(info.unit.transfer(to_unit_id, RESOURCE_TYPES.URANIUM, info.unit.cargo.uranium))
        pr("Unit", info.unit.id, '- transfer', info.unit.cargo.uranium, 'uranium to ', to_unit_id)
        info.set_last_action_transfer()
    elif info.unit.cargo.coal > 0:
        actions.append(info.unit.transfer(to_unit_id, RESOURCE_TYPES.COAL, info.unit.cargo.coal))
        pr("Unit", info.unit.id, '- transfer', info.unit.cargo.coal, 'coal to ', to_unit_id)
        info.set_last_action_transfer()
    elif info.unit.cargo.wood > 0:
        actions.append(info.unit.transfer(to_unit_id, RESOURCE_TYPES.WOOD, info.unit.cargo.wood))
        pr("Unit", info.unit.id, '- transfer', info.unit.cargo.wood, 'wood to ', to_unit_id)
        info.set_last_action_transfer()


def can_city_live(city, all_night_turns_lef) -> bool:
    return city.fuel / (city.get_light_upkeep() + 20) >= min(all_night_turns_lef, 30)


def move_unit_to_pos(actions, move_mapper: MoveHelper, info: UnitInfo, reason, pos: Position):
    direction = info.unit.pos.direction_to(pos)
    move_unit_to(actions, direction, move_mapper, info, reason, pos)


def move_unit_to(actions, direction, move_mapper: MoveHelper, info: UnitInfo, reason="", target_far_position=None):
    unit = info.unit
    next_state_pos = unit.pos.translate(direction, 1)
    # pr("Unit", unit.id, 'XXX -', unit.pos, next_state_pos, direction)
    if direction == DIRECTIONS.CENTER or next_state_pos.equals(unit.pos):
        # do not annotate
        pr(move_mapper.log_prefix, unit.id, '- not moving "', '', '" ', reason)
        move_mapper.add_position(unit.pos, unit)
    else:
        if target_far_position is not None:
            # target_far_position is only used for the annotation line
            actions.append(annotate.line(unit.pos.x, unit.pos.y, target_far_position.x, target_far_position.y))
            # actions.append(annotate.text(unit.pos.x, unit.pos.y, reason))

        actions.append(unit.move(direction))
        move_mapper.add_position(next_state_pos, unit)
        info.set_last_action_move(direction, next_state_pos)
        pr(move_mapper.log_prefix + unit.id, '- moving towards "', direction, next_state_pos, '" :', reason
           , str(target_far_position or ''))


def try_to_move_to(actions, move_mapper, info: UnitInfo, pos: Position, msg: str) -> bool:
    direction = info.unit.pos.direction_to(pos)
    # if nobody is already moving there
    if not move_mapper.has_position(pos):
        move_unit_to(actions, direction, move_mapper, info, msg, pos)
        return True
    else:
        return False


# return dist of cities, autonomy
def adjacent_cities(player, pos: Position, dist=1) -> {City, Tuple[int, int, DIRECTIONS]}:
    cities = {}
    for city in player.cities.values():
        for city_tile in city.citytiles:
            if city_tile.pos.distance_to(pos) <= dist:
                # pr(pos, "adjacent_cities", city_tile.pos)
                cities[city] = (
                    len(city.citytiles), get_autonomy_turns(city), MapAnalysis.directions_to(pos, city_tile.pos)[0])

    return cities


def get_direction_to_quick(game_state: Game, info: UnitInfo, target_pos: Position, move_mapper: MoveHelper,
                           resource_tiles, unsafe_cities, allow_clash_unit: bool = False) -> DIRECTIONS:
    # below to turn smart direction on for all resources and city trip
    # return get_direction_to_smart(game_state,unit, target_pos, move_mapper)

    unit: Unit = info.unit
    from_pos = unit.pos
    if from_pos.equals(target_pos):
        return DIRECTIONS.CENTER

    directions = MapAnalysis.directions_to(from_pos, target_pos)
    possible_directions = []

    check_penalise_directions(directions, info)

    for direction in directions:
        next_pos = from_pos.translate(direction, 1)

        # if we are trying to move on top of somebody else, skip
        # pr(t_prefix, ' XXX - try', direction, next_pos,'mapper', move_mapper.move_mapper.keys())
        if move_mapper.can_move_to_pos(next_pos, game_state, allow_clash_unit, unit.id + ' moving to ' + direction):
            # calculate how many resources there are to gather while walking, and predilect those if you have no cargo
            number_of_adjacent_res = len(MapAnalysis.get_resources_around(resource_tiles, next_pos, 1))
            is_empty = MapAnalysis.is_cell_empty(next_pos, game_state)
            near_resources = MapAnalysis.is_position_adjacent_to_resource(resource_tiles, next_pos)
            is_city = move_mapper.is_position_city(next_pos)
            if is_city:
                city_id = MapAnalysis.get_city_id_from_pos(next_pos, move_mapper.player)
                if not city_id in unsafe_cities:
                    continue
            possible_directions.append(
                (direction,  # 0
                 -number_of_adjacent_res,  # 1
                 -int(is_empty),  # 2
                 -int(is_empty and near_resources),  # 3
                 -int(is_city)  # 4
                 ))
        else:
            # pr(' XXX - skip')
            continue

    if info.unit.get_cargo_space_left() == 0:
        # if we do not have cargo, predilect empty tiles
        possible_directions.sort(key=lambda x: (x[2]))  # sort by it is empty
    elif info.unit.get_cargo_space_left() <= 20:
        # if we have 20 only left, moving in an empty near resouces, would just do great
        possible_directions.sort(key=lambda x: (x[3]))  # sort by it is empty and near resources
    elif info.unit.get_cargo_space_left() == 100:
        # no cargo, whatsover favour cities to travel faster, then more resources
        possible_directions.sort(key=lambda x: (x[4], x[1]))  # sort by it is empty and near resources
    else:
        # in any other case (20<cargo<100), just go where more resorces
        possible_directions.sort(key=lambda x: (x[1]))

    if len(possible_directions) == 0:
        return DIRECTIONS.CENTER
    else:
        return next(iter(possible_directions))[0]


def check_penalise_directions(directions, info: UnitInfo):
    return

    if info.alarm > 0 and directions.__len__() > 1 and info.last_move_direction is not None:
        pr(info.unit.id, 'penalising direction', info.last_move_direction, 'as last collided', directions)
        if info.last_move_direction in directions:
            # move the previous collided direction to the end of list
            directions.append(directions.pop(directions.index(info.last_move_direction)))


# as get_direction_to_quick, but avoid other cities
def get_direction_to_city(game_state: Game, info: UnitInfo, target_pos: Position, unsafe_cities,
                          move_mapper: MoveHelper,
                          allow_clash_unit: bool = False) -> DIRECTIONS:
    # below to turn smart direction on for all resources and city trip
    # return get_direction_to_smart(game_state,unit, target_pos, move_mapper)
    unit = info.unit
    from_pos = unit.pos
    if from_pos.equals(target_pos):
        return DIRECTIONS.CENTER

    directions = MapAnalysis.directions_to(from_pos, target_pos)

    check_penalise_directions(directions, info)

    for direction in directions:
        next_pos = from_pos.translate(direction, 1)
        if not MapAnalysis.is_position_valid(next_pos, game_state):
            continue
        if move_mapper.is_position_city(next_pos):
            city_on_the_way = MapAnalysis.get_city_id_from_pos(next_pos, move_mapper.player)
            if city_on_the_way not in unsafe_cities:
                # this is a safe city, but not the one where we want to reach
                # pr(' XXX - skip ', direction, next_pos, 'as it goes to safe city', city_on_the_way)
                continue

        # if we are trying to move on top of somebody else, skip
        # pr(' XXX - try', direction, next_pos,'mapper', move_mapper.move_mapper.keys())
        if move_mapper.can_move_to_pos(next_pos, game_state, allow_clash_unit, unit.id + ' moving to ' + direction):
            return direction
        else:
            # pr(' XXX - skip')
            continue

    return DIRECTIONS.CENTER


def is_resource_minable(actor, resource_type: RESOURCE_TYPES, research_rate=0., in_future_turns=0) -> bool:
    expected_additional_research = int(research_rate * in_future_turns)
    return (resource_type == RESOURCE_TYPES.WOOD) or \
           (resource_type == RESOURCE_TYPES.COAL and actor.research_points + expected_additional_research >= 50) or \
           (resource_type == RESOURCE_TYPES.URANIUM and actor.research_points + expected_additional_research >= 200)


def get_direction_to_smart_XXX(game_state: Game, unit: Unit, target_pos: Position,
                               move_mapper: MoveHelper) -> DIRECTIONS:
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
