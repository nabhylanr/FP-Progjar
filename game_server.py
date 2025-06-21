import threading
import time
import json
import logging
from game_state import GameState

class TugOfWarGameServer:
    def __init__(self):
        self.clients = {}  # {client_id: {'socket': socket, 'team': 'left'|'right'}}
        self.game_state = GameState()
        self.lock = threading.Lock()
        self.running = True
        
    def add_client(self, client_id, socket):
        """Add new client and assign to team"""
        with self.lock:
            # Debug: Print current clients before assignment
            print(f"Current clients before adding {client_id}:")
            for c_id, c_info in self.clients.items():
                print(f"  {c_id}: team={c_info.get('team')}")
            
            # Count players per team
            left_count = sum(1 for c in self.clients.values() if c.get('team') == 'left')
            right_count = sum(1 for c in self.clients.values() if c.get('team') == 'right')
            
            print(f"Team counts - Left: {left_count}, Right: {right_count}")
            
            # Assign to team with fewer players, or alternate if equal
            if left_count < right_count:
                team = 'left'
            elif right_count < left_count:
                team = 'right'
            else:
                # If equal, alternate based on total client count
                total_clients = len(self.clients)
                team = 'left' if total_clients % 2 == 0 else 'right'
            
            self.clients[client_id] = {
                'socket': socket,
                'team': team
            }
            
            print(f"Client {client_id} assigned to team {team}")
            
            # Send team assignment
            self.send_to_client(client_id, {
                'command': 'TEAM_ASSIGNED',
                'team': team
            })
            
            # Broadcast updated game state
            self.broadcast_game_state()
    
    def remove_client(self, client_id):
        """Remove client from game"""
        with self.lock:
            if client_id in self.clients:
                team = self.clients[client_id]['team']
                del self.clients[client_id]
                print(f"Client {client_id} left from team {team}")
                self.broadcast_game_state()
    
    def handle_command(self, client_id, command):
        """Handle command from client"""
        cmd_type = command.get('command')
        
        if cmd_type == 'PRESS_LEFT':
            self.handle_button_press(client_id, 'left')
        elif cmd_type == 'PRESS_RIGHT':
            self.handle_button_press(client_id, 'right')
        elif cmd_type == 'START_GAME':
            self.start_new_game()
        elif cmd_type == 'JOIN_GAME':
            # Handle explicit join request (optional)
            print(f"Client {client_id} requested to join game")
        else:
            logging.warning(f"Unknown command from {client_id}: {cmd_type}")
    
    def handle_button_press(self, client_id, direction):
        """Handle button press from client"""
        with self.lock:
            if not self.game_state.game_active:
                print(f"Button press ignored - game not active")
                return
                
            # Get client info
            client_info = self.clients.get(client_id)
            if not client_info:
                print(f"Button press from unknown client: {client_id}")
                return
                
            client_team = client_info.get('team')
            
            # Verify client team matches button direction
            if (direction == 'left' and client_team == 'left') or \
               (direction == 'right' and client_team == 'right'):
                
                # Update bar position
                old_position = self.game_state.bar_position
                if direction == 'left':
                    self.game_state.bar_position -= 1
                else:
                    self.game_state.bar_position += 1
                
                # Keep bar in bounds
                self.game_state.bar_position = max(-50, min(50, self.game_state.bar_position))
                
                print(f"Button press from {client_id} (team {client_team}): {old_position} -> {self.game_state.bar_position}")
                
                # Check win condition
                if self.game_state.bar_position <= -50:
                    self.end_game('LEFT')
                elif self.game_state.bar_position >= 50:
                    self.end_game('RIGHT')
            else:
                print(f"Invalid button press: client {client_id} (team {client_team}) pressed {direction}")
    
    def start_new_game(self):
        """Start new game round"""
        with self.lock:
            # Check if we have at least one player on each team
            left_count = sum(1 for c in self.clients.values() if c.get('team') == 'left')
            right_count = sum(1 for c in self.clients.values() if c.get('team') == 'right')
            
            if left_count == 0 or right_count == 0:
                print(f"Cannot start game - need players on both teams (Left: {left_count}, Right: {right_count})")
                self.broadcast_message({
                    'command': 'GAME_ERROR',
                    'message': 'Butuh pemain di kedua tim untuk memulai!'
                })
                return
            
            self.game_state.reset_game()
            print(f"New game started! Teams - Left: {left_count}, Right: {right_count}")
            self.broadcast_game_state()
    
    def end_game(self, winner):
        """End current game"""
        self.game_state.game_active = False
        self.game_state.winner = winner
        
        self.broadcast_message({
            'command': 'GAME_END',
            'winner': winner,
            'bar_position': self.game_state.bar_position
        })
        
        print(f"Game ended! Winner: {winner}, Final position: {self.game_state.bar_position}")
        
        # Auto-restart after 5 seconds
        threading.Timer(5.0, self.start_new_game).start()
    
    def send_to_client(self, client_id, message):
        """Send message to specific client"""
        try:
            if client_id in self.clients:
                socket_obj = self.clients[client_id]['socket']
                msg = json.dumps(message) + '\n'
                socket_obj.send(msg.encode())
        except Exception as e:
            logging.warning(f"Failed to send to {client_id}: {e}")
            # Remove dead client
            self.remove_client(client_id)
    
    def broadcast_message(self, message):
        """Broadcast message to all clients"""
        msg = json.dumps(message) + '\n'
        dead_clients = []
        
        for client_id, client_info in self.clients.items():
            try:
                client_info['socket'].send(msg.encode())
            except Exception as e:
                logging.warning(f"Failed to broadcast to {client_id}: {e}")
                dead_clients.append(client_id)
        
        # Remove dead clients
        for client_id in dead_clients:
            self.remove_client(client_id)
    
    def broadcast_game_state(self):
        """Broadcast current game state to all clients"""
        left_count = sum(1 for c in self.clients.values() if c.get('team') == 'left')
        right_count = sum(1 for c in self.clients.values() if c.get('team') == 'right')
        
        state_msg = {
            'command': 'GAME_UPDATE',
            'bar_position': self.game_state.bar_position,
            'timer': self.game_state.timer,
            'left_count': left_count,
            'right_count': right_count,
            'game_active': self.game_state.game_active,
            'winner': self.game_state.winner
        }
        
        print(f"Broadcasting game state - Left: {left_count}, Right: {right_count}, Position: {self.game_state.bar_position}")
        self.broadcast_message(state_msg)
    
    def game_loop(self):
        """Main game loop - runs in separate thread"""
        while self.running:
            time.sleep(1)  # Update every second
            
            with self.lock:
                if self.game_state.game_active and self.game_state.timer > 0:
                    self.game_state.timer -= 1
                    
                    # Check time up
                    if self.game_state.timer <= 0:
                        if self.game_state.bar_position < 0:
                            winner = 'LEFT'
                        elif self.game_state.bar_position > 0:
                            winner = 'RIGHT'
                        else:
                            winner = 'DRAW'
                        self.end_game(winner)
                
                # Broadcast state update every 5 seconds when game is active
                if self.game_state.game_active:
                    self.broadcast_game_state()