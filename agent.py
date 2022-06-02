from fleet import CustomFleet
from map import Map, get_all_flight_plans_under_length
from kaggle_environments.envs.kore_fleets.helpers import Board, ShipyardAction
from time import sleep
from trajectoryPlanner import TrajectoryPlanner
from fleet import CustomFleet

trajPlanner = None

def agent(obs, config):
    global trajPlanner

    board = Board(obs, config)

    map = Map(board)

    me=board.current_player

    me = board.current_player
    turn = board.step
    spawn_cost = board.configuration.spawn_cost
    kore_left = me.kore

    if not trajPlanner:
        trajPlanner = TrajectoryPlanner(config.episodeSteps, board.cells.keys())

    for fleet_id, fleet in board.fleets.items():
        fleet = CustomFleet.convert(fleet, role='')
        if fleet_id not in trajPlanner.fleet_handled:
            trajPlanner.add_trajectory(turn=turn, fleet=fleet)
            trajPlanner.fleet_handled.add(fleet_id)

    # loop through all shipyards you control
    for shipyard in me.shipyards:
        paths = get_all_flight_plans_under_length(4)
        trajectories = map.convert_flight_plan_to_trajectories(me.shipyards[0].cell, paths, turn)
        for trajectory in trajectories:
            trajectory.evaluate()

        if shipyard.ship_count >= 5 and len(trajPlanner.fleet_handled) < 2:
            # start_route = sorted([traj for traj in trajectories if len(traj.flight_plan) <= 4], key=lambda x: x.kore_inclunding_drift, reverse=True)
            # action = ShipyardAction.launch_fleet_with_flight_plan(5, start_route[0].flight_plan)
            action = ShipyardAction.launch_fleet_with_flight_plan(5, '5E')
            shipyard.next_action = action

        # TODO: Check if only one ship get spawn per turn
        #   - can be troublesome with mutliple shipyard
        #   - can be troublesome with ennemy spawn

        # build a withdrawer
        # elif len(trajPlanner.fleet_handled) == 2:
        #     # TODO: get a ship that will fetch drifters 
        #     start_routes = trajPlanner.all_drifters_intercept_routes()
        #     interception_route = []
        #     action = ShipyardAction.launch_fleet_with_flight_plan(5, start_route[0].flight_plan)


        # build a ship!
        elif kore_left >= spawn_cost:
            action = ShipyardAction.spawn_ships(1)
            shipyard.next_action = action
        else:
            pass

    return me.next_actions
