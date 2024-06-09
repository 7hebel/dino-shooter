from modules import collectables
from modules import environment
from modules import directions
from modules import headers
from modules import helpers
from modules import voxels

from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import threading
import pygame
import time
import uuid
import json
import sys

pygame.font.init()
GUI_FONT = pygame.font.Font("./textures/ui/font.ttf", 32)


def drop_shadow_text(screen, text, x, y, color=(255,255,255), drop_color=(128,128,128)):
    dropshadow_offset = 1 + (32 // 15)
    text_bitmap = GUI_FONT.render(text, True, drop_color)
    screen.blit(text_bitmap, (x+dropshadow_offset, y+dropshadow_offset) )
    text_bitmap = GUI_FONT.render(text, True, color)
    screen.blit(text_bitmap, (x, y))

        
@dataclass
class Enemy:
    x: int
    y: int
    color: str
    facing: directions.AngleDirection


@dataclass
class RenderData:
    x_offset: int
    y_offset: int
    voxel_map: list
    env_map: list
    bullets: list
    enemies: list[Enemy]


@dataclass
class RenderMargins:
    top_index: int
    left_index: int
    right_index: int
    bottom_index: int
    left_append: int
    top_append: int


@dataclass
class BulletPayload:
    bullet_id: str
    color: str
    shot_x: int
    shot_y: int
    direction: directions.AngleDirection
    
    def __post_init__(self):
        self.x = self.shot_x
        self.y = self.shot_y
        self.moved = 0
        

class BulletsManager:
    def __init__(self, player) -> None:
        self.player: Player = player
        self.active_bullets: list[BulletPayload] = []
        self._remove = []
        self._is_ticking = False
    
    def add_bullet(self, bullet: BulletPayload) -> None:
        self.active_bullets.append(bullet)
        if not self._is_ticking:
            self.start_tick()
        
    def remove_bullet(self, bullet) -> None:
        if bullet.bullet_id not in self._remove:
            self._remove.append(bullet.bullet_id)
        
    def start_tick(self):
        self._is_ticking = True
        
        def ticking():
            while self.active_bullets:
                is_bullet_in_viewport = False
                
                for bullet in self.active_bullets:
                    if bullet.bullet_id in self._remove:
                        self.active_bullets.remove(bullet)
                        self._remove.remove(bullet.bullet_id)
                        is_bullet_in_viewport = True
                        continue
                    
                    if bullet.direction == directions.AngleDirection.N:
                        bullet.y -= 1
                    if bullet.direction == directions.AngleDirection.S:
                        bullet.y += 1
                    if bullet.direction == directions.AngleDirection.E:
                        bullet.x += 1
                    if bullet.direction == directions.AngleDirection.W:
                        bullet.x -= 1
                        
                    bullet.moved += 1
                    if bullet.moved > 25:
                        self.remove_bullet(bullet)
                        is_bullet_in_viewport = True
                        continue
                
                    if bullet.x < 0 or bullet.x > len(self.player.world.voxel_world[0]) - 1 or bullet.y < 0 or bullet.y > len(self.player.world.voxel_world) - 1:
                        self.remove_bullet(bullet)
                        is_bullet_in_viewport = True
                        continue
                    
                    if self.player.world.voxel_world[bullet.y][bullet.x] in (voxels.stone, voxels.snow):
                        self.remove_bullet(bullet)
                        is_bullet_in_viewport = True
                        continue
                    
                    if bullet.color == self.player.color:
                        for enemy in self.player.enemies.values():
                            if (bullet.x, bullet.y) == (enemy.x, enemy.y):
                                self.player.send_event(headers.BULLET_HIT, {"target": enemy.color})
                                self.remove_bullet(bullet)
                                is_bullet_in_viewport = True
                                continue
                            
                    if isinstance(self.player.world.env_layer[bullet.y][bullet.x], environment.EnvVoxel):
                        shot_feedback = self.player.world.env_layer[bullet.y][bullet.x].on_shot()

                        if shot_feedback.remove_voxel:
                            self.player.world.env_layer[bullet.y][bullet.x] = None
                            
                        if not shot_feedback.continue_fly:
                            self.remove_bullet(bullet)
                        
                        if bullet.color == self.player.color:
                            self.player.send_env_update(bullet.x, bullet.y)

                        is_bullet_in_viewport = True
                            
                    if bullet.x in range(self.player.x - self.player.visibility - 1, self.player.x + self.player.visibility + 1) and bullet.y in range(self.player.y - self.player.visibility - 1, self.player.y + self.player.visibility + 1):
                        is_bullet_in_viewport = True                       
                        
                if is_bullet_in_viewport:
                    self.player.render(force=False)
                
                time.sleep(0.1)
                
            self._is_ticking = False
            
        ticker = threading.Thread(target=ticking, daemon=True)
        ticker.start()
                
                    
class AmmunitionManager:
    def __init__(self, loaded: int, unloaded: int, mag_capacity: int, draw_fn) -> None:
        self.loaded = loaded
        self.unloaded = unloaded
        self.mag_capacity = mag_capacity
        self.draw_fn = draw_fn
        
    def __str__(self) -> str:
        return f"{self.loaded}/{self.unloaded}"
        
    def shot(self) -> bool:
        """ Removes loaded round. Returns status (can shoot). """
        if self.loaded > 0:
            self.loaded -= 1
            return True
        return False
    
    def reload(self) -> None:
        to_load = self.mag_capacity-self.loaded
        for _ in range(to_load):
            if self.unloaded <= 0:
                break
            else:
                self.unloaded -= 1
                self.loaded += 1
                self.draw_fn()
                time.sleep(0.1)
                
    def add_ammo(self, amount: int) -> None:
        self.unloaded += amount
        if self.unloaded > 99:
            self.unloaded = 99
        
                    
class Player:
    def __init__(self, screen, world, client, color: str, walk_cooldown: float = 0.25, init_spawn: tuple[int, int] = None):
        if init_spawn is None:
            self.y, self.x = world.get_spawn_point()
        else:
            self.y, self.x = init_spawn
        self.visibility = 5
        self.slowness = 0
        self.speedness = 0
        self.facing = directions.AngleDirection.S
        self.world = world
        self.screen: pygame.Surface = screen
        self.color = color
        self.bullets_manager = BulletsManager(self)
        self.walk_cooldown = walk_cooldown
        self.shoot_cooldown = 0.5
        self.ammo_manager = AmmunitionManager(10, 30, 10, self.render)
        self.walls_available = 3
        self._next_shot_at = 0
        self.health = 100
        self.is_started = False
        self.client = client
        self.enemies: dict[str, Enemy] = {}
        self.exit_game = False
        self._redner_lock = False
        
        self.stream_receiver = threading.Thread(target=self.game_stream_receiver, daemon=True)
        self.stream_receiver.start()

        self.send_event(headers.CLIENT_READY)

        self.render()
        self.input_handler()
        
    def send_event(self, event_type: str, payload: dict = {}) -> None:
        """ Send event to server. """
        data = {
            "EVENT": event_type,
            "PAYLOAD": payload
        }
        self.client.send((json.dumps(data)+";").encode())
            
    def game_stream_receiver(self) -> None:
        """ Receive and process all data from server. """
        while True:
            try:
                data = self.client.recv(headers.CONN_BUFSIZE).decode()
                packets = data.split(";")
                for p in packets:
                    if not p:
                        continue
                    message = json.loads(p)
                    self.handle_server_message(message)
                    
            except ConnectionError:
                print("ERROR: Server stopped.")
                self.exit_game = True
                return
    
    def handle_server_message(self, message: dict) -> None:
        event_type = message.get("EVENT")
        payload = message.get("PAYLOAD")
        
        if event_type == headers.START_GAME:
            self.is_started = True
            self.render()
            self.send_player_state_update()
            
        if event_type == headers.ENEMY_UPDATE:
            self.enemies[payload["color"]] = Enemy(**payload)
            self.render()
            
        if event_type == headers.ENV_UPDATE:
            new_voxel = environment.import_env_voxel(payload.get("voxel"))
            self.world.env_layer[payload.get("y")][payload.get("x")] = new_voxel
            self.render()
            
        if event_type == headers.DESTROY_ENEMY:
            color = payload.get("color")
            if color in self.enemies:
                self.enemies.pop(color)
                self.render()
            
        if event_type == headers.GAME_OVER:
            print("Game over")
            self.exit_game = True
            sys.exit()
            
        if event_type == headers.BULLET_HIT:
            self.deal_damage(25)
            self.render()
            
        if event_type == headers.RENDER_BULLET:
            bullet_data = BulletPayload(**payload)
            self.bullets_manager.add_bullet(bullet_data)
            
    def send_player_state_update(self) -> None:
        data = {
            "color": self.color,
            "x": self.x,
            "y": self.y,
            "facing": self.facing
        }
        self.send_event(headers.PLAYER_UPDATE, data)
            
    def send_env_update(self, x: int, y: int) -> None:
        data = {
            "x": x,
            "y": y,
            "voxel": environment.export_env_voxel(self.world.env_layer[y][x])
        }
        self.send_event(headers.ENV_UPDATE, data)
            
    def get_player_texture(self) -> pygame.Surface:
        image = pygame.image.load(f"./textures/players/{self.color}.png").convert_alpha()
        
        if self.get_ground_block() == voxels.deep_water:
            image.set_alpha(140)
        if self.get_ground_block() == voxels.shallow_water:
            image.set_alpha(220)
        
        return pygame.transform.rotate(image, -self.facing)

    def deal_damage(self, damage: int) -> None:
        self.health -= damage
        if self.health <= 0:
            self.send_event(headers.DEATH, {"color": self.color})
            self.exit_game = True
        self.render()

    def move(self, direction: directions.AngleDirection) -> None:
        past_x, past_y = self.x, self.y
        
        if direction in directions.NORTHISH:
            self.y -= 1
        if direction in directions.SOUTHISH:
            self.y += 1
        if direction in directions.EASTISH:
            self.x += 1
        if direction in directions.WESTISH:
            self.x -= 1
            
        if self.y < 0:
            self.y = 0
        if self.x < 0:
            self.x = 0
        if self.y > self.world.height-1:
            self.y = self.world.height-1
        if self.x > self.world.width-1:
            self.x = self.world.width-1
            
        # Non steppable blocks.
        rolled_back = False
        env_voxel = self.get_env_voxel()
        if isinstance(env_voxel, environment.EnvVoxel):
            if not env_voxel.can_player_stand_on:
                self.x = past_x
                self.y = past_y
                rolled_back = True
                
        if not rolled_back:
            ground_voxel = self.get_ground_block()
            if ground_voxel in (voxels.stone, voxels.snow):
                self.x = past_x
                self.y = past_y
                rolled_back = True
                
        if not rolled_back:
            for enemy in self.enemies.values():
                if enemy.x == self.x and enemy.y == self.y:
                    self.x = past_x
                    self.y = past_y
                    rolled_back = True
                
        self.send_player_state_update()
        
        # Collectables.
        if isinstance(env_voxel, collectables.Collectable):
            env_voxel.collect(self)
            self.world.env_layer[self.y][self.x] = None
            self.send_env_update(self.x, self.y)
        
        # Cactus damange.
        for surr_pos in self.get_neighbour_coords():
            if isinstance(self.world.env_layer[surr_pos[1]][surr_pos[0]], environment.Cactus):
                self.deal_damage(10)
                
        self.slowness = self.get_ground_block().voxel_slowness
        self.render()  
        
    def update_facing(self, facing: directions.AngleDirection) -> None:
        self.facing = facing
        self.send_player_state_update()
        self.render()
        
    def update_visibility(self, new_value: int) -> None:
        width_boost, height_boost = 0, new_value
        if new_value > 13:
            return
        if new_value > 7:
            width_boost = (new_value - 7) * 100
            height_boost = 7
        
        self.visibility = new_value
        screen_size = 200 + (height_boost * 100)
        pygame.display.set_mode((screen_size + width_boost, screen_size))
        self.render()
        
    def get_ground_block(self) -> voxels.GroundVoxel:
        return self.world.voxel_world[self.y][self.x]
        
    def get_env_voxel(self) -> environment.EnvVoxel | None:
        return self.world.env_layer[self.y][self.x]
        
    def get_neighbour_coords(self) -> list[tuple[int, int]]:
        """ Returns coordinates of cross neighbours. """
        coords = []
        for x, y in [(self.x-1, self.y), (self.x+1, self.y), (self.x, self.y-1), (self.x, self.y+1)]:        
            if x != 0 and y != 0 and x != self.world.width and y != self.world.height:
                coords.append((x, y)) 
        return coords
        
    def calc_render_margins(self) -> RenderMargins:
        top_index = self.y - self.visibility
        left_index = self.x - self.visibility
        right_index = self.x + self.visibility
        bottom_index = self.y + self.visibility
        
        left_append = 0
        top_append = 0
        
        if top_index < 0:
            top_append = -top_index
            top_index = 0
        if left_index < 0:
            left_append = -left_index
            left_index = 0
            
        return RenderMargins(
            top_index, left_index, right_index, bottom_index,
            left_append, top_append
        )
        
    def prepare_world_for_camera(self) -> RenderData:
        margins = self.calc_render_margins()
               
        world_map = self.world.voxel_world[margins.top_index:margins.bottom_index+1]
        env_layer = self.world.env_layer[margins.top_index:margins.bottom_index+1]
        for r_index, row in enumerate(world_map):
            world_map[r_index] = row[margins.left_index:margins.right_index+1]
        for r_index, row in enumerate(env_layer):
            env_layer[r_index] = row[margins.left_index:margins.right_index+1]
            
        bullets = []
        for bullet in self.bullets_manager.active_bullets:
            if bullet.bullet_id in self.bullets_manager._remove:
                continue
            if bullet.x in range(margins.left_index, margins.right_index) and bullet.y in range(margins.top_index, margins.bottom_index):
                bullet_data = BulletPayload("", bullet.color, bullet.x-margins.left_index, bullet.y-margins.top_index, bullet.direction)
                bullets.append(bullet_data)
                   
        enemies = []
        for enemy in self.enemies.values():
            if enemy.x in range(margins.left_index, margins.right_index) and enemy.y in range(margins.top_index, margins.bottom_index):
                if not isinstance(self.world.env_layer[enemy.y][enemy.x], environment.Bush):
                    enemy_data = Enemy(enemy.x-margins.left_index, enemy.y-margins.top_index, enemy.color, enemy.facing)
                    enemies.append(enemy_data)
                     
        return RenderData(margins.left_append, margins.top_append, world_map, env_layer, bullets, enemies)
        
    def render(self, force: bool = False) -> None:
        if self._redner_lock and not force:
            return
        self._redner_lock = True
        
        self.screen.fill((0, 0, 0))
        render_data = self.prepare_world_for_camera()
        if not self.is_started:
            drop_shadow_text(self.screen, "Waiting...", self.screen.get_width() // 2 - 70, 300)
            pygame.display.flip()
            self._redner_lock = False
            return
        
        # Ground layer.
        y = render_data.y_offset
        for y_index, world_row in enumerate(render_data.voxel_map):
            x = render_data.x_offset
            
            for x_index, voxel in enumerate(world_row):
                texture = voxel.get_texture(self.x+x, self.y+y)
                img_rect = texture.get_rect().move(x*64, y*64)
                self.screen.blit(texture, img_rect)
                
                # Rounded texture corners.
                n_block = None
                if y_index != 0:
                    n_block = render_data.voxel_map[y_index-1][x_index]
                       
                e_block = None
                if x_index != len(world_row)-1:
                    e_block = render_data.voxel_map[y_index][x_index+1]
                    
                w_block = None
                if x_index != 0:
                    w_block = render_data.voxel_map[y_index][x_index-1]
                    
                s_block = None
                if y_index != len(render_data.voxel_map)-1:
                    s_block = render_data.voxel_map[y_index+1][x_index]
                    
                if w_block is not None and w_block == n_block:
                    corner_texture = w_block.corner_texture
                    if corner_texture:
                        corner_texture = corner_texture.copy()
                        corner_rect = corner_texture.get_rect().move(x*64, y*64)
                        self.screen.blit(corner_texture, corner_rect)
                
                if n_block is not None and n_block == e_block:
                    corner_texture = n_block.corner_texture
                    if corner_texture:
                        corner_texture = corner_texture.copy()
                        corner_texture = pygame.transform.rotate(corner_texture, 270)
                        corner_rect = corner_texture.get_rect().move(x*64, y*64)
                        self.screen.blit(corner_texture, corner_rect)
                    
                if e_block is not None and e_block == s_block:
                    corner_texture = e_block.corner_texture
                    if corner_texture:
                        corner_texture = corner_texture.copy()
                        corner_texture = pygame.transform.rotate(corner_texture, 180)
                        corner_rect = corner_texture.get_rect().move(x*64, y*64)
                        self.screen.blit(corner_texture, corner_rect)
                        
                if s_block is not None and s_block == w_block:
                    corner_texture = s_block.corner_texture
                    if corner_texture:
                        corner_texture = corner_texture.copy()
                        corner_texture = pygame.transform.rotate(corner_texture, 90)
                        corner_rect = corner_texture.get_rect().move(x*64, y*64)
                        self.screen.blit(corner_texture, corner_rect)
                
                x += 1
            y += 1
        
        # Player.
        player_texture = self.get_player_texture()
        player_rect = player_texture.get_rect().move(self.visibility*64, self.visibility*64)
        self.screen.blit(player_texture, player_rect)
        
        # Environment layer.
        y = render_data.y_offset
        for i, env_row in enumerate(render_data.env_map):
            x = render_data.x_offset
            
            for j, env_voxel in enumerate(env_row):
                if env_voxel is None:
                    x += 1
                    continue
                
                texture = env_voxel.get_texture()
                
                if x == self.visibility and y == self.visibility:
                    if isinstance(env_voxel, environment.Bush):
                        texture.set_alpha(100)
                        
                if texture:
                    img_rect = texture.get_rect().move(x*64, y*64)
                    self.screen.blit(texture, img_rect)
                else:
                    render_data.env_map[i][j] = None

                x += 1
            y += 1
        
        # Enemies.
        for enemy_data in render_data.enemies:
            enemy_texture = pygame.image.load(f"./textures/players/{enemy_data.color}.png").convert_alpha()
            enemy_texture = pygame.transform.rotate(enemy_texture, -enemy_data.facing)

            if self.world.voxel_world[self.enemies[enemy_data.color].y][self.enemies[enemy_data.color].x] == voxels.deep_water:
                enemy_texture.set_alpha(140)
            if self.world.voxel_world[self.enemies[enemy_data.color].y][self.enemies[enemy_data.color].x] == voxels.shallow_water:
                enemy_texture.set_alpha(220)
                
            enemy_rect = enemy_texture.get_rect().move(
                (enemy_data.x+render_data.x_offset)*64, 
                (enemy_data.y+render_data.y_offset)*64
            )
            
            self.screen.blit(enemy_texture, enemy_rect)

        # Bullets.
        for bullet_data in render_data.bullets:
            bullet_data: BulletPayload
            
            
            bullet_image = pygame.image.load(f"./textures/bullets/bullet_{bullet_data.color}.png").convert_alpha()
            bullet_image = pygame.transform.rotate(bullet_image, -bullet_data.direction)
            
            bullet_rect = bullet_image.get_rect().move(
                (bullet_data.shot_x+render_data.x_offset)*64, 
                (bullet_data.shot_y+render_data.y_offset)*64
            )
    
            self.screen.blit(bullet_image, bullet_rect)
                   
        # God ray.
        godray_image = pygame.image.load("./textures/godray.png").convert_alpha()
        godray_image = pygame.transform.scale(godray_image, (self.screen.get_height()*1.2, self.screen.get_width()*1.2))
        godray_image.set_alpha(220)
        
        godray_rect = godray_image.get_rect()
        self.screen.blit(godray_image, godray_rect)
                    
        # Interface.
        drop_shadow_text(self.screen, f"{self.health}", 40, self.screen.get_height()-40, color=(255, 200, 200), drop_color=(125, 0, 0))
        heart_image = pygame.image.load("./textures/ui/heart.png").convert_alpha()
        heart_rect = heart_image.get_rect().move(8, self.screen.get_height()-40)
        self.screen.blit(heart_image, heart_rect)
        
        drop_shadow_text(self.screen, f"{self.visibility}", 165, self.screen.get_height()-40, color=(200, 200, 255), drop_color=(0, 0, 125))
        eye_image = pygame.image.load("./textures/ui/eye.png").convert_alpha()
        eye_rect = eye_image.get_rect().move(130, self.screen.get_height()-40)
        self.screen.blit(eye_image, eye_rect)
        
        drop_shadow_text(self.screen, f"{(self.walk_cooldown + self.slowness + self.speedness):.2}", 270, self.screen.get_height()-40, color=(230, 217, 184), drop_color=(112, 90, 25))
        boots_image = pygame.image.load("./textures/ui/speed.png").convert_alpha()
        boots_rect = boots_image.get_rect().move(225, self.screen.get_height()-40)
        self.screen.blit(boots_image, boots_rect)

        drop_shadow_text(self.screen, f"{self.walls_available}", 420, self.screen.get_height()-40, color=(200, 140, 100), drop_color=(70, 40, 15))
        shot_cooldown_image = pygame.image.load("./textures/ui/box.png").convert_alpha()
        shot_cooldown_rect = shot_cooldown_image.get_rect().move(380, self.screen.get_height()-40)
        self.screen.blit(shot_cooldown_image, shot_cooldown_rect)
        
        drop_shadow_text(self.screen, str(self.ammo_manager), self.screen.get_width()-145, self.screen.get_height()-40)
        ammo_image = pygame.image.load("./textures/ui/ammo.png").convert_alpha()
        ammo_rect = ammo_image.get_rect().move(self.screen.get_width()-40, self.screen.get_height()-40)
        self.screen.blit(ammo_image, ammo_rect)
        
        self._redner_lock = False
        pygame.display.flip()
        # pygame.display.update()

    def shoot(self) -> None:
        if self.get_ground_block() == voxels.deep_water:
            return
        
        if self._next_shot_at:
            if datetime.now() <= self._next_shot_at:
                return
        
        shot_status = self.ammo_manager.shot()
        if not shot_status:
            return
        
        bull_x = self.x
        bull_y = self.y

        bullet_data = BulletPayload(
            uuid.uuid4().hex,
            self.color,
            bull_x,
            bull_y,
            self.facing
        )
        
        self.bullets_manager.add_bullet(bullet_data)   
        self._next_shot_at = datetime.now() + timedelta(seconds=self.shoot_cooldown)
        self.send_event(headers.RENDER_BULLET, asdict(bullet_data))

    def build_wall(self):
        if self.walls_available <= 0:
            return
        
        wall_x, wall_y = self.x, self.y
        
        if self.facing == directions.AngleDirection.N:
            wall_y -= 1
        if self.facing == directions.AngleDirection.S:
            wall_y += 1
        if self.facing == directions.AngleDirection.E:
            wall_x += 1
        if self.facing == directions.AngleDirection.W:
            wall_x -= 1
            
        if wall_y < 0 or wall_x < 0 or wall_y > self.world.height-1 or wall_x > self.world.width-1:
            return
        
        for enemy in self.enemies.values():
            if (wall_x, wall_y) == (enemy.x, enemy.y):
                return
            
        ground_voxel = self.world.voxel_world[wall_y][wall_x]
        env_voxel = self.world.env_layer[wall_y][wall_x]
        
        if ground_voxel not in (voxels.snow, voxels.stone, voxels.deep_water):
            if not isinstance(env_voxel, (environment.Tree, environment.Box)):
                self.walls_available -= 1
                self.world.env_layer[wall_y][wall_x] = environment.Box()
        
                self.render()
                self.send_env_update(wall_x, wall_y)              
        
    def input_handler(self):
        self.render()
        
        while True:
            if self.exit_game:
                return
               
            moved = False
            rotated = False
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    exit()
                    
                if not self.is_started:
                    continue

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_a and not moved:
                        moved = True
                        self.move(directions.AngleDirection.W)
                    if event.key == pygame.K_d and not moved:
                        moved = True
                        self.move(directions.AngleDirection.E)
                    if event.key == pygame.K_w and not moved:
                        moved = True
                        self.move(directions.AngleDirection.N)
                    if event.key == pygame.K_s and not moved:
                        moved = True
                        self.move(directions.AngleDirection.S)
                        
                    if event.key == pygame.K_UP and not rotated:
                        rotated = True
                        self.update_facing(directions.AngleDirection.N)
                    if event.key == pygame.K_DOWN and not rotated:
                        rotated = True
                        self.update_facing(directions.AngleDirection.S)
                    if event.key == pygame.K_LEFT and not rotated:
                        rotated = True
                        self.update_facing(directions.AngleDirection.W)
                    if event.key == pygame.K_RIGHT and not rotated:
                        rotated = True
                        self.update_facing(directions.AngleDirection.E)
                        
                    if event.key == pygame.K_SPACE:
                        self.shoot()
                    if event.key == pygame.K_r:
                        self.ammo_manager.reload()
                    if event.key == pygame.K_e:
                        self.build_wall()
                        
            time.sleep(self.walk_cooldown + self.slowness - self.speedness)
                
                        