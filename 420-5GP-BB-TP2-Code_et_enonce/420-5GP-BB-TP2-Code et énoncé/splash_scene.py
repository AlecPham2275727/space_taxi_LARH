import pygame

from scene import Scene
from scene_manager import SceneManager
from game_settings import GameSettings


class SplashScene(Scene):
    """ Scène titre (splash). """

    _FADE_IN_DURATION: int = 1500
    _FADE_OUT_DURATION: int = 1500  # ms

    def __init__(self) -> None:
        super().__init__()
        self._settings = GameSettings()
        self._surface = pygame.image.load(self._settings.SPLASH_IMAGE).convert_alpha()
        self._music = pygame.mixer.Sound(self._settings.SPLASH_AUDIO)
        self._music.play(loops=-1, fade_ms=1500)  # Charger la musique en même temps que l'écran noir

        # Police pour le texte
        self.font = pygame.font.Font(self._settings.GAME_FONT, 24)
        self.text_alpha = 255
        self.alpha_direction = -5

        self._fade_in_start_time = pygame.time.get_ticks()
        self._fade_in_alpha = 255

        self._fade_out_start_time = None

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._fade_out_start_time = pygame.time.get_ticks()
                SceneManager().change_scene("level1_load", SplashScene._FADE_OUT_DURATION)
        
        if event.type == pygame.JOYBUTTONDOWN:
            if event.button == 9:
                self._fade_out_start_time = pygame.time.get_ticks()
                SceneManager().change_scene("level1_load", SplashScene._FADE_OUT_DURATION)

    def update(self) -> None:
        if self._fade_out_start_time:
            elapsed_time = pygame.time.get_ticks() - self._fade_out_start_time
            volume = max(0.0, 1.0 - (elapsed_time / SplashScene._FADE_OUT_DURATION))
            self._music.set_volume(volume)
            if volume == 0:
                self._fade_out_start_time = None

        current_time = pygame.time.get_ticks()

        # Mettre à jour le fondu noir
        if self._fade_in_alpha > 0:
            elapsed_time = current_time - self._fade_in_start_time
            self._fade_in_alpha = max(0, 255 - int((elapsed_time / SplashScene._FADE_IN_DURATION) * 255))

        # Mise à jour de la transparence pour le clignotement
        self.text_alpha += self.alpha_direction
        if self.text_alpha <= 50 or self.text_alpha >= 255:
            self.alpha_direction *= -1

    def render(self, screen: pygame.Surface) -> None:
        screen.blit(self._surface, (0, 0))

        # Crée le texte
        text_surface = self.create_text_surface("PRESS SPACE OR RETURN TO PLAY")
        text_surface.set_alpha(self.text_alpha)
        text_rect = text_surface.get_rect(center=(screen.get_width() // 2, screen.get_height() - 100))
        screen.blit(text_surface, text_rect)

        # Appliquer le fondu entrant
        if self._fade_in_alpha > 0:
            fade_surface = pygame.Surface(screen.get_size())
            fade_surface.fill((0, 0, 0))
            fade_surface.set_alpha(self._fade_in_alpha)
            screen.blit(fade_surface, (0, 0))

    def surface(self) -> pygame.Surface:
        return self._surface

    def create_text_surface(self, text: str) -> pygame.Surface:
        # Créer le texte avec les couleurs demandées
        parts = text.split()
        surfaces = []

        for part in parts:
            if part in ["SPACE", "RETURN"]:
                color = (255, 255, 0)  # Couleur pour le texte en jaune
            else:
                color = (255, 255, 255)  # Couleur pour le texte en blanc

            base_surface = self.font.render(part, True, color)
            outline_color = (0, 0, 50)  # Couleur pour le contour du texte en bleu foncé
            outline_surface = pygame.Surface(
              (base_surface.get_width() + 16, base_surface.get_height() + 16), pygame.SRCALPHA
            )

            # Dessiner le contour du texte
            for offset_x in range(-4, 5):
                for offset_y in range(-4, 5):
                    if abs(offset_x) + abs(offset_y) <= 4:
                        rendered_outline = self.font.render(part, True, outline_color)
                        outline_surface.blit(rendered_outline, (offset_x + 8, offset_y + 8))

            # Ajouter le texte principal par-dessus
            outline_surface.blit(base_surface, (8, 8))
            surfaces.append(outline_surface)

        # Combiner les mots sur une ligne
        total_width = sum(surface.get_width() for surface in surfaces) + (len(surfaces) - 1) * 4
        combined_surface = pygame.Surface((total_width, surfaces[0].get_height()), pygame.SRCALPHA)
        x_offset = 0

        for surface in surfaces:
            combined_surface.blit(surface, (x_offset, 0))
            x_offset += surface.get_width() + 4

        return combined_surface
