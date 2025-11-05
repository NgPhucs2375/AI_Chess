# ui.py
import pygame
import os
import sys
import json
from copy import deepcopy
import traceback

# -------------------------
# Cấu hình cơ bản / Constants
# -------------------------
WIDTH, HEIGHT = 740, 740          # kích thước bàn cờ (không tính panel)
ROWS, COLS = 8, 8
SQUARE_SIZE = WIDTH // COLS

# Panel ở trên bên phải: rộng rộng hơn để chứa đủ button
PANEL_WIDTH = 500
PANEL_HEIGHT = 180

# Màu sắc
WHITE = (240, 240, 210)
BROWN = (181, 136, 99)
HIGHLIGHT = (255, 223, 0)
MOVE_HINT = (50, 205, 50)
CHECK_HIGHLIGHT = (255, 80, 80)

# wood / warm palette (nền vàng gỗ)
WOOD = (222, 184, 135)        # màu nền gỗ
PANEL_BG = (245, 236, 220)    # panel sáng (như gỗ sáng)
PANEL_BORDER = (140, 85, 40)  # viền gỗ tối
# loại bỏ màu xám: button cùng tông gỗ, không còn "xám xám"
BUTTON_BG = PANEL_BG
BUTTON_BORDER = PANEL_BORDER
BUTTON_TEXT = (30, 20, 10)
MOVELOG_BG = (205, 170, 120)  # move log tông gỗ tối hơn
MOVELOG_TEXT = (10, 10, 10)

# -------------------------
# Pygame init & fonts
# -------------------------
pygame.init()
pygame.font.init()
# đổi font sang giao diện gọn hơn (Segoe UI), fallback tự động nếu ko có
FONT = pygame.font.SysFont('Segoe UI', 18)
BUTTON_FONT = pygame.font.SysFont('Segoe UI', 20, bold=True)
MOVELOG_FONT = pygame.font.SysFont('Segoe UI', 14)

# tạo cửa sổ: cộng luôn PANEL_WIDTH sang phải
screen = pygame.display.set_mode((WIDTH + PANEL_WIDTH, HEIGHT))
pygame.display.set_caption("Chess - Người với Người ")
clock = pygame.time.Clock()

# -------------------------
# Load images
# -------------------------
pieces = {}
piece_types = [
    "wp", "wr", "wn", "wb", "wq", "wk",
    "bp", "br", "bn", "bb", "bq", "bk"
]

script_dir = os.path.dirname(os.path.abspath(__file__))
images_dir = os.path.join(script_dir, "images")

try:
    for piece in piece_types:
        img_path = os.path.join(images_dir, f"{piece}.png")
        if not os.path.exists(img_path):
            raise FileNotFoundError(f"Image not found: {img_path}")
        image = pygame.image.load(img_path).convert_alpha()
        image = pygame.transform.scale(image, (SQUARE_SIZE, SQUARE_SIZE))
        pieces[piece] = image
except Exception as e:
    print(f"Error loading images: {e}")
    print("Make sure ./images contains wp.png, wr.png, ... bk.png")
    sys.exit(1)

# -------------------------
# Starting board (standard)
# -------------------------
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

# -------------------------
# GameState (rules & logic)
# -------------------------
class GameState:
    def __init__(self):
        self.board = [row[:] for row in starting_board]
        self.white_to_move = True
        # castling: [w_kingside, w_queenside, b_kingside, b_queenside]
        self.castling_rights = [True, True, True, True]
        self.en_passant = None  # (row, col) target square where capture is allowed, or None
        self.move_log = []      # list of move dicts for undo/redo
        self.move_history = []  # list of notation strings for display
        self.white_score = 0    # điểm hiện tại cho trắng (theo vật liệu)
        self.black_score = 0    # điểm hiện tại cho đen
        self.update_king_positions()

    def update_king_positions(self):
        self.white_king_pos = None
        self.black_king_pos = None
        for r in range(8):
            for c in range(8):
                p = self.board[r][c]
                if p == "wk":
                    self.white_king_pos = (r, c)
                elif p == "bk":
                    self.black_king_pos = (r, c)

    def in_bounds(self, r, c):
        return 0 <= r < ROWS and 0 <= c < COLS

    def is_white(self, piece):
        return piece != "" and piece[0] == "w"

    def is_black(self, piece):
        return piece != "" and piece[0] == "b"

    # returns True if square (r,c) is attacked by color ('w' or 'b')
    def is_square_attacked(self, r, c, by_color):
        # pawns: if square (r,c) is attacked by white pawns, there must be a white pawn at r+1 (since white moves up = decreasing row)
        if by_color == 'w':
            for dc in (-1, 1):
                rr = r + 1
                cc = c + dc
                if self.in_bounds(rr, cc) and self.board[rr][cc] == 'wp':
                    return True
        else:
            for dc in (-1, 1):
                rr = r - 1
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

        # orthogonal sliding (rook/queen)
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

        # diagonal sliding (bishop/queen)
        diag = [(1,1),(1,-1),(-1,1),(-1,-1)]
        for dr,dc in diag:
            rr,cc = r+dr, c+dc
            while self.in_bounds(rr,cc):
                p = self.board[rr][cc]
                if p != "":
                    if (by_color=='w' and p[0]=='w') or (by_color=='b' and p[0]=='b'):
                        if p[1] in ('b','q'):
                            return True
                        else:
                            break
                    else:
                        break
                rr += dr; cc += dc

        # king adjacency
        for dr in (-1,0,1):
            for dc in (-1,0,1):
                if dr == 0 and dc == 0: continue
                rr,cc = r+dr, c+dc
                if self.in_bounds(rr,cc):
                    p = self.board[rr][cc]
                    if p != "" and p[1] == 'k' and ((by_color=='w' and p[0]=='w') or (by_color=='b' and p[0]=='b')):
                        return True

        return False

    # Generate pseudo-legal moves for piece at r, c (doesn't check for leaving king in check)
    def generate_piece_moves(self, r, c):
        piece = self.board[r][c]
        if piece == "": return []
        color = piece[0]
        ptype = piece[1]
        moves = []

        def add_if_empty_or_capture(rr,cc):
            if not self.in_bounds(rr,cc): return
            targ = self.board[rr][cc]
            if targ == "" or (color=='w' and targ[0]=='b') or (color=='b' and targ[0]=='w'):
                moves.append(((r,c),(rr,cc), False))

        if ptype == 'p':
            direction = -1 if color == 'w' else 1
            start_row = 6 if color=='w' else 1
            fr = r + direction
            if self.in_bounds(fr,c) and self.board[fr][c] == "":
                moves.append(((r,c),(fr,c), False))
                fr2 = r + 2*direction
                if r == start_row and self.in_bounds(fr2,c) and self.board[fr2][c] == "":
                    moves.append(((r,c),(fr2,c), False))
            for dc in (-1,1):
                rr = r + direction
                cc = c + dc
                if self.in_bounds(rr,cc):
                    targ = self.board[rr][cc]
                    if targ != "" and ((color=='w' and targ[0]=='b') or (color=='b' and targ[0]=='w')):
                        moves.append(((r,c),(rr,cc), False))
            # en-passant
            if self.en_passant:
                ep_r, ep_c = self.en_passant
                if ep_r == r + direction and abs(ep_c - c) == 1:
                    moves.append(((r,c),(ep_r,ep_c), True))

        elif ptype == 'n':
            deltas = [(2,1),(1,2),(-1,2),(-2,1),(-2,-1),(-1,-2),(1,-2),(2,-1)]
            for dr,dc in deltas:
                rr,cc = r+dr, c+dc
                add_if_empty_or_capture(rr,cc)

        elif ptype in ('r','b','q'):
            dirs = []
            if ptype in ('r','q'): dirs += [(1,0),(-1,0),(0,1),(0,-1)]
            if ptype in ('b','q'): dirs += [(1,1),(1,-1),(-1,1),(-1,-1)]
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

        elif ptype == 'k':
            for dr in (-1,0,1):
                for dc in (-1,0,1):
                    if dr==0 and dc==0: continue
                    rr,cc = r+dr, c+dc
                    add_if_empty_or_capture(rr,cc)
            # castling
            if color == 'w' and r==7 and c==4:
                wk_side, wq_side = self.castling_rights[0], self.castling_rights[1]
                if wk_side and self.board[7][7] == 'wr' and self.board[7][5]=="" and self.board[7][6]=="":
                    if not self.in_check('w') and not self.is_square_attacked(7,5,'b') and not self.is_square_attacked(7,6,'b'):
                        moves.append(((r,c),(7,6), "castle_k"))
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

    def in_check(self, color):
        self.update_king_positions()
        king_pos = self.white_king_pos if color=='w' else self.black_king_pos
        if king_pos is None:
            return False
        r,c = king_pos
        return self.is_square_attacked(r,c, 'b' if color=='w' else 'w')

    def is_insufficient_material(self):
        pieces_list = []
        for r in range(8):
            for c in range(8):
                p = self.board[r][c]
                if p != "": pieces_list.append(p)
        kings = [p for p in pieces_list if p[1] == 'k']
        others = [p for p in pieces_list if p[1] != 'k']
        if len(kings) == 2 and len(others) == 0:
            return True
        if len(kings) == 2 and len(others) == 1 and others[0][1] in ('b','n'):
            return True
        return False

    def get_all_legal_moves(self):
        moves = []
        color = 'w' if self.white_to_move else 'b'
        for r in range(8):
            for c in range(8):
                p = self.board[r][c]
                if p != "" and p[0] == color:
                    pseudo = self.generate_piece_moves(r,c)
                    for mv in pseudo:
                        if self.is_legal_move(mv):
                            moves.append(mv)
        return moves

    # apply move (assumes legal)
    def make_move(self, move, promotion_choice=None):
        # move: ((fr,fc),(tr,tc), flag)
        (fr,fc),(tr,tc),flag = move
        moving = self.board[fr][fc]
        if moving == "": return False

        # check promotion requirement (signal caller by returning None)
        if moving[1] == 'p':
            if (moving[0]=='w' and tr==0) or (moving[0]=='b' and tr==7):
                if promotion_choice is None:
                    return None  # caller must handle promotion UI and call again with choice

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

        # promotion
        if moving[1] == 'p':
            if (moving[0]=='w' and tr==0) or (moving[0]=='b' and tr==7):
                if promotion_choice:
                    promotion = moving[0] + promotion_choice
                    self.board[tr][tc] = promotion
                else:
                    return None

        # castling rook adjustments
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

        # update castling rights when king or rook moves/captured
        def revoke_castle_for(piece, r_src, c_src):
            if piece == 'wk':
                self.castling_rights[0] = False; self.castling_rights[1] = False
            if piece == 'bk':
                self.castling_rights[2] = False; self.castling_rights[3] = False
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

        # log the move for undo
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

        # --- update score if capture happened ---
        if captured and captured != "":
            # simple piece values
            values = {'p':1, 'n':3, 'b':3, 'r':5, 'q':9, 'k':0}
            val = values.get(captured[1], 0)
            if moving[0] == 'w':
                self.white_score += val
            else:
                self.black_score += val
        # --- end score update ---

        # notation building (simple SAN-like)
        fr0, fc0 = move[0]; tr0, tc0 = move[1]
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
        # switch turn, check check/checkmate for notation suffix
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
        (fr,fc),(tr,tc),flag = move
        piece = self.board[fr][fc]
        captured = self.board[tr][tc]
        if piece == "": return False
        # make move temporarily
        self.board[fr][fc] = ""
        self.board[tr][tc] = piece
        ep_capture = None
        if flag is True:
            ep_capture = self.board[fr][tc]
            self.board[fr][tc] = ""
        color = piece[0]
        legal = not self.in_check(color)
        # undo
        self.board[fr][fc] = piece
        self.board[tr][tc] = captured
        if ep_capture:
            self.board[fr][tc] = ep_capture
        return legal

    def to_dict(self):
        return {
            'board': [row[:] for row in self.board],
            'white_to_move': self.white_to_move,
            'castling_rights': list(self.castling_rights),
            'en_passant': list(self.en_passant) if self.en_passant else None,
            'move_log': self.move_log,
            'move_history': self.move_history
        }

    def load_from_dict(self, data):
        self.board = [row[:] for row in data['board']]
        self.white_to_move = data['white_to_move']
        self.castling_rights = list(data['castling_rights'])
        self.en_passant = tuple(data['en_passant']) if data['en_passant'] else None
        self.move_log = data['move_log']
        self.move_history = data['move_history']
        self.update_king_positions()

    # UNDO move
    def undo_move(self):
        """Undo last move. Returns removed move dict or None."""
        if not self.move_log:
            return None
        last = self.move_log.pop()
        move = last['move']
        (fr,fc),(tr,tc),flag = move
        # revert piece move
        moving = last['moving']
        self.board[fr][fc] = moving
        # revert capture or en-passant
        if last['is_en_passant']:
            # en-passant captured piece was at (fr,tc) originally
            cap_piece = last['captured']
            self.board[fr][tc] = cap_piece
            self.board[tr][tc] = ""
        else:
            self.board[tr][tc] = last['captured'] if last['captured'] else ""
        # revert promotion
        if last['promotion']:
            # if promotion occurred, the moving piece recorded was pawn?? we replace promoted piece back to pawn
            # moving (in log) was piece before move, so if promotion happened moving contains 'wp' or 'bp'
            # ensure revert square contains pawn
            pawn_code = moving[0] + 'p'
            self.board[fr][fc] = pawn_code
        # revert castling rook movement
        if last['is_castle']:
            if moving == 'wk':
                # determine destination was either (7,6) or (7,2)
                if self.board[7][6] == 'wk':
                    # shouldn't be king - but we move rook back depending on which moved earlier
                    pass
            # simpler approach: recompute from last['prev_castling'] is stored but easier to set rooks back by positions
            # We'll set rooks back based on where they should be for original board:
            # If white castle kingside: king from (7,6) back to (7,4) and rook from (7,5) back to (7,7)
            # But we already moved king back above to fr,fc
            if last['is_castle'] and last['moving'] in ('wk','bk'):
                if last['moving'] == 'wk':
                    # determine which side by where rook is now
                    if self.board[7][5] == 'wr' and self.board[7][7] == "":
                        # kingside undone already covered
                        pass
                # We will reconstruct castling rooks by checking previous castling rights saved (not ideal but generally ok)
                # For correctness: restore rooks to original squares if empty
                # white kingside original rook (7,7)
                if self.board[7][7] == "":
                    # attempt to find a white rook in (7,5) or (7,3) and move back
                    if self.board[7][5] == 'wr':
                        self.board[7][7] = 'wr'; self.board[7][5] = ""
                    if self.board[7][3] == 'wr':
                        self.board[7][0] = 'wr'; self.board[7][3] = ""
                # black similar
                if self.board[0][7] == "":
                    if self.board[0][5] == 'br':
                        self.board[0][7] = 'br'; self.board[0][5] = ""
                    if self.board[0][3] == 'br':
                        self.board[0][0] = 'br'; self.board[0][3] = ""

        # restore en-passant and castling rights
        self.en_passant = last['prev_en_passant']
        self.castling_rights = list(last['prev_castling'])
        # pop last notation
        if self.move_history:
            self.move_history.pop()
        self.update_king_positions()
        # toggle turn back
        self.white_to_move = not self.white_to_move
        return last

# -------------------------
# Drawing functions
# -------------------------
def draw_board(screen, gs, valid_moves):
    # draw squares
    for r in range(ROWS):
        for c in range(COLS):
            color = WHITE if (r + c) % 2 == 0 else BROWN
            pygame.draw.rect(screen, color, pygame.Rect(c * SQUARE_SIZE, r * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))
    # draw pieces
    for r in range(ROWS):
        for c in range(COLS):
            piece = gs.board[r][c]
            if piece != "":
                screen.blit(pieces[piece], pygame.Rect(c * SQUARE_SIZE, r * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))
    # draw valid moves markers
    if valid_moves:
        for mv in valid_moves:
            r,c = mv
            pygame.draw.rect(screen, MOVE_HINT, pygame.Rect(c * SQUARE_SIZE, r * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE), 3)

# Panel (bottom-right) rendering: background, buttons, move log
def draw_panel(screen, gs, white_time_sec, black_time_sec, running_side):
    layout = compute_panel_layout()
    panel_rect = layout['panel_rect']
    pygame.draw.rect(screen, PANEL_BG, panel_rect)
    pygame.draw.rect(screen, PANEL_BORDER, panel_rect, 2, border_radius=8)

    def fmt_time(secs):
        if secs < 0: secs = 0
        m = int(secs) // 60
        s = int(secs) % 60
        return f"{m:02d}:{s:02d}"

    # clocks
    pygame.draw.rect(screen, MOVELOG_BG, layout['white_box'], border_radius=6)
    pygame.draw.rect(screen, PANEL_BORDER, layout['white_box'], 2, border_radius=6)
    w_label = BUTTON_FONT.render("White", True, BUTTON_TEXT)
    w_time = BUTTON_FONT.render(fmt_time(white_time_sec), True, HIGHLIGHT if running_side == 'w' else BUTTON_TEXT)
    screen.blit(w_label, (layout['white_box'].x + 8, layout['white_box'].centery - w_label.get_height() // 2))
    screen.blit(w_time, (layout['white_box'].right - 8 - w_time.get_width(), layout['white_box'].centery - w_time.get_height() // 2))

    pygame.draw.rect(screen, MOVELOG_BG, layout['black_box'], border_radius=6)
    pygame.draw.rect(screen, PANEL_BORDER, layout['black_box'], 2, border_radius=6)
    b_label = BUTTON_FONT.render("Black", True, BUTTON_TEXT)
    b_time = BUTTON_FONT.render(fmt_time(black_time_sec), True, HIGHLIGHT if running_side == 'b' else BUTTON_TEXT)
    screen.blit(b_label, (layout['black_box'].x + 8, layout['black_box'].centery - b_label.get_height() // 2))
    screen.blit(b_time, (layout['black_box'].right - 8 - b_time.get_width(), layout['black_box'].centery - b_time.get_height() // 2))

    # score (bigger font to stand out)
    score_text = BUTTON_FONT.render(f"W: {gs.white_score}   B: {gs.black_score}", True, BUTTON_TEXT)
    score_x, score_y = layout['score_pos']
    screen.blit(score_text, (score_x, score_y))
    score_h = score_text.get_height()

    # Now compute correct btn_box_y including the score height (important for click alignment)
    btn_box_rect = pygame.Rect(layout['btn_box_rect'].x, layout['btn_box_rect'].y + score_h, layout['btn_box_rect'].w, layout['btn_box_rect'].h)
    pygame.draw.rect(screen, PANEL_BG, btn_box_rect, border_radius=8)
    pygame.draw.rect(screen, PANEL_BORDER, btn_box_rect, 2, border_radius=8)

    # draw buttons inside that small box (shift Y by score_h)
    start_x = btn_box_rect.x + layout['padding']//2
    start_y = btn_box_rect.y + layout['padding']//2
    labels = ["Lùi", "Tiếp", "Hòa", "Thoát"]
    btns = []
    for i, label in enumerate(labels):
        x = start_x + i * (layout['btn_w'] + layout['gap'])
        rect = pygame.Rect(x, start_y, layout['btn_w'], layout['btn_h'])
        pygame.draw.rect(screen, BUTTON_BG, rect, border_radius=6)
        pygame.draw.rect(screen, BUTTON_BORDER, rect, 2, border_radius=6)
        text = BUTTON_FONT.render(label, True, BUTTON_TEXT)
        screen.blit(text, (rect.centerx - text.get_width() // 2, rect.centery - text.get_height() // 2))
        btns.append((label, rect))

    # return layout + actual button rects (actual rects include score offset)
    layout['btn_box_rect'] = btn_box_rect
    layout['btn_rects_actual'] = {label: rect for label, rect in btns}
    return layout

def draw_move_history(screen, gs):
    # draw move history box below the panel (to the right of the board)
    panel_x = WIDTH
    log_x = panel_x + 12
    log_y = PANEL_HEIGHT + 6
    log_w = PANEL_WIDTH - 24
    log_h = HEIGHT - log_y - 12
    log_rect = pygame.Rect(log_x - 6, log_y - 6, log_w + 12, log_h + 12)  # include small border
    pygame.draw.rect(screen, MOVELOG_BG, log_rect, border_radius=8)
    pygame.draw.rect(screen, PANEL_BORDER, log_rect, 2, border_radius=8)

    # prepare moves in pairs
    moves = gs.move_history
    pairs = []
    for i in range(0, len(moves), 2):
        num = i//2 + 1
        w = moves[i]
        b = moves[i+1] if i+1 < len(moves) else ""
        pairs.append((num, w, b))

    # compute how many rows fit
    line_h = 18
    max_rows = max(1, log_h // line_h)
    start_row = max(0, len(pairs) - max_rows)
    visible = pairs[start_row:]

    # columns inside log area
    col_num_x = log_x + 6
    num_col_w = int(log_w * 0.12)
    white_col_w = int(log_w * 0.42)
    black_col_w = log_w - num_col_w - white_col_w - 12
    col_white_x = col_num_x + num_col_w + 6
    col_black_x = col_white_x + white_col_w + 8

    y = log_y + 6

    def fit_text(txt, maxw, font):
        if txt == "": return ""
        if font.size(txt)[0] <= maxw:
            return txt
        s = txt
        while s and font.size(s + "…")[0] > maxw:
            s = s[:-1]
        return s + "…"

    for num, wmove, bmove in visible:
        tnum = MOVELOG_FONT.render(f"{num}.", True, MOVELOG_TEXT)
        w_text = fit_text(wmove, white_col_w, MOVELOG_FONT)
        b_text = fit_text(bmove, black_col_w, MOVELOG_FONT)
        twhite = MOVELOG_FONT.render(w_text, True, MOVELOG_TEXT)
        tblack = MOVELOG_FONT.render(b_text, True, MOVELOG_TEXT)
        screen.blit(tnum, (col_num_x, y))
        screen.blit(twhite, (col_white_x, y))
        screen.blit(tblack, (col_black_x, y))
        y += line_h

# Promotion menu drawing (centered modal)
PROMOTION_PIECE_SIZE = 48
PROMOTION_PADDING = 8
def draw_promotion_menu(turn, menu_x):
    piece_codes = ['q','r','b','n']
    bg_w = len(piece_codes) * PROMOTION_PIECE_SIZE + (len(piece_codes) + 1)*PROMOTION_PADDING
    bg_h = PROMOTION_PIECE_SIZE + 2*PROMOTION_PADDING
    bg_rect = pygame.Rect(menu_x, HEIGHT//2 - bg_h//2, bg_w, bg_h)
    pygame.draw.rect(screen, PANEL_BG, bg_rect, border_radius=8)
    pygame.draw.rect(screen, PANEL_BORDER, bg_rect, 2, border_radius=8)
    piece_positions = []
    for i, code in enumerate(piece_codes):
        piece_color = 'w' if turn == 'w' else 'b'
        img = pieces[piece_color + code]
        x = menu_x + PROMOTION_PADDING + i*(PROMOTION_PIECE_SIZE + PROMOTION_PADDING)
        y = HEIGHT//2 - PROMOTION_PIECE_SIZE//2
        screen.blit(img, pygame.Rect(x, y, PROMOTION_PIECE_SIZE, PROMOTION_PIECE_SIZE))
        piece_positions.append((pygame.Rect(x, y, PROMOTION_PIECE_SIZE, PROMOTION_PIECE_SIZE), code))
    return piece_positions

# -------------------------
# Save & Load
# -------------------------
def save_game(gs, filename=None):
    if filename is None:
        filename = os.path.join(script_dir, "saved_game.json")
    try:
        with open(filename, 'w') as f:
            json.dump(gs.to_dict(), f, indent=2)
        print(f"Game saved to: {filename}")
    except Exception as e:
        print(f"Save failed: {e}")

def load_game(filename=None):
    if filename is None:
        filename = os.path.join(script_dir, "saved_game.json")
    if not os.path.exists(filename):
        print("Save file not found.")
        return None
    try:
        with open(filename) as f:
            data = json.load(f)
        gs = GameState()
        gs.load_from_dict(data)
        print("Game loaded.")
        return gs
    except Exception as e:
        print(f"Load failed: {e}")
        return None

# -------------------------
# Main loop
# -------------------------
def main():
    gs = GameState()
    selected_square = None
    valid_moves_list = []
    target_map = {}
    awaiting_promotion = None
    redo_stack = []

    # --- clocks: 10 minutes each (seconds) ---
    # dùng biến TEST_SECONDS để dễ thay đổi khi test
    TEST_SECONDS = 600    # đặt tg 10 phút 
    white_time = TEST_SECONDS
    black_time = TEST_SECONDS
    running_side = 'w' if gs.white_to_move else 'b'
    last_tick = pygame.time.get_ticks()
    game_over = False
    winner = None

    running = True
    while running:
        now = pygame.time.get_ticks()
        dt = (now - last_tick) / 1000.0
        last_tick = now

        # update clocks only if game not over
        if not game_over:
            if running_side == 'w':
                white_time -= dt
                if white_time <= 0:
                    white_time = 0
                    game_over = True
                    winner = 'Black'
                    pygame.display.set_caption("Black wins on time")
            else:
                black_time -= dt
                if black_time <= 0:
                    black_time = 0
                    game_over = True
                    winner = 'White'
                    pygame.display.set_caption("White wins on time")

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and not game_over:
                mx, my = pygame.mouse.get_pos()

                # If waiting promotion, check promotion menu clicks
                if awaiting_promotion:
                    bg_w = 4 * PROMOTION_PIECE_SIZE + 5 * PROMOTION_PADDING
                    menu_x = (WIDTH - bg_w) // 2
                    piece_positions = draw_promotion_menu('w' if gs.white_to_move else 'b', menu_x)
                    for rect, piece_code in piece_positions:
                        if rect.collidepoint(mx, my):
                            res = gs.make_move(awaiting_promotion, promotion_choice=piece_code)
                            if res:
                                awaiting_promotion = None
                                selected_square = None
                                valid_moves_list = []
                                target_map = {}
                                redo_stack.clear()
                                # switch clocks
                                running_side = 'b' if running_side == 'w' else 'w'
                                last_tick = pygame.time.get_ticks()
                            break
                    continue

                # Click inside chessboard
                if mx < WIDTH and my < HEIGHT:
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
                            if p != "" and ((p[0] == 'w' and gs.white_to_move) or (p[0] == 'b' and not gs.white_to_move)):
                                selected_square = clicked
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
                                fr,fc = mv[0]; tr,tc = mv[1]
                                moving = gs.board[fr][fc]
                                # promotion check
                                if moving != "" and moving[1] == 'p' and ((moving[0]=='w' and tr==0) or (moving[0]=='b' and tr==7)):
                                    awaiting_promotion = mv
                                else:
                                    res = gs.make_move(mv)
                                    if res is None:
                                        pass
                                    else:
                                        redo_stack.clear()
                                        selected_square = None
                                        valid_moves_list = []
                                        target_map = {}
                                        # switch clock side
                                        running_side = 'b' if running_side == 'w' else 'w'
                                        last_tick = pygame.time.get_ticks()
                                        if gs.is_insufficient_material():
                                            pygame.display.set_caption("Draw by insufficient material")
                            else:
                                # select other piece
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

                # Click inside panel area (right)
                else:
                    # use same layout as draw_panel
                    layout = compute_panel_layout()
                    # compute score height same as draw_panel
                    score_text = BUTTON_FONT.render(f"W: {gs.white_score}   B: {gs.black_score}", True, BUTTON_TEXT)
                    score_h = score_text.get_height()
                    # build actual button rects shifted by score_h
                    btn_rects = {}
                    for label, r in layout['btn_rects'].items():
                        btn_rects[label] = pygame.Rect(r.x, r.y + score_h, r.w, r.h)

                    if layout['panel_rect'].collidepoint(mx, my):
                        clicked_label = None
                        for label, rect in btn_rects.items():
                            if rect.collidepoint(mx, my):
                                clicked_label = label
                                break

                        if clicked_label is None:
                            # clicked panel background -> ignore
                            pass
                        else:
                            if clicked_label == "Lùi":
                                last = gs.undo_move()
                                if last:
                                    redo_stack.append(last)
                                    selected_square = None
                                    valid_moves_list = []
                                    target_map = {}
                                    running_side = 'b' if running_side == 'w' else 'w'
                                    last_tick = pygame.time.get_ticks()
                                else:
                                    print("Không có nước để lùi.")
                            elif clicked_label == "Tiếp":
                                if redo_stack:
                                    item = redo_stack.pop()
                                    mv = item['move']
                                    promotion_piece = None
                                    if item['promotion']:
                                        promotion_piece = item['promotion'][1]
                                    res = gs.make_move(mv, promotion_choice=promotion_piece) if promotion_piece else gs.make_move(mv)
                                    if res:
                                        running_side = 'b' if running_side == 'w' else 'w'
                                        last_tick = pygame.time.get_ticks()
                                        print("Redo applied.")
                                    else:
                                        print("Redo failed.")
                                else:
                                    print("Không có nước để tiến.")
                            elif clicked_label == "Hòa":
                                game_over = True
                                winner = None
                                pygame.display.set_caption("Draw")
                                show_draw_modal(seconds=3)
                            elif clicked_label == "Thoát":
                                pygame.quit()
                                sys.exit()

        # Render (thêm vào đây để vẽ mỗi frame)
        screen.fill(WOOD)
        draw_board(screen, gs, valid_moves_list)
        layout = draw_panel(screen, gs, white_time, black_time, running_side)
        draw_move_history(screen, gs)

        # If promotion is pending, draw overlay + promotion menu (same as click handling)
        if awaiting_promotion:
            overlay = pygame.Surface((WIDTH, HEIGHT))
            overlay.set_alpha(130)
            overlay.fill((0,0,0))
            screen.blit(overlay, (0,0))
            bg_w = 4 * PROMOTION_PIECE_SIZE + 5 * PROMOTION_PADDING
            menu_x = (WIDTH - bg_w) // 2
            draw_promotion_menu('w' if gs.white_to_move else 'b', menu_x)

        # highlight selected square and draw move hints
        if selected_square:
            r,c = selected_square
            pygame.draw.rect(screen, HIGHLIGHT, pygame.Rect(c*SQUARE_SIZE, r*SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE), 3)
            for move in valid_moves_list:
                tr, tc = move
                pygame.draw.line(screen, MOVE_HINT,
                                 (c*SQUARE_SIZE + SQUARE_SIZE//2, r*SQUARE_SIZE + SQUARE_SIZE//2),
                                 (tc*SQUARE_SIZE + SQUARE_SIZE//2, tr*SQUARE_SIZE + SQUARE_SIZE//2), 3)
                pygame.draw.rect(screen, MOVE_HINT, pygame.Rect(tc*SQUARE_SIZE, tr*SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE), 3)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()

# -------------------------
# Panel layout helper (fix: cung cấp hàm compute_panel_layout dùng bởi draw_panel & xử lý click)
# -------------------------
def compute_panel_layout():
    panel_x = WIDTH
    panel_y = 0
    padding = 12
    clocks_h = 48
    clock_w = PANEL_WIDTH - 2 * padding
    clock_h = (clocks_h - padding // 2) // 2
    clock_x = panel_x + padding
    clock_y = panel_y + padding
    white_box = pygame.Rect(clock_x, clock_y, clock_w, clock_h)
    black_box = pygame.Rect(clock_x, clock_y + clock_h + 6, clock_w, clock_h)

    # score placement (under black box)
    score_pos = (clock_x, black_box.bottom + 6)

    # buttons (we'll offset them by the score height at draw time)
    btn_w, btn_h = 100, 40
    gap = 10
    btn_box_y = black_box.bottom + 6  # base Y (score height added later)
    btn_box_width = 4 * btn_w + 3 * gap + padding * 2
    btn_box_rect = pygame.Rect(panel_x + padding, btn_box_y, btn_box_width, btn_h + padding)

    start_x = btn_box_rect.x + padding // 2
    start_y = btn_box_rect.y + padding // 2
    labels = ["Lùi", "Tiếp", "Hòa", "Thoát"]
    btn_rects = {label: pygame.Rect(start_x + i * (btn_w + gap), start_y, btn_w, btn_h) for i, label in enumerate(labels)}

    panel_rect = pygame.Rect(panel_x, panel_y, PANEL_WIDTH, PANEL_HEIGHT)
    return {
        'panel_rect': panel_rect,
        'white_box': white_box,
        'black_box': black_box,
        'score_pos': score_pos,
        'btn_box_rect': btn_box_rect,
        'btn_rects': btn_rects,
        'btn_w': btn_w,
        'btn_h': btn_h,
        'gap': gap,
        'padding': padding
    }

# -------------------------
# Simple modal for draw (fix: ensure function exists)
# -------------------------
def show_draw_modal(seconds=3):
    popup_w, popup_h = 360, 140
    popup_x = WIDTH + (PANEL_WIDTH - popup_w) // 2
    popup_y = HEIGHT // 2 - popup_h // 2
    popup_rect = pygame.Rect(popup_x, popup_y, popup_w, popup_h)
    start = pygame.time.get_ticks()
    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if e.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                return
        # draw overlay + popup
        overlay = pygame.Surface((WIDTH, HEIGHT))
        overlay.set_alpha(140)
        overlay.fill((0,0,0))
        screen.blit(overlay, (0,0))
        pygame.draw.rect(screen, PANEL_BG, popup_rect, border_radius=8)
        pygame.draw.rect(screen, PANEL_BORDER, popup_rect, 2, border_radius=8)
        t1 = FONT.render("Hòa - Trận đấu kết thúc", True, (10,10,10))
        t2 = MOVELOG_FONT.render(f"Thoát sau {seconds} giây...", True, (10,10,10))
        screen.blit(t1, (popup_rect.centerx - t1.get_width()//2, popup_rect.y + 24))
        screen.blit(t2, (popup_rect.centerx - t2.get_width()//2, popup_rect.y + 64))
        pygame.display.flip()
        if pygame.time.get_ticks() - start >= seconds * 1000:
            return

# ensure the script runs main when executed
if __name__ == "__main__":
    main()
