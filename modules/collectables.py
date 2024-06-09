from modules import voxels

from abc import abstractmethod
import pygame
import random


class Collectable:
    def __init__(self, name: str, spawn_on: list[voxels.GroundVoxel], spawn_chance: float) -> None:
        """ 
        Spawn chance should be a percentage number in: <0, 1> 
        """
        self.name = name
        self.spawn_on = spawn_on
        self.spawn_chance = spawn_chance
        
    def get_texture(self) -> pygame.Surface | None:
        return None
        
    @abstractmethod
    def collect(self, player) -> None:
        ...
        

class C_AmmunitionBox(Collectable):
    def __init__(self) -> None:
        super().__init__("ammo_box", [voxels.grass, voxels.sand, voxels.shallow_water, voxels.deep_water], 0.003)

    def get_texture(self) -> pygame.Surface | None:
        return pygame.image.load("./textures/collectables/ammobox.png").convert_alpha()

    def collect(self, player) -> None:
        additional_ammo = random.randint(5, 20)
        player.ammo_manager.add_ammo(additional_ammo)
        

class C_HealthBox(Collectable):
    def __init__(self) -> None:
        super().__init__("health_box", [voxels.grass, voxels.sand, voxels.shallow_water, voxels.deep_water], 0.001)

    def get_texture(self) -> pygame.Surface | None:
        return pygame.image.load("./textures/collectables/healthbox.png").convert_alpha()

    def collect(self, player) -> None:
        additional_health = random.randint(30, 60)
        player.health += additional_health
        if player.health > 150:
            player.health = 150


class C_VisibilityBoost(Collectable):
    def __init__(self) -> None:
        super().__init__("vis_boost", [voxels.grass, voxels.sand, voxels.shallow_water, voxels.deep_water], 0.0003)

    def get_texture(self) -> pygame.Surface | None:
        return pygame.image.load("./textures/collectables/vis_boost.png").convert_alpha()

    def collect(self, player) -> None:
        player.update_visibility(player.visibility + 1)


class C_SpeedBoost(Collectable):
    def __init__(self) -> None:
        super().__init__("speed_boost", [voxels.grass, voxels.sand, voxels.shallow_water, voxels.deep_water], 0.0003)

    def get_texture(self) -> pygame.Surface | None:
        return pygame.image.load("./textures/collectables/speed_boost.png").convert_alpha()

    def collect(self, player) -> None:
        player.speedness += random.randrange(5, 15) / 100
        if player.speedness > player.walk_cooldown:
            player.speedness = player.walk_cooldown
        player.speedness = round(player.speedness, 2)


class C_AdditionalBox(Collectable):
    def __init__(self) -> None:
        super().__init__("add_box", [voxels.grass, voxels.sand, voxels.shallow_water, voxels.deep_water], 0.005)

    def get_texture(self) -> pygame.Surface | None:
        return pygame.image.load("./textures/collectables/add_box.png").convert_alpha()

    def collect(self, player) -> None:
        if player.walls_available < 10:
            player.walls_available += 1


all_collectables = [C_AmmunitionBox(), C_HealthBox(), C_VisibilityBoost(), C_SpeedBoost(), C_AdditionalBox()]
