#!/usr/bin/env python3
"""Celestine Chord — neon four-lane rhythm-tap arcade for ElbowOS."""
from __future__ import annotations

import math
import os
import random
import subprocess
import sys

import pygame

W, H = 1080, 1920
FPS = 30
TITLE = "CELESTINE CHORD"
HANDLE = "x.com/ElbowOS"
VOID = (6, 10, 28)
NAVY = (10, 22, 58)
INK = (8, 16, 42)
ICE = (168, 236, 255)
CYAN = (64, 220, 255)
MINT = (96, 255, 196)
LILAC = (196, 150, 255)
GOLD = (255, 214, 92)
PEARL = (240, 248, 255)
ROSE = (255, 92, 168)
LANE_COLS = (CYAN, MINT, LILAC, GOLD)
KEYS = (pygame.K_d, pygame.K_f, pygame.K_j, pygame.K_k)
HIT_Y = 1580
NOTE_H = 36
JUDGE = 54


class Note:
    __slots__ = ("lane", "y", "chord", "hit")

    def __init__(self, lane: int, y: float, chord: bool = False):
        self.lane, self.y, self.chord, self.hit = lane, y, chord, False


class Spark:
    __slots__ = ("x", "y", "vx", "vy", "life", "col", "r")

    def __init__(self, x, y, vx, vy, life, col, r=5):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.life, self.col, self.r = life, col, r


class Game:
    def __init__(self, record: bool):
        self.record = record
        self.surf = pygame.Surface((W, H))
        self.clock = pygame.time.Clock()
        self.font_lg = pygame.font.Font(None, 62)
        self.font_md = pygame.font.Font(None, 42)
        self.font_sm = pygame.font.Font(None, 28)
        self.score = 0
        self.reset()

    def reset(self) -> None:
        self.t = 0.0
        self.combo = 0
        self.best = 0
        self.speed = 620.0
        self.notes: list[Note] = []
        self.sparks: list[Spark] = []
        self.flash = [0.0, 0.0, 0.0, 0.0]
        self.pulse = 0.0
        self.spawn_acc = 0.0
        self.beat = 0.48
        self.msg = ""
        self.msg_t = 0.0
        self.stars = [[random.uniform(0, W), random.uniform(0, H),
                       random.uniform(0.6, 2.4)] for _ in range(70)]
        self.lanes_x = [180, 380, 580, 780]
        self.lane_w = 160

    def burst(self, x, y, col, n=14) -> None:
        for _ in range(n):
            a = random.random() * math.tau
            spd = random.uniform(60, 380)
            self.sparks.append(Spark(x, y, math.cos(a) * spd, math.sin(a) * spd,
                                     random.uniform(0.16, 0.4), col, random.randint(3, 8)))

    def spawn_pack(self) -> None:
        r = random.random()
        if r < 0.18:
            lanes = random.sample(range(4), 2)
            for ln in lanes:
                self.notes.append(Note(ln, -40, True))
        elif r < 0.26:
            lanes = random.sample(range(4), 3)
            for ln in lanes:
                self.notes.append(Note(ln, -40, True))
        else:
            self.notes.append(Note(random.randrange(4), -40, False))

    def tap(self, lane: int) -> None:
        self.flash[lane] = 0.18
        best, best_d = None, 1e9
        for n in self.notes:
            if n.hit or n.lane != lane:
                continue
            d = abs(n.y - HIT_Y)
            if d < best_d:
                best, best_d = n, d
        if best is None or best_d > JUDGE * 2.2:
            self.combo = 0
            self.msg, self.msg_t = "MISS", 0.35
            return
        best.hit = True
        if best_d < 18:
            pts, tag = 50, "PERFECT"
        elif best_d < JUDGE:
            pts, tag = 30, "GOOD"
        else:
            pts, tag = 12, "LATE"
        self.combo += 1
        self.best = max(self.best, self.combo)
        bonus = 20 if best.chord else 0
        self.score += (pts + bonus) * max(1, self.combo // 4 + 1)
        self.msg, self.msg_t = ("CHORD " + tag) if best.chord else tag, 0.4
        cx = self.lanes_x[lane] + self.lane_w // 2
        self.burst(cx, HIT_Y, LANE_COLS[lane], 18 if best.chord else 10)
        self.pulse = 0.22

    def autoplay(self) -> None:
        pending = [n for n in self.notes if not n.hit and abs(n.y - HIT_Y) < 28]
        for n in pending:
            self.tap(n.lane)

    def handle(self, ev) -> None:
        if ev.type != pygame.KEYDOWN:
            return
        if ev.key == pygame.K_r:
            self.score = 0
            self.reset()
            return
        for i, k in enumerate(KEYS):
            if ev.key == k:
                self.tap(i)

    def update(self, dt: float) -> None:
        self.t += dt
        self.msg_t = max(0.0, self.msg_t - dt)
        self.pulse = max(0.0, self.pulse - dt)
        for i in range(4):
            self.flash[i] = max(0.0, self.flash[i] - dt)
        self.speed = 620 + min(280, self.t * 14)
        self.beat = max(0.28, 0.48 - self.t * 0.008)
        self.spawn_acc += dt
        if self.spawn_acc >= self.beat:
            self.spawn_acc -= self.beat
            self.spawn_pack()
        live: list[Note] = []
        for n in self.notes:
            n.y += self.speed * dt
            if n.y > HIT_Y + 90:
                if not n.hit:
                    self.combo = 0
                    self.msg, self.msg_t = "DROP", 0.28
                continue
            if not n.hit:
                live.append(n)
        self.notes = live
        if self.record:
            self.autoplay()
        keep: list[Spark] = []
        for sp in self.sparks:
            sp.life -= dt
            if sp.life <= 0:
                continue
            sp.x += sp.vx * dt
            sp.y += sp.vy * dt
            keep.append(sp)
        self.sparks = keep
        for st in self.stars:
            st[1] += (18 + st[2] * 22) * dt
            if st[1] > H:
                st[1] = 0
                st[0] = random.uniform(0, W)

    def draw(self, s: pygame.Surface) -> None:
        s.fill(VOID)
        pygame.draw.rect(s, NAVY, (0, 0, W, 200))
        pygame.draw.rect(s, INK, (0, 1760, W, 160))
        for x, y, r in self.stars:
            pygame.draw.circle(s, (40, 80, 140), (int(x), int(y)), max(1, int(r)))
        for i, lx in enumerate(self.lanes_x):
            col = LANE_COLS[i]
            pygame.draw.rect(s, (14, 24, 52), (lx, 210, self.lane_w, 1540), border_radius=18)
            pygame.draw.rect(s, col, (lx, 210, self.lane_w, 1540), 3, border_radius=18)
            if self.flash[i] > 0:
                glow = pygame.Surface((self.lane_w, 1540), pygame.SRCALPHA)
                glow.fill((*col, int(70 * self.flash[i] / 0.18)))
                s.blit(glow, (lx, 210))
            hy = HIT_Y
            pygame.draw.rect(s, col, (lx + 8, hy - 8, self.lane_w - 16, 22), border_radius=8)
            pygame.draw.rect(s, PEARL, (lx + 18, hy - 4, self.lane_w - 36, 14), 2, border_radius=6)
            lab = self.font_md.render("DFJK"[i], True, col)
            s.blit(lab, lab.get_rect(center=(lx + self.lane_w // 2, 1820)))
        for n in self.notes:
            lx = self.lanes_x[n.lane]
            col = LANE_COLS[n.lane]
            y = int(n.y)
            if n.chord:
                pygame.draw.rect(s, PEARL, (lx + 12, y - 8, self.lane_w - 24, NOTE_H + 16), border_radius=12)
                pygame.draw.rect(s, col, (lx + 22, y, self.lane_w - 44, NOTE_H), border_radius=10)
            else:
                pygame.draw.rect(s, col, (lx + 22, y, self.lane_w - 44, NOTE_H), border_radius=10)
                pygame.draw.rect(s, PEARL, (lx + 34, y + 8, self.lane_w - 68, 10), border_radius=4)
        for sp in self.sparks:
            pygame.draw.circle(s, sp.col, (int(sp.x), int(sp.y)), max(1, int(sp.r * sp.life * 2.8)))
        if self.pulse > 0:
            ring = pygame.Surface((W, H), pygame.SRCALPHA)
            pygame.draw.rect(ring, (180, 240, 255, int(50 * self.pulse / 0.22)), (0, HIT_Y - 40, W, 80))
            s.blit(ring, (0, 0))
        title = self.font_lg.render(TITLE, True, ICE)
        s.blit(title, title.get_rect(center=(W // 2, 52)))
        handle = self.font_sm.render(HANDLE, True, LILAC)
        s.blit(handle, handle.get_rect(center=(W // 2, 102)))
        hud = self.font_md.render(f"SCORE  {self.score}    COMBO x{self.combo}", True, MINT)
        s.blit(hud, hud.get_rect(center=(W // 2, 152)))
        if self.msg_t > 0:
            mc = GOLD if "PERFECT" in self.msg or "CHORD" in self.msg else ROSE if self.msg in ("MISS", "DROP") else ICE
            m = self.font_lg.render(self.msg, True, mc)
            s.blit(m, m.get_rect(center=(W // 2, 1688)))
        hint = self.font_sm.render("D F J K tap lanes   R reset   x.com/ElbowOS", True, CYAN)
        s.blit(hint, hint.get_rect(center=(W // 2, H - 36)))

    def play(self) -> None:
        screen = pygame.display.set_mode((W, H))
        pygame.display.set_caption(TITLE)
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT or (ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE):
                    running = False
                else:
                    self.handle(ev)
            self.update(dt)
            self.draw(self.surf)
            screen.blit(self.surf, (0, 0))
            pygame.display.flip()

    def record_mp4(self, path: str) -> None:
        cmd = [
            "ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
            "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-crf", "20", "-preset", "fast", "-movflags", "+faststart", path,
        ]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        frames = FPS * 15
        for i in range(frames):
            self.update(1.0 / FPS)
            self.draw(self.surf)
            proc.stdin.write(pygame.image.tostring(self.surf, "RGB"))
            if i % 30 == 0:
                print(f"frame {i}/{frames}", flush=True)
        proc.stdin.close()
        rc = proc.wait()
        if rc != 0:
            raise SystemExit(f"ffmpeg failed: {rc}")
        print("wrote", path)


def main() -> None:
    record = "--record" in sys.argv or os.environ.get("ELBOWOS_RECORD") == "1"
    play = "--play" in sys.argv
    if record or not play:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    pygame.init()
    pygame.font.init()
    g = Game(record or not play)
    if record or not play:
        out = os.environ.get("ELBOWOS_MP4", "/home/workdir/artifacts/CELESTINE_CHORD_ElbowOS.mp4")
        g.record_mp4(out)
    else:
        g.play()
    pygame.quit()


if __name__ == "__main__":
    main()
