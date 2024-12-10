import random

import pygame
import os

from level_scene import LevelScene
from scene import Scene
from scene_manager import SceneManager
from game_settings import GameSettings


class LevelLoadingScene(Scene):
    """ Scène de chargement d'un niveau. """

    _FADE_OUT_DURATION: int = 500  # ms

    def __init__(self, level: int, level_name: str) -> None:
        super().__init__()
        self._settings = GameSettings()
        self._level = level
        self._level_name = level_name
        self._surface = pygame.image.load(self._settings.LEVEL_LOADING_SCENE).convert_alpha()
        self._music = pygame.mixer.Sound(self._settings.LOADING_AUDIO)
        self._music_started = False
        self._fade_out_start_time = None
        self._taxi_image = pygame.image.load(self._settings.LIVES_ICONS_FILENAME).convert_alpha()
        self._taxi_position = [self._settings.SCREEN_WIDTH // 2, self._settings.SCREEN_HEIGHT // 2]
        self._taxi_direction = [random.choice([-1, 1]), random.choice([-1, 1])]
        self._taxi_speed = 2

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._fade_out_start_time = pygame.time.get_ticks()
                self.load_level()

        if event.type == pygame.JOYBUTTONDOWN:
            if event.button == 1:
                self.load_level()

    def load_level(self):
        self._fade_out_start_time = pygame.time.get_ticks()
        
        if os.path.exists(self._settings.get_level_configuration(self._level)):
            SceneManager().add_scene(f"level{self._level}", LevelScene(self._level))
            SceneManager().change_scene(f"level{self._level}", LevelLoadingScene._FADE_OUT_DURATION)
        else:
            SceneManager().change_scene("game_over", LevelLoadingScene._FADE_OUT_DURATION)

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

        self._taxi_position[0] += self._taxi_direction[0] * self._taxi_speed
        self._taxi_position[1] += self._taxi_direction[1] * self._taxi_speed

        if self._taxi_position[0] <= 0 or self._taxi_position[0] >= self._settings.SCREEN_WIDTH:
            self._taxi_direction[0] *= -1
        if self._taxi_position[1] <= 0 or self._taxi_position[1] >= self._settings.SCREEN_HEIGHT:
            self._taxi_direction[1] *= -1

    def render(self, screen: pygame.Surface) -> None:
        scaled_surface = pygame.transform.scale(self._surface, (self._settings.SCREEN_WIDTH,
                                                                self._settings.SCREEN_HEIGHT))
        screen.blit(scaled_surface, (0, 0))

        # Agrandir et dessiner le taxi
        scaled_taxi = pygame.transform.scale(self._taxi_image, (80, 40))
        taxi_rect = scaled_taxi.get_rect(center=self._taxi_position)
        screen.blit(scaled_taxi, taxi_rect)

        # Texte du nom du niveau
        font = pygame.font.Font(self._settings.GAME_FONT, 40)
        text_surface = font.render(self._level_name, True, (255, 255, 255))
        text_rect = text_surface.get_rect(center=(self._settings.SCREEN_WIDTH // 2,
                                                  self._settings.SCREEN_HEIGHT // 3))

        screen.blit(text_surface, text_rect)

        # Ajouter les instructions pour les touches
        instructions_font = pygame.font.Font(self._settings.GAME_FONT, 14)
        instructions_text = [
            "Pour jouer, utilisez les touches suivantes du clavier :",
            "Flèche Haut : Monter",
            "Flèche Bas : Descendre",
            "Flèche Gauche : Se déplacer à gauche",
            "Flèche Droite : Se déplacer à droite",
            "Barre d'Espace : Ouvrir les trains d'atterrissage"
        ]

        instruction_y_start = self._settings.SCREEN_HEIGHT // 2 + 50  # Ajuster l'espacement du texte selon l'écran

        for i, line in enumerate(instructions_text):
            instructions_surface = instructions_font.render(line, True, (255, 255, 255))
            instructions_rect = instructions_surface.get_rect(center=(self._settings.SCREEN_WIDTH // 2,
                                                                      instruction_y_start + (
                                                                                i * 30)))  # 30 pour espacer les lignes
            screen.blit(instructions_surface, instructions_rect)

    def surface(self) -> pygame.Surface:
        return self._surface
