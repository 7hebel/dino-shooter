from modules import headers
from modules import world

import threading
import socket
import random
import json
import time
import sys
import os


os.system("cls || clear")

PLAYERS_AMOUNT = 2
if len(sys.argv) > 1:
    try:
        PLAYERS_AMOUNT = int(sys.argv[1])
    except ValueError:
        print(f"ERROR: Invalid custom PLAYERS_AMOUNT: {PLAYERS_AMOUNT} (using 2)")
print(f"Awaiting {PLAYERS_AMOUNT} players...")

PLAYER_COLORS = ["red", "blue", "orange"]
color_pointer = -1
def get_player_color() -> str:
    global color_pointer
    color_pointer += 1
    if color_pointer > len(PLAYER_COLORS)-1:
        color_pointer = 0
    return PLAYER_COLORS[color_pointer]

is_game_started = False


def is_game_over() -> bool:
    if not is_game_started:
        return False
    return len(ClientHandler.active_clients) <= 1

def get_winner() -> str:
    if not is_game_over():
        return ""
    if ClientHandler.active_clients:
        return list(ClientHandler.active_clients.keys())[0].title()
    return ""


class ClientHandler:
    active_clients: dict[str, "ClientHandler"] = {}
    
    @staticmethod
    def spread_message(header: str, message: dict = {}) -> None:
        """ Send message to all active clients. """
        for client in ClientHandler.active_clients.values():
            client.send_to_client(header, message)
    
    @staticmethod
    def remove_client(color: str) -> None:
        if color in ClientHandler.active_clients:
            ClientHandler.active_clients.pop(color)
        
        ClientHandler.spread_message(headers.DESTROY_ENEMY, {"color": color})
        if is_game_over():
            print(f"\nWinner: {get_winner()}")
            print("\n=== GAME OVER ===\n")
            ClientHandler.spread_message(headers.GAME_OVER)
    
    def __init__(self, connection, address, world) -> None:
        if ClientHandler.active_clients == len(PLAYER_COLORS):
            print("! Refusing connection: max players")
            return
        if is_game_started:
            print("! Refusing connection: game is started")
            return
        
        self.connection = connection
        self.address = address
        self.color = get_player_color()
        self.world = world
        self.player_y, self.player_x = self.world.get_spawn_point()
        self.is_ready = False
        
        self.receiver_th = threading.Thread(target=self.receiver, daemon=True)
        self.receiver_th.start()
        
        print(f"* Registered {self.color} player!")
        
        self.send_to_client(headers.GAME_INIT_WORLD_DATA, self.world.to_dict())
        time.sleep(0.25)
        self.send_to_client(headers.GAME_INIT_PLAYER_DATA, {
            "color": self.color,
            "spawn_x": self.player_x,
            "spawn_y": self.player_y
        })
        
        ClientHandler.active_clients[self.color] = self
        
    def send_to_client(self, header: str, message: dict = {}) -> None:
        data = {"EVENT": header, "PAYLOAD": message}
        
        try:
            self.connection.send((json.dumps(data)+";").encode())
        except ConnectionError:
            print(f"ERROR: cannot send message to: {self.color}")
            ClientHandler.remove_client(self.color)
        
    def receiver(self):
        while True:
            try:
                msg = self.connection.recv(headers.CONN_BUFSIZE).decode()
            except ConnectionError:
                print(f"* {self.color}: Connection stopped.")
                ClientHandler.remove_client(self.color)
                return

            for packet in msg.split(";"):
                if packet:
                    self.handle_message(packet)

    def handle_message(self, message: dict) -> None:
        global is_game_started
        
        message = json.loads(message)
        event_type = message.get("EVENT")
        payload = message.get("PAYLOAD")
        
        if event_type == headers.CLIENT_READY:
            print(f"{self.color}: Client is ready ({len(ClientHandler.active_clients)}/{PLAYERS_AMOUNT})")
            self.is_ready = True
            
            if len(ClientHandler.active_clients) != PLAYERS_AMOUNT:
                return
            for client in ClientHandler.active_clients.values():
                if not client.is_ready:
                    return
                            
            # Start game.
            ClientHandler.spread_message(headers.START_GAME)
            is_game_started = True
            print("\n=== GAME STARTED ===\n")

        if event_type == headers.PLAYER_UPDATE:
            self.player_x = payload.get("x")
            self.player_y = payload.get("y")
            
            for color, client in ClientHandler.active_clients.items():
                if color == self.color:
                    continue
                client.send_to_client(headers.ENEMY_UPDATE, payload)
                
        if event_type == headers.ENV_UPDATE:
            ClientHandler.spread_message(headers.ENV_UPDATE, payload)

        if event_type == headers.BULLET_HIT:
            target = payload["target"]
            if target not in ClientHandler.active_clients:
                print(f"ERROR: Received bullet hit to unregistered enemy? {target}")
                return
            
            ClientHandler.active_clients[target].send_to_client(headers.BULLET_HIT)
            
        if event_type == headers.DEATH:
            color = payload["color"]
            self.remove_client(color)
            
        if event_type == headers.RENDER_BULLET:
            color = payload["color"]
            for color, client in ClientHandler.active_clients.items():
                if color == self.color:
                    continue
                client.send_to_client(headers.RENDER_BULLET, payload)


PORT = 5050
SERVER = socket.gethostbyname(socket.gethostname())
ADDRESS = (SERVER, PORT)

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(ADDRESS)


def connection_accepter(public_world):
    server.listen()
    print(f"Server is listening on: {SERVER}:{PORT}\n")
    
    while True:
        try:
            conn, addr = server.accept()
        except OSError:
            return
        ClientHandler(conn, addr, public_world)

def start_server():
    public_world = world.World(height=100, width=100, seed=random.randint(1, 1000))
    conn_accepter = threading.Thread(target=connection_accepter, args=(public_world,), daemon=False)
    conn_accepter.start()
    
    while not is_game_over():
        pass
    
    server.close()        
    

start_server()
