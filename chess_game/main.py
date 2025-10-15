import pygame
from chess_gui import ChessGUI

def main():
    pygame.init()
    pygame.display.set_caption("Game Cờ Vua - Python")

    game = ChessGUI()
    game.run()

    pygame.quit()

if __name__ == "__main__":
    main()
