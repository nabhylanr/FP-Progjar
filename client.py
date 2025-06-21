import pygame
import sys
import socket
import json
import threading
import logging
import time

# Initialize Pygame
pygame.init()

WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Tug of War Digital")

clock = pygame.time.Clock()
FPS = 60

class TugOfWarClient:
    def __init__(self):
        self.lobby_socket = None
        self.game_socket = None
        self.connected_to_lobby = False
        self.connected_to_game = False
        self.my_team = None
        self.room_id = None
        self.game_server = None
        
        self.game_data = {
            'bar_position': 0,
            'timer': 60,
            'left_count': 0,
            'right_count': 0,
            'game_active': False,
            'winner': None
        }
        
        # Server addresses
        self.lobby_address = ('192.168.0.125', 55554)  # Lobby server
        self.last_key_time = {'a': 0, 'd': 0}
        
        # Connection status
        self.status = "CONNECTING_LOBBY"  # CONNECTING_LOBBY -> WAITING_ROOM -> IN_GAME
        
    def connect_to_lobby(self):
        """Connect to lobby server first"""
        try:
            self.lobby_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.lobby_socket.connect(self.lobby_address)
            self.connected_to_lobby = True
            
            # Start listening to lobby
            lobby_thread = threading.Thread(target=self.listen_lobby, daemon=True)
            lobby_thread.start()
            
            print("✅ Connected to lobby server")
            self.status = "WAITING_ROOM"
            return True
            
        except Exception as e:
            print(f"❌ Failed to connect to lobby: {e}")
            self.status = "LOBBY_ERROR"
            return False
    
    def listen_lobby(self):
        """Listen for lobby messages"""
        buffer = ""
        while self.connected_to_lobby:
            try:
                data = self.lobby_socket.recv(1024)
                if data:
                    buffer += data.decode()
                    
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        if line.strip():
                            try:
                                message = json.loads(line.strip())
                                self.handle_lobby_message(message)
                            except json.JSONDecodeError:
                                pass
                else:
                    break
                    
            except Exception as e:
                print(f"❌ Lobby listen error: {e}")
                break
        
        self.connected_to_lobby = False
    
    def handle_lobby_message(self, message):
        """Handle lobby messages"""
        cmd = message.get('command')
        
        if cmd == 'LOBBY_WELCOME':
            print(f"🏠 {message.get('message')}")
            
        elif cmd == 'JOIN_GAME_SERVER':
            # Get game server info from lobby
            server_ip = message.get('server_ip')
            server_port = message.get('server_port')
            self.room_id = message.get('room_id')
            self.game_server = (server_ip, server_port)
            
            print(f"🎮 Assigned to {self.room_id} on server {self.game_server}")
            
            # Now connect to actual game server
            self.connect_to_game_server()
            
        elif cmd == 'ROOM_STATUS':
            room_id = message.get('room_id')
            players = message.get('players_count')
            max_players = message.get('max_players')
            print(f"🏠 Room {room_id}: {players}/{max_players} players")
            
        elif cmd == 'LOBBY_ERROR':
            print(f"❌ Lobby error: {message.get('message')}")
            self.status = "LOBBY_ERROR"
    
    def connect_to_game_server(self):
        """Connect to assigned game server"""
        if not self.game_server:
            return False
            
        try:
            self.game_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.game_socket.connect(self.game_server)
            self.connected_to_game = True
            
            # Start listening to game server
            game_thread = threading.Thread(target=self.listen_game_server, daemon=True)
            game_thread.start()
            
            # Send join request to game server
            self.send_game_command({'command': 'JOIN_GAME'})
            
            print(f"✅ Connected to game server {self.game_server}")
            self.status = "IN_GAME"
            return True
            
        except Exception as e:
            print(f"❌ Failed to connect to game server: {e}")
            self.status = "GAME_ERROR"
            return False
    
    def listen_game_server(self):
        """Listen for game server messages"""
        buffer = ""
        while self.connected_to_game and self.game_socket:
            try:
                data = self.game_socket.recv(1024)
                if data:
                    buffer += data.decode()
                    
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        if line.strip():
                            try:
                                message = json.loads(line.strip())
                                self.handle_game_message(message)
                            except json.JSONDecodeError:
                                pass
                else:
                    break
                    
            except Exception as e:
                if self.connected_to_game:
                    print(f"❌ Game server disconnected: {e}")
                break
        
        self.connected_to_game = False
        self.status = "GAME_DISCONNECTED"
    
    def handle_game_message(self, message):
        """Handle game server messages"""
        cmd = message.get('command')
        
        if cmd == 'TEAM_ASSIGNED':
            self.my_team = message.get('team')
            print(f"👤 Assigned to team: {self.my_team}")
            
        elif cmd == 'GAME_UPDATE':
            self.game_data.update({
                'bar_position': message.get('bar_position', 0),
                'timer': message.get('timer', 60),
                'left_count': message.get('left_count', 0),
                'right_count': message.get('right_count', 0),
                'game_active': message.get('game_active', False),
                'winner': message.get('winner')
            })
            
        elif cmd == 'GAME_END':
            self.game_data['winner'] = message.get('winner')
            self.game_data['game_active'] = False
    
    def send_game_command(self, command):
        """Send command to game server"""
        if self.connected_to_game and self.game_socket:
            try:
                message = json.dumps(command) + '\n'
                self.game_socket.send(message.encode())
                return True
            except Exception as e:
                print(f"❌ Send error: {e}")
                return False
        return False
    
    def send_button_press(self, direction):
        """Send button press with anti-spam"""
        current_time = time.time()
        if current_time - self.last_key_time.get(direction, 0) < 0.1:
            return
            
        self.last_key_time[direction] = current_time
        
        if self.connected_to_game and self.game_data['game_active']:
            if direction == 'left':
                self.send_game_command({'command': 'PRESS_LEFT'})
            else:
                self.send_game_command({'command': 'PRESS_RIGHT'})
    
    def send_start_game(self):
        """Send start game command"""
        if self.connected_to_game:
            self.send_game_command({'command': 'START_GAME'})

def draw_game(screen, client):
    """Draw game interface"""
    screen.fill((30, 30, 50))
    
    font_large = pygame.font.Font(None, 48)
    font_medium = pygame.font.Font(None, 36)
    font_small = pygame.font.Font(None, 24)
    
    # Title
    title = font_large.render("TUG OF WAR DIGITAL", True, (255, 255, 255))
    screen.blit(title, (WIDTH//2 - title.get_width()//2, 50))
    
    # Status based messages
    if client.status == "CONNECTING_LOBBY":
        status_text = font_medium.render("Connecting to lobby...", True, (255, 255, 0))
        screen.blit(status_text, (WIDTH//2 - status_text.get_width()//2, HEIGHT//2))
        return
        
    elif client.status == "LOBBY_ERROR":
        error_text = font_large.render("LOBBY CONNECTION FAILED", True, (255, 0, 0))
        screen.blit(error_text, (WIDTH//2 - error_text.get_width()//2, HEIGHT//2))
        return
        
    elif client.status == "WAITING_ROOM":
        wait_text = font_medium.render("Finding game room...", True, (255, 255, 0))
        screen.blit(wait_text, (WIDTH//2 - wait_text.get_width()//2, HEIGHT//2))
        
        if client.room_id:
            room_text = font_small.render(f"Room: {client.room_id}", True, (200, 200, 200))
            screen.blit(room_text, (WIDTH//2 - room_text.get_width()//2, HEIGHT//2 + 40))
        return
        
    elif client.status == "GAME_ERROR":
        error_text = font_large.render("GAME SERVER CONNECTION FAILED", True, (255, 0, 0))
        screen.blit(error_text, (WIDTH//2 - error_text.get_width()//2, HEIGHT//2))
        return
        
    elif client.status == "GAME_DISCONNECTED":
        error_text = font_large.render("DISCONNECTED FROM GAME", True, (255, 0, 0))
        screen.blit(error_text, (WIDTH//2 - error_text.get_width()//2, HEIGHT//2))
        return
    
    # If we reach here, we're IN_GAME
    
    # Room info
    if client.room_id and client.game_server:
        room_text = font_small.render(f"Room: {client.room_id} | Server: {client.game_server}", True, (150, 150, 150))
        screen.blit(room_text, (10, 10))
    
    # Team assignment
    if client.my_team:
        team_text = font_medium.render(f"TIM ANDA: {client.my_team.upper()}", True, 
                                     (255, 100, 100) if client.my_team == 'left' else (100, 100, 255))
        screen.blit(team_text, (WIDTH//2 - team_text.get_width()//2, 100))
    
    # Team counts  
    left_text = font_medium.render(f"TIM KIRI ({client.game_data['left_count']})", True, (255, 100, 100))
    right_text = font_medium.render(f"TIM KANAN ({client.game_data['right_count']})", True, (100, 100, 255))
    
    screen.blit(left_text, (100, 150))
    screen.blit(right_text, (WIDTH - 250, 150))
    
    # Progress bar
    bar_width = 500
    bar_height = 40
    bar_x = (WIDTH - bar_width) // 2
    bar_y = 250
    
    pygame.draw.rect(screen, (100, 100, 100), (bar_x, bar_y, bar_width, bar_height))
    
    # Left and right zones
    left_surface = pygame.Surface((bar_width//2, bar_height))
    left_surface.fill((255, 100, 100))
    left_surface.set_alpha(100)
    screen.blit(left_surface, (bar_x, bar_y))
    
    right_surface = pygame.Surface((bar_width//2, bar_height))
    right_surface.fill((100, 100, 255))
    right_surface.set_alpha(100)
    screen.blit(right_surface, (bar_x + bar_width//2, bar_y))
    
    # Position indicator
    pos_ratio = (client.game_data['bar_position'] + 50) / 100
    pos_ratio = max(0, min(1, pos_ratio))
    indicator_x = bar_x + (pos_ratio * bar_width)
    pygame.draw.circle(screen, (255, 255, 0), (int(indicator_x), bar_y + bar_height//2), 20)
    
    # Center line
    pygame.draw.line(screen, (255, 255, 255), 
                    (bar_x + bar_width//2, bar_y), 
                    (bar_x + bar_width//2, bar_y + bar_height), 3)
    
    # Timer
    timer_text = font_medium.render(f"Timer: {client.game_data['timer']}", True, (255, 255, 255))
    screen.blit(timer_text, (WIDTH//2 - timer_text.get_width()//2, 350))
    
    # Game controls and status
    if client.my_team and client.game_data['game_active']:
        if client.my_team == 'left':
            inst = "Tekan 'A' untuk menarik ke kiri!"  
            color = (255, 100, 100)
        else:
            inst = "Tekan 'D' untuk menarik ke kanan!"
            color = (100, 100, 255)
        
        inst_text = font_small.render(inst, True, color)
        screen.blit(inst_text, (WIDTH//2 - inst_text.get_width()//2, 400))
    
    # Game status
    if client.game_data['winner']:
        winner_text = font_large.render(f"TIM {client.game_data['winner']} MENANG!", True, (255, 255, 0))
        screen.blit(winner_text, (WIDTH//2 - winner_text.get_width()//2, 450))
    elif not client.game_data['game_active']:
        wait_text = font_medium.render("Tekan SPACE untuk mulai game", True, (255, 255, 255))
        screen.blit(wait_text, (WIDTH//2 - wait_text.get_width()//2, 450))

def main():
    client = TugOfWarClient()
    
    # Connect to lobby first
    if not client.connect_to_lobby():
        print("❌ Failed to connect to lobby")
        return
    
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            elif event.type == pygame.KEYDOWN:
                if client.status == "IN_GAME":
                    if event.key == pygame.K_a:
                        client.send_button_press('left')
                    elif event.key == pygame.K_d:
                        client.send_button_press('right')
                    elif event.key == pygame.K_SPACE:
                        client.send_start_game()
                        
                if event.key == pygame.K_ESCAPE:
                    running = False
        
        # Draw game
        draw_game(screen, client)
        pygame.display.flip()
        clock.tick(FPS)
    
    # Cleanup
    try:
        if client.lobby_socket:
            client.lobby_socket.close()
        if client.game_socket:
            client.game_socket.close()
    except:
        pass
    
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()