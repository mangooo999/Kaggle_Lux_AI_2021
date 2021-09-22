#!/usr/bin/python3
import mortoray_path_finding as mpf
from lux.game_map import Position


class MyFinder(mpf.draw.Finder):
	"""Integrate into the simple UI	"""
	def __init__(self):
		self.reset()
	
	def step(self, frames):
		self.max_distance = max( 0, self.max_distance + frames )
		self.result = mpf.finder.fill_shortest_path(self.game.board, self.game.start, self.game.end, max_distance = self.max_distance)
		self.set_board(self.result[0])
		self.set_path(mpf.finder.backtrack_to_start(self.result[0], self.game.end))
	
	def reset(self):
		self.game = mpf.random_creator.create_wall_maze(20,10)
		#self.game = mpf.random_creator.create_wall_maze(20,10,Position(7, 6),Position(13,4))
		print('start',self.game.start)
		print('end  ',self.game.end)
		self.max_distance = 18
		self.step(0)
	

header_text = """Keys:
	Left - Lower maximum distance
	Right - Increase maximum distance
	R - create a new maze
	Esc - Exit"""
print( header_text )

finder = MyFinder()
finder.run()
