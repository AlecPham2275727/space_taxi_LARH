# CRÉDIT: Pour la tâche des réacteurs qui tue l'astronaute, j'ai consulté les sources suivantes:
# https://www.pygame.org/docs/ref/mask.html
# https://scuba.cs.uchicago.edu/pygame/ref/mask.html#pygame.mask.Mask.overlap
# https://stackoverflow.com/questions/67846651/pygame-masks-python
# https://www.pygame.org/docs/ref/mask.html#pygame.mask.Mask.draw

from enum import Enum, auto

import pygame

from astronaut import Astronaut
from hud import HUD
from obstacle import Obstacle
from pad import Pad
from pump import Pump
from input_settings import InputSettings
from game_settings import GameSettings


class ImgSelector(Enum):
    """ Sélecteur d'image de taxi. """
    IDLE = auto()
    BOTTOM_REACTOR = auto()
    TOP_REACTOR = auto()
    REAR_REACTOR = auto()
    BOTTOM_AND_REAR_REACTORS = auto()
    TOP_AND_REAR_REACTORS = auto()
    GEAR_OUT = auto()
    GEAR_SHOCKS = auto()
    GEAR_OUT_AND_BOTTOM_REACTOR = auto()
    DESTROYED = auto()


class DirectionSelector(Enum):
    LEFT = auto()
    RIGHT = auto()
    UP = auto()
    DOWN = auto()


class Taxi(pygame.sprite.Sprite):
    """ Un taxi spatial. """

    _NB_TAXI_IMAGES = 6

    _FLAG_LEFT = 1 << 0  # indique si le taxi va vers la gauche
    _FLAG_TOP_REACTOR = 1 << 1  # indique si le réacteur du dessus est allumé
    _FLAG_BOTTOM_REACTOR = 1 << 2  # indique si le réacteur du dessous est allumé
    _FLAG_REAR_REACTOR = 1 << 3  # indique si le réacteur arrière est allumé
    _FLAG_GEAR_OUT = 1 << 4  # indique si le train d'atterrissage est sorti
    _FLAG_DESTROYED = 1 << 5  # indique si le taxi est détruit
    _FLAG_GEAR_SHOCKS = 1 << 6  # indique si le train d'atterrissage est compressé

    _REACTOR_SOUND_VOLUME = 0.25

    _REAR_REACTOR_POWER = 0.001
    _BOTTOM_REACTOR_POWER = 0.0005
    _TOP_REACTOR_POWER = 0.00025

    _MAX_ACCELERATION_X = 0.075
    _MAX_ACCELERATION_Y_UP = 0.08
    _MAX_ACCELERATION_Y_DOWN = 0.05

    _MAX_VELOCITY_SMOOTH_LANDING = 0.50  # vitesse maximale permise pour un atterrissage en douceur
    _MAX_VELOCITY_ROUGH_LANDING = 1.00
    _CRASH_ACCELERATION = 0.10

    _FRICTION_MUL = 0.9995  # la vitesse horizontale est multipliée par la friction
    _FRICTION_PAD = 0.9395
    _GRAVITY_ADD = 0.005  # la gravité est ajoutée à la vitesse verticale

    # _GRAVITY_ADD = 0.0
    def __init__(self, pos: tuple) -> None:
        """
        Initialise une instance de taxi.
        :param pos:
        """
        super(Taxi, self).__init__()
        self._velocity = None
        self._flags = None
        self._right_leg_rect = None
        self._left_leg_rect = None
        self._landed = False
        self._pad_landed_on = None
        self._sliding = None
        self._astronaut = None
        self._settings = GameSettings()
        self._fuel_ran_out = False

        self._initial_pos = pos

        self._hud = HUD()

        self._joystick = InputSettings().joystick

        self._reactor_sound = pygame.mixer.Sound(self._settings.REACTOR_SOUND)
        self._reactor_sound.set_volume(0)
        self._reactor_sound.play(-1)

        self._crash_sound = pygame.mixer.Sound(self._settings.CRASH_SOUND)
        self._smooth_landing_sound = pygame.mixer.Sound(self._settings.SMOOTH_LANDING_SOUND)
        self._rough_landing_sound = pygame.mixer.Sound(self._settings.ROUGH_LANDING_SOUND)

        self._surfaces, self._masks = Taxi._load_and_build_surfaces()

        self._reinitialize()

        self._start_compressed_gear_time = 0

        self._movement_locked = False
        self._unlock_time = 0
        self.crashed_on_one_foot = False

        self._previous_direction_x = None
        self._previous_direction_y = None

    @property
    def pad_landed_on(self) -> Pad or None:
        return self._pad_landed_on

    def board_astronaut(self, astronaut: Astronaut) -> None:
        self._astronaut = astronaut

    def crash_on_obstacle(self, obstacle: Obstacle) -> bool:
        """
        Vérifie si le taxi est en situation de crash contre un obstacle.
        :param obstacle: obstacle avec lequel vérifier
        :return: True si le taxi est en contact avec l'obstacle, False sinon
        """
        return self._crash_on_level_objects(obstacle)

    def _crash_on_level_objects(self, collidable_object: pygame.sprite.Sprite) -> bool:
        """
        Vérifie si le taxi est en situation de crash contre un objet du niveau.
        :param collidable_object: objet qui peut être en collision
        :return: True si le taxi est en contact avec l'objet, False sinon
        """
        if not isinstance(collidable_object, (Pump, Pad, Obstacle)):
            return False

        if self._flags & Taxi._FLAG_DESTROYED == Taxi._FLAG_DESTROYED:
            return False

        if self.rect.colliderect(collidable_object.rect):
            if self.mask.overlap(collidable_object.mask, (collidable_object.rect.x - self.rect.x,
                                                          collidable_object.rect.y - self.rect.y)):
                self._flags = self._FLAG_DESTROYED
                self._crash_sound.play()
                self._velocity = pygame.Vector2(0.0)
                self._acceleration.y = Taxi._CRASH_ACCELERATION
                self._acceleration.x = 0.0
                return True

        return False

    def crash_on_pad(self, pad: Pad) -> bool:
        """
        Vérifie si le taxi est en situation de crash contre une plateforme.
        :param pad: plateforme avec laquelle vérifier
        :return: True si le taxi est en contact avec la plateforme, False sinon
        """
        return self._crash_on_level_objects(pad)

    def crash_on_pump(self, pump: Pump) -> bool:
        """
        Vérifie si le taxi est en situation de crash contre une pompe.
        :param pump: pompe avec laquelle vérifier
        :return: True si le taxi est en contact avec la pompe, False sinon
        """
        return self._crash_on_level_objects(pump)

    def draw(self, surface: pygame.Surface) -> None:
        """ Dessine le taxi sur la surface fournie comme argument. """
        surface.blit(self.image, self.rect)

    def handle_event(self, event: pygame.event.Event) -> None:
        """ Gère les événements du taxi. """
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                if self._pad_landed_on is None:
                    if self._flags & Taxi._FLAG_GEAR_OUT != Taxi._FLAG_GEAR_OUT:
                        # pas de réacteurs du dessus et arrière lorsque le train d'atterrissage est sorti
                        self._flags &= ~(Taxi._FLAG_TOP_REACTOR | Taxi._FLAG_REAR_REACTOR)

                    self._flags ^= Taxi._FLAG_GEAR_OUT  # flip le bit pour refléter le nouvel état

                    self._select_image()

        if event.type == pygame.JOYBUTTONDOWN:
            if event.button == 1:
                if self._pad_landed_on is None:
                    if self._flags & Taxi._FLAG_GEAR_OUT != Taxi._FLAG_GEAR_OUT:
                        self._flags &= ~(Taxi._FLAG_TOP_REACTOR | Taxi._FLAG_REAR_REACTOR)

                    self._flags ^= Taxi._FLAG_GEAR_OUT

                    self._select_image()

    def has_exited(self) -> bool:
        """
        Vérifie si le taxi a quitté le niveau (par la sortie).
        :return: True si le taxi est sorti du niveau, False sinon
        """
        return self.rect.y <= -self.rect.height

    def stop_reactor_sound(self) -> None:
        """ Arrête le son des réacteurs """
        self._reactor_sound.stop()

    def hit_astronaut(self, astronaut: Astronaut) -> bool:
        """
        Vérifie si le taxi frappe un astronaute.
        :param astronaut: astronaute pour lequel vérifier
        :return: True si le taxi frappe l'astronaute, False sinon
        """

        if self._pad_landed_on or astronaut.is_onboard():
            return False

        if self.rect.colliderect(astronaut.rect):
            if self.mask_taxi_reactor.overlap(astronaut.mask,
                                              (astronaut.rect.x - self.rect.x, astronaut.rect.y - self.rect.y)):
                return True

        return False

    def is_destroyed(self) -> bool:
        """
        Vérifie si le taxi est détruit.
        :return: True si le taxi est détruit, False sinon
        """
        return self._flags & Taxi._FLAG_DESTROYED == Taxi._FLAG_DESTROYED

    def land_on_pad(self, pad: Pad) -> bool:
        """
        Vérifie si le taxi est en situation d'atterrissage sur une plateforme.
        :param pad: plateforme pour laquelle vérifier
        :return: True si le taxi est atterri, False sinon
        """
        gear_out = (self._flags & Taxi._FLAG_GEAR_OUT) == Taxi._FLAG_GEAR_OUT
        if not gear_out:
            return False

        if self._velocity.y > Taxi._MAX_VELOCITY_ROUGH_LANDING or self._velocity.y < 0.0:  # self._acceleration_y < 0.0:
            return False

        if not self.rect.colliderect(pad.rect):
            return False

        # Définir les zones des pattes
        # Source : https://www.pygame.org/docs/ref/rect.html
        self._left_leg_rect = pygame.Rect(self.rect.left, self.rect.bottom - 10, self.rect.width / 4, 6)
        self._right_leg_rect = pygame.Rect(self.rect.centerx + self.rect.width / 4, self.rect.bottom - 10,
                                           self.rect.width / 4, 6)

        # Vérifier les collisions des masques des pattes
        left_leg_offset = (
            self._left_leg_rect.x - pad.rect.x,
            self._left_leg_rect.y - pad.rect.y)
        right_leg_offset = (self._right_leg_rect.x - pad.rect.x,
                            self._right_leg_rect.y - pad.rect.y)

        left_leg_collision = pad.mask.overlap(pad.mask, left_leg_offset)
        right_leg_collision = pad.mask.overlap(pad.mask, right_leg_offset)
        
        # Si la seulement la patte droite est sur la plataforme la valeur de left_leg_collision est (0,0)
        # Si la seulement la patte gauche est sur la plataforme la valeur de right_leg_collision est None
        if (left_leg_collision == (0, 0)) or (not right_leg_collision):
            # Crash si une seule patte est sur la plateforme
            self.handle_crash()
            return False
        elif left_leg_collision and right_leg_collision:
            if not self._landed:
                # Atterrissage réussi
                self._landed = True
                if self._MAX_VELOCITY_SMOOTH_LANDING < self._velocity.y <= self._MAX_VELOCITY_ROUGH_LANDING:
                    self._rough_landing_sound.play()
                    self._flags &= ~Taxi._FLAG_GEAR_OUT
                    self._flags |= Taxi._FLAG_GEAR_SHOCKS
                    self._start_compressed_gear_time = pygame.time.get_ticks()

                elif self._MAX_VELOCITY_SMOOTH_LANDING >= self._velocity.y > 0.0:
                    self._smooth_landing_sound.play()
                    self._flags &= Taxi._FLAG_LEFT | Taxi._FLAG_GEAR_OUT

                self.rect.bottom = pad.rect.top + 4
                self._position.y = float(self.rect.y)
                self._velocity.y = self._acceleration.y = self._acceleration.x = 0.0
                self._sliding = True

                self._pad_landed_on = pad
                if self._astronaut:
                    if self._astronaut.target_pad == Pad.UP:
                        print("L'astronaute doit être transporté vers la sortie, non débarqué.")
                    elif (self._astronaut.target_pad.number == pad.number) and not self._astronaut.isDisembarked:
                        self.unboard_astronaut()
            return True

    def handle_crash(self):
        """ Gère le crash du taxi et interrompt toutes les animations. """
        self._flags = Taxi._FLAG_DESTROYED
        self._crash_sound.play()
        self._velocity = pygame.Vector2(0.0)
        self._acceleration.y = Taxi._CRASH_ACCELERATION
        self._acceleration.x = 0.0
        self.crashed_on_one_foot = True

        self._hud.loose_live()

    def refuel_from(self, pump: Pump) -> bool:
        """
        Vérifie si le taxi est en position de faire le plein d'essence.
        :param pump: pompe pour laquelle vérifier
        :return: True si le taxi est en bonne position, False sinon
        """
        if self._pad_landed_on is None:
            return False

        if not self.rect.colliderect(pump.rect):
            return False

        return True

    def reset(self) -> None:
        """ Réinitialise le taxi. """
        self._reinitialize()

    def unboard_astronaut(self) -> None:
        """ Fait descendre l'astronaute qui se trouve à bord. """
        self.crashed_on_one_foot = False
        self._astronaut.isDisembarked = True
        self._astronaut.set_arrived_target(True)
        if self._astronaut.target_pad is not Pad.UP:
            self._astronaut.move(self.rect.x + 20, self._pad_landed_on.rect.y - self._astronaut.rect.height)
            self._astronaut.jump(self._pad_landed_on.astronaut_end.x)

        self._hud.add_bank_money(self._astronaut.get_trip_money())
        self._astronaut.set_money_saved(self._astronaut.get_trip_money())
        self._astronaut.set_trip_money(0.0)

    def update(self, *args, **kwargs) -> None:
        """
        Met à jour le taxi. Cette méthode est appelée à chaque itération de la boucle de jeu.
        :param args: inutilisé
        :param kwargs: inutilisé
        """
        # Empêche tout mouvement tant que le verrouillage est actif
        if self._movement_locked:
            if pygame.time.get_ticks() >= self._unlock_time:
                self._movement_locked = False
            else:
                return

        # ÉTAPE 1 - gérer les touches présentement enfoncées
        self._handle_input()

        # ÉTAPE 2 - calculer la nouvelle position du taxi
        self._velocity.x += self._acceleration.x
        self._velocity.x *= Taxi._FRICTION_MUL
        self._velocity.y += self._acceleration.y

        if self._pad_landed_on is None:
            self._velocity.y += Taxi._GRAVITY_ADD

        self._position += self._velocity

        self.rect.x = round(self._position.x)
        self.rect.y = round(self._position.y)

        if self._pad_landed_on and self._sliding:
            self._velocity.x *= self._FRICTION_PAD
            if self._velocity.x < 0.1:
                self._sliding = False
                self._velocity.x = 0

        # ÉTAPE 3 - fait entendre les réacteurs ou pas
        reactor_flags = Taxi._FLAG_TOP_REACTOR | Taxi._FLAG_REAR_REACTOR | Taxi._FLAG_BOTTOM_REACTOR
        if self._flags & reactor_flags:
            self._reactor_sound.set_volume(Taxi._REACTOR_SOUND_VOLUME)
        else:
            self._reactor_sound.set_volume(0)

        if self._flags & Taxi._FLAG_GEAR_SHOCKS:
            elapsed_time = pygame.time.get_ticks() - self._start_compressed_gear_time
            if elapsed_time >= 500:
                self._flags &= ~Taxi._FLAG_GEAR_SHOCKS
                self._flags |= Taxi._FLAG_GEAR_OUT

        # ÉTAPE 4 - sélectionner la bonne image en fonction de l'état du taxi
        self._select_image()

        self._combine_reactor_mask()

        if not self._fuel_ran_out:
            self._consume_fuel()

        if self.is_destroyed():
            return

    def lock_movement(self, duration):
        """ Verrouille le mouvement du taxi pendant une durée spécifiée (en millisecondes). """
        self._movement_locked = True
        self._unlock_time = pygame.time.get_ticks() + duration

    def _combine_reactor_mask(self) -> None:
        """ Crée un mask qui inclut les réacteurs qui sont activées selon les flags du taxi """
        facing = self._flags & Taxi._FLAG_LEFT

        mask_with_reactor = pygame.mask.from_surface(self.image)

        reactors = [
            (Taxi._FLAG_BOTTOM_REACTOR, ImgSelector.BOTTOM_REACTOR),
            (Taxi._FLAG_TOP_REACTOR, ImgSelector.TOP_REACTOR),
            (Taxi._FLAG_REAR_REACTOR, ImgSelector.REAR_REACTOR)
        ]

        for flag, activated_reactor in reactors:
            if self._flags & flag:
                reactor_mask = self._masks[activated_reactor][facing]
                mask_with_reactor.draw(reactor_mask, (0, 0))

        self.mask_taxi_reactor = mask_with_reactor

    def _handle_input(self) -> None:
        """ Change ou non l'état du taxi en fonction des touches présentement enfoncées. """
        x_axis = y_axis = 0.0

        if self._joystick:
            x_axis = self._joystick.get_axis(0)
            y_axis = self._joystick.get_axis(4)

        keys = pygame.key.get_pressed()

        if self._flags & Taxi._FLAG_DESTROYED == Taxi._FLAG_DESTROYED:
            return

        gear_out = self._flags & Taxi._FLAG_GEAR_OUT == Taxi._FLAG_GEAR_OUT
        gear_shocks = self._flags & Taxi._FLAG_GEAR_SHOCKS == Taxi._FLAG_GEAR_SHOCKS

        current_direction_x = None
        current_direction_y = None

        if (keys[pygame.K_LEFT] or x_axis < -0.5) and (not gear_out and not gear_shocks):
            current_direction_x = DirectionSelector.LEFT
            self._flags |= Taxi._FLAG_LEFT | Taxi._FLAG_REAR_REACTOR
            self._acceleration.x = max(self._acceleration.x - Taxi._REAR_REACTOR_POWER, -Taxi._MAX_ACCELERATION_X)

        elif (keys[pygame.K_RIGHT] or x_axis > 0.5) and (not gear_out and not gear_shocks):
            current_direction_x = DirectionSelector.RIGHT
            self._flags &= ~Taxi._FLAG_LEFT
            self._flags |= self._FLAG_REAR_REACTOR
            self._acceleration.x = min(self._acceleration.x + Taxi._REAR_REACTOR_POWER, Taxi._MAX_ACCELERATION_X)

        else:
            self._flags &= ~Taxi._FLAG_REAR_REACTOR
            self._acceleration.x = 0.0

        if current_direction_x != self._previous_direction_x:
            self._acceleration.x = 0.0

        self._previous_direction_x = current_direction_x

        if (keys[pygame.K_DOWN] or y_axis > 0.5) and (not gear_out and not gear_shocks):
            current_direction_y = DirectionSelector.DOWN
            self._flags &= ~Taxi._FLAG_BOTTOM_REACTOR
            self._flags |= Taxi._FLAG_TOP_REACTOR
            self._acceleration.y = min(self._acceleration.y + Taxi._TOP_REACTOR_POWER, Taxi._MAX_ACCELERATION_Y_DOWN)

        elif keys[pygame.K_UP] or y_axis < -0.5:
            self._landed = False
            current_direction_y = DirectionSelector.UP
            self._flags |= Taxi._FLAG_BOTTOM_REACTOR
            self._acceleration.y = max(self._acceleration.y - Taxi._BOTTOM_REACTOR_POWER, -Taxi._MAX_ACCELERATION_Y_UP)
            if self._pad_landed_on:
                self._flags &= ~Taxi._FLAG_GEAR_OUT  # rentrer le train d'atterrissage
                self._pad_landed_on = None

        else:
            self._flags &= ~(Taxi._FLAG_TOP_REACTOR | Taxi._FLAG_BOTTOM_REACTOR)
            self._acceleration.y = 0.0

        if current_direction_y != self._previous_direction_y:
            self._acceleration.y = 0.0

        self._previous_direction_y = current_direction_y

    def _reinitialize(self) -> None:
        """ Initialise (ou réinitialise) les attributs de l'instance. """
        self._flags = 0
        self._select_image()

        self.rect = self.image.get_rect()
        self.rect.x = self._initial_pos[0] - self.rect.width / 2
        self.rect.y = self._initial_pos[1] - self.rect.height / 2

        self._position = pygame.Vector2(float(self.rect.x), float(self.rect.y))
        self._velocity = pygame.Vector2(0.0, 0.0)
        self._acceleration = pygame.Vector2(0.0, 0.0)

        self._pad_landed_on = None
        self._taking_off = False

        self._astronaut = None
        self._sliding = False
        self._start_compressed_gear_time = 0
        self._hud.set_trip_money(0.0)
        self._hud.reset_fuel()
        self._fuel_ran_out = False
        self._landed = False
        self.crashed_on_one_foot = False

    def _consume_fuel(self):
        """
            Consomme du carburant basé sur les réacteurs actifs.
        """
        total_consumption = 0.0
        if self._flags & Taxi._FLAG_TOP_REACTOR:
            total_consumption += Taxi._TOP_REACTOR_POWER * 50

        if self._flags & Taxi._FLAG_BOTTOM_REACTOR:
            total_consumption += Taxi._BOTTOM_REACTOR_POWER * 50

        if self._flags & Taxi._FLAG_REAR_REACTOR:
            total_consumption += Taxi._REAR_REACTOR_POWER * 50

        if total_consumption > 0.0:
            self._hud.consume_fuel(total_consumption)

        if self._hud.get_current_fuel() <= 0.0:
            self._flags = Taxi._FLAG_DESTROYED
            self._velocity.x = 0.0
            self._acceleration = pygame.Vector2(0.0, Taxi._CRASH_ACCELERATION)
            self._hud.loose_live()
            self._fuel_ran_out = True

    def _select_image(self) -> None:
        """ Sélectionne l'image et le masque à utiliser pour l'affichage du taxi en fonction de son état. """
        facing = self._flags & Taxi._FLAG_LEFT

        if self._flags & Taxi._FLAG_DESTROYED:
            self.image = self._surfaces[ImgSelector.DESTROYED][facing]
            self.mask = self._masks[ImgSelector.DESTROYED][facing]
            return

        condition_flags = Taxi._FLAG_TOP_REACTOR | Taxi._FLAG_REAR_REACTOR
        if self._flags & condition_flags == condition_flags:
            self.image = self._surfaces[ImgSelector.TOP_AND_REAR_REACTORS][facing]
            self.mask = self._masks[ImgSelector.TOP_AND_REAR_REACTORS][facing]
            return

        condition_flags = Taxi._FLAG_BOTTOM_REACTOR | Taxi._FLAG_REAR_REACTOR
        if self._flags & condition_flags == condition_flags:
            self.image = self._surfaces[ImgSelector.BOTTOM_AND_REAR_REACTORS][facing]
            self.mask = self._masks[ImgSelector.BOTTOM_AND_REAR_REACTORS][facing]
            return

        if self._flags & Taxi._FLAG_REAR_REACTOR:
            self.image = self._surfaces[ImgSelector.REAR_REACTOR][facing]
            self.mask = self._masks[ImgSelector.REAR_REACTOR][facing]
            return

        condition_flags = Taxi._FLAG_GEAR_OUT | Taxi._FLAG_BOTTOM_REACTOR
        if self._flags & condition_flags == condition_flags:
            self.image = self._surfaces[ImgSelector.GEAR_OUT_AND_BOTTOM_REACTOR][facing]
            self.mask = self._masks[ImgSelector.GEAR_OUT_AND_BOTTOM_REACTOR][facing]
            return

        if self._flags & Taxi._FLAG_BOTTOM_REACTOR:
            self.image = self._surfaces[ImgSelector.BOTTOM_REACTOR][facing]
            self.mask = self._masks[ImgSelector.BOTTOM_REACTOR][facing]
            return

        if self._flags & Taxi._FLAG_TOP_REACTOR:
            self.image = self._surfaces[ImgSelector.TOP_REACTOR][facing]
            self.mask = self._masks[ImgSelector.TOP_REACTOR][facing]
            return

        if self._flags & Taxi._FLAG_GEAR_OUT:
            self.image = self._surfaces[ImgSelector.GEAR_OUT][facing]
            self.mask = self._masks[ImgSelector.GEAR_OUT][facing]
            return

        if self._flags & Taxi._FLAG_DESTROYED:
            self.image = self._surfaces[ImgSelector.DESTROYED][facing]
            self.mask = self._masks[ImgSelector.DESTROYED][facing]
            return

        if self._flags & Taxi._FLAG_GEAR_SHOCKS:
            self.image = self._surfaces[ImgSelector.GEAR_SHOCKS][facing]
            self.mask = self._masks[ImgSelector.GEAR_SHOCKS][facing]
            return

        self.image = self._surfaces[ImgSelector.IDLE][facing]
        self.mask = self._masks[ImgSelector.IDLE][facing]

    @staticmethod
    def _load_and_build_surfaces() -> tuple:
        """
        Charge et découpe la feuille de sprites (sprite sheet) pour le taxi.
        Construit les images et les masques pour chaque état.
        :return: un tuple contenant deux dictionnaires (avec les états comme clés):
                     - un dictionnaire d'images (pygame.Surface)
                     - un dictionnaire de masques (pygame.Mask)
        """
        surfaces = {}
        masks = {}
        sprite_sheet = pygame.image.load(GameSettings.TAXIS_FILENAME).convert_alpha()
        sheet_width = sprite_sheet.get_width()
        sheet_height = sprite_sheet.get_height()

        # taxi normal - aucun réacteur - aucun train d'atterrissage
        surface = pygame.Surface((sheet_width / Taxi._NB_TAXI_IMAGES, sheet_height), flags=pygame.SRCALPHA)
        source_rect = surface.get_rect()
        surface.blit(sprite_sheet, (0, 0), source_rect)
        flipped = pygame.transform.flip(surface, True, False)
        surfaces[ImgSelector.IDLE] = surface, flipped
        masks[ImgSelector.IDLE] = pygame.mask.from_surface(surface), pygame.mask.from_surface(flipped)

        # taxi avec réacteur du dessous
        surface = pygame.Surface((sheet_width / Taxi._NB_TAXI_IMAGES, sheet_height), flags=pygame.SRCALPHA)
        source_rect = surface.get_rect()
        surface.blit(sprite_sheet, (0, 0), source_rect)
        source_rect.x = source_rect.width
        surface.blit(sprite_sheet, (0, 0), source_rect)
        flipped = pygame.transform.flip(surface, True, False)
        surfaces[ImgSelector.BOTTOM_REACTOR] = surface, flipped
        masks[ImgSelector.BOTTOM_REACTOR] = masks[ImgSelector.IDLE]

        # taxi avec réacteur du dessus
        surface = pygame.Surface((sheet_width / Taxi._NB_TAXI_IMAGES, sheet_height), flags=pygame.SRCALPHA)
        source_rect = surface.get_rect()
        surface.blit(sprite_sheet, (0, 0), source_rect)
        source_rect.x = 2 * source_rect.width
        surface.blit(sprite_sheet, (0, 0), source_rect)
        flipped = pygame.transform.flip(surface, True, False)
        surfaces[ImgSelector.TOP_REACTOR] = surface, flipped
        masks[ImgSelector.TOP_REACTOR] = masks[ImgSelector.IDLE]

        # taxi avec réacteur arrière
        surface = pygame.Surface((sheet_width / Taxi._NB_TAXI_IMAGES, sheet_height), flags=pygame.SRCALPHA)
        source_rect = surface.get_rect()
        surface.blit(sprite_sheet, (0, 0), source_rect)
        source_rect.x = 3 * source_rect.width
        surface.blit(sprite_sheet, (0, 0), source_rect)
        flipped = pygame.transform.flip(surface, True, False)
        surfaces[ImgSelector.REAR_REACTOR] = surface, flipped
        masks[ImgSelector.REAR_REACTOR] = masks[ImgSelector.IDLE]

        # taxi avec réacteurs du dessous et arrière
        surface = pygame.Surface((sheet_width / Taxi._NB_TAXI_IMAGES, sheet_height), flags=pygame.SRCALPHA)
        source_rect = surface.get_rect()
        surface.blit(sprite_sheet, (0, 0), source_rect)
        source_rect.x = source_rect.width
        surface.blit(sprite_sheet, (0, 0), source_rect)
        source_rect.x = 3 * source_rect.width
        surface.blit(sprite_sheet, (0, 0), source_rect)
        flipped = pygame.transform.flip(surface, True, False)
        surfaces[ImgSelector.BOTTOM_AND_REAR_REACTORS] = surface, flipped
        masks[ImgSelector.BOTTOM_AND_REAR_REACTORS] = masks[ImgSelector.IDLE]

        # taxi avec réacteurs du dessus et arrière
        surface = pygame.Surface((sheet_width / Taxi._NB_TAXI_IMAGES, sheet_height), flags=pygame.SRCALPHA)
        source_rect = surface.get_rect()
        surface.blit(sprite_sheet, (0, 0), source_rect)
        source_rect.x = 2 * source_rect.width
        surface.blit(sprite_sheet, (0, 0), source_rect)
        source_rect.x = 3 * source_rect.width
        surface.blit(sprite_sheet, (0, 0), source_rect)
        flipped = pygame.transform.flip(surface, True, False)
        surfaces[ImgSelector.TOP_AND_REAR_REACTORS] = surface, flipped
        masks[ImgSelector.TOP_AND_REAR_REACTORS] = masks[ImgSelector.IDLE]

        # taxi avec train d'atterrissage
        surface = pygame.Surface((sheet_width / Taxi._NB_TAXI_IMAGES, sheet_height), flags=pygame.SRCALPHA)
        source_rect = surface.get_rect()
        surface.blit(sprite_sheet, (0, 0), source_rect)
        source_rect.x = 4 * source_rect.width
        surface.blit(sprite_sheet, (0, 0), source_rect)
        flipped = pygame.transform.flip(surface, True, False)
        surfaces[ImgSelector.GEAR_OUT] = surface, flipped
        masks[ImgSelector.GEAR_OUT] = pygame.mask.from_surface(surface), pygame.mask.from_surface(flipped)

        # taxi avec train d'atterrissage comprimé
        surface = pygame.Surface((sheet_width / Taxi._NB_TAXI_IMAGES, sheet_height), flags=pygame.SRCALPHA)
        source_rect = surface.get_rect()
        source_rect.x = 5 * source_rect.width
        surface.blit(sprite_sheet, (0, 0), source_rect)
        flipped = pygame.transform.flip(surface, True, False)
        surfaces[ImgSelector.GEAR_SHOCKS] = surface, flipped
        masks[ImgSelector.GEAR_SHOCKS] = pygame.mask.from_surface(surface), pygame.mask.from_surface(flipped)

        # taxi avec réacteur du dessous et train d'atterrissage
        surface = pygame.Surface((sheet_width / Taxi._NB_TAXI_IMAGES, sheet_height), flags=pygame.SRCALPHA)
        source_rect = surface.get_rect()
        surface.blit(sprite_sheet, (0, 0), source_rect)
        source_rect.x = source_rect.width
        surface.blit(sprite_sheet, (0, 0), source_rect)
        source_rect.x = 4 * source_rect.width
        surface.blit(sprite_sheet, (0, 0), source_rect)
        flipped = pygame.transform.flip(surface, True, False)
        surfaces[ImgSelector.GEAR_OUT_AND_BOTTOM_REACTOR] = surface, flipped
        masks[ImgSelector.GEAR_OUT_AND_BOTTOM_REACTOR] = masks[ImgSelector.GEAR_OUT]

        # taxi détruit
        surface = pygame.Surface((sheet_width / Taxi._NB_TAXI_IMAGES, sheet_height), flags=pygame.SRCALPHA)
        source_rect = surface.get_rect()
        surface.blit(sprite_sheet, (0, 0), source_rect)
        surface = pygame.transform.flip(surface, False, True)
        flipped = pygame.transform.flip(surface, True, False)
        surfaces[ImgSelector.DESTROYED] = surface, flipped
        masks[ImgSelector.DESTROYED] = pygame.mask.from_surface(surface), pygame.mask.from_surface(flipped)

        return surfaces, masks
