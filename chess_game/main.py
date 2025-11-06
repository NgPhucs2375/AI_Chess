import pygame
# Chỉ cần import ChessGUI
from chess_gui import ChessGUI 

# Main function to run the chess game
def main():
    """
    Initializes Pygame, sets up the game window, creates and runs the ChessGUI instance.
    """
    # Pygame.init() và set_caption đã được chuyển vào ChessGUI.__init__()
    
    # 3. Khởi tạo giao diện cờ vua 
    game = ChessGUI() 

    # 4. Chạy vòng lặp chính của trò chơi (sẽ chứa vòng lặp chính và pygame.quit())
    game.run() 

if __name__ == "__main__": 
    # Đảm bảo hàm main() chỉ được gọi khi file này được chạy trực tiếp
    main()