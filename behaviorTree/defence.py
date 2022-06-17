from py_trees import behaviour, common
from kaggle_environments.envs.kore_fleets.helpers import Board, ShipyardAction, Point



class EnoughToDefend(behaviour.Behaviour):
    def __init__(self, name):
        super().__init__(name)
        self.blackboard = self.attach_blackboard_client("Board")
        self.blackboard.register_key(key="shipyard", access=common.Access.READ)
        self.blackboard.register_key(key="me", access=common.Access.READ)
        self.blackboard.register_key(key="incoming_fleet_infos", access=common.Access.READ)

        self.blackboard.register_key(key="not_needed_fleet", access=common.Access.WRITE)
        self.blackboard.register_key(key="need_to_build", access=common.Access.WRITE)

    def update(self):
        self.logger.debug("  %s [Foo::update()]" % self.name)
        inc_fleet_infos = self.blackboard.incoming_fleet_infos
        shipyard = self.blackboard.shipyard

        # TODO: Theorically, we have to take into account: ship refueling and max spawn increasing
        max_available_fleet = inc_fleet_infos['residing_fleet_number'] + inc_fleet_infos["eta"] * min(shipyard.max_spawn, int(self.blackboard.me.kore % 10))

        if max_available_fleet < inc_fleet_infos['incomming_fleet_number']:
            return common.Status.FAILURE
        else:
            self.blackboard.need_to_build = inc_fleet_infos['residing_fleet_number'] < inc_fleet_infos['incomming_fleet_number']
            self.blackboard.not_needed_fleet = max_available_fleet - inc_fleet_infos['incomming_fleet_number']
            return common.Status.SUCCESS
