from modules import helpers

import random
import pygame

default_grass = pygame.image.load("./textures/grass/grass2.png")
grass_images = [
    pygame.image.load("./textures/grass/grass1.png"),
    pygame.image.load("./textures/grass/grass3.png"),
    pygame.image.load("./textures/grass/grass4.png"),
    pygame.image.load("./textures/grass/grass5.png"),
    pygame.image.load("./textures/grass/grass6.png"),
    pygame.image.load("./textures/grass/grass7.png"),
    pygame.image.load("./textures/grass/grass8.png"),
    pygame.image.load("./textures/grass/grass9.png"),
]
grass_images.extend(([default_grass] * 20))

sand_textures = [
    pygame.image.load("./textures/sand/sand1.png"),
    pygame.image.load("./textures/sand/sand2.png"),
    pygame.image.load("./textures/sand/sand3.png"),
    pygame.image.load("./textures/sand/sand4.png"),
]


class GroundVoxel:
    def __init__(self, name: str, on_stand_slowness: float = 0, all_textures: list = None, no_corner: bool = False):
        self.name = name
        self.voxel_slowness = on_stand_slowness
        self.basic_texture = None
        self.corner_texture = None
        if not no_corner:
            self.corner_texture = pygame.image.load(f"./textures/corners/corner_{name}.png")
        
        self.has_random_textures = all_textures is not None
        self.all_random_textures = all_textures
        self._txt_cache = {}
        
        if not self.has_random_textures:
            self.basic_texture = pygame.image.load(f"./textures/{name}.png")
        
        
    def get_texture(self, x: int, y: int) -> pygame.Surface:
        if not self.has_random_textures:
            return self.basic_texture

        cache_key = f"{x}.{y}"
        if cache_key in self._txt_cache:
            return self.all_random_textures[self._txt_cache[cache_key]]
        
        cache_value = random.randint(0, len(self.all_random_textures)-1)
        self._txt_cache[cache_key] = cache_value
        return self.all_random_textures[cache_value]

        
deep_water = GroundVoxel("deep_water", 0.5, no_corner=True)
shallow_water = GroundVoxel("shallow_water", 0.2)
grass = GroundVoxel("grass", all_textures=grass_images)
sand = GroundVoxel("sand", 0.05, all_textures=sand_textures)
stone = GroundVoxel("stone")
snow = GroundVoxel("snow", 0.1, no_corner=True)

generation_map = {
    helpers.FloatRange(-0.6, -0.35): deep_water,
    helpers.FloatRange(-0.35, -0.25): shallow_water,
    helpers.FloatRange(-0.25, -0.1): sand,
    helpers.FloatRange(-0.1, 0.35): grass,
    helpers.FloatRange(0.35, 0.45): stone,
    helpers.FloatRange(0.45, 0.61): snow
}    


def voxel_from_perlin(value: float) -> GroundVoxel:
    for gen_range, voxel in generation_map.items():
        if value in gen_range:
            return voxel

    return value

