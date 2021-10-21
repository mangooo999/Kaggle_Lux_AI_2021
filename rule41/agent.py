import math
import sys
import collections

import time

from game_state_info.game_state_info import GameStateInfo
from ConfigManager import ConfigManager

from typing import Optional, Dict, Tuple, DefaultDict, Sequence

from lux.game import Game
from lux.game_map import Cell, Position, RESOURCE_TYPES

from UnitInfo import UnitInfo
from GameInfo import GameInfo
from MoveHelper import MoveHelper
from lux.game_objects import CityTile, Unit, City, DIRECTIONS

from cluster.cluster import Cluster
import resources.resource_helper as ResourceService
from cluster.cluster_controller import ClusterControl
import maps.map_analysis as MapAnalysis
from LazyWrapper import LazyWrapper

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
    if True:
        print(*args, sep=sep, file=sys.stderr)
    elif f:
        print(*args, sep=sep, file=sys.stderr)


def prx(*args): pr(*args, f=True)


def adjacent_empty_tile_favor_close_to_city_and_res(pos: Position, empty_tyles, game_state, player, opponent,
                                                    resource_tiles, prefix) -> Optional[Cell]:
    if len(empty_tyles) == 0:
        return None
    elif len(empty_tyles) == 1:
        return game_state.map.get_cell_by_pos(empty_tyles[0])
    else:
        enemy_unity, enemy_distance = opponent.get_closest_unit(pos)
        enemy_direction = DIRECTIONS.CENTER
        if 3 <= enemy_distance <= 5:
            enemy_direction = pos.direction_to(enemy_unity.pos)
            # pr(prefix, "XXXX0 enemy is at ", enemy_direction, enemy_distance)

        # pr(prefix,"Trying to solve which empty one is close to most cities tiles")
        results = {}
        # pr(prefix,"XXXX1 adjacent_empty_tile_favor_close_to_city empty_tyles" , empty_tyles)

        for adjacent_position in empty_tyles:
            adjacent_city_tiles, adjacent_city = MapAnalysis.find_number_of_adjacent_city_tile(adjacent_position,
                                                                                               player)
            adjacent_res = len(MapAnalysis.get_resources_around(resource_tiles, adjacent_position, 1))

            is_going_toward_enemy = pos.direction_to(adjacent_position) == enemy_direction

            # adjacent_res2 = len(MapAnalysis.get_resources_around(resource_tiles, adjacent_position, 2))
            # results[adjacent_position] = (adjacent_city,adjacent_city_tiles, adjacent_res,adjacent_res2)
            results[adjacent_position] = (adjacent_city, adjacent_city_tiles, adjacent_res, int(is_going_toward_enemy))

            # pr(prefix,"- XXXX1b",adjacent_position,results[adjacent_position])

        # pr(prefix,"XXXX2 adjacent_empty_tile_favor_close_to_city", results)
        # ordered by number of tiles, so we take last element
        results = dict(collections.OrderedDict(sorted(results.items(), key=lambda x: x[1], reverse=True)))
        # pr(prefix,"XXXX3 adjacent_empty_tile_favor_close_to_city", results)
        result = next(iter(results.keys()))

        # pr("Return", result)
        return game_state.map.get_cell_by_pos(result)


def get_empty_tile_near_resources(empty_tiles, resource_tiles) -> list[Position]:
    results = []
    for adjacent_position in empty_tiles:
        if MapAnalysis.is_position_adjacent_to_resource(resource_tiles, adjacent_position):
            results.append(adjacent_position)
            # pr("- ",adjacent_position,number_of_adjacent)
    return results

def empty_tile_near_res_and_city(empty_tiles, wood_tiles, game_state, player) -> Optional[Cell]:
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


def find_closest_city_tile_no_logic(pos: Position, player):
    if len(player.cities) > 0:
        city_tiles_distance = {}
        for k, city in player.cities.items():
            for city_tile in city.citytiles:
                city_tiles_distance[city_tile.pos] = city_tile.pos.distance_to(pos)
        # order by dist
        city_tiles_distance = collections.OrderedDict(sorted(city_tiles_distance.items(), key=lambda x: x[1]))
        return next(iter(city_tiles_distance.keys()))
    else:
        return pos


# snippet to find the all city tiles distance and sort them.
def find_city_tile_distance(pos: Position, player, unsafe_cities, game_state_info) -> Dict[
    CityTile, Tuple[int, int, int, str]]:
    city_tiles_distance: Dict[CityTile, Tuple[int, int, int, str]] = {}
    if len(player.cities) > 0:
        # the cities are stored as a dictionary mapping city id to the city object, which has a citytiles field that
        # contains the information of all citytiles in that city
        for k, city in player.cities.items():
            city_autonomy = city.get_autonomy_turns()
            will_live = city_autonomy >= game_state_info.next_night_number_turn
            if city.cityid in unsafe_cities:
                for city_tile in city.citytiles:
                    dist = city_tile.pos.distance_to(pos)
                    # order by distance asc, autonomy desc
                    city_tiles_distance[city_tile] = (
                        dist, city_autonomy, -len(city.citytiles), city.cityid)
    # order by
    # - increasing distance (closest city first),
    # - increasing autonomy (smallest autonomy first)
    # - decreasing size (biggest cities first)

    city_tiles_distance = collections.OrderedDict(sorted(city_tiles_distance.items(), key=lambda x: x[1]))
    #     pr(len(city_tiles_distance))
    return city_tiles_distance


def get_random_step(from_pos: Position) -> DIRECTIONS:
    directions = DIRECTIONS.get_random_directions()

    for direction in directions:
        if move_mapper.can_move_to_direction(from_pos, direction, game_state):
            return direction
    # otherwise
    return DIRECTIONS.CENTER


game_state = None
unit_info: DefaultDict[str, UnitInfo] = {}
game_info = GameInfo(pr)
clusters: ClusterControl
start_time = 0


def agent(observation, configuration):
    global game_state
    global clusters
    global config
    global start_time
    global move_mapper

    ### Do not edit ###
    if observation["step"] == 0:
        game_state = Game()
        game_state._initialize(observation["updates"])
        game_state._update(observation["updates"][2:])
        game_state.id = observation.player

        # This is the start of the game
        clusters = ClusterControl(game_state, pr)
        config = ConfigManager(game_state.map_width, pr)
        start_time = time.time()

    else:
        game_state._update(observation["updates"])

    actions = []

    ### AI Code goes down here! ###
    game_state_info: GameStateInfo = GameStateInfo(game_state.turn, pr)

    player = game_state.players[observation.player]
    opponent = game_state.players[(observation.player + 1) % 2]
    move_mapper = MoveHelper(player, opponent, game_state.turn, pr)

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

        # check if we should move very quickly to another cluster
        distance = math.inf
        better_cluster_pos = None
        good_pos_around_city = None

        pr(t_prefix, "check for a better initial cluster, this cluster res=", len(initial_cluster.resource_cells))
        for cluster in clusters.get_clusters():
            if cluster.res_type == RESOURCE_TYPES.WOOD and cluster.has_no_units_no_enemy():
                r_pos, r_distance = MapAnalysis.get_closest_position(initial_city_pos, cluster.perimeter_empty)
                res = cluster.resource_cells.__len__()
                if res > 2 * len(initial_cluster.resource_cells) and r_distance < 12 and r_distance < distance:
                    pr(t_prefix, 'There seems to be a better cluster', cluster.to_string_light())
                    better_cluster_pos = r_pos
                    distance = r_distance

        if better_cluster_pos is not None:
            good_pos_around_city = better_cluster_pos
        else:
            initial_enemy_city_pos = list(opponent.cities.values())[0].citytiles[0].pos
            distance_cities = initial_city_pos.distance_to(initial_enemy_city_pos)
            if 3 <= distance_cities <= 5:
                step_to_enemy = initial_city_pos.translate_towards(initial_enemy_city_pos)
                if MapAnalysis.is_position_adjacent_to_resource(wood_tiles, step_to_enemy):
                    pr(t_prefix, "Confrontational first step towards enemy")
                    good_pos_around_city = step_to_enemy

            if good_pos_around_city is None:
                x3: list = MapAnalysis.get_resources_around(available_resources_tiles, initial_city_pos, 3)
                game_info.at_start_resources_within3 = len(x3)
                pr(t_prefix, "Resources within distance 3 of", initial_city_pos, "initial pos", len(x3))

                possible_positions = MapAnalysis.get_12_positions(initial_city_pos, game_state)
                good_pos_around_city = get_best_first_move(t_prefix, game_state, initial_city_pos,
                                                           possible_positions, wood_tiles, initial_enemy_city_pos)

        # END initial calculations

    # Spawn of new troops and assigment of roles below
    for unit in player.units:
        unit_number = unit_number + 1
        if not unit.id in unit_info:
            # new unit
            unit_info[unit.id] = UnitInfo(unit, pr)
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
                    and is_resource_minable(player, next_clust.res_type, game_info.get_research_rate(5), game_state_info.steps_until_night) \
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
                    r_pos, distance = MapAnalysis.get_closest_to_positions(unit.pos, next_clust.perimeter_empty)
                    time_distance = 2 * distance + unit.cooldown

                    # TODO we could try to add here the resources if we are sure it doesn't pass from a city
                    # # we only consider reachable clusters before the night
                    if time_distance > game_state_info.steps_until_night:
                        continue
                    if not is_resource_minable(player, next_clust.res_type, game_info.get_research_rate(5), time_distance):
                        continue
                    if info is None:
                        continue
                    # we also consider expanders to be moved, as their role gets transferred
                    if not (info.is_role_none() or info.is_role_city_expander()):
                        continue

                    # from lowest (best), to highest
                    score = time_distance + next_clust.score
                    already_incoming = next_clust.incoming_explorers_position.count(r_pos)

                    clust_analyses[cluster.id].append(
                        (distance,
                         unit,
                         next_clust,
                         r_pos,
                         score,
                         time_distance,
                         already_incoming))

    for cluster in clusters.get_clusters():

        # big cluster, try to spread our units in empty perimeter
        if cluster.res_type == RESOURCE_TYPES.WOOD \
                and (cluster.get_equivalent_resources() > 8) \
                and (len(cluster.enemy_unit) < (cluster.get_equivalent_resources() // 4)) \
                and (cluster.num_units() + len(cluster.incoming_explorers)) >= 3:
            pr(t_prefix, "big cluster", cluster.to_string_light())
            for pos in cluster.perimeter_empty:
                MIN_DIST = 3
                # not close to friendly
                if player.get_num_units_and_city_number_around_pos(pos, MIN_DIST) > 0:
                    continue

                # not close to enemies
                if opponent.get_num_units_and_city_number_around_pos(pos, MIN_DIST) > 0:
                    continue

                # not close to other traveller
                if pos.distance_to_mult(cluster.incoming_explorers_position) <= MIN_DIST:
                    continue

                units_to_pos = []
                for unitid in cluster.units:
                    unit = player.units_by_id[unitid]
                    info = None
                    if unitid in unit_info:
                        info = unit_info[unitid]
                    if info is not None:
                        # pr("XXX",info.unit.id,info.role)
                        if info.is_role_none():
                            dist = unit.pos.distance_to(pos)
                            units_to_pos.append((dist, info, pos))
                units_to_pos.sort(key=lambda x: (x[0]))  # distance, increasing

                spread_move = next(iter(units_to_pos), None)
                if spread_move is not None:
                    dist = spread_move[0]
                    i: UnitInfo = spread_move[1]  # infor
                    u = i.unit
                    pos = spread_move[2]
                    pr(t_prefix, "assigning", u.id, "to spread in big cluster", cluster.id, pos)
                    i.set_unit_role_traveler(pos, dist * 2)
                    break

        if len(clust_analyses[cluster.id]) == 0:
            continue
        # else:

        # sort
        clust_analyses[cluster.id].sort(key=lambda x: (x[4], x[6]))  # score, already incoming

        # first element of sequence associated to this cluster analyses is the closest cluster
        best_cluster = next(iter(clust_analyses[cluster.id]), None)
        # pr(t_prefix,"XXXX",best_cluster)
        # find the closest unit of cluster to next cluster
        best_cluster_dist: int = best_cluster[0]
        best_cluster_unit: Unit = best_cluster[1]
        best_cluster_cluster: Cluster = best_cluster[2]
        best_cluster_pos: Position = best_cluster[3]

        move_to_best_cluster: bool = False

        # pick the closest with no units or no incoming
        dist = math.inf
        closest_cluster_dist = None
        closest_cluster_unit: Unit = None
        closest_cluster_cluster: Cluster = None
        closest_cluster_pos: Position = None
        for c in clust_analyses[cluster.id]:
            this_cluster: Cluster = c[2]
            this_cluster_dist: int = c[0]
            if len(this_cluster.units) == 0 and len(this_cluster.incoming_explorers) == 0 and this_cluster_dist < dist:
                closest_cluster_dist: int = this_cluster_dist
                closest_cluster_unit: Unit = c[1]
                closest_cluster_cluster: Cluster = this_cluster
                closest_cluster_pos: Position = c[3]
                dist = this_cluster_dist

        move_to_closest_cluster: bool = False

        is_this_wood = cluster.res_type == RESOURCE_TYPES.WOOD
        is_that_wood = best_cluster_cluster.res_type == RESOURCE_TYPES.WOOD
        is_this_or_that_wood = is_this_wood or is_that_wood

        move_if = is_this_or_that_wood

        if closest_cluster_cluster is not None:
            if config.super_fast_expansion and cluster.res_type == RESOURCE_TYPES.WOOD and cluster.num_units() > 1:
                pr(t_prefix, 'super_fast_expansion move_to_closest_cluster')
                move_to_closest_cluster = True

            if move_if and cluster.get_equivalent_units() > 1 and closest_cluster_dist < 4 and \
                    closest_cluster_cluster.get_equivalent_units() == 0:
                pr(t_prefix, 'There is a very near closest uncontested cluster', closest_cluster_cluster.id,
                   'next to this cluster', cluster.id, 'at dist ', closest_cluster_dist)
                move_to_closest_cluster = True


        if move_if and cluster.has_eq_gr_units_than_res() and cluster.get_equivalent_units() > 1:
            pr(t_prefix, 'cluster', cluster.id, ' is overcrowded u=r, u=', cluster.num_units(), cluster.num_resource())
            move_to_best_cluster = True

        if move_if and cluster.get_equivalent_units() > config.cluster_wood_overcrowded:
            pr(t_prefix, 'cluster', cluster.id, ' is overcrowded u>', config.cluster_wood_overcrowded,
               'u=', cluster.units)
            move_to_best_cluster = True

        if move_if and cluster.get_equivalent_units() > 1 and best_cluster_dist < 4 and \
                best_cluster_cluster.get_equivalent_units() == 0:
            pr(t_prefix, 'There is a very near best uncontested cluster', best_cluster_cluster.id,
               'next to this cluster', cluster.id, 'at dist ', best_cluster_dist)
            move_to_best_cluster = True

        if move_if and cluster.get_equivalent_units() > 1 and cluster.closest_enemy_distance > 9 \
                and best_cluster_cluster.has_no_units_no_incoming() \
                and best_cluster_cluster.num_enemy_units() * 5 < best_cluster_cluster.get_equivalent_resources():
            pr(t_prefix, 'enemy is very far, and next cluster has no units, no incoming ', best_cluster_cluster.id,
               'next to this cluster', cluster.id, 'at dist ', best_cluster_dist)
            move_to_best_cluster = True

        if move_to_best_cluster:
            pr(t_prefix, 'try_move_units_cluster best_cluster ', best_cluster_cluster.id)
            repurpose_unit(best_cluster_cluster, best_cluster_pos, best_cluster_unit, cluster, t_prefix)

        elif move_to_closest_cluster:
            pr(t_prefix, 'try_move_units_cluster closest_cluster ', closest_cluster_cluster.id)
            repurpose_unit(closest_cluster_cluster, closest_cluster_pos, closest_cluster_unit, cluster, t_prefix)

    # max number of units available
    units_cap = sum([len(x.citytiles) for x in player.cities.values()])

    unit_ceiling = int(min(float(units_cap), max(float(len(available_resources_tiles)) * 1.8, 5)))

    cities = list(player.cities.values())
    unsafe_cities = {}
    immediately_unsafe_cities = {}
    available_city_actions = 0
    available_city_actions_now_and_next = 0;
    do_research_points = 0
    number_city_tiles = 0

    # set unsafe cities, record how many available city actions we have
    if len(cities) > 0:
        for city in cities:
            will_live = city.get_autonomy_turns() >= game_state_info.all_night_turns_lef
            will_live_next_night = city.get_autonomy_turns() >= game_state_info.next_night_number_turn
            payload = (city.get_num_tiles(), will_live_next_night)
            # collect unsafe cities
            if not will_live:
                unsafe_cities[city.cityid] = payload
            if not will_live_next_night:
                immediately_unsafe_cities[city.cityid] = payload

            # record how many available city actions we have now
            for city_tile in city.citytiles:
                number_city_tiles = number_city_tiles + 1
                if city_tile.can_act():
                    available_city_actions += 1
                if city_tile.cooldown <= 1:
                    available_city_actions_now_and_next += 1

    # logging
    if game_state.turn == 360:
        prx(t_prefix, "END C=", number_city_tiles, 'u=', len(player.units), 't=', str(time.time() - start_time))
        prx(t_prefix, "enemy C=", "?", 'u=', len(opponent.units))
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
            city_autonomy = city.get_autonomy_turns()
            will_live = city_autonomy >= game_state_info.all_night_turns_lef
            will_live_this_night = city_autonomy >= game_state_info.next_night_number_turn
            city_size = len(city.citytiles)
            for city_tile in city.citytiles:
                if city_tile.can_act():
                    units_around = MapAnalysis.get_units_around(player, city_tile.pos, 2)
                    res_around = len(MapAnalysis.get_resources_around(available_resources_tiles, city_tile.pos, 3))
                    dummy, closest_resource = MapAnalysis.get_closest_position_cells(city_tile.pos,
                                                                                     available_resources_tiles)
                    has_res_around = res_around > 0
                    score1 = 0
                    score2 = closest_resource
                    if has_res_around:
                        # RES around
                        if not will_live_this_night:
                            if not units_around:
                                # first city that have not unit around, that will die next
                                score1 = 0
                                score2 = -city_size
                            else:
                                score1 = 1
                                score2 = float(units_around) / float(res_around + 1)
                        elif not will_live:
                            if not units_around:
                                # then city  that will die at one point
                                score1 = 3
                                score2 = -city_size
                            else:
                                score1 = 4
                                score2 = float(units_around) / float(res_around + 1)
                    else:
                        # NO RES around
                        if not units_around:
                            # there are no resources, no units, if no other city with resource around
                            score1 = 5
                            score2 = closest_resource
                        else:
                            # at the moment we score identically city with no resource around,
                            # regardless if they have or not units
                            score1 = 5
                            score2 = closest_resource

                    ordered_tyles[(
                        score1,
                        score2,
                        closest_resource,
                        int(will_live),
                        float(units_around) / float(res_around + 1))
                    ] = city_tile

        ordered_tyles = collections.OrderedDict(sorted(ordered_tyles.items(), key=lambda x: x[0]))
        pr(t_prefix, "Ordered cities we want to create workers ", ordered_tyles)

    while min(number_work_we_can_build, number_work_we_want_to_build) > 0:
        for city_tile in ordered_tyles.values():
            # let's create one more unit in the last created city tile if we can
            actions.append(city_tile.build_worker())
            pr(t_prefix, city_tile.pos, "- created worker")
            number_work_we_can_build -= 1
            number_work_we_want_to_build -= 1

    if len(cities) > 0:
        for city in cities:
            for city_tile in city.citytiles:
                # pr(t_prefix, "- C tile ", city_tile.pos, " CD=", city_tile.cooldown)
                if city_tile.can_act():
                    if game_state.turn < 30:  # TODO maybe this should be based on how close is the unit to build
                        # we are turn<30, we need to prioritise spawning in the right city rather than research
                        # if we have resources around here, but no units, do not research
                        near_resource = MapAnalysis.is_position_adjacent_to_resource_distance(
                            available_resources_tiles, city_tile.pos, 2)
                        near_units = player.get_units_number_around_pos(city_tile.pos, 2)
                        if near_resource and near_units == 0:
                            pr(t_prefix,
                               "- this city tile could do research, but better to wait till it can create a worker")
                            continue
                        # else:
                        # pr(t_prefix, "- - nothing")
                    if game_info.still_can_do_reseach():
                        # let's do research
                        game_info.do_research(actions, city_tile, str(city_tile.pos) + " research")

    pr(t_prefix, "Unsafe cities            ", unsafe_cities)
    pr(t_prefix, "Immediately Unsafe cities", immediately_unsafe_cities)

    # trace the agent move
    # store all unit current location on move tracker
    for unit in player.units:
        if not unit.can_act():
            # those units cannot move
            move_mapper.add_initial_position(unit.pos, unit)

    # map of resource to unit going for them
    resource_target_by_unit = {}

    for unit in player.units:
        get_unit_action(unit, actions, all_resources_tiles,
                        available_resources_tiles, clusters,
                        game_state, game_state_info,
                        number_city_tiles, opponent,
                        player, resource_target_by_unit, unsafe_cities,
                        wood_tiles)

    # if this unit didn't do any action, check if we can transfer his cargo back in the direction this come from
    for unit in player.units:
        info: UnitInfo = unit_info[unit.id]
        u_prefix: str = "T_" + game_state.turn.__str__() + str(unit.id)
        # pr(prefix, "XXX check unit has worked", unit.can_act(), info.has_done_action_this_turn)
        if unit.is_worker() and unit.can_act() and not info.has_done_action_this_turn:
            pr(u_prefix, " this unit has not worked")
            if unit.get_cargo_space_used() == 0 and len(available_resources_tiles) == 0:
                # return home
                send_unit_home(actions, game_state, info, player, u_prefix, unit, "no cargo, no resource")
            elif unit.cargo.coal > 0 or unit.cargo.uranium > 0:
                adjacent_empty_tiles = LazyWrapper(
                    lambda: MapAnalysis.find_all_adjacent_empty_tiles(game_state, unit.pos))
                in_resource, near_resource = MapAnalysis.is_position_in_X_adjacent_to_resource(
                    available_resources_tiles,
                    unit.pos)

                transfer_to_best_friend_outside_resource(actions, adjacent_empty_tiles,
                                                         available_resources_tiles, info, in_resource,
                                                         near_resource,
                                                         player, unit, u_prefix)

    # for i,j in resource_target_by_unit.items():
    #    pr("XXXX resources map ",game_info.turn,i,len(j))

    return actions


def get_unit_action(unit, actions, all_resources_tiles, available_resources_tiles, clusters, game_state,
                    game_state_info, number_city_tiles, opponent, player,
                    resource_target_by_unit, unsafe_cities, wood_tiles):
    info: UnitInfo = unit_info[unit.id]
    u_prefix: str = "T_" + game_state.turn.__str__() + str(unit.id)

    pr(u_prefix, ";pos", unit.pos, 'CD=', unit.cooldown, unit.cargo.to_string(), 'fuel=',
       unit.cargo.fuel(), 'canBuildHere', unit.can_build(game_state.map), 'role', info.role)

    in_city = LazyWrapper(lambda: move_mapper.is_position_city(unit.pos))
    adjacent_units = LazyWrapper(lambda: player.get_units_around_pos(unit.pos, 1))
    adjacent_empty_tiles = LazyWrapper(lambda: MapAnalysis.find_all_adjacent_empty_tiles(game_state, unit.pos))
    empty_tile_near_resources = LazyWrapper(lambda: get_empty_tile_near_resources(adjacent_empty_tiles(),
                                                                                  available_resources_tiles))
    in_resource, near_resource = MapAnalysis.is_position_in_X_adjacent_to_resource(available_resources_tiles,
                                                                                   unit.pos)
    empty_tile_near_wood_and_city = LazyWrapper(lambda: empty_tile_near_res_and_city(adjacent_empty_tiles(), wood_tiles,
                                 game_state, player))
    # End of game, try to save units that are not going anymore to do anything
    if (len(all_resources_tiles) == 0 and unit.cargo.fuel() == 0 and not in_city()) \
            or (game_state.turn >= 350):
        # those units are not useful anymore, return home
        send_unit_home(actions, game_state, info, player, u_prefix, unit, "nothing to do, go home")
        return

    if (len(all_resources_tiles) == 0 and unit.cargo.fuel() > 0 and len(unsafe_cities) == 0):
        pr(u_prefix, ' end of game, with resources ', unit.get_cargo_space_used())
        if unit.can_build(game_state.map):
            dummy, cities = MapAnalysis.find_adjacent_city_tile(unit.pos, player)
            if len(cities) == 0:
                build_city(actions, info, u_prefix, 'end of game')
                return
            else:
                additional_fuel = 0
                # check if we are adjacent and can cause issues

                # fuel that can be gathered from adjacent units
                if game_state_info.turns_to_night > 2:
                    for u in adjacent_units():
                        additional_fuel += u.cargo.fuel()

                do_build = True
                for c in cities:
                    increased_upkeep = 23 - 5 * len(cities)
                    expected_autonomy = (c.fuel + additional_fuel) // (c.get_light_upkeep() + increased_upkeep)
                    if expected_autonomy < game_state_info.all_night_turns_lef:
                        pr(u_prefix, "end of game. Do not build near adjacent", c.cityid,
                           "because low expected autonomy", expected_autonomy)
                        do_build = False
                        break
                    else:
                        pr(u_prefix, 'adjacent city', c.cityid, 'will be fine with autonomy', expected_autonomy)

                if do_build:
                    build_city(actions, info, u_prefix, 'end of game (adjacent)')
                    return
                else:
                    for adjacent_position in adjacent_empty_tiles():
                        # pr(u_prefix, "XXXXXXX ", num_adjacent_here)
                        dummy, num_adjacent_city = MapAnalysis.find_number_of_adjacent_city_tile(adjacent_position,
                                                                                                 player)
                        if num_adjacent_city == 0:
                            move_unit_to_or_transfer(actions, unit.pos.direction_to(adjacent_position), info,
                                                     player, u_prefix, unit,
                                                     'end of game, move away city')
                            return

        # end of game, try to put together 100 to build something
        transferred = transfer_to_best_friend_outside_resource(actions, adjacent_empty_tiles,
                                                               available_resources_tiles, info, in_resource,
                                                               near_resource, player, unit, u_prefix)
        if transferred:
            pr(u_prefix, ' end of game, transferred resource to put together 100')
            return

        # find closest unit with resources:
        distance_to_friend_with_res = math.inf
        friend_unit_with_res = None
        for f in player.units:
            if f.cargo.fuel() > 0 and f.id != unit.id:
                dist = unit.pos.distance_to(f.pos)
                if 1 < dist < distance_to_friend_with_res:
                    distance_to_friend_with_res = dist
                    friend_unit_with_res = f

        if friend_unit_with_res is not None:
            directions = MapAnalysis.directions_to_no_city(unit.pos, friend_unit_with_res.pos, player)
            for direction in directions:
                if move_mapper.can_move_to_direction(unit.pos, direction, game_state):
                    move_mapper.move_unit_to(actions, direction, info,
                                             'try to move' + direction +
                                             ' closer to ' + friend_unit_with_res.id + ' to put together 100',
                                             friend_unit_with_res.pos)
                    return

    if (move_mapper.is_position_city(unit.pos) and 2 < game_state.turn < 15 and number_city_tiles == 1
            and len(player.units) == 1):
        pr(u_prefix, ' NEEDS to become an expander')
        info.set_unit_role_expander(u_prefix)

    if unit.is_worker() and unit.can_act():
        # SHORTCUTS
        # in SHORTCUTS

        in_empty = LazyWrapper(lambda: MapAnalysis.is_cell_empty(unit.pos, game_state))

        # near SHORTCUTS
        near_wood = LazyWrapper(lambda: MapAnalysis.is_position_adjacent_to_resource(wood_tiles, unit.pos))
        near_city = LazyWrapper(lambda: player.is_position_adjacent_city(unit.pos))

        # adjacent SHORTCUTS
        best_adjacent_empty_tile = LazyWrapper(lambda: adjacent_empty_tile_favor_close_to_city_and_res(unit.pos,
                                                                                           adjacent_empty_tiles(),
                                                                                           game_state,
                                                                                           player,
                                                                                           opponent,
                                                                                           available_resources_tiles,
                                                                                           u_prefix))
        resources_distance, adjacent_resources = find_resources_distance(
            unit.pos, clusters, all_resources_tiles, game_info)
        city_tile_distance = LazyWrapper(
            lambda: find_city_tile_distance(unit.pos, player, unsafe_cities, game_state_info))
        adjacent_next_to_resources = LazyWrapper(lambda: get_walkable_that_are_near_resources(
            u_prefix, MapAnalysis.get_4_positions(unit.pos, game_state), available_resources_tiles))

        # enemy SHORTCUTS
        adjacent_enemy_units = LazyWrapper(lambda: opponent.get_units_around_pos(unit.pos, 1))
        num_adjacent_enemy_unit = LazyWrapper(lambda: len(adjacent_enemy_units()))
        num_hostiles_within2 = LazyWrapper(lambda: opponent.get_num_units_and_city_number_around_pos(unit.pos, 2))
        is_in_highly_hostile_area = LazyWrapper(lambda: num_hostiles_within2() > 5)

        # pr(u_prefix, 'adjacent_empty_tiles', [x.__str__() for x in adjacent_empty_tiles()],
        #    'favoured', best_adjacent_empty_tile.pos if best_adjacent_empty_tile else '')

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
        if info.is_role_city_expander() and unit.get_cargo_space_left() > 0 and num_adjacent_enemy_unit() == 0:
            pr(u_prefix, ' is expander')

            # all action expander are based on building next turn. We don't build at last day, so skip if day before
            if game_state_info.turns_to_night > 1:
                if near_city() and (not in_city()) and near_wood():
                    # if we are next to city and to wood, just stay here
                    move_mapper.stay(unit, ' expander we are between city and wood do not move')
                    return

                # if we have the possibility of going in a tile that is like the  above
                expander_spot = empty_tile_near_wood_and_city()

                if expander_spot is not None:
                    if move_mapper.try_to_move_to(actions, info, expander_spot.pos, " expander to perfect pos"):
                        return

        #   EXPANDER ENDS

        # night rules
        if game_state_info.is_night_time() or game_state_info.is_night_tomorrow():
            # time_to_dawn differs from game_state_info.turns_to_dawn as it could be even 11 on turn before night
            time_to_dawn = 10 + game_state_info.steps_until_night

            pr(u_prefix, ' it is night...', 'time_to_dawn', time_to_dawn,
               'inCity:', in_city(), 'empty:', in_empty(), 'nearwood:', near_wood())

            # search for adjacent cities in danger
            if game_state_info.is_night_time() and unit.cargo.fuel() > 0 and not in_city():
                # if we have resources, next to a city that will die in this night,
                # and we have enough resources to save it, then move
                cities = MapAnalysis.adjacent_cities(player, unit.pos)
                # order cities by decreasing size
                cities = collections.OrderedDict(sorted(cities.items(), key=lambda x: x[-1]))
                # TODO use maybe immediate_unsafe_cities here?
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
                        move_mapper.move_unit_to(actions, city_payload[2], info, " try to save a city")
                        return

            if near_wood() and in_empty():
                pr(u_prefix, ' it is night, we are in a empty cell near resources')
                # empty near a resource, we can stay here, but we could even better go to same near city

                # if we have the possibility of going in a tile that is empty_tile_near_wood_and_city, then go
                best_night_spot = empty_tile_near_wood_and_city()

                if best_night_spot is not None \
                        and move_mapper.try_to_move_to(actions, info, best_night_spot.pos, " best_night_spot"):
                    return
                else:
                    move_mapper.stay(unit, ' it is night, we will stay here')
                    return

            # if we have the possibility of going in a tile that is empty_tile_near_wood_and_city
            # go if not in a city, or if you are in a city, go just last 1 days of night (so we gather and covered)
            best_night_spot = empty_tile_near_wood_and_city()

            if best_night_spot is not None:
                enemy_there = opponent.is_unit_adjacent(best_night_spot.pos)  # IN OR ADJACENT
                if (not in_city()) or time_to_dawn <= 1 or enemy_there:
                    if move_mapper.try_to_move_to(actions, info, best_night_spot.pos, " best_night_spot"):
                        return

            if in_city():
                if not near_resource:
                    # not near resource
                    pr(u_prefix, ' it is night, we are in city, not next resource, do not move')
                    for pos in adjacent_next_to_resources().keys():
                        if move_mapper.can_move_to_pos(pos, game_state) and not move_mapper.has_position(pos):
                            direction = unit.pos.direction_to(pos)
                            move_mapper.move_unit_to(actions, direction, info, "night, next to resource")
                            return
                    # could not find find next to resource
                    return
                else:
                    # in city, near resource
                    move_mapper.stay(unit, ' it is night, we are in city, next resource, do not move')
                    return

        # DAWN

        if game_state_info.is_dawn():
            pr(u_prefix, "It's dawn")
            if near_wood() \
                    and in_empty() \
                    and 0 < unit.get_cargo_space_left() <= 21:
                move_mapper.stay(unit, ' at dawn, can build next day')
                return

        # ALARM, we tried too many times the same move
        if info.alarm >= 4 and len(unsafe_cities) > 0:
            pr(u_prefix, ' has tried too many times to go to ', info.last_move_direction)
            if unit.can_build(game_state.map):
                build_city(actions, info, u_prefix, ':we tried too many times to go to' + info.last_move_direction)
            else:
                direction = get_random_step(unit.pos)
                move_mapper.move_unit_to(actions, direction, info,
                                         "randomly, too many try to " + info.last_move_direction)
            return

        #   TRAVELER
        if info.is_role_traveler():
            pr(u_prefix, ' is traveler to', info.target_position)
            if unit.can_build(game_state.map) and info.build_if_you_can:
                pr(u_prefix, ' traveler build')
                build_city(actions, info, u_prefix, 'traveler build')
                return

            direction = get_direction_to_quick(game_state, info, info.target_position,
                                               available_resources_tiles, unsafe_cities)
            if direction != DIRECTIONS.CENTER and move_mapper.can_move_to_direction(info.unit.pos, direction,
                                                                                    game_state):
                move_mapper.move_unit_to(actions, direction, info, " move to traveler pos", info.target_position)
                return
            else:
                pr(u_prefix, ' traveller cannot move:'+direction)
                if unit.pos.distance_to(info.target_position) <= 1: info.clean_unit_role()

        #   RETURNER
        if info.is_role_returner():
            pr(u_prefix, ' is returner')

            if len(unsafe_cities) == 0:
                info.clean_unit_role()
            else:
                pr(u_prefix, " Returner city2")
                direction, better_cluster_pos, msg = find_best_city(game_state, city_tile_distance(),
                                                                    unsafe_cities, info, player, pr)
                move_unit_to_or_transfer(actions, direction, info, player, u_prefix, unit,
                                         'returner ' + msg)
                return

                    #   HASSLER
        if info.is_role_hassler():
            pr(u_prefix, ' is hassler')
            if opponent.is_position_adjacent_city(unit.pos):
                pr(u_prefix, ' hassler arrived to enemy')
                if unit.can_build(game_state.map):
                    build_city(actions, info, u_prefix, 'hassler build next to city, and done!')
                    info.clean_unit_role()
                    return
                elif unit.get_cargo_space_left() == 0 and best_adjacent_empty_tile() is not None:

                    pr(u_prefix, " hassler full and close to empty, trying to move and build",
                       best_adjacent_empty_tile().pos)
                    direction = unit.pos.direction_to(best_adjacent_empty_tile().pos)
                    next_pos = unit.pos.translate(direction, 1)
                    move_mapper.move_unit_to(actions, direction, info,
                                             " move to build nearby enemy",
                                             next_pos)
                    return

            else:
                enemy_surrounding = MapAnalysis.find_closest_adjacent_enemy_city_tile(unit.pos, opponent)
                direction = unit.pos.direction_to(enemy_surrounding.pos)
                # if nobody is already moving there
                if not move_mapper.has_position(enemy_surrounding.pos):
                    move_mapper.move_unit_to(actions, direction, info, " move to enemy", enemy_surrounding.pos)
                    return

            return
        #   HASSLER ENDS

        # build city tiles adjacent of other tiles to make only one city.
        if unit.can_build(game_state.map):
            if (num_adjacent_enemy_unit() > 0 or is_in_highly_hostile_area()) and unit.cargo.fuel() < 150:
                build_city(actions, info, u_prefix, 'because we are close to enemy')
                return
            if near_city():
                # this is an excellent spot, but is there even a better one, one that join two different cities?
                if game_state_info.turns_to_night > 2:
                    # only if we have then time to build after 2 turns cooldown
                    dummy, num_adjacent_here = MapAnalysis.find_number_of_adjacent_city_tile(unit.pos, player)
                    for adjacent_position in adjacent_empty_tiles():
                        # pr(u_prefix, "XXXXXXX ", num_adjacent_here)
                        dummy, num_adjacent_city = MapAnalysis.find_number_of_adjacent_city_tile(adjacent_position,
                                                                                                 player)
                        # pr(u_prefix, "XXXXXXX ", num_adjacent_city, adjacent_position)
                        if num_adjacent_city > num_adjacent_here and move_mapper.can_move_to_pos(adjacent_position,
                                                                                                 game_state):
                            move_mapper.move_unit_to_pos(actions, info,
                                                         " moved to a place where we can build{0} instead".format(
                                                             str(num_adjacent_city))
                                                         , adjacent_position)
                            return

                do_not_build = False
                if game_state_info.turns_to_night < 4:
                    dummy, cities = MapAnalysis.find_adjacent_city_tile(unit.pos, player)
                    for c in cities:
                        # prx(u_prefix,"XXXX1 auton",c.cityid,c.get_num_tiles(),c.get_autonomy_turns())
                        if c.get_autonomy_turns() < 10:
                            # pr(u_prefix, "Do not build near adjacent", c.cityid,"because low autonomy",
                            #     c.get_autonomy_turns())
                            do_not_build = True
                            if c.get_num_tiles() > 1:
                                # check if city fuel + our cargo will save this city
                                for t in c.citytiles:
                                    turns = max(game_state_info.turns_to_night // 1.5,
                                                min(2, game_state_info.turns_to_night - 1)
                                                )
                                    harvested_fuel = turns * \
                                                     MapAnalysis.get_max_fuel_harvest_in_pos(
                                                         available_resources_tiles, t.pos)
                                    expected_autonomy = (
                                                                c.fuel + unit.cargo.fuel() + harvested_fuel) // c.get_light_upkeep()
                                    # prx(u_prefix, "XXXX1",c.cityid,c.fuel,unit.cargo.fuel(), harvested_fuel,
                                    #                       "//",c.get_light_upkeep(),"=", expected_autonomy)
                                    # prx(u_prefix, "XXXX1 auton+",harvested_fuel," =", c.cityid, c.get_num_tiles(), expected_autonomy)

                                    if t.pos.is_adjacent(unit.pos):
                                        if expected_autonomy >= 10:
                                            pr(u_prefix, "We can save this city by raise autonomy to ",
                                               expected_autonomy)
                                            move_mapper.move_unit_to_pos(actions, info, 'save this city', t.pos)
                                            return

                            break
                        else:
                            # autonomy if we build here
                            increased_upkeep = 23 - 5 * len(cities)
                            expected_autonomy = c.fuel // (c.get_light_upkeep() + increased_upkeep)
                            # prx(u_prefix, "XXXX2 eauto", c.cityid,c.get_num_tiles(), expected_autonomy)
                            if expected_autonomy < 10:
                                pr(u_prefix, "Do not build near adjacent", c.cityid,
                                   "because low expected autonomy",
                                   expected_autonomy)
                                do_not_build = True
                                break

                if not do_not_build:
                    build_city(actions, info, u_prefix, 'in adjacent city!')
                    return

            else:  # if can build but we are not near city

                # if we can move to a tile where we are adjacent, do and it and build there
                if best_adjacent_empty_tile() is not None:
                    pr(u_prefix, " check if adjacent empty is more interesting", best_adjacent_empty_tile().pos)
                    direction = unit.pos.direction_to(best_adjacent_empty_tile().pos)
                    next_pos = unit.pos.translate(direction, 1)
                    # if nobody is already moving there
                    if not move_mapper.has_position(next_pos):
                        pr(u_prefix, " and nobody is moving here")
                        # and if next pos is actually adjacent
                        if player.is_position_adjacent_city(next_pos):
                            move_mapper.move_unit_to(actions, direction, info,
                                                     " we could have build here, but we move close to city instead",
                                                     next_pos)
                            return

            if (not near_city()) and \
                    (game_state_info.turns_to_night > 1 or
                     (game_state_info.turns_to_night == 1 and near_resource)):
                unit_fuel = unit.cargo.fuel()
                if unit_fuel < 200:
                    build_city(actions, info, u_prefix,
                               'NOT in adjacent city, we have not so much fuel ' + str(unit_fuel))
                    return
                else:
                    do_build = True
                    # check if there are cities next to us that are better served with our fuel
                    for city_tile, dist in city_tile_distance().items():
                        distance = dist[0]
                        city_size = abs(dist[2])
                        if city_size >= 5 and distance < 6:
                            do_build = False
                            pr(u_prefix, " we could have built NOT in adjacent city, but there is a need city close"
                               , city_tile.cityid, 'dist', distance, 'size', city_size)
                            info.set_unit_role_returner()
                            break

                    if adjacent_resources:
                        # move away from resource
                        for empty in adjacent_empty_tiles():
                            if move_mapper.can_move_to_pos(empty, game_state):
                                if not MapAnalysis.is_position_adjacent_to_resource(available_resources_tiles,
                                                                                    empty):
                                    direction = unit.pos.direction_to(empty)
                                    move_unit_to_or_transfer(actions, direction, info, player,
                                                             u_prefix, unit, 'high resources')
                                    move_mapper.stay(unit,
                                                     " we could have built, but better moving far away from resurces")
                                    return

                    if do_build:
                        build_city(actions, info, u_prefix,
                                   'NOT in adjacent city, we have lot of fuel, but no city needs saving')
                        return

        # IF WE CANNOT BUILD, or we could and have decided not to
        if in_empty() and near_city() and near_wood():
            # stay here, so we can build
            move_mapper.stay(unit, " empty, near city, near wood, stay here")
            return


        # if we are next to enemy, try to make sure we do not back off
        enemy_pos = opponent.get_units_and_city_number_around_pos(unit.pos)
        if len(enemy_pos) > 0:
            # NEXT TO ENEMY BEHAVIOUR
            if in_city():
                enemy_positions = []
                enemy_direction = []
                for e_pos in enemy_pos:
                    enemy_direction.append(unit.pos.direction_to(e_pos))

                # pick empty that are near wood, not on enemy not backing off, and possibly near city
                if len(adjacent_empty_tiles()) > 0:
                    possible_moves = []
                    for pos in adjacent_empty_tiles():
                        if pos in enemy_positions:
                            continue
                        if not MapAnalysis.is_position_adjacent_to_resource(wood_tiles, pos):
                            continue

                        if move_mapper.can_move_to_pos(pos, game_state):
                            num_adjacent_city = MapAnalysis.find_number_of_adjacent_city_tile(pos, player)
                            is_pos_walk_away = DIRECTIONS.opposite(unit.pos.direction_to(pos)) in enemy_direction
                            possible_moves.append((int(is_pos_walk_away), -num_adjacent_city[0], pos))

                    possible_moves.sort(key=lambda x: (x[0], x[1]))

                    if len(possible_moves) > 0:
                        next_pos = next(iter(possible_moves))[2]
                        move_mapper.move_unit_to(actions, unit.pos.direction_to(next_pos), info, "standing enemy",
                                                 next_pos)
                        return

        else:
            # no enemy or city around us
            possible_moves = []
            for pos in empty_tile_near_resources():
                # look if any walkable empty tile, is near an enemy
                if not move_mapper.can_move_to_pos(pos, game_state):
                    continue  # cannot move here, next
                if opponent.get_num_units_and_city_number_around_pos(pos) == 0:
                    continue  # this is not close to enemy
                pr(u_prefix, 'this pos is around enemy and resource ', pos)
                possible_moves.append(pos)
            # not close to an enemy, but we are in a city close to adjacent that is close to enemy:
            if len(possible_moves) > 0:
                next_pos = next(iter(possible_moves))
                move_mapper.move_unit_to(actions, unit.pos.direction_to(next_pos), info, "block enemy",
                                         next_pos)
                return

        if is_in_highly_hostile_area():
            pr(u_prefix, "hostile area;nearW=", near_wood(), "inRes=", in_resource, 'inEmp=', in_empty())
            # we are in wood in a highly hostile area, rule for building already implemented,
            # here we try try to penetrate and not backoff
            if near_wood() and in_empty():
                move_mapper.stay(unit, "hostile area, empty, near wood, stay here, so we can build")
                return
            if near_wood() and not in_resource:
                # only try to move near wood
                for r in adjacent_resources:
                    if move_mapper.can_move_to_pos(r.pos, game_state):
                        move_mapper.move_unit_to_pos(actions, info, 'hostile area, from near to res', r.pos)
                        return

            transferred = transfer_to_best_friend_outside_resource(actions, adjacent_empty_tiles,
                                                                   available_resources_tiles, info, in_resource,
                                                                   near_resource,
                                                                   player, unit, u_prefix)
            if transferred:
                return

            if in_resource:
                pr(u_prefix, "hostile area, in resource")
                # if we didn't pass to somebody in empty, see if there is something empty
                for empty in MapAnalysis.find_all_adjacent_empty_tiles(game_state, unit.pos):
                    if move_mapper.can_move_to_pos(empty, game_state):
                        move_mapper.move_unit_to_pos(actions, info, 'hostile area, from res to near', empty)
                        return

        if near_wood() and in_empty():
            if unit.get_cargo_space_used() >= 60:
                move_mapper.stay(unit, " Near wood1, in empty, with substantial cargo, stay put")
                return
            elif unit.get_cargo_space_used() >= 40:
                #todo only move closer to another wood, next city or to block enemy
                move_mapper.stay(unit, " Near wood2, in empty, with substantial cargo, stay put")
                return

        if len(unsafe_cities) == 0:
            enough_fuel = math.inf
        else:
            if game_state_info.is_night_time():
                enough_fuel = 500
            elif game_state_info.turns_to_night < 4:
                enough_fuel = 300
            else:
                enough_fuel = 400




        # if near_resource and in_empty() and unit.get_cargo_space_used() >= 0:
        #     transferred = transfer_to_best_friend_outside_resource(actions, adjacent_empty_tiles,
        #                                                           available_resources_tiles, info,
        #                                                           in_resource, near_resource,
        #                                                           player, unit, u_prefix)
        #     if transferred:
        #         pr(u_prefix, " Near resources, transferred to somebody not near resouces")
        #         continue

        if (not info.is_role_returner()) and unit.get_cargo_space_left() > 0 \
                and (unit.cargo.fuel() < enough_fuel or len(unsafe_cities) == 0 or info.is_role_hassler()):
            if not in_resource:
                # find the closest resource if it exists to this unit

                pr(u_prefix, " Find resources")

                if resources_distance is not None and len(resources_distance) > 0:

                    # create a move action to the direction of the closest resource tile and add to our actions list
                    direction, better_cluster_pos, msg, resource_type = \
                        find_best_resource(game_state, resources_distance, resource_target_by_unit,
                                           info, available_resources_tiles, u_prefix, unsafe_cities)
                    if direction == DIRECTIONS.CENTER and len(unsafe_cities) == 0:
                        transferred = transfer_to_best_friend_outside_resource(actions, adjacent_empty_tiles,
                                                                               available_resources_tiles, info,
                                                                               in_resource, near_resource,
                                                                               player, unit, u_prefix)
                        if transferred:
                            return

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
                    move_mapper.move_unit_to(actions, direction, info, msg, better_cluster_pos)
                    return
                else:
                    pr(u_prefix, " resources_distance invalid (or empty?)")
            else:
                resource_type = game_state.map.get_cell(unit.pos.x, unit.pos.y).resource.type
                pr(u_prefix, " Already on resources:", resource_type)
                if resource_type != RESOURCE_TYPES.WOOD \
                        and player.is_unit_in_pos(info.last_move_before_pos) \
                        and (not player.is_unit_in_pos(unit.pos.translate(info.last_move_direction))) \
                        and move_mapper.can_move_to_direction(unit.pos, info.last_move_direction, game_state):
                    move_mapper.move_unit_to(actions, info.last_move_direction, info, 'move a bit further')
                elif resource_type != RESOURCE_TYPES.WOOD and player.is_unit_in_pos(info.last_move_before_pos):
                    transfer_to_best_friend_outside_resource(actions, adjacent_empty_tiles,
                                                             available_resources_tiles, info,
                                                             in_resource,
                                                             near_resource, player, unit, u_prefix)

                elif resource_type == RESOURCE_TYPES.WOOD and \
                        game_state_info.turns_to_night > 10 \
                        and unit.get_cargo_space_left() <= 40 \
                        and best_adjacent_empty_tile() is not None:
                    move_mapper.move_unit_to_pos(actions, info,
                                                 " towards closest empty (anticipating getting resources, wood)",
                                                 best_adjacent_empty_tile().pos)
                else:
                    resource_target_by_unit.setdefault((unit.pos.x, unit.pos.y), []).append(unit.id)
                    move_mapper.stay(unit, " Stay on resources")
                return
        else:
            if game_state_info.turns_to_night > 10 and unit.get_cargo_space_left() <= info.gathered_last_turn \
                    and in_resource and best_adjacent_empty_tile() is not None:
                # if we are on a resource, and we can move to an empty tile,
                # then it means we can at least collect 20 next turn on CD and then build
                # find the closest empty tile it to build a city
                move_mapper.move_unit_to_pos(actions, info,
                                             " towards closest empty (anticipating getting resources)",
                                             best_adjacent_empty_tile().pos)
            elif game_state_info.turns_to_night > 6 and unit.get_cargo_space_left() == 0 \
                    and best_adjacent_empty_tile() is not None:
                # find the closest empty tile it to build a city
                move_unit_to_pos_or_transfer(actions, best_adjacent_empty_tile().pos, info,
                                             player, u_prefix, unit, " towards closest empty ")
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
                            move_mapper.move_unit_to_pos(actions, info, " towards closest next-best-empty ",
                                                         next_pos)
                            break

            elif not info.is_role_hassler():
                pr(u_prefix, " Goto city; fuel=", unit.cargo.fuel())
                # find closest city tile and move towards it to drop resources to a it to fuel the city
                if len(unsafe_cities) > 0:
                    pr(u_prefix, " Goto city2")

                    direction, better_cluster_pos, msg = find_best_city(game_state, city_tile_distance(),
                                                                        unsafe_cities, info, player, pr)

                    pr(u_prefix, " Goto city3: " + msg)
                    if unit.cargo.fuel() >= 200 and info.is_role_none():
                        info.set_unit_role_returner(u_prefix)

                    move_unit_to_or_transfer(actions, direction, info, player, u_prefix, unit,
                                             'city' + msg)
                    pr(u_prefix, " Goto city4")
                    return


def repurpose_unit(best_cluster_cluster, best_cluster_pos, best_cluster_unit, cluster, t_prefix):
    pr(t_prefix, ' repurposing', best_cluster_unit.id, ' from', cluster.id, best_cluster_cluster.to_string_light())
    is_expander = unit_info[best_cluster_unit.id].is_role_city_expander()
    unit_info[best_cluster_unit.id].set_unit_role_explorer(best_cluster_pos)
    if is_expander:
        # we need to set expander some other unit
        for u in cluster.units:
            if unit_info[u].is_role_none():
                pr(t_prefix, best_cluster_cluster.id, 'expander repurposed')
                unit_info[u].set_unit_role_expander(t_prefix)
                break


def send_unit_home(actions, game_state, info, player, u_prefix, unit, msg):
    pr(u_prefix, msg)
    closest_city = find_closest_city_tile_no_logic(unit.pos, player)
    directions = MapAnalysis.directions_to(unit.pos, closest_city)
    for direction in directions:
        if move_mapper.can_move_to_direction(unit.pos, direction, game_state):
            move_mapper.move_unit_to(actions, direction, info, msg, closest_city)
            return True
    return False


def transfer_to_best_friend_outside_resource(actions, adjacent_empty_tiles, available_resources_tiles, info,
                                             in_resource, near_resource, player, unit, prefix) -> bool:
    for pos in adjacent_empty_tiles():
        friend = player.get_unit_in_pos(pos)
        if friend is not None:
            if friend.get_cargo_space_left() == 0:
                continue

            friend_in_resource, friend_near_resource = MapAnalysis.is_position_in_X_adjacent_to_resource(
                available_resources_tiles, friend.pos)

            if in_resource and not friend_in_resource:
                # if we are on resource, but friend is not
                transfer_all_resources(actions, info, friend.id, prefix, pos)
                return True
            elif (not in_resource) and near_resource and not (friend_near_resource or friend_in_resource):
                # if we are near resource, but friend is not
                transfer_all_resources(actions, info, friend.id, prefix, pos)
                return True
            elif (in_resource and friend_in_resource) or \
                    ((not in_resource) and near_resource and (not friend_in_resource) and friend_near_resource) or \
                    (not (in_resource or near_resource or friend_in_resource or friend_near_resource)):
                # if both in or near resourse, or none, transfer to who has more
                if 0 < friend.get_cargo_space_left() < unit.get_cargo_space_left():
                    transfer_all_resources(actions, info, friend.id, prefix, pos)
                    return True

    return False


def get_best_first_move(t_prefix, game_state, initial_city_pos, possible_positions, resource_tiles,
                        initial_enemy_city_pos: Position):
    first_best_position = None
    first_move = {}
    distance_cities = initial_city_pos.distance_to(initial_enemy_city_pos)
    direction_to_enemy = DIRECTIONS.CENTER
    direction_from_enemy = DIRECTIONS.CENTER
    if 3 <= distance_cities <= 4:
        direction_to_enemy = initial_city_pos.direction_to(initial_enemy_city_pos)
        direction_from_enemy = DIRECTIONS.opposite(direction_to_enemy)

    result = get_walkable_that_are_near_resources(t_prefix, possible_positions, resource_tiles)
    for next_pos, res_2 in result.items():
        pr(t_prefix, next_pos, res_2)
        is_empty, has_empty_next = MapAnalysis.is_cell_empty_or_empty_next(next_pos, game_state)
        pr(t_prefix, 'Resources within 2 of', res_2, ';empty', is_empty,
           ';emptyNext', has_empty_next)

        res_4 = len(MapAnalysis.get_resources_around(resource_tiles, next_pos, 4))
        dist = initial_city_pos.distance_to(next_pos)
        direction = initial_city_pos.direction_to(next_pos)

        if dist == 1 and is_empty and res_2 == 3:
            score = 1  # best as we can build in 2
        elif dist == 1 and is_empty and res_2 == 3:
            score = 2  # second best as we can build in 3
        elif is_empty or has_empty_next:
            score = 3  # everything that is either empty or
        else:
            score = 9

        score_aggressive = 0
        if direction == direction_to_enemy:
            score_aggressive = -1  # favour towards enemy
        elif direction == direction_from_enemy:
            score_aggressive = +1  # discourage from enemy

        first_move[next_pos] = (score, dist, score_aggressive, -res_2, -res_4)
    pr(t_prefix, 'Not Ordered Resources within 2', first_move)
    if len(first_move.keys()) > 0:
        result = collections.OrderedDict(sorted(first_move.items(), key=lambda x: x[1]))
        pr(t_prefix, 'Ordered Resources within 2', result)
        first_best_position = next(iter(result.keys()))
        pr(t_prefix, 'first_best_position', first_best_position)
    return first_best_position


def get_walkable_that_are_near_resources(t_prefix, possible_positions, resources):
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


def move_unit_to_pos_or_transfer(actions, pos, info, player, prefix, unit, msg) -> bool:
    direction = info.unit.pos.direction_to(pos)
    return move_unit_to_or_transfer(actions, direction, info, player, prefix, unit, msg)


def move_unit_to_or_transfer(actions, direction, info, player, prefix, unit, msg) -> bool:
    next_pos = unit.pos.translate(direction, 1)
    move_to_city = MapAnalysis.is_position_city(next_pos, player)
    friend_unit = player.get_unit_in_pos(next_pos)
    if direction != DIRECTIONS.CENTER and friend_unit is not None and move_to_city:
        transfer_all_resources(actions, info, friend_unit.id, prefix, next_pos)
        return True

    if unit.get_cargo_space_used() > 0:
        # check if anybody in the pos we want to go
        if friend_unit is not None:
            if unit_info[friend_unit.id].is_role_none() or unit_info[friend_unit.id].is_role_returner() \
                    and friend_unit.get_cargo_space_left() >= unit.get_cargo_space_used():
                pr(prefix, msg, "instead of moving", direction, ", do transfer to", friend_unit.id, ' in ',
                   unit.pos.translate(direction, 1))
                transfer_all_resources(actions, info, friend_unit.id, prefix, next_pos)
                return True

    if direction != DIRECTIONS.CENTER and move_mapper.can_move_to_direction(info.unit.pos, direction, game_state):
        move_mapper.move_unit_to(actions, direction, info, " move to " + msg + " pos", info.target_position)
    else:
        direction = get_random_step(unit.pos)
        move_mapper.move_unit_to(actions, direction, info, "randomly (due to " + msg + ")")

    return False


def find_best_city(game_state, city_tile_distance, unsafe_cities, info: UnitInfo, player, pr) \
        -> Tuple[ DIRECTIONS, Optional[Position], str]:
    unit = info.unit

    for city_tile, payload in city_tile_distance.items():
        if city_tile is None:
            continue

        unit = info.unit
        from_pos = unit.pos
        city_id = payload[3]
        if from_pos.equals(city_tile.pos):
            direction = DIRECTIONS.CENTER
        else:
            directions = MapAnalysis.get_directions_to_city(from_pos, city_id, player)
            # pr(' XXX - directions_to ', directions)
            possible_directions = []
            for direction in directions:
                if direction == DIRECTIONS.CENTER:
                    continue
                next_pos = from_pos.translate(direction, 1)
                if not MapAnalysis.is_position_valid(next_pos, game_state):
                    continue
                if move_mapper.is_position_city(next_pos):
                    city_on_the_way = MapAnalysis.get_city_id_from_pos(next_pos, move_mapper.player)
                    if city_on_the_way not in unsafe_cities:
                        # this is a safe city, but not the one where we want to reach
                        # pr(' XXX - skip ', direction, next_pos, 'as it goes to safe city', city_on_the_way)
                        continue
                possible_directions.append((direction,next_pos))

            # pr(' XXX - possible_directions ', possible_directions)
            # first look for friends in this direction
            for direction,next_pos in possible_directions:
                friend = move_mapper.player.get_unit_in_pos(next_pos)
                if friend is not None:
                    if friend.get_cargo_space_left()>0 and unit.get_cargo_space_used()>0:
                        return direction, city_tile.pos, " towards friend " + friend.id

            # then check if we can move
            for direction,next_pos in possible_directions:
                # if we are trying to move on top of somebody else, skip
                # pr(' XXX - try', direction, next_pos,'mapper', move_mapper.move_mapper.keys())
                msg = unit.id + ' moving to ' + direction
                if move_mapper.can_move_to_pos(next_pos, game_state, msg=msg):
                    return direction, city_tile.pos, " towards closest city" + city_tile.__str__() \
                           + payload.__str__()
                else:
                    # pr(' XXX - skip')
                    continue

    direction = get_random_step(unit.pos)
    return direction, None, "randomly (due to city)"


def build_city(actions, info: UnitInfo, u_prefix, msg=''):
    actions.append(info.unit.build_city())
    pr(u_prefix, '- build city', msg)
    move_mapper.add_position(info.unit.pos, info.unit)
    info.set_last_action_build()


def transfer_all_resources(actions, info: UnitInfo, to_unit_id: str, prefix, pos: Position = None):
    to_unit_string = to_unit_id
    if pos is not None:
        to_unit_string = to_unit_string + pos.__str__()

    if info.unit.cargo.uranium > 0:
        actions.append(info.unit.transfer(to_unit_id, RESOURCE_TYPES.URANIUM, info.unit.cargo.uranium))
        pr(prefix, "Unit", info.unit.id, '- transfer', info.unit.cargo.uranium, 'uranium to ', to_unit_string)
        info.set_last_action_transfer()
        move_mapper.add_position(info.unit.pos, info.unit)
    elif info.unit.cargo.coal > 0:
        actions.append(info.unit.transfer(to_unit_id, RESOURCE_TYPES.COAL, info.unit.cargo.coal))
        pr(prefix, "Unit", info.unit.id, '- transfer', info.unit.cargo.coal, 'coal to ', to_unit_string)
        info.set_last_action_transfer()
        move_mapper.add_position(info.unit.pos, info.unit)
    elif info.unit.cargo.wood > 0:
        actions.append(info.unit.transfer(to_unit_id, RESOURCE_TYPES.WOOD, info.unit.cargo.wood))
        pr(prefix, "Unit", info.unit.id, '- transfer', info.unit.cargo.wood, 'wood to ', to_unit_string)
        info.set_last_action_transfer()
        move_mapper.add_position(info.unit.pos, info.unit)

    if unit_info[to_unit_id].is_role_traveler: unit_info[to_unit_id].clean_unit_role()
    if unit_info[info.unit.id].is_role_returner():
        unit_info[info.unit.id].clean_unit_role('Transferred resources, transfer role')
        unit_info[to_unit_id].set_unit_role_returner(to_unit_id)


def can_city_live(city, all_night_turns_lef) -> bool:
    return city.fuel / (city.get_light_upkeep() + 20) >= min(all_night_turns_lef, 30)


def get_direction_to_quick(game_state: Game, info: UnitInfo, target_pos: Position,
                           resource_tiles, unsafe_cities, allow_clash_unit: bool = False) -> DIRECTIONS:
    # below to turn smart direction on for all resources and city trip
    # return get_direction_to_smart(game_state,unit, target_pos)

    unit: Unit = info.unit
    from_pos = unit.pos
    if from_pos.equals(target_pos):
        return DIRECTIONS.CENTER

    directions = MapAnalysis.directions_to(from_pos, target_pos)
    possible_directions = []

    for direction in directions:
        next_pos = from_pos.translate(direction, 1)

        # if we are trying to move on top of somebody else, skip
        # pr(unit.id,' XXX - try', direction, next_pos)
        if move_mapper.can_move_to_pos(next_pos, game_state, allow_clash_unit, unit.id + ' moving to ' + direction):
            # pr(unit.id, ' XXX - seems ok', direction, next_pos)
            # calculate how many resources there are to gather while walking, and favour those if you have no cargo
            number_of_adjacent_res = len(MapAnalysis.get_resources_around(resource_tiles, next_pos, 1))
            is_empty = MapAnalysis.is_cell_empty(next_pos, game_state)
            near_resources = MapAnalysis.is_position_adjacent_to_resource(resource_tiles, next_pos)
            is_city = move_mapper.is_position_city(next_pos)
            if is_city and unit.get_cargo_space_used() > 0:
                city_id = MapAnalysis.get_city_id_from_pos(next_pos, move_mapper.player)
                if not city_id in unsafe_cities:
                    pr(' try to avoid our city because it is not unsafe, and we have resources')
                    continue
            possible_directions.append(
                (direction,  # 0
                 -number_of_adjacent_res,  # 1
                 -int(is_empty),  # 2
                 -int(is_empty and near_resources),  # 3
                 -int(is_city)  # 4
                 ))
        else:
            # pr(unit.id,' XXX - skip', direction, next_pos)
            continue

    if info.unit.get_cargo_space_left() == 0:
        # if we do not have cargo, favour empty tiles
        possible_directions.sort(key=lambda x: (x[2]))  # sort by it is empty
    elif info.unit.get_cargo_space_left() <= 20:
        # if we have 20 only left, moving in an empty near resources, would just do great
        possible_directions.sort(key=lambda x: (x[3]))  # sort by it is empty and near resources
    elif info.unit.get_cargo_space_left() == 100:
        # no cargo, whatsoever favour cities to travel faster, then more resources
        possible_directions.sort(key=lambda x: (x[4], x[1]))  # sort by it is empty and near resources
    else:
        # in any other case (20<cargo<100), just go where more resources
        possible_directions.sort(key=lambda x: (x[1]))

    if len(possible_directions) == 0:
        return DIRECTIONS.CENTER
    else:
        return next(iter(possible_directions))[0]


def is_resource_minable(actor, resource_type: RESOURCE_TYPES, research_rate=0., in_future_turns=0) -> bool:
    expected_additional_research = int(research_rate * in_future_turns)
    return (resource_type == RESOURCE_TYPES.WOOD) or \
           (resource_type == RESOURCE_TYPES.COAL and actor.research_points + expected_additional_research >= 50) or \
           (resource_type == RESOURCE_TYPES.URANIUM and actor.research_points + expected_additional_research >= 200)


def get_direction_to_smart_XXX(game_state: Game, unit: Unit, target_pos: Position) -> DIRECTIONS:
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


def find_best_resource(game_state, resources_distance, resource_target_by_unit, info,
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
                    direction = get_direction_to_quick(game_state, info, resource.pos, resources,
                                                       unsafe_cities, False)
                    if direction != DIRECTIONS.CENTER:
                        return direction, resource.pos, " towards closest resource ", resource_dist_info[2]

    if len(unsafe_cities) == 0:
        return DIRECTIONS.CENTER, None, "stay where we are as we cannot go to resources, but no unsafe cities", ""
    else:
        direction = get_random_step(unit.pos)
        return direction, None, "randomly (due to resource)", ""


# the next snippet all resources distance and return as sorted order.
def find_resources_distance(pos, clusters: ClusterControl, resource_tiles, game_info: GameInfo) -> Dict[CityTile,
                                                                                                        Tuple[
                                                                                                            int, int, DIRECTIONS]]:
    resources_distance = {}
    adjacent_resources = {}
    for resource_tile in resource_tiles:

        score = 0
        if resource_tile.pos in clusters.resource_pos_to_cluster:
            cluster = clusters.resource_pos_to_cluster[resource_tile.pos]
            # prx("XXX1",game_info.turn,resource_tile.pos,resource_tile.resource.type," in ",cluster.id,cluster.get_centroid())
            # prx("XXX2",game_info.turn,cluster.to_string_light(),file=sys.stderr)
            # prx("XXX3",game_info.turn,cluster.id, len(cluster.perimeter), len(cluster.walkable_perimeter))
            if len(cluster.perimeter_accessible) == 0:
                score = 2  # not accessible, (and therefore also not walkable)
            elif len(cluster.perimeter_walkable) == 0:
                score = 1  # accessible but not walkable

        dist = resource_tile.pos.distance_to(pos)

        if resource_tile.resource.type == RESOURCE_TYPES.WOOD:
            resources_distance[resource_tile] = (score, dist, -resource_tile.resource.amount)
            if dist == 1:
                adjacent_resources[resource_tile] = (resource_tile.resource.amount, resource_tile.resource.type)

        else:
            expected_resource_additional = (float(dist * 2.0) * float(game_info.get_research_rate(5)))
            expected_resource_at_distance = float(game_info.reseach_points) + expected_resource_additional
            # check if we are likely to have researched this by the time we arrive
            if resource_tile.resource.type == RESOURCE_TYPES.COAL and \
                    expected_resource_at_distance < 50.0:
                continue
            elif resource_tile.resource.type == RESOURCE_TYPES.URANIUM and \
                    expected_resource_at_distance < 200.0:
                continue
            else:
                # order by distance asc, resource asc
                resources_distance[resource_tile] = (score, dist, -resource_tile.resource.amount)
                if dist == 1:
                    adjacent_resources[resource_tile] = (resource_tile.resource.amount, resource_tile.resource.type)

    resources_distance = collections.OrderedDict(sorted(resources_distance.items(), key=lambda x: x[1]))
    return resources_distance, adjacent_resources
