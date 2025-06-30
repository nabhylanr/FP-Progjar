from socket import *
import socket
import time
import sys
import logging
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from game_server import TugOfWarGameServer
from http_server import WebServerThread  # Import web server

# Instance global game server
game_server = TugOfWarGameServer()

def ProcessTheClient(connection, address):
    """
    Handle client connection for Tug of War game
    """
    client_id = f"{address[0]}:{address[1]}:{int(time.time() * 1000) % 10000}"  # More unique ID
    
    print(f"New client connected: {client_id}")
    
    # Register client to game
    game_server.add_client(client_id, connection)
    
    rcv = ""
    try:
        while True:
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
                                game_server.handle_command(client_id, command)
                            except json.JSONDecodeError as e:
                                logging.warning(f"Invalid JSON from {client_id}: {line} | Error: {e}")
                else:
                    # Client disconnected
                    print(f"Client {client_id} disconnected (no data)")
                    break
                    
            except socket.timeout:
                # Send ping to check if client is still alive
                try:
                    ping_msg = json.dumps({'command': 'PING'}) + '\n'
                    connection.send(ping_msg.encode())
                except:
                    print(f"Client {client_id} ping failed - disconnecting")
                    break
                    
            except OSError as e:
                print(f"OSError from {client_id}: {e}")
                break
            except Exception as e:
                print(f"Unexpected error from {client_id}: {e}")
                break
                
    except Exception as e:
        logging.warning(f"Error handling client {client_id}: {e}")
    finally:
        # Remove client from game
        print(f"Cleaning up client {client_id}")
        game_server.remove_client(client_id)
        try:
            connection.close()
        except:
            pass

def Server():
    """
    Main server function
    """
    active_clients = []
    my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        my_socket.bind(('0.0.0.0', 55555))
        my_socket.listen(20)  # Increased backlog
        
        # Start game timer thread
        game_timer_thread = threading.Thread(target=game_server.game_loop, daemon=True)
        game_timer_thread.start()
        
        # Start web server untuk dashboard
        web_server = WebServerThread(game_server, port=8080)
        web_server.start()
        
        print("="*60)
        print("🎮 TUG OF WAR GAME SERVER STARTED")
        print("="*60)
        print(f"📡 Game Server: localhost:55555")
        print(f"🌐 Web Dashboard: http://localhost:8080/dashboard")
        print(f"📊 API Status: http://localhost:8080/api/status")
        print("="*60)
        print("📋 Connect game clients to: localhost:55555")
        print("🖥️  View game status at: http://localhost:8080/dashboard")
        print("="*60)
        
        with ThreadPoolExecutor(max_workers=50) as executor:  # Increased max workers
            client_counter = 0
            
            while True:
                try:
                    connection, client_address = my_socket.accept()
                    client_counter += 1
                    
                    print(f"🆕 Client #{client_counter} connected from {client_address}")
                    
                    # Submit client handler to thread pool
                    future = executor.submit(ProcessTheClient, connection, client_address)
                    active_clients.append(future)
                    
                    # Clean up finished futures
                    active_clients = [f for f in active_clients if f.running()]
                    
                    # Show statistics
                    active_count = len(active_clients)
                    left_count = len([c for c in game_server.clients.values() if c.get('team') == 'left'])
                    right_count = len([c for c in game_server.clients.values() if c.get('team') == 'right'])
                    
                    print(f"📊 Active connections: {active_count} | Left team: {left_count} | Right team: {right_count}")
                    
                except Exception as e:
                    logging.error(f"Error accepting connection: {e}")
                    
    except Exception as e:
        logging.error(f"Server error: {e}")
    finally:
        print("🛑 Server shutting down...")
        game_server.running = False
        if 'web_server' in locals():
            web_server.running = False
        my_socket.close()

def main():
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    try:
        Server()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Server error: {e}")

if __name__ == "__main__":
    main()