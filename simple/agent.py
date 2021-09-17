# for kaggle-environments
from lux.game import Game
from lux.game_map import Cell, RESOURCE_TYPES
from lux.constants import Constants
from lux.game_constants import GAME_CONSTANTS
from lux import annotate
import math
import sys


### Define helper functions

def get_cell_from_pos(game_state,pos):
    return game_state.map.get_cell(pos.x, pos.y)

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

def can_build_now(player,night_step_left):
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
    night_step_left = 40 - max((observation["step"] % 40), 30)

    resource_tiles = find_resources(game_state)

    can_build = can_build_now(player, night_step_left)

    for unit in player.units:
        # if the unit is a worker (can mine resources) and can perform an action this turn
        if unit.is_worker() and unit.can_act():

            is_building = False
            # we want to mine only if there is space left in the worker's cargo
            if can_build and unit.can_build(game_state.map):
                #                 print("Is build...")
                # build city tiles is_adjacent of other tiles to make only one city.
                for city in player.cities.values():
                    for citytiles in city.citytiles:
                        if citytiles.pos.is_adjacent(unit.pos):
                            is_building = True
                            #                             print("IS Build")
                            break

                    if is_building:
                        break

                if is_building:
                    action = unit.build_city()
                    actions.append(action)
                    can_build = False
                    #                     print('city build..')
                    continue
            #
            if is_building:
                continue

            # we want to mine only if there is space left in the worker's cargo
            if unit.get_cargo_space_left() > 0:
                # find the closest resource if it exists to this unit
                closest_resource_tile = find_closest_resources(unit.pos, player, resource_tiles)
                if closest_resource_tile is not None:
                    # create a move action to move this unit in the direction of the closest resource tile and add to our actions list
                    action = unit.move(unit.pos.direction_to(closest_resource_tile.pos))
                    actions.append(action)
            else:

                # find the closest citytile and move the unit towards it to drop resources to a citytile to fuel the city
                closest_city_tile = find_closest_city_tile(unit.pos, player)
                if closest_city_tile is not None:
                    # create a move action to move this unit in the direction of the closest resource tile and add to our actions list
                    action = unit.move(unit.pos.direction_to(closest_city_tile.pos))
                    actions.append(action)

    return actions