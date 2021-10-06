import sys

from lux.game_constants import GAME_CONSTANTS


class GameStateInfo:
    def __init__(self, turn: int):
        MAX_DAYS = GAME_CONSTANTS['PARAMETERS']['MAX_DAYS']
        DAY_LENGTH = GAME_CONSTANTS['PARAMETERS']['DAY_LENGTH']
        NIGHT_LENGTH = GAME_CONSTANTS['PARAMETERS']['NIGHT_LENGTH']
        FULL_LENTH = DAY_LENGTH + NIGHT_LENGTH

        self.all_night_turns_lef = ((MAX_DAYS - 1 - turn) // FULL_LENTH + 1) * NIGHT_LENGTH

        self.turns_to_night = (DAY_LENGTH - turn) % FULL_LENTH
        self.turns_to_night = 0 if self.turns_to_night > 30 else self.turns_to_night

        self.turns_to_dawn = FULL_LENTH - turn % FULL_LENTH
        self.turns_to_dawn = 0 if self.turns_to_dawn > 10 else self.turns_to_dawn

        if self.is_night_time():
            self.all_night_turns_lef -= (10 - self.turns_to_dawn)

        # below is probably duplicate
        self.steps_until_night = 30 - turn % 40

        print("T_" + str(turn), self.__str__(), file=sys.stderr)

    def is_dawn(self) -> bool:
        return self.turns_to_night == 30

    def is_day_time(self) -> bool:
        return self.turns_to_dawn == 0

    def is_night_time(self) -> bool:
        return self.turns_to_night == 0

    def is_night_tomorrow(self) -> bool:
        return -8 <= self.steps_until_night <= 1

    def __str__(self):
        return ','.join("%s: %s" % item for item in vars(self).items())
