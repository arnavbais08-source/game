# racing_game.py
import pygame
import sys
import math
from pathlib import Path

pygame.init()
WIDTH, HEIGHT = 1500, 900
SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
CLOCK = pygame.time.Clock()
FONT = pygame.font.SysFont("Algerian", 30)

# ---- Config ----
CAR_IMAGE = "newcar.png"      # must point to right-facing car image
TRACK_IMAGE = "newtrack.png"  # large track image
FPS = 60

# physics
ACCELERATION = 0.20
REVERSE_ACCEL = 0.012
MAX_SPEED = 3.0
FRICTION = 0.05
TURN_SPEED_BASE = 2.0  # degrees per frame at low speed

# checkpoints (list of rects in track coordinates). We'll make a simple 3 checkpoint lap.
# You should set these roughly on your track (x,y,w,h) in pixels relative to the top-left of track.png
CHECKPOINTS = [
    (1750, 230, 20),#start checkpoint(x,y,radius)
    
    (1990, 1100, 20),#mid checkpoint
    (850, 1220, 20),#end checkpoint

]

FINISH_LINE = pygame.Rect(1100, 300, 5, 110)  # where laps are counted; should overlap checkpoint[0]

# ---- Helper functions ----
def point_in_circle(px, py, cx, cy, r):
    return (px - cx) ** 2 + (py - cy) ** 2 <= r ** 2
def load_image(path, colorkey=None):
    img = pygame.image.load(path).convert_alpha()
    if colorkey is not None:
        img.set_colorkey(colorkey)
    return img

def blit_center(surface, img, pos):
    r = img.get_rect(center=pos)
    surface.blit(img, r)

# ---- Car class ----
class Car:
    def __init__(self, x, y, image):
        self.x = x  # world coords (track image coords)
        self.y = y
        self.angle = 0.0  # degrees, 0 pointing right
        self.speed = 0.0
        self.image_orig = image
        self.image = image
        self.rect = self.image.get_rect(center=(x, y))
        self.check_idx = 0  # next checkpoint index to trigger
        self.laps = 0
        self.best_lap = None
        self.lap_start_time = None
        self.on_finish = False


    def update(self, dt, keys):
        # dt in seconds
        # Controls: Up/Down accelerate/brake, Left/Right turn
        forward = keys[pygame.K_UP] or keys[pygame.K_w]
        backward = keys[pygame.K_DOWN] or keys[pygame.K_s]
        left = keys[pygame.K_LEFT] or keys[pygame.K_a]
        right = keys[pygame.K_RIGHT] or keys[pygame.K_d]

        # Acceleration
        if forward:
            self.speed += ACCELERATION
        elif backward:
            self.speed -= REVERSE_ACCEL
        else:
            # friction
            if self.speed > 0:
                self.speed = max(0, self.speed - FRICTION)
            elif self.speed < 0:
                self.speed = min(0, self.speed + FRICTION)

        # Clamp speed
        self.speed = max(-MAX_SPEED/2, min(MAX_SPEED, self.speed))

        # Turning depends on speed (sharper at low speed)
        turn_speed = TURN_SPEED_BASE * (1.0 if abs(self.speed) < 1 else (MAX_SPEED / max(abs(self.speed), 1)))
        if left:
            self.angle += turn_speed * (1 if self.speed >= 0 else -1)
        if right:
            self.angle -= turn_speed * (1 if self.speed >= 0 else -1)

        # Movement
        rad = math.radians(self.angle)
        self.x += math.cos(rad) * self.speed * dt * 60  # scale by 60 to make frame-rate independent feel like Scratch
        self.y -= math.sin(rad) * self.speed * dt * 60

        # Update rotated image
        self.image = pygame.transform.rotozoom(self.image_orig, self.angle, 1.0)
        self.rect = self.image.get_rect(center=(self.x, self.y))

    def world_pos(self):
        return (self.x, self.y)

# ---- Main game class ----
class RacingGame:
    def __init__(self):
        base = Path(__file__).parent
        # load images
        self.track_img = load_image(str(base / TRACK_IMAGE))
        self.track_w, self.track_h = self.track_img.get_size()
        car_img = load_image(str(base / CAR_IMAGE))
        # starting position: pick near first checkpoint or configurable pos
        start_x, start_y = FINISH_LINE.center
        self.car = Car(start_x, start_y + 10, car_img)  # start slightly after finish
        self.camera_x = max(0, self.car.x - WIDTH // 2)
        self.camera_y = max(0, self.car.y - HEIGHT // 2)
        self.running = True
        self.play_state = "menu"  # 'menu', 'playing', 'finished'
         
        
        self.checkpoints = CHECKPOINTS
        self.finish_rect = FINISH_LINE
        self.font = FONT
    def car_on_track(self):
    # Car position in track coordinates
     x = int(self.car.x)
     y = int(self.car.y)

    # Safety check: if car is outside the image → treat as off-track
     if x < 0 or y < 0 or x >= self.track_w or y >= self.track_h:
         return False

     pixel_color = self.track_img.get_at((x, y))[:3]

    # Dark road color range (tuned for your road)
     road_min = (80, 80, 80)
     road_max = (160, 160, 160)

     return all(road_min[i] <= pixel_color[i] <= road_max[i] for i in range(3))
        

    def reset(self):
        start_x, start_y = FINISH_LINE.center
        self.car = Car(start_x, start_y + 10, load_image(CAR_IMAGE))
        self.camera_x = max(0, self.car.x - WIDTH // 2)
        self.camera_y = max(0, self.car.y - HEIGHT // 2)
        self.play_state = "playing"

    def update_camera(self):
        # keep camera centered on car but clamped to track bounds
        self.camera_x = int(self.car.x - WIDTH // 2)
        self.camera_y = int(self.car.y - HEIGHT // 2)
        self.camera_x = max(0, min(self.camera_x, self.track_w - WIDTH))
        self.camera_y = max(0, min(self.camera_y, self.track_h - HEIGHT))
    def check_checkpoints(self):
     next_idx = self.car.check_idx

     # Check checkpoints in order
     if next_idx < len(self.checkpoints):
         cx, cy, r = self.checkpoints[next_idx]

         if point_in_circle(self.car.x, self.car.y, cx, cy, r):
             self.car.check_idx += 1
             print("Checkpoint Cleared")

     # All checkpoints passed → check finish line
     elif next_idx == len(self.checkpoints):

         if self.finish_rect.collidepoint(self.car.x, self.car.y):

             # Count lap only once per crossing
             if not self.car.on_finish:
                 self.car.laps += 1
                 self.car.check_idx = 0
                 self.car.on_finish = True

                 if self.car.laps >= 3:
                     self.play_state = "finished"

         else:
             # Car left finish line → allow next lap
             self.car.on_finish = False                


    def draw_ui(self):
        def draw_ui(self):
         s_lap = f"Laps: {self.car.laps}"
         SCREEN.blit(self.font.render(s_lap, True, (255,255,255)), (10,10))
    def run(self):
        while self.running:
            dt = CLOCK.tick(FPS) / 1000.0
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    self.running = False
                if ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_ESCAPE:
                        self.running = False
                    if ev.key == pygame.K_SPACE and self.play_state == "menu":
                        self.reset()
                    if ev.key == pygame.K_r and self.play_state == "finished":
                        self.reset()

            keys = pygame.key.get_pressed()
            if self.play_state == "playing":
             self.car.update(dt, keys)

    # Off-track penalty
            if not self.car_on_track():
             self.car.speed *= 0.8  # gradual slowdown
            if abs(self.car.speed) > 1.5:
             self.car.speed -= 0.1 if self.car.speed > 0 else -0.1  # extra drag

            self.update_camera()
            self.check_checkpoints()


            # draw track portion based on camera
            SCREEN.fill((0,0,0))
            # Blit the portion of the track
            track_view = pygame.Rect(self.camera_x, self.camera_y, WIDTH, HEIGHT)
            SCREEN.blit(self.track_img, (0,0), track_view)

            # draw checkpoints (debugging) - optional: comment out for release
            for cx, cy, r in self.checkpoints:
             if (self.camera_x < cx < self.camera_x + WIDTH and
             self.camera_y < cy < self.camera_y + HEIGHT):

              pygame.draw.circle(
              SCREEN,
              (255, 165, 0),   # orange filled circle
              (int(cx - self.camera_x), int(cy - self.camera_y)),
               r
               )
        

            # finish line debug
            if track_view.colliderect(self.finish_rect):
                localf = pygame.Rect(self.finish_rect.x - self.camera_x, self.finish_rect.y - self.camera_y, self.finish_rect.w, self.finish_rect.h)
                pygame.draw.rect(SCREEN, (255,0,0), localf)

            # draw car at camera-relative position
            car_screen_pos = (self.car.x - self.camera_x, self.car.y - self.camera_y)
            car_rect = self.car.image.get_rect(center=car_screen_pos)
            SCREEN.blit(self.car.image, car_rect)

            # UI
            self.draw_ui()

            # overlay state screens
            if self.play_state == "menu":
                text_surf = self.font.render("Press SPACE to start", True, (0, 0, 0))
                text_rect = text_surf.get_rect(center=(WIDTH//2, HEIGHT//2))
                SCREEN.blit(text_surf, text_rect)
            elif self.play_state == "finished":
                s = self.font.render("Finished! Press R to retry", True, (0,0,0))
                SCREEN.blit(s, (WIDTH//2 - s.get_width()//2, HEIGHT//2 - 20))

            pygame.display.flip()

        pygame.quit()
        sys.exit()

# ---- Run ----
if __name__ == "__main__":
    # check assets exist
    base = Path(__file__).parent
    for p in (base / CAR_IMAGE, base / TRACK_IMAGE):
        if not p.exists():
            print(f"Missing asset: {p.name}. Place {p.name} in the same folder.")
            sys.exit(1)
    game = RacingGame()
    game.run()  