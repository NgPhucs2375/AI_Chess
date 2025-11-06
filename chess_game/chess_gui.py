import pygame
import os
import sys
import chess
from chess_engine import ChessEngine 

# Kích thước cố định cho BÀN CỜ
WIDTH, HEIGHT = 640, 640
ROWS, COLS = 8, 8
SQ_SIZE = WIDTH // COLS
BOARD_WIDTH = WIDTH 

# Kích thước cửa sổ MỚI (Bàn cờ + Bảng điều khiển)
CONTROL_WIDTH = 500
TOTAL_WIDTH = WIDTH + CONTROL_WIDTH
TOTAL_HEIGHT = HEIGHT

# --- ĐỊNH NGHĨA MÀU SẮC DỊU NHẸ, SÁNG SỦA ---
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
# Màu trung tính
GRAY = (150, 150, 150)        # Xám Trung bình (Nền nút MẶC ĐỊNH/KHÔNG chọn)
LIGHT_GRAY = (220, 220, 220)  # Xám Rất Nhạt (Nền Bảng điều khiển/Lịch sử)
DARK_GRAY = (80, 80, 80)      # Xám Đậm (Màu chữ chính/Viền)

# MÀU NỔI BẬT MỚI: Tông Xanh Dương Nhạt Dịu Mắt
HIGHLIGHT_COLOR = (173, 216, 230) # Xanh Dương Nhạt (Light Blue) - Nền nút ĐÃ CHỌN
HOVER_COLOR = (176, 224, 230)     # Xanh Phấn Nhạt (Powder Blue) - Hiệu ứng HOVER
# Tải hình ảnh quân cờ: Giả định thư mục /images/ và /img/ tồn tại.
try:
    base_path = os.path.dirname(__file__)
    def load_image(filename):
        # Ưu tiên tìm trong thư mục images, sau đó là thư mục gốc
        try: return pygame.image.load(os.path.join(base_path, 'images', filename))
        except: return pygame.image.load(os.path.join(base_path, filename))
        
    piece_images = {
        'P' : load_image('wp.png'), 'p' : load_image('bp.png'),
        'N' : load_image('wn.png'), 'n' : load_image('bn.png'),
        'B' : load_image('wb.png'), 'b' : load_image('bb.png'),
        'R' : load_image('wr.png'), 'r' : load_image('br.png'),
        'Q' : load_image('wq.png'), 'q' : load_image('bq.png'),
        'K' : load_image('wk.png'), 'k' : load_image('bk.png'),
    }
except pygame.error as e:
    print(f"Lỗi tải hình ảnh: {e}. Sử dụng Fallback Text.")
    piece_images = {} 

class ChessGUI:
    def __init__(self):
        """Khởi tạo giao diện cờ vua"""

        pygame.init() 
        self.screen = pygame.display.set_mode((TOTAL_WIDTH, TOTAL_HEIGHT)) 
        pygame.display.set_caption("Game Cờ Vua - Python Form Team 2")
        
        # Cấu hình mức độ khó (SỬ DỤNG CHẾ ĐỘ MINIMAX MỚI)
        self.difficulty_levels = {
            # MODE 'minimax_pure': Minimax cơ bản (chậm và yếu)
            "Easy": {'depth': 2, 'time': 0.5, 'mode': 'minimax_pure'}, 
            # MODE 'minimax_full': Minimax + Alpha-Beta (tốt)
            "Medium": {'depth': 3, 'time': 1.0, 'mode': 'minimax_full'}, 
            # MODE 'minimax_full': Minimax + Alpha-Beta + Nâng cao (rất tốt)
            "Difficult": {'depth': 5, 'time': 5.0, 'mode': 'minimax_full'} 
        }
        self.current_difficulty = "Medium" 
        
        self.running = True
        self.engine = ChessEngine()
        self.selected_square = None
        self.legal_moves = []
        
        base_path = os.path.dirname(__file__) 
        # Cố gắng tìm board2.png trong thư mục img
        board_path = os.path.join(base_path,"img","board2.png")
        try:
            self.board_texture = pygame.transform.scale(pygame.image.load(board_path).convert(),(WIDTH, HEIGHT))
        except pygame.error:
            # Nếu không tìm thấy, cố gắng tạo bảng thay thế
            self.board_texture = self._create_fallback_board()


        self.control_rect = pygame.Rect(WIDTH, 0, CONTROL_WIDTH, TOTAL_HEIGHT)
        self.button_rects = {}
        
        # Thêm biến cho các nút điều khiển mới
        self.new_game_rect = None 
        self.undo_rect = None
        self.redo_rect = None
        self.draw_rect = None
        self.quit_rect = None
        
        # Biến để lưu trữ nước đi bị lùi
        self.undone_moves = []
        
        # Biến trạng thái game
        self.is_draw_offered = False
        
        # SỬ DỤNG FONT TIẾNG ANH (hoặc font Unicode)
        font_name = 'Arial Unicode MS' 
        self.font_small = pygame.font.SysFont(font_name, 18)
        self.font_medium = pygame.font.SysFont(font_name, 24, bold=True)
        self.font_big = pygame.font.SysFont(font_name, 36, bold=True)
        
        # Các biến cho lịch sử nước đi
        history_box_start_y = 50 + len(self.difficulty_levels) * 50 + 20 + 40 + 160 # Đẩy xuống dưới các nút mới
        self.move_history_surface = pygame.Surface((CONTROL_WIDTH - 20, TOTAL_HEIGHT - history_box_start_y - 10)) 
        self.move_scroll_y = 0
        self.max_scroll = 0
        
        self.promotion_pending = None 
        self.promotion_rects = []
    
    def new_game(self):
        """Đặt lại trò chơi về trạng thái ban đầu."""
        self.engine.board = chess.Board()
        self.selected_square = None
        self.legal_moves = []
        self.promotion_pending = None
        self.promotion_rects = []
        self.move_scroll_y = 0
        self.engine.tt.table.clear() 
        self.engine.killers.clear() 
        self.engine.history.clear() 
        self.undone_moves = []
        self.is_draw_offered = False
        print("--- Đã bắt đầu ván cờ mới ---")
        
    def undo_move(self):
        """Lùi lại 2 nước đi (người chơi và AI) nếu có thể."""
        if len(self.engine.board.move_stack) >= 2:
            # Lùi nước đi của AI (đen)
            ai_move = self.engine.board.pop()
            self.undone_moves.append(ai_move)
            # Lùi nước đi của Người chơi (trắng)
            player_move = self.engine.board.pop()
            self.undone_moves.append(player_move)
            self.selected_square = None
            self.legal_moves = []
            self.is_draw_offered = False
            print(f"Đã lùi 2 nước: {player_move.uci()} và {ai_move.uci()}")
        elif len(self.engine.board.move_stack) >= 1:
            # Trường hợp chỉ còn 1 nước đi (AI chưa kịp đi)
            player_move = self.engine.board.pop()
            self.undone_moves.append(player_move)
            self.selected_square = None
            self.legal_moves = []
            self.is_draw_offered = False
            print(f"Đã lùi 1 nước: {player_move.uci()}")
        else:
            print("Không thể lùi thêm nước đi.")

    def redo_move(self):
        """Tiếp 2 nước đi (người chơi và AI) nếu có thể."""
        if len(self.undone_moves) >= 2:
            # Tiếp nước đi của Người chơi (trắng)
            player_move = self.undone_moves.pop()
            self.engine.board.push(player_move)
            # Tiếp nước đi của AI (đen)
            ai_move = self.undone_moves.pop()
            self.engine.board.push(ai_move)
            self.selected_square = None
            self.legal_moves = []
            self.is_draw_offered = False
            print(f"Đã tiếp 2 nước: {player_move.uci()} và {ai_move.uci()}")
        elif len(self.undone_moves) >= 1:
            # Trường hợp chỉ còn 1 nước đi để tiếp (AI chưa kịp đi)
            player_move = self.undone_moves.pop()
            self.engine.board.push(player_move)
            self.selected_square = None
            self.legal_moves = []
            self.is_draw_offered = False
            print(f"Đã tiếp 1 nước: {player_move.uci()}")
        else:
            print("Không có nước đi nào để tiếp.")

    def offer_draw(self):
        """Đề nghị hòa."""
        self.is_draw_offered = True
        print("Người chơi đề nghị Hòa.")

    def exit_game(self):
        """Thoát trò chơi."""
        self.running = False
        print("Đã thoát game.")
        pygame.quit()
        sys.exit()

    def _create_fallback_board(self):
        """Tạo bàn cờ đơn giản nếu không tải được texture."""
        surface = pygame.Surface((WIDTH, HEIGHT))
        colors = [(205, 133, 63), (255, 222, 173)] 
        for r in range(ROWS):
            for c in range(COLS):
                color = colors[(r + c) % 2]
                pygame.draw.rect(surface, color, (c * SQ_SIZE, r * SQ_SIZE, SQ_SIZE, SQ_SIZE))
        return surface

    def draw_board(self):
        """Vẽ bàn cờ 8x8"""
        self.screen.blit(self.board_texture,(0,0))
        
        # Vẽ ô được chọn
        if self.selected_square is not None:
            row = 7 - chess.square_rank(self.selected_square)
            col = chess.square_file(self.selected_square)
            rect = pygame.Rect(col * SQ_SIZE, row * SQ_SIZE, SQ_SIZE, SQ_SIZE)
            s = pygame.Surface((SQ_SIZE, SQ_SIZE), pygame.SRCALPHA)
            s.fill((255, 255, 0, 128)) 
            self.screen.blit(s, rect.topleft)

        # Vẽ các nước đi hợp lệ
        for move_square in self.legal_moves:
            row = 7 - chess.square_rank(move_square)
            col = chess.square_file(move_square)
            center = (col * SQ_SIZE + SQ_SIZE // 2, row * SQ_SIZE + SQ_SIZE // 2)
            pygame.draw.circle(self.screen, (0, 255, 0, 100), center, 10)
            
    def draw_pieces(self):
        """Ve cac quan co len ban co"""
        board = self.engine.board 
        for square, piece in board.piece_map().items(): 
            symbol = piece.symbol()
            row = 7 - chess.square_rank(square)
            col = chess.square_file(square)
            
            image = piece_images.get(symbol)
            
            if image:
                if image.get_size() != (SQ_SIZE, SQ_SIZE):
                    image = pygame.transform.scale(image, (SQ_SIZE, SQ_SIZE))
                self.screen.blit(image, (col * SQ_SIZE, row * SQ_SIZE))
            else:
                font = pygame.font.SysFont('arial', SQ_SIZE // 2, bold=True)
                text = font.render(symbol, True, BLACK if piece.color == chess.WHITE else WHITE)
                text_rect = text.get_rect(center=(col * SQ_SIZE + SQ_SIZE // 2, row * SQ_SIZE + SQ_SIZE // 2))
                pygame.draw.rect(self.screen, GRAY, text_rect.inflate(10, 10), border_radius=5)
                self.screen.blit(text, text_rect)


    def draw_controls(self):
        """Vẽ bảng điều khiển bên phải (Replay + Level + History + Controls)"""
        
        # Lấy vị trí chuột hiện tại để xử lý hover
        mx, my = pygame.mouse.get_pos()
        
        pygame.draw.rect(self.screen, LIGHT_GRAY, self.control_rect)
        pygame.draw.line(self.screen, DARK_GRAY, self.control_rect.topleft, self.control_rect.bottomleft, 1)

        y_offset = 10
        button_height = 30  # Chiều cao nút rất nhỏ
        button_width = CONTROL_WIDTH - 20
        
        # Khoảng cách giữa các nút
        spacing = 5 
        
        # --- 1. Hàng Nút Điều Khiển Chính (5 nút: Replay, Undo, Redo, Draw, Exit) ---
        
        # Tính toán chiều rộng cho 5 nút
        five_btn_total_spacing = spacing * 4 # 4 khoảng cách giữa 5 nút
        five_btn_width = (button_width - five_btn_total_spacing) // 5 

        x_start = WIDTH + 10

        # Danh sách các nút (Tên tiếng Anh, Biến Rect)
        controls_config = [
            ("Replay", self.new_game_rect),
            ("Undo", self.undo_rect), 
            ("Redo", self.redo_rect), 
            ("Draw", self.draw_rect), 
            ("Exit", self.quit_rect), 
        ]
        
        # Cập nhật Rects và vẽ
        for i, (text, rect_var) in enumerate(controls_config):
            rect = pygame.Rect(x_start + i * (five_btn_width + spacing), y_offset, five_btn_width, button_height)
            
            # Cập nhật biến Rect của đối tượng
            if text == "Replay": setattr(self, 'new_game_rect', rect)
            elif text == "Undo": setattr(self, 'undo_rect', rect)
            elif text == "Redo": setattr(self, 'redo_rect', rect)
            elif text == "Draw": 
                setattr(self, 'draw_rect', rect)
            elif text == "Exit": setattr(self, 'quit_rect', rect)
            
            # Logic Màu: Mặc định Xám (GRAY), nếu hover thì Xanh Nhạt (HOVER_COLOR), nếu Draw đang offer thì Xám Đậm hơn
            color = GRAY
            text_color = WHITE # Màu chữ mặc định (trên nền Xám/Xám Đậm)
            
            if rect.collidepoint(mx, my): # Hiệu ứng hover (Xanh Nhạt)
                color = HOVER_COLOR
                text_color = BLACK
            elif text == "Draw" and self.is_draw_offered: # Nút Draw đang được nhấn
                color = DARK_GRAY
            
            pygame.draw.rect(self.screen, color, rect, border_radius=4)
            text_surface = self.font_small.render(text, True, text_color) 
            self.screen.blit(text_surface, text_surface.get_rect(center=rect.center))

        y_offset += button_height + 20
        
        # --- 2. Tiêu đề Level ---
        title_text = self.font_medium.render("Level", True, BLACK) 
        self.screen.blit(title_text, (WIDTH + 10, y_offset))
        
        y_offset += 30 
        button_height = 35 
        self.button_rects.clear()
        
        # --- 3. Hàng Nút Cấp Độ (3 nút: Easy, Medium, Difficult) ---
        
        three_btn_total_spacing = spacing * 2
        three_btn_width = (button_width - three_btn_total_spacing) // 3
        
        level_x_start = WIDTH + 10
        
        for i, (level, config) in enumerate(self.difficulty_levels.items()):
            
            rect = pygame.Rect(level_x_start + i * (three_btn_width + spacing), y_offset, three_btn_width, button_height)
            
            # Logic Màu Level: Mặc định Xám, Đang chọn là HIGHLIGHT_COLOR (Xanh Nhạt), Hover là HOVER_COLOR
            color = GRAY
            text_color = WHITE
            
            if level == self.current_difficulty:
                color = HIGHLIGHT_COLOR # Trạng thái được chọn (Xanh Nhạt)
                text_color = BLACK
            
            if rect.collidepoint(mx, my) and level != self.current_difficulty: # Hover (Xanh Phấn Nhạt)
                color = HOVER_COLOR
                text_color = BLACK
            
            self.button_rects[level] = rect
            
            pygame.draw.rect(self.screen, color, rect, border_radius=5)
            
            # Hiển thị tên
            display_text = level
            if display_text == "Medium":
                display_text = "Med"
            elif display_text == "Difficult":
                display_text = "Hard"
            
            text = self.font_small.render(display_text, True, text_color)
            self.screen.blit(text, text.get_rect(center=rect.center))
            
        y_offset += button_height + 20

        # --- 4. Tiêu đề History of moves ---
        history_box_y = y_offset + 10 
        history_title = self.font_medium.render("History of moves", True, BLACK) 
        self.screen.blit(history_title, (WIDTH + 10, history_box_y - 20))
        
        self.draw_move_history(history_box_y)

    def draw_move_history(self, history_box_y):
        """Vẽ danh sách nước đi đã được thực hiện."""
        
        temp_board = chess.Board()
        moves_san = []
        for move in self.engine.board.move_stack:
            moves_san.append(temp_board.san(move))
            try:
                temp_board.push(move)
            except Exception as e:
                print(f"Lỗi khi push move trong lịch sử: {e}")
                
        formatted_moves = []
        for i in range(0, len(moves_san), 2):
            move_num = i // 2 + 1
            white_move = moves_san[i]
            black_move = moves_san[i+1] if i + 1 < len(moves_san) else ""
            formatted_moves.append(f"{move_num}. {white_move} {black_move}")

        history_box_h = TOTAL_HEIGHT - history_box_y - 10
        history_rect = pygame.Rect(WIDTH + 10, history_box_y, CONTROL_WIDTH - 20, history_box_h)
        self.move_history_surface = pygame.Surface((CONTROL_WIDTH - 20, history_box_h)) 
        
        self.move_history_surface.fill(LIGHT_GRAY)
        line_height = 20
        
        total_content_height = len(formatted_moves) * line_height
        self.max_scroll = max(0, total_content_height - history_box_h) 
        
        current_y = 5 - self.move_scroll_y
        for move_text in formatted_moves:
            text_surface = self.font_small.render(move_text, True, BLACK)
            self.move_history_surface.blit(text_surface, (5, current_y))
            current_y += line_height

        
        self.screen.blit(self.move_history_surface, history_rect.topleft) 
        pygame.draw.rect(self.screen, BLACK, history_rect, 1) 
    
    def handle_mouse_click(self, pos):
        """Xử lý click chuột cho cả bàn cờ và bảng điều khiển."""
        x, y = pos
        
        # --- Xử lý các nút điều khiển ---
        if self.new_game_rect and self.new_game_rect.collidepoint(x, y):
            self.new_game()
            return
        
        if self.undo_rect and self.undo_rect.collidepoint(x, y):
            self.undo_move()
            return
        
        if self.redo_rect and self.redo_rect.collidepoint(x, y):
            self.redo_move()
            return
        
        if self.draw_rect and self.draw_rect.collidepoint(x, y) and not self.engine.board.is_game_over():
            self.offer_draw()
            return
        
        if self.quit_rect and self.quit_rect.collidepoint(x, y):
            self.exit_game()
            return
        
        # --- Xử lý nút chọn Level ---
        if self.control_rect.collidepoint(x, y):
            for level, rect in self.button_rects.items():
                if rect.collidepoint(x, y):
                    self.current_difficulty = level
                    print(f"Đã chọn mức độ: {level}")
                    return 

        # --- Xử lý hộp thoại Phong cấp ---
        if self.promotion_pending is not None:
            for piece_type, rect in self.promotion_rects:
                if rect.collidepoint(x, y):
                    from_sq, to_sq = self.promotion_pending
                    move = chess.Move(from_sq, to_sq, promotion=piece_type)
                    if move in self.engine.board.legal_moves:
                        self.engine.board.push(move)
                        self.undone_moves = [] # Xóa lịch sử Redo
                        self.is_draw_offered = False
                    self.promotion_pending = None
                    self.promotion_rects = []
                    return
            # Click ra ngoài hộp thoại phong cấp thì hủy
            self.promotion_pending = None
            self.promotion_rects = []
            return
        
        # --- Xử lý nước đi trên Bàn cờ ---
        if x > BOARD_WIDTH or self.engine.board.is_game_over(): 
            return

        col = pos[0] // SQ_SIZE
        row = 7 - (pos[1] // SQ_SIZE)
        square = chess.square(col, row)
        
        if self.selected_square == square:
            self.selected_square = None
            self.legal_moves = []
            return

        piece = self.engine.board.piece_at(square)
        if piece and piece.color == self.engine.board.turn:
            # Chọn quân cờ
            self.selected_square = square
            self.legal_moves = [
                move.to_square for move in self.engine.board.legal_moves
                if move.from_square == square
            ]
        else:
            if self.selected_square is not None:
                # Thực hiện nước đi
                from_sq = self.selected_square
                to_sq = square
                
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
                    self.undone_moves = [] # Xóa lịch sử Redo
                    self.is_draw_offered = False
                self.selected_square = None
                self.legal_moves = []

    def handle_mouse_wheel(self, event):
        """Xử lý cuộn chuột trên lịch sử nước đi."""
        if self.control_rect.collidepoint(pygame.mouse.get_pos()):
            # Tính lại vị trí history_box_start_y
            history_box_start_y = 50 + len(self.difficulty_levels) * 50 + 20 + 40 + 160 
            history_rect = pygame.Rect(WIDTH + 10, history_box_start_y, CONTROL_WIDTH - 20, TOTAL_HEIGHT - history_box_start_y - 10)
            
            if history_rect.collidepoint(pygame.mouse.get_pos()):
                scroll_amount = event.y * 20 
                new_scroll = self.move_scroll_y - scroll_amount
                self.move_scroll_y = max(0, min(self.max_scroll, new_scroll))

    def draw_promotion_dialog(self):
        """Vẽ hộp thoại phong cấp"""
        if not self.promotion_pending:
            return

        from_sq, to_sq = self.promotion_pending
        pawn_piece = self.engine.board.piece_at(from_sq)
        color = pawn_piece.color if pawn_piece else self.engine.board.turn 

        overlay = pygame.Surface((TOTAL_WIDTH, TOTAL_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))

        w, h = 240, 60
        cx, cy = TOTAL_WIDTH // 2, TOTAL_HEIGHT // 2 
        box = pygame.Rect(cx - w // 2, cy - h // 2, w, h)
        pygame.draw.rect(self.screen, (240, 240, 240), box, border_radius=8)
        pygame.draw.rect(self.screen, (60, 60, 60), box, 2, border_radius=8)

        promos = [chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT]
        self.promotion_rects = []
        cell_w = w // 4
        
        for i, promo in enumerate(promos):
            rect = pygame.Rect(box.x + i * cell_w, box.y, cell_w, h)
            symbol_map = {
                chess.QUEEN: 'Q', chess.ROOK: 'R', chess.BISHOP: 'B', chess.KNIGHT: 'N'
            }
            symbol = symbol_map.get(promo, '?')
            key = symbol if color == chess.WHITE else symbol.lower()
            img = piece_images.get(key)
            
            if img:
                img = pygame.transform.scale(img, (cell_w, h))
                self.screen.blit(img, rect.topleft)
            else:
                font = pygame.font.SysFont(None, 40)
                txt = font.render(symbol, True, BLACK)
                self.screen.blit(txt, txt.get_rect(center=rect.center))

            mx, my = pygame.mouse.get_pos()
            if rect.collidepoint(mx, my):
                pygame.draw.rect(self.screen, (255, 215, 0), rect, 3, border_radius=6)

            self.promotion_rects.append((promo, rect))
            
    def draw_game_over(self):
        """Vẽ thông báo trò chơi kết thúc."""
        if self.is_draw_offered:
            result = "DRAW OFFERED"
            # Sử dụng màu Xanh Nhạt dịu mắt cho đề nghị Hòa
            color = HIGHLIGHT_COLOR 
        elif self.engine.board.is_checkmate():
            result = "WHITE WINS (CHECKMATE)!" if self.engine.board.turn == chess.BLACK else "BLACK WINS (CHECKMATE)!"
            # Sử dụng màu Highlight cho thông báo thắng/thua
            color = HIGHLIGHT_COLOR 
        elif self.engine.board.is_stalemate():
            result = "DRAW (STALEMATE)"
            color = GRAY
        elif self.engine.board.is_insufficient_material():
            result = "DRAW (INSUFFICIENT MATERIAL)"
            color = GRAY
        elif self.engine.board.is_fifty_moves():
            result = "DRAW (50 MOVES RULE)"
            color = GRAY
        elif self.engine.board.is_repetition():
            result = "DRAW (THREEFOLD REPETITION)"
            color = GRAY
        else:
            return 
            
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))
        
        # Chữ luôn màu Trắng trên nền tối/sáng
        text_surface = self.font_big.render(result, True, WHITE) 
        text_rect = text_surface.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        
        bg_rect = text_rect.inflate(40, 20)
        # Vẽ nền thông báo bằng màu dịu nhẹ mới
        pygame.draw.rect(self.screen, color, bg_rect, border_radius=10)
        
        self.screen.blit(text_surface, text_rect)

            
    def run(self):
        """Vòng lặp chính"""
        clock = pygame.time.Clock()
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                
                if event.type == pygame.MOUSEBUTTONDOWN:
                    self.handle_mouse_click(pygame.mouse.get_pos())
                
                if event.type == pygame.MOUSEWHEEL: 
                    self.handle_mouse_wheel(event)
            
            # KIỂM TRA AI ĐI (Đen)
            if (self.engine.board.turn == chess.BLACK and 
                self.promotion_pending is None and 
                not self.engine.board.is_game_over() and
                not self.is_draw_offered): # Thêm check draw offered
                
                config = self.difficulty_levels[self.current_difficulty]
                
                # SỬ DỤNG THAM SỐ MODE MỚI
                move = self.engine.best_move(
                    depth=config['depth'], 
                    time_limit=config['time'],
                    mode=config['mode'] 
                ) 
                if move:
                    self.engine.board.push(move)
                    self.undone_moves = [] # Xóa lịch sử Redo sau khi AI đi
            
            self.draw_board()
            self.draw_pieces()
            self.draw_controls() 
            self.draw_promotion_dialog()
            self.draw_game_over() 

            pygame.display.flip()
            clock.tick(30)
        
        pygame.quit()