from modules import helpers
from modules import voxels

from dataclasses import dataclass
from abc import abstractmethod
import pygame
import random


@dataclass
class BulletHitInfo:
    continue_fly: bool
    remove_voxel: bool
    texture_affected: bool


class EnvVoxel:
    def __init__(self, name: str, can_spawn_on: list[voxels.GroundVoxel], can_player_stand_on: bool):
        self.name = name
        self.can_stand_on = can_spawn_on
        self.can_player_stand_on = can_player_stand_on

    def on_shot(self) -> BulletHitInfo:
        """ 
        Called when bullets hits this voxel. 
        """
        return BulletHitInfo(True, False, False)
        
    @abstractmethod
    def get_texture(self) -> pygame.Surface | None:
        ...
        
        
class Tree(EnvVoxel):
    def __init__(self):
        super().__init__("tree", [voxels.grass], False)
        self.health = random.randint(2, 3)
        self._txt_dir = "./textures/env/tree/"
        
    def get_texture(self) -> pygame.Surface | None:
        path = self._txt_dir
        
        if self.health == 3:
            path += "tree-1.png"
        if self.health == 2:
            path += "tree-2.png"
        if self.health == 1:
            path += "tree-3.png"
        if self.health < 1:
            return None
            
        return pygame.image.load(path).convert_alpha()
        
    def on_shot(self) -> BulletHitInfo:
        if self.health > 1:
            self.health -= 1
            if self.health == 1:
                self.can_player_stand_on = True
            return BulletHitInfo(False, False, True)
        else:
            return BulletHitInfo(False, True, True)
    
    
class Bush(EnvVoxel):
    def __init__(self):
        super().__init__("bush", [voxels.grass], True)
        
    def get_texture(self) -> pygame.Surface | None:
        return pygame.image.load("./textures/env/bush.png").convert_alpha()
    
    
class Box(EnvVoxel):
    def __init__(self):
        super().__init__("box", [], False)
        self.health = 5
        
    def get_texture(self) -> pygame.Surface | None:
        return pygame.image.load(f"./textures/box/box{self.health}.png").convert_alpha()
    
    def on_shot(self) -> BulletHitInfo:
        if self.health == 1:
            return BulletHitInfo(False, True, True)
            
        if self.health > 1:
            self.health -= 1
            return BulletHitInfo(False, False, True)


class Cactus(EnvVoxel):
    def __init__(self):
        super().__init__("cactus", [voxels.sand], False)
        self.texture_path = f"./textures/env/cactus/cactus{random.randint(1,9)}.png"
        
    def get_texture(self) -> pygame.Surface | None:
        return pygame.image.load(self.texture_path).convert_alpha()
    
    def on_shot(self) -> BulletHitInfo:
        return BulletHitInfo(False, True, False)

    
generation_map = {
    helpers.FloatRange(-0.6, -0.2): Tree,
    helpers.FloatRange(0.3, 0.61): Bush,
    helpers.FloatRange(-0.4, -0.15): Cactus,
}


def env_voxel_from_perlin(value: float) -> EnvVoxel | None:
    for gen_range, env_voxel in generation_map.items():
        if value in gen_range:
            return env_voxel()

    return None


def export_env_voxel(env_voxel: EnvVoxel | None) -> dict:
    if env_voxel is None:
        return {"name": None}
    export_data = {"name": env_voxel.name}
    
    for attr_name in dir(env_voxel):
        if attr_name.startswith("__"):
            continue
        value = getattr(env_voxel, attr_name)
        if not hasattr(value, "__call__") and attr_name not in ["can_stand_on", "can_player_stand_on"]:
            export_data[attr_name] = value
        
    return export_data

def import_env_voxel(data: dict) -> EnvVoxel | None:
    if data["name"] is None:
        return None
    
    objects_translation = {
        "tree": Tree,
        "cactus": Cactus,
        "bush": Bush,
        "box": Box,
    }
    
    name = data.pop("name")
    env_obj = objects_translation[name]()
    for attr_name, attr_value in data.items():
        setattr(env_obj, attr_name, attr_value)    
    return env_obj
    
    
    