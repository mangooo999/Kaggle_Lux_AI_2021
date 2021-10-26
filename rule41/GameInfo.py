from lux.game_objects import Player
from lux.game import Game

import sys
import itertools


class ResearchStats:
    def __init__(self):
        """
        initialize state
        """
        self.points = 0
        self.increase_points_last_turn = 0
        self.increase_points_sequence = []

    def update(self, actor: Player):
        self.increase_points_last_turn = actor.research_points - self.points
        self.points = actor.research_points
        self.increase_points_sequence.insert(0, self.increase_points_last_turn)

    def get_increase_last_n_turns(self, n: int) -> int:
        sum_research = 0
        for r in itertools.islice(self.increase_points_sequence, n):
            sum_research += r
        return sum_research

    def get_research_rate(self, n: int) -> float:
        return float(self.get_increase_last_n_turns(n)) / float(n)


class GameInfo:
    def __init__(self, pr):
        """
        initialize state
        """
        self.log_prefix = 'GameInfo'
        self.turn = 0
        self.research = ResearchStats()
        self.opponent_research = ResearchStats()
        self.research_this_turn = 0
        self.at_start_resources_within3 = 0
        self.pr = pr

    def update(self, player: Player, opponent: Player, game_state: Game):
        self.research.update(player)
        self.opponent_research.update(opponent)
        self.turn = game_state.turn
        self.log_research_stats(5)
        self.log_prefix = 'GameInfo#' + self.turn.__str__()
        self.research_this_turn = 0

    def get_research_increase_last_n_turns(self, n: int) -> int:
        return self.research.get_increase_last_n_turns(n)

    def get_opponent_research_increase_last_n_turns(self, n: int) -> int:
        return self.opponent_research.get_increase_last_n_turns(n)

    def do_research(self, actions, city_tile, msg):
        actions.append(city_tile.research())
        self.pr(msg)
        self.research_this_turn += 1

    def get_research_rate(self, n: int) -> float:
        return self.research.get_research_rate(n)

    def get_opponent_research_rate(self, n: int) -> float:
        return self.opponent_research.get_research_rate(n)

    def log_research_stats(self, n: int):
        self.pr(self.log_prefix, 'research_points', self.research.points, ' research_rate',
                self.get_research_rate(n),
                'opp_research_points', self.opponent_research.points, ' opp_research_rate',
                self.get_opponent_research_rate(n)
                )

    def get_total_reseach(self):
        return self.research.points + self.research_this_turn

    def still_can_do_reseach(self):
        return self.get_total_reseach() < 200
