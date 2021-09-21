import sys
from lux.game_objects import Player, Unit
from lux.game_map import Position


class MoveHelper:
    def __init__(self):
        """
        initialize state
        """
        self.move_mapper = {}

    def add_position(self,pos: Position, unit: Unit):
        self.move_mapper[self.__hash_pos__(pos)] = unit

    def has_position(self,pos: Position):
        if self.__hash_pos__(pos) in self.move_mapper:
            unit: Unit = self.move_mapper.get(self.__hash_pos__(pos))
            print('Collision in', pos,'with',unit.id,file=sys.stderr)
            return True
        else:
            return False

    def __hash_pos__(self,pos: Position):
        return (pos.x,pos.y)
