from dis import dis
from kaggle_environments.envs.kore_fleets.helpers import Board, ShipyardAction, Point

from map import get_map_shipyard_position_candidates, get_all_flight_plans_under_length, get_map_kore_convolutions
from trajectoryPlanner import TrajectoryPlanner, CollisionAndComeBackRoute, compute_flight_plan
from utils import get_min_ship
from planner import Planner


# import debugpy

# debugpy.listen(5678)
# print("Waiting for debugger attach")
# debugpy.wait_for_client()

def get_shipyard_scaling(num_ships):
    if num_ships < 100:
        return 1
    if num_ships < 200:
        return 3
    elif num_ships < 300:
        return 5
    elif num_ships < 500:
        return 7
    elif num_ships < 1000:
        return 10
    else:
        return 12

planner = None

def baseline(obs, config):
    global planner

    board = Board(obs, config)
    me = board.current_player
    turn = board.step
    spawn_cost = board.configuration.spawn_cost
    kore_left = me.kore

    if not planner:
        planner = Planner(board, turn)
    
    planner.turn = turn
    planner.compute_snapshots(board=board)

    # loop through all shipyards you control
    for shipyard in me.shipyards:
        if shipyard.next_action is None:

            # Always try to make ships (multiple of 3 (3 ships): N2S, 5 (8 ships): N3EWS), 21 (N3W6E6S)
            # Compute better reward for each combinaison (with % mined and regeneration taken into account)(deactivate withdrawer)
            # 
            # Add Multiple shipyard handling:
            #   - In between high value stars
            #   - Start at one finish at one
            #   - Transfer ships to keep ships count averaged
            #
            # Create a miner baseline rule based IA
            #
            # ------------------------------------------
            # Use logic of withdrawer to compute routes to attack this IA.
            #
            if len(me.shipyard_ids) < get_shipyard_scaling(sum([f.ship_count for f in  me.fleets])) and shipyard.ship_count >= 75: # TODO: Get smarter unified metrics to scale shipyard production
                min_dist = 4 # min and max dist from which we can place shipyard
                max_dist = 7
                shipyard_point_candidates = get_map_shipyard_position_candidates(board, distA=min_dist, distB=max_dist)
                convolutions = get_map_kore_convolutions(board, 7)
                candidates = [(pos, convolutions[(pos.x, pos.y)]) for pos in shipyard_point_candidates]
                best_position = list(sorted(candidates, key=lambda x: x[1], reverse=True))
                if len(best_position):
                    best_position = best_position[0]

                    route = compute_flight_plan(shipyard.cell.position, Point(best_position[0][0], best_position[0][1]), compress_last=False)
                    route += 'C'
                    action = ShipyardAction.launch_fleet_with_flight_plan(75, route)
                    shipyard.next_action = action

            elif shipyard.ship_count >= 21:
                routes = get_all_flight_plans_under_length(7)
                travel_simulations = planner.get_simulations(origin_cell=shipyard.cell, turn=turn, routes=routes)

                high_kore_routes = list(sorted([el for el in travel_simulations if not el.intercepted], key=lambda x: x.mined_kore_per_step, reverse=True))[0:35]  # get higly rewarded routes
                closest_routes = list(sorted([el for el in high_kore_routes], key=lambda x: x.max_dist, reverse=False))[0:10]  # get closest routes
                low_wasted_routes = list(sorted([el for el in closest_routes], key=lambda x: x.empty_cells_ratio, reverse=False))[0:5]  # get routes with lower empty cells count
                selected_route = list(sorted([el for el in low_wasted_routes], key=lambda x: x.same_trajectory_count, reverse=False))  # get routes with which are not used by other fleets

                if len(selected_route):
                    selected_route = selected_route[0]
                    # print({'fp': low_wasted_routes[0].flight_plan, 'waste': low_wasted_routes[0].empty_cells_ratio, 'turn': low_wasted_routes[0].turn})
                    action = ShipyardAction.launch_fleet_with_flight_plan(selected_route.min_fleet, selected_route.flight_plan)
                    shipyard.next_action = action
                else:
                    shipyard.next_action = ShipyardAction.spawn_ships(min(shipyard.max_spawn, int(kore_left / 10)))

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

