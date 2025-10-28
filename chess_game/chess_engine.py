import chess
class ChessEngine:
    def __init__(self):
        # Khởi tạo bàn cờ 8x8, các quân cờ ban đầu
        self.board = self.create_starting_board()

    def create_starting_board(self):
        # Có thể dùng thư viện 'chess' để dễ hơn
        return chess.Board()

    def print_board(self): # ham in ban
        print(self.board)
    
    def evaluate_board(self):
        # Hàm đánh giá trạng thái bàn cờ (chưa triển khai)
        pieces_values = { # giá trị của từng loại quân cờ
            chess.PAWN: 1,
            chess.KNIGHT: 3,
            chess.BISHOP: 3,
            chess.ROOK: 5,
            chess.QUEEN: 9,
            chess.KING: 1000
        }
        """Trả về điểm số của bàn cờ: điểm dương nếu trắng tốt hơn, âm nếu đen tốt hơn"""
        diem = 0
        for piece_type in pieces_values:
            diem += len(self.board.pieces(piece_type, chess.WHITE)) * pieces_values[piece_type]
            diem -= len(self.board.pieces(piece_type, chess.BLACK)) * pieces_values[piece_type]
        return diem   

        # thêm các yếu tố khác như vị trí quân cờ, kiểm soát trung tâm, v.v.
        value += 0.0001 * (len(list(self.board.legal_moves))) # khuyến khích nhiều nước đi hơn
        return value
    
             
    def minimax_AplhaBeta(self,depth,alpha,beta,is_maxmizing):
        """Hàm minimax với cắt tỉa alpha-beta."""
        if depth == 0 or self.board.is_game_over(): # check xem nếu độ sâu là 0 hoặc là trò chơi kết thúc
           return self.evaluate_board(),None # trả về giá trị đánh giá của bàn cờ theo hàm đã tạo ở ngang trên
                
        best_move = None
        if is_maxmizing: # check nếu xem là lượt của máy tối đa hóa chưa
            max_eval = float('-inf') # khởi tạo 1 giá trị âm vô hạn để có thể so sánh vì nó cần 1 mốc khởi đầu nhỏ để mọi điểm hợp lệ sau đó đều lớn hơn để duyệt
            for move in self.board.legal_moves: # vòng lặp duyệt qua tất cả các bước đi hợp lệ có thể đi 
                    self.board.push(move) # đẩy nước đó lên bàn cờ tạm thời
                    eval,_ = self.minimax_AplhaBeta(depth - 1,alpha,beta, False) # gọi đệ quy vào nhánh tiếp theo của cây trò chơi ,với độ sâu giảm đi 1 vì đi đc 1 nước và chuyển trạng thái là lượt của người chơi (False) vì người chơi chọn tối thiểu hóa
                    self.board.pop() # bỏ nước đi đó ra khỏi bàn cờ tạm thời để thử nước đi khác
                    if eval > max_eval:
                        max_eval = eval
                        best_move = move
                    alpha = max(alpha,eval)
                    if beta <= alpha:
                        break # cắt tỉa nhánh   
            return max_eval,best_move # trả về giá trị lớn nhất tìm đc
        else: # nếu là lượt của người chơi tối thiểu hóa
            min_eval = float('inf') # khởi tạo 1 giá trị dương vô hạn để có thể so sánh vì nó cần 1 mốc khởi đầu lớn để mọi điểm hợp lệ sau đó đều nhỏ hơn để duyệt  
            for move in self.board.legal_moves: # vòng lặp duyệt qua tất cả các bước đi hợp lệ có thể đi
                    self.board.push(move) # đẩy vào bỏad temp
                    eval,_ = self.minimax_AplhaBeta(depth -1,alpha,beta, True) # gọi đệ quy và chuyển trạng thái là lượt của máy (True) vì máy chọn tối đa hóa
                    self.board.pop() # bỏ đi ra khỏi board temp để thử nước khác
                    if eval < min_eval:
                        min_eval = eval
                        best_move = move
                    beta = min(beta,eval)
                    if beta <= alpha:
                        break # cắt tỉa nhánh
            return min_eval,best_move # trả về giá trị nhỏ nhất tìm đc
        
        
    def best_move(self,depth = 2): 
        """Tim nuoc di tot nhat cho mays"""
        _,best_move = self.minimax_AplhaBeta(depth,float('-inf'),float('inf'),True) # gọi hàm minimax với cắt tỉa alpha-beta
        return best_move
                
            