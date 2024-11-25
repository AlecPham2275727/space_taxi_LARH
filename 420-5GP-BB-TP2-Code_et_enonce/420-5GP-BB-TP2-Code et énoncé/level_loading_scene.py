import pygame

from scene import Scene
from scene_manager import SceneManager
from game_settings import GameSettings


class LevelLoadingScene(Scene):
    """ Scène de chargement d'un niveau. """

    _FADE_OUT_DURATION: int = 500  # ms

    def __init__(self, level: int) -> None:
        super().__init__()
        self._settings = GameSettings()
        self._level = level
        self._surface = pygame.image.load(self._settings.LOADING_IMAGE).convert_alpha()
        self._music = pygame.mixer.Sound(self._settings.LOADING_AUDIO)
        self._music_started = False
        self._fade_out_start_time = None

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._fade_out_start_time = pygame.time.get_ticks()
                SceneManager().change_scene(f"level{self._level}", LevelLoadingScene._FADE_OUT_DURATION)

        if event.type == pygame.JOYBUTTONDOWN:
            if event.button == 1:
                self._fade_out_start_time = pygame.time.get_ticks()
                SceneManager().change_scene(f"level{self._level}", LevelLoadingScene._FADE_OUT_DURATION)


    def update(self) -> None:
        if not self._music_started:
            self._music.play()
            self._music_started = True

        if self._fade_out_start_time:
            elapsed_time = pygame.time.get_ticks() - self._fade_out_start_time
            volume = max(0.0, 1.0 - (elapsed_time / LevelLoadingScene._FADE_OUT_DURATION))
            self._music.set_volume(volume)
            if volume == 0:
                self._fade_out_start_time = None

    def render(self, screen: pygame.Surface) -> None:
        screen.blit(self._surface, (0, 0))

    def surface(self) -> pygame.Surface:
        return self._surface
