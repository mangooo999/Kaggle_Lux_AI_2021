from astar3 import *


def turns_it_will_live(autonomy, steps_until_night,_next_night_number_turn=-1) ->int:
    autonomy=max(0,autonomy)
    if _next_night_number_turn == -1:
        next_night_number_turn = min(10, 10 + steps_until_night)
    else:
        next_night_number_turn = _next_night_number_turn

    turn_to_night= max(0,steps_until_night)
    print('turn_to_night',turn_to_night, 'next_night_number_turn',next_night_number_turn, 'aut',autonomy)
    if autonomy>=next_night_number_turn:
       return turns_it_will_live(autonomy-next_night_number_turn,turn_to_night+40,10)
    else:
       return autonomy + turn_to_night


# data from main article
DIAGRAM1_WALLS = [from_id_width(id, width=30) for id in [21,22,51,52,81,82,93,94,111,112,123,124,133,134,141,142,153,154,163,164,171,172,173,174,175,183,184,193,194,201,202,203,204,205,213,214,223,224,243,244,253,254,273,274,283,284,303,304,313,314,333,334,343,344,373,374,403,404,433,434]]

g = GridWithWeights(30, 15)
g.walls = DIAGRAM1_WALLS
start, goal = (0, 7), (27, 2)
came_from, cost_so_far = a_star_search(g, start, goal)
draw_grid(g, point_to=came_from, path=reconstruct_path(came_from, start, goal), start=start, goal=goal)

turn = 7

steps_until_night = 30 - turn % 40
next_night_number_turn = min(10, 10 + steps_until_night)


autonomy = 24
# turn_to_night = 11
res = turns_it_will_live(autonomy,steps_until_night)

print("xxxxx", 'autonomy=',autonomy,';turn_to_night=',steps_until_night,' res=',res)