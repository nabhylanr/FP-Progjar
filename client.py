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
        self.socket = None
        self.connected = False
        self.my_team = None
        self.game_data = {
            'bar_position': 0,
            'timer': 60,
            'left_count': 0,
            'right_count': 0,
            'game_active': False,
            'winner': None
        }
        # Ganti 'localhost' dengan IP server untuk multiplayer antar laptop
        self.server_address = ('192.168.0.31', 55555)  # Untuk testing lokal
        # self.server_address = ('192.168.1.100', 55555)  # Contoh IP server untuk multiplayer
        self.last_key_time = {'a': 0, 'd': 0}  # Anti-spam
        
    def connect_to_server(self):
        """Connect to game server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect(self.server_address)
            self.connected = True
            
            # Start listening thread
            listen_thread = threading.Thread(target=self.listen_server, daemon=True)
            listen_thread.start()
            
            print("Connected to server")
            
            # Send join request
            self.send_command({'command': 'JOIN_GAME'})
            
            return True
            
        except Exception as e:
            print(f"Failed to connect: {e}")
            return False
    
    def listen_server(self):
        """Listen for messages from server"""
        buffer = ""
        while self.connected:
            try:
                data = self.socket.recv(1024)
                if data:
                    buffer += data.decode()
                    
                    # Process complete messages
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        if line.strip():
                            try:
                                message = json.loads(line.strip())
                                self.handle_server_message(message)
                            except json.JSONDecodeError as e:
                                logging.warning(f"Invalid JSON: {line}")
                else:
                    break
                    
            except Exception as e:
                if self.connected:  # Only log if we're supposed to be connected
                    logging.warning(f"Listen error: {e}")
                break
        
        self.connected = False
        print("Disconnected from server")
    
    def handle_server_message(self, message):
        """Handle message from server"""
        cmd = message.get('command')
        
        if cmd == 'TEAM_ASSIGNED':
            self.my_team = message.get('team')
            print(f"Assigned to team: {self.my_team}")
            
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
            print(f"Game ended! Winner: {message.get('winner')}")
            
        elif cmd == 'GAME_ERROR':
            print(f"Game error: {message.get('message')}")
    
    def send_command(self, command):
        """Send command to server"""
        if self.connected:
            try:
                message = json.dumps(command) + '\n'
                self.socket.send(message.encode())
                return True
            except Exception as e:
                logging.warning(f"Send error: {e}")
                self.connected = False
                return False
        return False
    
    def send_button_press(self, direction):
        """Send button press to server with anti-spam"""
        current_time = time.time()
        if current_time - self.last_key_time.get(direction, 0) < 0.1:  # 100ms cooldown
            return
            
        self.last_key_time[direction] = current_time
        
        if self.connected and self.game_data['game_active']:
            command = f'PRESS_{direction.upper()}'
            self.send_command({'command': command})
    
    def send_start_game(self):
        """Send start game command"""
        if self.connected:
            self.send_command({'command': 'START_GAME'})

def draw_game(screen, client):
    """Draw game interface"""
    # Clear screen
    screen.fill((30, 30, 50))
    
    # Fonts
    font_large = pygame.font.Font(None, 48)
    font_medium = pygame.font.Font(None, 36)
    font_small = pygame.font.Font(None, 24)
    
    # Connection status
    if not client.connected:
        error_text = font_large.render("DISCONNECTED FROM SERVER", True, (255, 0, 0))
        screen.blit(error_text, (WIDTH//2 - error_text.get_width()//2, HEIGHT//2))
        return
    
    # Title
    title = font_large.render("TUG OF WAR DIGITAL", True, (255, 255, 255))
    screen.blit(title, (WIDTH//2 - title.get_width()//2, 50))
    
    # Team assignment info
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
    
    # Background bar
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
    pos_ratio = max(0, min(1, pos_ratio))  # Clamp to 0-1
    indicator_x = bar_x + (pos_ratio * bar_width)
    pygame.draw.circle(screen, (255, 255, 0), (int(indicator_x), bar_y + bar_height//2), 20)
    
    # Center line
    pygame.draw.line(screen, (255, 255, 255), 
                    (bar_x + bar_width//2, bar_y), 
                    (bar_x + bar_width//2, bar_y + bar_height), 3)
    
    # Position value
    pos_text = font_small.render(f"Posisi: {client.game_data['bar_position']}", True, (255, 255, 255))
    screen.blit(pos_text, (WIDTH//2 - pos_text.get_width()//2, bar_y + bar_height + 10))
    
    # Timer
    timer_color = (255, 255, 255) if client.game_data['timer'] > 10 else (255, 0, 0)
    timer_text = font_medium.render(f"Timer: {client.game_data['timer']}", True, timer_color)
    screen.blit(timer_text, (WIDTH//2 - timer_text.get_width()//2, 350))
    
    # Controls
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
        if client.game_data['left_count'] == 0 or client.game_data['right_count'] == 0:
            wait_text = font_medium.render("Menunggu pemain di kedua tim...", True, (255, 255, 255))
        else:
            wait_text = font_medium.render("Menunggu permainan dimulai...", True, (255, 255, 255))
        screen.blit(wait_text, (WIDTH//2 - wait_text.get_width()//2, 450))
    
    # Start game instruction
    start_text = font_small.render("Tekan SPACE untuk memulai permainan baru", True, (200, 200, 200))
    screen.blit(start_text, (WIDTH//2 - start_text.get_width()//2, 520))
    
    # Instructions
    control_text = font_small.render("Kontrol: A = Kiri, D = Kanan, SPACE = Mulai Game", True, (150, 150, 150))
    screen.blit(control_text, (WIDTH//2 - control_text.get_width()//2, 550))

def main():
    client = TugOfWarClient()
    
    if not client.connect_to_server():
        print("Failed to connect to server")
        return
    
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_a:
                    client.send_button_press('left')
                elif event.key == pygame.K_d:
                    client.send_button_press('right')
                elif event.key == pygame.K_SPACE:
                    client.send_start_game()
                elif event.key == pygame.K_ESCAPE:
                    running = False
        
        # Draw game
        draw_game(screen, client)
        pygame.display.flip()
        clock.tick(FPS)
    
    # Cleanup
    if client.connected:
        try:
            client.socket.close()
        except:
            pass
    
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()