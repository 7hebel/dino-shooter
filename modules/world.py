from modules import collectables
from modules import environment
from modules import perlin
from modules import voxels

import random


def perctentage_random(chance: float) -> bool:
    return random.random() < chance


def generate_voxel_world(perlin_map: list[list[float]]) -> list:
    world = []
    
    for row in perlin_map:
        world_row = []
        
        for perlin_value in row:
            voxel = voxels.voxel_from_perlin(perlin_value)
            world_row.append(voxel)
            
        world.append(world_row)
        
    return world


def generate_env_layer(world_map, env_map) -> list:
    env_layer = []
    
    for y, row in enumerate(env_map):
        env_layer_row = []
        
        for x, perlin_value in enumerate(row):
            env_voxel = environment.env_voxel_from_perlin(perlin_value)
            if env_voxel is None:
                added_collectable = False
                for collectable in collectables.all_collectables:
                    if perctentage_random(collectable.spawn_chance):
                        if world_map[y][x] in collectable.spawn_on:
                            env_layer_row.append(collectable)
                            added_collectable = True
                            break
                    
                if added_collectable:
                    continue
            
            if env_voxel is not None:
                ground_voxel = world_map[y][x]
                if env_voxel.can_stand_on and ground_voxel in env_voxel.can_stand_on:
                    env_layer_row.append(env_voxel)
                    continue
                        
            env_layer_row.append(None)
        env_layer.append(env_layer_row)
        
    return env_layer


class World:
    def __init__(self, height: int = 100, width: int = 100, seed: int = 10, override_env: list = None) -> None:
        self.height = height
        self.width = width
        self.seed = seed
        
        self.world_perlin_map = perlin.generate_perlin_map(self.height, self.width, self.seed)
        self.voxel_world = generate_voxel_world(self.world_perlin_map)
        
        self.env_perlin_map = perlin.generate_perlin_map(self.height, self.width, self.seed, 0.15*height)
        if override_env is None:
            self.env_layer = generate_env_layer(self.voxel_world, self.env_perlin_map)
        
        else:
            self.env_layer = []
            
            input_translation_table = {
                "tree": environment.Tree,
                "cactus": environment.Cactus,
                "bush": environment.Bush,
                "box": environment.Box,
                "ammo_box": collectables.C_AmmunitionBox,
                "health_box": collectables.C_HealthBox,
                "vis_boost": collectables.C_VisibilityBoost,
                "speed_boost": collectables.C_SpeedBoost,
                "add_box": collectables.C_AdditionalBox
            }
            
            for data_row in override_env:
                env_row = []
                
                for item in data_row:
                    if item is None:
                        env_row.append(None)
                        continue
                    
                    if type(item) == int:
                        env_row.extend([None] * item)
                        continue
                    
                    env_obj = input_translation_table[item]()
                    env_row.append(env_obj)
                self.env_layer.append(env_row)
        
    def get_spawn_point(self) -> tuple[int, int]:
        # return (random.randint(5, 10), random.randint(5, 10))
        x = random.randint(5, self.width-5)
        y = random.randint(5, self.height-5)
        while True:
            if self.voxel_world[y][x] not in (voxels.stone, voxels.snow):
                if not isinstance(self.env_layer[y][x], (environment.Tree, environment.Cactus)):
                    return (y, x)
        
    def to_dict(self) -> dict:
        env_data = []

        for env_row in self.env_layer:
            row = []
            null_count = 0
            
            for env_voxel in env_row:
                if env_voxel is None:
                    null_count += 1
                    continue
                
                if null_count > 0:
                    row.append(null_count)
                    null_count = 0
                
                row.append(env_voxel.name)
            
            if null_count:
                row.append(null_count)
                null_count = 0
            env_data.append(row)
            
        return {
            "height": self.height,
            "width": self.width,
            "seed": self.seed,
            "env_data": env_data
        }
