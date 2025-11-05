import pygame

class Button:
    def __init__(self, x, y, w, h, text, font_size=24, color=(100, 100, 100), hover_color=(150, 150, 150), text_color=(255, 255, 255)):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.text_color = text_color
        self.font = pygame.font.SysFont(None, font_size)

    def draw(self, screen):
        """Vẽ button lên màn hình"""
        mouse_pos = pygame.mouse.get_pos()
        if self.rect.collidepoint(mouse_pos):
            pygame.draw.rect(screen, self.hover_color, self.rect, border_radius=8)
        else:
            pygame.draw.rect(screen, self.color, self.rect, border_radius=8)

        text_surface = self.font.render(self.text, True, self.text_color)
        screen.blit(text_surface, text_surface.get_rect(center=self.rect.center))

    def is_clicked(self, event):
        """Trả về True nếu button được nhấn"""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                return True
        return False


class ButtonManager:
    def __init__(self):
        # Ví dụ: tạo 1 nút "New Game"
        self.buttons = [
            Button(500, 10, 120, 40, "New Game")
        ]

    def draw(self, screen):
        for btn in self.buttons:
            btn.draw(screen)

    def handle_event(self, event, game):
        for btn in self.buttons:
            if btn.is_clicked(event):
                if btn.text == "New Game":
                    game.engine.board.reset()
