import pygame

WIDTH, HEIGHT = 640, 640
ROWS, COLS = 8, 8
SQ_SIZE = WIDTH // COLS
WHITE = (255, 255, 255)
GRAY = (128, 128, 128)

class ChessGUI:
    def __init__(self):
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.running = True

    def draw_board(self):
        """Vẽ bàn cờ 8x8"""
        colors = [WHITE, GRAY]
        for row in range(ROWS):
            for col in range(COLS):
                color = colors[(row + col) % 2]
                pygame.draw.rect(self.screen, color,
                                 pygame.Rect(col * SQ_SIZE, row * SQ_SIZE, SQ_SIZE, SQ_SIZE))

    def run(self):
        """Vòng lặp chính"""
        clock = pygame.time.Clock()
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False

            self.draw_board()
            pygame.display.flip()
            clock.tick(30)
