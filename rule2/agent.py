from lux.game import Game
from lux.game_map import Cell, RESOURCE_TYPES, Position
from lux.constants import Constants
from lux.game_constants import GAME_CONSTANTS
from lux import annotate
import math
import sys
import collections
### Define helper functions

# this snippet finds all resources stored on the map and puts them into a list so we can search over them
def find_resources(game_state):
    resource_tiles: list[Cell] = []
    width, height = game_state.map_width, game_state.map_height
    for y in range(height):
        for x in range(width):
            cell = game_state.map.get_cell(x, y)
            if cell.has_resource():
                resource_tiles.append(cell)
    return resource_tiles

# the next snippet finds the closest resources that we can mine given position on a map
def find_closest_resources(pos, player, resource_tiles):
    closest_dist = math.inf
    closest_resource_tile = None
    for resource_tile in resource_tiles:
        # we skip over resources that we can't mine due to not having researched them
        if resource_tile.resource.type == Constants.RESOURCE_TYPES.COAL and not player.researched_coal(): continue
        if resource_tile.resource.type == Constants.RESOURCE_TYPES.URANIUM and not player.researched_uranium(): continue
        dist = resource_tile.pos.distance_to(pos)
        if dist < closest_dist:
            closest_dist = dist
            closest_resource_tile = resource_tile
    return closest_resource_tile

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


# the next snippet all resources distance and return as sorted order.
def find_resources_distance(pos, player, resource_tiles):
    resources_distance = {}
    for resource_tile in resource_tiles:
        # we skip over resources that we can't mine due to not having researched them
        if resource_tile.resource.type == Constants.RESOURCE_TYPES.COAL and not player.researched_coal(): continue
        if resource_tile.resource.type == Constants.RESOURCE_TYPES.URANIUM and not player.researched_uranium(): continue
        dist = resource_tile.pos.distance_to(pos)
        resources_distance[resource_tile] = dist
    resources_distance = collections.OrderedDict(sorted(resources_distance.items(), key= lambda x:x[1]))
    return resources_distance



# snippet to find the all citytiles distance and sort them.
def find_city_tile_distance(pos, player):
    city_tiles_distance = {}
    if len(player.cities) > 0:
        closest_dist = math.inf
        # the cities are stored as a dictionary mapping city id to the city object, which has a citytiles field that
        # contains the information of all citytiles in that city
        for k, city in player.cities.items():
            for city_tile in city.citytiles:
                dist = city_tile.pos.distance_to(pos)
                city_tiles_distance[city_tile] = dist
    city_tiles_distance = collections.OrderedDict(sorted(city_tiles_distance.items(), key= lambda x:x[1]))
#     print(len(city_tiles_distance))
    return city_tiles_distance

import random
def get_random_step():
    return random.choice(['s','n','w','e'])


game_state = None


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
    width, height = game_state.map.width, game_state.map.height

    # add debug statements like so!
    if game_state.turn == 0:
        print("Agent is running!", file=sys.stderr)

    print("----------------------- Turn number ",game_state.turn,"----------------------------", file=sys.stderr)

    resource_tiles = find_resources(game_state)
    #     print("Observation setp: ",observation["step"])

    #     build_worker()

    #     print(len(player.cities))
    #     print(len(player.units))

    total_city_tiles = sum([len(city.citytiles) for city in player.cities.values()])
    #     print('Total City: ', len(player.cities.values()))
    #     print('total citytiles: ', total_city_tiles)

    if total_city_tiles > len(player.units):
        for city in player.cities.values():
            city_tiles = city.citytiles[0]
            if city_tiles.cooldown <= 0:
                action = city_tiles.build_worker()
                actions.append(action)
                break

    night_step_left = 40 - max((observation["step"] % 40), 30)

    can_build = can_build_due_to_night(night_step_left, player)

    # tract the agent move
    move_mapper = {}
    # store all unit current location on move tracker
    for unit in player.units:
        move_mapper[(unit.pos.x, unit.pos.y)] = unit

    #     print("Straing unit loop..")

    for unit in player.units:
        print("Unit ",unit.id," pos ",unit.pos,' can act',unit.can_act(), file=sys.stderr)
        # if the unit is a worker (can mine resources) and can perform an action this turn
        #         print('free space: ', unit.get_cargo_space_left())
        #         print('cool down: ', unit.cooldown )
        if unit.is_worker() and unit.can_act():
            # build city tiles adjacent of other tiles to make only one city.
            if can_build and unit.can_build(game_state.map):
                if is_position_adjacent_city(player, unit.pos):
                    action = unit.build_city()
                    actions.append(action)
                    can_build = False
                    print('- build city in adjacent city..', file=sys.stderr)
                    continue
            #

            # if unit cant make citytiles try to collct resouce collection.
            resources_distance = find_resources_distance(unit.pos, player, resource_tiles)
            city_tile_distance = find_city_tile_distance(unit.pos, player)
            #             print(closest_resource_tile.resource.type, closest_resource_tile.resource.amount)

            if unit.get_cargo_space_left() > 0 and not is_position_resource(resource_tiles, unit.pos):
                # find the closest resource if it exists to this unit

                #                 print(closest_resource_tile

                if resources_distance is not None and len(resources_distance) > 0:
                    # create a move action to move this unit in the direction of the closest resource tile and add to our actions list
                    closest_resource_tile, c_dist = None, None
                    can_move = False
                    for resource, dist in resources_distance.items():
                        if move_mapper.get((resource.pos.x, resource.pos.y)) is None:
                            closest_resource_tile = resource
                            c_dist = dist

                            #                     print(closest_resource_tile.resource.type, closest_resource_tile.resource.amount)
                            if closest_resource_tile is not None and not closest_resource_tile.pos.equals(unit.pos):
                                actions.append(annotate.line(unit.pos.x, unit.pos.y, closest_resource_tile.pos.x,
                                                             closest_resource_tile.pos.y))
                                direction = unit.pos.direction_to(closest_resource_tile.pos)
                                next_pos = unit.pos.translate(direction, 1)

                                #if we are trying to move on top of somebody else, abort
                                if move_mapper.get((next_pos.x, next_pos.y)):
                                    continue

                                can_move = True
                                move_unit_to(actions, direction, move_mapper, unit," towards closest resource "+closest_resource_tile.pos.__str__())
                                break
                    if not can_move:
                        direction = get_random_step()
                        move_unit_to(actions, direction, move_mapper, unit,"randomly (due to resource)")

            else:
                # find the closest citytile and move the unit towards it to drop resources to a citytile to fuel the city
                if city_tile_distance is not None and len(city_tile_distance) > 0:
                    closest_city_tile = None
                    can_move = False
                    for city_tile, dist in city_tile_distance.items():
                        if move_mapper.get((city_tile.pos.x, city_tile.pos.y)) is None:
                            closest_city_tile = city_tile

                            if closest_city_tile is not None:
                                # create a move action to move this unit in the direction of the closest resource tile and add to our actions list
                                actions.append(annotate.line(unit.pos.x, unit.pos.y, closest_city_tile.pos.x,
                                                             closest_city_tile.pos.y))
                                #                         action = unit.move(unit.pos.direction_to(closest_city_tile.pos))
                                direction = unit.pos.direction_to(closest_city_tile.pos)
                                next_pos = unit.pos.translate(direction, 1)

                                if move_mapper.get((next_pos.x, next_pos.y)):
                                    continue

                                can_move = True
                                move_unit_to(actions, direction, move_mapper, unit, " towards closest city "+closest_city_tile.pos.__str__())
                                #                         print('Back in city..')
                                break

                    if not can_move:
                        direction = get_random_step()
                        move_unit_to(actions, direction, move_mapper, unit,"randomly (due to city)")

    #     print(move_mapper)
    #     print('')
    return actions


def move_unit_to(actions, direction, move_mapper, unit, reason=""):
    next_state_pos = unit.pos.translate(direction, 1)
    action = unit.move(direction)
    actions.append(action)
    move_mapper[(next_state_pos.x, next_state_pos.y)] = unit
    print('- moving towards "',direction,'" ',reason, file=sys.stderr)


def can_build_due_to_night(night_step_left, player):
    can_build = False
    if len(player.cities) > 0:
        for k, city in player.cities.items():
            #             print(city.fuel)
            total_city_tiles = len(city.citytiles)
            #             print(total_city_tiles)

            total_need_fuel = (23 * total_city_tiles * night_step_left) * 3.5
            #             print('fuel need: ', total_need_fuel)

            if city.fuel - total_need_fuel > 20:
                can_build = True
                #                 print('can build true')
                break
    return can_build


def is_position_adjacent_city(player, pos):
    for city in player.cities.values():
        for citytiles in city.citytiles:
            if citytiles.pos.is_adjacent(pos):
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