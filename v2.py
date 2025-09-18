import sys
import math
import random
import json
import os

import pygame


# ---------- Настройки ----------
WIDTH, HEIGHT = 1000, 800
FPS = 120
TITLE = "Oracle"

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (40, 40, 40)
LIGHT_GRAY = (120, 120, 120)
GREEN = (46, 204, 113)
RED = (231, 76, 60)
YELLOW = (241, 196, 15)
BLUE = (52, 152, 219)

                                       
# ---------- Вспомогательные функции ----------
def load_font(size: int) -> pygame.font.Font:
    pygame.font.init()
    try:
        return pygame.font.SysFont("segoeui", size)
    except Exception:
        return pygame.font.Font(None, size)


def draw_text(surface: pygame.Surface, text: str, size: int, color, x: int, y: int, center=True):
    font = load_font(size)
    lines = text.split("\n")
    total_height = sum(font.size(line)[1] for line in lines)
    offset_y = -total_height // 2 if center else 0
    for i, line in enumerate(lines):
        surf = font.render(line, True, color)
        rect = surf.get_rect()
        if center:
            rect.center = (x, y + offset_y + i * (rect.height + 4))
        else:
            rect.topleft = (x, y + i * (rect.height + 4))
        surface.blit(surf, rect)


def load_player_sprite(size: tuple[int, int]) -> pygame.Surface:
    # Пытаемся загрузить спрайт игрока из assets/player.png и масштабируем под size
    # Если файла нет, рисуем запасной плейсхолдер (маленький человечек)
    path = os.path.join("assets", "player.png")
    try:
        img = pygame.image.load(path).convert_alpha()
        if img.get_size() != size:
            img = pygame.transform.smoothscale(img, size)
        return img
    except Exception:
        w, h = size
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        body_color = (70, 200, 120)
        pygame.draw.rect(surf, body_color, pygame.Rect(0, 0, w, h), border_radius=6)
        eye_r = max(2, w // 10)
        pygame.draw.circle(surf, (255, 255, 255), (w // 3, h // 3), eye_r)
        pygame.draw.circle(surf, (255, 255, 255), (2 * w // 3, h // 3), eye_r)
        pygame.draw.line(surf, (0, 0, 0), (w // 4, h * 2 // 3), (3 * w // 4, h * 2 // 3), 2)
        return surf


def load_menu_background(size: tuple[int, int]) -> pygame.Surface:
    # Загружает фон главного меню из assets/menu_bg.png, масштабирует под экран
    # Если файла нет, рисует простой градиентный фон
    path = os.path.join("assets", "menu_bg.png")
    w, h = size
    try:
        img = pygame.image.load(path).convert()
        if img.get_size() != size:
            img = pygame.transform.smoothscale(img, size)
        return img
    except Exception:
        bg = pygame.Surface((w, h))
        top = (20, 24, 36)
        bottom = (6, 6, 10)
        for y in range(h):
            t = y / max(1, h - 1)
            r = int(top[0] * (1 - t) + bottom[0] * t)
            g = int(top[1] * (1 - t) + bottom[1] * t)
            b = int(top[2] * (1 - t) + bottom[2] * t)
            pygame.draw.line(bg, (r, g, b), (0, y), (w, y))
        return bg


# ---------- Текстуры ----------
_TEXTURE_CACHE: dict[tuple[str, tuple[int, int]], pygame.Surface] = {}


def load_texture(asset_rel_path: str, size: tuple[int, int], fallback_color=(80, 80, 80), border_radius: int = 0) -> pygame.Surface:
    # Кэшируем по (путь,size)
    key = (asset_rel_path, size)
    if key in _TEXTURE_CACHE:
        return _TEXTURE_CACHE[key]
    full_path = os.path.join("assets", asset_rel_path)
    try:
        img = pygame.image.load(full_path).convert_alpha()
        if img.get_size() != size:
            img = pygame.transform.smoothscale(img, size)
        _TEXTURE_CACHE[key] = img
        return img
    except Exception:
        w, h = size
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        if border_radius > 0:
            pygame.draw.rect(surf, fallback_color, pygame.Rect(0, 0, w, h), border_radius=border_radius)
        else:
            surf.fill(fallback_color)
        _TEXTURE_CACHE[key] = surf
        return surf


def draw_textured_rect(screen: pygame.Surface, rect: pygame.Rect, asset_rel_path: str, fallback_color=(80, 80, 80), border_radius: int = 0):
    tex = load_texture(asset_rel_path, (rect.width, rect.height), fallback_color=fallback_color, border_radius=border_radius)
    screen.blit(tex, rect.topleft)


def make_scene_switch(scene_name: str, game_state: "GameState"):
    # Отложенное создание сцены по имени класса, чтобы избежать предупреждений линтера
    def factory(manager):
        cls = globals()[scene_name]
        return cls(manager, game_state)
    return factory


# ---------- Базовые сущности ----------
class Scene:
    def __init__(self, manager: "SceneManager"):
        self.manager = manager

    def handle_event(self, event: pygame.event.Event):
        pass

    def update(self, dt: float):
        pass

    def draw(self, screen: pygame.Surface):
        pass


class SceneManager:
    def __init__(self, start_scene_factory):
        self.current = start_scene_factory(self)

    def change(self, new_scene_factory):
        self.current = new_scene_factory(self)

    def handle_event(self, event):
        if self.current:
            self.current.handle_event(event)

    def update(self, dt):
        if self.current:
            self.current.update(dt)

    def draw(self, screen):
        if self.current:
            self.current.draw(screen)


class GameState:
    def __init__(self):
        self.honor = 0
        self.gold = 0
        self.helped_npc = False
        self.has_key = False
        self.beast_defeated = False
        # Новое: инвентарь и квесты
        self.has_sword = False
        self.potions = 0
        self.artifact_found = False
        self.guard_defeated = False
        self.quests = {
            "beast": "Помочь городу изгнать зверя",
            "key": "Найти способ открыть северную дверь",
            "dungeon": "Исследовать тайник у ворот",
        }
        # Расширение
        self.herbs = 0
        self.companion_joined = False
        self.last_location = "overworld"
        # Враги подземелья и зачистка
        self.defeated_enemies: list[str] = []
        self.dungeon_fully_cleared = False
        # Прокачка и артефакт/рогалик
        self.level = 1
        self.xp = 0
        self.xp_to_next = 10
        self.base_atk = 2
        self.max_hp = 10
        self.artifact_level = 0
        self.run_number = 0
        self.miniboss_defeated = False
        self.final_boss_defeated = False
        # Способности (подобие RoR2): Q/E/R — активные с перезарядкой
        self.abilities = {
            "q": {"learned": False, "cd": 0.0, "max_cd": 6.0, "name": "Рывок-удар"},
            "e": {"learned": False, "cd": 0.0, "max_cd": 8.0, "name": "Барьер"},
            "r": {"learned": False, "cd": 0.0, "max_cd": 16.0, "name": "Арканный взрыв"},
        }
        # Активности: тотем-вызов, забег на время
        self.totem_defeated = False
        self.trial_active = False
        self.trial_time_left = 0.0
        self.trial_stage = 0
        self.trial_completed = False

    def to_dict(self) -> dict:
        return {
            "honor": self.honor,
            "gold": self.gold,
            "helped_npc": self.helped_npc,
            "has_key": self.has_key,
            "beast_defeated": self.beast_defeated,
            "has_sword": self.has_sword,
            "potions": self.potions,
            "artifact_found": self.artifact_found,
            "guard_defeated": self.guard_defeated,
            "quests": self.quests,
            "herbs": self.herbs,
            "companion_joined": self.companion_joined,
            "last_location": self.last_location,
            "defeated_enemies": self.defeated_enemies,
            "dungeon_fully_cleared": self.dungeon_fully_cleared,
            "level": self.level,
            "xp": self.xp,
            "xp_to_next": self.xp_to_next,
            "base_atk": self.base_atk,
            "max_hp": self.max_hp,
            "artifact_level": self.artifact_level,
            "run_number": self.run_number,
            "miniboss_defeated": self.miniboss_defeated,
            "final_boss_defeated": self.final_boss_defeated,
            "abilities": self.abilities,
            "totem_defeated": self.totem_defeated,
            "trial_active": self.trial_active,
            "trial_time_left": self.trial_time_left,
            "trial_stage": self.trial_stage,
            "trial_completed": self.trial_completed,
        }

    @staticmethod
    def from_dict(data: dict) -> "GameState":
        gs = GameState()
        gs.honor = data.get("honor", 0)
        gs.gold = data.get("gold", 0)
        gs.helped_npc = data.get("helped_npc", False)
        gs.has_key = data.get("has_key", False)
        gs.beast_defeated = data.get("beast_defeated", False)
        gs.has_sword = data.get("has_sword", False)
        gs.potions = data.get("potions", 0)
        gs.artifact_found = data.get("artifact_found", False)
        gs.guard_defeated = data.get("guard_defeated", False)
        qs = data.get("quests") or {}
        if isinstance(qs, dict):
            gs.quests = qs
        gs.herbs = data.get("herbs", 0)
        gs.companion_joined = data.get("companion_joined", False)
        gs.last_location = data.get("last_location", "overworld")
        gs.defeated_enemies = list(data.get("defeated_enemies", []))
        gs.dungeon_fully_cleared = data.get("dungeon_fully_cleared", False)
        gs.level = data.get("level", 1)
        gs.xp = data.get("xp", 0)
        gs.xp_to_next = data.get("xp_to_next", 10)
        gs.base_atk = data.get("base_atk", 2)
        gs.max_hp = data.get("max_hp", 10)
        gs.artifact_level = data.get("artifact_level", 0)
        gs.run_number = data.get("run_number", 0)
        gs.miniboss_defeated = data.get("miniboss_defeated", False)
        gs.final_boss_defeated = data.get("final_boss_defeated", False)
        # Способности и активности
        gs.abilities = data.get("abilities", gs.abilities)
        gs.totem_defeated = data.get("totem_defeated", False)
        gs.trial_active = data.get("trial_active", False)
        gs.trial_time_left = data.get("trial_time_left", 0.0)
        gs.trial_stage = data.get("trial_stage", 0)
        gs.trial_completed = data.get("trial_completed", False)
        return gs

    # Прокачка и рогалик
    def grant_xp(self, amount: int):
        self.xp += amount
        while self.xp >= self.xp_to_next:
            self.xp -= self.xp_to_next
            self.level += 1
            self.xp_to_next = int(self.xp_to_next * 1.5)
            # Рост характеристик
            self.max_hp += 2
            self.base_atk += 1

    def start_new_run(self):
        self.run_number += 1
        # Часть прогресса переносится (уровни, артефакт), сюжет сбрасывается
        self.honor = 0
        self.gold = 0
        self.helped_npc = False
        self.has_key = False
        self.beast_defeated = False
        self.guard_defeated = False
        self.defeated_enemies = []
        self.dungeon_fully_cleared = False
        self.artifact_found = False
        self.miniboss_defeated = False
        self.final_boss_defeated = False
        self.last_location = "overworld"
        # Сброс активностей; способности остаются выученными между забегами
        self.totem_defeated = False
        self.trial_active = False
        self.trial_time_left = 0.0
        self.trial_stage = 0
        self.trial_completed = False


# ---------- Игровые сцены ----------
class TitleScene(Scene):
    def __init__(self, manager: SceneManager):
        super().__init__(manager)
        self.menu_items = ["Новая игра", "Продолжить", "Выход"]
        self.index = 0
        self.blink = 0
        self.has_save = os.path.exists("savegame.json")
        self.bg_image = load_menu_background((WIDTH, HEIGHT))

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.index = (self.index - 1) % len(self.menu_items)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.index = (self.index + 1) % len(self.menu_items)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                if self.index == 0:
                    game_state = GameState()
                    self.manager.change(lambda m: OverworldScene(m, game_state))
                elif self.index == 1:
                    if self.has_save:
                        try:
                            with open("savegame.json", "r", encoding="utf-8") as f:
                                data = json.load(f)
                            gs = GameState.from_dict(data)
                            if gs.last_location == "dungeon":
                                self.manager.change(make_scene_switch("DungeonScene", gs))
                            elif gs.last_location == "fields":
                                self.manager.change(make_scene_switch("FieldsScene", gs))
                            else:
                                self.manager.change(make_scene_switch("OverworldScene", gs))
                        except Exception:
                            self.manager.change(lambda m: OverworldScene(m, GameState()))
                else:
                    pygame.quit()
                    sys.exit(0)

    def update(self, dt):
        self.blink = (self.blink + dt) % 1.0

    def draw(self, screen):
        screen.blit(self.bg_image, (0, 0))
        draw_text(screen, TITLE, 48, YELLOW, WIDTH // 2, HEIGHT // 2 - 120, center=True)
        items = list(self.menu_items)
        if not self.has_save and "Продолжить" in items:
            items[1] = "Продолжить (нет сохранения)"
        for i, item in enumerate(items):
            color = WHITE if i != self.index else BLUE
            draw_text(screen, item, 32, color, WIDTH // 2, HEIGHT // 2 - 20 + i * 50, center=True)
        if self.blink < 0.5:
            draw_text(screen, "Стрелки — выбор, Enter — подтвердить", 20, LIGHT_GRAY, WIDTH // 2, HEIGHT - 60, center=True)
            draw_text(screen, "Совет: N — начать новый забег (рогалик)", 18, LIGHT_GRAY, WIDTH // 2, HEIGHT - 30, center=True)


class OverworldScene(Scene):
    def __init__(self, manager: SceneManager, game_state: GameState):
        super().__init__(manager)
        self.game_state = game_state
        self.game_state.last_location = "overworld"
        # Карта: прямоугольная область с простыми препятствиями
        self.walls = [
            pygame.Rect(0, 0, WIDTH, 32),
            pygame.Rect(0, HEIGHT - 32, WIDTH, 32),
            pygame.Rect(0, 0, 32, HEIGHT),
            pygame.Rect(WIDTH - 32, 0, 32, HEIGHT),
            pygame.Rect(280, 160, 400, 24),
            pygame.Rect(280, 360, 400, 24),
        ]
        self.player = pygame.Rect(100, HEIGHT // 2, 28, 28)
        self.player_sprite = load_player_sprite((self.player.width, self.player.height))
        self.speed = 260
        self.npc = pygame.Rect(WIDTH - 200, HEIGHT // 2 - 20, 32, 32)
        self.door = pygame.Rect(WIDTH - 80, 72, 40, 64)
        self.shop = pygame.Rect(80, 100, 36, 36)
        self.thief = pygame.Rect(120, HEIGHT - 140, 30, 30)
        self.fields_gate = pygame.Rect(60, HEIGHT // 2 - 18, 36, 36)
        # Новые активности
        self.altar = pygame.Rect(220, 120, 36, 36)
        self.totem = pygame.Rect(WIDTH // 2 - 18, HEIGHT // 2 + 80, 36, 36)
        self.shrine = pygame.Rect(WIDTH - 220, HEIGHT - 140, 36, 36)
        self.message_timer = 0.0
        self.message = ""
        self.show_minimap = False

    def collide(self, rect: pygame.Rect) -> bool:
        for wall in self.walls:
            if rect.colliderect(wall):
                return True
        return False

    def try_move(self, dx: float, dy: float, dt: float):
        step_x = pygame.Rect(self.player)
        step_x.x += int(dx * self.speed * dt)
        if not self.collide(step_x):
            self.player = step_x
        step_y = pygame.Rect(self.player)
        step_y.y += int(dy * self.speed * dt)
        if not self.collide(step_y):
            self.player = step_y

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_e:
            if self.player.colliderect(self.npc.inflate(40, 40)):
                self.talk_to_npc()
            elif self.player.colliderect(self.shop.inflate(40, 40)):
                self.enter_shop()
            elif self.player.colliderect(self.thief.inflate(40, 40)):
                self.meet_thief()
            elif self.player.colliderect(self.altar.inflate(28, 28)):
                self.use_altar()
            elif self.player.colliderect(self.totem.inflate(28, 28)):
                self.challenge_totem()
            elif self.player.colliderect(self.shrine.inflate(28, 28)):
                self.use_shrine()
            elif self.player.colliderect(self.fields_gate.inflate(20, 20)):
                self.manager.change(make_scene_switch("FieldsScene", self.game_state))
            elif self.player.colliderect(self.door.inflate(20, 20)):
                self.enter_dungeon()
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_q:
            self.open_quest_log()
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_m:
            self.show_minimap = not self.show_minimap
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_n:
            # Начать новый забег (рогалик) — быстрый рестарт с переносом прогресса
            self.game_state.start_new_run()
            self.message = "Начат новый забег! Сложность возросла."
            self.message_timer = 2.5
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_F5:
            try:
                with open("savegame.json", "w", encoding="utf-8") as f:
                    json.dump(self.game_state.to_dict(), f, ensure_ascii=False, indent=2)
                self.message = "Игра сохранена (F5)."
                self.message_timer = 2.0
            except Exception:
                self.message = "Не удалось сохранить."
                self.message_timer = 2.0
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_F9:
            try:
                with open("savegame.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                gs = GameState.from_dict(data)
                self.manager.change(make_scene_switch("OverworldScene", gs))
            except Exception:
                self.message = "Загрузка не удалась."
                self.message_timer = 2.0

    def talk_to_npc(self):
        def on_choice(choice_id: int):
            if choice_id == 0:
                self.game_state.honor += 1
                self.game_state.helped_npc = True
                self.message = "Вы пообещали помочь. Честь +1"
                self.message_timer = 2.0
            elif choice_id == 1:
                self.game_state.gold += 5
                self.message = "Вы потребовали плату. Золото +5"
                self.message_timer = 2.0
            else:
                self.message = "Вы отказались. Кто-то другой поможет..."
                self.message_timer = 2.0

        text = (
            "Путник: Говорят, древний артефакт хранит подземелье у ворот.\n"
            "Но прежде — зверь у северных ворот и стражи внизу. Без этого дверь не откроется.\n"
            "Поможешь городу?"
        )
        choices = [
            ("Помочь бескорыстно", 0),
            ("Помочь за 5 золота", 1),
            ("Отказать", 2),
        ]
        self.manager.change(lambda m: DialogueScene(m, text, choices, on_choice, self))

    def enter_dungeon(self):
        def after_key(choice_id: int):
            if choice_id == 0:
                self.game_state.has_key = True
                self.message = "Вы нашли ключ под ковриком у двери."
                self.message_timer = 2.0

        if not self.game_state.beast_defeated:
            # Перед боем — короткая сцена проверки навыка/удачи
            self.manager.change(lambda m: SkillCheckScene(m, self.game_state, self))
        else:
            # После победы можно открыть тайник, если есть ключ
            if not self.game_state.has_key:
                text = "Дверь заперта. Осмотреться у порога?"
                choices = [("Да, поискать ключ", 0), ("Нет", 1)]
                self.manager.change(lambda m: DialogueScene(m, text, choices, after_key, self))
            else:
                # Внутри двери теперь подземелье
                self.manager.change(lambda m: DungeonScene(m, self.game_state))

    def enter_shop(self):
        def on_choice(choice_id: int):
            if choice_id == 0 and self.game_state.gold >= 5:
                self.game_state.gold -= 5
                self.game_state.potions += 1
                self.message = "Куплено: зелье (+1)."
                self.message_timer = 2.0
            elif choice_id == 1 and self.game_state.gold >= 8 and not self.game_state.has_sword:
                self.game_state.gold -= 8
                self.game_state.has_sword = True
                self.message = "Куплен меч (урон +2)."
                self.message_timer = 2.0
            elif choice_id == 2:
                self.message = "Может, в другой раз..."
                self.message_timer = 1.5
            else:
                self.message = "Недостаточно золота."
                self.message_timer = 1.5

        text = "Лавочник: Лучший товар в городе! Что берёте?"
        items = [
            ("Купить зелье (5 золота)", 0),
            ("Купить меч (8 золота)", 1),
            ("Ничего", 2),
        ]
        self.manager.change(lambda m: DialogueScene(m, text, items, on_choice, self))

    def meet_thief(self):
        def on_choice(choice_id: int):
            if choice_id == 0:
                # Взять ключ у вора за честь
                if not self.game_state.has_key:
                    self.game_state.has_key = True
                    self.game_state.honor = max(0, self.game_state.honor - 1)
                    self.message = "Вы приняли сомнительный ключ. Честь -1."
                    self.message_timer = 2.0
                else:
                    self.message = "У вас уже есть ключ."
                    self.message_timer = 1.5
            elif choice_id == 1:
                # Попытка карманной кражи
                success = random.random() < 0.5
                if success:
                    self.game_state.gold += 4
                    self.game_state.honor = max(0, self.game_state.honor - 1)
                    self.message = "Вы стащили немного золота. Честь -1."
                else:
                    self.message = "Провал! Вас заметили, пришлось сбежать."
                self.message_timer = 2.0
            else:
                self.message = "Вы отвергли предложение вора."
                self.message_timer = 1.5

        text = (
            "Вор: Ключ от северной двери, говоришь?\n"
            "Могу достать 'альтернативный' ключ... или подзаработать вместе."
        )
        choices = [("Взять ключ (Честь -1)", 0), ("Обокрасть прохожего", 1), ("Уйти", 2)]
        self.manager.change(lambda m: DialogueScene(m, text, choices, on_choice, self))

    def open_quest_log(self):
        self.manager.change(lambda m: QuestLogScene(m, self.game_state, self))

    def update(self, dt):
        keys = pygame.key.get_pressed()
        dx = dy = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dx -= 1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx += 1
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            dy -= 1
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            dy += 1
        if dx != 0 and dy != 0:
            inv = 1 / math.sqrt(2)
            dx *= inv
            dy *= inv
        self.try_move(dx, dy, dt)

        if self.message_timer > 0:
            self.message_timer -= dt
            if self.message_timer <= 0:
                self.message = ""

    def draw(self, screen):
        screen.fill((18, 22, 28))
        # Пол (плитка)
        tile_size = 32
        for x in range(0, WIDTH, tile_size):
            for y in range(0, HEIGHT, tile_size):
                rect = pygame.Rect(x, y, tile_size, tile_size)
                draw_textured_rect(screen, rect, "tiles/overworld_floor.png", fallback_color=(24, 28, 34))
        # Стены
        for wall in self.walls:
            draw_textured_rect(screen, wall, "tiles/overworld_wall.png", fallback_color=GRAY)
        # Дверь
        draw_textured_rect(screen, self.door, "objects/door.png", fallback_color=YELLOW, border_radius=4)
        draw_text(screen, "Северные ворота", 18, YELLOW, self.door.centerx, self.door.top - 20, center=True)
        # Выход на поля
        pygame.draw.rect(screen, (80, 160, 80), self.fields_gate)
        draw_text(screen, "На поля", 18, WHITE, self.fields_gate.centerx, self.fields_gate.top - 16, center=True)
        # NPC
        draw_textured_rect(screen, self.npc, "characters/npc.png", fallback_color=BLUE, border_radius=4)
        draw_text(screen, "Путник", 18, WHITE, self.npc.centerx, self.npc.top - 16, center=True)
        # Лавочник
        draw_textured_rect(screen, self.shop, "objects/shop.png", fallback_color=(200, 120, 40), border_radius=4)
        draw_text(screen, "Лавка", 18, WHITE, self.shop.centerx, self.shop.top - 16, center=True)
        # Вор
        draw_textured_rect(screen, self.thief, "characters/thief.png", fallback_color=(120, 120, 120), border_radius=4)
        # Новые активности
        draw_textured_rect(screen, self.altar, "objects/altar.png", fallback_color=(160, 120, 200), border_radius=6)
        draw_textured_rect(screen, self.totem, "objects/totem.png", fallback_color=(180, 90, 50), border_radius=6)
        draw_textured_rect(screen, self.shrine, "objects/shrine.png", fallback_color=(120, 200, 200), border_radius=6)
        draw_text(screen, "Алтарь", 16, WHITE, self.altar.centerx, self.altar.top - 14, center=True)
        draw_text(screen, "Тотем", 16, WHITE, self.totem.centerx, self.totem.top - 14, center=True)
        draw_text(screen, "Святыня", 16, WHITE, self.shrine.centerx, self.shrine.top - 14, center=True)
        draw_text(screen, "Вор", 18, WHITE, self.thief.centerx, self.thief.top - 16, center=True)
        # Игрок (спрайт)
        screen.blit(self.player_sprite, self.player.topleft)

        # HUD
        hud = (
            f"Честь: {self.game_state.honor}   Золото: {self.game_state.gold}   "
            f"Ключ: {'есть' if self.game_state.has_key else 'нет'}   "
            f"Зелья: {self.game_state.potions}   Меч: {'да' if self.game_state.has_sword else 'нет'}   "
            f"Травы: {self.game_state.herbs}   Ур: {self.game_state.level} ({self.game_state.xp}/{self.game_state.xp_to_next})   "
            f"HP: {self.game_state.max_hp}   ATK: {self.game_state.base_atk}   Артефакт: {self.game_state.artifact_level}   Забег: {self.game_state.run_number}"
        )
        draw_text(screen, hud, 20, WHITE, 16, 12, center=False)

        if self.player.colliderect(self.npc.inflate(40, 40)):
            draw_text(screen, "Нажмите E, чтобы поговорить", 18, LIGHT_GRAY, WIDTH // 2, HEIGHT - 60, center=True)
        elif self.player.colliderect(self.shop.inflate(40, 40)):
            draw_text(screen, "Нажмите E, чтобы открыть лавку", 18, LIGHT_GRAY, WIDTH // 2, HEIGHT - 60, center=True)
        elif self.player.colliderect(self.thief.inflate(40, 40)):
            draw_text(screen, "Нажмите E, чтобы поговорить с вором", 18, LIGHT_GRAY, WIDTH // 2, HEIGHT - 60, center=True)
        elif self.player.colliderect(self.altar.inflate(28, 28)):
            draw_text(screen, "Нажмите E, чтобы использовать алтарь (выучить способность)", 18, LIGHT_GRAY, WIDTH // 2, HEIGHT - 60, center=True)
        elif self.player.colliderect(self.totem.inflate(28, 28)) and not self.game_state.totem_defeated:
            draw_text(screen, "Нажмите E, чтобы начать испытание тотема", 18, LIGHT_GRAY, WIDTH // 2, HEIGHT - 60, center=True)
        elif self.player.colliderect(self.shrine.inflate(28, 28)):
            draw_text(screen, "Нажмите E, чтобы помолиться у святыни", 18, LIGHT_GRAY, WIDTH // 2, HEIGHT - 60, center=True)
        elif self.player.colliderect(self.door.inflate(20, 20)):
            draw_text(screen, "Нажмите E, чтобы войти", 18, LIGHT_GRAY, WIDTH // 2, HEIGHT - 60, center=True)
        elif self.player.colliderect(self.fields_gate.inflate(20, 20)):
            draw_text(screen, "Нажмите E, чтобы выйти на поля", 18, LIGHT_GRAY, WIDTH // 2, HEIGHT - 60, center=True)

        if self.message:
            draw_text(screen, self.message, 20, YELLOW, WIDTH // 2, 40, center=True)
        draw_text(screen, "Q — квест-лог   M — мини-карта   N — новый забег   F5/F9 — сохранение/загрузка", 16, LIGHT_GRAY, WIDTH - 520, 16, center=False)

        if self.show_minimap:
            self.draw_minimap(screen)

    def use_altar(self):
        options: list[tuple[str, int]] = []
        order = [
            ("q", "Выучить Q — Рывок-удар"),
            ("e", "Выучить E — Барьер"),
            ("r", "Выучить R — Арканный взрыв"),
        ]
        for key, label in order:
            if not self.game_state.abilities[key]["learned"]:
                options.append((label, 100 + ord(key)))
        if not options:
            self.message = "Вы уже постигли все способности."
            self.message_timer = 2.0
            return

        def on_choice(choice_id: int):
            key = chr(choice_id - 100)
            if key in self.game_state.abilities and not self.game_state.abilities[key]["learned"]:
                self.game_state.abilities[key]["learned"] = True
                self.message = f"Вы обучились способности {self.game_state.abilities[key]['name']}!"
                self.message_timer = 2.0

        text = "Алтарь знаний: выберите способность для обучения"
        self.manager.change(lambda m: DialogueScene(m, text, options + [("Отмена", 0)], on_choice, self))

    def challenge_totem(self):
        if self.game_state.totem_defeated:
            self.message = "Тотем умолк. Испытание уже пройдено."
            self.message_timer = 2.0
            return

        def on_win(gs: GameState):
            gs.totem_defeated = True
            gs.gold += 10
            gs.grant_xp(6)
        self.manager.change(lambda m: CombatScene(m, self.game_state, self, enemy_name="Испытание тотема", enemy_hp=16, enemy_atk=4, enemy_id="totem_challenge", on_win=on_win, xp_reward=0))

    def use_shrine(self):
        # Простая логика: если мало зелий — выдать, иначе подлечить
        if self.game_state.potions < 2:
            self.game_state.potions += 1
            self.message = "Святыня благословила вас зельем."
        else:
            heal = min(self.game_state.max_hp, self.game_state.max_hp)  # привлекательный текст; фактического HP нет вне боя
            self.message = "Святыня укрепила дух и тело."
        self.message_timer = 2.0

    def draw_minimap(self, screen: pygame.Surface):
        mw, mh = 180, 100
        mx, my = WIDTH - mw - 16, 30
        pygame.draw.rect(screen, (0, 0, 0), (mx - 4, my - 4, mw + 8, mh + 8))
        pygame.draw.rect(screen, (30, 30, 30), (mx, my, mw, mh))
        scale_x = mw / WIDTH
        scale_y = mh / HEIGHT
        for wall in self.walls:
            r = pygame.Rect(mx + int(wall.left * scale_x), my + int(wall.top * scale_y), int(wall.width * scale_x), int(wall.height * scale_y))
            pygame.draw.rect(screen, (70, 70, 90), r)
        for obj, color in [
            (self.npc, (50, 120, 255)),
            (self.shop, (220, 150, 60)),
            (self.thief, (140, 140, 140)),
            (self.door, (220, 220, 60)),
            (self.fields_gate, (80, 200, 120)),
        ]:
            r = pygame.Rect(mx + int(obj.centerx * scale_x) - 2, my + int(obj.centery * scale_y) - 2, 4, 4)
            pygame.draw.rect(screen, color, r)
        pr = pygame.Rect(mx + int(self.player.centerx * scale_x) - 2, my + int(self.player.centery * scale_y) - 2, 4, 4)
        pygame.draw.rect(screen, (80, 220, 80), pr)


class DialogueScene(Scene):
    def __init__(self, manager: SceneManager, text: str, choices: list[tuple[str, int]], on_choice, return_scene: Scene):
        super().__init__(manager)
        self.text = text
        self.choices = choices
        self.on_choice = on_choice
        self.index = 0
        self.return_scene = return_scene

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.index = (self.index - 1) % len(self.choices)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.index = (self.index + 1) % len(self.choices)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                choice_id = self.choices[self.index][1]
                if self.on_choice:
                    self.on_choice(choice_id)
                # Вернуться в указанную сцену (обычно — мир)
                self.manager.current = self.return_scene
            elif event.key in (pygame.K_ESCAPE,):
                self.manager.current = self.return_scene

    def update(self, dt):
        pass

    def draw(self, screen):
        screen.fill((10, 10, 14))
        # Текст
        draw_text(screen, self.text, 24, WHITE, WIDTH // 2, HEIGHT // 2 - 100, center=True)
        # Выбор
        for i, (label, _) in enumerate(self.choices):
            color = BLUE if i == self.index else LIGHT_GRAY
            draw_text(screen, label, 28, color, WIDTH // 2, HEIGHT // 2 - 10 + i * 40, center=True)
        draw_text(screen, "Enter — выбрать, Esc — назад", 18, LIGHT_GRAY, WIDTH // 2, HEIGHT - 40, center=True)


class QuestLogScene(Scene):
    def __init__(self, manager: SceneManager, game_state: GameState, return_scene: Scene):
        super().__init__(manager)
        self.game_state = game_state
        self.return_scene = return_scene

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            self.manager.current = self.return_scene

    def update(self, dt):
        pass

    def draw(self, screen):
        screen.fill((14, 14, 18))
        draw_text(screen, "Квесты и подсказки", 36, YELLOW, WIDTH // 2, 48, center=True)

        # Краткий сюжет
        lore = (
            "Город страдает от зверя и стражей в подземелье у северных ворот.\n"
            "Изгони зверя, найди ключ, зачисти подземелье, возьми артефакт.\n"
            "После артефакта появится лейтенант Теней, а дальше — путь к финалу."
        )
        draw_text(screen, lore, 20, LIGHT_GRAY, WIDTH // 2, 120, center=True)

        # Состояние ключевых флагов
        y = 200
        font_size = 22
        flags = [
            ("Зверь изгнан", self.game_state.beast_defeated),
            ("Есть ключ", self.game_state.has_key),
            ("Меч куплен", self.game_state.has_sword),
            ("Артефакт найден", self.game_state.artifact_found),
            ("Спутник присоединился", self.game_state.companion_joined),
            ("Подземелье зачищено", self.game_state.dungeon_fully_cleared),
            ("Мини-босс побеждён", getattr(self.game_state, "miniboss_defeated", False)),
            ("Финальный босс побеждён", getattr(self.game_state, "final_boss_defeated", False)),
            ("Испытание тотема", getattr(self.game_state, "totem_defeated", False)),
            ("Забег на время выполнен", getattr(self.game_state, "trial_completed", False)),
        ]
        for title, done in flags:
            color = GREEN if done else LIGHT_GRAY
            draw_text(screen, ("[✓] " if done else "[ ] ") + title, font_size, color, WIDTH // 2, y, center=True)
            y += 28

        # Динамические подсказки
        tips: list[str] = []
        if not self.game_state.beast_defeated:
            tips.append("Подойдите к северным воротам и пройдите скилл-чек (SPACE) против зверя.")
        if self.game_state.beast_defeated and not self.game_state.has_key:
            tips.append("Около двери осмотритесь и найдите ключ (E), либо поговорите с вором.")
        if self.game_state.has_key and not self.game_state.dungeon_fully_cleared:
            tips.append("Войдите в подземелье. Победите Стража и двух Часовых (E у них).")
        if self.game_state.dungeon_fully_cleared and not self.game_state.artifact_found:
            tips.append("Откройте сундук в подземелье, чтобы взять артефакт (E у сундука).")
        if self.game_state.artifact_found and not getattr(self.game_state, "miniboss_defeated", False):
            tips.append("После взятия артефакта найдите у выхода мини-босса Лейтенанта и победите его.")
        if getattr(self.game_state, "miniboss_defeated", False) and not getattr(self.game_state, "final_boss_defeated", False):
            tips.append("Усилите героя: купите меч, соберите травы у Травника для зелий/спутника, повышайте уровень в боях.")
        if not getattr(self.game_state, "totem_defeated", False):
            tips.append("В городе найдите Тотем испытаний и победите его для награды.")
        if not getattr(self.game_state, "trial_completed", False):
            tips.append("На полях попробуйте забег на время. Начало — у первой контрольной точки.")
        if self.game_state.companion_joined is False:
            tips.append("На полях соберите 3 травы и попросите Травника присоединиться (E).")
        if self.game_state.artifact_found and self.game_state.honor < 2:
            tips.append("Поднимите честь (помогите путнику бескорыстно), это влияет на лучшие концовки.")
        if len(tips) == 0:
            tips.append("Исследуйте мир, начните новый забег (N) для увеличения сложности и прогресса.")

        draw_text(screen, "Подсказки", 24, YELLOW, WIDTH // 2, y + 16, center=True)
        y += 56
        for tip in tips[:8]:
            draw_text(screen, "• " + tip, 20, WHITE, WIDTH // 2, y, center=True)
            y += 26

        draw_text(screen, "Нажмите любую клавишу, чтобы вернуться", 18, LIGHT_GRAY, WIDTH // 2, HEIGHT - 36, center=True)


class SkillCheckScene(Scene):
    def __init__(self, manager: SceneManager, game_state: GameState, return_scene: Scene):
        super().__init__(manager)
        self.game_state = game_state
        self.return_scene = return_scene
        self.slider_x = 0.0
        self.slider_speed = 0.9  # нормализовано [0..1] за секунду
        # Усложнение/упрощение от чести: выше честь — шире зона успеха
        base = 0.20
        bonus = min(0.25, self.game_state.honor * 0.08)
        self.success_center = 0.5
        self.success_width = base + bonus  # +- width/2 вокруг центра
        self.resolved = False
        self.result_text = ""
        self.timer = 0.0

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and not self.resolved:
            if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                diff = abs(self.slider_x - self.success_center)
                if diff <= self.success_width / 2:
                    self.game_state.beast_defeated = True
                    self.result_text = "Вы изгнали зверя! Город спасён."
                else:
                    self.result_text = "Провал. Зверь отступил во тьму... Попробуйте снова."
                self.resolved = True
                self.timer = 1.5
        elif event.type == pygame.KEYDOWN and self.resolved:
            # После результата — назад в мир или к концовке
            if self.game_state.beast_defeated:
                self.manager.change(lambda m: self.return_scene.__class__(m, self.return_scene.game_state))
            else:
                self.manager.current = self.return_scene

    def update(self, dt):
        if not self.resolved:
            self.slider_x += self.slider_speed * dt
            # пинг-понг
            if self.slider_x > 1.0:
                self.slider_x = 1.0
                self.slider_speed *= -1
            elif self.slider_x < 0.0:
                self.slider_x = 0.0
                self.slider_speed *= -1
        else:
            if self.timer > 0:
                self.timer -= dt

    def draw(self, screen):
        screen.fill((16, 12, 18))
        draw_text(screen, "Изгнание зверя", 36, YELLOW, WIDTH // 2, 60, center=True)
        # Полоса
        bar_rect = pygame.Rect(120, HEIGHT // 2 - 12, WIDTH - 240, 24)
        pygame.draw.rect(screen, LIGHT_GRAY, bar_rect, 2)
        # Зона успеха
        zone_w = int(bar_rect.width * self.success_width)
        zone_x = int(bar_rect.left + bar_rect.width * (self.success_center - self.success_width / 2))
        pygame.draw.rect(screen, (60, 120, 60), (zone_x, bar_rect.top + 2, zone_w, bar_rect.height - 4))
        # Бегунок
        knob_x = int(bar_rect.left + bar_rect.width * self.slider_x)
        pygame.draw.circle(screen, BLUE, (knob_x, bar_rect.centery), 10)

        if not self.resolved:
            draw_text(screen, "Нажмите ПРОБЕЛ в зелёной зоне", 22, WHITE, WIDTH // 2, HEIGHT // 2 + 80, center=True)
        else:
            color = GREEN if self.game_state.beast_defeated else RED
            draw_text(screen, self.result_text, 24, color, WIDTH // 2, HEIGHT // 2 + 80, center=True)
            draw_text(screen, "Нажмите любую клавишу, чтобы продолжить", 20, LIGHT_GRAY, WIDTH // 2, HEIGHT - 40, center=True)


class EndingScene(Scene):
    def __init__(self, manager: SceneManager, game_state: GameState):
        super().__init__(manager)
        self.game_state = game_state
        self.index = 0
        self.text, self.color = self.compute_ending()

    def compute_ending(self):
        if not self.game_state.beast_defeated:
            return ("Зверь остался бродить по окраинам...\nГорожане в страхе.", RED)
        if self.game_state.artifact_found and self.game_state.honor >= 2 and self.game_state.companion_joined and self.game_state.dungeon_fully_cleared:
            return ("С артефактом, доброй славой и поддержкой спутника\n"
                    "город расцвёл. Вы — наставник и защитник.", YELLOW)
        if self.game_state.artifact_found and self.game_state.honor >= 2 and self.game_state.dungeon_fully_cleared:
            return ("С артефактом и доброй славой вы возродили город.\n"
                    "Имя ваше войдёт в летописи.", YELLOW)
        if self.game_state.final_boss_defeated and self.game_state.run_number >= 1:
            return ("Вы сокрушили Владыку Теней, завершив забег №" + str(self.game_state.run_number) + ".\n"
                    "Город свободен, но новые угрозы ждут в следующих забегах...", YELLOW)
        if self.game_state.artifact_found and not self.game_state.dungeon_fully_cleared:
            return ("Вы нашли артефакт, не победив всех стражей...\n"
                    "Сила его нестабильна, и город в опасности.", RED)
        if self.game_state.honor >= 1 and self.game_state.gold >= 5 and self.game_state.has_sword:
            return ("Вы помогли путнику и получили плату.\n"
                    "Город спасён, а меч стал символом защиты.", GREEN)
        if self.game_state.has_key and self.game_state.artifact_found:
            return ("Вы нашли артефакт, но ваши поступки двусмысленны...\n"
                    "Горожане сомневаются, кому он служит.", BLUE)
        return ("Вы изгнали зверя, но прошли мимо возможностей...\n"
                "Иногда выбор важнее битвы.", LIGHT_GRAY)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                # Перезапуск
                self.manager.change(lambda m: TitleScene(m))

    def update(self, dt):
        pass

    def draw(self, screen):
        screen.fill((12, 10, 10))
        draw_text(screen, "Концовка", 40, self.color, WIDTH // 2, 100, center=True)
        draw_text(screen, self.text, 28, WHITE, WIDTH // 2, HEIGHT // 2, center=True)
        draw_text(screen, "Enter — вернуться в меню", 20, LIGHT_GRAY, WIDTH // 2, HEIGHT - 40, center=True)
        if self.game_state.companion_joined:
            draw_text(screen, "Спутник остаётся рядом, пока город нуждается в нём.", 18, LIGHT_GRAY, WIDTH // 2, HEIGHT - 80, center=True)


class CombatScene(Scene):
    def __init__(self, manager: SceneManager, game_state: GameState, return_scene: Scene, enemy_name: str = "Страж", enemy_hp: int = 8, enemy_atk: int = 2, enemy_id: str | None = None, on_win=None, xp_reward: int = 4):
        super().__init__(manager)
        self.game_state = game_state
        self.return_scene = return_scene
        self.enemy_name = enemy_name
        self.player_hp = self.game_state.max_hp
        # Базовый урон растёт с уровнем и мечом
        self.player_atk = self.game_state.base_atk + (2 if self.game_state.has_sword else 0)
        self.enemy_hp = enemy_hp
        # Скалирование врагов от номера забега и уровня
        scale = 1.0 + self.game_state.run_number * 0.2 + max(0, self.game_state.level - 1) * 0.05
        self.enemy_hp = int(self.enemy_hp * scale)
        self.enemy_atk = int(enemy_atk * scale)
        self.turn = "player"
        self.log: list[str] = ["Бой начался!"]
        self.spell_cooldown = 0.0
        self.enemy_id = enemy_id
        self.on_win = on_win
        self.xp_reward = int(xp_reward * (1.0 + self.game_state.run_number * 0.3))
        # Щит от способности E (поглощает часть урона следующей атаки)
        self.temp_shield = 0

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and self.turn == "player" and self.player_hp > 0 and self.enemy_hp > 0:
            if event.key in (pygame.K_1, pygame.K_RETURN, pygame.K_SPACE):
                dmg = random.randint(self.player_atk - 1, self.player_atk + 1)
                dmg = max(1, dmg)
                self.enemy_hp -= dmg
                self.log.append(f"Вы ударили: -{dmg} HP")
                self.turn = "enemy"
            elif event.key == pygame.K_2 and self.game_state.potions > 0:
                self.game_state.potions -= 1
                heal = random.randint(3, 6)
                self.player_hp = min(12, self.player_hp + heal)
                self.log.append(f"Вы выпили зелье: +{heal} HP")
                self.turn = "enemy"
            elif event.key == pygame.K_f and self.spell_cooldown <= 0.0:
                dmg = 3 + (1 if self.game_state.artifact_found else 0)
                self.enemy_hp -= dmg
                self.log.append(f"Огненное заклинание: -{dmg} HP")
                self.spell_cooldown = 3.0
                self.turn = "enemy"
            # Способности Q/E/R
            elif event.key == pygame.K_q and self.game_state.abilities["q"]["learned"] and self.game_state.abilities["q"]["cd"] <= 0.0:
                # Рывок-удар: мощный удар 150% урона
                base = random.randint(self.player_atk - 1, self.player_atk + 1)
                dmg = max(2, int(base * 1.5))
                self.enemy_hp -= dmg
                self.game_state.abilities["q"]["cd"] = self.game_state.abilities["q"]["max_cd"]
                self.log.append(f"Q — Рывок-удар: -{dmg} HP")
                self.turn = "enemy"
            elif event.key == pygame.K_e and self.game_state.abilities["e"]["learned"] and self.game_state.abilities["e"]["cd"] <= 0.0:
                # Барьер: щит на следующий входящий удар (-50% урона)
                self.temp_shield = 50  # проценты
                self.game_state.abilities["e"]["cd"] = self.game_state.abilities["e"]["max_cd"]
                self.log.append("E — Барьер активирован: следующий удар по вам слабее")
                self.turn = "enemy"
            elif event.key == pygame.K_r and self.game_state.abilities["r"]["learned"] and self.game_state.abilities["r"]["cd"] <= 0.0:
                # Арканный взрыв: большой урон, зависит от артефакта
                bonus = 2 * (1 if self.game_state.artifact_found else 0)
                dmg = 5 + bonus
                self.enemy_hp -= dmg
                self.game_state.abilities["r"]["cd"] = self.game_state.abilities["r"]["max_cd"]
                self.log.append(f"R — Арканный взрыв: -{dmg} HP")
                self.turn = "enemy"
        elif event.type == pygame.KEYDOWN and (self.player_hp <= 0 or self.enemy_hp <= 0):
            # Завершить бой
            self.manager.current = self.return_scene
            if self.enemy_hp <= 0:
                if self.enemy_id and self.enemy_id not in self.game_state.defeated_enemies:
                    self.game_state.defeated_enemies.append(self.enemy_id)
                # Обратная совместимость: отметим стража
                if self.enemy_name == "Страж":
                    self.game_state.guard_defeated = True
                # Выдать опыт, повысить уровень/характеристики
                self.game_state.grant_xp(self.xp_reward)
                if callable(self.on_win):
                    try:
                        self.on_win(self.game_state)
                    except Exception:
                        pass

    def update(self, dt):
        if self.spell_cooldown > 0.0:
            self.spell_cooldown = max(0.0, self.spell_cooldown - dt)
        # Кулдауны способностей
        for k in ("q", "e", "r"):
            if self.game_state.abilities.get(k, {}).get("cd", 0.0) > 0.0:
                self.game_state.abilities[k]["cd"] = max(0.0, self.game_state.abilities[k]["cd"] - dt)
        if self.turn == "enemy" and self.player_hp > 0 and self.enemy_hp > 0:
            if self.game_state.companion_joined and self.enemy_hp > 0:
                cdmg = random.randint(1, 2)
                self.enemy_hp -= cdmg
                self.log.append(f"Спутник атакует: -{cdmg} HP")
                if self.enemy_hp <= 0:
                    return
            dmg = random.randint(self.enemy_atk - 1, self.enemy_atk + 1)
            dmg = max(1, dmg)
            if self.temp_shield > 0:
                reduced = int(dmg * (1 - self.temp_shield / 100))
                reduced = max(0, reduced)
                self.log.append(f"Барьер поглотил часть урона ({dmg}->{reduced})")
                dmg = reduced
                self.temp_shield = 0
            self.player_hp -= dmg
            self.log.append(f"{self.enemy_name} ударил: -{dmg} HP")
            self.turn = "player"

    def draw(self, screen):
        screen.fill((20, 16, 18))
        draw_text(screen, f"Бой: {self.enemy_name}", 34, YELLOW, WIDTH // 2, 60, center=True)
        draw_text(screen, f"Ваше HP: {self.player_hp}", 26, GREEN, WIDTH // 2 - 200, 140, center=True)
        draw_text(screen, f"HP врага: {self.enemy_hp}", 26, RED, WIDTH // 2 + 200, 140, center=True)
        y = 220
        for line in self.log[-6:]:
            draw_text(screen, line, 22, WHITE, WIDTH // 2, y, center=True)
            y += 28
        if self.player_hp > 0 and self.enemy_hp > 0 and self.turn == "player":
            spell_txt = "F — Заклинание" + (f" ({self.spell_cooldown:.1f}s)" if self.spell_cooldown > 0 else "")
            q_cd = self.game_state.abilities["q"]["cd"]
            e_cd = self.game_state.abilities["e"]["cd"]
            r_cd = self.game_state.abilities["r"]["cd"]
            q_txt = "Q — Рывок" + (f" ({q_cd:.1f}s)" if q_cd > 0 else "") if self.game_state.abilities["q"]["learned"] else "Q — ???"
            e_txt = "E — Барьер" + (f" ({e_cd:.1f}s)" if e_cd > 0 else "") if self.game_state.abilities["e"]["learned"] else "E — ???"
            r_txt = "R — Взрыв" + (f" ({r_cd:.1f}s)" if r_cd > 0 else "") if self.game_state.abilities["r"]["learned"] else "R — ???"
            draw_text(screen, f"1 — Атака   2 — Зелье   {spell_txt}   {q_txt}   {e_txt}   {r_txt}", 20, LIGHT_GRAY, WIDTH // 2, HEIGHT - 80, center=True)
        else:
            text = "Победа! Нажмите любую клавишу" if self.enemy_hp <= 0 else "Поражение... Нажмите любую клавишу"
            draw_text(screen, text, 22, LIGHT_GRAY, WIDTH // 2, HEIGHT - 80, center=True)


class DungeonScene(Scene):
    def __init__(self, manager: SceneManager, game_state: GameState):
        super().__init__(manager)
        self.game_state = game_state
        self.game_state.last_location = "dungeon"
        self.player = pygame.Rect(80, HEIGHT - 100, 28, 28)
        self.player_sprite = load_player_sprite((self.player.width, self.player.height))
        self.speed = 240
        self.walls = [
            pygame.Rect(0, 0, WIDTH, 24),
            pygame.Rect(0, HEIGHT - 24, WIDTH, 24),
            pygame.Rect(0, 0, 24, HEIGHT),
            pygame.Rect(WIDTH - 24, 0, 24, HEIGHT),
            pygame.Rect(220, 180, WIDTH - 440, 20),
        ]
        # Несколько врагов в залах
        self.guard = pygame.Rect(WIDTH // 2 - 16, 120, 32, 32)
        self.sentry_left = pygame.Rect(180, 260, 28, 28)
        self.sentry_right = pygame.Rect(WIDTH - 220, 260, 28, 28)
        self.chest = pygame.Rect(WIDTH - 140, 80, 28, 28)
        self.exit_rect = pygame.Rect(40, HEIGHT - 60, 40, 40)
        self.message = ""
        self.message_timer = 0.0
        self.show_minimap = False

    def collide(self, rect: pygame.Rect) -> bool:
        for wall in self.walls:
            if rect.colliderect(wall):
                return True
        return False

    def try_move(self, dx: float, dy: float, dt: float):
        step_x = pygame.Rect(self.player)
        step_x.x += int(dx * self.speed * dt)
        if not self.collide(step_x):
            self.player = step_x
        step_y = pygame.Rect(self.player)
        step_y.y += int(dy * self.speed * dt)
        if not self.collide(step_y):
            self.player = step_y

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_e:
            if self.player.colliderect(self.guard.inflate(30, 30)) and not self.game_state.guard_defeated:
                # Начать бой со стражем
                self.manager.change(lambda m: CombatScene(m, self.game_state, self, enemy_name="Страж", enemy_hp=10, enemy_atk=3, enemy_id="guardian", xp_reward=6))
            elif self.player.colliderect(self.sentry_left.inflate(28, 28)) and "sentry_left" not in self.game_state.defeated_enemies:
                self.manager.change(lambda m: CombatScene(m, self.game_state, self, enemy_name="Часовой", enemy_hp=7, enemy_atk=2, enemy_id="sentry_left", xp_reward=4))
            elif self.player.colliderect(self.sentry_right.inflate(28, 28)) and "sentry_right" not in self.game_state.defeated_enemies:
                self.manager.change(lambda m: CombatScene(m, self.game_state, self, enemy_name="Часовой", enemy_hp=7, enemy_atk=2, enemy_id="sentry_right", xp_reward=4))
            elif self.player.colliderect(self.chest.inflate(20, 20)):
                # Открытие сундука только после зачистки всех врагов
                required = {"guardian", "sentry_left", "sentry_right"}
                cleared = required.issubset(set(self.game_state.defeated_enemies)) or (self.game_state.guard_defeated and "sentry_left" in self.game_state.defeated_enemies and "sentry_right" in self.game_state.defeated_enemies)
                if cleared:
                    self.game_state.dungeon_fully_cleared = True
                    if not self.game_state.artifact_found:
                        self.game_state.artifact_found = True
                        self.game_state.artifact_level += 1
                        self.message = "Вы нашли древний артефакт!"
                        self.message_timer = 2.0
                        # Спавн мини-босса у выхода
                        self.spawn_miniboss()
                    else:
                        self.message = "Сундук пуст."
                        self.message_timer = 1.5
                else:
                    self.message = "Сундук запечатан. Победите всех стражей подземелья."
                    self.message_timer = 2.0
            elif self.player.colliderect(self.exit_rect.inflate(10, 10)):
                # Вернуться на поверхность
                self.manager.change(lambda m: OverworldScene(m, self.game_state))
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_m:
            self.show_minimap = not self.show_minimap
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_F5:
            try:
                with open("savegame.json", "w", encoding="utf-8") as f:
                    json.dump(self.game_state.to_dict(), f, ensure_ascii=False, indent=2)
                self.message = "Игра сохранена (F5)."
                self.message_timer = 2.0
            except Exception:
                self.message = "Не удалось сохранить."
                self.message_timer = 2.0
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_F9:
            try:
                with open("savegame.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                gs = GameState.from_dict(data)
                self.manager.change(make_scene_switch("DungeonScene", gs))
            except Exception:
                self.message = "Загрузка не удалась."
                self.message_timer = 2.0

    def update(self, dt):
        keys = pygame.key.get_pressed()
        dx = dy = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dx -= 1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx += 1
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            dy -= 1
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            dy += 1
        if dx != 0 and dy != 0:
            inv = 1 / math.sqrt(2)
            dx *= inv
            dy *= inv
        self.try_move(dx, dy, dt)

        if self.message_timer > 0:
            self.message_timer -= dt
            if self.message_timer <= 0:
                self.message = ""

        # Если мини-босс создан и не побеждён — возможность столкновения
        if hasattr(self, "miniboss") and not self.game_state.miniboss_defeated:
            if self.player.colliderect(self.miniboss.inflate(30, 30)):
                def on_win(gs: GameState):
                    gs.miniboss_defeated = True
                self.manager.change(lambda m: CombatScene(m, self.game_state, self, enemy_name="Лейтенант Теней", enemy_hp=14, enemy_atk=4, enemy_id="miniboss", on_win=on_win, xp_reward=8))

    def draw(self, screen):
        screen.fill((10, 8, 12))
        # Плитка пола и стены
        tile_size = 32
        for x in range(0, WIDTH, tile_size):
            for y in range(0, HEIGHT, tile_size):
                rect = pygame.Rect(x, y, tile_size, tile_size)
                draw_textured_rect(screen, rect, "tiles/dungeon_floor.png", fallback_color=(18, 16, 22))
        for wall in self.walls:
            draw_textured_rect(screen, wall, "tiles/dungeon_wall.png", fallback_color=(60, 60, 80))
        # Выход
        draw_textured_rect(screen, self.exit_rect, "objects/exit.png", fallback_color=(100, 80, 60), border_radius=4)
        draw_text(screen, "Выход", 18, WHITE, self.exit_rect.centerx, self.exit_rect.top - 16, center=True)
        # Страж
        color_guard = (180, 40, 40) if not self.game_state.guard_defeated else (40, 140, 60)
        draw_textured_rect(screen, self.guard, "enemies/guardian.png", fallback_color=color_guard, border_radius=4)
        draw_text(screen, "Страж", 18, WHITE, self.guard.centerx, self.guard.top - 16, center=True)
        # Часовые
        color_sl = (180, 40, 40) if "sentry_left" not in self.game_state.defeated_enemies else (40, 140, 60)
        color_sr = (180, 40, 40) if "sentry_right" not in self.game_state.defeated_enemies else (40, 140, 60)
        draw_textured_rect(screen, self.sentry_left, "enemies/sentry.png", fallback_color=color_sl, border_radius=4)
        draw_textured_rect(screen, self.sentry_right, "enemies/sentry.png", fallback_color=color_sr, border_radius=4)
        draw_text(screen, "Часовой", 16, WHITE, self.sentry_left.centerx, self.sentry_left.top - 14, center=True)
        draw_text(screen, "Часовой", 16, WHITE, self.sentry_right.centerx, self.sentry_right.top - 14, center=True)
        # Сундук
        draw_textured_rect(screen, self.chest, "objects/chest.png", fallback_color=(180, 140, 40), border_radius=4)
        draw_text(screen, "Сундук", 18, WHITE, self.chest.centerx, self.chest.top - 16, center=True)
        # Мини-босс
        if hasattr(self, "miniboss") and not self.game_state.miniboss_defeated:
            draw_textured_rect(screen, self.miniboss, "enemies/miniboss.png", fallback_color=(200, 80, 200), border_radius=4)
            draw_text(screen, "Лейтенант", 16, WHITE, self.miniboss.centerx, self.miniboss.top - 14, center=True)
        # Игрок (спрайт)
        screen.blit(self.player_sprite, self.player.topleft)

        if self.player.colliderect(self.guard.inflate(30, 30)) and not self.game_state.guard_defeated:
            draw_text(screen, "Нажмите E, чтобы сразиться со стражем", 18, LIGHT_GRAY, WIDTH // 2, HEIGHT - 60, center=True)
        elif self.player.colliderect(self.sentry_left.inflate(28, 28)) and "sentry_left" not in self.game_state.defeated_enemies:
            draw_text(screen, "Нажмите E, чтобы сразиться с часовым", 18, LIGHT_GRAY, WIDTH // 2, HEIGHT - 60, center=True)
        elif self.player.colliderect(self.sentry_right.inflate(28, 28)) and "sentry_right" not in self.game_state.defeated_enemies:
            draw_text(screen, "Нажмите E, чтобы сразиться с часовым", 18, LIGHT_GRAY, WIDTH // 2, HEIGHT - 60, center=True)
        elif self.player.colliderect(self.chest.inflate(20, 20)):
            draw_text(screen, "Нажмите E, чтобы открыть сундук", 18, LIGHT_GRAY, WIDTH // 2, HEIGHT - 60, center=True)
        elif self.player.colliderect(self.exit_rect.inflate(10, 10)):
            draw_text(screen, "Нажмите E, чтобы уйти", 18, LIGHT_GRAY, WIDTH // 2, HEIGHT - 60, center=True)
        elif hasattr(self, "miniboss") and not self.game_state.miniboss_defeated and self.player.colliderect(self.miniboss.inflate(30, 30)):
            draw_text(screen, "Сразиться с Лейтенантом (подойдите ближе)", 18, LIGHT_GRAY, WIDTH // 2, HEIGHT - 60, center=True)

        if self.message:
            draw_text(screen, self.message, 20, YELLOW, WIDTH // 2, 40, center=True)
        if self.show_minimap:
            self.draw_minimap(screen)

    def draw_minimap(self, screen: pygame.Surface):
        mw, mh = 180, 100
        mx, my = WIDTH - mw - 16, 30
        pygame.draw.rect(screen, (0, 0, 0), (mx - 4, my - 4, mw + 8, mh + 8))
        pygame.draw.rect(screen, (30, 30, 30), (mx, my, mw, mh))
        scale_x = mw / WIDTH
        scale_y = mh / HEIGHT
        for wall in self.walls:
            r = pygame.Rect(mx + int(wall.left * scale_x), my + int(wall.top * scale_y), int(wall.width * scale_x), int(wall.height * scale_y))
            pygame.draw.rect(screen, (70, 70, 90), r)
        for obj, color in [
            (self.guard, (200, 60, 60)),
            (self.chest, (200, 180, 60)),
            (self.exit_rect, (120, 100, 80)),
        ]:
            r = pygame.Rect(mx + int(obj.centerx * scale_x) - 2, my + int(obj.centery * scale_y) - 2, 4, 4)
            pygame.draw.rect(screen, color, r)
        pr = pygame.Rect(mx + int(self.player.centerx * scale_x) - 2, my + int(self.player.centery * scale_y) - 2, 4, 4)
        pygame.draw.rect(screen, (80, 220, 80), pr)

    def spawn_miniboss(self):
        # Появляется у выхода
        self.miniboss = pygame.Rect(self.exit_rect.centerx - 16, self.exit_rect.top - 48, 32, 32)


class FieldsScene(Scene):
    def __init__(self, manager: SceneManager, game_state: GameState):
        super().__init__(manager)
        self.game_state = game_state
        self.game_state.last_location = "fields"
        self.player = pygame.Rect(WIDTH - 100, HEIGHT // 2, 28, 28)
        self.player_sprite = load_player_sprite((self.player.width, self.player.height))
        self.speed = 260
        self.walls = [
            pygame.Rect(0, 0, WIDTH, 24),
            pygame.Rect(0, HEIGHT - 24, WIDTH, 24),
            pygame.Rect(0, 0, 24, HEIGHT),
            pygame.Rect(WIDTH - 24, 0, 24, HEIGHT),
            pygame.Rect(260, 100, 24, 280),
        ]
        self.herbalist = pygame.Rect(100, 120, 30, 30)
        self.exit_gate = pygame.Rect(WIDTH - 80, HEIGHT // 2 - 18, 36, 36)
        # Точки с травами
        self.herb_nodes = [
            pygame.Rect(300, 140, 16, 16),
            pygame.Rect(360, 200, 16, 16),
            pygame.Rect(420, 300, 16, 16),
            pygame.Rect(520, 240, 16, 16),
            pygame.Rect(640, 180, 16, 16),
        ]
        self.collected = set()
        self.message = ""
        self.message_timer = 0.0
        self.show_minimap = False
        # Чекпоинты для забега на время
        self.checkpoints = [
            pygame.Rect(260, 120, 22, 22),
            pygame.Rect(480, 200, 22, 22),
            pygame.Rect(680, 280, 22, 22),
        ]
        self.active_checkpoint = 0

    def collide(self, rect: pygame.Rect) -> bool:
        for wall in self.walls:
            if rect.colliderect(wall):
                return True
        return False

    def try_move(self, dx: float, dy: float, dt: float):
        step_x = pygame.Rect(self.player)
        step_x.x += int(dx * self.speed * dt)
        if not self.collide(step_x):
            self.player = step_x
        step_y = pygame.Rect(self.player)
        step_y.y += int(dy * self.speed * dt)
        if not self.collide(step_y):
            self.player = step_y

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_e:
            if self.player.colliderect(self.herbalist.inflate(30, 30)):
                self.talk_herbalist()
            elif self.player.colliderect(self.exit_gate.inflate(20, 20)):
                self.manager.change(make_scene_switch("OverworldScene", self.game_state))
            else:
                # Сбор травы
                for i, node in enumerate(self.herb_nodes):
                    if i not in self.collected and self.player.colliderect(node.inflate(20, 20)):
                        self.collected.add(i)
                        self.game_state.herbs += 1
                        self.message = "Вы собрали травы (+1)"
                        self.message_timer = 1.5
                        break
                # Старт/рестарт забега у первой точки
                if self.player.colliderect(self.checkpoints[0].inflate(20, 20)) and not self.game_state.trial_active and not self.game_state.trial_completed:
                    self.start_trial()
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_m:
            self.show_minimap = not self.show_minimap
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_F5:
            try:
                with open("savegame.json", "w", encoding="utf-8") as f:
                    json.dump(self.game_state.to_dict(), f, ensure_ascii=False, indent=2)
                self.message = "Игра сохранена (F5)."
                self.message_timer = 2.0
            except Exception:
                self.message = "Не удалось сохранить."
                self.message_timer = 2.0
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_F9:
            try:
                with open("savegame.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                gs = GameState.from_dict(data)
                self.manager.change(make_scene_switch("FieldsScene", gs))
            except Exception:
                self.message = "Загрузка не удалась."
                self.message_timer = 2.0

    def talk_herbalist(self):
        def on_choice(choice_id: int):
            if choice_id == 0:
                if self.game_state.herbs >= 3 and not self.game_state.companion_joined:
                    self.game_state.herbs -= 3
                    self.game_state.companion_joined = True
                    self.message = "Травник присоединился как спутник!"
                    self.message_timer = 2.0
                else:
                    self.message = "Недостаточно трав или спутник уже с вами."
                    self.message_timer = 2.0
            elif choice_id == 1:
                if self.game_state.herbs >= 1:
                    self.game_state.herbs -= 1
                    self.game_state.potions += 1
                    self.message = "Травник приготовил зелье из трав."
                    self.message_timer = 2.0
                else:
                    self.message = "Нет трав для зелья."
                    self.message_timer = 2.0
        text = "Травник: Травы редки. Принесёшь три — отправлюсь с тобой, или сделаю зелье."
        choices = [("Попросить спутничества (3 травы)", 0), ("Сделать зелье (1 трава)", 1), ("Ничего", 2)]
        self.manager.change(lambda m: DialogueScene(m, text, choices, on_choice, self))

    def update(self, dt):
        keys = pygame.key.get_pressed()
        dx = dy = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dx -= 1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx += 1
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            dy -= 1
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            dy += 1
        if dx != 0 and dy != 0:
            inv = 1 / math.sqrt(2)
            dx *= inv
            dy *= inv
        self.try_move(dx, dy, dt)

        if self.message_timer > 0:
            self.message_timer -= dt
            if self.message_timer <= 0:
                self.message = ""

        # Логика забега на время
        if self.game_state.trial_active:
            self.game_state.trial_time_left = max(0.0, self.game_state.trial_time_left - dt)
            # Проверка чекпоинта
            if self.active_checkpoint < len(self.checkpoints):
                if self.player.colliderect(self.checkpoints[self.active_checkpoint].inflate(10, 10)):
                    self.active_checkpoint += 1
                    self.message = f"Чекпоинт {self.active_checkpoint}/{len(self.checkpoints)}!"
                    self.message_timer = 1.5
            if self.active_checkpoint >= len(self.checkpoints):
                # Успех
                self.game_state.trial_active = False
                self.game_state.trial_completed = True
                self.game_state.gold += 8
                self.game_state.grant_xp(5)
                self.message = "Забег пройден! Награда получена."
                self.message_timer = 2.0
            elif self.game_state.trial_time_left <= 0:
                # Провал
                self.game_state.trial_active = False
                self.message = "Время вышло! Попробуйте снова."
                self.message_timer = 2.0

    def draw(self, screen):
        screen.fill((18, 26, 18))
        # Плитка пола и стены
        tile_size = 32
        for x in range(0, WIDTH, tile_size):
            for y in range(0, HEIGHT, tile_size):
                rect = pygame.Rect(x, y, tile_size, tile_size)
                draw_textured_rect(screen, rect, "tiles/fields_floor.png", fallback_color=(20, 34, 20))
        for wall in self.walls:
            draw_textured_rect(screen, wall, "tiles/fields_wall.png", fallback_color=(40, 70, 40))
        # Объекты
        draw_textured_rect(screen, self.exit_gate, "objects/gate.png", fallback_color=(100, 200, 100), border_radius=4)
        draw_text(screen, "К городу", 18, WHITE, self.exit_gate.centerx, self.exit_gate.top - 16, center=True)
        draw_textured_rect(screen, self.herbalist, "characters/herbalist.png", fallback_color=(100, 160, 240), border_radius=4)
        draw_text(screen, "Травник", 18, WHITE, self.herbalist.centerx, self.herbalist.top - 16, center=True)
        # Травы
        for i, node in enumerate(self.herb_nodes):
            if i not in self.collected:
                draw_textured_rect(screen, node, "objects/herb.png", fallback_color=(120, 220, 120), border_radius=4)
        # Чекпоинты забега
        for i, cp in enumerate(self.checkpoints):
            color = (200, 200, 80) if i == self.active_checkpoint and self.game_state.trial_active else (120, 120, 60)
            draw_textured_rect(screen, cp, "objects/checkpoint.png", fallback_color=color, border_radius=4)
        # Игрок (спрайт)
        screen.blit(self.player_sprite, self.player.topleft)

        if self.player.colliderect(self.herbalist.inflate(30, 30)):
            draw_text(screen, "Нажмите E, чтобы говорить с травником", 18, LIGHT_GRAY, WIDTH // 2, HEIGHT - 60, center=True)
        elif self.player.colliderect(self.exit_gate.inflate(20, 20)):
            draw_text(screen, "Нажмите E, чтобы вернуться в город", 18, LIGHT_GRAY, WIDTH // 2, HEIGHT - 60, center=True)
        else:
            for i, node in enumerate(self.herb_nodes):
                if i not in self.collected and self.player.colliderect(node.inflate(20, 20)):
                    draw_text(screen, "Нажмите E, чтобы собрать травы", 18, LIGHT_GRAY, WIDTH // 2, HEIGHT - 60, center=True)
                    break
            if not self.game_state.trial_completed:
                if self.player.colliderect(self.checkpoints[0].inflate(20, 20)) and not self.game_state.trial_active:
                    draw_text(screen, "Нажмите E у стартовой точки, чтобы начать забег", 18, LIGHT_GRAY, WIDTH // 2, HEIGHT - 60, center=True)

        if self.game_state.trial_active:
            draw_text(screen, f"Забег — время: {self.game_state.trial_time_left:.1f}s", 20, YELLOW, WIDTH // 2, 40, center=True)

        if self.message:
            draw_text(screen, self.message, 20, YELLOW, WIDTH // 2, 40, center=True)
        draw_text(screen, "M — мини-карта   F5/F9 — сохранение/загрузка", 16, LIGHT_GRAY, WIDTH - 300, 16, center=False)
        if self.show_minimap:
            self.draw_minimap(screen)

    def draw_minimap(self, screen: pygame.Surface):
        mw, mh = 180, 100
        mx, my = WIDTH - mw - 16, 30
        pygame.draw.rect(screen, (0, 0, 0), (mx - 4, my - 4, mw + 8, mh + 8))
        pygame.draw.rect(screen, (30, 30, 30), (mx, my, mw, mh))
        scale_x = mw / WIDTH
        scale_y = mh / HEIGHT
        for wall in self.walls:
            r = pygame.Rect(mx + int(wall.left * scale_x), my + int(wall.top * scale_y), int(wall.width * scale_x), int(wall.height * scale_y))
            pygame.draw.rect(screen, (70, 90, 70), r)
        for node in self.herb_nodes:
            r = pygame.Rect(mx + int(node.centerx * scale_x) - 2, my + int(node.centery * scale_y) - 2, 4, 4)
            pygame.draw.rect(screen, (120, 220, 120), r)
        for obj, color in [
            (self.herbalist, (100, 160, 240)),
            (self.exit_gate, (100, 200, 100)),
            (self.checkpoints[0], (200, 200, 80)),
        ]:
            r = pygame.Rect(mx + int(obj.centerx * scale_x) - 2, my + int(obj.centery * scale_y) - 2, 4, 4)
            pygame.draw.rect(screen, color, r)
    def start_trial(self):
        self.game_state.trial_active = True
        self.game_state.trial_time_left = 20.0
        self.game_state.trial_stage = 0
        self.active_checkpoint = 0
        self.message = "Забег начат! Доберитесь до всех чекпоинтов."
        self.message_timer = 2.0
# ---------- Основной цикл ----------
def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption(TITLE)
    clock = pygame.time.Clock()

    manager = SceneManager(lambda m: TitleScene(m))

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            else:
                manager.handle_event(event)

        manager.update(dt)
        manager.draw(screen)

        pygame.display.flip()

    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()


