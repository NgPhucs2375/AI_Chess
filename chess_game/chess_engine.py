import chess
import time
import random
from collections import defaultdict

class TranspositionTable:
    """Lop bang luu cac trang thai da danh gia de tang toc do."""
    """Gom : Exact,Lower, Upper"""
    def __init__(self):
        self.table = {}
    
    def store(self,key,depth,flag,score,best_move):
        current = self.table.get(key)
        
        # giu lai entry tot hon
        if current is None or depth >= current[0]:
            self.table[key] = (depth,flag,score,best_move)
            
    def probe(self,key,depth,alpha,beta):
        entry = self.table.get(key)
        if entry is None:
            return None
        edepth,flag,val,mmove = entry
        if edepth >= depth:
            return None
        if flag == 'EXACT':
            return val, mmove,flag
        if flag == 'LOWER' and val >= beta:
            return val, mmove,flag
        if flag == 'UPPER' and val <= alpha:
            return val, mmove,flag
        return None

class ChessEngine:
    def __init__(self):
        # start position
        self.board = chess.Board()
        # transposition cache (fen, depth, is_maximizing) -> (score, best_move)
        self.cache = {}
        
        self.piece_values = {
            chess.PAWN: 100,
            chess.KNIGHT: 320,
            chess.BISHOP: 330,
            chess.ROOK: 500,
            chess.QUEEN: 900,
            chess.KING: 20000
        }
        
        self.mobility_weights = {
            chess.PAWN: 0.05,
            chess.KNIGHT: 0.2,
            chess.BISHOP: 0.2,
            chess.ROOK: 0.25,
            chess.QUEEN: 0.15,
            chess.KING: 0.05
        }
        
        self.PST = self.__init___piece_square_tables()
        
        # zobrist + TT + killer + history 
        self._init_zobrist()
        self.tt = TranspositionTable()
        self.killers = defaultdict(lambda: [None, None])  # two killer moves per depth
        self.history = defaultdict(int)  # history heuristic
        
        # timout control 
        self.stop_time = None

    def print_board(self):
        print(self.board)

    def _init_zobrist(self):
        """Khoi tao bang Zobrist cho hash nhanh."""
        self.zobrist_piece = {}
        for pt in (chess.PAWN,chess.KNIGHT,chess.BISHOP,chess.ROOK,chess.QUEEN,chess.KING):
            for color in (chess.WHITE,chess.BLACK):
                for sq in chess.SQUARES:
                    self.zobrist_piece[(pt,color,sq)] = random.getrandbits(64)
        self.zobrist_side = random.getrandbits(64)
        self.zobrist_castle = {
            'K' : random.getrandbits(64),
            'Q' : random.getrandbits(64),
            'k' : random.getrandbits(64),
            'q' : random.getrandbits(64),
        }
        self.zobrist_ep = [random.getrandbits(64) for _ in range(8)]
        
    def zobrist_hash(self):
        """Tinh hash Zobrist cho trang thai hien tai cua ban co."""
        h =0
        for sq in chess.SQUARES:
            piece = self.board.piece_at(sq)
            if piece:
                h ^= self.zobrist_piece[(piece.piece_type,piece.color,sq)]
        if self.board.turn == chess.BLACK:
            h ^= self.zobrist_side
        if self.board.has_kingside_castling_rights(chess.WHITE):
            h ^= self.zobrist_castle['K']
        if self.board.has_queenside_castling_rights(chess.WHITE):
            h ^= self.zobrist_castle['Q']
        if self.board.has_kingside_castling_rights(chess.BLACK):
            h ^= self.zobrist_castle['k']
        if self.board.has_queenside_castling_rights(chess.BLACK):
            h ^= self.zobrist_castle['q']
        ep = self.board.ep_square
        if ep is not None:
            f = chess.square_file(ep)
            h ^= self.zobrist_ep[f]
        return h
        
            
    #---------------------------------------
    # 1. EVALUATION ENTRY POINT
    #---------------------------------------
    def evaluate_board(self):
    
        # Kiểm tra trạng thái kết thúc trò chơi
        if self.board.is_checkmate():
            return -99999 if self.board.turn == chess.WHITE else 99999
        if self.board.is_stalemate() or self.board.is_insufficient_material():
            return 0

        score = 0
        score += self._material_eval()
        score += self._mobility_eval()
        score += self._pawn_structure_eval()
        score += self._center_control_eval()
        score += self._King_safety_eval()
        score += self._threats_eval()
        
        return int(score)
   

    

    def _material_eval(self): 
        """Đánh giá vật chất và bảng vị trí quân cờ"""
        score = 0
        for sq in chess.SQUARES:
            piece = self.board.piece_at(sq)
            if not piece:
                continue
            val = self.piece_values[piece.piece_type]
            pst = self.PST[piece.piece_type]
            if piece.color == chess.WHITE:
                score += val + pst[sq]
            else:
                score -= val + pst[chess.square_mirror(sq)]
        return score

    def _mobility_eval(self):
        """Đánh giá khả năng di chuyển của các quân cờ"""
        score = 0
        for sq in chess.SQUARES:
            piece = self.board.piece_at(sq)
            if not piece:
                continue
            attacks = len(self.board.attacks(sq))
            w = self.mobility_weights.get(piece.piece_type, 0)
            if piece.color == chess.WHITE:
                score += attacks * w
            else:
                score -= attacks * w
        return score

    def _pawn_structure_eval(self):
        """Đánh giá cấu trúc tốt của các con tốt"""
        score = 0
        pawn_files_white = [chess.square_file(sq) for sq in self.board.pieces(chess.PAWN, chess.WHITE)]
        pawn_files_black = [chess.square_file(sq) for sq in self.board.pieces(chess.PAWN, chess.BLACK)]
        white_pawns = set(self.board.pieces(chess.PAWN, chess.WHITE))
        black_pawns = set(self.board.pieces(chess.PAWN, chess.BLACK))

        doubled_penalty = 25
        isolated_penalty = 20
        passed_bonus = 25

        def is_passed(sq, color):
            """Kiểm tra xem con tốt có phải là con tốt THONG KHONG"""
            f = chess.square_file(sq)
            r = chess.square_rank(sq)
            enemy = black_pawns if color == chess.WHITE else white_pawns
            for ep in enemy:
                ef = chess.square_file(ep)
                er = chess.square_rank(ep)
                if abs(ef - f) <= 1:
                    if (color == chess.WHITE and er > r) or (color == chess.BLACK and er < r):
                        return False
            return True

        for sq in self.board.pieces(chess.PAWN, chess.WHITE):
            f = chess.square_file(sq)
            if pawn_files_white.count(f) > 1:
                score -= doubled_penalty
            if not any(adj in pawn_files_white for adj in (f - 1, f + 1) if 0 <= adj <= 7):
                score -= isolated_penalty
            if is_passed(sq, chess.WHITE):
                score += passed_bonus

        for sq in self.board.pieces(chess.PAWN, chess.BLACK):
            f = chess.square_file(sq)
            if pawn_files_black.count(f) > 1:
                score += doubled_penalty
            if not any(adj in pawn_files_black for adj in (f - 1, f + 1) if 0 <= adj <= 7):
                score += isolated_penalty
            if is_passed(sq, chess.BLACK):
                score -= passed_bonus

        return score

    def _center_control_eval(self):
        """Đánh giá kiểm soát trung tâm"""
        score = 0
        for sq in (chess.D4, chess.D5, chess.E4, chess.E5):
            p = self.board.piece_at(sq)
            if p:
                score += 30 if p.color == chess.WHITE else -30
        return score

    def __init___piece_square_tables(self):
        """Khởi tạo PSTs (Piece Square Tables)."""
        return {
            chess.PAWN: [
                0,0,0,0,0,0,0,0,
                5,10,10,-20,-20,10,10,5,
                5,-5,-10,0,0,-10,-5,5,
                0,0,0,20,20,0,0,0,
                5,5,10,25,25,10,5,5,
                10,10,20,30,30,20,10,10,
                50,50,50,50,50,50,50,50,
                0,0,0,0,0,0,0,0
            ],
            chess.KNIGHT: [
                -50,-40,-30,-30,-30,-30,-40,-50,
                -40,-20,0,0,0,0,-20,-40,
                -30,0,10,15,15,10,0,-30,
                -30,5,15,20,20,15,5,-30,
                -30,0,15,20,20,15,0,-30,
                -30,5,10,15,15,10,5,-30,
                -40,-20,0,5,5,0,-20,-40,
                -50,-40,-30,-30,-30,-30,-40,-50
            ],
            chess.BISHOP: [
                -20,-10,-10,-10,-10,-10,-10,-20,
                -10,0,0,0,0,0,0,-10,
                -10,0,5,10,10,5,0,-10,
                -10,5,5,10,10,5,5,-10,
                -10,0,10,10,10,10,0,-10,
                -10,10,10,10,10,10,10,-10,
                -10,5,0,0,0,0,5,-10,
                -20,-10,-10,-10,-10,-10,-10,-20
            ],
            chess.ROOK: [
                0,0,0,0,0,0,0,0,
                5,10,10,10,10,10,10,5,
                -5,0,0,0,0,0,0,-5,
                -5,0,0,0,0,0,0,-5,
                -5,0,0,0,0,0,0,-5,
                -5,0,0,0,0,0,0,-5,
                -5,0,0,0,0,0,0,-5,
                0,0,0,5,5,0,0,0
            ],
            chess.QUEEN: [
                -20,-10,-10,-5,-5,-10,-10,-20,
                -10,0,0,0,0,0,0,-10,
                -10,0,5,5,5,5,0,-10,
                -5,0,5,5,5,5,0,-5,
                0,0,5,5,5,5,0,0,
                -10,5,5,5,5,5,0,-10,
                -10,0,5,0,0,0,0,-10,
                -20,-10,-10,-5,-5,-10,-10,-20
            ],
            chess.KING: [
                -30,-40,-40,-50,-50,-40,-40,-30,
                -30,-40,-40,-50,-50,-40,-40,-30,
                -30,-40,-40,-50,-50,-40,-40,-30,
                -30,-40,-40,-50,-50,-40,-40,-30,
                -20,-30,-30,-40,-40,-30,-30,-20,
                -10,-20,-20,-20,-20,-20,-20,-10,
                20,20,0,0,0,0,20,20,
                20,30,10,0,0,10,30,20
            ]
        }

    def _King_safety_eval(self):
        """Đánh giá độ an toàn của vua"""
        score = 0
        king_white_sq = self.board.king(chess.WHITE)
        king_black_sq = self.board.king(chess.BLACK)
        
        def penalty(king_sq,color):
            if king_sq is None:
                return 0
            # phat neu vua o trung tam hoac mo rong
            file = chess.square_file(king_sq)
            rank = chess.square_rank(king_sq)
            pen = 0
            
            # phat manh neu vua o trung tam
            if rank in(3,4) or file in(3,4):
                pen += 60
                
            # kiem tra cac quan che chan xung quanh
            font_rank = rank +(1 if color == chess.WHITE else -1)
            for df in [-1,0,1]:
                f = file + df
                if 0 <= f <= 7 and 0 <= font_rank <= 7:
                    sq = chess.square(f,font_rank)
                    piece = self.board.piece_at(sq)
                    if not piece or piece.piece_type != chess.PAWN or piece.color != color:
                        pen += 20
            # neu vua chua nhap thanh => phat them
            if (color == chess.WHITE and not self.board.has_kingside_castling_rights(chess.WHITE) and not self.board.has_queenside_castling_rights(chess.WHITE)) or \
               (color == chess.BLACK and not self.board.has_kingside_castling_rights(chess.BLACK) and not self.board.has_queenside_castling_rights(chess.BLACK)):
                pen += 20

            return pen
        score -= penalty(king_white_sq,chess.WHITE)
        score += penalty(king_black_sq,chess.BLACK)
        return score
    
    def _threats_eval(self):
        """Đánh giá các mối đe dọa trên bàn cờ"""
        score = 0
        piece_values = self.piece_values
        for sq in chess.SQUARES:
            piece = self.board.piece_at(sq)
            if not piece:
                continue
            attackers = self.board.attackers(not piece.color, sq)
            defenders = self.board.attackers(piece.color, sq)

            # neu bi tan cong ma khong duoc bao vw -> phat diem
            if attackers and not defenders:
                if piece.color == chess.WHITE:
                    score -= piece_values[piece.piece_type]
                else:
                    score += piece_values[piece.piece_type]
                    
            # neu quan minh dang tan cong quan co gia tri cao hon -> thuong diem        
            for at in attackers:
                target = self.board.piece_at(sq)
                attackers_piece = self.board.piece_at(at)
                if target and attackers_piece and piece_values[target.piece_type] > piece_values[attackers_piece.piece_type]:
                    if attackers_piece.color == chess.WHITE:
                        score += 15
                    else:
                        score -= 15

        return score
    
    def _mvv_lva_value(self,move):
        """ Ham tra ve gia tri MVV-LVA cho nuoc di """
        if not self.board.is_capture(move):
            return 0
        victim = self.board.piece_at(move.to_square)
        attacker = self.board.piece_at(move.from_square)
        if victim and attacker:
            return 0
        v = self.piece_values.get(victim.piece_type,0)
        a = self.piece_values.get(attacker.piece_type,0)
        return 10000 + (v*10-a)
    
    def _order_moves_improved(self,depth):
        """cai tien yeu cau sap xep nuoc di voi MVV-LVA, killer move va history heuristic"""
        moves = list(self.board.legal_moves)
        key_tt = None
        try:
            h = self.zobrist_hash()
            tt_entry = self.tt.table.get(h)
            if tt_entry:
                key_tt = tt_entry[3]  # best move from TT
        except Exception:
            key_tt = None
        
        def score_move(m):
            s = 0
            if key_tt and m == key_tt:
                s += 100000  # diem cao nhat cho nuoc di TT
            s += self._mvv_lva_value(m)  # MVV-LVA dung de danh gia nuoc di an quan co tot hon nuoc di khong an
            if m.promotion: # neu la nuoc an quan co thi cung uu tien
                s += 8000  # uu tien cho nuoc thang quan
            # killer move heuristic
            k1,k2 = self.killers.get(depth,(None,None)) # lay 2 nuoc di killer de so sanh voi nuoc di hien tai va tang diem neu trung
            if m == k1: # so sanh voi nuoc di killer 1 neu trung tang diem
                s += 5000
            elif m == k2: # so sanh voi nuoc di killer 2 neu trung tang diem
                s += 4000
            s += self.history.get((m.from_square,m.to_square),0)  # history heuristic
            return -s  # sap xep tang dan
        
        moves.sort(key=score_move) # saap xep nuoc di cho diem cao den thap
        return moves # tra ve danh sach nuoc di da sap xep
    
    def _record_killer(self,move,depth):
        """Luu nuoc di killer vao danh sach killer moves"""
        k1,k2 = self.killers.get(depth,(None,None))
        if k1 is None:
            self.killers[depth][0] = move
            return
        elif move != k1:
            self.killers[depth][1] = k1  # dich chuyen killer 1 xuong killer 2
            self.killers[depth][0] = move  # luu nuoc di hien tai vao killer 1
    
    def _record_history(self,move,depth,bonus=1): # truyen vao 4 tham so bao gom khoi tao, nuoc di, do sau, diem tang them
        """Cập nhật bảng lịch sử cho nước đi"""
        key = (move.from_square, move.to_square) # tao key tu nuoc di va o den de cap nhat vao history de tang toc do alpha-beta
        self.history[key] += bonus * (2 ** depth) # tang diem cho nuoc di trong history heuristic
    
    def _order_moves(self): # ham sap xep nuoc di
        """danh sach nuoc di duoc sap xep de tang toc do alpha-beta"""
        moves = list(self.board.legal_moves)
        def key(m):
            # capture or promotion => high priority
            score = 0
            if self.board.is_capture(m):
                score += 100
                # prefer captures of high-value pieces
                to_piece = self.board.piece_at(m.to_square)
                if to_piece:
                    score += {chess.PAWN:10, chess.KNIGHT:30, chess.BISHOP:30, chess.ROOK:50, chess.QUEEN:90}.get(to_piece.piece_type,0)
            if m.promotion:
                score += 80
            return -score  # negative because we sort ascending
        moves.sort(key=key)
        return moves

    def minimax_alpha_beta(self, depth, alpha, beta, is_maximizing):
        """Minimax với cắt tỉa alpha-beta và bộ nhớ đệm bảng chuyển vị."""
        # kiem tra timeout : neu het thoi gian thi tra ve danh gia hien tai con khong can tim nuoc di
        if self.stop_time is not None and time.time() > self.stop_time:
            return self.evaluate_board(), None
               
       
          # probe TT first
        h = self.zobrist_hash()
        tt_hit = self.tt.probe(h, depth, alpha, beta)
        if tt_hit is not None:
            val, best_move, flag = tt_hit
            return val, best_move

        if depth == 0 or self.board.is_game_over():
            val = self.evaluate_board()
            return val, None

        best_move = None
        if is_maximizing:
            max_eval = float('-inf')
            for move in self._order_moves_improved(depth):
                self.board.push(move)
                eval_score, _ = self.minimax_alpha_beta(depth - 1, alpha, beta, False)
                self.board.pop()
                
                if eval_score is None:
                    return None, None  # timeout occurred in deeper call
                
                if eval_score > max_eval:
                    max_eval = eval_score
                    best_move = move
                alpha = max(alpha, eval_score)
                if alpha >= beta:
                    if not self.board.is_capture(move):
                        self._record_killer(move, depth)
                        self._record_history(move, depth, bonus=1)
                    break
            
            # store in TT
            if max_eval <= alpha:
                flag = 'UPPER'
            elif max_eval >= beta:
                flag = 'LOWER'
            else:
                flag = 'EXACT'
            self.tt.store(h, depth, flag, max_eval, best_move)
            return max_eval, best_move
        else:
            min_eval = float('inf')
            for move in self._order_moves_improved(depth):
                self.board.push(move)
                eval_score, _ = self.minimax_alpha_beta(depth - 1, alpha, beta, True)
                self.board.pop()
                
                if eval_score is None:
                    return None, None  # timeout occurred in deeper call
                
                if eval_score < min_eval:
                    min_eval = eval_score
                    best_move = move
                beta = min(beta, eval_score)
                if alpha >= beta:
                    if not self.board.is_capture(move):
                        self._record_killer(move, depth)
                        self._record_history(move, depth, bonus=1)
                    break
            # store in TT
            if min_eval <= alpha:
                flag = 'UPPER'
            elif min_eval >= beta:
                flag = 'LOWER'
            else:
                flag = 'EXACT'
            self.tt.store(h, depth, flag, min_eval, best_move)
            return min_eval, best_move

    def best_move(self,depth=5,time_limit=3.0):
            """ dung iterative deepening de tim nuoc di tot nhat trong gioi han thoi gian """
            start = time.time()
            self.stop_time = start + time_limit
            best_move = None
            best_score = float('-inf')
            
            try:
                for depth in range(1,depth + 1):
                    if time.time() - start > time_limit:
                        break
                    score_move = None
                    score, mv = self.minimax_alpha_beta(depth, float('-inf'), float('inf'), True)
                    if score is None:
                        break
                    if mv is not None:
                        best_move = mv
                        best_score = score
                    if abs(best_score) >= 99999:
                        break
            finally:
                self.stop_time = None  # reset timeout
            return best_move

