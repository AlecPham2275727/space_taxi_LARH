import pygame
import time
import json
import os

from astronaut import Astronaut
from game_settings import GameSettings
from gate import Gate
from hud import HUD
from obstacle import Obstacle
from pad import Pad
from pump import Pump
from scene import Scene
from scene_manager import SceneManager
from taxi import Taxi


class LevelScene(Scene):
    """ Un niveau de jeu. """

    _FADE_OUT_DURATION: int = 500  # ms

    _TIME_BETWEEN_ASTRONAUTS: int = 5  # s

    def __init__(self, level: int) -> None:
        """
        Initiliase une instance de niveau de jeu.
        :param level: le numéro de niveau
        """
        super().__init__()

        self._level = level
        config_file = f"level{self._level}.cfg"
        self._level_config = self._load_level_config(config_file)
        self._surface = pygame.image.load(self._level_config["surface"])
        self._music = pygame.mixer.Sound("snd/476556__magmisoundtracks__sci-fi-music-loop-01.wav")
        self._music = pygame.mixer.Sound(self._level_config["music"])
        self._music_started = False
        self._fade_out_start_time = None

        self._settings = GameSettings()
        self._hud = HUD()

        self._taxi = Taxi(tuple(self._level_config["taxi_position"]))

        self._gate = Gate(self._level_config["gate"]["image"], self._level_config["gate"]["position"])

        self._obstacles = [Obstacle(obstacle["image"], tuple(obstacle["position"])) for obstacle in self._level_config["obstacles"]]
        self._obstacle_sprites = pygame.sprite.Group()
        self._obstacle_sprites.add(self._obstacles)

        self._pumps = [Pump(pump["image"],tuple(pump["position"])) for pump in self._level_config["pumps"]]
        self._pump_sprites = pygame.sprite.Group()
        self._pump_sprites.add(self._pumps)

        self._pads = [Pad(pad["number"], pad["image"], tuple(pad["position"]), pad["astronaut_start_x"], pad["astronaut_end_x"]) for pad in self._level_config["pads"]]
        self._pad_sprites = pygame.sprite.Group()
        self._pad_sprites.add(self._pads)
        self._objectives = self.determinate_objectives()

        self._reinitialize()
        self._hud.visible = True

    def determinate_objectives(self):
        objectives = (
            [(self._pads[3], self._pads[0]),
             (self._pads[2], self._pads[4]),
             (self._pads[0], self._pads[1]),
             (self._pads[4], self._pads[2]),
             (self._pads[1], self._pads[3]),
             (self._pads[0], Pad.UP, self._gate)]
        )
        return objectives

    def handle_event(self, event: pygame.event.Event) -> None:
        """ Gère les événements PyGame. """
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE and self._taxi.is_destroyed():
                self._taxi.reset()
                self._retry_current_astronaut()
                return

        if self._astronaut:
            if self._taxi.is_destroyed() and self._astronaut.is_onboard():
                self._astronaut.reset_trip_money()

        if self._taxi:
            self._taxi.handle_event(event)

    def update(self) -> None:
        """
        Met à jour le niveau de jeu. Cette méthode est appelée à chaque itération de la boucle de jeu.
        :param delta_time: temps écoulé (en secondes) depuis la dernière trame affichée
        """
        if not self._music_started:
            self._music.play(-1)
            self._music_started = True

        if self._fade_out_start_time:
            elapsed_time = pygame.time.get_ticks() - self._fade_out_start_time
            volume = max(0.0, 1.0 - (elapsed_time / LevelScene._FADE_OUT_DURATION))
            self._music.set_volume(volume)
            if volume == 0:
                self._fade_out_start_time = None

        if self._taxi is None:
            return

        if self._astronaut:
            self._astronaut.update()
            self._hud.set_trip_money(self._astronaut.get_trip_money())

            if self._astronaut.is_onboard():
                self._taxi.board_astronaut(self._astronaut)
                if self._astronaut.target_pad is Pad.UP:
                    if self._gate.is_closed():
                        self._gate.open()
                    elif self._taxi.has_exited():
                        self._taxi.stop_reactor_sound()
                        self._taxi.unboard_astronaut()
                        self._taxi = None
                        self._fade_out_start_time = pygame.time.get_ticks()
                        SceneManager().change_scene(f"level{self._level + 1}_load", LevelScene._FADE_OUT_DURATION)
                        return
            elif self._astronaut.has_reached_destination():
                if self._nb_taxied_astronauts < len(self._objectives) - 1:
                    self._nb_taxied_astronauts += 1
                    self._astronaut = None
                    self._last_taxied_astronaut_time = time.time()
            elif self._taxi.hit_astronaut(self._astronaut):
                self._astronaut.scream_in_agony()
                if self._astronaut.get_arrived_target():
                    money_lost = self._astronaut.get_money_saved() / 2
                    self._astronaut.set_money_saved(0.0)
                    # self._hud.set_trip_money(0.0)
                    self._hud.add_bank_money(- money_lost)
                    self._astronaut = None
                    if self._nb_taxied_astronauts < len(self._astronauts) - 1:
                        self._nb_taxied_astronauts += 1
                        self._last_taxied_astronaut_time = time.time()
                else:
                    self._retry_current_astronaut()
            elif self._taxi.pad_landed_on:
                if self._taxi.pad_landed_on.number == self._astronaut.source_pad.number:
                    if self._astronaut.is_waiting_for_taxi():
                        self._astronaut.jump(self._taxi.rect.x + 20)
            elif self._astronaut.is_jumping_on_starting_pad():
                self._astronaut.wait()
        else:
            if time.time() - self._last_taxied_astronaut_time >= LevelScene._TIME_BETWEEN_ASTRONAUTS:
                self._astronaut = self.spawn_astronaut(self._nb_taxied_astronauts)

        self._taxi.update()

        for pad in self._pads:
            if self._taxi.land_on_pad(pad):
                pass  # introduire les effets secondaires d'un atterrissage ici
            elif self._taxi.crash_on_pad(pad):
                self._hud.loose_live()

        for obstacle in self._obstacles:
            if self._taxi.crash_on_obstacle(obstacle):
                self._hud.loose_live()

        if self._gate.is_closed() and self._taxi.crash_on_obstacle(self._gate):
            self._hud.loose_live()

        for pump in self._pumps:
            if self._taxi.crash_on_pump(pump):
                self._hud.loose_live()
            elif self._taxi.refuel_from(pump):
                self._hud.add_fuel(0.1)

    def render(self, screen: pygame.Surface) -> None:
        """
        Effectue le rendu du niveau pour l'afficher à l'écran.
        :param screen: écran (surface sur laquelle effectuer le rendu)
        """
        screen.blit(self._surface, (0, 0))
        self._obstacle_sprites.draw(screen)
        self._gate.draw(screen)
        self._pump_sprites.draw(screen)
        self._pad_sprites.draw(screen)
        if self._taxi:
            self._taxi.draw(screen)
        if self._astronaut:
            self._astronaut.draw(screen)
        self._hud.render(screen)

    def surface(self) -> pygame.Surface:
        return self._surface

    def _reinitialize(self) -> None:
        """ Initialise (ou réinitialise) le niveau. """
        self._nb_taxied_astronauts = 0
        self._retry_current_astronaut()
        self._hud.reset()

    def spawn_astronaut(self, index) -> Astronaut:
        objectives = self._objectives[index]
        if index == len(self._objectives)-1:
            return Astronaut(objectives[0], objectives[1], objectives[2])
        else:
            return Astronaut(objectives[0], objectives[1])

    def _retry_current_astronaut(self) -> None:
        """ Replace le niveau dans l'état où il était avant la course actuelle. """
        self._gate.close()

        self._astronauts = [
            Astronaut(
                self._pads[astronaut["source_pad"]],
                Pad.UP if astronaut["destination_pad"] == "UP" else self._pads[astronaut["destination_pad"]],
                astronaut["trip_money"]
            )
            for astronaut in self._level_config["astronauts"]
        ]
        self._last_taxied_astronaut_time = time.time()
        self._astronaut = None

#source :
#https://opensource.com/article/21/6/what-config-files
#https://www.geeksforgeeks.org/read-json-file-using-python/
    def _load_level_config(self, config_file: str) -> dict:
        """ Charge la configuration du niveau depuis un fichier JSON et la retourne.
            :param config_file: chemin vers le fichier de configuration
            :return: dictionnaire contenant la configuration du niveau
     """
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"Le fichier de configuration {config_file} est introuvable.")

        with open(config_file, 'r') as file:
            level_config = json.load(file)

        return level_config

