from lux.game import Game
from lux.game_map import Cell, RESOURCE_TYPES, Position
from lux.constants import Constants
from lux.game_constants import GAME_CONSTANTS
from collections import OrderedDict
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

def is_cell_empty(pos, game_state):
    cell = game_state.map.get_cell(pos.x,pos.y)
    result = (not cell.has_resource()) and cell.citytile is None;
    #print("- ", pos, 'empty',result, file=sys.stderr)
    return result

# snippet to find the all citytiles distance and sort them.
def find_number_of_adjacent_city_tile(pos, player):
    number = 0
    for city in player.cities.values():
        for citytiles in city.citytiles:
            if citytiles.pos.is_adjacent(pos):
                number=number+1

    return number

def find_closest_empty_tile(pos, game_state,player):
    adjacent_positions = [Position(pos.x+1,pos.y),Position(pos.x,pos.y+1),Position(pos.x-1,pos.y),Position(pos.x,pos.y-1)];
    empty_tyles=[]
    for adjacent_position in adjacent_positions:
        try:
            if is_cell_empty(adjacent_position,game_state):
                empty_tyles.append(adjacent_position)
        except Exception:
            continue
    if len(empty_tyles)==0:
        return None
    elif len(empty_tyles)==1:
        return game_state.map.get_cell_by_pos(empty_tyles[0])
    else:
        #print("Trying to solve which empty one is close to most cities tiles", file=sys.stderr)
        results = OrderedDict()
        for adjacent_position in empty_tyles:
            number_of_adjacent = find_number_of_adjacent_city_tile(adjacent_position,player)
            results[number_of_adjacent] = adjacent_position
            print("- ",adjacent_position,number_of_adjacent, file=sys.stderr)
        # ordered by number of tiles, so we take last element
        #print("results", results, file=sys.stderr)
        result = list(results.values())[-1]
        #print("Return", result, file=sys.stderr)
        return game_state.map.get_cell_by_pos(result)


# the next snippet all resources distance and return as sorted order.
def find_resources_distance(pos, player, resource_tiles):
    resources_distance = {}
    for resource_tile in resource_tiles:
        # we skip over resources that we can't mine due to not having researched them
        if resource_tile.resource.type == Constants.RESOURCE_TYPES.COAL and not player.researched_coal(): continue
        if resource_tile.resource.type == Constants.RESOURCE_TYPES.URANIUM and not player.researched_uranium(): continue
        dist = resource_tile.pos.distance_to(pos)
        # order by distance asc, resource asc
        resources_distance[resource_tile] = (dist,-resource_tile.resource.amount)
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
                # order by distance asc, autonomy desc
                city_tiles_distance[city_tile] = (dist,-get_autonomy_turns(city))
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

    # max number of units available
    units_cap = sum([len(x.citytiles) for x in player.cities.values()])
    # current number of units
    units = len(player.units)

    night_steps_left = ((359 - game_state.turn) // 40 + 1) * 10
    steps_until_night = 30 - game_state.turn % 40

    cities = list(player.cities.values())
    if len(cities) > 0:
        for city in cities:
            can_create_worker = (units < units_cap)
            turns_city_can_live = get_autonomy_turns(city)
            print("City ", city.cityid,'size=', len(city.citytiles), ' fuel=',city.fuel,' upkeep=',city.get_light_upkeep(),'autonomy',turns_city_can_live,file=sys.stderr)

            for city_tile in city.citytiles[::-1]:
                print("- Citytile ", city_tile.pos, " CD=", city_tile.cooldown,file=sys.stderr)
                if city_tile.can_act():
                    if not can_create_worker:
                        # let's do research
                        action = city_tile.research()
                        actions.append(action)
                        print("- - research" ,file=sys.stderr)
                    else:
                        # let's create one more unit in the last created city tile if we can
                        action = city_tile.build_worker()
                        actions.append(action)
                        can_create_worker = False
                        print("- - created worker", file = sys.stderr)



    # we want to build new tiless only if we have a lot of fuel in all cities
    can_build = can_build_for_resources(night_steps_left,steps_until_night, player)

    print("night_step_left ", night_steps_left, "steps_until_night ", steps_until_night, 'can_build: ', can_build,file=sys.stderr)

    # trace the agent move
    move_mapper = {}
    # store all unit current location on move tracker
    for unit in player.units:
        move_mapper[(unit.pos.x, unit.pos.y)] = unit

    #     print("Straing unit loop..")

    for unit in player.units:
        print("Unit",unit.id,";pos",unit.pos,'CD=',unit.cooldown,unit.cargo,'free:', unit.get_cargo_space_left(),"canBuildHere",unit.can_build(game_state.map),file=sys.stderr)
        # if the unit is a worker (can mine resources) and can perform an action this turn
        #         print('free:', unit.get_cargo_space_left())
        #         print('cooldown:', unit.cooldown )
        if unit.is_worker() and unit.can_act():

            # build city tiles adjacent of other tiles to make only one city.
            if unit.can_build(game_state.map):
                #if is_position_adjacent_city(player, unit.pos):
                    build_city(actions, unit,'in adjacent city..')
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
                                direction = unit.pos.direction_to(closest_resource_tile.pos)
                                next_pos = unit.pos.translate(direction, 1)

                                #if we are trying to move on top of somebody else, abort
                                if move_mapper.get((next_pos.x, next_pos.y)):
                                    continue

                                can_move = True
                                move_unit_to(actions, direction, move_mapper, unit," towards closest resource ",closest_resource_tile.pos)
                                break
                    if not can_move:
                        direction = get_random_step()
                        move_unit_to(actions, direction, move_mapper, unit,"randomly (due to resource)")


            else:
                closest_empty_tile = find_closest_empty_tile(unit.pos, game_state, player)
                if steps_until_night > 10 and can_build and unit.get_cargo_space_left() <= 20 and is_position_resource(resource_tiles, unit.pos) and closest_empty_tile is not None:
                    # if we are on a resource, and we can move to an empty tile, then it means we can at least collect 20 next turn on CD and then build
                    # find the closest empty tile it to build a city
                    direction = unit.pos.direction_to(closest_empty_tile.pos)
                    move_unit_to(actions, direction, move_mapper, unit, " towards closest empty (anticipating getting resources)", closest_empty_tile.pos)
                elif steps_until_night > 10 and can_build and unit.get_cargo_space_left() == 0 and closest_empty_tile is not None:
                    # find the closest empty tile it to build a city
                    direction = unit.pos.direction_to(closest_empty_tile.pos)
                    move_unit_to(actions, direction, move_mapper, unit, " towards closest empty ", closest_empty_tile.pos)
                else:
                    # find the closest citytile and move the unit towards it to drop resources to a citytile to fuel the city
                    if city_tile_distance is not None and len(city_tile_distance) > 0:
                        closest_city_tile = None
                        can_move = False
                        for city_tile, dist in city_tile_distance.items():
                            if move_mapper.get((city_tile.pos.x, city_tile.pos.y)) is None:
                                closest_city_tile = city_tile

                                if closest_city_tile is not None:
                                    direction = unit.pos.direction_to(closest_city_tile.pos)
                                    next_pos = unit.pos.translate(direction, 1)

                                    if move_mapper.get((next_pos.x, next_pos.y)):
                                        continue

                                    can_move = True
                                    move_unit_to(actions, direction, move_mapper, unit, " towards closest city ",closest_city_tile.pos)
                                    break

                        if not can_move:
                            direction = get_random_step()
                            move_unit_to(actions, direction, move_mapper, unit,"randomly (due to city)")

    #     print(move_mapper)
    #     print('')
    return actions


def get_autonomy_turns(city):
    turns_city_can_live = city.fuel // city.get_light_upkeep()
    return turns_city_can_live


def build_city(actions, unit,msg=''):
    action = unit.build_city()
    actions.append(action)
    print("Unit", unit.id, '- build city',msg, file=sys.stderr)


def can_build_for_resources(night_steps_left, steps_until_night,player):
    if steps_until_night>20:
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



def move_unit_to(actions, direction, move_mapper, unit, reason="", pos=None):
    next_state_pos = unit.pos.translate(direction, 1)
    action = unit.move(direction)
    actions.append(action)
    move_mapper[(next_state_pos.x, next_state_pos.y)] = unit
    if pos is None:
        print("Unit", unit.id,'- moving towards "',direction,'" ',reason, file=sys.stderr)
    else:
        actions.append(annotate.line(unit.pos.x, unit.pos.y, pos.x,pos.y))
        actions.append(annotate.text(unit.pos.x, unit.pos.y, reason))
        print("Unit", unit.id,'- moving towards "', direction, '" ', reason, pos, file=sys.stderr)


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

def get_position_city(player, pos):
    for city in player.cities.values():
        for citytiles in city.citytiles:
            if citytiles.pos.equals(pos):
                return city.cityid

    return ''