import time
import heapq
from collections import defaultdict, deque
from typing import DefaultDict, Dict, List, Tuple, Set

import numpy as np

from .constants import Constants
from .game_map import GameMap, RESOURCE_TYPES
from .game_objects import Player, Unit, City, CityTile
from .game_position import Position
from .game_constants import GAME_CONSTANTS

INPUT_CONSTANTS = Constants.INPUT_CONSTANTS


class Mission:
    def __init__(self, unit_id: str, target_position: Position, target_action: str = ""):
        self.target_position: Position = target_position
        self.target_action: str = target_action
        self.unit_id: str = unit_id
        self.delays: int = 0
        # [TODO] some expiry date for each mission

    def __str__(self):
        return " ".join([str(self.target_position), self.target_action])


class Missions(defaultdict):
    def __init__(self):
        self: DefaultDict[str, Mission] = defaultdict(Mission)

    def add(self, mission: Mission):
        self[mission.unit_id] = mission

    def cleanup(self, player: Player,
                player_city_tile_xy_set: Set[Tuple],
                opponent_city_tile_xy_set: Set[Tuple],
                convolved_collectable_tiles_xy_set: Set[Tuple]):
        # probably should be a standalone function instead of a method

        for unit_id in list(self.keys()):
            mission: Mission = self[unit_id]

            # if dead, delete from list
            if unit_id not in player.units_by_id:
                del self[unit_id]
                continue

            unit: Unit = player.units_by_id[unit_id]
            # if you want to build city without resource, delete from list
            if mission.target_action and mission.target_action[:5] == "bcity":
                if unit.cargo == 0:
                    del self[unit_id]
                    continue

            # if opponent has already built a base, reconsider your mission
            if tuple(mission.target_position) in opponent_city_tile_xy_set:
                del self[unit_id]
                continue

            # if you are in a base, reconsider your mission
            if tuple(unit.pos) in player_city_tile_xy_set:
                del self[unit_id]
                continue

            # if your target no longer have resource, reconsider your mission
            if tuple(mission.target_position) not in convolved_collectable_tiles_xy_set:
                del self[unit_id]
                continue

    def __str__(self):
        return " ".join([unit_id + " " + str(x) for unit_id,x in self.items()])

    def get_targets(self):
        return [mission.target_position for unit_id, mission in self.items()]

    def get_targets_and_actions(self):
        return [(mission.target_position, mission.target_action) for unit_id, mission in self.items()]


class DisjointSet:
    def __init__(self):
        self.parent = {}
        self.sizes = defaultdict(int)
        self.points = defaultdict(int)  # tracks resource pile size
        self.num_sets = 0

    def find(self, a, point=0):
        if a not in self.parent:
            self.parent[a] = a
            self.sizes[a] += 1
            self.points[a] += point
            self.num_sets += 1
        acopy = a
        while a != self.parent[a]:
            a = self.parent[a]
        while acopy != a:
            self.parent[acopy], acopy = a, self.parent[acopy]
        return a

    def union(self, a, b):
        a, b = self.find(a), self.find(b)
        if a != b:
            if self.sizes[a] < self.sizes[b]:
                a, b = b, a

            self.num_sets -= 1
            self.parent[b] = a
            self.sizes[a] += self.sizes[b]
            self.points[a] += self.points[b]

    def get_size(self, a):
        return self.sizes[self.find(a)]

    def get_point(self, a):
        return self.points[self.find(a)]

    def get_groups(self):
        groups = defaultdict(list)
        for element in self.parent:
            leader = self.find(element)
            if leader:
                groups[leader].append(element)
        return groups

    def get_group_count(self):
        return sum(self.points[leader] > 1 for leader in self.get_groups().keys())


class Game:

    # counted from the time after the objects are saved to disk
    compute_start_time = -1

    def _initialize(self, messages):
        """
        initialize state
        """
        self.player_id: int = int(messages[0])
        self.turn: int = -1
        # get some other necessary initial input
        mapInfo = messages[1].split(" ")
        self.map_width: int = int(mapInfo[0])
        self.map_height: int = int(mapInfo[1])
        self.map: GameMap = GameMap(self.map_width, self.map_height)
        self.players: List[Player] = [Player(0), Player(1)]

        self.x_iteration_order = list(range(self.map_width))
        self.y_iteration_order = list(range(self.map_height))
        self.dirs: List = [
            Constants.DIRECTIONS.NORTH,
            Constants.DIRECTIONS.EAST,
            Constants.DIRECTIONS.SOUTH,
            Constants.DIRECTIONS.WEST,
            Constants.DIRECTIONS.CENTER
        ]
        self.dirs_dxdy: List = [(0,-1), (1,0), (0,1), (-1,0), (0,0)]


    def fix_iteration_order(self):
        '''
        Fix iteration order at initisation to allow moves to be symmetric
        '''
        assert len(self.player.cities) == 1
        assert len(self.opponent.cities) == 1
        px,py = tuple(list(self.player.cities.values())[0].citytiles[0].pos)
        ox,oy = tuple(list(self.opponent.cities.values())[0].citytiles[0].pos)

        flipping = False
        self.y_order_coefficient = 1
        self.x_order_coefficient = 1

        if px == ox:
            if py < oy:
                flipping = True
                self.y_iteration_order = self.y_iteration_order[::-1]
                self.y_order_coefficient = -1
                idx1, idx2 = 0,2
        elif py == oy:
            if px < ox:
                flipping = True
                self.x_iteration_order = self.x_iteration_order[::-1]
                self.x_order_coefficient = -1
                idx1, idx2 = 1,3
        else:
            assert False

        if flipping:
            self.dirs[idx1], self.dirs[idx2] = self.dirs[idx2], self.dirs[idx1]
            self.dirs_dxdy[idx1], self.dirs_dxdy[idx2] = self.dirs_dxdy[idx2], self.dirs_dxdy[idx1]


    def _end_turn(self):
        print("D_FINISH")


    def _reset_player_states(self):
        self.players[0].units = []
        self.players[0].cities = {}
        self.players[0].city_tile_count = 0
        self.players[1].units = []
        self.players[1].cities = {}
        self.players[1].city_tile_count = 0

        self.player: Player = self.players[self.player_id]
        self.opponent: Player = self.players[1 - self.player_id]

    def get_match_status(self):
        return 'c={0}:{1} '.format(self.player.city_tile_count, self.opponent.city_tile_count) \
               + 'u={0}:{1}'.format(len(self.player.units), len(self.opponent.units))

    def get_research_status(self):
        return 'r={0}:{1}'.format(self.player.research_points,self.opponent.research_points)

    def _update(self, messages):
        """
        update state
        """
        self.map = GameMap(self.map_width, self.map_height)
        self.turn += 1
        self._reset_player_states()

        for update in messages:
            if update == "D_DONE":
                break
            strs = update.split(" ")
            input_identifier = strs[0]

            if input_identifier == INPUT_CONSTANTS.RESEARCH_POINTS:
                team = int(strs[1])   # probably player_id
                self.players[team].research_points = int(strs[2])

            elif input_identifier == INPUT_CONSTANTS.RESOURCES:
                r_type = strs[1]
                x = int(strs[2])
                y = int(strs[3])
                amt = int(float(strs[4]))
                self.map._setResource(r_type, x, y, amt)

            elif input_identifier == INPUT_CONSTANTS.UNITS:
                unittype = int(strs[1])
                team = int(strs[2])
                unitid = strs[3]
                x = int(strs[4])
                y = int(strs[5])
                cooldown = float(strs[6])
                wood = int(strs[7])
                coal = int(strs[8])
                uranium = int(strs[9])
                unit = Unit(team, unittype, unitid, x, y, cooldown, wood, coal, uranium)
                self.players[team].units.append(unit)
                self.map.get_cell(x, y).unit = unit

            elif input_identifier == INPUT_CONSTANTS.CITY:
                team = int(strs[1])
                cityid = strs[2]
                fuel = float(strs[3])
                lightupkeep = float(strs[4])
                self.players[team].cities[cityid] = City(team, cityid, fuel, lightupkeep)

            elif input_identifier == INPUT_CONSTANTS.CITY_TILES:
                team = int(strs[1])
                cityid = strs[2]
                x = int(strs[3])
                y = int(strs[4])
                cooldown = float(strs[5])
                city = self.players[team].cities[cityid]
                citytile = city._add_city_tile(x, y, cooldown)
                self.map.get_cell(x, y).citytile = citytile
                self.players[team].city_tile_count += 1

            elif input_identifier == INPUT_CONSTANTS.ROADS:
                x = int(strs[1])
                y = int(strs[2])
                road = float(strs[3])
                self.map.get_cell(x, y).road = road

        # create indexes to refer to unit by id
        self.player.make_index_units_by_id()
        self.opponent.make_index_units_by_id()


