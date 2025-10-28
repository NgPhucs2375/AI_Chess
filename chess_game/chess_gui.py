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
        
        
        
        base_path = os.path.dirname(__file__) # đường dẫn cơ sở đến thư mục hiện tại
        board_path = os.path.join(base_path,"img","board2.png") # đường dẫn đến hình ảnh ô trắng
        self.board_texture = pygame.transform.scale(pygame.image.load(board_path).convert(),(WIDTH, HEIGHT)) # tải và thay đổi kích thước hình ảnh bàn cờ

    def draw_board(self): # ham ve ban co
        """Vẽ bàn cờ 8x8"""
        self.screen.blit(self.board_texture,(0,0)) # ve ban co len
        
    def draw_pieces(self): # ham ve quan co
        """Ve cac quan co len ban co"""
        self.board = self.engine.board # lay ban co tu engine
        for square in chess.SQUARES: # vong lap qua tung o tren ban co
            quan_co = self.board.piece_at(square) # lay quan co o do
            if quan_co: 
                
                ki_tu = quan_co.symbol() # lay ki tu dai dien cho quan co
                row = 7 - chess.square_rank(square) # tinh hang
                col = chess.square_file(square) # tinh cot
                hinh_quan = piece_images[ki_tu] # lay hinh anh quan co tu dict piece_images
               
                scaled_piece = pygame.transform.scale(hinh_quan, (SQ_SIZE, SQ_SIZE)) # scale hinh anh ve kich thuoc o co
                self.screen.blit(scaled_piece, (col * SQ_SIZE, row * SQ_SIZE)) # ve quan co len ban co


    def run(self): # ham run chinh
        """Vòng lặp chính"""
        clock = pygame.time.Clock() # kiểm soát tốc độ khung hình
        while self.running: # vòng lặp chính
            for event in pygame.event.get(): # xử lý sự kiện
                if event.type == pygame.QUIT: # nếu đóng cửa sổ
                    self.running = False # thoát vòng lặp
                
                if event.type == pygame.MOUSEBUTTONDOWN: # nếu nhấn chuột
                    x,y = event.pos # lấy tọa độ chuột
                    row,col = y // SQ_SIZE,x // SQ_SIZE # tính toán hàng và cột
                    square = chess.square(col,7 - row) # chuyển đổi sang tọa độ bàn cờ của thư viện chess
                      
                    if self.selected_square is None: # neu chua chon o nao
                        if self.engine.board.piece_at(square) is not None and self.engine.board.piece_at(square).color == chess.WHITE: # neu o do co quan co va la quan trang
                            self.selected_square = square # chon o do 
                    else: # neu da chon o truoc do
                        move = chess.Move(self.selected_square,square) # tao nuoc di tu o da chon den o hien tai
                        if move in self.engine.board.legal_moves: # neu nuoc di hop le
                            self.engine.board.push(move) # thuc hien nuoc di
                             
                            #Cho may di lai
                            best_move = self.engine.best_move(depth = 2 ) # tim nuoc di tot nhat cho may
                            if best_move: # neu tim duoc nuoc di
                                self.engine.board.push(best_move) # thuc hien nuoc di cua may
                        self.selected_square = None # bo chon o
                        
            self.draw_board() # gọi hàm vẽ bàn cờ
            self.draw_pieces() # gọi hàm vẽ quân cờ
            pygame.display.flip() # cập nhật màn hình 
            clock.tick(30) # giới hạn tốc độ khung hình ở 30 FPS
