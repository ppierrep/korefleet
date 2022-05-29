
from map import Map, get_all_flight_plans_under_length, convert_flight_plan_to_trajectories
from kaggle_environments.envs.kore_fleets.helpers import Board, ShipyardAction
from time import sleep

def agent(obs, config):
    board = Board(obs, config)

    map = Map(board)

    me=board.current_player

    me = board.current_player
    turn = board.step
    spawn_cost = board.configuration.spawn_cost
    kore_left = me.kore

    paths = get_all_flight_plans_under_length(4)
    print(len(paths))
    trajectories = map.convert_flight_plan_to_trajectories(paths)
    # # loop through all shipyards you control
    # for shipyard in me.shipyards:
    #     # build a ship!
    #     if kore_left >= spawn_cost:
    #         action = ShipyardAction.spawn_ships(1)
    #         shipyard.next_action = action
 

    #         # for path in map.list_available_route(shipyard.cell, 2):
    #         #     path.evaluate()

    return me.next_actions
