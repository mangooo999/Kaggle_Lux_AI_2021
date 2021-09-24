import sys
from lux.game_objects import Player, Unit
from lux.game_map import Position


class MoveHelper:
    def __init__(self, player, opponent):
        """
        initialize state
        """
        self.move_mapper = {}
        self.player = player
        self.opponent = opponent

    def add_position(self, pos: Position, unit: Unit):
        self.move_mapper[self.__hash_pos__(pos)] = unit

    def has_position(self, pos: Position) -> bool:
        if self.__hash_pos__(pos) in self.move_mapper:
            return True
        else:
            return False

    def __hash_pos__(self, pos: Position):
        return (pos.x, pos.y)

    def can_move_to(self, pos) -> bool:
        # we cannot move if somebody is already going, and it is not a city
        if self.has_position(pos) and not self.is_position_city(pos):
            unit: Unit = self.move_mapper.get(self.__hash_pos__(pos))
            print('Collision in', pos, 'with', unit.id, file=sys.stderr)
            return False
        else:
            return not self.is_position_enemy_city(pos)

    def cannot_move_to(self, pos) -> bool:
        return not self.can_move_to(pos)

    def is_position_city(self, pos) -> bool:
        return self.get_city_id_from_pos(pos, self.player) != ''

    def is_position_enemy_city(self, pos) -> bool:
        return self.get_city_id_from_pos(pos, self.opponent) != ''

    def get_city_id_from_pos(self, pos, actor):
        for city in actor.cities.values():
            for city_tile in city.citytiles:
                if city_tile.pos.equals(pos):
                    return city.cityid

        return ''
