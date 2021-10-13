import sys
from typing import Tuple

from lux.game_objects import Player, Unit, DIRECTIONS
from lux.game_map import Position
import maps.map_analysis as MapAnalysis



class MoveHelper:
    def __init__(self, player, opponent, turn,pr):
        """
        initialize state
        """
        self.move_mapper = {}
        self.player = player
        self.opponent = opponent
        self.turn = turn
        self.log_prefix = "T_{0}".format(str(self.turn))
        self.pr=pr

    def add_position(self, pos: Position, unit: Unit):
        self.move_mapper[self.__hash_pos__(pos)] = unit

    def has_position(self, pos: Position) -> bool:
        if self.__hash_pos__(pos) in self.move_mapper:
            return True
        else:
            return False

    def __hash_pos__(self, pos: Position) -> Tuple[int, int]:
        return pos.x, pos.y

    def can_move_to_direction(self, pos: Position, direction: DIRECTIONS,game_state) -> bool:
        return self.can_move_to_pos(pos.translate(direction, 1),game_state)

    def can_move_to_pos(self, pos: Position, game_state, allow_clash_unit: bool = False, msg: str = '') -> bool:
        # we cannot move if somebody is already going, and it is not a city
        if ((not allow_clash_unit) and self.has_position(pos)) and not self.is_position_city(pos):
            unit: Unit = self.move_mapper.get(self.__hash_pos__(pos))
            self.pr(self.log_prefix + msg, 'Collision in', pos, 'with', unit.id)
            return False
        else:
            return MapAnalysis.is_position_valid(pos,game_state) and not self.is_position_enemy_city(pos)

    def cannot_move_to(self, pos: Position) -> bool:
        return not self.can_move_to_pos(pos)

    def is_position_city(self, pos: Position) -> bool:
        return MapAnalysis.get_city_id_from_pos(pos, self.player) != ''

    def is_position_enemy_city(self, pos: Position) -> bool:
        return MapAnalysis.get_city_id_from_pos(pos, self.opponent) != ''



