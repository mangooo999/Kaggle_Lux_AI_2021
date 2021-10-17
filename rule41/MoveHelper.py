import sys
from typing import Tuple

from lux.game_objects import Player, Unit, DIRECTIONS
from lux.game_map import Position
from lux import annotate
import maps.map_analysis as MapAnalysis
from UnitInfo import UnitInfo

class MoveHelper:
    def __init__(self, player, opponent, turn, pr):
        """
        initialize state
        """
        self.initial_position_mapper = {}
        self.movement_mapper = {}
        self.player = player
        self.opponent = opponent
        self.turn = turn
        self.log_prefix = "T_{0}".format(str(self.turn))
        self.pr = pr


    def add_initial_position(self, pos: Position, unit: Unit):
        # self.pr(self.log_prefix, 'XXX initial',unit.id ,' in', pos)
        self.initial_position_mapper[self.__hash_pos__(pos)] = unit

    def add_position(self, pos: Position, unit: Unit):
        # self.pr(self.log_prefix, 'XXX movement', unit.id, ' in', pos)
        self.movement_mapper[self.__hash_pos__(pos)] = unit

    def has_initial_position(self, pos: Position) -> bool:
        return self.__hash_pos__(pos) in self.initial_position_mapper

    def has_movement_position(self, pos: Position) -> bool:
        return self.__hash_pos__(pos) in self.movement_mapper

    def has_position(self, pos: Position) -> bool:
        return self.has_initial_position(pos) or \
                self.has_movement_position(pos)

    def get_unit_from_mapper(self,pos) -> Unit:
        if self.__hash_pos__(pos) in self.initial_position_mapper:
            return self.initial_position_mapper.get(self.__hash_pos__(pos))
        elif self.__hash_pos__(pos) in self.movement_mapper:
            return self.movement_mapper.get(self.__hash_pos__(pos))
        else:
            return None


    def __hash_pos__(self, pos: Position) -> Tuple[int, int]:
        return pos.x, pos.y

    def can_move_to_direction(self, from_pos: Position, direction: DIRECTIONS,game_state) -> bool:
        return self.can_move_to_pos(from_pos.translate(direction, 1),game_state)

    def can_move_to_pos(self, pos: Position, game_state, allow_clash_unit: bool = False, msg: str = '') -> bool:
        # we cannot move if somebody is already going, and it is not a city
        if ((not allow_clash_unit) and self.has_initial_position(pos)) and not self.is_position_city(pos):
            unit: Unit = self.get_unit_from_mapper(pos)
            self.pr(self.log_prefix + msg, 'Collision static in', pos, 'with', unit.id)
            return False
        elif self.has_movement_position(pos) and not self.is_position_city(pos):
            unit: Unit = self.get_unit_from_mapper(pos)
            self.pr(self.log_prefix + msg, 'Collision dynamic in', pos, 'with', unit.id)
            return False
        else:
            return MapAnalysis.is_position_valid(pos,game_state) and not self.is_position_enemy_city(pos)

    def is_position_city(self, pos: Position) -> bool:
        return MapAnalysis.get_city_id_from_pos(pos, self.player) != ''

    def is_position_enemy_city(self, pos: Position) -> bool:
        return MapAnalysis.get_city_id_from_pos(pos, self.opponent) != ''

    def stay(self,unit, reason):
        self.pr(self.log_prefix+unit.id, '- not moving:', reason)
        self.add_position(unit.pos, unit)

    def move_unit_to_pos(self, actions, info: UnitInfo, reason, pos: Position):
        direction = info.unit.pos.direction_to(pos)
        self.move_unit_to(actions, direction, info, reason, pos)

    def move_unit_to(self, actions, direction, info: UnitInfo, reason="", target_far_position=None):
        unit = info.unit
        next_state_pos = unit.pos.translate(direction, 1)
        # pr("Unit", unit.id, 'XXX -', unit.pos, next_state_pos, direction)
        if direction == DIRECTIONS.CENTER or next_state_pos.equals(unit.pos):
            # do not annotate
            self.pr(self.log_prefix, unit.id, '- not moving "', '', '" ', reason)
            self.add_position(unit.pos, unit)
        else:
            if target_far_position is not None:
                # target_far_position is only used for the annotation line
                actions.append(annotate.line(unit.pos.x, unit.pos.y, target_far_position.x, target_far_position.y))
                # actions.append(annotate.text(unit.pos.x, unit.pos.y, reason))

            actions.append(unit.move(direction))
            self.add_position(next_state_pos, unit)
            info.set_last_action_move(direction, next_state_pos)
            self.pr(self.log_prefix + unit.id, '- moving towards "', direction, next_state_pos, '" :', reason
               , str(target_far_position or ''))


    def try_to_move_to(self, actions, info: UnitInfo, pos: Position, msg: str) -> bool:
        direction = info.unit.pos.direction_to(pos)
        # if nobody is already moving there
        if not self.has_position(pos):
            self.move_unit_to(actions, direction, info, msg, pos)
            return True
        else:
            return False



