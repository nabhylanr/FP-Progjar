import sys
import os.path
import uuid
import socket
import threading
import time
import json
import logging
from glob import glob
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

class GameState:
    def __init__(self):
        self.reset_game()
    
    def reset_game(self):
        """Reset game to initial state"""
        self.bar_position = 0    # -50 to +50
        self.timer = 60          # seconds
        self.game_active = True
        self.winner = None

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

class HttpServer:
    def __init__(self):
        self.sessions = {}
        self.types = {}
        self.types['.pdf'] = 'application/pdf'
        self.types['.jpg'] = 'image/jpeg'
        self.types['.txt'] = 'text/plain'
        self.types['.html'] = 'text/html'
        
    def response(self, kode=404, message='Not Found', messagebody=bytes(), headers={}):
        tanggal = datetime.now().strftime('%c')
        resp = []
        resp.append("HTTP/1.0 {} {}\r\n".format(kode, message))
        resp.append("Date: {}\r\n".format(tanggal))
        resp.append("Connection: close\r\n")
        resp.append("Server: myserver/1.0\r\n")
        resp.append("Content-Length: {}\r\n".format(len(messagebody)))
        for kk in headers:
            resp.append("{}:{}\r\n".format(kk, headers[kk]))
        resp.append("\r\n")
        response_headers = ''
        for i in resp:
            response_headers = "{}{}".format(response_headers, i)
        # menggabungkan resp menjadi satu string dan menggabungkan dengan messagebody yang berupa bytes
        # response harus berupa bytes
        # message body harus diubah dulu menjadi bytes
        if (type(messagebody) is not bytes):
            messagebody = messagebody.encode()
        response = response_headers.encode() + messagebody
        # response adalah bytes
        return response
        
    def proses(self, data):
        requests = data.split("\r\n")
        # print(requests)
        baris = requests[0]
        # print(baris)
        all_headers = [n for n in requests[1:] if n != '']
        j = baris.split(" ")
        try:
            method = j[0].upper().strip()
            if (method == 'GET'):
                object_address = j[1].strip()
                return self.http_get(object_address, all_headers)
            if (method == 'POST'):
                object_address = j[1].strip()
                return self.http_post(object_address, all_headers)
            else:
                return self.response(400, 'Bad Request', '', {})
        except IndexError:
            return self.response(400, 'Bad Request', '', {})
            
    def http_get(self, object_address, headers):
        files = glob('./*')
        # print(files)
        thedir = './'
        if (object_address == '/'):
            return self.response(200, 'OK', 'Ini Adalah web Server percobaan', dict())
        if (object_address == '/video'):
            return self.response(302, 'Found', '', dict(location='https://youtu.be/katoxpnTf04'))
        if (object_address == '/santai'):
            return self.response(200, 'OK', 'santai saja', dict())
        object_address = object_address[1:]
        if thedir + object_address not in files:
            return self.response(404, 'Not Found', '', {})
        fp = open(thedir + object_address, 'rb')  # rb => artinya adalah read dalam bentuk binary
        # harus membaca dalam bentuk byte dan BINARY
        isi = fp.read()
        
        fext = os.path.splitext(thedir + object_address)[1]
        content_type = self.types[fext]
        
        headers = {}
        headers['Content-type'] = content_type
        
        return self.response(200, 'OK', isi, headers)
        
    def http_post(self, object_address, headers):
        headers = {}
        isi = "kosong"
        return self.response(200, 'OK', isi, headers)

class CombinedServer:
    """Combined HTTP and Game Server"""
    
    def __init__(self, http_port=8080, game_port=55555):
        self.http_port = http_port
        self.game_port = game_port
        self.http_server = HttpServer()
        self.game_server = TugOfWarGameServer()
        self.running = True
        
    def process_game_client(self, connection, address):
        """Handle game client connection"""
        client_id = f"{address[0]}:{address[1]}:{int(time.time() * 1000) % 10000}"
        
        print(f"New game client connected: {client_id}")
        
        # Register client to game
        self.game_server.add_client(client_id, connection)
        
        rcv = ""
        try:
            while self.running:
                try:
                    # Set socket timeout to detect disconnections
                    connection.settimeout(30.0)
                    data = connection.recv(1024)
                    
                    if data:
                        # Decode bytes to string
                        d = data.decode()
                        rcv = rcv + d
                        
                        # Process complete messages (ended with \n)
                        while '\n' in rcv:
                            line, rcv = rcv.split('\n', 1)
                            if line.strip():
                                # Process game command
                                try:
                                    command = json.loads(line.strip())
                                    print(f"Command from {client_id}: {command}")
                                    self.game_server.handle_command(client_id, command)
                                except json.JSONDecodeError as e:
                                    logging.warning(f"Invalid JSON from {client_id}: {line} | Error: {e}")
                    else:
                        # Client disconnected
                        print(f"Game client {client_id} disconnected (no data)")
                        break
                        
                except socket.timeout:
                    # Send ping to check if client is still alive
                    try:
                        ping_msg = json.dumps({'command': 'PING'}) + '\n'
                        connection.send(ping_msg.encode())
                    except:
                        print(f"Game client {client_id} ping failed - disconnecting")
                        break
                        
                except OSError as e:
                    print(f"OSError from game client {client_id}: {e}")
                    break
                except Exception as e:
                    print(f"Unexpected error from game client {client_id}: {e}")
                    break
                    
        except Exception as e:
            logging.warning(f"Error handling game client {client_id}: {e}")
        finally:
            # Remove client from game
            print(f"Cleaning up game client {client_id}")
            self.game_server.remove_client(client_id)
            try:
                connection.close()
            except:
                pass
    
    def process_http_client(self, connection, address):
        """Handle HTTP client connection"""
        try:
            # Set timeout for HTTP requests
            connection.settimeout(10.0)
            
            # Receive HTTP request
            request_data = connection.recv(4096).decode()
            
            if request_data:
                print(f"HTTP request from {address}: {request_data.split()[0:3] if len(request_data.split()) >= 3 else request_data[:50]}")
                
                # Process HTTP request
                response = self.http_server.proses(request_data)
                
                # Send HTTP response
                connection.send(response)
            
        except Exception as e:
            logging.warning(f"Error handling HTTP client {address}: {e}")
        finally:
            try:
                connection.close()
            except:
                pass
    
    def start_game_server(self):
        """Start the game server"""
        game_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        game_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            game_socket.bind(('0.0.0.0', self.game_port))
            game_socket.listen(20)
            
            print(f"🎮 Game Server listening on port {self.game_port}")
            
            with ThreadPoolExecutor(max_workers=50) as executor:
                while self.running:
                    try:
                        connection, client_address = game_socket.accept()
                        # Submit game client handler to thread pool
                        executor.submit(self.process_game_client, connection, client_address)
                        
                    except Exception as e:
                        if self.running:
                            logging.error(f"Error accepting game connection: {e}")
                        
        except Exception as e:
            logging.error(f"Game server error: {e}")
        finally:
            game_socket.close()
    
    def start_http_server(self):
        """Start the HTTP server"""
        http_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        http_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            http_socket.bind(('0.0.0.0', self.http_port))
            http_socket.listen(20)
            
            print(f"🌐 HTTP Server listening on port {self.http_port}")
            
            with ThreadPoolExecutor(max_workers=50) as executor:
                while self.running:
                    try:
                        connection, client_address = http_socket.accept()
                        # Submit HTTP client handler to thread pool
                        executor.submit(self.process_http_client, connection, client_address)
                        
                    except Exception as e:
                        if self.running:
                            logging.error(f"Error accepting HTTP connection: {e}")
                        
        except Exception as e:
            logging.error(f"HTTP server error: {e}")
        finally:
            http_socket.close()
    
    def start(self):
        """Start both servers"""
        print("="*60)
        print("🚀 COMBINED HTTP & GAME SERVER STARTING")
        print("="*60)
        print(f"🌐 HTTP Server: http://localhost:{self.http_port}")
        print(f"🎮 Game Server: localhost:{self.game_port}")
        print("="*60)
        
        # Start game timer thread
        game_timer_thread = threading.Thread(target=self.game_server.game_loop, daemon=True)
        game_timer_thread.start()
        
        # Start HTTP server in separate thread
        http_thread = threading.Thread(target=self.start_http_server, daemon=True)
        http_thread.start()
        
        # Start game server in main thread
        self.start_game_server()
    
    def stop(self):
        """Stop both servers"""
        print("🛑 Stopping servers...")
        self.running = False
        self.game_server.running = False

def main():
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Create combined server
    server = CombinedServer(http_port=8080, game_port=55555)
    
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
        server.stop()
    except Exception as e:
        print(f"❌ Server error: {e}")
        server.stop()

if __name__ == "__main__":
    main()