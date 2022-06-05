from kaggle_environments.envs.kore_fleets.helpers import Board, ShipyardAction

from map import Map, get_all_flight_plans_under_length
from trajectoryPlanner import TrajectoryPlanner, CollisionAndComeBackRoute
from utils import get_min_ship
import debugpy

debugpy.listen(5678)
print("Waiting for debugger attach")
debugpy.wait_for_client()

trajPlanner = None
_routes = ['N3W', 'S3W', 'E3N', 'S', 'N2W', 'S2E', 'N3W', 'S3W']
schedule_next_action = []

def agent(obs, config):
    global trajPlanner
    global schedule_next_action
    global _routes

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
        # print(fleet.position)
        if fleet_id not in trajPlanner.fleet_handled:
            trajPlanner.add_trajectory(turn=turn, fleet=fleet)
            trajPlanner.fleet_handled.add(fleet_id)
    
    decommisionned_ship = set(trajPlanner.fleet_handled) - set(board.fleets.keys())
    for ship_id in decommisionned_ship:
        trajPlanner.fleet_handled.remove(ship_id)

    if len(schedule_next_action):
        # Only works with one shipyard for the turn
        next_action = schedule_next_action[-1]
        shipyID = next_action['shipyardID']
        shipyAction = next_action['action']
        shipyard = [s for s in me.shipyards if s.id == shipyID]
        if len(shipyard):
            shipyard = shipyard[0]
            if next_action['delay'] == 0:
                shipyard.next_action = shipyAction
                schedule_next_action.pop()
            else:
                next_action['delay'] -= 1
                shipyard.next_action = ShipyardAction.spawn_ships(min(shipyard.max_spawn, int(spawn_cost % 10)))
    
    # loop through all shipyards you control
    for shipyard in me.shipyards:
        if shipyard.next_action is None:
            # paths = get_all_flight_plans_under_length(4)
            # trajectories = map.convert_flight_plan_to_trajectories(me.shipyards[0].cell, paths, turn)
            # for trajectory in trajectories:
            #     trajectory.evaluate()


            if shipyard.ship_count >= 21 and len(trajPlanner.fleet_handled) < 2:
                # start_route = sorted([traj for traj in trajectories if len(traj.flight_plan) <= 3], key=lambda x: x.kore_inclunding_drift, reverse=True)
                # action = ShipyardAction.launch_fleet_with_flight_plan(5, start_route[0].flight_plan)
                action = ShipyardAction.launch_fleet_with_flight_plan(5, _routes[-1])
                _routes.pop()
                shipyard.next_action = action

            # TODO: Check if only one ship get spawn per turn
            #   - can be troublesome with mutliple shipyard
            #   - can be troublesome with ennemy spawn

            # build a withdrawer
            elif len(trajPlanner.fleet_handled) == 2:
                routes = []
                for fleetID in list(trajPlanner.fleet_handled):
                    routes.extend(trajPlanner.get_drifter_interception_routes(turn=turn, drifter_id=fleetID, from_cell=me.shipyards[0].cell))  # TODO: check if target other withdrawer
                    
                # Sort by mission time
                routes = list(sorted([r for r in routes if len(r.round_trip_path)], key=lambda x: len(x.round_trip_path)))
                # if(len(routes) and len(routes[0].round_trip_path)):
                if(len(routes)):
                    number_of_fleet = max(get_min_ship(routes[0].round_trip_path), routes[0].minimum_ship_number) # max of either min required size for length or min required size to intercept
                    schedule_next_action.append({
                        'shipyardID': shipyard.id,
                        'action': ShipyardAction.launch_fleet_with_flight_plan(number_of_fleet, routes[0].round_trip_path),
                        'delay': routes[0].time_before_sending_ship
                    })

            # build a ship!
            elif kore_left >= spawn_cost:
                action = ShipyardAction.spawn_ships(1)
                shipyard.next_action = action
            else:
                pass

    return me.next_actions
