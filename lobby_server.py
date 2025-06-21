import socket
import threading
import json
import time
import random

# Backend game servers
GAME_SERVERS = [
    ('192.168.0.125', 55556),
    ('192.168.0.181', 55557), 
    ('192.168.0.31', 55558)
]

# Game rooms - each room assigned to one server
game_rooms = {}  # {room_id: {'server': tuple, 'players': [], 'status': 'waiting/playing', 'created': time}}
waiting_players = []  # List of players waiting for match
room_counter = 1

rooms_lock = threading.Lock()

def find_available_server():
    """Find server with least rooms"""
    server_load = {}
    for server in GAME_SERVERS:
        server_load[server] = 0
    
    # Count rooms per server
    for room in game_rooms.values():
        server = room['server']
        if server in server_load:
            server_load[server] += 1
    
    # Return server with least load
    return min(server_load.keys(), key=lambda x: server_load[x])

def create_game_room():
    """Create new game room"""
    global room_counter
    
    with rooms_lock:
        room_id = f"room_{room_counter}"
        room_counter += 1
        
        # Assign to least loaded server
        assigned_server = find_available_server()
        
        game_rooms[room_id] = {
            'server': assigned_server,
            'players': [],
            'status': 'waiting',
            'created': time.time(),
            'max_players': 4  # 2 per team
        }
        
        print(f"🎮 Created {room_id} on server {assigned_server}")
        return room_id

def add_player_to_room(room_id, player_id):
    """Add player to room"""
    with rooms_lock:
        if room_id in game_rooms:
            room = game_rooms[room_id]
            if len(room['players']) < room['max_players']:
                room['players'].append(player_id)
                print(f"👤 Added {player_id} to {room_id} (Server: {room['server']})")
                return True
    return False

def find_or_create_room():
    """Find available room or create new one"""
    with rooms_lock:
        # Find room with space
        for room_id, room in game_rooms.items():
            if room['status'] == 'waiting' and len(room['players']) < room['max_players']:
                return room_id
        
        # No available room, create new one
        return create_game_room()

def handle_client(client_socket, client_addr):
    """Handle lobby client"""
    client_id = f"{client_addr[0]}:{client_addr[1]}"
    print(f"🆕 Lobby client: {client_id}")
    
    try:
        # Send welcome message
        welcome = {
            'command': 'LOBBY_WELCOME',
            'message': 'Connected to game lobby'
        }
        send_message(client_socket, welcome)
        
        # Find room for player
        room_id = find_or_create_room()
        room = game_rooms[room_id]
        
        # Add player to room
        if add_player_to_room(room_id, client_id):
            # Send game server info
            game_info = {
                'command': 'JOIN_GAME_SERVER',
                'server_ip': room['server'][0],
                'server_port': room['server'][1],
                'room_id': room_id,
                'message': f'Join game server at {room["server"]}'
            }
            send_message(client_socket, game_info)
            
            # Send room status
            room_status = {
                'command': 'ROOM_STATUS',
                'room_id': room_id,
                'players_count': len(room['players']),
                'max_players': room['max_players'],
                'server': room['server']
            }
            send_message(client_socket, room_status)
            
        else:
            error_msg = {
                'command': 'LOBBY_ERROR',
                'message': 'Failed to join room'
            }
            send_message(client_socket, error_msg)
            
    except Exception as e:
        print(f"❌ Lobby error for {client_id}: {e}")
    finally:
        client_socket.close()

def send_message(socket, message):
    """Send JSON message"""
    try:
        msg = json.dumps(message) + '\n'
        socket.send(msg.encode())
    except Exception as e:
        print(f"❌ Send error: {e}")

def cleanup_old_rooms():
    """Clean up empty rooms"""
    while True:
        time.sleep(60)  # Check every minute
        
        with rooms_lock:
            current_time = time.time()
            rooms_to_remove = []
            
            for room_id, room in game_rooms.items():
                # Remove rooms older than 10 minutes with no players
                if len(room['players']) == 0 and (current_time - room['created']) > 600:
                    rooms_to_remove.append(room_id)
            
            for room_id in rooms_to_remove:
                del game_rooms[room_id]
                print(f"🗑️ Cleaned up old room: {room_id}")

def show_status():
    """Show lobby status"""
    while True:
        time.sleep(30)  # Show every 30 seconds
        
        with rooms_lock:
            print("\n" + "="*50)
            print("🏠 LOBBY STATUS")
            print("="*50)
            print(f"📊 Total Rooms: {len(game_rooms)}")
            
            for room_id, room in game_rooms.items():
                print(f"  {room_id}: {len(room['players'])}👤 -> {room['server']}")
            
            print("="*50 + "\n")

def start_lobby_server(port=55554):
    """Start lobby server"""
    
    # Start cleanup thread
    cleanup_thread = threading.Thread(target=cleanup_old_rooms, daemon=True)
    cleanup_thread.start()
    
    # Start status thread
    status_thread = threading.Thread(target=show_status, daemon=True) 
    status_thread.start()
    
    # Create lobby socket
    lobby_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    lobby_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        lobby_socket.bind(('0.0.0.0', port))
        lobby_socket.listen(50)
        
        print("=" * 60)
        print(f"🏠 LOBBY SERVER STARTED ON PORT {port}")
        print("=" * 60)
        print(f"📡 Listening on 0.0.0.0:{port}")
        print(f"🎯 Game servers: {GAME_SERVERS}")
        print("=" * 60)
        
        while True:
            try:
                client_socket, client_addr = lobby_socket.accept()
                
                # Handle client in new thread
                client_thread = threading.Thread(
                    target=handle_client,
                    args=(client_socket, client_addr),
                    daemon=True
                )
                client_thread.start()
                
            except Exception as e:
                print(f"❌ Error accepting client: {e}")
                
    except KeyboardInterrupt:
        print("\n🛑 Lobby server stopped by user")
    except Exception as e:
        print(f"❌ Lobby server error: {e}")
    finally:
        lobby_socket.close()

if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 55554
    start_lobby_server(port)