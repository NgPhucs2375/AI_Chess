import pygame
import os
import chess
from chess_engine import ChessEngine

WIDTH, HEIGHT = 640, 640
ROWS, COLS = 8, 8
SQ_SIZE = WIDTH // COLS
WHITE = (255, 255, 255)
GRAY = (128, 128, 128)

# Tải hình ảnh quân cờ
# chu Hoa la trang, chu thuong la den
piece_images = {
    'P' : pygame.image.load(os.path.join(os.path.dirname(__file__), 'images', 'wp.png')),
    'p' : pygame.image.load(os.path.join(os.path.dirname(__file__), 'images', 'bp.png')),
    'N' : pygame.image.load(os.path.join(os.path.dirname(__file__), 'images', 'wn.png')),
    'n' : pygame.image.load(os.path.join(os.path.dirname(__file__), 'images', 'bn.png')),
    'B' : pygame.image.load(os.path.join(os.path.dirname(__file__), 'images', 'wb.png')),
    'b' : pygame.image.load(os.path.join(os.path.dirname(__file__), 'images', 'bb.png')),
    'R' : pygame.image.load(os.path.join(os.path.dirname(__file__), 'images', 'wr.png')),
    'r' : pygame.image.load(os.path.join(os.path.dirname(__file__), 'images', 'br.png')),
    'Q' : pygame.image.load(os.path.join(os.path.dirname(__file__), 'images', 'wq.png')),
    'q' : pygame.image.load(os.path.join(os.path.dirname(__file__), 'images', 'bq.png')),
    'K' : pygame.image.load(os.path.join(os.path.dirname(__file__), 'images', 'wk.png')),
    'k' : pygame.image.load(os.path.join(os.path.dirname(__file__), 'images', 'bk.png')),
}

class ChessGUI: # class giao dien nguoi dung
    def __init__(self): # ham khoi tao
        """Khởi tạo giao diện cờ vua"""
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT)) # tạo cửa sổ pygame với kích thước WIDTH x HEIGHT
        self.running = True # biến chạy vòng lặp chính
        self.engine = ChessEngine() # Khởi tạo engine cờ vua 
        self.selected_square = None # oo ô vuông được chọn
        self.selected_square = None # o vuong duoc chon
        self.legal_moves = []   # danh sach nuoc di hop le cho o duoc chon

           # --- phong quân ---
        self.promotion_pending = None   # (from, to)
        self.promotion_rects = []

        
        
        base_path = os.path.dirname(__file__) # đường dẫn cơ sở đến thư mục hiện tại
        board_path = os.path.join(base_path,"img","board2.png") # đường dẫn đến hình ảnh ô trắng
        self.board_texture = pygame.transform.scale(pygame.image.load(board_path).convert(),(WIDTH, HEIGHT)) # tải và thay đổi kích thước hình ảnh bàn cờ

    def draw_board(self): # ham ve ban co
        """Vẽ bàn cờ 8x8"""
        self.screen.blit(self.board_texture,(0,0)) # ve ban co len
        
          # Highlight ô được chọn
        if self.selected_square is not None:
            row = 7 - chess.square_rank(self.selected_square)
            col = chess.square_file(self.selected_square)
            rect = pygame.Rect(col * SQ_SIZE, row * SQ_SIZE, SQ_SIZE, SQ_SIZE)
            pygame.draw.rect(self.screen, (255, 255, 0, 100), rect, 4)

        # Highlight các nước đi hợp lệ
        for move_square in self.legal_moves:
            row = 7 - chess.square_rank(move_square)
            col = chess.square_file(move_square)
            center = (col * SQ_SIZE + SQ_SIZE // 2, row * SQ_SIZE + SQ_SIZE // 2)
            pygame.draw.circle(self.screen, (0, 255, 0, 100), center, 10)
        
    def draw_pieces(self): # ham ve quan co
        """Ve cac quan co len ban co"""
        board = self.engine.board # lay ban co tu engine
        bilit = self.screen.blit # gan ham bl
        scale = pygame.transform.scale # gan ham scale
        
        for square, piece in board.piece_map().items(): # duyet qua cac o co va quan co tren do
            symbol = piece.symbol() # lay ky hieu quan co
            row = 7 - chess.square_rank(square) # tinh hang
            col = chess.square_file(square) # tinh cot
            image = piece_images[symbol] # lay hinh anh quan co tu dictionary
            
            # scale hinh anh quan co ve kich thuoc o co
            if image.get_size() != (SQ_SIZE, SQ_SIZE):
                image = scale(image, (SQ_SIZE, SQ_SIZE))
            bilit(image, (col * SQ_SIZE, row * SQ_SIZE)) # ve quan co len ban co

    def handle_mouse_click(self, pos):
        if self.promotion_pending is not None:
            x, y = pos
            for piece_type, rect in self.promotion_rects:
                if rect.collidepoint(x, y):
                    from_sq, to_sq = self.promotion_pending
                    move = chess.Move(from_sq, to_sq, promotion=piece_type)
                    if move in self.engine.board.legal_moves:
                        self.engine.board.push(move)
                    self.promotion_pending = None
                    self.promotion_rects = []
                    return
                 # click ngoài => hủy chọn
            self.promotion_pending = None
            self.promotion_rects = []
            return
        
        col = pos[0] // SQ_SIZE
        row = 7 - (pos[1] // SQ_SIZE)
        square = chess.square(col, row)

        if self.selected_square == square:
            # Bỏ chọn nếu click lại vào chính ô đó
            self.selected_square = None
            self.legal_moves = []
            return

        piece = self.engine.board.piece_at(square)
        if piece and piece.color == self.engine.board.turn:
            # Chọn quân cờ, hiển thị nước đi hợp lệ
            self.selected_square = square
            self.legal_moves = [
                move.to_square for move in self.engine.board.legal_moves
                if move.from_square == square
            ]
        else:
            # Nếu đang có quân được chọn thì thử di chuyển
            if self.selected_square is not None:
                from_sq = self.selected_square
                to_sq = square
                # Kiểm tra nếu là nước phong
                promotion_moves = [
                    m for m in self.engine.board.legal_moves
                    if m.from_square == from_sq and m.to_square == to_sq and m.promotion is not None
                ]
                if promotion_moves:
                    self.promotion_pending = (from_sq, to_sq)
                    return
                move = chess.Move(from_sq, to_sq)
                if move in self.engine.board.legal_moves:
                    self.engine.board.push(move)
                self.selected_square = None
                self.legal_moves = []

    def draw_promotion_dialog(self):
        if not self.promotion_pending:
            return

        from_sq, to_sq = self.promotion_pending
        pawn_piece = self.engine.board.piece_at(from_sq)
        color = pawn_piece.color if pawn_piece else self.engine.board.turn

        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))

        w, h = 240, 60
        cx, cy = WIDTH // 2, HEIGHT // 2
        box = pygame.Rect(cx - w // 2, cy - h // 2, w, h)
        pygame.draw.rect(self.screen, (240, 240, 240), box, border_radius=8)
        pygame.draw.rect(self.screen, (60, 60, 60), box, 2, border_radius=8)

        promos = [chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT]
        self.promotion_rects = []
        cell_w = w // 4
        for i, promo in enumerate(promos):
            rect = pygame.Rect(box.x + i * cell_w, box.y, cell_w, h)
            symbol = {
                chess.QUEEN: 'Q', chess.ROOK: 'R', chess.BISHOP: 'B', chess.KNIGHT: 'N'
            }[promo]
            key = symbol if color == chess.WHITE else symbol.lower()
            img = piece_images.get(key)
            if img:
                img = pygame.transform.scale(img, (cell_w, h))
                self.screen.blit(img, rect.topleft)
            else:
                font = pygame.font.SysFont(None, 40)
                txt = font.render(symbol, True, (0, 0, 0))
                self.screen.blit(txt, txt.get_rect(center=rect.center))

            mx, my = pygame.mouse.get_pos()
            if rect.collidepoint(mx, my):
                pygame.draw.rect(self.screen, (255, 215, 0), rect, 3, border_radius=6)

            self.promotion_rects.append((promo, rect))

      
                
    def run(self): # ham run chinh
        """Vòng lặp chính"""
        clock = pygame.time.Clock() # kiểm soát tốc độ khung hình
        while self.running: # vòng lặp chính
            for event in pygame.event.get(): # xử lý sự kiện
                if event.type == pygame.QUIT: # nếu đóng cửa sổ
                    self.running = False # thoát vòng lặp
                
                if event.type == pygame.MOUSEBUTTONDOWN: # nếu nhấn chuột
                    self.handle_mouse_click(pygame.mouse.get_pos())
            
              # KIỂM TRA AI ĐI
            if not self.engine.board.turn:  # nếu tới lượt đen (AI)
                move = self.engine.best_move()  # gọi engine trả về nước đi tốt nhất
                if move:
                    self.engine.board.push(move)
                        
                        
            self.draw_board() # gọi hàm vẽ bàn cờ
            self.draw_pieces() # gọi hàm vẽ quân cờ
            self.draw_promotion_dialog()  # hiển thị dialog nếu cần

            pygame.display.flip() # cập nhật màn hình 
            clock.tick(30) # giới hạn tốc độ khung hình ở 30 FPS
