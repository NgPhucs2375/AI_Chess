class ChessEngine:
    def __init__(self):
        # Khởi tạo bàn cờ 8x8, các quân cờ ban đầu
        self.board = self.create_starting_board()

    def create_starting_board(self):
        # Có thể dùng thư viện 'chess' để dễ hơn
        import chess
        return chess.Board()

    def print_board(self):
        print(self.board)
