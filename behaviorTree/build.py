from py_trees import behaviour, common
from kaggle_environments.envs.kore_fleets.helpers import Board, ShipyardAction, Point


class BuildFleet(behaviour.Behaviour):
    def __init__(self, name):
        super().__init__(name)
        self.blackboard = self.attach_blackboard_client("Board")
        self.blackboard.register_key(key="shipyard", access=common.Access.READ)
        self.blackboard.register_key(key="me", access=common.Access.READ)
        self.blackboard.register_key(key="action", access=common.Access.WRITE)

    def setup(self):
        self.logger.debug("  %s [Foo::setup()]" % self.name)

    def initialise(self):
        self.logger.debug("  %s [Foo::initialise()]" % self.name)

    def update(self):
        self.logger.debug("  %s [Foo::update()]" % self.name)
        action = ShipyardAction.spawn_ships(min(self.blackboard.shipyard.max_spawn, int(self.blackboard.me.kore / 10)))
        self.blackboard.action = action
        return common.Status.SUCCESS

    def terminate(self, new_status):
        self.logger.debug("  %s [Foo::terminate().terminate()][%s->%s]" % (self.name, self.status, new_status))
