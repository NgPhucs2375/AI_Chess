class GameState:
    def __init__(self):
        self.board = [row[:] for row in starting_board]
        self.white_to_move = True
        self.move_log = []
