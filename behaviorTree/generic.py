from py_trees import behaviour, common
from kaggle_environments.envs.kore_fleets.helpers import Board, ShipyardAction, Point


# TODO generation per turn to define when building shipyard


class EnoughFleet(behaviour.Behaviour):
    def __init__(self, name, number):
        super().__init__(name)
        self.number = number
        self.blackboard = self.attach_blackboard_client("Board")
        self.blackboard.register_key(key="shipyard", access=common.Access.READ)
    
    def update(self):
        self.logger.debug("  %s [Foo::update()]" % self.name)
        return common.Status.SUCCESS if self.blackboard.shipyard.ship_count >= self.number else common.Status.FAILURE


class EnoughKore(behaviour.Behaviour):
    def __init__(self, name, number):
        super().__init__(name)
        self.number = number
        self.blackboard = self.attach_blackboard_client("Board")
        self.blackboard.register_key(key="me", access=common.Access.READ)
    
    def update(self):
        self.logger.debug("  %s [Foo::update()]" % self.name)
        return common.Status.SUCCESS if self.blackboard.me.kore >= self.number else common.Status.FAILURE
