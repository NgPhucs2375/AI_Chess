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
        if edepth < depth:
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

        material = self._material_eval()
        mobility = self._mobility_eval()
        pawn_struct = self._pawn_structure_eval()
        center = self._center_control_eval()
        king_safety = self._King_safety_eval()
        threats = self._threats_eval()
        
        # dùng trọng số để diều chỉnh và tái cấu trúc ảnh hưởng của các quân cờ vì nếu không thì máy sẽ ưu tiên phát triển trung tâm và khai mở vua hơn cả việc mất Ngựa :) điên vl
       
        score = (
            3.0 * material + 
            0.20 * mobility +
            0.30 * pawn_struct +
            0.10 * center +
            0.90 * king_safety +
            0.90 * threats
        )
        

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
        """Đánh giá các mối đe dọa trên bàn cờ (sửa double-count)."""
        score = 0
        piece_values = self.piece_values
        for sq in chess.SQUARES:
            piece = self.board.piece_at(sq)
            if not piece:
                continue
            attackers = self.board.attackers(not piece.color, sq)
            defenders = self.board.attackers(piece.color, sq)

            # penalty nếu bị tấn công mà không có người bảo vệ
            if attackers and not defenders:
                pen = self.piece_values[piece.piece_type] * 1.2
                if piece.color == chess.WHITE:
                    score -= pen
                else:
                    score += pen

            # reward nếu ta tấn công vật hơn kẻ địch tấn công
            for at in attackers:
                attackers_piece = self.board.piece_at(at)
                if attackers_piece:
                    target = piece
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
        # nếu thiếu thông tin thì không đánh giá
        if not victim or not attacker:
            return 0
        v = self.piece_values.get(victim.piece_type,0)
        a = self.piece_values.get(attacker.piece_type,0)
        return 10000 + (v*10 - a)
    
    def static_exchange_eval(self, move):
        """Approximate full SEE by simulating captures on a copied board.
        Trả về giá trị vật chất ròng (>=0 có lợi, <0 bất lợi)."""
        # only meaningful for captures
        if not self.board.is_capture(move):
            return 0

        try:
            sim = self.board.copy()
        except Exception:
            # fallback to push/pop on original board if copy not available (rare)
            self.board.push(move)
            val = self.piece_values.get(self.board.piece_at(move.to_square).piece_type, 0) if self.board.piece_at(move.to_square) else 0
            self.board.pop()
            return val

        # initial victim value (what move captures)
        victim_piece = self.board.piece_at(move.to_square)
        if victim_piece is None and self.board.is_en_passant(move):
            # en-passant victim square (behind to_square)
            ep_sq = move.to_square + ( -8 if self.board.turn == chess.WHITE else 8 )
            victim_piece = self.board.piece_at(ep_sq)
        victim_value = self.piece_values.get(victim_piece.piece_type, 0) if victim_piece else 0

        gains = [victim_value]

        # play the initial move on simulation board
        try:
            sim.push(move)
        except Exception:
            # illegal weird move: treat as neutral
            return 0

        target = move.to_square
        side = sim.turn  # opponent to move now

        # simulate sequence of cheapest recaptures until none left
        while True:
            # collect legal captures that land on target square
            captures = [m for m in sim.legal_moves if m.to_square == target and sim.is_capture(m)]
            if not captures:
                break
            # choose attacker with least material (cheapest attacker)
            def attacker_value(mv):
                p = sim.piece_at(mv.from_square)
                return self.piece_values.get(p.piece_type, 0) if p else 0
            best = min(captures, key=attacker_value)
            # value of piece that will be captured by this recapture
            captured = sim.piece_at(best.to_square)
            cap_val = self.piece_values.get(captured.piece_type, 0) if captured else 0
            gains.append(cap_val)
            sim.push(best)
            side = sim.turn

        # minimax-like resolution of gains to get net material outcome
        net = 0
        for g in reversed(gains):
            net = g - max(0, net)

        return net

    def _order_moves_improved(self, depth):
        """Improved ordering: TT best move, MVV-LVA, promotions, killers, history,
           and penalize captures that SEE says are losing."""
        moves = list(self.board.legal_moves)

        # TT best move
        key_tt = None
        try:
            h = self.zobrist_hash()
            tt_entry = self.tt.table.get(h)
            if tt_entry:
                key_tt = tt_entry[3]
        except Exception:
            key_tt = None

        # precompute attackers of our pieces for defensive bonuses
        my_color = self.board.turn
        attackers_of_my = set()
        for sq, pc in self.board.piece_map().items():
            if pc.color == my_color:
                attackers_of_my.update(self.board.attackers(not my_color, sq))

        k1, k2 = self.killers.get(depth, [None, None])

        def score_move(m):
            s = 0
            if key_tt is not None and m == key_tt:
                s += 100000
            s += self._mvv_lva_value(m)
            if m.promotion:
                s += 8000
            if m == k1:
                s += 5000
            elif m == k2:
                s += 4000
            s += self.history.get((m.from_square, m.to_square), 0)

            # Defensive bonuses
            if self.is_hanging(m.from_square):
                s += 600
            if self.board.is_capture(m) and m.to_square in attackers_of_my:
                s += 1200
            for atk_sq in attackers_of_my:
                # moving to square that attacks an attacker
                if atk_sq in self.board.attacks(m.to_square):
                    s += 800
                    break

            # Use SEE: if capture is losing on exchange, heavily penalize
            if self.board.is_capture(m):
                see_val = self.static_exchange_eval(m)
                if see_val < 0:
                    s -= 20000  # deprioritize losing captures strongly
                else:
                    # small bonus for winning captures
                    s += min(2000, see_val * 8)

            return -s  # sort ascending, negate to prefer larger s

        moves.sort(key=score_move)
        return moves

    def _record_killer(self,move,depth):
        """Luu nuoc di killer vao danh sach killer moves"""
        k1,k2 = self.killers.get(depth,(None,None))
        if k1 is None:
            self.killers[depth][0] = move
            return
        elif move != k1:
            self.killers[depth][1] = k1  # dich chuyen killer 1 xuong killer 2
            self.killers[depth][0] = move  # luu nuoc di hien tai vao killer 1
    
    def _record_history(self,move,depth,bonus=1): # truyen vao 4 tham so bao gom
        """Cập nhật bảng lịch sử cho nước đi"""
        key = (move.from_square, move.to_square) # tao key tu nuoc di va o den de cap nhat vao history de tang toc do alpha-beta
        self.history[key] += bonus * (2 ** depth) # tang diem cho nuoc di trong history heuristic
    
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

    def qsearch(self, alpha, beta, is_maximizing):
        """Tìm kiếm tĩnh (Quiescence Search) để giải quyết hiệu ứng chân trời. Hàm này chỉ xem xét các nước đi "ồn ào" (ăn quân, phong cấp)."""
    
        # 1. Kiểm tra timeout (quan trọng)
        if self.stop_time is not None and time.time() > self.stop_time:
            return None # Tín hiệu timeout

        # 2. Lấy điểm "Stand-pat" (điểm "đứng yên" nếu không làm gì)
        # Đây là điểm số nếu người chơi chọn không thực hiện nước đi ồn ào nào.
        stand_pat_score = self.evaluate_board()

        # 3. Cắt tỉa Alpha-Beta ban đầu
        if is_maximizing:
            if stand_pat_score >= beta:
                return stand_pat_score # Cắt tỉa Beta
            
            alpha = max(alpha, stand_pat_score)
            max_eval = stand_pat_score # Điểm tốt nhất ban đầu là điểm đứng yên
        else: # is_minimizing
            if stand_pat_score <= alpha:
                return stand_pat_score # Cắt tỉa Alpha
            beta = min(beta, stand_pat_score)
            min_eval = stand_pat_score # Điểm tốt nhất ban đầu là điểm đứng yên

        # 4. Tạo và sắp xếp các nước đi "ồn ào"
        # Chỉ lấy nước ăn quân (capture) và phong cấp (promotion)
        noisy_moves = [m for m in self.board.legal_moves if m.promotion is not None or self.board.is_capture(m)]
        
        # Sắp xếp nhanh bằng MVV-LVA (đã có trong _mvv_lva_value)
        noisy_moves.sort(key=lambda m: -self._mvv_lva_value(m))

        # 5. Duyệt các nước đi ồn ào (Logic tương tự minimax)
        for move in noisy_moves:
        # Lọc SEE: Bỏ qua các nước ăn quân rõ ràng là lỗ
            if self.board.is_capture(move) and self.static_exchange_eval(move) < 0:
                continue 

            self.board.push(move)
            # Gọi đệ quy qsearch, lật is_maximizing
            eval_score = self.qsearch(alpha, beta, not is_maximizing) 
            self.board.pop()

            if eval_score is None:
                return None # Lan truyền tín hiệu timeout

        # Cập nhật điểm số
            if is_maximizing:
                if eval_score > max_eval:
                    max_eval = eval_score
                alpha = max(alpha, eval_score)
                if alpha >= beta:
                    break # Cắt tỉa Beta
            else: # is_minimizing
                if eval_score < min_eval:
                    min_eval = eval_score
                beta = min(beta, eval_score)
                if alpha >= beta:
                    break # Cắt tỉa Alpha

        # 6. Trả về điểm số cuối cùng
        return max_eval if is_maximizing else min_eval

    def minimax_alpha_beta(self, depth, alpha, beta, is_maximizing):
        """Minimax với cắt tỉa alpha-beta và bộ nhớ đệm bảng chuyển vị."""
        
        if self.stop_time is not None and time.time() > self.stop_time:
            return self.evaluate_board(), None

        h = self.zobrist_hash() # tinh hash hien tai
        tt_hit = self.tt.probe(h, depth, alpha, beta) # tra bang TT
        
        
        """ Nếu tìm thấy trong TT, trả về giá trị và nước đi tốt nhất."""
        if tt_hit is not None:
            val, best_move, flag = tt_hit
            return val, best_move


        """Nếu trò chơi kết thúc, đánh giá ngay."""
        if self.board.is_game_over():
            val = self.evaluate_board()
            return val, None

        """Nếu đạt độ sâu 0, chuyển sang Tìm kiếm Tĩnh (QSearch)."""
        if depth == 0:
             # qsearch sẽ trả về điểm số (hoặc None nếu timeout)
            val = self.qsearch(alpha, beta, is_maximizing) 
             # qsearch không trả về best_move, chỉ trả về điểm
            return val, None

        best_move = None
        alpha_orig, beta_orig = alpha, beta   # <-- giữ giá trị ban đầu
        
        """Minimax với cắt tỉa alpha-beta."""
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
            # store in TT: dùng alpha_orig/beta_orig để quyết flag
            if max_eval <= alpha_orig:
                flag = 'UPPER'
            elif max_eval >= beta_orig:
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
            # store in TT: dùng alpha_orig/beta_orig để quyết flag
            if min_eval <= alpha_orig:
                flag = 'UPPER'
            elif min_eval >= beta_orig:
                flag = 'LOWER'
            else:
                flag = 'EXACT'
            self.tt.store(h, depth, flag, min_eval, best_move)
            return min_eval, best_move

    def best_move(self,depth=6,time_limit=5.0): # hehe tang depth de bot khong len tam 5 la no may roi cai con lai la thoi gian bot phan hoi trong khoang time do lay toi uu nhat tinh ra dc
            """ Test depth = 3–4 thôi.

                Quan sát xem bot có còn “thí quân” không.

                Nếu nó chơi quá bị động → tăng hệ số mobility và center.

                Nếu nó vẫn thí quân → tăng material lên 1.2 hoặc 1.5. """
                
            """ dung iterative deepening de tim nuoc di tot nhat trong gioi han thoi gian """
            start = time.time()
            self.stop_time = start + time_limit
            best_move = None
            best_score = float('-inf')
            # Reset heuristic cho lượt tìm kiếm mới
            self.killers.clear()
            self.history.clear()
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


    def is_hanging(self, square):
        """True nếu ô có quân ta bị tấn công nhưng không được bảo vệ."""
        piece = self.board.piece_at(square)
        if not piece:
            return False
        attackers = self.board.attackers(not piece.color, square)
        if not attackers:
            return False
        defenders = self.board.attackers(piece.color, square)
        return len(defenders) == 0

