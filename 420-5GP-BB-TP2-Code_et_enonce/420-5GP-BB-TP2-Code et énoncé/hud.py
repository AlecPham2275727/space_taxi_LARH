import pygame
import threading
import time

from game_settings import GameSettings


class HUD:
    """ Singleton pour l'affichage tête haute (HUD). """

    _LIVES_ICONS_SPACING = 10
    _TEXT_FADE_IN_DURATION = 250
    _TEXT_FADE_OUT_DURATION = 500
    _OPAQUE_TEXT_DURATION = 1750

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(HUD, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self) -> None:
        if not hasattr(self, '_initialized'):
            self._settings = GameSettings()

            self._center_screen = self._settings.SCREEN_WIDTH // 2, self._settings.SCREEN_HEIGHT // 2

            self._money_font = pygame.font.Font(self._settings.GAME_FONT, 24)
            self._fuel_font = pygame.font.Font(self._settings.GAME_FONT, 10)
            self._destination_font = pygame.font.Font(self._settings.GAME_FONT, 30)

            self._bank_money = 0
            self._bank_money_surface = self._render_bank_money_surface()
            self._bank_money_pos = pygame.Vector2(20, self._settings.SCREEN_HEIGHT - (self._bank_money_surface.get_height() + 10))

            self._trip_money = 0
            self._trip_money_surface = self._render_trip_money_surface()

            self._lives = self._settings.NB_PLAYER_LIVES
            self._lives_icon = pygame.image.load(self._settings.LIVES_ICONS_FILENAME).convert_alpha()
            self._lives_pos= pygame.Vector2(20, self._settings.SCREEN_HEIGHT - (self._lives_icon.get_height() + 40))

            self._fuel_gauge_full = pygame.image.load(self._settings.FUEL_GAUGE_FULL_FILENAME).convert_alpha()
            self._fuel_gauge_empty = pygame.image.load(self._settings.FUEL_GAUGE_EMPTY_FILENAME).convert_alpha()
            self._fuel_gauge_width = self._fuel_gauge_full.get_width()
            self._fuel_gauge_height = self._fuel_gauge_full.get_height()

            self._destination_text_thread = None
            self._destination_text_displayed_time = None
            self._destination_text_alpha = 0
            self._destination_text = None

            self._fuel_gauge_pos = pygame.Vector2(
                (self._settings.SCREEN_WIDTH - self._fuel_gauge_width) / 2,
                self._settings.SCREEN_HEIGHT - self._fuel_gauge_height - 3
            )

            self._fuel_level = 1.0
            self._max_fuel = 100.0
            self._current_fuel = self._max_fuel

            self.visible = False

            self._initialized = True

    def render(self, screen: pygame.Surface) -> None:
        self._screen = screen
        spacing = self._lives_icon.get_width() + HUD._LIVES_ICONS_SPACING
        for n in range(self._lives):
            screen.blit(self._lives_icon, (self._lives_pos.x + (n * spacing), self._lives_pos.y))

        screen.blit(self._bank_money_surface, (self._bank_money_pos.x, self._bank_money_pos.y))

        x = self._settings.SCREEN_WIDTH - self._trip_money_surface.get_width() - 20
        y = self._settings.SCREEN_HEIGHT - self._trip_money_surface.get_height() - 10
        screen.blit(self._trip_money_surface, (x, y))

        screen.blit(self._fuel_gauge_empty, self._fuel_gauge_pos)

        fuel_width = int(self._fuel_gauge_width * self._fuel_level)
        if fuel_width > 0:
            fuel_full_clipped = self._fuel_gauge_full.subsurface(pygame.Rect(0, 0, fuel_width, self._fuel_gauge_height))
            screen.blit(fuel_full_clipped, self._fuel_gauge_pos)

        fuel_text = self._fuel_font.render("FUEL", True, (255, 255, 255))
        center_x = self._fuel_gauge_pos.x + self._fuel_gauge_width / 2
        center_y = self._fuel_gauge_pos.y + self._fuel_gauge_height / 2

        #source : https://www.reddit.com/r/pygame/comments/qw7fmk/how_to_set_center_position_of_text/?rdt=60642
        text_rect = fuel_text.get_rect(center=(center_x, center_y))
        screen.blit(fuel_text, text_rect)


    def add_bank_money(self, amount: float) -> None:
        self._bank_money += round(amount, 2)
        self._bank_money_surface = self._render_bank_money_surface()

    def get_lives(self) -> int:
        return self._lives

    def loose_live(self) -> None:
        if self._lives > 0:
            self._lives -= 1

    def reset(self) -> None:
        self._bank_money = 0
        self._bank_money_surface = self._render_bank_money_surface()
        self._lives = self._settings.NB_PLAYER_LIVES
        self.reset_fuel()

    def set_trip_money(self, trip_money: float) -> None:
        if self._trip_money != trip_money:
            self._trip_money = trip_money
            self._trip_money_surface = self._render_trip_money_surface()

    def update_fuel_level(self) -> None:
        self._fuel_level = self._current_fuel / self._max_fuel

    def get_current_fuel(self) -> float:
        return self._current_fuel

    def reset_fuel(self) -> None:
        """ Réinitialise l'essence au niveau maximal. """
        self._current_fuel = self._max_fuel
        self.update_fuel_level()

    def add_fuel(self, amount: float) -> None:
        self._current_fuel = min(self._current_fuel + amount, self._max_fuel)
        self.update_fuel_level()

    def consume_fuel(self, total_consumption):
        self._current_fuel -= total_consumption
        self.update_fuel_level()

    def _render_bank_money_surface(self) -> pygame.Surface:
        money_str = f"{self._bank_money:.2f}"
        return self._money_font.render(f"${money_str: >8}", True, (51, 51, 51))

    def _render_trip_money_surface(self) -> pygame.Surface:
        money_str = f"{self._trip_money:.2f}"
        return self._money_font.render(f"${money_str: >5}", True, (51, 51, 51))
    
    def display_pad_destination(self, target_pad: int) -> None:
        if self._destination_text_thread is None:
            self._destination_text_thread = threading.Thread(target=self._handle_text_display, args=(target_pad, ))
            self._destination_text_displayed_time = pygame.time.get_ticks()
            self._destination_text_thread.start()

    def _handle_text_display(self, target_pad: int) -> None:
        # The following code was inspired by a previous work in a school project: please go see the Read.me
        self._destination_text = f"Pad {target_pad} please!"
        total_duration = self._TEXT_FADE_IN_DURATION + self._OPAQUE_TEXT_DURATION +  self._TEXT_FADE_OUT_DURATION
        
        while pygame.time.get_ticks() - self._destination_text_displayed_time < total_duration:
            elapsed_time = pygame.time.get_ticks() - self._destination_text_displayed_time

            if elapsed_time < self._TEXT_FADE_IN_DURATION:
                self._destination_text_alpha = int(255 * (elapsed_time / self._TEXT_FADE_IN_DURATION))
            elif elapsed_time < self._TEXT_FADE_IN_DURATION + self._OPAQUE_TEXT_DURATION:
                self._destination_text_alpha = 255
            elif elapsed_time < total_duration:
                self._destination_text_alpha = int(255 - 255 * (elapsed_time / total_duration))

            self._update_text_opacity()
            time.sleep(0.0001)

        self._destination_text = None  
        self._destination_text_displayed_time = None
        self._destination_text_thread = None 
    
    def _update_text_opacity(self) -> None:
         # Source: https://www.geeksforgeeks.org/python-display-text-to-pygame-window/
        displayed_destination_text = self._destination_font.render(self._destination_text, True, (255, 255, 255))
        displayed_destination_text.set_alpha(self._destination_text_alpha) 
        destination_text_rect = displayed_destination_text.get_rect(center=self._center_screen)
        self._screen.blit(displayed_destination_text, destination_text_rect)
    


       




