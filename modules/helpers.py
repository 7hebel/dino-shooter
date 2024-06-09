
 
def interpolation(d, x):
    return d[0][1] + (x - d[0][0]) * ((d[1][1] - d[0][1])/(d[1][0] - d[0][0])) 

class FloatRange:
    def __init__(self, min: float, max: float) -> None:
        self.min = min
        self.max = max
        
        if self.min > self.max:
            self.min, self.max = self.max, self.min
        
    def __contains__(self, value: float) -> bool:
        return value >= self.min and value < self.max

