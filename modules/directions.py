class CombinedRange:
    def __init__(self, *ranges) -> None:
        self.ranges = ranges

    def __contains__(self, value: int) -> bool:
        for r in self.ranges:
            if value in r:
                return True
        return False


class AngleDirection:
    N  = 0
    NE = 45
    E  = 90
    SE = 135
    S  = 180
    SW = 225
    W  = 270
    NW = 315
    
    
NORTHISH = {AngleDirection.N, AngleDirection.NE, AngleDirection.NW}
SOUTHISH = {AngleDirection.S, AngleDirection.SE, AngleDirection.SW}
EASTISH = {AngleDirection.E, AngleDirection.NE, AngleDirection.SE}
WESTISH = {AngleDirection.W, AngleDirection.NW, AngleDirection.SW}
    

def calc_direction_angle_range(mid_angle: int) -> range:
    angle_deviation = 45/2       
    min = mid_angle - angle_deviation
    max = mid_angle + angle_deviation
    
    if min < 0:
        min = 360 + min
    
    if max > 360:
        max = max - 360

    if min > max:
        r1 = range(int(min), 360)
        r2 = range(0, int(max))
        return CombinedRange(r1, r2)
        
    return range(int(min), int(max))


def get_angle_direction(angle: int) -> AngleDirection:
    for dir_name in dir(AngleDirection):
        if not dir_name.startswith("__"):
            dir_value = getattr(AngleDirection, dir_name)
            dir_range = calc_direction_angle_range(dir_value)

            if angle in dir_range:
                return dir_value

    print(f"Error: unknown angle direction for: {angle}")
    return AngleDirection.S


def get_angle_arrow_char(angle: int) -> str:
    return {
        AngleDirection.N: "↑",
        AngleDirection.NE: "↗",
        AngleDirection.NW: "↖",
        AngleDirection.S: "↓",
        AngleDirection.SE: "↘",
        AngleDirection.SW: "↙",
        AngleDirection.E: "→",
        AngleDirection.W: "←",
    }.get(angle, "?")
    