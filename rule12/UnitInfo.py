from lux.game_map import Position
from lux.game_objects import Unit
import sys


class UnitInfo:
    def __init__(self, unit: Unit):
        """
        initialize state
        """
        self.id = unit.id
        self.last_action = ''
        self.last_move = ''
        self.has_mission = False
        self.previous_pos = None
        self.gathered_last_turn = 0
        self.last_free_cargo = unit.get_cargo_space_left()
        self.current_pos = unit.pos
        self.role = ''
        self.log_prefix = 'Unit_info ' + self.id
        self.target_position = None
        self.role_time_turn_limit = 0
        print(self.log_prefix, 'created', file=sys.stderr)

    def update(self, unit: Unit):
        # update position
        self.previous_pos = self.current_pos
        self.current_pos = unit.pos

        #
        self.gathered_last_turn = unit.get_cargo_space_left() - self.last_free_cargo
        self.last_free_cargo = unit.get_cargo_space_left()
        if self.role_time_turn_limit > 0:
            self.role_time_turn_limit -=1
            if self.role_time_turn_limit == 0:
                self.clean_unit_role()

    def set_unit_role_traveller(self, pos:Position,number_turns):
        print(self.log_prefix, 'set this unit as traveller to',pos," for number_turns",number_turns,file=sys.stderr)
        self.set_unit_role('traveller')
        self.target_position=pos
        self.role_time_turn_limit = number_turns

    def set_unit_role(self, role):
        self.role = role

    def clean_unit_role(self):
        if self.role != '':
            print(self.log_prefix, 'removing role',self.role,file=sys.stderr)
        self.role = ''
        self.target_position = None
        self.role_time_turn_limit = 0

    def is_role_city_expander(self):
        return self.role == 'expander'

    def is_role_hassler(self):
        return self.role == 'hassler'

    def is_role_traveller(self):
        return self.role == 'traveller'
