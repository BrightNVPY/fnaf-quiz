import pygame
import json
import random
import time
import os
import sys
import traceback

def _crash_handler(exc_type, exc_value, exc_tb):
    print("\n=== THE GAME CRASHED — FULL ERROR BELOW ===\n", flush=True)
    traceback.print_exception(exc_type, exc_value, exc_tb)
    try:
        input("\nPress Enter to close this window...")
    except Exception:
        pass

sys.excepthook = _crash_handler

print(">>> FNAF QUIZ STARTING - THIS IS THE NEW BUILD WITH DEBUG PRINTS <<<", flush=True)

pygame.init()
pygame.mixer.init()

# --- PATH HELPERS (for PyInstaller --onefile bundling) ---

def resource_path(relative_path):
    """Path to a bundled asset (img/, sound/, questions.json).
    Works both when run as a normal .py script and when run as a
    PyInstaller --onefile exe (which extracts data to sys._MEIPASS)."""
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

def writable_path(relative_path):
    """Path to a file we need to READ/WRITE at runtime and have persist
    next to the exe (log.txt). Must NOT point into the temp _MEIPASS
    folder, since that gets wiped when the exe closes."""
    if getattr(sys, "frozen", False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

WIDTH, HEIGHT = 1000, 650
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("FNAF Quiz")

font = pygame.font.SysFont("consolas", 24)
title_font = pygame.font.SysFont("consolas", 50, bold=True)
scary_font = pygame.font.SysFont("couriernew", 28, bold=True)
huge_font = pygame.font.SysFont("impact", 120, bold=True)

WHITE, GRAY, BLACK, RED, GREEN, YELLOW = (255, 255, 255), (40, 40, 40), (0, 0, 0), (200, 0, 0), (0, 200, 0), (255, 255, 0)

shake_intensity = 0
shake_duration = 0

def trigger_shake(intensity, duration):
    global shake_intensity, shake_duration
    shake_intensity = intensity
    shake_duration = duration

def get_shake_offset():
    global shake_duration
    if shake_duration > 0:
        shake_duration -= 1
        return random.randint(-shake_intensity, shake_intensity), random.randint(-shake_intensity, shake_intensity)
    return 0, 0

def load_questions():
    try:
        with open(resource_path("questions.json"), "r", encoding="utf-8") as f:
            raw_questions = json.load(f)

        processed_questions = []
        for q in raw_questions:
            # Determine the index of the correct answer (0=A, 1=B, 2=C, 3=D)
            correct_letter = q["answer"].strip().upper()
            correct_idx = ord(correct_letter) - ord('A')
            correct_text = q["options"][correct_idx]

            # Shuffle options copy
            new_options = q["options"][:]
            random.shuffle(new_options)

            # Re-map the correct letter to match the new option position
            new_correct_idx = new_options.index(correct_text)
            new_answer_letter = chr(65 + new_correct_idx)

            processed_questions.append({
                "question": q["question"],
                "options": new_options,
                "answer": new_answer_letter
            })

        return processed_questions  # Keeps original question sequence intact

    except Exception as e:
        return [{"question": "Error: questions.json missing", "options": ["A", "B", "C", "D"], "answer": "A"}]

def get_history():
    log_path = writable_path("log.txt")
    if not os.path.exists(log_path):
        return []
    with open(log_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        return [line.strip() for line in lines if line.strip()]

def get_high_score():
    logs = get_history()
    best = 0
    for log in logs:
        try:
            parts = log.split("Score: ")[1].split("/")[0]
            score_val = int(parts)
            if score_val > best:
                best = score_val
        except:
            continue
    return best

def load_characters(phase):
    path = resource_path(f"img/phase{phase}/")
    suffix = "2.png" if phase == 2 else "1.png"
    try:
        f = pygame.transform.scale(pygame.image.load(os.path.join(path, f"Freddy{suffix}")), (180, 280))
        b = pygame.transform.scale(pygame.image.load(os.path.join(path, f"Bonnie{suffix}")), (180, 280))
        c = pygame.transform.scale(pygame.image.load(os.path.join(path, f"Chica{suffix}")), (180, 280))
        return (f, b, c)
    except:
        s = pygame.Surface((180, 280)); s.fill((50, 50, 50))
        return (s, s, s)

print("DEBUG base path:", getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__))), flush=True)
print("DEBUG resource_path('img/stage.png') ->", resource_path("img/stage.png"), "exists:", os.path.exists(resource_path("img/stage.png")), flush=True)
try:
    stage = pygame.transform.scale(pygame.image.load(resource_path("img/stage.png")), (WIDTH, HEIGHT))
    win_img = pygame.transform.scale(pygame.image.load(resource_path("img/paycheck.png")), (WIDTH, HEIGHT))
    lose_img = pygame.transform.scale(pygame.image.load(resource_path("img/TheBiteof83.png")), (WIDTH, HEIGHT))
except Exception as e:
    print("ASSET LOAD ERROR (stage/win/lose):", repr(e))
    stage = pygame.Surface((WIDTH, HEIGHT)); stage.fill(BLACK)
    win_img = lose_img = stage

try:
    chica_blackout_img = pygame.image.load(resource_path("img/ClassicChica_Infobox.png"))
    blackout_jumpscare_img = pygame.image.load(resource_path("img/chicajump.png"))
    space_overlay_img = pygame.image.load(resource_path("img/mask.png")).convert_alpha()
    space_overlay_img = pygame.transform.scale(space_overlay_img, (WIDTH, HEIGHT))
    blackout_snd = pygame.mixer.Sound(resource_path("sound/powerdown.wav"))

    # --- VENT SOUND ADJUSTMENTS ---
    vent_small = pygame.mixer.Sound(resource_path("sound/vent.wav"))
    vent_small.set_volume(0.4)
    vent_medium = pygame.mixer.Sound(resource_path("sound/vent.wav"))
    vent_medium.set_volume(0.7)
    vent_loud = pygame.mixer.Sound(resource_path("sound/vent.wav"))
    vent_loud.set_volume(1.0)

    bonnie_vent_jumpscare = pygame.image.load(resource_path("img/bonniejump.png"))
    freddy_eyes = pygame.image.load(resource_path("img/eye.png"))
    freddy_eyes_big = pygame.transform.scale(freddy_eyes, (int(freddy_eyes.get_width()*1.8), int(freddy_eyes.get_height()*1.8)))
    special_jumpscare_img = pygame.image.load(resource_path("img/Specialjumpscare.png"))

    jumpscare_snd = pygame.mixer.Sound(resource_path("sound/jumpscare.wav"))
    vent_jumpscare_snd = pygame.mixer.Sound(resource_path("sound/special_jumpscare.wav"))
    blackout_jumpscare_snd = pygame.mixer.Sound(resource_path("sound/special_jumpscare.wav"))
    special_jumpscare_snd = pygame.mixer.Sound(resource_path("sound/special_jumpscare.wav"))
except Exception as e:
    print("ASSET LOAD ERROR (blackout/vent/eyes/special):", repr(e))
    chica_blackout_img = pygame.Surface((250, 350)); chica_blackout_img.fill((20, 20, 20))
    space_overlay_img = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA); space_overlay_img.fill((0,0,0,0))
    blackout_jumpscare_img = lose_img
    bonnie_vent_jumpscare = lose_img
    blackout_snd = None
    vent_small = vent_medium = vent_loud = None
    freddy_eyes = pygame.Surface((60, 30)); freddy_eyes.fill(RED)
    freddy_eyes_big = pygame.Surface((110, 55)); freddy_eyes_big.fill(RED)
    special_jumpscare_img = lose_img
    jumpscare_snd = vent_jumpscare_snd = blackout_jumpscare_snd = None

hallucination_channel = pygame.mixer.Channel(1)
blackout_channel = pygame.mixer.Channel(2)
vent_channel = pygame.mixer.Channel(3)

win_snd = phase_change_snd = hallucination_snd = None
try:
    win_snd = pygame.mixer.Sound(resource_path("sound/win.wav"))
    phase_change_snd = pygame.mixer.Sound(resource_path("sound/fnaf-freddys-laugh.wav"))
    hallucination_snd = pygame.mixer.Sound(resource_path("sound/bb.wav"))
except Exception as e:
    print("ASSET LOAD ERROR (win/phase/bb sound):", repr(e))

# --- PHONE CALL SETUP ---
phone_ring_snd = phone_talk_snd = None
try:
    phone_ring_snd = pygame.mixer.Sound(resource_path("sound/phone_ring.wav"))
    phone_talk_snd = pygame.mixer.Sound(resource_path("sound/phone_talk.wav"))
except Exception as e:
    print("ASSET LOAD ERROR (phone sounds):", repr(e))

phone_channel = pygame.mixer.Channel(4)

current_track = None
def play_music(track_path, vol=1.0):
    global current_track
    if current_track != track_path:
        try:
            pygame.mixer.music.load(resource_path(track_path))
            pygame.mixer.music.set_volume(vol)
            pygame.mixer.music.play(-1)
            current_track = track_path
        except Exception as e:
            print("MUSIC LOAD ERROR:", track_path, repr(e))

def save_to_log(name, final_score, total_q, elapsed_time):
    with open(writable_path("log.txt"), "a", encoding="utf-8") as f:
        f.write(f"User: {name} | Time: {elapsed_time}s | Score: {final_score}/{total_q}\n")

def draw_wrapped(text, x, y, max_width, current_font):
    words = text.split()
    lines = []
    cur = ""
    for w in words:
        test = cur + w + " "
        if current_font.size(test)[0] < max_width:
            cur = test
        else:
            lines.append(cur)
            cur = w + " "
    lines.append(cur)
    for i, line in enumerate(lines):
        screen.blit(current_font.render(line, True, WHITE), (x, y + i * 32))
    return len(lines)

def trigger_its_me():
    if hallucination_snd: hallucination_channel.play(hallucination_snd)
    for _ in range(5):
        screen.fill(BLACK)
        txt = huge_font.render("IT'S ME", True, WHITE)
        screen.blit(txt, (WIDTH//2 - txt.get_width()//2, HEIGHT//2 - txt.get_height()//2))
        pygame.display.update(); pygame.time.delay(40)
        screen.fill(BLACK); pygame.display.update(); pygame.time.delay(20)

def flicker_black_white():
    for _ in range(6):
        screen.fill((255, 255, 255)); pygame.display.update(); pygame.time.delay(60)
        screen.fill((0, 0, 0)); pygame.display.update(); pygame.time.delay(60)

def reset_game():
    global lives, score, index, user_input, start_time, phase, freddy, bonnie, chica, win, sound_played
    global battery, outage_state, outage_timer, total_blackout_time, is_jumpscare_death
    global vent_status, vent_timer, vent_threat_active, vent_stage, vent_repeat_count, blackout_trigger_time
    global phone_state, phone_pause_start
    random.shuffle(questions)
    lives, score, index, user_input = 3, 0, 0, ""
    start_time = time.time()
    total_blackout_time = 0
    blackout_trigger_time = 0
    phase = 1
    freddy, bonnie, chica = load_characters(phase)
    win, sound_played = False, False
    is_jumpscare_death = False
    battery = 100.0
    outage_state = "NORMAL"
    outage_timer = 0
    vent_status = "OPEN"
    vent_timer = 0
    vent_threat_active = False
    vent_stage = 0
    vent_repeat_count = 0
    phone_channel.stop()
    phone_state = "IDLE"
    phone_pause_start = 0

# --- INITIALIZATION ---
questions = load_questions()
state = "LOGIN"
player_name = ""
scroll_y = 0
reset_game()
running = True
clock = pygame.time.Clock()

# --- BUTTON RECTS ---
btn_login_start = pygame.Rect(350, 400, 300, 60)
btn_start = pygame.Rect(350, 250, 300, 60)
btn_hist = pygame.Rect(350, 350, 300, 60)
btn_exit = pygame.Rect(350, 450, 300, 60)
btn_charge = pygame.Rect(50, 580, 150, 40)
btn_vent = pygame.Rect(800, 580, 150, 40)
btn_phone = pygame.Rect(425, 580, 150, 40)
btn_back = pygame.Rect(350, 560, 300, 50)
btn_clear = pygame.Rect(750, 80, 120, 40)

while running:
    sx, sy = get_shake_offset()
    screen.fill(BLACK)

    if state == "LOGIN":
        play_music("sound/bg.wav", 0.5)
        screen.blit(stage, (sx, sy))
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        screen.blit(overlay, (0, 0))
        title_text = title_font.render("ENTER YOUR NAME", True, WHITE)
        screen.blit(title_text, (WIDTH//2 - title_text.get_width()//2, 150))
        input_rect = pygame.Rect(300, 280, 400, 60)
        pygame.draw.rect(screen, GRAY, input_rect)
        pygame.draw.rect(screen, WHITE, input_rect, 3)
        name_surf = font.render(player_name, True, YELLOW)
        screen.blit(name_surf, (input_rect.x + 20, input_rect.y + 15))
        pygame.draw.rect(screen, GRAY, btn_login_start)
        pygame.draw.rect(screen, WHITE, btn_login_start, 3)
        start_label = font.render("CONTINUE", True, WHITE)
        screen.blit(start_label, (btn_login_start.centerx - start_label.get_width()//2, btn_login_start.centery - start_label.get_height()//2))

    elif state == "MENU":
        play_music("sound/bg.wav", 0.5)
        screen.blit(stage, (sx, sy))
        title_text = title_font.render(f"WELCOME, {player_name}", True, WHITE)
        screen.blit(title_text, (WIDTH//2 - title_text.get_width()//2, 100))
        for btn, txt in [(btn_start, "Start Game"), (btn_hist, "History"), (btn_exit, "Exit Game")]:
            pygame.draw.rect(screen, GRAY, btn); pygame.draw.rect(screen, WHITE, btn, 3)
            label = font.render(txt, True, WHITE)
            screen.blit(label, (btn.centerx - label.get_width()//2, btn.centery - label.get_height()//2))

    elif state == "HISTORY":
        screen.blit(stage, (sx, sy))
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))
        hist_title = title_font.render("GAME LOGS", True, YELLOW)
        screen.blit(hist_title, (WIDTH//2 - hist_title.get_width()//2, 30))
        high_score = get_high_score()
        hs_txt = font.render(f"BEST SCORE: {high_score}", True, GREEN)
        screen.blit(hs_txt, (150, 90))
        pygame.draw.rect(screen, RED, btn_clear)
        pygame.draw.rect(screen, WHITE, btn_clear, 2)
        clear_label = font.render("CLEAR", True, WHITE)
        screen.blit(clear_label, (btn_clear.centerx - clear_label.get_width()//2, btn_clear.centery - clear_label.get_height()//2))
        history_list = get_history()
        history_rect = pygame.Rect(150, 130, 700, 400)
        surf_height = max(400, len(history_list) * 35 + 20)
        hist_surf = pygame.Surface((700, surf_height), pygame.SRCALPHA)
        if not history_list:
            hist_surf.blit(font.render("No history found.", True, WHITE), (0, 0))
        else:
            for i, line in enumerate(history_list):
                entry = font.render(line, True, WHITE)
                hist_surf.blit(entry, (0, i * 35))
        screen.blit(hist_surf, (history_rect.x, history_rect.y), (0, scroll_y, 700, 400))
        pygame.draw.rect(screen, WHITE, history_rect, 2)
        if surf_height > 400:
            bar_height = int(400 * (400 / surf_height))
            bar_y = history_rect.y + int(scroll_y * (400 / surf_height))
            pygame.draw.rect(screen, GRAY, (history_rect.right + 5, history_rect.y, 10, 400))
            pygame.draw.rect(screen, YELLOW, (history_rect.right + 5, bar_y, 10, bar_height))
        pygame.draw.rect(screen, GRAY, btn_back); pygame.draw.rect(screen, WHITE, btn_back, 3)
        back_txt = font.render("BACK TO MENU", True, WHITE)
        screen.blit(back_txt, (btn_back.centerx - back_txt.get_width()//2, btn_back.centery - back_txt.get_height()//2))

    elif state == "GAME":
        if outage_state == "NORMAL":
            play_music("sound/freddys-music-box_mZSbZz6.wav", 0.1)
            screen.blit(stage, (sx, sy))

            drain_rate = 0.24 if vent_status == "CLOSED" else 0.05
            battery -= drain_rate

            mouse_pos = pygame.mouse.get_pos()
            mouse_pressed = pygame.mouse.get_pressed()
            if btn_charge.collidepoint(mouse_pos) and mouse_pressed[0]:
                battery = min(100, battery + 0.15)

            if phone_state == "RINGING" and btn_phone.collidepoint(mouse_pos) and mouse_pressed[0]:
                phone_channel.stop()
                if phone_talk_snd: phone_channel.play(phone_talk_snd)
                phone_state = "TALKING"

            if battery <= 0:
                battery, outage_state, outage_timer = 0, "LEFT", time.time()
                pygame.mixer.music.stop()

            time_left = max(0, 45 - int((time.time() - start_time) - total_blackout_time))

            pygame.draw.rect(screen, BLACK, (0, 0, WIDTH, 60))
            stats_txt = f"{player_name} | Lives: {lives} | Time: {time_left} | Score: {score}"
            power_txt = f"Power: {int(battery)}%"
            vent_txt = f"Vent: {vent_status}"

            screen.blit(font.render(stats_txt, True, WHITE), (20, 15))
            screen.blit(font.render(power_txt, True, YELLOW if battery < 20 else GREEN), (600, 15))
            screen.blit(font.render(vent_txt, True, RED if vent_status == "CLOSED" else GREEN), (820, 15))

            screen.blit(freddy, (60 + sx, 150 + sy))
            screen.blit(bonnie, (410 + sx, 130 + sy))
            screen.blit(chica, (760 + sx, 170 + sy))

            pygame.draw.rect(screen, GRAY, btn_charge); pygame.draw.rect(screen, WHITE, btn_charge, 2)
            screen.blit(font.render("CHARGE", True, WHITE), (btn_charge.x + 35, btn_charge.y + 8))

            v_btn_color = RED if vent_status == "CLOSED" else GRAY
            pygame.draw.rect(screen, v_btn_color, btn_vent); pygame.draw.rect(screen, WHITE, btn_vent, 2)
            screen.blit(font.render("CLOSE VENT", True, WHITE), (btn_vent.x + 10, btn_vent.y + 8))

            if phone_state == "RINGING":
                pygame.draw.rect(screen, YELLOW, btn_phone); pygame.draw.rect(screen, WHITE, btn_phone, 2)
                screen.blit(font.render("ANSWER (P)", True, BLACK), (btn_phone.x + 15, btn_phone.y + 8))
            elif phone_state == "TALKING":
                pygame.draw.rect(screen, GRAY, btn_phone); pygame.draw.rect(screen, WHITE, btn_phone, 2)
                screen.blit(font.render("ON CALL...", True, WHITE), (btn_phone.x + 15, btn_phone.y + 8))

            if phone_state == "IDLE":
                if random.randint(1, 1500) == 1:
                    state = "BLACKOUT"; blackout_trigger_time = time.time()
                    if blackout_snd: blackout_channel.play(blackout_snd)

                if random.randint(1, 1200) == 1: trigger_its_me()

                if not vent_threat_active and random.randint(1, 700) == 1:
                    vent_threat_active, vent_stage, vent_repeat_count, vent_timer = True, 0, 0, time.time()
                    if vent_small: vent_channel.play(vent_small)

                if vent_threat_active:
                    if vent_status == "CLOSED": vent_threat_active = False
                    elif time.time() - vent_timer > 2.0:
                        vent_repeat_count += 1; vent_timer = time.time()
                        if vent_repeat_count >= 3: vent_stage += 1; vent_repeat_count = 0
                        if vent_stage == 0:
                            if vent_small: vent_channel.play(vent_small)
                        elif vent_stage == 1:
                            if vent_medium: vent_channel.play(vent_medium)
                        elif vent_stage == 2:
                            if vent_loud: vent_channel.play(vent_loud)
                        elif vent_stage > 2:
                            state, is_jumpscare_death = "VENT_FAIL", True
                            if vent_jumpscare_snd: vent_jumpscare_snd.play()
                            trigger_shake(50, 60)

            elif phone_state == "TALKING":
                # Once the "someone talking about me" audio finishes, resume animatronic activity
                if not phone_channel.get_busy():
                    if vent_threat_active:
                        vent_timer += time.time() - phone_pause_start
                    phone_state = "IDLE"
            # else: phone_state == "RINGING" -> everything animatronic stays frozen, just wait for pickup

            if index < len(questions) and lives > 0 and time_left > 0:
                q = questions[index]
                panel = pygame.Rect(50, 310, 900, 240)
                pygame.draw.rect(screen, GRAY, panel); pygame.draw.rect(screen, WHITE if phase==1 else RED, panel, 4)
                curr_f = scary_font if phase == 2 else font
                line_count = draw_wrapped(q["question"], panel.x + 25, panel.y + 20, 850, curr_f)
                opt_y = panel.y + 25 + (line_count * 32)
                for i, opt in enumerate(q["options"]):
                    screen.blit(curr_f.render(f"{chr(65+i)}. {opt}", True, WHITE), (panel.x + 50, opt_y + i * 28))
                input_box = pygame.Rect(350, 570, 300, 50)
                pygame.draw.rect(screen, BLACK, input_box); pygame.draw.rect(screen, WHITE if phase==1 else RED, input_box, 2)
                screen.blit(font.render(user_input, True, WHITE), (input_box.x + 15, input_box.y + 12))

            else:
                # FIXED: Only set win to True if all questions were completed with remaining lives
                win = (index >= len(questions) and lives > 0)
                is_jumpscare_death = False
                save_to_log(player_name, score, len(questions), 45 - time_left)
                state = "GAMEOVER"

        else: # Outage Logic
            elapsed = time.time() - outage_timer; screen.fill(BLACK)
            if outage_state == "LEFT":
                screen.blit(freddy_eyes, (150 - freddy_eyes.get_width()//2, HEIGHT//2 - freddy_eyes.get_height()//2))
                if elapsed > 2: outage_state, outage_timer = "RIGHT", time.time()
            elif outage_state == "RIGHT":
                screen.blit(freddy_eyes, (850 - freddy_eyes.get_width()//2, HEIGHT//2 - freddy_eyes.get_height()//2))
                if elapsed > 2: outage_state, outage_timer = "CENTER", time.time()
            elif outage_state == "CENTER":
                screen.blit(freddy_eyes_big, (WIDTH//2 - freddy_eyes_big.get_width()//2, HEIGHT//2 - freddy_eyes_big.get_height()//2))
                if elapsed > 2:
                    outage_state, outage_timer, is_jumpscare_death = "JUMPSCARE", time.time(), True
                    if special_jumpscare_snd: special_jumpscare_snd.play()
                    trigger_shake(45, 90)
            elif outage_state == "JUMPSCARE":
                screen.blit(special_jumpscare_img, (sx, sy))
                if elapsed > 4: running = False

    elif state == "VENT_FAIL":
        screen.blit(bonnie_vent_jumpscare, (sx, sy))
        if not pygame.mixer.get_busy(): running = False

    elif state == "BLACKOUT":
        screen.fill(BLACK)
        battery -= 0.05
        screen.blit(chica_blackout_img, (WIDTH//2 - chica_blackout_img.get_width()//2, HEIGHT//2 - chica_blackout_img.get_height()//2))
        elapsed_blackout = time.time() - blackout_trigger_time
        keys = pygame.key.get_pressed()
        if keys[pygame.K_SPACE]:
            screen.blit(space_overlay_img, (0, 0))
            if elapsed_blackout > 3.0:
                total_blackout_time += elapsed_blackout
                state = "GAME"
        if elapsed_blackout > 0.5 and not keys[pygame.K_SPACE]:
            state, is_jumpscare_death = "BLACKOUT_FAIL", True
            if blackout_jumpscare_snd: blackout_jumpscare_snd.play()
            trigger_shake(45, 90)

    elif state == "BLACKOUT_FAIL":
        screen.blit(blackout_jumpscare_img, (sx, sy))
        if not pygame.mixer.get_busy(): running = False

    elif state == "GAMEOVER":
        pygame.mixer.music.stop()
        phone_channel.stop()
        screen.blit(win_img if win else lose_img, (sx, sy))
        if not sound_played:
            if win:
                if win_snd: win_snd.play()
            else:
                if jumpscare_snd: jumpscare_snd.play()
            sound_played = True
        screen.blit(font.render("Press SPACE to Menu", True, WHITE), (360, 610))

    for event in pygame.event.get():
        if event.type == pygame.QUIT: running = False
        if event.type == pygame.MOUSEWHEEL and state == "HISTORY":
            scroll_y -= event.y * 20
            h_logs = get_history()
            max_scroll = max(0, (len(h_logs) * 35) - 400)
            if scroll_y < 0: scroll_y = 0
            if scroll_y > max_scroll: scroll_y = max_scroll
        if event.type == pygame.KEYDOWN:
            if state == "LOGIN":
                if event.key == pygame.K_RETURN and player_name != "":
                    state = "MENU"
                elif event.key == pygame.K_BACKSPACE:
                    player_name = player_name[:-1]
                else:
                    if len(player_name) < 15 and event.unicode.isalnum():
                        player_name += event.unicode.upper()
            elif state == "GAME":
                if event.key == pygame.K_p and phone_state == "RINGING":
                    phone_channel.stop()
                    if phone_talk_snd: phone_channel.play(phone_talk_snd)
                    phone_state = "TALKING"
                    continue
                if event.key == pygame.K_8:
                    vent_threat_active, vent_stage, vent_timer = True, 0, time.time() - 2.0
                    continue
                if event.key == pygame.K_9:
                    state = "BLACKOUT"; blackout_trigger_time = time.time()
                    continue
                if event.key == pygame.K_0:
                    battery, outage_state, outage_timer = 0, "LEFT", time.time()
                    pygame.mixer.music.stop(); continue
                if event.key == pygame.K_RALT: win, state = True, "GAMEOVER"
                elif event.key == pygame.K_RCTRL: win, state = False, "GAMEOVER"
                elif outage_state == "NORMAL":
                    if event.key == pygame.K_RETURN and user_input != "":
                        if user_input.upper().strip() == str(questions[index]["answer"]).strip().upper():
                            score += 1
                        else:
                            lives -= 1
                            trigger_shake(15, 12)

                            # FIXED: Trigger Phase 2 after 2 wrong answers (lives drop to 1 or below)
                            if lives <= 1 and phase == 1:
                                if phase_change_snd: phase_change_snd.play()
                                trigger_shake(10, 15); flicker_black_white(); phase = 2
                                freddy, bonnie, chica = load_characters(phase)

                        index += 1; user_input = ""; start_time = time.time(); total_blackout_time = 0
                    elif event.key == pygame.K_BACKSPACE: user_input = user_input[:-1]
                    else:
                        if len(event.unicode) > 0 and event.key not in [pygame.K_TAB, pygame.K_ESCAPE]:
                            user_input += event.unicode.upper()
            elif state == "GAMEOVER" and event.key == pygame.K_SPACE:
                state = "MENU"; reset_game()
        if event.type == pygame.MOUSEBUTTONDOWN:
            if state == "LOGIN":
                if btn_login_start.collidepoint(event.pos) and player_name != "":
                    state = "MENU"
            elif state == "MENU":
                if btn_start.collidepoint(event.pos):
                    reset_game(); state = "GAME"
                    phone_state = "RINGING"
                    phone_pause_start = time.time()
                    if phone_ring_snd: phone_channel.play(phone_ring_snd, loops=-1)
                if btn_hist.collidepoint(event.pos): state = "HISTORY"
                if btn_exit.collidepoint(event.pos): running = False
            elif state == "HISTORY":
                if btn_back.collidepoint(event.pos): state = "MENU"
                if btn_clear.collidepoint(event.pos):
                    with open(writable_path("log.txt"), "w", encoding="utf-8") as f:
                        f.write("")
                    scroll_y = 0
            elif state == "GAME" and outage_state == "NORMAL":
                if btn_vent.collidepoint(event.pos):
                    vent_status = "CLOSED" if vent_status == "OPEN" else "OPEN"

    pygame.display.update()
    clock.tick(30)
pygame.quit()
print("\n>>> GAME CLOSED NORMALLY <<<", flush=True)
try:
    input("Press Enter to close this window...")
except Exception:
    pass