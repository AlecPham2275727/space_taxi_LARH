import math

import pygame
import random
import time

from enum import Enum, auto
from pad import Pad
from gate import Gate
from game_settings import GameSettings
from hud import HUD


class AstronautState(Enum):
    """ Différents états d'un astronaute. """
    WAITING = auto()
    WAVING = auto()
    JUMPING_RIGHT = auto()
    JUMPING_LEFT = auto()
    ONBOARD = auto()
    REACHED_DESTINATION = auto()
    APPEAR = auto()


class Astronaut(pygame.sprite.Sprite):
    """ Un astronaute. """

    _NB_WAITING_IMAGES = 1
    _NB_WAVING_IMAGES = 4
    _NB_JUMPING_IMAGES = 6
    _NB_TELEPORT_IMAGES = 11

    _VELOCITY = 0.2
    _LOOSE_ONE_CENT_EVERY = 0.05  # perd 1 cent tous les 5 centièmes de seconde
    _ONE_CENT = 0.01
    _WAVING_DELAYS = 10.0, 30.0

    # temps d'affichage pour les trames de chaque état affiché/animé
    _FRAME_TIMES = {AstronautState.WAITING: 0.1,
                    AstronautState.WAVING: 0.1,
                    AstronautState.JUMPING_LEFT: 0.15,
                    AstronautState.JUMPING_RIGHT: 0.15,
                    AstronautState.APPEAR: 0.2,
                    AstronautState.REACHED_DESTINATION: 1}

    _FRAMES = None
    _AUDIO_CLIPS = None

    def __init__(self, source_pad: Pad, target_pad: Pad, gate: Gate = None) -> None:
        """
        Initialise une instance d'astronaute.
        :param source_pad: le pad sur lequel apparaîtra l'astronaute
        :param target_pad: le pad où souhaite se rendre l'astronaute
        :param trip_money: le montant de départ pour la course (diminue avec le temps)
        """
        super(Astronaut, self).__init__()
        self._gate = gate
        self._source_pad = source_pad
        self._target_pad = target_pad

        self._hud = HUD()

        self._trip_money = self.calculate_trip_price()
        self._time_is_money = 0.0
        self._last_saved_time = None
        self._disappear_animation_finished = False

        if Astronaut._FRAMES is None or Astronaut._AUDIO_CLIPS is None:
            Astronaut._FRAMES, Astronaut._AUDIO_CLIPS = self._load_shared_resources()

        self._all_frames = Astronaut._FRAMES
        self._hey_taxi_clips, self._pad_please_clips, self._hey_clips = Astronaut._load_clips()

        (waiting_frames, waving_frames, jumping_left_frames, jumping_right_frames,
         disappear_frames, appear_frames) = Astronaut._load_and_build_frames()
        self._all_frames = {AstronautState.WAITING: waiting_frames,
                            AstronautState.WAVING: waving_frames,
                            AstronautState.JUMPING_LEFT: jumping_left_frames,
                            AstronautState.JUMPING_RIGHT: jumping_right_frames,
                            AstronautState.APPEAR: appear_frames,
                            AstronautState.REACHED_DESTINATION: disappear_frames}

        self.image, self.mask = self._all_frames[AstronautState.APPEAR][0]
        self.rect = self.image.get_rect()
        self.rect.x = self._source_pad.astronaut_start.x
        self.rect.y = self._source_pad.astronaut_start.y

        self._pos_x = float(self.rect.x)  # sert pour les calculs de position, plus précis qu'un entier
        self._target_x = 0.0  # position horizontale où l'astronaute tente de se rendre lorsqu'il saute
        self._velocity = 0.0

        self._waving_delay = 0  # temps avant d'envoyer la main (0 initialement, aléatoire ensuite)

        self._state = AstronautState.APPEAR
        self._frames = self._all_frames[self._state]
        self._state_time = 0  # temps écoulé dans l'état actuel
        self._current_frame = 0
        self._last_frame_time = time.time()
        self._arrived_pad_target = False

    def calculate_trip_price(self):
        origin = (self.source_pad.rect.x, self.source_pad.rect.y)
        if self.target_pad is Pad.UP:
            # L'objectif va être considéré la porte de sortie vue que Pad.UP n'a pas un rect
            target = (self._gate.rect.x, self._gate.rect.y)
        else:
            target = (self._target_pad.rect.x, self._target_pad.rect.y)
        distance = ((target[0] - origin[0]) ** 2) + ((target[1] - origin[1]) ** 2)
        base_price = 10

        trip_price = base_price + (distance * 0.00001)

        return trip_price

    @property
    def source_pad(self) -> Pad:
        return self._source_pad

    @property
    def target_pad(self) -> Pad:
        return self._target_pad

    def draw(self, surface: pygame.Surface) -> None:
        """ Dessine l'astronaute, sauf s'il est à bord du taxi. """
        if self._state != AstronautState.ONBOARD:
            surface.blit(self.image, self.rect)

    def get_trip_money(self) -> float:
        return self._trip_money

    def get_money_saved(self) -> float:
        return self._money_saved

    def set_money_saved(self, money_saved: float) -> None:
        self._money_saved = money_saved

    def set_arrived_target(self, arrived: bool) -> bool:
        self._arrived_pad_target = arrived

    def get_arrived_target(self) -> bool:
        return self._arrived_pad_target

    def has_reached_destination(self) -> bool:
        return self._disappear_animation_finished

    def reset_trip_money(self) -> None:
        self._time_is_money = 0.0
        self._trip_money = 0.0

    def scream_in_agony(self) -> None:
        clip = random.choice(self._hey_clips)
        clip.play()

    def is_jumping_on_starting_pad(self) -> bool:
        """
        Vérifie si l'astronaute est en train de se déplacer sur sa plateforme de départ.
        Pour que ce soit le cas, il doit :
            - être en train de sauter
            - être situé à sa hauteur de départ (donc sur une plateforme à la même hauteur)
            - être situé horizontalement dans les limites de la plateforme de départ
        :return: True si c'est le cas, False sinon
        """
        if self._state not in (AstronautState.JUMPING_LEFT, AstronautState.JUMPING_RIGHT):
            return False
        if self.rect.y != self._source_pad.astronaut_start.y:
            return False
        if self._source_pad.astronaut_start.x <= self.rect.x <= self._source_pad.rect.x + self._source_pad.rect.width:
            return True
        return False

    def is_onboard(self) -> bool:
        return self._state == AstronautState.ONBOARD

    def is_waiting_for_taxi(self) -> bool:
        return self._state in (AstronautState.WAITING, AstronautState.WAVING)

    def jump(self, target_x) -> None:
        """
        Commande à l'astronaute de se déplacer vers une destination horizontale (les astronautes
        ne se déplacent que horizontalement dans Space Taxi).
        :param target_x: cible horizontale (position x à l'écran)
        """
        self._target_x = target_x
        if self._target_x < self.rect.x:
            self._velocity = -Astronaut._VELOCITY
            self._state = AstronautState.JUMPING_LEFT
        elif self._target_x > self.rect.x:
            self._velocity = Astronaut._VELOCITY
            self._state = AstronautState.JUMPING_RIGHT
        self._state_time = 0
        self._frames = self._all_frames[self._state]
        self._current_frame = 0

    def move(self, x: int, y: int) -> None:
        """
        Place l'astronaute à la position (x,y) à l'écran.
        :param x: position horizontale
        :param y: position verticale
        """
        self.rect.x = x
        self.rect.y = y

        self._pos_x = float(self.rect.x)

    def set_trip_money(self, trip_money: float) -> None:
        self._trip_money = trip_money

    def update(self, *args, **kwargs) -> None:
        """
        Met à jour l'astronaute. Cette méthode est appelée à chaque itération de la boucle de jeu.
        :param args: inutilisé
        :param kwargs: inutilisé
        """
        current_time = time.time()

        # ÉTAPE 1 - diminuer le montant de la course si le moment est venu
        if self._last_saved_time is None:
            self._last_saved_time = current_time
        else:
            self._time_is_money += current_time - self._last_saved_time
            self._last_saved_time = current_time
            if self._time_is_money >= Astronaut._LOOSE_ONE_CENT_EVERY:
                self._time_is_money = 0.0
                self._trip_money = max(0.0, self._trip_money - Astronaut._ONE_CENT)

        if self._state == AstronautState.ONBOARD:
            # pas d'animation dans cet état
            return

        # ÉTAPE 2 - changer de trame si le moment est venu
        frame_change_condition = None
        if self._state == AstronautState.REACHED_DESTINATION:
            frame_change_condition = (current_time - self._last_frame_time >=
                                      Astronaut._FRAME_TIMES[self._state]/len(self._frames))
        else:
            frame_change_condition = current_time - self._last_frame_time >= Astronaut._FRAME_TIMES[self._state]
        if frame_change_condition:
            self._current_frame = (self._current_frame + 1) % len(self._frames)
            self._last_frame_time = current_time

        # ÉTAPE 3 - changer d'état si le moment est venu
        self._state_time += current_time - self._last_frame_time
        if ((self._state == AstronautState.APPEAR) and
                (self._state_time >= self._FRAME_TIMES[AstronautState.REACHED_DESTINATION] * len(self._frames))):
            self.change_state(AstronautState.WAITING)
        elif ((self._state == AstronautState.REACHED_DESTINATION) and
              (self._state_time >= self._FRAME_TIMES[AstronautState.REACHED_DESTINATION] * len(self._frames))):
            self._disappear_animation_finished = True
        elif self._state == AstronautState.WAITING:
            if self._state_time >= self._waving_delay:
                self._call_taxi()
                self.change_state(AstronautState.WAVING)
        elif self._state == AstronautState.WAVING:
            last_frame = self._current_frame == len(self._frames) - 1
            spent_state_time = self._state_time >= self._FRAME_TIMES[AstronautState.WAVING] * len(self._frames)
            if last_frame and spent_state_time:
                self.change_state(AstronautState.WAITING)
                self._waving_delay = random.uniform(*Astronaut._WAVING_DELAYS)
        elif self._state in (AstronautState.JUMPING_RIGHT, AstronautState.JUMPING_LEFT):
            if self.rect.x == self._target_x:
                if self._target_pad is not Pad.UP and self._target_x == self._target_pad.astronaut_end.x:
                    self.change_state(AstronautState.REACHED_DESTINATION)
                else:
                    self._state = AstronautState.ONBOARD
                    self._play_destination_clip()
                    if self._target_pad is None:
                        self._pad_please_clips[0].play()
                    else:
                        self._hud.display_pad_destination(self.target_pad.number)

                return

            self._pos_x += self._velocity
            self.rect.x = round(self._pos_x)

        self.image, self.mask = self._frames[self._current_frame]

        if self._state == AstronautState.REACHED_DESTINATION:
            return

    def change_state(self, entered_state):
        self._state = entered_state
        self._state_time = 0
        self._frames = self._all_frames[entered_state]
        self._current_frame = 0

    # refactor
    def wait(self) -> None:
        """ Replace l'astronaute dans l'état d'attente. """
        self.change_state(AstronautState.WAITING)

    def _call_taxi(self) -> None:
        """ Joue le son d'appel du taxi. """
        if self._state == AstronautState.WAITING:
            clip = random.choice(self._hey_taxi_clips)
            clip.play()

    @staticmethod
    def _load_and_build_frames() -> tuple:
        """
        Charge et découpe la feuille de sprites (sprite sheet) pour un astronaute.
        :return: un tuple contenant dans l'ordre:
                     - une liste de trames (image, masque) pour attendre
                     - une liste de trames (image, masque) pour envoyer la main
                     - une liste de trames (image, masque) pour se déplacer vers la gauche
                     - une liste de trames (image, masque) pour se déplacer vers la droite
                     - une liste de trames (image, masque) pour se téléporter
        """
        nb_images = (Astronaut._NB_WAITING_IMAGES + Astronaut._NB_WAVING_IMAGES + Astronaut._NB_JUMPING_IMAGES +
                     Astronaut._NB_TELEPORT_IMAGES)
        sprite_sheet = pygame.image.load(GameSettings.ASTRONAUT_FILENAME).convert_alpha()
        sheet_width = sprite_sheet.get_width()
        sheet_height = sprite_sheet.get_height()
        image_size = (sheet_width / nb_images, sheet_height)

        # astronaute qui attend
        waiting_surface = pygame.Surface(image_size, flags=pygame.SRCALPHA)
        source_rect = waiting_surface.get_rect()
        waiting_surface.blit(sprite_sheet, (0, 0), source_rect)
        waiting_mask = pygame.mask.from_surface(waiting_surface)
        waiting_frames = [(waiting_surface, waiting_mask)]

        # astronaute qui envoie la main (les _NB_WAVING_IMAGES prochaines images)
        waving_frames = []
        waving_frames_collection = []
        first_frame = Astronaut._NB_WAITING_IMAGES

        for frame in range(first_frame, first_frame + Astronaut._NB_WAVING_IMAGES):
            surface = pygame.Surface(image_size, flags=pygame.SRCALPHA)
            source_rect = surface.get_rect()
            source_rect.x = frame * source_rect.width
            surface.blit(sprite_sheet, (0, 0), source_rect)
            mask = pygame.mask.from_surface(surface)
            waving_frames_collection.append((surface, mask))

        waving_frames_collection.extend(waving_frames_collection[1:-1][::-1])
        repeated_frames = [waving_frames_collection[1], waving_frames_collection[2], waving_frames_collection[3],
                           waving_frames_collection[2], waving_frames_collection[1]]

        waving_frames.extend([waving_frames_collection[0]])
        for i in range(3):
            waving_frames.extend(repeated_frames)
        waving_frames.extend([waving_frames_collection[0]])

        # astronaute qui se déplace en sautant (les _NB_JUMPING_IMAGES prochaines images)
        jumping_left_frames = []
        jumping_right_frames = []
        first_frame = Astronaut._NB_WAITING_IMAGES + Astronaut._NB_WAVING_IMAGES
        for frame in range(first_frame, first_frame + Astronaut._NB_JUMPING_IMAGES):
            surface = pygame.Surface(image_size, flags=pygame.SRCALPHA)
            source_rect = surface.get_rect()
            source_rect.x = frame * source_rect.width
            surface.blit(sprite_sheet, (0, 0), source_rect)
            mask = pygame.mask.from_surface(surface)
            jumping_right_frames.append((surface, mask))

            flipped_surface = pygame.transform.flip(surface, True, False)
            flipped_mask = pygame.mask.from_surface(flipped_surface)
            jumping_left_frames.append((flipped_surface, flipped_mask))

        # astronaute qui se téléporte

        teleport_frames = []
        appear_frames = []
        disappear_frames = []
        first_frame = Astronaut._NB_WAITING_IMAGES + Astronaut._NB_WAVING_IMAGES + Astronaut._NB_JUMPING_IMAGES + 1
        for frame in range(first_frame, first_frame + Astronaut._NB_TELEPORT_IMAGES - 1):
            surface = pygame.Surface(image_size, flags=pygame.SRCALPHA)
            source_rect = surface.get_rect()
            source_rect.x = frame * source_rect.width
            surface.blit(sprite_sheet, (0, 0), source_rect)
            mask = pygame.mask.from_surface(surface)
            teleport_frames.append((surface, mask))

        for i in range(int(len(teleport_frames) / 2)):
            chosen_appear_frame = teleport_frames[random.randint(i * 2, i * 2 + 1)]
            chosen_disappear_frame = teleport_frames[
                random.randint((len(teleport_frames) - i * 2) - 2, (len(teleport_frames) - i * 2) - 1)]
            appear_frames.append(chosen_appear_frame)
            disappear_frames.append(chosen_disappear_frame)

        return (waiting_frames, waving_frames, jumping_left_frames, jumping_right_frames, appear_frames,
                disappear_frames)

    @staticmethod
    def _load_clips() -> tuple:
        """
        Charge les clips sonores (voix).
        :return: un tuple contenant dans l'ordre:
                     - une liste de clips (pygame.mixer.Sound) "Hey, taxi"
                     - une liste de clips (pygame.mixer.Sound) "Pad # please" ou "Up please"
                     - une liste de clips (pygame.mixer.Sound) "Hey!"
        """
        hey_taxis = [pygame.mixer.Sound("voices/gary_hey_taxi_01.mp3"),
                     pygame.mixer.Sound("voices/gary_hey_taxi_02.mp3"),
                     pygame.mixer.Sound("voices/gary_hey_taxi_03.mp3")]

        pad_pleases = [pygame.mixer.Sound("voices/gary_up_please_01.mp3"),
                       pygame.mixer.Sound("voices/gary_pad_1_please_01.mp3"),
                       pygame.mixer.Sound("voices/gary_pad_2_please_01.mp3"),
                       pygame.mixer.Sound("voices/gary_pad_3_please_01.mp3"),
                       pygame.mixer.Sound("voices/gary_pad_4_please_01.mp3"),
                       pygame.mixer.Sound("voices/gary_pad_5_please_01.mp3")]

        heys = [pygame.mixer.Sound("voices/gary_hey_01.mp3")]

        return hey_taxis, pad_pleases, heys

    def _play_destination_clip(self) -> None:
        """ Joue un clip audio qui indique la destination. """
        if self._target_pad is Pad.UP:
            clip = self._pad_please_clips[0] # Si la destination est "Up"
        else:
            pad_number = self._target_pad.number
            clip = self._pad_please_clips[pad_number]
        clip.play()

    @staticmethod
    def _load_shared_resources():
        """ Charge les ressources partagées par toutes les instances. """
        frames = Astronaut._load_and_build_frames()
        audio_clips = Astronaut._load_clips()
        return frames, audio_clips

    def stop_animation(self):
        """ Arrête toute animation et interaction de l'astronaute.self """
        self._state = AstronautState.REACHED_DESTINATION
        self._velocity = 0.0
        self._current_frame = 0
        print("Animation de l'astronaute arrêtée.")