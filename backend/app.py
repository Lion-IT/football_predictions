import sys
import os
# import socket

# Add the necessary directories to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask
from routes.matches import matches_blueprint
from routes.team import team_blueprint
from routes.player import player_blueprint

app = Flask(__name__)

# Rejestracja blueprintów
app.register_blueprint(matches_blueprint, url_prefix='/api/matches')
app.register_blueprint(team_blueprint, url_prefix='/api/team')
app.register_blueprint(player_blueprint, url_prefix='/api/player')

# def find_free_port():
#     with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
#         s.bind(('', 0))
#         return s.getsockname()[1]

if __name__ == '__main__':
    # port = find_free_port()
    # print(f"Starting server on port {port}")
    app.run(debug=True, host='0.0.0.0', port=53502)