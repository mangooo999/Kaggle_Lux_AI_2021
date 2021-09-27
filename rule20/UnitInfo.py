from lux.game_map import Position
from lux.game_objects import Unit
import sys


class UnitInfo:
    def __init__(self, unit: Unit):
        """
        initialize state
        """
        self.id = unit.id
        self.unit = unit
        self.last_action = ''
        self.last_move = ''
        self.last_move_direction = ''
        self.last_move_turn = 0
        self.current_turn = 0
        self.has_mission = False
        self.previous_pos = None
        self.gathered_last_turn = 0
        self.last_free_cargo = unit.get_cargo_space_left()
        self.current_pos = unit.pos
        self.role = ''
        self.log_prefix = 'Unit_info ' + self.id
        self.target_position = None
        self.role_time_turn_limit = 0
        self.has_done_action_this_turn = False
        self.last_move_before_pos = unit.pos
        print(self.log_prefix, 'created', file=sys.stderr)

    def update(self, unit: Unit, current_turn):
        self.unit = unit
        # update position
        self.previous_pos = self.current_pos
        self.current_pos = unit.pos
        self.has_done_action_this_turn = False
        self.current_turn = current_turn
        #
        self.gathered_last_turn = unit.get_cargo_space_left() - self.last_free_cargo
        self.last_free_cargo = unit.get_cargo_space_left()
        if self.role_time_turn_limit > 0:
            self.role_time_turn_limit -= 1
            if self.role_time_turn_limit == 0:
                self.clean_unit_role()

        if self.is_role_returner() and self.unit.get_cargo_space_left() == 100:
            self.clean_unit_role()

    def set_last_action_move(self, direction):
        self.last_move = 'm'
        self.last_move_direction = direction
        self.last_move_turn = self.current_turn
        self.last_move_before_pos = self.unit.pos
        self.has_done_action_this_turn = True

    def set_last_action_build(self):
        self.last_move = 'b'
        self.has_done_action_this_turn = True

    def set_last_action_transfer(self):
        self.last_move = 't'
        self.has_done_action_this_turn = True

    def set_unit_role_traveler(self, pos: Position, number_turns, prefix=''):
        print(self.log_prefix, 'set this unit as traveler to', pos, " for number_turns", number_turns, file=sys.stderr)
        self.set_unit_role('traveler', prefix)
        self.target_position = pos
        self.role_time_turn_limit = number_turns

    def set_unit_role_returner(self, pos: Position, prefix: str = ''):
        if pos is not None:
            print(self.log_prefix, 'set this unit as returner to', pos, file=sys.stderr)
            self.set_unit_role('returner', prefix)
            self.target_position = pos

    def set_unit_role(self, role, prefix: str = ''):
        self.role = role
        print(prefix, "Setting unit", self.id, " as ", self.role, file=sys.stderr)

    def clean_unit_role(self):
        if self.role != '':
            print(self.log_prefix, 'removing role', self.role, file=sys.stderr)
        self.role = ''
        self.target_position = None
        self.role_time_turn_limit = 0

    def is_role_city_expander(self):
        return self.role == 'expander'

    def is_role_city_explorer(self):
        return self.role == 'explorer'

    def is_role_hassler(self):
        return self.role == 'hassler'

    def is_role_traveler(self):
        return self.role == 'traveler'

    def is_role_returner(self):
        return self.role == 'returner'
