
from map import Map
from kaggle_environments.envs.kore_fleets.helpers import Board, ShipyardAction

def agent(obs, config):
    board = Board(obs, config)

    map = Map(board)

    me=board.current_player

    me = board.current_player
    turn = board.step
    spawn_cost = board.configuration.spawn_cost
    kore_left = me.kore

    # loop through all shipyards you control
    for shipyard in me.shipyards:
        # build a ship!
        if kore_left >= spawn_cost:
            action = ShipyardAction.spawn_ships(1)
            shipyard.next_action = action
 

            print(len(map.list_available_route(shipyard.cell, 4)))


    return me.next_actions