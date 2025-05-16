import os
import pygame
import random
import json
import sys
from typing import Dict
from datetime import datetime, timedelta

# Inicialização
pygame.init()
pygame.mixer.init()

# Configurações de tela (fullscreen para celular)
SCREEN_INFO = pygame.display.Info()
SCREEN_WIDTH, SCREEN_HEIGHT = SCREEN_INFO.current_w, SCREEN_INFO.current_h
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN | pygame.SCALED)
pygame.display.set_caption("Duelo no Oeste: Showdown Extremo")
clock = pygame.time.Clock()
FPS = 60

# Constantes
ASSETS_DIR = "assets"
SPRITE_SIZE = (200, 250)
BULLET_SIZE = (30, 10)
BASE_BULLET_SPEED = 25
CHAO_Y = SCREEN_HEIGHT * 0.90  # 90% da tela
MAX_ROUNDS = 10

# Cores
WHITE = (255, 255, 255)
RED = (200, 50, 50)
BLUE = (50, 50, 200)
GOLD = (255, 215, 0)
GREEN = (50, 200, 50)
BROWN = (139, 69, 19)
BLACK_ALPHA = (0, 0, 0, 180)  # Preto com transparência

class AssetManager:
    @staticmethod
    def load_assets() -> Dict[str, any]:
        """Carrega todos os assets organizados por pastas"""
        assets = {
            # Imagens
            "bg_menu": AssetManager._load_image("menu_bg.jpg", "backgrounds"),
            "bg_game": AssetManager._load_image("game_bg.jpg", "backgrounds"),

            # Sprites
            "player1": {
                "idle": AssetManager._load_image("cowboy_idle.png", "sprites"),
                "shoot": AssetManager._load_image("cowboy_shoot.png", "sprites"),
                "dead": AssetManager._load_image("cowboy_dead.png", "sprites")
            },
            "player2": {
                "idle": AssetManager._load_image("enemy_idle.png", "sprites"),
                "shoot": AssetManager._load_image("enemy_shoot.png", "sprites"),
                "dead": AssetManager._load_image("enemy_dead.png", "sprites")
            },

            # Sons
            "sounds": {
                "shot": AssetManager._load_sound("shot.wav"),
                "win": AssetManager._load_sound("win.wav"),
                "lose": AssetManager._load_sound("lose.wav"),
                "click": AssetManager._load_sound("click.wav"),
                "achievement": AssetManager._load_sound("achievement.wav")
            },
            "music": {
                "duel": AssetManager._load_music("duel.mp3"),
                "achievements": AssetManager._load_music("achievements.mp3")
            },

            # UI
            "bullet": AssetManager._load_image("bullet.png", "ui")
        }
        return assets

    @staticmethod
    def _load_image(filename: str, subfolder: str) -> pygame.Surface:
        """Carrega imagem com fallback"""
        try:
            path = os.path.join(ASSETS_DIR, "images", subfolder, filename)
            img = pygame.image.load(path).convert_alpha()
            return pygame.transform.scale(img, (SPRITE_SIZE if subfolder == "sprites" 
                                         else BULLET_SIZE if filename == "bullet.png"
                                         else (SCREEN_WIDTH, SCREEN_HEIGHT)))
        except:
            surf = pygame.Surface((SPRITE_SIZE if subfolder == "sprites" 
                                 else BULLET_SIZE if filename == "bullet.png"
                                 else (SCREEN_WIDTH, SCREEN_HEIGHT)), pygame.SRCALPHA)
            surf.fill(RED if "cowboy" in filename else BLUE if "enemy" in filename else WHITE)
            return surf

    @staticmethod
    def _load_sound(filename: str) -> pygame.mixer.Sound:
        """Carrega efeitos sonoros com fallback silencioso"""
        try:
            path = os.path.join(ASSETS_DIR, "sounds", filename)
            sound = pygame.mixer.Sound(path)
            sound.set_volume(0.7)
            return sound
        except:
            return pygame.mixer.Sound(buffer=bytes([0]*1000))

    @staticmethod
    def _load_music(filename: str) -> str:
        """Retorna caminho da música"""
        path = os.path.join(ASSETS_DIR, "music", filename)
        return path if os.path.exists(path) else ""

class Game:
    def __init__(self):
        self.assets = AssetManager.load_assets()
        self.font_large = pygame.font.Font(None, 72)
        self.font_medium = pygame.font.Font(None, 48)
        self.font_small = pygame.font.Font(None, 36)

        # Estado do jogo
        self.reset_game_state()
        self.setup_controls()

        # Conquistas
        self.achievements = {
            "round_5": False,
            "round_10": False,
            "fast_winner": False,
            "perfect_10": False,
            "no_miss": False,
            "first_blood": False,
            "pvp_winner": False,
            "daily_win": False,
            "daily_5wins": False,
            "daily_10shots": False
        }

        # Conquistas diárias
        self.daily_achievements = {
            "last_play_date": None,
            "daily_wins": 0,
            "daily_shots": 0
        }

        self.load_achievements()
        self.check_daily_reset()

        # Música
        self.music_volume = 0.5
        self.current_music = ""

    def reset_game_state(self):
        """Reseta todo o estado do jogo"""
        self.game_mode = None  # 'arcade', 'pvp'
        self.game_state = "menu"
        self.arcade_score = 0
        self.arcade_round = 1
        self.arcade_wins = 0
        self.pvp_score = [0, 0]  # [player1, player2]
        self.reset_duel_state()

    def reset_duel_state(self):
        """Reseta o estado do duelo atual"""
        self.player1_state = "idle"
        self.player2_state = "idle"
        self.player1_pos = [SCREEN_WIDTH*0.2, CHAO_Y - SPRITE_SIZE[1]]
        self.player2_pos = [SCREEN_WIDTH*0.8 - SPRITE_SIZE[0], CHAO_Y - SPRITE_SIZE[1]]
        self.bullets = []
        self.last_shot = 0
        self.winner = None
        self.duel_start_time = 0
        self.shots_fired = 0
        self.shots_hit = 0
        self.last_shot_time = 0

    def setup_controls(self):
        """Configura controles touch para celular"""
        btn_width = SCREEN_WIDTH // 2.5
        btn_height = SCREEN_HEIGHT // 8
        spacing = 20

        # Posiciona os botões verticalmente centralizados
        start_y = SCREEN_HEIGHT // 3

        self.controls = {
            # Menu - botões organizados com espaçamento
            "arcade": pygame.Rect(SCREEN_WIDTH//2 - btn_width//2, start_y, btn_width, btn_height),
            "pvp": pygame.Rect(SCREEN_WIDTH//2 - btn_width//2, start_y + btn_height + spacing, btn_width, btn_height),
            "achievements": pygame.Rect(SCREEN_WIDTH//2 - btn_width//2, start_y + 2*(btn_height + spacing), btn_width, btn_height),

            # Duelo
            "shoot_left": pygame.Rect(0, SCREEN_HEIGHT-btn_height, btn_width, btn_height),
            "shoot_right": pygame.Rect(SCREEN_WIDTH-btn_width, SCREEN_HEIGHT-btn_height, btn_width, btn_height)
        }

    def check_daily_reset(self):
        """Verifica se precisa resetar as conquistas diárias"""
        today = datetime.now().date()
        last_play = self.daily_achievements.get("last_play_date")

        if last_play:
            try:
                last_play_date = datetime.strptime(last_play, "%Y-%m-%d").date()
                if last_play_date < today:
                    self.reset_daily_achievements()
            except:
                self.reset_daily_achievements()
        else:
            self.reset_daily_achievements()

        self.daily_achievements["last_play_date"] = today.strftime("%Y-%m-%d")

    def reset_daily_achievements(self):
        """Reseta as conquistas diárias"""
        self.daily_achievements["daily_wins"] = 0
        self.daily_achievements["daily_shots"] = 0
        self.achievements["daily_win"] = False
        self.achievements["daily_5wins"] = False
        self.achievements["daily_10shots"] = False
        self.save_achievements()

    # --- Sistema de Áudio ---
    def play_music(self, track: str):
        """Toca uma música específica"""
        if track in self.assets["music"] and self.assets["music"][track]:
            if self.current_music != track:
                pygame.mixer.music.stop()
                pygame.mixer.music.load(self.assets["music"][track])
                pygame.mixer.music.set_volume(self.music_volume)
                pygame.mixer.music.play(-1)
                self.current_music = track

    def stop_music(self):
        """Para a música atual"""
        pygame.mixer.music.stop()
        self.current_music = ""

    def play_sound(self, sound: str):
        """Toca um efeito sonoro"""
        if sound in self.assets["sounds"]:
            self.assets["sounds"][sound].play()

    # --- Lógica do Jogo ---
    def start_arcade_mode(self):
        """Inicia o modo arcade com 10 rodadas"""
        self.reset_game_state()
        self.game_mode = "arcade"
        self.start_duel()

    def start_pvp_mode(self):
        """Inicia o modo Player vs Player"""
        self.reset_game_state()
        self.game_mode = "pvp"
        self.start_duel()

    def start_duel(self):
        """Inicia um novo duelo"""
        self.reset_duel_state()
        self.game_state = "countdown"
        self.countdown = 3
        self.countdown_start = pygame.time.get_ticks()
        self.play_music("duel")
        self.play_sound("click")

    def calculate_difficulty(self) -> float:
        """Retorna multiplicador de dificuldade (1.0 a 10.0) - extremamente difícil"""
        if self.game_mode == "arcade":
            # Aumenta a dificuldade exponencialmente
            return min(10.0, 1.0 + (self.arcade_round * 0.9))
        return 1.0

    def calculate_ai_reaction_time(self) -> int:
        """Tempo de reação da IA em ms (extremamente rápido conforme as rodadas)"""
        if self.game_mode == "arcade":
            # No round 1: 400ms, round 5: 200ms, round 10: 100ms (quase impossível)
            return max(100, 500 - (self.arcade_round * 40))
        return 1000

    def fire_shot(self, player: int):
        """Dispara um tiro com cooldown"""
        now = pygame.time.get_ticks()
        if now - self.last_shot < 300:  # Cooldown de 300ms
            return

        self.last_shot = now
        self.shots_fired += 1
        self.daily_achievements["daily_shots"] += 1
        self.check_daily_achievements()

        speed = BASE_BULLET_SPEED * self.calculate_difficulty()

        if player == 1:
            self.bullets.append({
                "x": self.player1_pos[0] + SPRITE_SIZE[0],
                "y": self.player1_pos[1] + SPRITE_SIZE[1]//2,
                "speed": speed,
                "player": 1
            })
            self.player1_state = "shoot"
            self.last_shot_time = now
        else:
            self.bullets.append({
                "x": self.player2_pos[0],
                "y": self.player2_pos[1] + SPRITE_SIZE[1]//2,
                "speed": -speed,
                "player": 2
            })
            self.player2_state = "shoot"

        self.play_sound("shot")

    def update(self):
        """Atualiza a lógica do jogo"""
        now = pygame.time.get_ticks()

        # Contagem regressiva
        if self.game_state == "countdown":
            elapsed = now - self.countdown_start
            self.countdown = max(0, 3 - int(elapsed / 1000))

            if elapsed >= 3000:
                self.game_state = "duel"
                self.duel_start_time = now
                self.play_sound("click")

        # Durante o duelo
        elif self.game_state == "duel":
            # Atualiza balas
            for bullet in self.bullets[:]:
                bullet["x"] += bullet["speed"]

                # Verifica colisões
                if bullet["player"] == 1 and bullet["x"] > self.player2_pos[0]:
                    self.player2_state = "dead"
                    self.winner = 1
                    self.shots_hit += 1
                    self.end_duel()
                elif bullet["player"] == 2 and bullet["x"] < self.player1_pos[0] + SPRITE_SIZE[0]:
                    self.player1_state = "dead"
                    self.winner = 2
                    self.end_duel()

                # Remove balas fora da tela
                if bullet["x"] < 0 or bullet["x"] > SCREEN_WIDTH:
                    self.bullets.remove(bullet)

            # IA no modo arcade - extremamente rápida
            if self.game_mode == "arcade":
                reaction_time = self.calculate_ai_reaction_time()
                if (now - self.duel_start_time > 100 and  # Espera mínimo de 300ms
                    now - self.last_shot_time > reaction_time and  # Tempo de reação ultra rápido
                    random.random() < 0.03 * self.calculate_difficulty()):  # Alta chance de atirar
                    self.fire_shot(2)

            # Reseta animação de tiro
            if now - self.last_shot > 200:
                if self.player1_state != "dead":
                    self.player1_state = "idle"
                if self.player2_state != "dead":
                    self.player2_state = "idle"

        # Durante o resultado
        elif self.game_state == "result":
            # Atualiza balas para continuar animação
            for bullet in self.bullets[:]:
                bullet["x"] += bullet["speed"]
                if bullet["x"] < 0 or bullet["x"] > SCREEN_WIDTH:
                    self.bullets.remove(bullet)

    def end_duel(self):
        """Finaliza o duelo atual"""
        self.game_state = "result"

        if self.winner == 1:
            self.play_sound("win")
            self.daily_achievements["daily_wins"] += 1
            self.check_daily_achievements()

            if self.game_mode == "arcade":
                self.arcade_wins += 1
                self.check_achievements()
            elif self.game_mode == "pvp":
                self.pvp_score[0] += 1
                if self.pvp_score[0] >= 5:  # Melhor de 5
                    self.unlock_achievement("pvp_winner")
        else:
            self.play_sound("lose")
            if self.game_mode == "pvp":
                self.pvp_score[1] += 1

    def handle_round_transition(self):
        """Gerencia transição entre rodadas"""
        if self.game_mode == "arcade":
            if self.winner == 1:
                self.arcade_round += 1
                if self.arcade_round <= MAX_ROUNDS:
                    self.start_duel()
                else:
                    self.stop_music()
                    self.game_state = "menu"
            else:
                self.start_duel()
        elif self.game_mode == "pvp":
            if max(self.pvp_score) < 5:  # Melhor de 5
                self.start_duel()
            else:
                self.stop_music()
                self.game_state = "menu"

    # --- Sistema de Conquistas ---
    def check_achievements(self):
        """Verifica conquistas ao vencer"""
        # Conquistas de progresso
        if self.arcade_round >= 5 and not self.achievements["round_5"]:
            self.unlock_achievement("round_5")

        if self.arcade_round >= 10 and not self.achievements["round_10"]:
            self.unlock_achievement("round_10")

        if self.arcade_wins >= 10 and not self.achievements["perfect_10"]:
            self.unlock_achievement("perfect_10")

        # Conquistas de habilidade
        duel_time = pygame.time.get_ticks() - self.duel_start_time
        if duel_time < 1000 and self.winner == 1 and not self.achievements["fast_winner"]:
            self.unlock_achievement("fast_winner")

        if self.shots_hit == self.shots_fired and self.shots_fired > 0 and self.winner == 1 and not self.achievements["no_miss"]:
            self.unlock_achievement("no_miss")

        if self.arcade_wins == 1 and not self.achievements["first_blood"]:
            self.unlock_achievement("first_blood")

    def check_daily_achievements(self):
        """Verifica conquistas diárias"""
        if self.daily_achievements["daily_wins"] >= 1 and not self.achievements["daily_win"]:
            self.unlock_achievement("daily_win")

        if self.daily_achievements["daily_wins"] >= 5 and not self.achievements["daily_5wins"]:
            self.unlock_achievement("daily_5wins")

        if self.daily_achievements["daily_shots"] >= 10 and not self.achievements["daily_10shots"]:
            self.unlock_achievement("daily_10shots")

    def unlock_achievement(self, name: str):
        """Desbloqueia uma conquista com efeitos"""
        if name in self.achievements and not self.achievements[name]:
            self.achievements[name] = True
            self.save_achievements()
            self.play_sound("achievement")

    def load_achievements(self):
        """Carrega conquistas salvas"""
        try:
            with open("achievements.json", "r") as f:
                data = json.load(f)
                self.achievements = data.get("achievements", self.achievements)
                self.daily_achievements = data.get("daily_achievements", self.daily_achievements)
        except:
            self.save_achievements()

    def save_achievements(self):
        """Salva conquistas em arquivo"""
        with open("achievements.json", "w") as f:
            json.dump({
                "achievements": self.achievements,
                "daily_achievements": self.daily_achievements
            }, f)

    def show_achievements(self):
        """Mostra tela de conquistas"""
        self.game_state = "achievements"
        self.play_music("achievements")

    # --- Renderização ---
    def draw(self):
        """Renderiza todos os elementos"""
        # Fundo
        if self.game_state == "menu":
            screen.blit(self.assets["bg_menu"], (0, 0))
            self.draw_menu()
        elif self.game_state == "achievements":
            screen.blit(self.assets["bg_game"], (0, 0))
            self.draw_achievements()
        else:
            screen.blit(self.assets["bg_game"], (0, 0))
            self.draw_game_elements()

        pygame.display.flip()

    def draw_menu(self):
        """Renderiza o menu principal com botões melhor organizados"""
        title = self.font_large.render("DUELO NO OESTE", True, GOLD)
        screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 100))

        # Botões coloridos com texto centralizado
        for btn_name, btn_rect in [(k, v) for k, v in self.controls.items() if k in ["arcade", "pvp", "achievements"]]:
            color = {
                "arcade": GREEN,
                "pvp": BLUE,
                "achievements": GOLD
            }[btn_name]

            pygame.draw.rect(screen, color, btn_rect, 0, 10)
            pygame.draw.rect(screen, WHITE, btn_rect, 2, 10)  # Borda

            text = self.font_medium.render(
                {"arcade": "Arcade (IMPOSSÍVEL)", 
                 "pvp": "PvP (2 jogadores)", 
                 "achievements": "Conquistas"}[btn_name], 
                True, WHITE
            )
            screen.blit(text, (btn_rect.centerx - text.get_width()//2, 
                             btn_rect.centery - text.get_height()//2))

    def draw_game_elements(self):
        """Renderiza elementos do jogo"""
        # Personagens
        screen.blit(self.assets["player1"][self.player1_state], self.player1_pos)
        screen.blit(self.assets["player2"][self.player2_state], self.player2_pos)

        # Balas
        for bullet in self.bullets:
            screen.blit(self.assets["bullet"], (bullet["x"], bullet["y"]))

        # Interface
        if self.game_state == "countdown":
            self.draw_countdown()
        elif self.game_state == "result":
            self.draw_result()

        # Controles mobile
        if self.game_state == "duel":
            self.draw_touch_controls()

        # Placar no modo PvP
        if self.game_mode == "pvp" and self.game_state == "duel":
            score_text = self.font_medium.render(f"{self.pvp_score[0]} - {self.pvp_score[1]}", True, WHITE)
            screen.blit(score_text, (SCREEN_WIDTH//2 - score_text.get_width()//2, 50))

        # Rodada no modo arcade
        if self.game_mode == "arcade" and self.game_state == "duel":
            round_text = self.font_medium.render(f"Rodada: {self.arcade_round}/{MAX_ROUNDS}", True, WHITE)
            screen.blit(round_text, (SCREEN_WIDTH//2 - round_text.get_width()//2, 50))

            # Mostra dificuldade
            diff_text = self.font_small.render(f"Dificuldade: {self.calculate_difficulty():.1f}/10.0", True, RED)
            screen.blit(diff_text, (SCREEN_WIDTH//2 - diff_text.get_width()//2, 100))

    def draw_countdown(self):
        """Renderiza contagem regressiva"""
        if self.countdown > 0:
            text = self.font_large.render(str(self.countdown), True, WHITE)
            screen.blit(text, (SCREEN_WIDTH//2 - text.get_width()//2, SCREEN_HEIGHT//3))
        else:
            text = self.font_large.render("ATIRE!", True, RED)
            screen.blit(text, (SCREEN_WIDTH//2 - text.get_width()//2, SCREEN_HEIGHT//3))

    def draw_result(self):
        """Renderiza tela de resultado"""
        # Fundo escurecido
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill(BLACK_ALPHA)
        screen.blit(overlay, (0, 0))

        # Textos
        if self.winner == 1:
            title = self.font_large.render("VITÓRIA!", True, GOLD)
        else:
            title = self.font_large.render("DERROTA!", True, RED)
        screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, SCREEN_HEIGHT//3))

        if self.game_mode == "arcade":
            round_text = self.font_medium.render(f"Rodada: {self.arcade_round}/{MAX_ROUNDS}", True, WHITE)
            screen.blit(round_text, (SCREEN_WIDTH//2 - round_text.get_width()//2, SCREEN_HEIGHT//2))

            # Mostra precisão
            accuracy = (self.shots_hit / self.shots_fired * 100) if self.shots_fired > 0 else 0
            acc_text = self.font_small.render(f"Precisão: {accuracy:.1f}%", True, WHITE)
            screen.blit(acc_text, (SCREEN_WIDTH//2 - acc_text.get_width()//2, SCREEN_HEIGHT//2 + 50))
        elif self.game_mode == "pvp":
            score_text = self.font_medium.render(f"Placar: {self.pvp_score[0]} - {self.pvp_score[1]}", True, WHITE)
            screen.blit(score_text, (SCREEN_WIDTH//2 - score_text.get_width()//2, SCREEN_HEIGHT//2))

        hint = self.font_small.render("Toque para continuar", True, WHITE)
        screen.blit(hint, (SCREEN_WIDTH//2 - hint.get_width()//2, SCREEN_HEIGHT - 150))

    def draw_touch_controls(self):
        """Renderiza controles touch"""
        btn_width = SCREEN_WIDTH // 3
        btn_height = SCREEN_HEIGHT // 6

        # Botões de tiro semi-transparentes
        s = pygame.Surface((btn_width, btn_height), pygame.SRCALPHA)
        s.fill((0, 0, 0, 150))
        screen.blit(s, (0, SCREEN_HEIGHT-btn_height))
        screen.blit(s, (SCREEN_WIDTH-btn_width, SCREEN_HEIGHT-btn_height))

        shoot_text = self.font_small.render("ATIRAR", True, WHITE)
        screen.blit(shoot_text, (btn_width//2 - shoot_text.get_width()//2, SCREEN_HEIGHT-btn_height//2))
        screen.blit(shoot_text, (SCREEN_WIDTH-btn_width//2 - shoot_text.get_width()//2, SCREEN_HEIGHT-btn_height//2))

    def draw_achievements(self):
        """Renderiza tela de conquistas"""
        # Fundo escurecido
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill(BLACK_ALPHA)
        screen.blit(overlay, (0, 0))

        title = self.font_large.render("CONQUISTAS", True, GOLD)
        screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 50))

        # Data atual
        today = datetime.now().strftime("%d/%m/%Y")
        date_text = self.font_small.render(f"Hoje: {today}", True, WHITE)
        screen.blit(date_text, (SCREEN_WIDTH - date_text.get_width() - 20, 20))

        achievements = [
            ("Primeiro Sangue", "first_blood", "Primeira vitória"),
            ("Rodada 5", "round_5", "Chegue à 5ª rodada"),
            ("Rodada 10", "round_10", "Complete todas as rodadas"),
            ("Gatilho Rápido", "fast_winner", "Vença em <1 segundo"),
            ("Precisão", "no_miss", "Vença sem errar tiros"),
            ("Perfeição", "perfect_10", "Vença todas as rodadas"),
            ("Campeão PvP", "pvp_winner", "Vença uma partida PvP"),
            ("Vitória Diária", "daily_win", "Vença 1 duelo hoje"),
            ("5 Vitórias Diárias", "daily_5wins", "Vença 5 duelos hoje"),
            ("10 Tiros Diários", "daily_10shots", "Dispare 10 tiros hoje")
        ]

        for i, (name, key, desc) in enumerate(achievements):
            y_pos = 120 + i * 60
            color = GREEN if self.achievements[key] else RED

            # Ícone
            pygame.draw.circle(screen, color, (80, y_pos + 25), 15)

            # Textos
            name_text = self.font_medium.render(name, True, color)
            desc_text = self.font_small.render(desc, True, WHITE)

            screen.blit(name_text, (110, y_pos))
            screen.blit(desc_text, (110, y_pos + 30))

            # Progresso para conquistas diárias
            if key == "daily_5wins" and not self.achievements[key]:
                progress = min(5, self.daily_achievements["daily_wins"])
                progress_text = self.font_small.render(f"{progress}/5", True, WHITE)
                screen.blit(progress_text, (SCREEN_WIDTH - 100, y_pos + 15))

            if key == "daily_10shots" and not self.achievements[key]:
                progress = min(10, self.daily_achievements["daily_shots"])
                progress_text = self.font_small.render(f"{progress}/10", True, WHITE)
                screen.blit(progress_text, (SCREEN_WIDTH - 100, y_pos + 15))

        # Instrução para voltar
        back_text = self.font_small.render("Toque para voltar", True, WHITE)
        screen.blit(back_text, (SCREEN_WIDTH//2 - back_text.get_width()//2, SCREEN_HEIGHT - 50))

    # --- Controles ---
    def handle_events(self):
        """Processa todos os eventos"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            # Controles touch
            if event.type == pygame.FINGERDOWN or event.type == pygame.MOUSEBUTTONDOWN:
                pos = (event.x * SCREEN_WIDTH, event.y * SCREEN_HEIGHT) if hasattr(event, 'x') else pygame.mouse.get_pos()
                self.handle_touch(pos)

            # Teclado
            if event.type == pygame.KEYDOWN:
                if self.game_state == "menu":
                    if event.key == pygame.K_1:
                        self.start_arcade_mode()
                    elif event.key == pygame.K_2:
                        self.start_pvp_mode()
                    elif event.key == pygame.K_3:
                        self.show_achievements()
                    elif event.key == pygame.K_ESCAPE:
                        return False

                elif self.game_state == "duel":
                    if event.key == pygame.K_f:
                        self.fire_shot(1)
                    elif event.key == pygame.K_j:
                        self.fire_shot(2)

                elif self.game_state == "result" and event.key == pygame.K_RETURN:
                    self.handle_round_transition()

                elif self.game_state == "achievements" and event.key == pygame.K_ESCAPE:
                    self.game_state = "menu"
                    self.stop_music()

        return True

    def handle_touch(self, pos):
        """Processa toques na tela"""
        if self.game_state == "menu":
            if self.controls["arcade"].collidepoint(pos):
                self.start_arcade_mode()
            elif self.controls["pvp"].collidepoint(pos):
                self.start_pvp_mode()
            elif self.controls["achievements"].collidepoint(pos):
                self.show_achievements()

        elif self.game_state == "duel":
            if self.controls["shoot_left"].collidepoint(pos):
                self.fire_shot(1)
            elif self.controls["shoot_right"].collidepoint(pos):
                self.fire_shot(2)

        elif self.game_state == "result":
            self.handle_round_transition()  # Toque em qualquer lugar para continuar

        elif self.game_state == "achievements":
            self.game_state = "menu"  # Toque em qualquer lugar para voltar
            self.stop_music()

def main():
    """Ponto de entrada principal"""
    game = Game()
    running = True

    while running:
        running = game.handle_events()
        game.update()
        game.draw()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()