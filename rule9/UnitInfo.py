
from lux.game_objects import Unit
import sys

class UnitInfo:
    def __init__(self, unit: Unit ):
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
        self.log_prefix = 'Unit_info '+self.id
        print(self.log_prefix,'created', file=sys.stderr)

    def update(self,unit: Unit):
        # update position
        self.previous_pos = self.current_pos
        self.current_pos = unit.pos

        #
        self.gathered_last_turn = unit.get_cargo_space_left() - self.last_free_cargo
        self.last_free_cargo = unit.get_cargo_space_left()

    def set_unit_role(self,role):
        self.role = role

    def clean_unit_role(self):
        self.role = ''

    def is_role_city_expander(self):
        return self.role=='expander'
