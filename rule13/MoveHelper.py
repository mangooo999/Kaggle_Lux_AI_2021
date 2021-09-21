from lux.game_objects import Player, Unit
from lux.game_map import Position


class MoveHelper:
    def __init__(self):
        """
        initialize state
        """
        self.move_mapper = {}

    def add_position(self,pos : Position, unit : Unit):
        self.move_mapper[(unit.pos.x, unit.pos.y)] = unit

    def has_position(self,pos : Position):
        return self.move_mapper.get(pos.x, pos.y)


