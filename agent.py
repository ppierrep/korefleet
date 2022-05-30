
from map import Map, get_all_flight_plans_under_length
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

    # loop through all shipyards you control
    for shipyard in me.shipyards:
        paths = get_all_flight_plans_under_length(3)
        trajectories = map.convert_flight_plan_to_trajectories(me.shipyards[0].cell, paths)
        for trajectory in trajectories:
            trajectory.evaluate()

        if shipyard.ship_count >= 5:
            start_route = sorted([traj for traj in trajectories if (traj.leads_to_shipyard and len(traj.flight_plan) <= 4)], key=lambda x: x.kore_inclunding_drift, reverse=True)
            action = ShipyardAction.launch_fleet_with_flight_plan(5, start_route[0].flight_plan)
            shipyard.next_action = action

        # build a ship!
        elif kore_left >= spawn_cost:
            action = ShipyardAction.spawn_ships(1)
            shipyard.next_action = action
        else:
            pass

    return me.next_actions
