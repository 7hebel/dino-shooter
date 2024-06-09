import matplotlib.pyplot as plt
from perlin_noise import PerlinNoise

PERLIN_MIN = -0.6
PERLIN_MAX = 0.6


def normalize_noise(value: float) -> float:
    if value < PERLIN_MIN:
        value = PERLIN_MIN
    if value > PERLIN_MAX:
        value = PERLIN_MAX
        
    return round(value, 2)


def generate_perlin_map(height: int = 100, width: int = 100, seed: int = 10, octaves: int = 10) -> list[list[float]]:
    noise = PerlinNoise(octaves=octaves, seed=seed)
    perlin_map = [[normalize_noise(noise([i/width, j/height])) for j in range(width)] for i in range(height)]
    # plt.imshow(perlin_map, cmap='gray')
    # plt.show()
    return perlin_map

