import pygame
import random
import math
import json
import os
import sys
import array

# Предварительная настройка звука
pygame.mixer.pre_init(44100, -16, 1, 1024)
pygame.init()

# Автоматическое растягивание на весь экран со сглаживанием
WIDTH, HEIGHT = 540, 960
try:
    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.SCALED | pygame.FULLSCREEN)
except Exception:
    screen = pygame.display.set_mode((WIDTH, HEIGHT))

pygame.display.set_caption("Wall Crusher")
clock = pygame.time.Clock()

# Шрифты
font_xs = pygame.font.SysFont("sans-serif", 17)
font_sm = pygame.font.SysFont("sans-serif", 21)
font_md = pygame.font.SysFont("sans-serif", 25, bold=True)
font_lg = pygame.font.SysFont("sans-serif", 36, bold=True)
font_xl = pygame.font.SysFont("sans-serif", 50, bold=True)

# Палитра
BG_COLOR = (14, 15, 24)
PANEL_COLOR = (26, 28, 45)
BTN_COLOR = (45, 50, 82)
BTN_ACTIVE = (30, 155, 95)
BTN_EQUIPPED = (50, 115, 215)
BTN_DISABLED = (38, 38, 48)
TEXT_COLOR = (240, 242, 255)
GOLD_COLOR = (255, 215, 45)
CRIT_COLOR = (255, 65, 85)
GEM_COLOR = (0, 230, 255)
REBIRTH_COLOR = (210, 90, 255)

# --- АУДИОДВИЖОК С ПОЛЗУНКАМИ ---
class AudioEngine:
    def __init__(self):
        self.sfx_vol = 0.8
        self.music_vol = 0.6
        self.ready = False
        self.music_channel = None
        try:
            self.hit = self._make_sfx(170, 45, 0.07, noise=0.3)
            self.crit = self._make_sfx(520, 130, 0.14, noise=0.1)
            self.coin = self._make_sfx(920, 1480, 0.08, noise=0.0)
            self.break_wall = self._make_sfx(130, 28, 0.30, noise=0.75)
            self.buy = self._make_sfx(420, 840, 0.12, noise=0.0)
            self.click_ui = self._make_sfx(600, 500, 0.04, noise=0.0)
            
            self.bgm = self._make_ambient_loop()
            self.music_channel = pygame.mixer.Channel(0)
            self.ready = True
        except Exception:
            self.ready = False

    def _make_sfx(self, f_start, f_end, duration, noise=0.0):
        sr = 44100
        n = int(sr * duration)
        buf = array.array('h')
        phase = 0.0
        for i in range(n):
            t = i / n
            freq = f_start + (f_end - f_start) * t
            phase += 2.0 * math.pi * freq / sr
            tone = math.sin(phase) * (1.0 - noise) + random.uniform(-1, 1) * noise
            decay = (1.0 - t) ** 1.5
            val = int(tone * decay * 0.4 * 32767)
            buf.append(max(-32768, min(32767, val)))
        return pygame.mixer.Sound(buffer=buf)

    def _make_ambient_loop(self):
        sr = 44100
        duration = 8.0
        n = int(sr * duration)
        buf = array.array('h')
        chords = [
            (220.0, 261.63, 329.63),
            (174.61, 220.0, 261.63),
            (261.63, 329.63, 392.00),
            (196.00, 246.94, 329.63),
        ]
        chord_len = n // 4
        for i in range(n):
            c_idx = min(3, i // chord_len)
            local_t = (i % chord_len) / chord_len
            env = math.sin(math.pi * local_t) ** 0.7
            t = i / sr
            f1, f2, f3 = chords[c_idx]
            wave = (
                math.sin(2.0 * math.pi * f1 * t) * 0.45 +
                math.sin(2.0 * math.pi * f2 * t) * 0.35 +
                math.sin(2.0 * math.pi * f3 * t) * 0.20
            )
            val = int(wave * env * 0.14 * 32767)
            buf.append(max(-32768, min(32767, val)))
        return pygame.mixer.Sound(buffer=buf)

    def play_sfx(self, snd):
        if self.ready and self.sfx_vol > 0:
            snd.set_volume(self.sfx_vol)
            snd.play()

    def update_music(self):
        if not self.ready or not self.music_channel:
            return
        if self.music_vol > 0:
            self.music_channel.set_volume(self.music_vol)
            if not self.music_channel.get_busy():
                self.music_channel.play(self.bgm, loops=-1)
        else:
            self.music_channel.stop()

audio = AudioEngine()

# --- 12 УНИКАЛЬНЫХ ТИПОВ СТЕН ---
BARRIERS = [
    ("Деревянный заслон",  (155, 95, 45),   (95, 55, 25),    "wood"),
    ("Кирпичная кладка",   (185, 65, 55),   (120, 35, 30),   "brick"),
    ("Армобетонный блок",  (130, 138, 148), (85, 90, 100),   "concrete"),
    ("Стальной шлюз",      (70, 120, 165),  (40, 75, 110),   "steel"),
    ("Титановый бастион",  (90, 95, 110),   (50, 55, 68),    "titanium"),
    ("Обсидиановый монолит",(45, 30, 65),   (25, 15, 40),    "obsidian"),
    ("Кристальная грань",  (60, 200, 235),  (30, 130, 165),  "crystal"),
    ("Магмовая порода",    (190, 50, 20),   (90, 20, 10),    "magma"),
    ("Плазменный щит",     (140, 45, 205),  (85, 20, 140),   "plasma"),
    ("Квантовый барьер",   (15, 175, 155),  (10, 105, 95),   "quantum"),
    ("Нейтронная броня",   (195, 175, 50),  (125, 105, 20),  "neutron"),
    ("Стена Бесконечности",(25, 20, 45),    (240, 80, 255),  "void"),
]

def create_wall_texture(w, h, b_info):
    _, base_col, border_col, style = b_info
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(surf, base_col, (0, 0, w, h), border_radius=16)
    rng = random.Random(style)

    if style == "wood":
        plank_h = h // 5
        for row in range(5):
            y = row * plank_h
            shade = rng.randint(-12, 12)
            p_col = tuple(max(0, min(255, c + shade)) for c in base_col)
            pygame.draw.rect(surf, p_col, (6, y + 2, w - 12, plank_h - 4), border_radius=4)
            pygame.draw.line(surf, border_col, (4, y), (w - 4, y), 3)
            for _ in range(7):
                gy = y + rng.randint(5, plank_h - 5)
                pygame.draw.line(surf, (110, 60, 20), (12, gy), (w - 12, gy + rng.randint(-3, 3)), 2)

    elif style == "brick":
        pygame.draw.rect(surf, (80, 75, 75), (6, 6, w - 12, h - 12), border_radius=12)
        bh, bw = 32, 64
        for row in range(0, h - 12, bh):
            offset = (bw // 2) if (row // bh) % 2 == 1 else 0
            for col in range(-offset, w - 12, bw):
                bx = max(8, col + 8)
                bw_clip = min(col + bw - 4, w - 8) - bx
                by = max(8, row + 8)
                bh_clip = min(row + bh - 4, h - 8) - by
                if bw_clip > 6 and bh_clip > 6:
                    var = rng.randint(-25, 20)
                    c = (max(0, min(255, base_col[0] + var)),
                         max(0, min(255, base_col[1] + var // 2)),
                         max(0, min(255, base_col[2] + var // 2)))
                    pygame.draw.rect(surf, c, (bx, by, bw_clip, bh_clip), border_radius=3)

    elif style == "concrete":
        for _ in range(160):
            px, py = rng.randint(12, w - 12), rng.randint(12, h - 12)
            r = rng.randint(2, 5)
            sh = rng.randint(-25, 20)
            c = tuple(max(0, min(255, ch + sh)) for ch in base_col)
            pygame.draw.circle(surf, c, (px, py), r)
        pygame.draw.line(surf, (70, 75, 85), (w // 2, 8), (w // 2, h - 8), 3)
        pygame.draw.line(surf, (70, 75, 85), (8, h // 2), (w - 8, h // 2), 3)

    elif style == "steel":
        for i in range(-h, w, 24):
            pygame.draw.line(surf, (90, 145, 190), (max(10, i), 10), (min(w - 10, i + h), h - 10), 5)
        pygame.draw.rect(surf, (45, 85, 125), (16, 16, w - 32, h - 32), width=3, border_radius=8)
        for pos in range(28, w - 20, 34):
            pygame.draw.circle(surf, (170, 210, 240), (pos, 26), 4)
            pygame.draw.circle(surf, (170, 210, 240), (pos, h - 26), 4)

    elif style == "titanium":
        for x in range(25, w - 20, 42):
            pygame.draw.line(surf, (125, 130, 145), (x, 10), (x, h - 10), 4)
        pygame.draw.line(surf, (60, 65, 75), (12, 12), (w - 12, h - 12), 4)
        pygame.draw.line(surf, (60, 65, 75), (w - 12, 12), (12, h - 12), 4)
        pygame.draw.rect(surf, (40, 44, 52), (14, 14, w - 28, h - 28), width=5, border_radius=12)

    elif style == "obsidian":
        for _ in range(18):
            pts = [(rng.randint(15, w - 15), rng.randint(15, h - 15)) for _ in range(3)]
            sh = rng.randint(-15, 35)
            c = (max(0, min(255, base_col[0] + sh)), max(0, min(255, base_col[1] + sh)), max(0, min(255, base_col[2] + sh * 2)))
            pygame.draw.polygon(surf, c, pts)
        for _ in range(6):
            pygame.draw.line(surf, (150, 80, 255), (rng.randint(20, w-20), rng.randint(20, h-20)), (rng.randint(20, w-20), rng.randint(20, h-20)), 2)

    elif style == "crystal":
        cx, cy = w // 2, h // 2
        for i in range(12):
            ang = i * (math.pi / 6)
            x2 = cx + int(math.cos(ang) * 130)
            y2 = cy + int(math.sin(ang) * 130)
            pygame.draw.line(surf, (180, 245, 255), (cx, cy), (x2, y2), 3)
        pygame.draw.polygon(surf, (130, 235, 255), [(cx, 35), (w - 40, cy), (cx, h - 35), (40, cy)], width=4)
        pygame.draw.polygon(surf, (220, 255, 255), [(cx, 75), (w - 80, cy), (cx, h - 75), (80, cy)])

    elif style == "magma":
        for _ in range(22):
            rx, ry = rng.randint(15, w - 55), rng.randint(15, h - 55)
            pygame.draw.ellipse(surf, (255, 140, 20), (rx, ry, rng.randint(25, 50), rng.randint(15, 35)))
        for _ in range(14):
            x1, y1 = rng.randint(15, w - 15), rng.randint(15, h - 15)
            x2, y2 = x1 + rng.randint(-60, 60), y1 + rng.randint(-60, 60)
            pygame.draw.line(surf, (255, 230, 60), (x1, y1), (x2, y2), 4)

    elif style == "plasma":
        step = 32
        for x in range(16, w - 16, step):
            pygame.draw.line(surf, (175, 70, 245), (x, 12), (x, h - 12), 2)
        for y in range(16, h - 16, step):
            pygame.draw.line(surf, (175, 70, 245), (12, y), (w - 12, y), 2)
        for r in range(85, 15, -18):
            pygame.draw.circle(surf, (220, 120, 255), (w // 2, h // 2), r, 3)

    elif style == "quantum":
        for x in range(20, w - 20, 22):
            length = rng.randint(30, h - 30)
            pygame.draw.line(surf, (0, 235, 200), (x, 15), (x, length), 2)
            pygame.draw.circle(surf, (170, 255, 240), (x, length), 4)

    elif style == "neutron":
        cx, cy = w // 2, h // 2
        pygame.draw.circle(surf, (255, 240, 130), (cx, cy), 32)
        pygame.draw.circle(surf, (255, 255, 255), (cx, cy), 18)
        pygame.draw.ellipse(surf, (255, 235, 100), (30, cy - 35, w - 60, 70), 3)
        pygame.draw.ellipse(surf, (255, 235, 100), (cx - 35, 25, 70, h - 50), 3)

    elif style == "void":
        for _ in range(45):
            sx, sy = rng.randint(15, w - 15), rng.randint(15, h - 15)
            pygame.draw.circle(surf, (255, 255, 255), (sx, sy), rng.randint(1, 3))
        for r in range(95, 15, -14):
            col = (min(255, 90 + r), 30, min(255, 150 + r))
            pygame.draw.circle(surf, col, (w // 2, h // 2), r, 3)
        pygame.draw.circle(surf, (5, 5, 10), (w // 2, h // 2), 24)
        pygame.draw.circle(surf, (255, 100, 255), (w // 2, h // 2), 26, 2)

    pygame.draw.rect(surf, border_col, (0, 0, w, h), width=8, border_radius=16)
    return surf

# --- 14 ПРОРАБОТАННЫХ ГЕРОЕВ (ДО 1 ТРИЛЛИОНА $) ---
HEROES = [
    {"id": 0,  "name": "Стажёр",          "cost": 0,             "color": (0, 200, 255),   "weapon": (180, 180, 200), "c_m": 1,    "a_m": 1,    "g_m": 1,    "cr_b": 0,  "desc": "Базовый боец (Без бонусов)"},
    {"id": 1,  "name": "Крушитель",       "cost": 250,           "color": (255, 110, 40),  "weapon": (220, 60, 40),   "c_m": 2,    "a_m": 1,    "g_m": 1,    "cr_b": 0,  "desc": "Урон клика x2"},
    {"id": 2,  "name": "Техно-маг",       "cost": 1500,          "color": (180, 70, 255),  "weapon": (0, 255, 220),   "c_m": 1,    "a_m": 2.5,  "g_m": 1,    "cr_b": 0,  "desc": "Авто-дроны DPS x2.5"},
    {"id": 3,  "name": "Ниндзя",          "cost": 8000,          "color": (230, 40, 80),   "weapon": (255, 255, 255), "c_m": 1.5,  "a_m": 1,    "g_m": 1,    "cr_b": 25, "desc": "+25% шанс крита, Клик x1.5"},
    {"id": 4,  "name": "Магнат",          "cost": 45000,         "color": (255, 215, 0),   "weapon": (255, 240, 120), "c_m": 1,    "a_m": 1,    "g_m": 3,    "cr_b": 0,  "desc": "Золото с монет x3"},
    {"id": 5,  "name": "Кибер-рыцарь",    "cost": 250000,        "color": (50, 230, 100),  "weapon": (100, 255, 150), "c_m": 4,    "a_m": 2.5,  "g_m": 1,    "cr_b": 0,  "desc": "Клик x4 и Авто-DPS x2.5"},
    {"id": 6,  "name": "Властелин Бури",  "cost": 1500000,       "color": (255, 60, 220),  "weapon": (150, 240, 255), "c_m": 5,    "a_m": 5,    "g_m": 2,    "cr_b": 15, "desc": "Урон x5, Золото x2, +15% крит"},
    {"id": 7,  "name": "Пиромант",        "cost": 12000000,      "color": (255, 70, 20),   "weapon": (255, 200, 30),  "c_m": 12,   "a_m": 6,    "g_m": 2,    "cr_b": 20, "desc": "Клик x12, Авто x6, Золото x2"},
    {"id": 8,  "name": "Крио-страж",      "cost": 95000000,      "color": (80, 230, 255),  "weapon": (200, 250, 255), "c_m": 10,   "a_m": 25,   "g_m": 3,    "cr_b": 10, "desc": "Авто-DPS x25, Клик x10, Золото x3"},
    {"id": 9,  "name": "Жнец Бездны",     "cost": 800000000,     "color": (130, 30, 190),  "weapon": (230, 50, 255),  "c_m": 35,   "a_m": 20,   "g_m": 4,    "cr_b": 35, "desc": "Клик x35, Авто x20, +35% крит"},
    {"id": 10, "name": "Звездный Паладин","cost": 6500000000,    "color": (255, 230, 120), "weapon": (255, 255, 220), "c_m": 60,   "a_m": 60,   "g_m": 8,    "cr_b": 20, "desc": "Урон x60, Золото x8"},
    {"id": 11, "name": "Хроно-лорд",      "cost": 55000000000,   "color": (0, 245, 190),   "weapon": (180, 255, 240), "c_m": 120,  "a_m": 200,  "g_m": 12,   "cr_b": 25, "desc": "Авто x200, Клик x120, Золото x12"},
    {"id": 12, "name": "Архонт Галактики","cost": 250000000000,  "color": (60, 90, 255),   "weapon": (255, 120, 255), "c_m": 450,  "a_m": 450,  "g_m": 30,   "cr_b": 35, "desc": "Весь урон x450, Золото x30"},
    {"id": 13, "name": "АБСОЛЮТ",         "cost": 1000000000000, "color": (255, 255, 255), "weapon": (255, 215, 0),   "c_m": 2500, "a_m": 2500, "g_m": 100,  "cr_b": 50, "desc": "Урон x2500, Золото x100, +50% крит"},
]

# --- РАНГИ И ТИТУЛЫ ПЕРЕРОЖДЕНИЙ ---
REBIRTH_RANKS = [
    (0,  "Смертный"),
    (1,  "Пробужденный"),
    (3,  "Искатель"),
    (6,  "Разрушитель"),
    (10, "Бессмертный"),
    (15, "Титан"),
    (25, "Полубог"),
    (40, "Демиург"),
    (60, "Вечный"),
]

SAVE_FILE = "wall_crusher_save.json"

class GameState:
    def __init__(self):
        self.gold = 0.0
        self.gems = 0
        self.rebirths = 0
        self.stage = 1
        self.click_lvl = 1
        self.auto_lvl = 0
        self.crit_lvl = 0
        self.gold_lvl = 1
        
        self.owned_heroes = [0]
        self.current_hero = 0
        
        self.max_hp = 55.0
        self.hp = 55.0
        self.cracks = []
        self.wall_surf = None
        
        self.load()
        audio.update_music()
        self.setup_barrier(reset_hp=False)

    @property
    def hero(self):
        if 0 <= self.current_hero < len(HEROES):
            return HEROES[self.current_hero]
        return HEROES[0]

    @property
    def rebirth_title(self):
        title = "Смертный"
        for req, name in REBIRTH_RANKS:
            if self.rebirths >= req:
                title = name
        return title

    @property
    def rebirth_power_mult(self):
        # Каждое перерождение усиливает весь урон на +100%, а кристаллы дают +50%
        return (1.0 + self.gems * 0.5) * (1.0 + self.rebirths * 1.0)

    @property
    def click_dmg(self):
        base = self.click_lvl * (1.24 ** (self.click_lvl - 1))
        return max(1.0, base * self.rebirth_power_mult * self.hero["c_m"])

    @property
    def auto_dps(self):
        if self.auto_lvl == 0:
            return 0.0
        base = self.auto_lvl * 2.5 * (1.22 ** (self.auto_lvl - 1))
        return base * self.rebirth_power_mult * self.hero["a_m"]

    @property
    def crit_chance(self):
        base = min(60, self.crit_lvl * 3)
        return min(100, base + self.hero["cr_b"])

    @property
    def gold_mult(self):
        base = 1.0 + (self.gold_lvl - 1) * 0.38
        rebirth_gold = 1.0 + (self.rebirths * 0.5)
        return base * self.hero["g_m"] * rebirth_gold

    def get_cost(self, upgrade_type):
        if upgrade_type == "click": return int(14 * (1.46 ** (self.click_lvl - 1)))
        elif upgrade_type == "auto": return int(30 * (1.50 ** (self.auto_lvl)))
        elif upgrade_type == "crit": return int(95 * (1.76 ** (self.crit_lvl)))
        elif upgrade_type == "gold": return int(160 * (1.78 ** (self.gold_lvl - 1)))
        return 0

    def get_barrier_info(self):
        idx = ((self.stage - 1) // 4) % len(BARRIERS)
        return BARRIERS[idx]

    def get_next_rebirth_req(self):
        # Требуемый уровень стены плавно растет с каждым перерождением (10, 12, 14... до 40)
        return min(40, 10 + self.rebirths * 2)

    def get_pending_gems(self):
        req = self.get_next_rebirth_req()
        if self.stage < req:
            return 0
        base_gems = 1 + (self.stage - req) // 3
        rebirth_bonus = 1.0 + (self.rebirths * 0.35)
        return max(1, int(base_gems * rebirth_bonus))

    def setup_barrier(self, reset_hp=True):
        self.max_hp = math.floor(55 * (1.56 ** (self.stage - 1)))
        if reset_hp or self.hp > self.max_hp or self.hp <= 0:
            self.hp = float(self.max_hp)
        
        self.wall_surf = create_wall_texture(290, 275, self.get_barrier_info())
        
        self.cracks = []
        cx, cy = 195 + 145, 175 + 137
        for _ in range(22):
            x1 = cx + random.randint(-110, 110)
            y1 = cy + random.randint(-110, 110)
            x2 = x1 + random.randint(-50, 50)
            y2 = y1 + random.randint(-50, 50)
            x3 = x2 + random.randint(-40, 40)
            y3 = y2 + random.randint(-40, 40)
            self.cracks.append(((x1, y1), (x2, y2), (x3, y3)))

    def save(self):
        data = {
            "gold": self.gold, "gems": self.gems, "rebirths": self.rebirths,
            "stage": self.stage, "click_lvl": self.click_lvl,
            "auto_lvl": self.auto_lvl, "crit_lvl": self.crit_lvl,
            "gold_lvl": self.gold_lvl, "hp": self.hp,
            "owned_heroes": self.owned_heroes, "current_hero": self.current_hero,
            "sfx_vol": audio.sfx_vol, "music_vol": audio.music_vol
        }
        try:
            with open(SAVE_FILE, "w") as f:
                json.dump(data, f)
        except Exception:
            pass

    def load(self):
        if os.path.exists(SAVE_FILE):
            try:
                with open(SAVE_FILE, "r") as f:
                    d = json.load(f)
                    self.gold = d.get("gold", 0.0)
                    self.gems = d.get("gems", 0)
                    self.rebirths = d.get("rebirths", 0)
                    self.stage = d.get("stage", 1)
                    self.click_lvl = d.get("click_lvl", 1)
                    self.auto_lvl = d.get("auto_lvl", 0)
                    self.crit_lvl = d.get("crit_lvl", 0)
                    self.gold_lvl = d.get("gold_lvl", 1)
                    self.hp = d.get("hp", 55.0)
                    self.owned_heroes = d.get("owned_heroes", [0])
                    self.current_hero = d.get("current_hero", 0)
                    audio.sfx_vol = d.get("sfx_vol", 0.8)
                    audio.music_vol = d.get("music_vol", 0.6)
            except Exception:
                pass

    def reset_game(self):
        self.gold = 0.0
        self.gems = 0
        self.rebirths = 0
        self.stage = 1
        self.click_lvl = 1
        self.auto_lvl = 0
        self.crit_lvl = 0
        self.gold_lvl = 1
        self.owned_heroes = [0]
        self.current_hero = 0
        self.setup_barrier()
        self.save()

    def rebirth(self):
        earned = self.get_pending_gems()
        if earned > 0:
            self.gems += earned
            self.rebirths += 1
            self.gold = 0.0
            self.stage = 1
            self.click_lvl = 1
            self.auto_lvl = 0
            self.crit_lvl = 0
            self.gold_lvl = 1
            self.setup_barrier()
            self.save()
            return True
        return False

def fmt(num):
    if num < 1000:
        return str(int(num))
    for unit in ["", "K", "M", "B", "T", "Qa", "Qi", "Sx", "Sp"]:
        if abs(num) < 1000.0:
            return f"{num:3.1f}{unit}".strip()
        num /= 1000.0
    return f"{num:.1f}Oc"

class Coin:
    def __init__(self, x, y, value):
        self.x, self.y = float(x), float(y)
        self.vx = random.uniform(-6.5, 6.5)
        self.vy = random.uniform(-11.0, -4.0)
        self.value = value
        self.radius = 15
        self.ground_y = random.randint(465, 505)
        self.collected = False
        self.age = 0
        self.anim_offset = random.uniform(0, 6.28)

    def update(self):
        self.age += 1
        if self.y < self.ground_y or self.vy < 0:
            self.x += self.vx
            self.y += self.vy
            self.vy += 0.55
            if self.x < 25 or self.x > WIDTH - 25:
                self.vx *= -0.7
            if self.y >= self.ground_y:
                self.y = float(self.ground_y)
                if abs(self.vy) > 2.5:
                    self.vy = -self.vy * 0.45
                    self.vx *= 0.6
                else:
                    self.vy, self.vx = 0, 0
        if self.age > 260:
            self.x += (60 - self.x) * 0.14
            self.y += (30 - self.y) * 0.14
            if abs(self.x - 60) < 25 and abs(self.y - 30) < 25:
                return True
        return False

    def draw(self, surf):
        w = max(4, int(self.radius * 2 * abs(math.sin(self.age * 0.1 + self.anim_offset))))
        rect = pygame.Rect(int(self.x - w // 2), int(self.y - self.radius), w, self.radius * 2)
        pygame.draw.ellipse(surf, GOLD_COLOR, rect)
        pygame.draw.ellipse(surf, (255, 250, 180), rect, width=2)

class Particle:
    def __init__(self, x, y, color):
        self.x, self.y = x, y
        self.vx = random.uniform(-6, 6)
        self.vy = random.uniform(-9, -2)
        self.size = random.randint(5, 11)
        self.color = color
        self.life = 255

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.45
        self.life -= 12

    def draw(self, surf):
        if self.life > 0:
            pygame.draw.rect(surf, self.color, (int(self.x), int(self.y), self.size, self.size), border_radius=2)

class FloatingText:
    def __init__(self, x, y, text, color, is_big=False):
        self.x = x + random.randint(-15, 15)
        self.y = y
        self.text = text
        self.color = color
        self.vy = -2.2
        self.life = 40
        self.font = font_lg if is_big else font_md

    def update(self):
        self.y += self.vy
        self.life -= 1

    def draw(self, surf):
        if self.life > 0:
            img = self.font.render(self.text, True, self.color)
            surf.blit(img, (int(self.x - img.get_width() // 2), int(self.y)))

# --- ПРОРАБОТАННАЯ ОТРИСОВКА ВСЕХ 14 ГЕРОЕВ ---
def draw_hero(surf, x, y, hero_data, swing_timer):
    c = hero_data["color"]
    wc = hero_data["weapon"]
    hid = hero_data["id"]

    # Тень
    pygame.draw.ellipse(surf, (10, 10, 18), (x - 36, y + 60, 72, 18))

    # Ауры и плащи для высокоуровневых героев (с 7 по 13)
    if hid >= 10:
        # Энергетические крылья / плащ за спиной
        wing_col = GOLD_COLOR if hid == 13 else wc
        pygame.draw.polygon(surf, wing_col, [(x - 15, y + 10), (x - 52, y - 20), (x - 42, y + 35)])
        pygame.draw.polygon(surf, wing_col, [(x + 15, y + 10), (x + 52, y - 20), (x + 42, y + 35)])
    elif hid >= 6:
        pygame.draw.circle(surf, wc, (x, y + 15), 42, width=2)

    # Корпус и броня
    pygame.draw.rect(surf, c, (x - 22, y, 44, 65), border_radius=12)
    pygame.draw.rect(surf, (255, 255, 255), (x - 22, y, 44, 65), width=2, border_radius=12)
    # Нагрудная пластина
    pygame.draw.rect(surf, (30, 35, 55), (x - 14, y + 12, 28, 24), border_radius=5)
    pygame.draw.circle(surf, wc, (x, y + 24), 6)

    # Наплечники для продвинутых бойцов
    if hid >= 5:
        pygame.draw.circle(surf, wc, (x - 24, y + 10), 10)
        pygame.draw.circle(surf, wc, (x + 24, y + 10), 10)

    # Голова
    pygame.draw.circle(surf, c, (x, y - 24), 22)
    pygame.draw.circle(surf, (255, 255, 255), (x, y - 24), 22, width=2)
    # Визор
    pygame.draw.rect(surf, (20, 25, 40), (x - 8, y - 34, 30, 14), border_radius=4)
    eye_col = (255, 215, 0) if hid == 13 else ((255, 50, 50) if hid in [3, 7, 9] else (0, 255, 255))
    pygame.draw.rect(surf, eye_col, (x, y - 30, 16, 6), border_radius=2)

    # Уникальные шлемы, короны и аксессуары
    if hid == 1: # Рога Крушителя
        pygame.draw.polygon(surf, (220, 220, 220), [(x-10, y-42), (x-24, y-58), (x-2, y-45)])
        pygame.draw.polygon(surf, (220, 220, 220), [(x+10, y-42), (x+24, y-58), (x+2, y-45)])
    elif hid == 2: # Сфера Техно-мага
        pygame.draw.circle(surf, (0, 255, 220), (x, y - 55), 8)
    elif hid == 3: # Повязка Ниндзя
        pygame.draw.line(surf, (230, 40, 80), (x - 22, y - 32), (x - 48, y - 22), 6)
        pygame.draw.line(surf, (230, 40, 80), (x - 22, y - 26), (x - 44, y - 10), 5)
    elif hid == 4: # Цилиндр Магната
        pygame.draw.rect(surf, (30, 30, 35), (x - 26, y - 46, 52, 6))
        pygame.draw.rect(surf, (30, 30, 35), (x - 18, y - 74, 36, 28))
        pygame.draw.rect(surf, GOLD_COLOR, (x - 18, y - 52, 36, 6))
    elif hid == 5: # Гребень Кибер-рыцаря
        pygame.draw.polygon(surf, (50, 230, 100), [(x, y - 66), (x - 12, y - 45), (x + 12, y - 45)])
    elif hid == 6: # Корона Бури
        pygame.draw.circle(surf, (255, 255, 255), (x, y - 55), 10, width=3)
    elif hid == 7: # Пламенный венец Пироманта
        pygame.draw.polygon(surf, (255, 180, 0), [(x-16, y-42), (x-10, y-66), (x, y-48), (x+10, y-68), (x+16, y-42)])
    elif hid == 8: # Ледяные шипы Крио-стража
        pygame.draw.polygon(surf, (180, 250, 255), [(x-14, y-44), (x, y-70), (x+14, y-44)])
    elif hid == 9: # Рога Жнеца Бездны
        pygame.draw.polygon(surf, (210, 50, 255), [(x-12, y-42), (x-28, y-68), (x-4, y-46)])
        pygame.draw.polygon(surf, (210, 50, 255), [(x+12, y-42), (x+28, y-68), (x+4, y-46)])
    elif hid in [10, 11, 12]: # Корона Высших Лордов
        pygame.draw.polygon(surf, GOLD_COLOR, [(x-18, y-44), (x-18, y-64), (x-6, y-52), (x, y-68), (x+6, y-52), (x+18, y-64), (x+18, y-44)])
    elif hid == 13: # Божественный Нимб АБСОЛЮТА
        pygame.draw.ellipse(surf, GOLD_COLOR, (x - 28, y - 68, 56, 16), width=4)
        pygame.draw.circle(surf, (255, 255, 255), (x, y - 60), 6)

    # Анимация оружия
    angle = -0.5 if swing_timer <= 0 else 0.75
    wx = x + 10 + int(math.cos(angle) * 44)
    wy = y + 15 + int(math.sin(angle) * 44)
    pygame.draw.line(surf, (210, 210, 220), (x + 5, y + 18), (wx, wy), 7)
    
    if hid in [0, 1, 4, 8]: # Молоты
        pygame.draw.rect(surf, wc, (wx - 15, wy - 19, 30, 38), border_radius=6)
    elif hid in [2, 6, 11, 12]: # Магические сферы и посохи
        pygame.draw.circle(surf, wc, (wx, wy), 17)
        pygame.draw.circle(surf, (255, 255, 255), (wx, wy), 9)
    elif hid in [3, 5, 7, 9, 10, 13]: # Энергетические клинки и косы
        pygame.draw.polygon(surf, wc, [(x + 5, y + 18), (wx + 18, wy - 12), (wx + 24, wy + 12)])

def draw_button(surf, rect, text, bg_col, border_col=(100, 115, 160), text_col=TEXT_COLOR):
    pygame.draw.rect(surf, bg_col, rect, border_radius=14)
    pygame.draw.rect(surf, border_col, rect, width=3, border_radius=14)
    t_surf = font_md.render(text, True, text_col)
    surf.blit(t_surf, (rect.centerx - t_surf.get_width() // 2, rect.centery - t_surf.get_height() // 2))

def draw_slider(surf, rect, title, value):
    pygame.draw.rect(surf, BTN_COLOR, rect, border_radius=12)
    pygame.draw.rect(surf, (100, 115, 160), rect, width=2, border_radius=12)
    
    title_surf = font_sm.render(f"{title}: {int(value * 100)}%", True, TEXT_COLOR)
    surf.blit(title_surf, (rect.x + 15, rect.y + 8))
    
    bar_rect = pygame.Rect(rect.x + 20, rect.y + 45, rect.width - 40, 12)
    pygame.draw.rect(surf, (30, 32, 48), bar_rect, border_radius=6)
    
    fill_width = int(bar_rect.width * value)
    if fill_width > 0:
        fill_rect = pygame.Rect(bar_rect.x, bar_rect.y, fill_width, bar_rect.height)
        pygame.draw.rect(surf, BTN_ACTIVE, fill_rect, border_radius=6)
    
    knob_x = bar_rect.x + fill_width
    pygame.draw.circle(surf, TEXT_COLOR, (knob_x, bar_rect.centery), 10)

game = GameState()
particles, float_texts, coins = [], [], []

shake_frames = 0
barrier_scale = 0
hero_swing = 0
save_timer = 0
current_tab = "upgrades"

# Переменные для плавного скроллинга списка героев
hero_scroll_y = 0.0
is_dragging_heroes = False
drag_start_y = 0
scroll_start_y = 0.0
HERO_ITEM_H = 62
HERO_VIEW_RECT = pygame.Rect(15, 575, 510, 370)
MAX_HERO_SCROLL = max(0, len(HEROES) * HERO_ITEM_H - HERO_VIEW_RECT.height + 10)

app_state = "MAIN_MENU"
prev_state = "MAIN_MENU"
reset_timer = 0.0

barrier_rect = pygame.Rect(195, 175, 290, 275)
pause_btn_rect = pygame.Rect(WIDTH - 68, 20, 48, 48)

tab_upg_rect = pygame.Rect(20, 522, 245, 42)
tab_hero_rect = pygame.Rect(275, 522, 245, 42)
upg_buttons = [
    {"id": "click", "title": "Импульс клика", "rect": pygame.Rect(20, 575, 245, 105)},
    {"id": "auto",  "title": "Авто-дрон (DPS)", "rect": pygame.Rect(275, 575, 245, 105)},
    {"id": "crit",  "title": "Шанс крита (x3)", "rect": pygame.Rect(20, 692, 245, 105)},
    {"id": "gold",  "title": "Ценность монет", "rect": pygame.Rect(275, 692, 245, 105)},
]
rebirth_rect = pygame.Rect(20, 812, 500, 82)

menu_play_rect = pygame.Rect(90, 460, 360, 75)
menu_set_rect = pygame.Rect(90, 555, 360, 70)
menu_quit_rect = pygame.Rect(90, 645, 360, 70)

pause_resume_rect = pygame.Rect(90, 290, 360, 65)
pause_new_rect = pygame.Rect(90, 370, 360, 65)
pause_set_rect = pygame.Rect(90, 450, 360, 65)
pause_main_rect = pygame.Rect(90, 530, 360, 65)

confirm_ok_rect = pygame.Rect(70, 530, 180, 65)
confirm_cancel_rect = pygame.Rect(290, 530, 180, 65)

set_sfx_rect = pygame.Rect(70, 320, 400, 95)
set_mus_rect = pygame.Rect(70, 435, 400, 95)
set_back_rect = pygame.Rect(90, 580, 360, 70)

menu_wall_preview = create_wall_texture(220, 200, BARRIERS[1])

def collect_coin(c):
    if not c.collected:
        c.collected = True
        game.gold += c.value
        audio.play_sfx(audio.coin)
        float_texts.append(FloatingText(c.x, c.y - 10, f"+{fmt(c.value)}$", GOLD_COLOR))

def deal_damage(amount, pos=None, is_click=False):
    global shake_frames, barrier_scale, hero_swing
    is_crit = False
    
    if is_click:
        hero_swing = 8
        if random.randint(1, 100) <= game.crit_chance:
            amount *= 3.0
            is_crit = True
            audio.play_sfx(audio.crit)
        else:
            audio.play_sfx(audio.hit)
            
        shake_frames = 7 if is_crit else 3
        barrier_scale = -12
        
        _, b_color, _, _ = game.get_barrier_info()
        px, py = pos if pos else barrier_rect.center
        for _ in range(10 if is_crit else 5):
            particles.append(Particle(px, py, b_color))
        
        if random.random() < 0.28:
            val = max(1, math.ceil(game.max_hp * 0.04 * game.gold_mult))
            coins.append(Coin(px, py, val))

        txt_col = CRIT_COLOR if is_crit else TEXT_COLOR
        prefix = "КРИТ! -" if is_crit else "-"
        float_texts.append(FloatingText(px, py - 20, f"{prefix}{fmt(amount)}", txt_col, is_crit))

    game.hp -= amount
    
    if game.hp <= 0:
        audio.play_sfx(audio.break_wall)
        total_reward = math.ceil((game.max_hp * 0.25) * game.gold_mult)
        coin_count = random.randint(5, 8)
        val_per_coin = max(1, total_reward // coin_count)
        
        for _ in range(coin_count):
            coins.append(Coin(barrier_rect.centerx, barrier_rect.centery, val_per_coin))
            
        game.stage += 1
        _, b_color, _, _ = game.get_barrier_info()
        for _ in range(30):
            particles.append(Particle(barrier_rect.centerx, barrier_rect.centery, b_color))
            
        shake_frames = 14
        game.setup_barrier()

def render_gameplay(ox, oy):
    screen.fill(BG_COLOR)
    pygame.draw.line(screen, (45, 50, 80), (0, 510), (WIDTH, 510), 4)

    # Верхняя панель
    pygame.draw.rect(screen, PANEL_COLOR, (0, 0, WIDTH, 118))
    pygame.draw.line(screen, (60, 65, 100), (0, 118), (WIDTH, 118), 3)

    gold_surf = font_lg.render(f"Золото: {fmt(game.gold)} $", True, GOLD_COLOR)
    reb_surf = font_sm.render(
        f"Перерождений: {game.rebirths} [{game.rebirth_title}]  |  Кристаллы: {fmt(game.gems)}",
        True, GEM_COLOR
    )
    dps_surf = font_xs.render(
        f"Клик: {fmt(game.click_dmg)}  |  Авто: {fmt(game.auto_dps)}/с  |  Крит: {game.crit_chance}%  |  Сила: x{fmt(game.rebirth_power_mult)}",
        True, (190, 200, 230)
    )

    screen.blit(gold_surf, (18, 10))
    screen.blit(reb_surf, (18, 52))
    screen.blit(dps_surf, (18, 84))

    # Кнопка Паузы
    pygame.draw.rect(screen, BTN_COLOR, pause_btn_rect, border_radius=10)
    pygame.draw.rect(screen, (110, 125, 175), pause_btn_rect, width=2, border_radius=10)
    pygame.draw.rect(screen, TEXT_COLOR, (pause_btn_rect.x + 14, pause_btn_rect.y + 12, 6, 24), border_radius=2)
    pygame.draw.rect(screen, TEXT_COLOR, (pause_btn_rect.x + 28, pause_btn_rect.y + 12, 6, 24), border_radius=2)

    # Название стены
    b_name, _, _, _ = game.get_barrier_info()
    title_surf = font_md.render(f"Уровень {game.stage}: {b_name}", True, TEXT_COLOR)
    screen.blit(title_surf, (WIDTH // 2 - title_surf.get_width() // 2, 130))

    # Отрисовка Героя
    active_hero_data = game.hero
    draw_hero(screen, 95, 360, active_hero_data, hero_swing)
    h_name_surf = font_xs.render(active_hero_data["name"], True, active_hero_data["color"])
    screen.blit(h_name_surf, (95 - h_name_surf.get_width() // 2, 440))

    # Стена и трещины
    draw_rect = barrier_rect.inflate(barrier_scale, barrier_scale).move(ox, oy)
    scaled_wall = pygame.transform.smoothscale(game.wall_surf, (draw_rect.width, draw_rect.height))
    screen.blit(scaled_wall, draw_rect.topleft)

    hp_ratio = max(0.0, game.hp / game.max_hp)
    visible_cracks = int((1.0 - hp_ratio) * len(game.cracks))
    for i in range(visible_cracks):
        p1, p2, p3 = game.cracks[i]
        pygame.draw.line(screen, (20, 20, 25), (p1[0] + ox, p1[1] + oy), (p2[0] + ox, p2[1] + oy), 4)
        pygame.draw.line(screen, (20, 20, 25), (p2[0] + ox, p2[1] + oy), (p3[0] + ox, p3[1] + oy), 3)

    # Полоска HP
    bar_bg = pygame.Rect(195, 462, 290, 30)
    pygame.draw.rect(screen, (35, 35, 45), bar_bg, border_radius=6)
    if hp_ratio > 0:
        pygame.draw.rect(screen, (220, 50, 60), (bar_bg.x, bar_bg.y, int(290 * hp_ratio), 30), border_radius=6)
    pygame.draw.rect(screen, (90, 95, 120), bar_bg, width=2, border_radius=6)

    hp_txt = font_sm.render(f"{fmt(max(0, game.hp))} / {fmt(game.max_hp)} HP", True, TEXT_COLOR)
    screen.blit(hp_txt, (bar_bg.centerx - hp_txt.get_width() // 2, bar_bg.centery - hp_txt.get_height() // 2))

    # Вкладки
    pygame.draw.rect(screen, BTN_EQUIPPED if current_tab == "upgrades" else BTN_COLOR, tab_upg_rect, border_radius=8)
    pygame.draw.rect(screen, BTN_EQUIPPED if current_tab == "heroes" else BTN_COLOR, tab_hero_rect, border_radius=8)
    
    t_u = font_md.render("УЛУЧШЕНИЯ", True, TEXT_COLOR)
    t_h = font_md.render(f"ГЕРОИ ({len(game.owned_heroes)}/{len(HEROES)})", True, TEXT_COLOR)
    screen.blit(t_u, (tab_upg_rect.centerx - t_u.get_width() // 2, tab_upg_rect.centery - t_u.get_height() // 2))
    screen.blit(t_h, (tab_hero_rect.centerx - t_h.get_width() // 2, tab_hero_rect.centery - t_h.get_height() // 2))

    if current_tab == "upgrades":
        for b in upg_buttons:
            uid = b["id"]
            rect = b["rect"]
            cost = game.get_cost(uid)
            is_max = (uid == "crit" and game.crit_lvl * 3 >= 60)
            can_buy = (game.gold >= cost) and not is_max

            color = BTN_ACTIVE if can_buy else (BTN_DISABLED if is_max else BTN_COLOR)
            pygame.draw.rect(screen, color, rect, border_radius=12)
            pygame.draw.rect(screen, (90, 100, 140), rect, width=2, border_radius=12)

            if uid == "click": val_str = f"Ур. {game.click_lvl}"
            elif uid == "auto": val_str = f"Ур. {game.auto_lvl}"
            elif uid == "crit": val_str = "МАКС (60%)" if is_max else f"База: {game.crit_lvl * 3}%"
            elif uid == "gold": val_str = f"Множ: x{fmt(game.gold_mult)}"

            cost_str = "МАКС" if is_max else f"Цена: {fmt(cost)} $"

            screen.blit(font_md.render(b["title"], True, TEXT_COLOR), (rect.x + 12, rect.y + 10))
            screen.blit(font_sm.render(val_str, True, (210, 220, 240)), (rect.x + 12, rect.y + 42))
            screen.blit(font_md.render(cost_str, True, GOLD_COLOR if can_buy else (150, 150, 160)), (rect.x + 12, rect.y + 68))

        # Кнопка ПЕРЕРОЖДЕНИЯ
        pending_gems = game.get_pending_gems()
        req_stage = game.get_next_rebirth_req()
        p_col = (115, 35, 165) if pending_gems > 0 else BTN_DISABLED
        pygame.draw.rect(screen, p_col, rebirth_rect, border_radius=12)
        pygame.draw.rect(screen, REBIRTH_COLOR if pending_gems > 0 else (70, 70, 90), rebirth_rect, width=2, border_radius=12)

        if pending_gems > 0:
            r_line1 = f"ПЕРЕРОЖДЕНИЕ (#{game.rebirths + 1})"
            r_line2 = f"Получить +{fmt(pending_gems)} крист. и множитель урона!"
        else:
            r_line1 = f"ПЕРЕРОЖДЕНИЕ НЕДОСТУПНО"
            r_line2 = f"Требуется {req_stage} уровень стены (сейчас {game.stage})"

        s1 = font_md.render(r_line1, True, TEXT_COLOR)
        s2 = font_xs.render(r_line2, True, GEM_COLOR if pending_gems > 0 else (160, 160, 175))
        screen.blit(s1, (rebirth_rect.centerx - s1.get_width() // 2, rebirth_rect.y + 14))
        screen.blit(s2, (rebirth_rect.centerx - s2.get_width() // 2, rebirth_rect.y + 48))

    elif current_tab == "heroes":
        # Ограничиваем область отрисовки для плавного скролла героев
        screen.set_clip(HERO_VIEW_RECT)
        for i, h in enumerate(HEROES):
            y_pos = HERO_VIEW_RECT.y + i * HERO_ITEM_H - int(hero_scroll_y)
            if y_pos + 56 < HERO_VIEW_RECT.y or y_pos > HERO_VIEW_RECT.bottom:
                continue
            h_rect = pygame.Rect(20, y_pos, 488, 55)
            owned = h["id"] in game.owned_heroes
            equipped = (game.current_hero == h["id"])
            can_buy = (not owned) and (game.gold >= h["cost"])

            bg = BTN_EQUIPPED if equipped else (BTN_COLOR if owned else (BTN_ACTIVE if can_buy else BTN_DISABLED))
            pygame.draw.rect(screen, bg, h_rect, border_radius=10)
            pygame.draw.rect(screen, h["color"], h_rect, width=2, border_radius=10)
            pygame.draw.circle(screen, h["color"], (h_rect.x + 25, h_rect.centery), 15)
            
            screen.blit(font_sm.render(h["name"], True, TEXT_COLOR), (h_rect.x + 50, h_rect.y + 6))
            screen.blit(font_xs.render(h["desc"], True, (210, 220, 240)), (h_rect.x + 50, h_rect.y + 30))

            if equipped: st_txt, st_col = "ВЫБРАН", GEM_COLOR
            elif owned: st_txt, st_col = "ВЫБРАТЬ", TEXT_COLOR
            else: st_txt, st_col = f"{fmt(h['cost'])} $", GOLD_COLOR if can_buy else (140, 140, 150)
            
            st_surf = font_sm.render(st_txt, True, st_col)
            screen.blit(st_surf, (h_rect.right - st_surf.get_width() - 12, h_rect.centery - st_surf.get_height() // 2))
        screen.set_clip(None)

        # Полоса прокрутки справа от героев
        if MAX_HERO_SCROLL > 0:
            sb_bg = pygame.Rect(514, HERO_VIEW_RECT.y, 6, HERO_VIEW_RECT.height)
            pygame.draw.rect(screen, (35, 38, 55), sb_bg, border_radius=3)
            thumb_h = max(30, int(HERO_VIEW_RECT.height * (HERO_VIEW_RECT.height / (len(HEROES) * HERO_ITEM_H))))
            thumb_y = HERO_VIEW_RECT.y + int((hero_scroll_y / MAX_HERO_SCROLL) * (HERO_VIEW_RECT.height - thumb_h))
            pygame.draw.rect(screen, GEM_COLOR, (514, thumb_y, 6, thumb_h), border_radius=3)

    for c in coins: c.draw(screen)
    for p in particles: p.draw(screen)
    for ft in float_texts: ft.draw(screen)

running = True
while running:
    dt = clock.tick(60) / 1000.0
    
    if app_state == "PLAYING":
        save_timer += dt
        if save_timer >= 5.0:
            game.save()
            save_timer = 0

        if game.auto_dps > 0:
            deal_damage(game.auto_dps * dt, is_click=False)

        mx, my = pygame.mouse.get_pos()
        if pygame.mouse.get_pressed()[0]:
            for c in coins:
                if math.hypot(c.x - mx, c.y - my) < c.radius + 28:
                    collect_coin(c)

        for c in coins[:]:
            if c.update(): collect_coin(c)
            if c.collected: coins.remove(c)

        for p in particles[:]:
            p.update()
            if p.life <= 0: particles.remove(p)

        for ft in float_texts[:]:
            ft.update()
            if ft.life <= 0: float_texts.remove(ft)

    elif app_state == "CONFIRM_RESET":
        if reset_timer > 0:
            reset_timer -= dt

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            game.save()
            running = False

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if app_state == "PLAYING": app_state = "PAUSED"
                elif app_state == "PAUSED": app_state = "PLAYING"
                elif app_state == "SETTINGS": app_state = prev_state
                elif app_state == "CONFIRM_RESET": app_state = "PAUSED"

        elif event.type == pygame.MOUSEWHEEL:
            if app_state == "PLAYING" and current_tab == "heroes":
                hero_scroll_y = max(0.0, min(MAX_HERO_SCROLL, hero_scroll_y - event.y * 40))

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos

            if app_state == "MAIN_MENU":
                if menu_play_rect.collidepoint(mx, my):
                    audio.play_sfx(audio.click_ui)
                    app_state = "PLAYING"
                elif menu_set_rect.collidepoint(mx, my):
                    audio.play_sfx(audio.click_ui)
                    prev_state = "MAIN_MENU"
                    app_state = "SETTINGS"
                elif menu_quit_rect.collidepoint(mx, my):
                    game.save()
                    running = False

            elif app_state == "PAUSED":
                if pause_resume_rect.collidepoint(mx, my):
                    audio.play_sfx(audio.click_ui)
                    app_state = "PLAYING"
                elif pause_new_rect.collidepoint(mx, my):
                    audio.play_sfx(audio.click_ui)
                    reset_timer = 3.0  # 3 секунды защиты таймера
                    app_state = "CONFIRM_RESET"
                elif pause_set_rect.collidepoint(mx, my):
                    audio.play_sfx(audio.click_ui)
                    prev_state = "PAUSED"
                    app_state = "SETTINGS"
                elif pause_main_rect.collidepoint(mx, my):
                    audio.play_sfx(audio.click_ui)
                    game.save()
                    app_state = "MAIN_MENU"

            elif app_state == "CONFIRM_RESET":
                if confirm_cancel_rect.collidepoint(mx, my):
                    audio.play_sfx(audio.click_ui)
                    app_state = "PAUSED"
                elif confirm_ok_rect.collidepoint(mx, my) and reset_timer <= 0:
                    audio.play_sfx(audio.buy)
                    game.reset_game()
                    app_state = "PLAYING"

            elif app_state == "SETTINGS":
                if set_back_rect.collidepoint(mx, my):
                    audio.play_sfx(audio.click_ui)
                    game.save()
                    app_state = prev_state

            elif app_state == "PLAYING":
                if pause_btn_rect.collidepoint(mx, my):
                    audio.play_sfx(audio.click_ui)
                    app_state = "PAUSED"
                    continue

                coin_clicked = False
                for c in coins:
                    if math.hypot(c.x - mx, c.y - my) < c.radius + 25:
                        collect_coin(c)
                        coin_clicked = True

                if barrier_rect.collidepoint(mx, my) and not coin_clicked:
                    deal_damage(game.click_dmg, pos=(mx, my), is_click=True)

                if tab_upg_rect.collidepoint(mx, my):
                    current_tab = "upgrades"
                elif tab_hero_rect.collidepoint(mx, my):
                    current_tab = "heroes"

                if current_tab == "upgrades":
                    for b in upg_buttons:
                        if b["rect"].collidepoint(mx, my):
                            uid = b["id"]
                            cost = game.get_cost(uid)
                            if uid == "crit" and game.crit_lvl * 3 >= 60: continue
                            if game.gold >= cost:
                                game.gold -= cost
                                audio.play_sfx(audio.buy)
                                if uid == "click": game.click_lvl += 1
                                elif uid == "auto": game.auto_lvl += 1
                                elif uid == "crit": game.crit_lvl += 1
                                elif uid == "gold": game.gold_lvl += 1
                                game.save()

                    if rebirth_rect.collidepoint(mx, my):
                        if game.rebirth():
                            audio.play_sfx(audio.break_wall)
                            float_texts.append(FloatingText(WIDTH // 2, HEIGHT // 2, f"ПЕРЕРОЖДЕНИЕ #{game.rebirths}!", REBIRTH_COLOR, True))

                elif current_tab == "heroes" and HERO_VIEW_RECT.collidepoint(mx, my):
                    is_dragging_heroes = True
                    drag_start_y = my
                    scroll_start_y = hero_scroll_y

        elif event.type == pygame.MOUSEMOTION:
            if is_dragging_heroes and app_state == "PLAYING" and current_tab == "heroes":
                dy = drag_start_y - event.pos[1]
                hero_scroll_y = max(0.0, min(MAX_HERO_SCROLL, scroll_start_y + dy))

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if is_dragging_heroes:
                mx, my = event.pos
                # Если палец почти не сдвинулся — засчитываем как клик по герою
                if abs(my - drag_start_y) < 10 and HERO_VIEW_RECT.collidepoint(mx, my):
                    for i, h in enumerate(HEROES):
                        y_pos = HERO_VIEW_RECT.y + i * HERO_ITEM_H - int(hero_scroll_y)
                        h_rect = pygame.Rect(20, y_pos, 488, 55)
                        if h_rect.collidepoint(mx, my):
                            hid = h["id"]
                            if hid in game.owned_heroes:
                                game.current_hero = hid
                                audio.play_sfx(audio.coin)
                                game.save()
                            elif game.gold >= h["cost"]:
                                game.gold -= h["cost"]
                                game.owned_heroes.append(hid)
                                game.current_hero = hid
                                audio.play_sfx(audio.buy)
                                game.save()
                is_dragging_heroes = False

    if app_state == "SETTINGS" and pygame.mouse.get_pressed()[0]:
        mx, my = pygame.mouse.get_pos()
        bar_w = set_sfx_rect.width - 40
        
        sfx_bar_rect = pygame.Rect(set_sfx_rect.x + 20, set_sfx_rect.y + 45, bar_w, 12)
        if set_sfx_rect.collidepoint(mx, my):
            rel_x = max(0, min(bar_w, mx - sfx_bar_rect.x))
            audio.sfx_vol = round(rel_x / bar_w, 2)
            game.save()

        mus_bar_rect = pygame.Rect(set_mus_rect.x + 20, set_mus_rect.y + 45, bar_w, 12)
        if set_mus_rect.collidepoint(mx, my):
            rel_x = max(0, min(bar_w, mx - mus_bar_rect.x))
            audio.music_vol = round(rel_x / bar_w, 2)
            audio.update_music()
            game.save()

    ox = random.randint(-5, 5) if shake_frames > 0 and app_state == "PLAYING" else 0
    oy = random.randint(-5, 5) if shake_frames > 0 and app_state == "PLAYING" else 0
    if shake_frames > 0: shake_frames -= 1
    if barrier_scale < 0: barrier_scale += 2
    if hero_swing > 0: hero_swing -= 1

    if app_state == "MAIN_MENU":
        screen.fill(BG_COLOR)
        for y in range(0, HEIGHT, 60):
            pygame.draw.line(screen, (22, 24, 38), (0, y), (WIDTH, y), 2)

        t_shadow = font_xl.render("WALL CRUSHER", True, (0, 0, 0))
        t_main = font_xl.render("WALL CRUSHER", True, GOLD_COLOR)
        screen.blit(t_shadow, (WIDTH // 2 - t_main.get_width() // 2 + 4, 84))
        screen.blit(t_main, (WIDTH // 2 - t_main.get_width() // 2, 80))
        screen.blit(font_sm.render("КРУШИ СТЕНЫ • КАЧАЙ ГЕРОЕВ • ПЕРЕРОЖДАЙСЯ", True, GEM_COLOR), (WIDTH // 2 - 210, 145))

        screen.blit(menu_wall_preview, (210, 210))
        draw_hero(screen, 145, 315, game.hero, 0)

        draw_button(screen, menu_play_rect, "ИГРАТЬ", BTN_ACTIVE, (80, 220, 140))
        draw_button(screen, menu_set_rect, "НАСТРОЙКИ", BTN_COLOR)
        draw_button(screen, menu_quit_rect, "ВЫХОД", (130, 45, 55), (200, 80, 90))

    elif app_state == "PLAYING":
        render_gameplay(ox, oy)

    elif app_state == "PAUSED":
        render_gameplay(0, 0)
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((10, 12, 20, 215))
        screen.blit(overlay, (0, 0))

        p_title = font_xl.render("ПАУЗА", True, TEXT_COLOR)
        screen.blit(p_title, (WIDTH // 2 - p_title.get_width() // 2, 200))

        draw_button(screen, pause_resume_rect, "ПРОДОЛЖИТЬ", BTN_ACTIVE, (80, 220, 140))
        draw_button(screen, pause_new_rect, "НАЧАТЬ НОВУЮ ИГРУ", (160, 50, 70), (220, 90, 110))
        draw_button(screen, pause_set_rect, "НАСТРОЙКИ", BTN_COLOR)
        draw_button(screen, pause_main_rect, "В ГЛАВНОЕ МЕНЮ", (120, 50, 75), (190, 90, 115))

    elif app_state == "CONFIRM_RESET":
        render_gameplay(0, 0)
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((12, 14, 24, 235))
        screen.blit(overlay, (0, 0))

        modal_rect = pygame.Rect(45, 290, 450, 320)
        pygame.draw.rect(screen, (28, 32, 52), modal_rect, border_radius=18)
        pygame.draw.rect(screen, (100, 115, 160), modal_rect, width=3, border_radius=18)

        q1 = font_lg.render("НОВАЯ ИГРА", True, CRIT_COLOR)
        q2 = font_md.render("Точно ли вы этого хотите?", True, TEXT_COLOR)
        q3 = font_sm.render("Весь прогресс и перерождения сбросятся!", True, (190, 190, 210))
        
        screen.blit(q1, (modal_rect.centerx - q1.get_width() // 2, modal_rect.y + 25))
        screen.blit(q2, (modal_rect.centerx - q2.get_width() // 2, modal_rect.y + 80))
        screen.blit(q3, (modal_rect.centerx - q3.get_width() // 2, modal_rect.y + 120))

        if reset_timer > 0:
            ok_col = BTN_DISABLED
            ok_text = f"ОК ({math.ceil(reset_timer)})"
            ok_border = (70, 70, 80)
        else:
            ok_col = (200, 50, 60)
            ok_text = "ОК"
            ok_border = (255, 100, 110)

        pygame.draw.rect(screen, ok_col, confirm_ok_rect, border_radius=12)
        pygame.draw.rect(screen, ok_border, confirm_ok_rect, width=3, border_radius=12)
        t_ok = font_md.render(ok_text, True, TEXT_COLOR if reset_timer <= 0 else (130, 130, 140))
        screen.blit(t_ok, (confirm_ok_rect.centerx - t_ok.get_width() // 2, confirm_ok_rect.centery - t_ok.get_height() // 2))

        draw_button(screen, confirm_cancel_rect, "ОТМЕНА", BTN_ACTIVE, (80, 220, 140))

    elif app_state == "SETTINGS":
        if prev_state == "PAUSED": render_gameplay(0, 0)
        else: screen.fill(BG_COLOR)
        
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((12, 14, 24, 235))
        screen.blit(overlay, (0, 0))

        s_title = font_xl.render("НАСТРОЙКИ", True, GOLD_COLOR)
        screen.blit(s_title, (WIDTH // 2 - s_title.get_width() // 2, 210))

        draw_slider(screen, set_sfx_rect, "ГРОМКОСТЬ ЭФФЕКТОВ", audio.sfx_vol)
        draw_slider(screen, set_mus_rect, "ГРОМКОСТЬ МУЗЫКИ", audio.music_vol)
        draw_button(screen, set_back_rect, "НАЗАД", BTN_EQUIPPED)

    pygame.display.flip()

pygame.quit()
sys.exit()
