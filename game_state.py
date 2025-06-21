import time

class GameState:
    def __init__(self):
        self.bar_position = 0  # -50 to +50, -50 = left wins, +50 = right wins
        self.timer = 60  # Game duration in seconds
        self.game_active = False
        self.winner = None
        self.start_time = None
        
    def reset_game(self):
        """Reset game state for new round"""
        self.bar_position = 0
        self.timer = 60
        self.game_active = True
        self.winner = None
        self.start_time = time.time()
        print("Game state reset - new game started!")
        
    def update_timer(self):
        """Update timer based on elapsed time"""
        if self.game_active and self.start_time:
            elapsed = time.time() - self.start_time
            self.timer = max(0, 60 - int(elapsed))
            return self.timer
        return self.timer