import math


def get_max_flight_plan(ship_number):
    return math.floor(2 * math.log(ship_number)) + 1

def get_min_ship(flight_plan: str) -> int:
    size = len(flight_plan)
    return math.ceil(math.exp((size - 1) / 2))
