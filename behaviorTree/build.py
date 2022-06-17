from py_trees import behaviour, common
from kaggle_environments.envs.kore_fleets.helpers import Board, ShipyardAction, Point

from map import get_map_shipyard_position_candidates, get_map_kore_convolutions
from trajectoryPlanner import TrajectoryPlanner, CollisionAndComeBackRoute, compute_flight_plan


class BuildFleet(behaviour.Behaviour):
    def __init__(self, name):
        super().__init__(name)
        self.blackboard = self.attach_blackboard_client("Board")
        self.blackboard.register_key(key="shipyard", access=common.Access.READ)
        self.blackboard.register_key(key="me", access=common.Access.READ)
        self.blackboard.register_key(key="action", access=common.Access.WRITE)

    def update(self):
        self.logger.debug("  %s [Foo::update()]" % self.name)
        action = ShipyardAction.spawn_ships(min(self.blackboard.shipyard.max_spawn, int(self.blackboard.me.kore / 10)))
        self.blackboard.action = action
        return common.Status.SUCCESS

class NeedToBuild(behaviour.Behaviour):
    def __init__(self, name):
        super().__init__(name)
        self.blackboard = self.attach_blackboard_client("Board")
        self.blackboard.register_key(key="need_to_build", access=common.Access.READ)

    def update(self):
        return common.Status.SUCCESS if self.blackboard.need_to_build else common.Status.FAILURE


class BuildShipyard(behaviour.Behaviour):
    def __init__(self, name):
        super().__init__(name)
        self.blackboard = self.attach_blackboard_client("Board")
        self.blackboard.register_key(key="board", access=common.Access.READ)
        self.blackboard.register_key(key="shipyard", access=common.Access.READ)
        self.blackboard.register_key(key="action", access=common.Access.WRITE)

    def update(self):
        self.logger.debug("  %s [Foo::update()]" % self.name)
        min_dist = 4 # min and max dist from which we can place shipyard
        max_dist = 7
        shipyard_point_candidates = get_map_shipyard_position_candidates(self.blackboard.board, distA=min_dist, distB=max_dist)
        convolutions = get_map_kore_convolutions(self.blackboard.board, 7)
        candidates = [(pos, convolutions[(pos.x, pos.y)]) for pos in shipyard_point_candidates]
        best_position = list(sorted(candidates, key=lambda x: x[1], reverse=True))
        if len(best_position):
            best_position = best_position[0]

            route = compute_flight_plan(self.blackboard.shipyard.cell.position, Point(best_position[0][0], best_position[0][1]), compress_last=False)
            route += 'C'
            action = ShipyardAction.launch_fleet_with_flight_plan(75, route)
            self.blackboard.shipyard.next_action = action
            self.blackboard.action = action
            return common.Status.SUCCESS
        return common.Status.FAILURE
