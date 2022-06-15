class Event():
    def __init__(
            self, 
            actors, 
            actors_shipcount,
            event_type, 
            turn,
            position,
            kore_balance=0, 
            deposited_kore=0, 
            damage_balance=0, 
            shipyard_balance=0, 
            fleet_balance=0
        ) -> None:

        self.actors = actors
        self.actors_shipcount = actors_shipcount
        self.event_type = event_type
        self.turn = turn + 1
        self.position = position
        
        self.kore_balance = kore_balance
        self.deposited_kore = deposited_kore
        self.damage_balance = damage_balance

        self.shipyard_balance = shipyard_balance
        self.fleet_balance = fleet_balance