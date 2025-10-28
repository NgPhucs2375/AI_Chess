import chess

class ChessEngine:
    def __init__(self):
        # start position
        self.board = chess.Board()
        # transposition cache (fen, depth, is_maximizing) -> (score, best_move)
        self.cache = {}

    def print_board(self):
        print(self.board)

    def evaluate_board(self):
        """Simplified and faster evaluation:
        - terminal checks
        - material + piece-square tables
        - mobility (attacks per piece)
        - pawn structure: doubled / isolated / passed
        - small center bonus
        """
        # fast terminal handling
        if self.board.is_checkmate():
            return -99999 if self.board.turn == chess.WHITE else 99999
        if self.board.is_stalemate() or self.board.is_insufficient_material():
            return 0

        piece_values = {
            chess.PAWN: 100,
            chess.KNIGHT: 320,
            chess.BISHOP: 330,
            chess.ROOK: 500,
            chess.QUEEN: 900,
            chess.KING: 20000
        }

        # keep the same PSTs as before (abbreviated names)
        PAWN_TABLE = [
            0, 0,  0,  0,  0,  0,  0,  0,
            5, 10, 10,-20,-20, 10, 10,  5,
            5, -5, -10, 0, 0,-10, -5,  5,
            0, 0, 0, 20, 20, 0, 0, 0,
            5, 5, 10, 25, 25, 10, 5, 5,
            10, 10, 20, 30, 30, 20, 10, 10,
            50, 50, 50, 50, 50, 50, 50, 50,
            0, 0, 0, 0, 0, 0, 0, 0
        ]

        KNIGHT_TABLE = [
            -50,-40,-30,-30,-30,-30,-40,-50,
            -40,-20, 0, 0, 0, 0,-20,-40,
            -30, 0, 10, 15, 15, 10, 0,-30,
            -30, 5, 15, 20, 20, 15, 5,-30,
            -30, 0, 15, 20, 20, 15, 0,-30,
            -30, 5, 10, 15, 15, 10, 5,-30,
            -40,-20, 0, 5, 5, 0,-20,-40,
            -50,-40,-30,-30,-30,-30,-40,-50
        ]

        BISHOP_TABLE = [
            -20,-10,-10,-10,-10,-10,-10,-20,
            -10, 0, 0, 0, 0, 0, 0,-10,
            -10, 0, 5, 10, 10, 5, 0,-10,
            -10, 5, 5, 10, 10, 5, 5,-10,
            -10, 0, 10, 10, 10, 10, 0,-10,
            -10, 10, 10, 10, 10, 10, 10,-10,
            -10, 5, 0, 0, 0, 0, 5,-10,
            -20,-10,-10,-10,-10,-10,-10,-20
        ]

        ROOK_TABLE = [
            0,  0,  0,  0,  0,  0,  0,  0,
            5, 10, 10, 10, 10, 10, 10,  5,
            -5,  0,  0,  0,  0,  0,  0, -5,
            -5,  0,  0,  0,  0,  0,  0, -5,
            -5,  0,  0,  0,  0,  0,  0, -5,
            -5,  0,  0,  0,  0,  0,  0, -5,
            -5,  0,  0,  0,  0,  0,  0, -5,
            0,  0,  0,  5,  5,  0,  0,  0
        ]

        QUEEN_TABLE = [
            -20,-10,-10, -5, -5,-10,-10,-20,
            -10,  0,  0,  0,  0,  0,  0,-10,
            -10,  0,  5,  5,  5,  5,  0,-10,
            -5,  0,  5,  5,  5,  5,  0, -5,
            0,  0,  5,  5,  5,  5,  0, -5,
            -10,  5,  5,  5,  5,  5,  0,-10,
            -10,  0,  5,  0,  0,  0,  0,-10,
            -20,-10,-10, -5, -5,-10,-10,-20
        ]

        KING_MID_TABLE = [
            -30,-40,-40,-50,-50,-40,-40,-30,
            -30,-40,-40,-50,-50,-40,-40,-30,
            -30,-40,-40,-50,-50,-40,-40,-30,
            -30,-40,-40,-50,-50,-40,-40,-30,
            -20,-30,-30,-40,-40,-30,-30,-20,
            -10,-20,-20,-20,-20,-20,-20,-10,
            20, 20,  0,  0,  0,  0, 20, 20,
            20, 30, 10,  0,  0, 10, 30, 20
        ]

        TABLES = {
            chess.PAWN: PAWN_TABLE,
            chess.KNIGHT: KNIGHT_TABLE,
            chess.BISHOP: BISHOP_TABLE,
            chess.ROOK: ROOK_TABLE,
            chess.QUEEN: QUEEN_TABLE,
            chess.KING: KING_MID_TABLE
        }

        score = 0

        # material + PST
        for sq in chess.SQUARES:
            piece = self.board.piece_at(sq)
            if not piece:
                continue
            val = piece_values[piece.piece_type]
            pst = TABLES[piece.piece_type]
            if piece.color == chess.WHITE:
                score += val + pst[sq]
            else:
                score -= val + pst[chess.square_mirror(sq)]

        # mobility: approximate by number of attacked squares by each piece (weighted)
        mobility_weights = {
            chess.PAWN: 0.05,
            chess.KNIGHT: 0.2,
            chess.BISHOP: 0.2,
            chess.ROOK: 0.25,
            chess.QUEEN: 0.15,
            chess.KING: 0.05
        }
        for sq in chess.SQUARES:
            piece = self.board.piece_at(sq)
            if not piece:
                continue
            attacks = len(self.board.attacks(sq))
            w = mobility_weights.get(piece.piece_type, 0)
            if piece.color == chess.WHITE:
                score += attacks * w
            else:
                score -= attacks * w

        # pawn structure: doubled, isolated, passed (simple and cheap)
        pawn_files_white = [chess.square_file(sq) for sq in self.board.pieces(chess.PAWN, chess.WHITE)]
        pawn_files_black = [chess.square_file(sq) for sq in self.board.pieces(chess.PAWN, chess.BLACK)]
        white_pawns = set(self.board.pieces(chess.PAWN, chess.WHITE))
        black_pawns = set(self.board.pieces(chess.PAWN, chess.BLACK))

        doubled_penalty = 25
        isolated_penalty = 20
        passed_bonus = 25

        # helper to check passed pawn (simple file+adjacent file check ahead)
        def is_passed(sq, color):
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
            # doubled
            if pawn_files_white.count(f) > 1:
                score -= doubled_penalty
            # isolated
            if not any(adj in pawn_files_white for adj in (f - 1, f + 1) if 0 <= adj <= 7):
                score -= isolated_penalty
            # passed
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

        # small center control bonus
        for sq in (chess.D4, chess.D5, chess.E4, chess.E5):
            p = self.board.piece_at(sq)
            if p:
                score += 30 if p.color == chess.WHITE else -30

        return int(score)

    def _order_moves(self):
        """Simple move ordering: captures/promotions first, then others."""
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
        key = (self.board.fen(), depth, is_maximizing)
        if key in self.cache:
            return self.cache[key]

        if depth == 0 or self.board.is_game_over():
            val = self.evaluate_board()
            self.cache[key] = (val, None)
            return val, None

        best_move = None
        if is_maximizing:
            max_eval = float('-inf')
            for move in self._order_moves():
                self.board.push(move)
                eval_score, _ = self.minimax_alpha_beta(depth - 1, alpha, beta, False)
                self.board.pop()
                if eval_score > max_eval:
                    max_eval = eval_score
                    best_move = move
                alpha = max(alpha, eval_score)
                if alpha >= beta:
                    break
            self.cache[key] = (max_eval, best_move)
            return max_eval, best_move
        else:
            min_eval = float('inf')
            for move in self._order_moves():
                self.board.push(move)
                eval_score, _ = self.minimax_alpha_beta(depth - 1, alpha, beta, True)
                self.board.pop()
                if eval_score < min_eval:
                    min_eval = eval_score
                    best_move = move
                beta = min(beta, eval_score)
                if alpha >= beta:
                    break
            self.cache[key] = (min_eval, best_move)
            return min_eval, best_move

    def best_move(self, depth=3):
        _, move = self.minimax_alpha_beta(depth, float('-inf'), float('inf'), True)
        return move

