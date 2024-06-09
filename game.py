from modules import headers
from modules import player
from modules import world 

from dataclasses import dataclass
import socket
import pygame
import json
import os

os.system("cls || clear")


@dataclass
class GameInitData:
    world_data: dict | None = None
    player_data: dict | None = None
    
    def is_ready(self) -> bool:
        return self.world_data is not None and self.player_data is not None
    
    def feed(self, header: str, data: dict) -> None:
        if header == headers.GAME_INIT_WORLD_DATA:
            self.world_data = data
        elif header == headers.GAME_INIT_PLAYER_DATA:
            self.player_data = data
        else:
            print(f"ERROR: Received GAME_INIT message with invalid header: {header}")  


def receive_single() -> dict:
    """ Receive single message from server. """
    data = client.recv(headers.CONN_BUFSIZE).decode().removesuffix(";")
    message = json.loads(data)
    if message:
        return message


ip_addr = input("IP: ")
# ip_addr = "192.168.56.1"
port = 5050
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

try:
    client.connect((ip_addr, port))
except ConnectionRefusedError:
    print("ERROR: Cannot establish connection with server")
    exit()

game_init_data = GameInitData()
while not game_init_data.is_ready():
    data = receive_single()
    game_init_data.feed(data.get("EVENT"), data.get("PAYLOAD"))

print("Received world and player data.")


pygame.init()
screen = pygame.display.set_mode((700, 750), vsync=1)
pygame.display.set_caption(f"Game [{game_init_data.player_data['color']}]")

gen_world = world.World(game_init_data.world_data["height"], game_init_data.world_data["width"], game_init_data.world_data["seed"], game_init_data.world_data["env_data"])
game_player = player.Player(screen, gen_world, client, game_init_data.player_data["color"], init_spawn=[game_init_data.player_data["spawn_y"], game_init_data.player_data["spawn_x"]])
