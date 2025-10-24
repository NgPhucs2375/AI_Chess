# ui.py
import pygame
import os
import sys
from copy import deepcopy
import json

# --- Cấu hình cơ bản ---
WIDTH, HEIGHT = 740, 740
ROWS, COLS = 8, 8
SQUARE_SIZE = WIDTH // COLS

# --- Màu sắc ---
WHITE = (240, 240, 210)   # ô sáng
BROWN = (181, 136, 99)    # ô tối
HIGHLIGHT = (255, 223, 0)
MOVE_HINT = (50, 205, 50)  # màu gợi ý nước đi
CHECK_HIGHLIGHT = (255, 80, 80)

pygame.font.init()
FONT = pygame.font.SysFont('Arial', 18)

pygame.init()
# expand window immediately to include move history panel
PANEL_WIDTH = 200
screen = pygame.display.set_mode((WIDTH + PANEL_WIDTH, HEIGHT))
pygame.display.set_caption("Chess - UI with Full Rules (Castling/EnPassant/Check)")
clock = pygame.time.Clock()

# --- hình ảnh quân cờ ---
pieces = {}
piece_types = [
    "wp", "wr", "wn", "wb", "wq", "wk",
    "bp", "br", "bn", "bb", "bq", "bk"
]

try:
    # Use absolute path to avoid encoding issues
    script_dir = os.path.dirname(os.path.abspath(__file__))
    images_dir = os.path.join(script_dir, "images")
    
    for piece in piece_types:
        img_path = os.path.join(images_dir, f"{piece}.png")
        if not os.path.exists(img_path):
            raise FileNotFoundError(f"Image not found: {img_path}")
        image = pygame.image.load(img_path)
        image = pygame.transform.scale(image, (SQUARE_SIZE, SQUARE_SIZE))
        pieces[piece] = image
except Exception as e:
    print(f"Error loading images: {e}")
    sys.exit(1)

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

# --- GameState để quản lý trạng thái và luật ---
class GameState:
    def __init__(self):
        self.board = [row[:] for row in starting_board]
        self.white_to_move = True
        # castling rights: [white_kingside, white_queenside, black_kingside, black_queenside]
        self.castling_rights = [True, True, True, True]
        self.en_passant = None  # square tuple where en-passant capture is allowed (row,col) or None
        self.move_log = []  # list of move dicts
        self.update_king_positions()
        self.move_history = []  # Lưu các nước đi dạng ký hiệu e2->e4, Nf3...


    def update_king_positions(self):
        self.white_king_pos = None
        self.black_king_pos = None
        for r in range(8):
            for c in range(8):
                p = self.board[r][c]
                if p == "wk":
                    self.white_king_pos = (r,c)
                elif p == "bk":
                    self.black_king_pos = (r,c)

    def in_bounds(self, r, c):
        return 0 <= r < ROWS and 0 <= c < COLS

    def is_white(self, piece):
        return piece != "" and piece[0] == "w"

    def is_black(self, piece):
        return piece != "" and piece[0] == "b"

    # returns True if square (r,c) is attacked by color ('w' or 'b')
    def is_square_attacked(self, r, c, by_color):
        # pawn attacks
        if by_color == 'w':
            for dc in (-1, 1):
                rr, cc = r+1, c+dc  # white pawns attack downward on board array? careful: we use row0 top - white starts at bottom -> white pawns move up (r-1). Attack squares for white are r-1,c+-1
            # correct: white pawns move up (decrease row). So attacks are (r-1, c+-1)
            pass

        # implement properly below
        # pawns
        if by_color == 'w':
            for dc in (-1, 1):
                rr = r + 1  # if checking if square r,c is attacked by white pawn, that pawn must be at r+1 (one row below)
                cc = c + dc
                if self.in_bounds(rr, cc) and self.board[rr][cc] == 'wp':
                    return True
        else:
            for dc in (-1, 1):
                rr = r - 1  # black pawn would be at r-1 (one row above) to attack r,c
                cc = c + dc
                if self.in_bounds(rr, cc) and self.board[rr][cc] == 'bp':
                    return True

        # knights
        deltas = [(2,1),(1,2),(-1,2),(-2,1),(-2,-1),(-1,-2),(1,-2),(2,-1)]
        for dr,dc in deltas:
            rr,cc = r+dr, c+dc
            if self.in_bounds(rr,cc):
                p = self.board[rr][cc]
                if p != "" and p[1] == 'n' and ((by_color=='w' and p[0]=='w') or (by_color=='b' and p[0]=='b')):
                    return True

        # sliding pieces: rook/queen (orthogonal)
        orth = [(1,0),(-1,0),(0,1),(0,-1)]
        for dr,dc in orth:
            rr,cc = r+dr, c+dc
            while self.in_bounds(rr,cc):
                p = self.board[rr][cc]
                if p != "":
                    if (by_color=='w' and p[0]=='w') or (by_color=='b' and p[0]=='b'):
                        if p[1] in ('r','q'):
                            return True
                        else:
                            break
                    else:
                        break
                rr += dr; cc += dc

        # diagonal sliding: bishop/queen
        diag = [(1,1),(1,-1),(-1,1),(-1,-1)]
        for dr,dc in diag:
            rr,cc = r+dr, c+dc
            while self.in_bounds(rr,cc):
                p = self.board[rr][cc]
                if p != "":
                    if (by_color=='w' and p[0]=='w') or (by_color=='b' and p[0]=='b'):
                        if p[1] in ('b','q'):
                            return True
                        # also pawn check for immediate diagonal (already handled above), king adjacency check below
                        else:
                            break
                    else:
                        break
                rr += dr; cc += dc

        # king adjacency
        for dr in (-1,0,1):
            for dc in (-1,0,1):
                if dr==0 and dc==0:
                    continue
                rr,cc = r+dr, c+dc
                if self.in_bounds(rr,cc):
                    p = self.board[rr][cc]
                    if p != "" and p[1] == 'k' and ((by_color=='w' and p[0]=='w') or (by_color=='b' and p[0]=='b')):
                        return True

        return False

    # Generate pseudo-legal moves for a piece at r, c (does not check for leaving king in check)
    def generate_piece_moves(self, r, c):
        piece = self.board[r][c]
        if piece == "":
            return []
        color = piece[0]
        ptype = piece[1]
        moves = []

        def add_if_empty_or_capture(rr,cc):
            if not self.in_bounds(rr,cc):
                return
            target = self.board[rr][cc]
            if target == "" or (color=='w' and target[0]=='b') or (color=='b' and target[0]=='w'):
                moves.append(((r,c),(rr,cc), False))  # (from,to, is_en_passant placeholder)

        # Pawn
        if ptype == 'p':
            direction = -1 if color == 'w' else 1
            start_row = 6 if color == 'w' else 1
            # forward 1
            fr = r + direction
            if self.in_bounds(fr, c) and self.board[fr][c] == "":
                moves.append(((r,c),(fr,c), False))
                # forward 2
                fr2 = r + 2*direction
                if r == start_row and self.in_bounds(fr2,c) and self.board[fr2][c] == "":
                    moves.append(((r,c),(fr2,c), False))
            # captures
            for dc in (-1,1):
                rr = r + direction
                cc = c + dc
                if self.in_bounds(rr,cc):
                    targ = self.board[rr][cc]
                    if targ != "" and ((color=='w' and targ[0]=='b') or (color=='b' and targ[0]=='w')):
                        moves.append(((r,c),(rr,cc), False))
            # en-passant capture
            if self.en_passant:
                ep_r, ep_c = self.en_passant
                # If en-passant target is diagonally adjacent
                if ep_r == r + direction and abs(ep_c - c) == 1:
                    moves.append(((r,c),(ep_r,ep_c), True))  # mark as en-passant

        # Knight
        elif ptype == 'n':
            deltas = [(2,1),(1,2),(-1,2),(-2,1),(-2,-1),(-1,-2),(1,-2),(2,-1)]
            for dr,dc in deltas:
                rr,cc = r+dr, c+dc
                add_if_empty_or_capture(rr,cc)

        # Sliding: rook, bishop, queen
        elif ptype in ('r','b','q'):
            dirs = []
            if ptype in ('r','q'):
                dirs += [(1,0),(-1,0),(0,1),(0,-1)]
            if ptype in ('b','q'):
                dirs += [(1,1),(1,-1),(-1,1),(-1,-1)]
            for dr,dc in dirs:
                rr,cc = r+dr, c+dc
                while self.in_bounds(rr,cc):
                    targ = self.board[rr][cc]
                    if targ == "":
                        moves.append(((r,c),(rr,cc), False))
                    else:
                        if (color=='w' and targ[0]=='b') or (color=='b' and targ[0]=='w'):
                            moves.append(((r,c),(rr,cc), False))
                        break
                    rr += dr; cc += dc

        # King
        elif ptype == 'k':
            for dr in (-1,0,1):
                for dc in (-1,0,1):
                    if dr==0 and dc==0:
                        continue
                    rr,cc = r+dr, c+dc
                    add_if_empty_or_capture(rr,cc)
            # castling
            if color == 'w' and r==7 and c==4:
                wk_side, wq_side = self.castling_rights[0], self.castling_rights[1]
                # kingside white: rook at (7,7), squares (7,5),(7,6) empty, not attacked, not in check
                if wk_side and self.board[7][7] == 'wr' and self.board[7][5]=="" and self.board[7][6]=="":
                    if not self.in_check('w') and not self.is_square_attacked(7,5,'b') and not self.is_square_attacked(7,6,'b'):
                        moves.append(((r,c),(7,6), "castle_k"))
                # queenside white: rook at (7,0), squares (7,1),(7,2),(7,3)
                if wq_side and self.board[7][0] == 'wr' and self.board[7][1]=="" and self.board[7][2]=="" and self.board[7][3]=="":
                    if not self.in_check('w') and not self.is_square_attacked(7,3,'b') and not self.is_square_attacked(7,2,'b'):
                        moves.append(((r,c),(7,2), "castle_q"))
            if color == 'b' and r==0 and c==4:
                bk_side, bq_side = self.castling_rights[2], self.castling_rights[3]
                if bk_side and self.board[0][7] == 'br' and self.board[0][5]=="" and self.board[0][6]=="":
                    if not self.in_check('b') and not self.is_square_attacked(0,5,'w') and not self.is_square_attacked(0,6,'w'):
                        moves.append(((r,c),(0,6), "castle_k"))
                if bq_side and self.board[0][0] == 'br' and self.board[0][1]=="" and self.board[0][2]=="" and self.board[0][3]=="":
                    if not self.in_check('b') and not self.is_square_attacked(0,3,'w') and not self.is_square_attacked(0,2,'w'):
                        moves.append(((r,c),(0,2), "castle_q"))

        return moves

    # is side in check?
    def in_check(self, color):
        self.update_king_positions()
        king_pos = self.white_king_pos if color=='w' else self.black_king_pos
        if king_pos is None:
            return False
        r,c = king_pos
        return self.is_square_attacked(r,c, 'b' if color=='w' else 'w')

    def is_insufficient_material(self):
        """Return True if position is insufficient mating material under a simple rule:
        - only two kings remain, OR
        - two kings and a single minor piece (bishop or knight) remain.
        This matches the requested rule: draw when only 2 kings and 1 bishop or knight.
        """
        pieces = []
        for r in range(8):
            for c in range(8):
                p = self.board[r][c]
                if p != "":
                    pieces.append(p)

        # count kings and non-king pieces
        kings = [p for p in pieces if p[1] == 'k']
        others = [p for p in pieces if p[1] != 'k']

        # only two kings
        if len(kings) == 2 and len(others) == 0:
            return True

        # two kings and a single minor piece (bishop or knight)
        if len(kings) == 2 and len(others) == 1 and others[0][1] in ('b', 'n'):
            return True

        return False

    # get all legal moves for side to move (filters out those leaving king in check)
    def get_all_legal_moves(self):
        moves = []
        color = 'w' if self.white_to_move else 'b'
        for r in range(8):
            for c in range(8):
                p = self.board[r][c]
                if p != "" and p[0] == color:
                    pseudo = self.generate_piece_moves(r,c)
                    for mv in pseudo:
                        # mv is ((fr,fc),(tr,tc), flag)
                        if self.is_legal_move(mv):
                            moves.append(mv)
        return moves

    # apply move (assumes legal). Move struct: ((fr,fc),(tr,tc), flag)
    def make_move(self, move, promotion_choice=None):
        (fr,fc),(tr,tc),flag = move
        moving = self.board[fr][fc]

        # FIRST: check if this move would require promotion (without changing board)
        if moving != "" and moving[1] == 'p':
            # white promotes on row 0, black on row 7
            if (moving[0] == 'w' and tr == 0) or (moving[0] == 'b' and tr == 7):
                # if no promotion choice provided, signal that promotion is required
                if promotion_choice is None:
                    return None  # caller should handle promotion UI and call again with choice

        # Now apply the move (promotion_choice present or not needed)
        captured = None
        is_en_passant = False
        is_castle = False
        promotion = None

        # en-passant capture handling
        if flag is True:
            is_en_passant = True
            cap_r = fr
            cap_c = tc
            captured = self.board[cap_r][cap_c]
            self.board[cap_r][cap_c] = ""
        else:
            captured = self.board[tr][tc]

        # move piece
        self.board[tr][tc] = moving
        self.board[fr][fc] = ""

        # Pawn promotion - handle now that piece moved
        if moving[1] == 'p':
            if (moving[0] == 'w' and tr == 0) or (moving[0] == 'b' and tr == 7):
                if promotion_choice:
                    promotion = moving[0] + promotion_choice
                    self.board[tr][tc] = promotion
                else:
                    # Should not happen because we checked earlier; but safe-guard
                    return None

        # castling handling
        if flag == "castle_k":
            is_castle = True
            if moving == 'wk':
                self.board[7][5] = 'wr'; self.board[7][7] = ""
            elif moving == 'bk':
                self.board[0][5] = 'br'; self.board[0][7] = ""
        elif flag == "castle_q":
            is_castle = True
            if moving == 'wk':
                self.board[7][3] = 'wr'; self.board[7][0] = ""
            elif moving == 'bk':
                self.board[0][3] = 'br'; self.board[0][0] = ""

        # update castling rights etc. (unchanged)
        def revoke_castle_for(piece, r_src, c_src):
            if piece == 'wk':
                self.castling_rights[0] = False
                self.castling_rights[1] = False
            if piece == 'bk':
                self.castling_rights[2] = False
                self.castling_rights[3] = False
            if piece == 'wr':
                if r_src == 7 and c_src == 7: self.castling_rights[0] = False
                if r_src == 7 and c_src == 0: self.castling_rights[1] = False
            if piece == 'br':
                if r_src == 0 and c_src == 7: self.castling_rights[2] = False
                if r_src == 0 and c_src == 0: self.castling_rights[3] = False

        revoke_castle_for(moving, fr, fc)
        if captured in ('wr','br'):
            revoke_castle_for(captured, tr, tc)

        prev_en_passant = self.en_passant
        if moving[1] == 'p' and abs(tr - fr) == 2:
            ep_row = (fr + tr) // 2
            self.en_passant = (ep_row, fc)
        else:
            self.en_passant = None

        self.move_log.append({
            'move': move,
            'moving': moving,
            'captured': captured,
            'is_en_passant': is_en_passant,
            'is_castle': is_castle,
            'promotion': promotion,
            'prev_en_passant': prev_en_passant,
            'prev_castling': tuple(self.castling_rights)
        })

        # Build notation and update move_history (unchanged existing logic)
        fr0, fc0 = move[0]
        tr0, tc0 = move[1]
        def sq(col, row):
            return f"{chr(col+97)}{8-row}"

        if flag == "castle_k":
            notation = "O-O"
        elif flag == "castle_q":
            notation = "O-O-O"
        else:
            ptype = moving[1]
            captured_marker = 'x' if captured and captured != "" and not is_en_passant else ''
            if ptype == 'p':
                if captured_marker:
                    notation = f"{chr(fc0+97)}{captured_marker}{sq(tc0,tr0)}"
                else:
                    notation = f"{sq(tc0,tr0)}"
            else:
                piece_letter = {'n':'N','b':'B','r':'R','q':'Q','k':'K'}.get(ptype, ptype.upper())
                notation = f"{piece_letter}{captured_marker}{sq(tc0,tr0)}"
            if promotion:
                notation += f"={promotion[1].upper()}"

        opponent = 'b' if moving[0] == 'w' else 'w'
        self.white_to_move = not self.white_to_move
        opp_moves = self.get_all_legal_moves()
        self.white_to_move = not self.white_to_move
        self.update_king_positions()
        if self.in_check(opponent):
            if not opp_moves:
                notation += '#'
            else:
                notation += '+'

        self.move_history.append(notation)
        self.update_king_positions()
        self.white_to_move = not self.white_to_move
        return True

    def is_legal_move(self, move):
        """Check if move is legal (doesn't leave king in check)"""
        (fr,fc),(tr,tc),flag = move
        
        # Make move on temporary board
        piece = self.board[fr][fc]
        captured = self.board[tr][tc]
        self.board[fr][fc] = ""
        self.board[tr][tc] = piece
        
        # Special handling for en-passant
        ep_capture = None
        if flag is True:  # en-passant
            ep_capture = self.board[fr][tc]
            self.board[fr][tc] = ""
            
        # Check if king is in check
        color = piece[0]
        is_legal = not self.in_check(color)
        
        # Undo move
        self.board[fr][fc] = piece
        self.board[tr][tc] = captured
        if ep_capture:
            self.board[fr][tc] = ep_capture
            
        return is_legal

    def to_dict(self):
        """Serialize game state to dict for saving"""
        return {
            'board': [row[:] for row in self.board],
            'white_to_move': self.white_to_move,
            'castling_rights': list(self.castling_rights),
            'en_passant': list(self.en_passant) if self.en_passant else None,
            'move_log': self.move_log,
            'move_history': self.move_history
        }
        
    def load_from_dict(self, data):
        """Load game state from dict"""
        self.board = [row[:] for row in data['board']]
        self.white_to_move = data['white_to_move']
        self.castling_rights = list(data['castling_rights'])
        self.en_passant = tuple(data['en_passant']) if data['en_passant'] else None
        self.move_log = data['move_log']
        self.move_history = data['move_history']
        self.update_king_positions()

# --- Vẽ bàn cờ và quân cờ ---
def draw_board(screen, gs, valid_moves):
    # Vẽ ô vuông
    for r in range(ROWS):
        for c in range(COLS):
            color = WHITE if (r + c) % 2 == 0 else BROWN
            pygame.draw.rect(screen, color, pygame.Rect(c * SQUARE_SIZE, r * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))

    # Vẽ quân cờ
    for r in range(ROWS):
        for c in range(COLS):
            piece = gs.board[r][c]
            if piece != "":
                screen.blit(pieces[piece], pygame.Rect(c * SQUARE_SIZE, r * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))

    # Vẽ nước đi hợp lệ
    if valid_moves:
        for move in valid_moves:
            r, c = move
            pygame.draw.rect(screen, MOVE_HINT, pygame.Rect(c * SQUARE_SIZE, r * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE), 3)

# --- Vẽ lịch sử nước đi ---
def draw_move_history(screen, move_history):
    # background
    pygame.draw.rect(screen, WHITE, pygame.Rect(WIDTH, 0, PANEL_WIDTH, HEIGHT))
    font = pygame.font.SysFont('Arial', 14)
    y = 10
    for i, move in enumerate(move_history):
        text = font.render(f"{i+1}. {move}", True, (0, 0, 0))
        screen.blit(text, (WIDTH + 10, y))
        y += 20

# --- Vẽ menu chọn quân cờ thăng cấp ---
PROMOTION_PIECE_SIZE = 50
PROMOTION_PADDING = 10
def draw_promotion_menu(turn, menu_x):
    piece_codes = ['q', 'r', 'b', 'n']  # quân cờ có thể chọn để thăng cấp
    colors = {'w': (255, 255, 255), 'b': (0, 0, 0)}
    # background
    # compute background width to fit all choices and paddings, then draw centered bg at menu_x
    bg_w = len(piece_codes) * PROMOTION_PIECE_SIZE + (len(piece_codes) + 1) * PROMOTION_PADDING
    bg_h = PROMOTION_PIECE_SIZE + 2 * PROMOTION_PADDING
    pygame.draw.rect(screen, WHITE, pygame.Rect(menu_x, HEIGHT//2 - bg_h//2, bg_w, bg_h))
    piece_positions = []
    for i, code in enumerate(piece_codes):
        # piece_color must be 'w' or 'b' to match keys in `pieces` (e.g., 'wq', 'bq')
        piece_color = 'w' if turn == 'w' else 'b'
        img = pieces[piece_color + code]
        x = menu_x + PROMOTION_PADDING + (i * (PROMOTION_PIECE_SIZE + PROMOTION_PADDING))
        y = HEIGHT//2 - PROMOTION_PIECE_SIZE//2 + PROMOTION_PADDING
        screen.blit(img, pygame.Rect(x, y, PROMOTION_PIECE_SIZE, PROMOTION_PIECE_SIZE))
        # return the single-letter code (lowercase) as the promotion choice expected by GameState.make_move
        piece_positions.append((pygame.Rect(x, y, PROMOTION_PIECE_SIZE, PROMOTION_PIECE_SIZE), code))
    return piece_positions

# --- Hàm chính khởi động game ---
def main():
    gs = GameState()
    selected_square = None
    valid_moves_list = []
    target_map = {}
    awaiting_promotion = None  # store (move, from_square) waiting for choice
    game_over = False

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = pygame.mouse.get_pos()

                # If waiting promotion: check clicks on promotion menu
                if awaiting_promotion:
                    move_pending = awaiting_promotion
                    # compute menu rects same as draw_promotion_menu
                    bg_w = 4 * PROMOTION_PIECE_SIZE + 5 * PROMOTION_PADDING
                    menu_x = (WIDTH - bg_w) // 2
                    piece_positions = draw_promotion_menu(
                        'w' if gs.white_to_move else 'b', menu_x)
                    # piece_positions are rects in screen coords; check click
                    for rect, piece_code in piece_positions:
                        if rect.collidepoint(mx, my):
                            # apply move with chosen promotion piece
                            gs.make_move(move_pending, promotion_choice=piece_code)
                            awaiting_promotion = None
                            selected_square = None
                            valid_moves_list = []
                            target_map = {}
                            break
                    continue  # ignore other clicks while choosing promotion

                # compute board square clicked
                if mx < WIDTH:
                    row = my // SQUARE_SIZE
                    col = mx // SQUARE_SIZE
                    clicked = (row, col)
                    if selected_square == clicked:
                        selected_square = None
                        valid_moves_list = []
                        target_map = {}
                    else:
                        if selected_square is None:
                            p = gs.board[row][col]
                            if p != "" and ((p[0]=='w' and gs.white_to_move) or (p[0]=='b' and not gs.white_to_move)):
                                selected_square = clicked
                                # generate legal moves
                                legal = []
                                pseudo = gs.generate_piece_moves(row, col)
                                for mv in pseudo:
                                    if gs.is_legal_move(mv):
                                        legal.append(mv)
                                valid_moves_list = [mv[1] for mv in legal]
                                target_map = {mv[1]: mv for mv in legal}
                        else:
                            # attempt to move
                            if clicked in target_map:
                                mv = target_map[clicked]
                                # check if move requires promotion BEFORE calling make_move
                                fr,fc = mv[0]; tr,tc = mv[1]
                                moving = gs.board[fr][fc]
                                if moving != "" and moving[1] == 'p' and ((moving[0]=='w' and tr==0) or (moving[0]=='b' and tr==7)):
                                    # need promotion choice from user
                                    awaiting_promotion = mv
                                else:
                                    gs.make_move(mv)
                                    selected_square = None
                                    valid_moves_list = []
                                    target_map = {}
                                    # after move, check for insufficient-material draw
                                    if gs.is_insufficient_material():
                                        print("Draw by insufficient material (only kings and at most one minor piece).")
                                        pygame.display.set_caption("Draw by insufficient material")
                                        game_over = True
                                        running = False
                            else:
                                # clicked other square: maybe select new piece
                                p = gs.board[row][col]
                                if p != "" and ((p[0]=='w' and gs.white_to_move) or (p[0]=='b' and not gs.white_to_move)):
                                    selected_square = clicked
                                    legal = []
                                    pseudo = gs.generate_piece_moves(row, col)
                                    for mv in pseudo:
                                        if gs.is_legal_move(mv):
                                            legal.append(mv)
                                    valid_moves_list = [mv[1] for mv in legal]
                                    target_map = {mv[1]: mv for mv in legal}
                                else:
                                    selected_square = None
                                    valid_moves_list = []
                                    target_map = {}

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_s:
                    save_game(gs)
                elif event.key == pygame.K_l:
                    loaded = load_game()
                    if loaded:
                        gs = loaded
                        selected_square = None
                        valid_moves_list = []
                        target_map = {}

        # --- Vẽ bàn cờ và quân cờ ---
        draw_board(screen, gs, valid_moves_list)

        # --- Vẽ lịch sử nước đi ---
        draw_move_history(screen, gs.move_history)

        # Nếu đang chờ người chơi chọn quân để phong: vẽ overlay và menu phong
        if awaiting_promotion:
            # semi-transparent overlay to indicate modal state
            overlay = pygame.Surface((WIDTH, HEIGHT))
            overlay.set_alpha(160)
            overlay.fill((0, 0, 0))
            screen.blit(overlay, (0, 0))
            bg_w = 4 * PROMOTION_PIECE_SIZE + 5 * PROMOTION_PADDING
            menu_x = (WIDTH - bg_w) // 2
            draw_promotion_menu('w' if gs.white_to_move else 'b', menu_x)

        # --- Hiển thị quân cờ đã chọn và nước đi hợp lệ ---
        if selected_square:
            r, c = selected_square
            pygame.draw.rect(screen, HIGHLIGHT, pygame.Rect(c * SQUARE_SIZE, r * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE), 3)
            # Vẽ mũi tên chỉ nước đi hợp lệ
            for move in valid_moves_list:
                tr, tc = move
                pygame.draw.line(screen, MOVE_HINT, (c * SQUARE_SIZE + SQUARE_SIZE//2, r * SQUARE_SIZE + SQUARE_SIZE//2), (tc * SQUARE_SIZE + SQUARE_SIZE//2, tr * SQUARE_SIZE + SQUARE_SIZE//2), 3)
                # Vẽ ô đích
                pygame.draw.rect(screen, MOVE_HINT, pygame.Rect(tc * SQUARE_SIZE, tr * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE), 3)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()

def save_game(gs, filename=None):
    """Save game state to JSON file"""
    if filename is None:
        filename = os.path.join(script_dir, "saved_game.json")
    try:
        with open(filename, 'w') as f:
            json.dump(gs.to_dict(), f, indent=2)
        print(f"Game saved to: {filename}")
    except Exception as e:
        print(f"Save failed: {e}")

def load_game(filename=None):
    """Load game state from JSON file"""
    if filename is None:
        filename = os.path.join(script_dir, "saved_game.json")
    if not os.path.exists(filename):
        print(f"Save file not found: {filename}")
        return None
    try:
        with open(filename) as f:
            data = json.load(f)
        gs = GameState()
        gs.load_from_dict(data)
        print(f"Game loaded from: {filename}")
        return gs
    except Exception as e:
        print(f"Load failed: {e}")
        return None

if __name__ == "__main__":
    main()
