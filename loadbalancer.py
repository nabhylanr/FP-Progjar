# load_balancer.py
import socket
import threading
import random

# List of backend servers (IP, Port)
backend_servers = [
    ('192.168.0.125', 55556),
    ('192.168.0.125', 55557),
    ('192.168.0.125', 55558)
]


def forward(client_socket, server_socket):
    try:
        while True:
            data = client_socket.recv(4096)
            if not data:
                break
            server_socket.sendall(data)
    except:
        pass
    finally:
        client_socket.close()
        server_socket.close()

def handle_client(client_socket):
    # Pilih backend server (random / round-robin bisa juga)
    backend = random.choice(backend_servers)
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.connect(backend)
        print(f"🔀 Forwarding client to {backend}")

        # Start bi-directional forwarding
        threading.Thread(target=forward, args=(client_socket, server_socket), daemon=True).start()
        threading.Thread(target=forward, args=(server_socket, client_socket), daemon=True).start()
    except Exception as e:
        print(f"❌ Failed to connect to backend {backend}: {e}")
        client_socket.close()

def start_load_balancer():
    lb_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    lb_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    lb_socket.bind(('0.0.0.0', 55555))  # Port for clients to connect
    lb_socket.listen(50)
    print("🚀 Load Balancer listening on port 55555...")

    while True:
        client_socket, addr = lb_socket.accept()
        print(f"🆕 New client from {addr}")
        threading.Thread(target=handle_client, args=(client_socket,), daemon=True).start()

if __name__ == "__main__":
    start_load_balancer()
