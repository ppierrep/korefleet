from py_trees import behaviour, common
from kaggle_environments.envs.kore_fleets.helpers import Board, ShipyardAction, Point
from trajectoryPlanner import compute_flight_plan


class RaidShipyard(behaviour.Behaviour):
    def __init__(self, name):
        super().__init__(name)
        self.blackboard = self.attach_blackboard_client("Board")
        self.blackboard.register_key(key="shipyard", access=common.Access.READ)
        self.blackboard.register_key(key="board", access=common.Access.READ)

        self.blackboard.register_key(key="raid_candidates", access=common.Access.READ)
        self.blackboard.register_key(key="action", access=common.Access.WRITE)

    def update(self):
        self.logger.debug("  %s [Foo::update()]" % self.name)
        candidates = self.blackboard.raid_candidates
        
        pos, _, count = sorted(candidates, key=lambda x: x[1], reverse=False)[0]  # sort by dist

        fplan = compute_flight_plan(self.blackboard.shipyard.position, pos, round_trip=False, compress_last=True)
        if len(fplan) > 0:
            action = ShipyardAction.launch_fleet_with_flight_plan(count + 25, fplan)

            self.blackboard.shipyard.next_action = action
            self.blackboard.action = action
            return common.Status.SUCCESS
        
        return common.Status.FAILURE

        


