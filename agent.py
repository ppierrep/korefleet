from kaggle_environments.envs.kore_fleets.helpers import Board, ShipyardAction

from map import Map, get_all_flight_plans_under_length
from trajectoryPlanner import TrajectoryPlanner, CollisionAndComeBackRoute
from utils import get_min_ship
# import debugpy

# debugpy.listen(5678)
# print("Waiting for debugger attach")
# debugpy.wait_for_client()

trajPlanner = None
schedule_next_action = []

def agent(obs, config):
    global trajPlanner
    global schedule_next_action

    board = Board(obs, config)

    map = Map(board)

    me=board.current_player

    me = board.current_player
    turn = board.step
    spawn_cost = board.configuration.spawn_cost
    kore_left = me.kore

    if not trajPlanner:
        trajPlanner = TrajectoryPlanner(config.episodeSteps, board.cells.keys(), board)

    for fleet_id, fleet in board.fleets.items():
        # print(fleet.position)
        if fleet_id not in trajPlanner.fleet_handled:
            trajPlanner.add_trajectory(turn=turn, fleet=fleet)
            trajPlanner.fleet_handled.add(fleet_id)
    
    trajPlanner.map = board # update map
    trajPlanner.update_kore(board, turn)
    
    decommisionned_ship = set(trajPlanner.fleet_handled) - set(board.fleets.keys())
    for ship_id in decommisionned_ship:
        trajPlanner.fleet_handled.remove(ship_id)

    # if len(schedule_next_action):
    #     # Only works with one shipyard for the turn
    #     next_action = schedule_next_action[-1]
    #     shipyID = next_action['shipyardID']
    #     shipyAction = next_action['action']
    #     shipyard = [s for s in me.shipyards if s.id == shipyID]
    #     if len(shipyard):
    #         shipyard = shipyard[0]
    #         if next_action['delay'] == 0:
    #             shipyard.next_action = shipyAction
    #             schedule_next_action.pop()
    #         else:
    #             next_action['delay'] -= 1
    #             shipyard.next_action = ShipyardAction.spawn_ships(min(shipyard.max_spawn, int(kore_left % 10)))
    
    # loop through all shipyards you control
    for shipyard in me.shipyards:
        if shipyard.next_action is None:

            if shipyard.ship_count >= 21 and len(trajPlanner.fleet_handled) < 5:
                routes = get_all_flight_plans_under_length(7)
                travel_simulations = trajPlanner.get_simulations(origin_cell=shipyard.cell, turn=turn, routes=routes, board=board)
                selected_route = list(sorted([el for el in travel_simulations if not el.intercepted], key=lambda x: x.mined_kore_per_step, reverse=True))[0]
                # print({'fp': selected_route.flight_plan, 'ks': selected_route.mined_kore_per_step, 'turn': selected_route.turn})
                action = ShipyardAction.launch_fleet_with_flight_plan(selected_route.min_fleet, selected_route.flight_plan)
                shipyard.next_action = action

            # Always try to make ships (multiple of 3 (3 ships): N2S, 5 (8 ships): N3EWS), 21 (N3W6E6S)
            # ------------------------------------------
            # Compute better reward for each combinaison (with % mined and regeneration taken into account)(deactivate withdrawer)
            # 
            # Add Multiple shipyard handling:
            #   - In between high value stars
            #   - Start at one finish at one
            #   - Transfer ships to keep ships count averaged
            #
            # Create a miner baseline rule based IA
            #
            # Use logic of withdrawer to compute routes to attack this IA.
            #
            #


            # TODO: Check if only one ship get spawn per turn
            #   - can be troublesome with mutliple shipyard
            #   - can be troublesome with ennemy spawn

            # build a withdrawer
            # elif len(trajPlanner.fleet_handled) == 2:
            #     routes = []
            #     for fleetID in list(trajPlanner.fleet_handled):
            #         routes.extend(trajPlanner.get_drifter_interception_routes(turn=turn, drifter_id=fleetID, from_cell=me.shipyards[0].cell))  # TODO: check if target other withdrawer
                    
            #     # Sort by mission time
            #     # TODO: Avoid being intercepted
            #     routes = list(sorted([r for r in routes if len(r.round_trip_path)], key=lambda x: len(x.round_trip_path)))
            #     if(len(routes)):
            #         number_of_fleet = max(get_min_ship(routes[0].round_trip_path), routes[0].minimum_ship_number) # max of either min required size for length or min required size to intercept
            #         schedule_next_action.append({
            #             'shipyardID': shipyard.id,
            #             'action': ShipyardAction.launch_fleet_with_flight_plan(number_of_fleet, routes[0].round_trip_path),
            #             'delay': routes[0].time_before_sending_ship
            #         })

            # build a ship!
            elif kore_left >= spawn_cost:
                shipyard.next_action = ShipyardAction.spawn_ships(min(shipyard.max_spawn, int(kore_left / 10)))
            else:
                pass

    return me.next_actions
