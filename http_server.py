import sys
import os.path
import uuid
import socket
import threading
import time
import json
from glob import glob
from datetime import datetime

class HttpServer:
    def __init__(self, game_server_ref=None):
        self.sessions = {}
        self.types = {}
        self.types['.pdf'] = 'application/pdf'
        self.types['.jpg'] = 'image/jpeg'
        self.types['.txt'] = 'text/plain'
        self.types['.html'] = 'text/html'
        self.types['.css'] = 'text/css'
        self.types['.js'] = 'application/javascript'
        self.types['.png'] = 'image/png'
        
        # Reference to game server untuk mendapatkan status game
        self.game_server = game_server_ref
        
    def response(self, kode=404, message='Not Found', messagebody=bytes(), headers={}):
        tanggal = datetime.now().strftime('%c')
        resp = []
        resp.append("HTTP/1.0 {} {}\r\n".format(kode, message))
        resp.append("Date: {}\r\n".format(tanggal))
        resp.append("Connection: close\r\n")
        resp.append("Server: tugofwar-webserver/1.0\r\n")
        resp.append("Content-Length: {}\r\n".format(len(messagebody)))
        for kk in headers:
            resp.append("{}:{}\r\n".format(kk, headers[kk]))
        resp.append("\r\n")
        response_headers = ''
        for i in resp:
            response_headers = "{}{}".format(response_headers, i)
        
        if (type(messagebody) is not bytes):
            messagebody = messagebody.encode()
        response = response_headers.encode() + messagebody
        return response
        
    def proses(self, data):
        requests = data.split("\r\n")
        baris = requests[0]
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
    
    def get_game_status(self):
        """Mendapatkan status game dari game server"""
        if not self.game_server:
            return {
                'connected': False,
                'error': 'Game server not connected'
            }
        
        try:
            # Thread-safe access to game state
            with self.game_server.lock:
                left_count = sum(1 for c in self.game_server.clients.values() if c.get('team') == 'left')
                right_count = sum(1 for c in self.game_server.clients.values() if c.get('team') == 'right')
                
                # Get actual game state values
                bar_position = self.game_server.game_state.bar_position
                timer = self.game_server.game_state.timer
                game_active = self.game_server.game_state.game_active
                winner = self.game_server.game_state.winner
                
                return {
                    'connected': True,
                    'bar_position': bar_position,
                    'timer': timer,
                    'left_count': left_count,
                    'right_count': right_count,
                    'game_active': game_active,
                    'winner': winner,
                    'total_clients': len(self.game_server.clients),
                    'timestamp': time.time()  # Add timestamp for debugging
                }
        except Exception as e:
            return {
                'connected': False,
                'error': str(e)
            }
    
    def generate_game_dashboard(self):
        """Generate HTML dashboard untuk game status"""
        status = self.get_game_status()
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Tug of War - Game Dashboard</title>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="1">
    <style>
        body {{ 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            margin: 0;
            padding: 20px;
            min-height: 100vh;
        }}
        .container {{ 
            max-width: 900px; 
            margin: 0 auto; 
            background: rgba(255,255,255,0.1);
            padding: 30px;
            border-radius: 15px;
            backdrop-filter: blur(10px);
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
        }}
        .title {{ 
            text-align: center; 
            font-size: 2.5em;
            margin-bottom: 30px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
            background: linear-gradient(45deg, #ffd700, #ffed4a);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        .status-box {{ 
            background: rgba(255,255,255,0.2); 
            padding: 20px; 
            margin: 15px 0; 
            border-radius: 10px;
            border-left: 5px solid #ffd700;
            transition: all 0.3s ease;
        }}
        .status-box:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        }}
        .teams {{ 
            display: flex; 
            justify-content: space-between; 
            margin: 20px 0;
            gap: 20px;
        }}
        .team {{ 
            background: rgba(255,255,255,0.2); 
            padding: 25px; 
            border-radius: 15px; 
            text-align: center;
            flex: 1;
            transition: all 0.3s ease;
        }}
        .team:hover {{
            transform: scale(1.02);
        }}
        .team.left {{ 
            border-top: 5px solid #ff6b6b; 
            background: linear-gradient(135deg, rgba(255,107,107,0.3), rgba(255,107,107,0.1));
        }}
        .team.right {{ 
            border-top: 5px solid #4ecdc4; 
            background: linear-gradient(135deg, rgba(78,205,196,0.3), rgba(78,205,196,0.1));
        }}
        .team h3 {{
            margin: 0 0 15px 0;
            font-size: 1.4em;
        }}
        .team .count {{
            font-size: 3em;
            font-weight: bold;
            margin: 10px 0;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
        }}
        .progress-container {{
            margin: 30px 0;
            text-align: center;
        }}
        .progress-bar {{ 
            width: 100%; 
            height: 50px; 
            background: linear-gradient(90deg, #333 0%, #555 50%, #333 100%); 
            border-radius: 25px; 
            margin: 20px 0;
            position: relative;
            overflow: hidden;
            border: 3px solid rgba(255,255,255,0.3);
        }}
        .progress-zones {{
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            display: flex;
        }}
        .zone-left {{
            flex: 1;
            background: linear-gradient(90deg, rgba(255,107,107,0.6), rgba(255,107,107,0.2));
        }}
        .zone-right {{
            flex: 1;
            background: linear-gradient(90deg, rgba(78,205,196,0.2), rgba(78,205,196,0.6));
        }}
        .progress-indicator {{
            position: absolute;
            top: 50%;
            transform: translateY(-50%);
            width: 30px;
            height: 30px;
            background: radial-gradient(circle, #ffd700, #ffed4a);
            border-radius: 50%;
            border: 4px solid white;
            box-shadow: 0 0 20px rgba(255,215,0,0.8), 0 0 40px rgba(255,215,0,0.4);
            z-index: 10;
            transition: left 0.3s ease;
        }}
        .center-line {{
            position: absolute;
            top: 0;
            left: 50%;
            width: 4px;
            height: 100%;
            background: rgba(255,255,255,0.8);
            transform: translateX(-50%);
            z-index: 5;
        }}
        .timer {{ 
            font-size: 3em; 
            text-align: center; 
            margin: 20px 0;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
            font-weight: bold;
        }}
        .timer.warning {{
            color: #ff6b6b;
            animation: pulse 1s infinite;
        }}
        .winner {{ 
            font-size: 3em; 
            text-align: center; 
            color: #ffd700;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.8);
            animation: bounce 1s infinite;
            margin: 30px 0;
        }}
        .game-info {{
            display: flex;
            justify-content: space-between;
            margin: 20px 0;
            flex-wrap: wrap;
        }}
        .info-item {{
            background: rgba(255,255,255,0.1);
            padding: 15px;
            border-radius: 10px;
            margin: 5px;
            flex: 1;
            min-width: 150px;
            text-align: center;
        }}
        .error {{ 
            background: rgba(255,0,0,0.3); 
            border-left-color: #ff0000;
        }}
        .debug {{
            background: rgba(0,0,0,0.2);
            padding: 10px;
            border-radius: 5px;
            font-family: monospace;
            font-size: 0.8em;
            margin-top: 20px;
        }}
        @keyframes pulse {{
            0% {{ transform: scale(1); }}
            50% {{ transform: scale(1.05); }}
            100% {{ transform: scale(1); }}
        }}
        @keyframes bounce {{
            0%, 20%, 50%, 80%, 100% {{ transform: translateY(0); }}
            40% {{ transform: translateY(-10px); }}
            60% {{ transform: translateY(-5px); }}
        }}
        .position-display {{
            font-size: 1.2em;
            margin: 10px 0;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1 class="title">🎮 TUG OF WAR DASHBOARD</h1>
        """
        
        if not status['connected']:
            html += f"""
        <div class="status-box error">
            <h2>❌ Game Server Disconnected</h2>
            <p>Error: {status.get('error', 'Unknown error')}</p>
        </div>
        """
        else:
            # Game status
            game_status = "🟢 GAME ACTIVE" if status['game_active'] else "🔴 WAITING FOR PLAYERS"
            html += f"""
        <div class="status-box">
            <h2>Status: {game_status}</h2>
            <div class="game-info">
                <div class="info-item">
                    <strong>Total Players</strong><br>
                    {status['total_clients']}
                </div>
                <div class="info-item">
                    <strong>Game Timer</strong><br>
                    {status['timer']}s
                </div>
                <div class="info-item">
                    <strong>Bar Position</strong><br>
                    {status['bar_position']}
                </div>
            </div>
        </div>
        
        <div class="teams">
            <div class="team left">
                <h3>🔴 LEFT TEAM</h3>
                <div class="count">{status['left_count']}</div>
                <p>Players</p>
            </div>
            <div class="team right">
                <h3>🔵 RIGHT TEAM</h3>
                <div class="count">{status['right_count']}</div>
                <p>Players</p>
            </div>
        </div>
        
        <div class="progress-container">
            <div class="progress-bar">
                <div class="progress-zones">
                    <div class="zone-left"></div>
                    <div class="zone-right"></div>
                </div>
                <div class="center-line"></div>
                """
            
            # Calculate indicator position (bar_position: -50 to +50, convert to 0-100%)
            # Fix: Ensure proper calculation
            pos_percent = ((status['bar_position'] + 50) / 100) * 100
            pos_percent = max(2, min(98, pos_percent))  # Keep indicator visible (2-98%)
            
            html += f'<div class="progress-indicator" style="left: {pos_percent}%;"></div>'
            html += '</div>'
            
            html += f"""
            <div class="position-display">
                Position: {status['bar_position']} / 50
                {' (LEFT WINNING)' if status['bar_position'] < -25 else ' (RIGHT WINNING)' if status['bar_position'] > 25 else ' (BALANCED)'}
            </div>
        </div>
            """
            
            # Timer display
            timer_class = "timer warning" if status['timer'] <= 10 else "timer"
            
            # Winner or game status
            if status['winner']:
                winner_text = status['winner']
                if winner_text == 'DRAW':
                    html += f'<div class="winner">🤝 IT\'S A DRAW! 🤝</div>'
                else:
                    html += f'<div class="winner">🏆 TEAM {winner_text} WINS! 🏆</div>'
            elif status['game_active']:
                html += f'<div class="{timer_class}">⏰ {status["timer"]} seconds remaining</div>'
            else:
                if status['left_count'] == 0 and status['right_count'] == 0:
                    html += '<p style="text-align: center; font-size: 1.5em;">⏳ Waiting for players to join...</p>'
                elif status['left_count'] == 0 or status['right_count'] == 0:
                    html += '<p style="text-align: center; font-size: 1.5em;">⏳ Waiting for players on both teams...</p>'
                else:
                    html += '<p style="text-align: center; font-size: 1.5em;">⏳ Ready to start! Press SPACE in game client.</p>'
        
        # Debug information
        html += f"""
        <div class="debug">
            <strong>Debug Info:</strong><br>
            Connected: {status['connected']}<br>
            Timestamp: {status.get('timestamp', 'N/A')}<br>
            Raw Position: {status.get('bar_position', 'N/A')}<br>
            Calculated Position: {pos_percent if status['connected'] else 'N/A'}%<br>
            Game Active: {status.get('game_active', 'N/A')}<br>
            Winner: {status.get('winner', 'None')}
        </div>
        """
        
        html += """
        <div style="text-align: center; margin-top: 30px;">
            <h3>🎮 How to Play:</h3>
            <p>1. Download and run the game client</p>
            <p>2. Connect to the server</p>
            <p>3. Use <strong>A</strong> (Left Team) or <strong>D</strong> (Right Team) keys to pull the rope!</p>
            <p>4. Press <strong>SPACE</strong> to start a new game</p>
            <p style="margin-top: 20px; opacity: 0.7; font-size: 0.9em;">
                Dashboard auto-refreshes every 1 second
            </p>
        </div>
    </div>
</body>
</html>"""
        return html
    
    def http_get(self, object_address, headers):
        files = glob('./*')
        thedir = './'
        
        # Route untuk dashboard game
        if object_address == '/':
            return self.response(200, 'OK', 'Tug of War Game Server - Visit /dashboard for game status', dict())
        
        if object_address == '/dashboard':
            dashboard_html = self.generate_game_dashboard()
            return self.response(200, 'OK', dashboard_html, {'Content-type': 'text/html'})
        
        if object_address == '/api/status':
            status = self.get_game_status()
            return self.response(200, 'OK', json.dumps(status, indent=2), {'Content-type': 'application/json'})
        
        if object_address == '/video':
            return self.response(302, 'Found', '', dict(location='https://youtu.be/katoxpnTf04'))
        
        if object_address == '/santai':
            return self.response(200, 'OK', 'santai saja', dict())
        
        # Handle file requests
        object_address = object_address[1:]
        if thedir + object_address not in files:
            return self.response(404, 'Not Found', '', {})
        
        fp = open(thedir + object_address, 'rb')
        isi = fp.read()
        fp.close()
        
        fext = os.path.splitext(thedir + object_address)[1]
        content_type = self.types.get(fext, 'application/octet-stream')
        
        headers = {}
        headers['Content-type'] = content_type
        
        return self.response(200, 'OK', isi, headers)
    
    def http_post(self, object_address, headers):
        headers = {}
        isi = "POST method not implemented for this endpoint"
        return self.response(501, 'Not Implemented', isi, headers)


class WebServerThread:
    def __init__(self, game_server_ref, port=8080):
        self.game_server = game_server_ref
        self.port = port
        self.running = False
        
    def start(self):
        """Start web server in separate thread"""
        self.running = True
        thread = threading.Thread(target=self._run_server, daemon=True)
        thread.start()
        print(f"🌐 Web dashboard started at http://localhost:{self.port}/dashboard")
        return thread
    
    def _run_server(self):
        """Run the HTTP server"""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            server_socket.bind(('0.0.0.0', self.port))
            server_socket.listen(5)
            
            http_server = HttpServer(self.game_server)
            
            while self.running:
                try:
                    client_socket, addr = server_socket.accept()
                    client_socket.settimeout(10.0)
                    
                    # Handle HTTP request
                    data = client_socket.recv(1024).decode()
                    if data:
                        response = http_server.proses(data)
                        client_socket.send(response)
                    
                    client_socket.close()
                    
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"Web server error: {e}")
                    
        except Exception as e:
            print(f"Failed to start web server: {e}")
        finally:
            server_socket.close()
            print("Web server stopped")


if __name__ == "__main__":
    # Test standalone
    httpserver = HttpServer()
    d = httpserver.proses('GET /dashboard HTTP/1.0')
    print(d)