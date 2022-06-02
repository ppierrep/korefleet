from kaggle_environments.envs.kore_fleets.helpers import Direction, Fleet, FleetId, Point, PlayerId, Board

from trajectory import Trajectory

class CustomFleet(Fleet):
    def __init__(
        self,
        # fleet_id: FleetId,
        # ship_count: int,
        # direction: Direction,
        # position: Point,
        # kore: int,
        # flight_plan: str,
        # player_id: PlayerId,
        # board: 'Board',

        # custom
        role: str,
        trajectory: Trajectory,
        *args,
        **kwargs

    ) -> None:
        super().__init__(*args, **kwargs)
        self.role = role
        self.trajectory = trajectory
    
    # from helper
    def less_than_other_allied_fleet(self, other):
        if not self.ship_count == other.ship_count:
            return self.ship_count < other.ship_count
        if not self.kore == other.kore:
            return self.kore < other.kore
        return self.direction.to_index() > other.direction.to_index()
    
    @staticmethod
    def convert(fleet: Fleet, role: str) -> 'CustomFleet':
        # TODO: better convert custom.__dict__.update(base.__dict__)
        trajectory = Trajectory(origin_cell=fleet.cell)
        return CustomFleet(
            role=role,
            trajectory=trajectory,
            fleet_id=fleet._id,
            ship_count=fleet._ship_count,
            direction=fleet._direction,
            position=fleet._position,
            flight_plan=fleet._flight_plan,
            kore=fleet._kore,
            player_id=fleet._player_id,
            board=fleet._board 
            )
        