class GameState:
    def __init__(self):
        self.reset_game()
    
    def reset_game(self):
        """Reset game to initial state"""
        self.bar_position = 0    # -50 to +50
        self.timer = 60          # seconds
        self.game_active = True
        self.winner = None