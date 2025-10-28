import pygame
from chess_gui import ChessGUI
from chess_engine import ChessEngine

# Main function to run the chess game
def main():
    pygame.init() # khởi tạo pygame
    pygame.display.set_caption("Game Cờ Vua - Python Form Team 2 (nghèo nhưng cố gắng thông minh)") # tiêu đề cửa sổ
    game = ChessGUI() # khởi tạo giao diện cờ vua
    game.run() # chạy giao diện cờ vua

    pygame.quit() # thoát pygame

if __name__ == "__main__": # nếu chạy file này trực tiếp
    main() # gọi hàm main để chạy trò chơi
