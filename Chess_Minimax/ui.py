import pygame
import sys

# --- Cấu hình cơ bản ---
WIDTH, HEIGHT = 740, 740
ROWS, COLS = 8, 8
SQUARE_SIZE = WIDTH // COLS

# --- Màu sắc ---
WHITE = (240, 240, 210)   # ô sáng
BROWN = (181, 136, 99)   # ô tối
HIGHLIGHT = (255, 223, 0) 

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Chess - UI")
clock = pygame.time.Clock()

# --- hình ảnh quân cờ ---
pieces = {}
piece_types = [
    "wp", "wr", "wn", "wb", "wq", "wk",
    "bp", "br", "bn", "bb", "bq", "bk"
]

for piece in piece_types:
    path = f"images/{piece}.png"
    print("Đang load:", path)
    image = pygame.image.load(path)
    image = pygame.transform.scale(image, (SQUARE_SIZE, SQUARE_SIZE))
    pieces[piece] = image

# --- Bố trí bàn cờ ban đầu ---
starting_board = [
    ["br", "bn", "bb", "bq", "bk", "bb", "bn", "br"],
    ["bp"] * 8,
    [""] * 8,
    [""] * 8,
    [""] * 8,
    [""] * 8,
    ["wp"] * 8,
    ["wr", "wn", "wb", "wq", "wk", "wb", "wn", "wr"]
]

# --- Hàm vẽ bàn cờ ---
def draw_board(selected_square=None):
    for row in range(ROWS):
        for col in range(COLS):
            color = WHITE if (row + col) % 2 == 0 else BROWN
            rect = pygame.Rect(col * SQUARE_SIZE, row * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE)
            pygame.draw.rect(screen, color, rect)

            # Nếu ô được chọn thì tô màu nổi bật
            if selected_square == (row, col):
                pygame.draw.rect(screen, HIGHLIGHT, rect)


# --- Hàm vẽ quân cờ ---
def draw_pieces(board):
    for row in range(ROWS):
        for col in range(COLS):
            piece = board[row][col]
            if piece != "":
                screen.blit(pieces[piece], (col * SQUARE_SIZE, row * SQUARE_SIZE))
# --- Vòng lặp chính ---
def main():
    selected_square = None
    board = [row[:] for row in starting_board]
    running = True

    while running:
        draw_board(selected_square)
        draw_pieces(board)
        pygame.display.flip()
        clock.tick(60)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.MOUSEBUTTONDOWN:
                x, y = pygame.mouse.get_pos()
                row = y // SQUARE_SIZE
                col = x // SQUARE_SIZE
                selected_square = (row, col)
                print(f"Ô được chọn: {selected_square}")

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
