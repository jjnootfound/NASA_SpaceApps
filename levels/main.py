# main.py
import os, sys, math
from direct.showbase.ShowBase import ShowBase
from direct.task import Task
from direct.gui.OnscreenImage import OnscreenImage
from direct.gui.DirectGui import DirectFrame, DirectButton, DirectLabel
from panda3d.core import (
    CardMaker, TransparencyAttrib, ClockObject, Filename, Vec3, TextNode,
    CollisionTraverser, CollisionNode, CollisionRay, CollisionHandlerQueue,
    CollisionSphere, BitMask32, getModelPath, loadPrcFileData
)

# ========= PRC / base =========
loadPrcFileData("", "window-title ISS Cupola Demo")
loadPrcFileData("", "show-frame-rate-meter 1")

# ================================
# ===  GAME CONFIG ==============
# ================================
# 2D assets
PLAYER_FRAMES = [
    "assets/models/player_walk1.png",
    "assets/models/player_walk2.png",
]
BACKGROUND_IMG = "assets/backgrounds/bg2.png"   # or "" to disable

# Cupola trigger (INVISIBLE)
TRIGGER_CENTER = (0.20, 0.12)   # (x,z) in render2d
TRIGGER_SIZE   = (0.22, 0.16)   # (width, height)

# === [BED_TRIGGER_*] ===
# Sleep trigger (small, PNG bed)
SLEEP_TRIGGER_CENTER = (0.300, -0.320)
SLEEP_TRIGGER_SIZE   = (0.160, 0.120)   # <-- EDIT: bed trigger size (w, h)
SHOW_SLEEP_HITBOX    = True            # <-- EDIT: show bed hitbox on start

BED_IMAGE            = "assets/models/astroBed.png"  # icon shown on map
BED_SCALE            = 0.10

# 3D model (try BAM, else GLB)
MODEL_PATH_BAM = "assets/cupola.bam"
MODEL_PATH_GLB = "assets/cupola.glb"
MODEL_POS    = (0, 0, 0)
MODEL_HPR    = (0, 0, 0)
MODEL_SCALE  = 1.0

# Optional clickable parts / markers
OBJ_SUBPARTS_INFO = {}
MARKERS_INFO = []

# ======= WALLS (AABB in render2d) =======
# (x, z, w, h)
WALLS = [
    (-0.323, -0.120, 0.300, 0.560),
    (0.197, 0.620, 0.300, 0.300),
    (0.497, 0.300, 0.300, 0.300),
    (0.617, -0.260, 0.300, 0.300),
    (0.257, -0.080, 0.380, 0.260),
    (0.017, -0.840, 1.020, 0.280),
    (-0.643, -0.540, 0.300, 0.300),
    (0.144, -0.266, 0.160, 0.260),
    (0.084, 0.094, 0.060, 0.120),
    (-0.096, 0.671, 0.300, 0.300),
    (-0.316, 0.611, 0.300, 0.300),
    (0.700, 0.440, 0.720, 1.240),
    (0.780, -0.620, 0.500, 0.700),
    (-0.760, -0.120, 0.540, 2.300),
    (-0.020, 0.860, 1.060, 0.300),
    (0.820, -0.220, 0.420, 0.160)
]
SHOW_WALLS = True  # toggle with F7

# ======= ENERGY HUD (100..0) =======
# 11 PNGs: index 0 = 100 (full), index 10 = 0 (empty)
ENERGY_ICON_PATHS = [
    "assets/hud/sleep/energyBar100.png",
    "assets/hud/sleep/energyBar90.png",
    "assets/hud/sleep/energyBar80.png",
    "assets/hud/sleep/energyBar70.png",
    "assets/hud/sleep/energyBar60.png",
    "assets/hud/sleep/energyBar50.png",
    "assets/hud/sleep/energyBar40.png",
    "assets/hud/sleep/energyBar30.png",
    "assets/hud/sleep/energyBar20.png",
    "assets/hud/sleep/energyBar10.png",
    "assets/hud/sleep/energyBar0.png",
]

# ---- ENERGY HUD size/pos (barra larga y delgada) ----
ENERGY_HUD_SCALE_X = 1   # largo (X)
ENERGY_HUD_SCALE_Z = 0.12   # alto  (Z)
ENERGY_HUD_POS     = (-0.90, 0, 0.88)   # top-left aprox; mueve X/Z a gusto

# ======= SLEEP LOADING BAR (images 0..100) =======
# IMPORTANT: use PNGs (convert SVG → PNG). Order: 0,10,20,...,100
SLEEP_BAR_IMAGE_PATHS = [
    "assets/hud/sleep/energyBar0.png",
    "assets/hud/sleep/energyBar10.png",
    "assets/hud/sleep/energyBar20.png",
    "assets/hud/sleep/energyBar30.png",
    "assets/hud/sleep/energyBar40.png",
    "assets/hud/sleep/energyBar50.png",
    "assets/hud/sleep/energyBar60.png",
    "assets/hud/sleep/energyBar70.png",
    "assets/hud/sleep/energyBar80.png",
    "assets/hud/sleep/energyBar90.png",
    "assets/hud/sleep/energyBar100.png",
]

# Sleep overlay style: True = light beige bg + dark text, False = dark bg + white text
SLEEP_OVERLAY_LIGHT    = True
SLEEP_DURATION_SECONDS = 8.0

# ---- Sleep bar (overlay) size/pos (IMAGEN y FALLBACK) ----
SLEEP_BAR_SCALE_X = 2.40   # largo (X) de IMAGEN de carga
SLEEP_BAR_SCALE_Z = 0.08   # alto  (Z) de IMAGEN de carga
SLEEP_BAR_HALF_W  = 1.20   # mitad de ancho FALLBACK
SLEEP_BAR_HALF_H  = 0.018  # mitad de alto  FALLBACK
SLEEP_BAR_MARGIN  = 0.02   # margen interno FALLBACK

# ============ 2D utils ============
def aabb_overlap(ax, az, aw, ah, bx, bz, bw, bh):
    return (abs(ax - bx) * 2 < (aw + bw)) and (abs(az - bz) * 2 < (ah + bh))

# ============ 2D entities ============
class Entity:
    def __init__(self, base_app: ShowBase, image_path: str, parent, pos=(0, 0), scale=0.15):
        self.base = base_app
        cm = CardMaker("sprite")
        cm.setFrame(-0.5, 0.5, -0.5, 0.5)  # 1x1 centered quad
        self.node = parent.attachNewNode(cm.generate())
        self.node.setTransparency(TransparencyAttrib.M_alpha)
        if image_path:
            tex = self.base.loader.loadTexture(image_path)
            self.node.setTexture(tex, 1)
        self.node.setPos(pos[0], 0, pos[1])  # (x, y=0, z)
        self.node.setScale(scale)

    def set_pos(self, x, z): self.node.setPos(x, 0, z)
    def get_pos(self):
        p = self.node.getPos(); return p.x, p.z
    def set_scale(self, s): self.node.setScale(s)
    def set_scale_xy(self, sx, sy): self.node.setScale(sx, 1, sy)
    def set_texture(self, texture): self.node.setTexture(texture, 1)
    def get_aabb_size(self):
        s = self.node.getScale(); return abs(s.x), abs(s.z)
    def hide(self): self.node.hide()
    def show(self): self.node.show()

class AnimatedEntity(Entity):
    def __init__(self, base_app: ShowBase, frames_paths, parent, pos=(0, 0), scale=0.15, frame_time=0.12):
        super().__init__(base_app, frames_paths[0], parent, pos=pos, scale=scale)
        self.frames = [self.base.loader.loadTexture(p) for p in frames_paths]
        self.frame_time = frame_time
        self.accum = 0.0
        self.idx = 0
        self.playing = False
    def set_playing(self, playing: bool):
        if self.playing and not playing:
            self.idx = 0
            self.set_texture(self.frames[0])
        self.playing = playing
    def update_anim(self, dt: float):
        if not self.playing: return
        self.accum += dt
        if self.accum >= self.frame_time:
            self.accum -= self.frame_time
            self.idx = (self.idx + 1) % len(self.frames)
            self.set_texture(self.frames[self.idx])

class TriggerZone:
    """
    Rectángulo AABB en render2d. Si visible=True dibuja un quad (hitbox).
    Ahora permite cambiar centro y tamaño dinámicamente.
    """
    def __init__(self, base_app: ShowBase, parent, center=(0,0), size=(0.3,0.3), visible=False, color=(1,1,0,0.25)):
        self.base = base_app
        self.parent = parent
        self.color = color
        self.visible = visible
        self.x, self.z = center
        self.w, self.h = size
        self.node = None
        self._rebuild_node()

    def _rebuild_node(self):
        if self.node:
            self.node.removeNode()
            self.node = None
        if not self.visible:
            return
        cm = CardMaker("trigger")
        cm.setFrame(-self.w/2, self.w/2, -self.h/2, self.h/2)
        self.node = self.parent.attachNewNode(cm.generate())
        self.node.setTransparency(TransparencyAttrib.M_alpha)
        self.node.setColor(*self.color)
        self.node.setPos(self.x, 0, self.z)

    def set_center(self, x, z):
        self.x, self.z = x, z
        if self.node:
            self.node.setPos(self.x, 0, self.z)

    def set_size(self, w, h):
        self.w, self.h = max(0.02, w), max(0.02, h)
        self._rebuild_node()

    def set_visible(self, v):
        self.visible = v
        self._rebuild_node()

# ======== Orbit camera 3D ========
class OrbitCamera:
    """RMB: orbit | MMB: pan | Wheel: zoom"""
    def __init__(self, base: ShowBase, camera, camnode):
        self.base, self.camera, self.camnode = base, camera, camnode
        self.target = base.render.attachNewNode("orbit_target")
        self.radius, self.yaw, self.pitch = 8.0, 30.0, 20.0
        self.min_pitch, self.max_pitch = -89.0, 89.0
        self.min_radius, self.max_radius = 1.5, 100.0
        self.rotate_active = self.pan_active = False
        self.last_mouse = None
        self.pan_speed, self.rot_speed, self.zoom_step = 0.008, 0.25, 0.9
        base.accept("mouse3", self._sr); base.accept("mouse3-up", self._er)
        base.accept("mouse2", self._sp); base.accept("mouse2-up", self._ep)
        base.accept("wheel_up", self._zi); base.accept("wheel_down", self._zo)
    def set_target_np(self, np): self.target = np
    def _sr(self): self.rotate_active = True; self.last_mouse = None
    def _er(self): self.rotate_active = False; self.last_mouse = None
    def _sp(self): self.pan_active = True; self.last_mouse = None
    def _ep(self): self.pan_active = False; self.last_mouse = None
    def _zi(self): self.radius = max(self.min_radius, self.radius * self.zoom_step)
    def _zo(self): self.radius = min(self.max_radius, self.radius / self.zoom_step)
    def update(self, dt):
        mw = self.base.mouseWatcherNode
        if not mw or not mw.hasMouse():
            self.last_mouse = None
            return
        m = mw.getMouse()
        if self.rotate_active or self.pan_active:
            if self.last_mouse is not None:
                dx, dy = (m.getX()-self.last_mouse.getX()), (m.getY()-self.last_mouse.getY())
                if self.rotate_active:
                    self.yaw   -= dx * self.rot_speed * 180.0
                    self.pitch += dy * self.rot_speed * 180.0
                    self.pitch  = max(self.min_pitch, min(self.max_pitch, self.pitch))
                if self.pan_active:
                    right = self.camera.getQuat().getRight()
                    up    = self.camera.getQuat().getUp()
                    move  = (right * (-dx * self.pan_speed * self.radius)) + (up * (-dy * self.pan_speed * self.radius))
                    self.target.setPos(self.target.getPos() + move)
            self.last_mouse = m
        yaw, pit = math.radians(self.yaw), math.radians(self.pitch)
        cx = self.radius * math.cos(pit) * math.sin(yaw)
        cy = -self.radius * math.cos(pit) * math.cos(yaw)
        cz = self.radius * math.sin(pit)
        self.camera.setPos(self.target, Vec3(cx, cy, cz))
        self.camera.lookAt(self.target)

# ====== glTF plugin registration (optional) ======
def _try_register_gltf_plugin():
    candidates = []
    try:
        import importlib.util
        spec = importlib.util.find_spec("panda3d_gltf")
        if spec and spec.origin:
            candidates.append(os.path.dirname(spec.origin))
    except Exception:
        pass
    candidates.append(os.path.join(sys.prefix, "Lib", "site-packages", "panda3d_gltf"))
    for plugin_dir in candidates:
        if not os.path.isdir(plugin_dir):
            continue
        if hasattr(os, "add_dll_directory"):
            try:
                os.add_dll_directory(plugin_dir)
                os.add_dll_directory(os.path.join(sys.prefix, "Lib", "site-packages", "panda3d"))
            except Exception:
                pass
        try:
            loadPrcFileData("", f"plugin-path {Filename.fromOsSpecific(plugin_dir).getFullpath()}")
            loadPrcFileData("", "load-file-type p3gltf")
            return True
        except Exception:
            pass
    return False

# ==================== Game ====================
class Game(ShowBase):
    def __init__(self):
        super().__init__()
        self.disableMouse()  # 2D control
        self.state, self.ui_blocked = "map2d", False
        self.dialog = self.info_label = None

        # ModelPath
        project_dir = os.path.dirname(os.path.abspath(__file__))
        getModelPath().appendDirectory(Filename.fromOsSpecific(project_dir))
        getModelPath().appendDirectory(Filename.fromOsSpecific(os.path.join(project_dir, "assets")))

        # 2D layers
        self.layer_bg   = self.render2d.attachNewNode("bg")
        self.layer_game = self.render2d.attachNewNode("game")
        self.layer_ui   = self.aspect2d.attachNewNode("ui")

        # Background
        if BACKGROUND_IMG:
            try:
                self.bg = OnscreenImage(image=BACKGROUND_IMG, parent=self.layer_bg)
                self.bg.setScale(1); self.bg.setTransparency(TransparencyAttrib.M_alpha)
            except Exception:
                self.bg = None

        # Player
        self.player = AnimatedEntity(self, PLAYER_FRAMES, self.layer_game, pos=(0.20, -0.5), scale=0.15, frame_time=0.12)
        self.speed, self.facing = 1.5, 1
        self.pressed = {k: False for k in ("w", "a", "s", "d", "space", "escape")}
        self._bind_inputs()

        # Triggers
        self.cupola_trigger = TriggerZone(self, self.layer_game, center=TRIGGER_CENTER, size=TRIGGER_SIZE, visible=False)

        self.sleep_trigger  = TriggerZone(
            self, self.layer_game,
            center=SLEEP_TRIGGER_CENTER, size=SLEEP_TRIGGER_SIZE,
            visible=SHOW_SLEEP_HITBOX, color=(0, 1, 1, 0.35)  # cian translúcido
        )
        # Bed icon (visual hint)
        try:
            self.bed_icon = Entity(self, BED_IMAGE, self.layer_game, pos=SLEEP_TRIGGER_CENTER, scale=BED_SCALE)
        except Exception:
            self.bed_icon = None

        self.was_in_cupola = False
        self.was_in_sleep  = False

        # Walls
        self.walls = []  # {"x","z","w","h","node"}
        self.show_walls = SHOW_WALLS
        self.wall_edit = False
        self.wall_sel = -1
        self.wall_hint = None
        self._build_walls_from_config()

        # Bed editor
        self.bed_edit = False
        self.bed_hint = None

        # Energy HUD (100 -> 0)
        self.energy_level = 10        # 10..0 (interno)
        self.walk_accum   = 0.0       # segundos caminados acumulados
        self.energy_textures = []
        self.energy_icons_loaded = self._load_energy_icons()
        self.energy_img = None
        self.energy_lbl = None
        self._build_energy_hud()

        # Sleep loading (images)
        self.sleep_textures = []
        self.sleep_images_loaded = self._load_sleep_bar_images()
        self.loading_overlay = None
        self.loading_time = 0.0
        self.loading_duration = SLEEP_DURATION_SECONDS
        self.sleep_img = None           # OnscreenImage for bar
        self.loading_back = None        # fallback bar bg
        self.loading_bar  = None        # fallback bar fg

        # Tasks
        self.taskMgr.add(self.update, "update")

        # 3D vars
        self.cupola_root = None
        self.click_mask = BitMask32.bit(1)
        self.picker_trav = self.picker_ray = self.picker_np = self.picker_queue = None
        self.back_btn = None
        self.camera_orbit = None

    # ----- Input binding -----
    def _bind_inputs(self):
        for key in ("w", "a", "s", "d", "space", "escape"):
            self.accept(key, self._key_down, [key])
            self.accept(f"{key}-up", self._key_up, [key])
        self.accept("p", self._print_player_pos)

        # Walls editor
        self.accept("f8", self._toggle_wall_editor)
        self.accept("f7", self._toggle_wall_visibility)
        self.accept("tab", self._cycle_wall, [1])
        self.accept("shift-tab", self._cycle_wall, [-1])
        self.accept("n", self._add_wall_here)
        self.accept("delete", self._delete_wall)
        self.accept("arrow_left",  self._nudge_wall, [-0.02,  0.00])
        self.accept("arrow_right", self._nudge_wall, [ 0.02,  0.00])
        self.accept("arrow_up",    self._nudge_wall, [ 0.00,  0.02])
        self.accept("arrow_down",  self._nudge_wall, [ 0.00, -0.02])
        self.accept("[", self._resize_wall, [-0.02,  0.00])
        self.accept("]", self._resize_wall, [ 0.02,  0.00])
        self.accept(";", self._resize_wall, [ 0.00, -0.02])
        self.accept("'", self._resize_wall, [ 0.00,  0.02])
        self.accept("enter", self._print_walls_constant)

        # Bed (sleep) editor
        self.accept("f9", self._toggle_bed_editor)            # entrar/salir editor
        self.accept("b",  self._print_bed_trigger_constant)   # imprimir constantes
        self.accept("arrow_left",  self._bed_nudge, [-0.02,  0.00])
        self.accept("arrow_right", self._bed_nudge, [ 0.02,  0.00])
        self.accept("arrow_up",    self._bed_nudge, [ 0.00,  0.02])
        self.accept("arrow_down",  self._bed_nudge, [ 0.00, -0.02])
        self.accept("[", self._bed_resize, [-0.02,  0.00])
        self.accept("]", self._bed_resize, [ 0.02,  0.00])
        self.accept(";", self._bed_resize, [ 0.00, -0.02])
        self.accept("'", self._bed_resize, [ 0.00,  0.02])

        # 3D model controls
        self.accept("r", self._model_hpr_delta, [5, 0, 0]);  self.accept("f", self._model_hpr_delta, [-5,0,0])
        self.accept("t", self._model_hpr_delta, [0, 5, 0]);  self.accept("g", self._model_hpr_delta, [0,-5,0])
        self.accept("y", self._model_hpr_delta, [0, 0, 5]);  self.accept("h", self._model_hpr_delta, [0, 0,-5])
        self.accept("u", self._model_pos_delta, [-0.2, 0, 0]); self.accept("j", self._model_pos_delta, [0.2, 0, 0])
        self.accept("i", self._model_pos_delta, [0, 0.2, 0]);  self.accept("k", self._model_pos_delta, [0,-0.2, 0])
        self.accept("o", self._model_pos_delta, [0, 0, 0.2]);  self.accept("l", self._model_pos_delta, [0, 0,-0.2])
        self.accept("+", self._model_scale_mul, [1.1]);       self.accept("-", self._model_scale_mul, [0.9])
        self.accept("0", self._model_reset)

    def _clear_movement(self):
        for k in ("w","a","s","d","space"):
            self.pressed[k] = False

    def _print_player_pos(self):
        x, z = self.player.get_pos()
        print(f"[POS] Player x={x:.3f}, z={z:.3f}")

    # ----- Input -----
    def _key_down(self, key):
        if not self.ui_blocked and not self.wall_edit and not self.bed_edit:
            self.pressed[key] = True

    def _key_up(self, key):
        if key in self.pressed:
            self.pressed[key] = False
        if self.ui_blocked and key != "escape":
            return
        if key == "escape":
            if self.state == "cupola3d":
                self.exit_cupola()
            else:
                self.userExit()

    # ----- Main loop -----
    def update(self, task: Task):
        dt = ClockObject.getGlobalClock().getDt()
        if self.state == "map2d":
            self.update_map2d(dt)
        elif self.state == "cupola3d" and self.camera_orbit:
            self.camera_orbit.update(dt)
        # Sleep overlay
        if self.loading_overlay is not None:
            self._update_loading(dt)
        return Task.cont

    def update_map2d(self, dt: float):
        if self.ui_blocked or self.wall_edit or self.bed_edit:
            return

        x, z = self.player.get_pos()
        moving, vx, vz = False, 0.0, 0.0
        if self.pressed["w"]: vz += self.speed; moving = True
        if self.pressed["s"]: vz -= self.speed; moving = True
        if self.pressed["a"]: vx -= self.speed; moving = True; self.facing = -1
        if self.pressed["d"]: vx += self.speed; moving = True; self.facing = 1

        # ENERGY: drop 1 level every 3s of ACCUMULATED walking (even if you stop)
        if moving and self.energy_level > 0:
            self.walk_accum += dt
            while self.walk_accum >= 3.0 and self.energy_level > 0:
                self.walk_accum -= 3.0
                self.energy_level = max(0, self.energy_level - 1)
                self._update_energy_hud()

        # Collisions vs walls (separable axis)
        pw, ph = self.player.get_aabb_size()
        hx, hz = pw * 0.5, ph * 0.5

        # X
        target_x = max(-1.2, min(1.2, x + vx * dt))
        for w in self.walls:
            if abs(target_x - w["x"]) < (hx + w["w"] * 0.5) and abs(z - w["z"]) < (hz + w["h"] * 0.5):
                target_x = w["x"] + hx + w["w"] * 0.5 if target_x > w["x"] else w["x"] - (hx + w["w"] * 0.5)
        # Z
        target_z = max(-1.0, min(1.0, z + vz * dt))
        for w in self.walls:
            if abs(target_x - w["x"]) < (hx + w["w"] * 0.5) and abs(target_z - w["z"]) < (hz + w["h"] * 0.5):
                target_z = w["z"] + hz + w["h"] * 0.5 if target_z > w["z"] else w["z"] - (hz + w["h"] * 0.5)

        self.player.set_pos(target_x, target_z)

        # Anim / flip
        self.player.set_playing(moving); self.player.update_anim(dt)
        base_scale = 0.18 if self.pressed["space"] else 0.15
        self.player.set_scale_xy(base_scale * self.facing, base_scale)

        # Triggers
        tz = self.cupola_trigger
        overlap_c = aabb_overlap(target_x, target_z, pw, ph, tz.x, tz.z, tz.w, tz.h)
        if overlap_c and not self.was_in_cupola and not self.dialog:
            self.ask_enter_cupola()
        self.was_in_cupola = overlap_c

        sz = self.sleep_trigger
        overlap_s = aabb_overlap(target_x, target_z, pw, ph, sz.x, sz.z, sz.w, sz.h)
        if overlap_s and not self.was_in_sleep and not self.dialog:
            self.ask_sleep()
        self.was_in_sleep = overlap_s

    # ----- Dialogs -----
    def ask_enter_cupola(self):
        self._clear_movement()
        self.ui_blocked = True
        self.dialog = DirectFrame(parent=self.layer_ui, frameColor=(0,0,0,0.75),
                                  frameSize=(-0.7, 0.7, -0.25, 0.25), pos=(0,0,0))
        DirectLabel(parent=self.dialog, text="Enter the Cupola?", scale=0.07, pos=(0,0,0.1))
        DirectButton(parent=self.dialog, text="Yes", scale=0.06, pos=(-0.2,0,-0.1), command=self._on_cupola_yes)
        DirectButton(parent=self.dialog, text="No",  scale=0.06, pos=( 0.2,0,-0.1), command=self._on_cupola_no)

    def _on_cupola_yes(self):
        self.dialog.destroy(); self.dialog = None
        self.enter_cupola()

    def _on_cupola_no(self):
        self.dialog.destroy(); self.dialog = None
        self.ui_blocked = False
        self._clear_movement()

    def ask_sleep(self):
        self._clear_movement()
        self.ui_blocked = True
        self.dialog = DirectFrame(parent=self.layer_ui, frameColor=(0,0,0,0.75),
                                  frameSize=(-0.7, 0.7, -0.25, 0.25), pos=(0,0,0))
        DirectLabel(parent=self.dialog, text="Go to sleep?", scale=0.07, pos=(0,0,0.1))
        DirectButton(parent=self.dialog, text="Yes", scale=0.06, pos=(-0.2,0,-0.1), command=self._on_sleep_yes)
        DirectButton(parent=self.dialog, text="No",  scale=0.06, pos=( 0.2,0,-0.1), command=self._on_sleep_no)

    def _on_sleep_yes(self):
        self.dialog.destroy(); self.dialog = None
        self._start_sleep_sequence()

    def _on_sleep_no(self):
        self.dialog.destroy(); self.dialog = None
        self.ui_blocked = False
        self._clear_movement()

    # ----- Sleep sequence -----
    def _start_sleep_sequence(self):
        self._clear_movement()
        self.ui_blocked = True

        # Overlay style
        if SLEEP_OVERLAY_LIGHT:
            bg = (0.98, 0.96, 0.92, 0.96)  # beige
            txt = (0, 0, 0, 1)             # black text
        else:
            bg = (0, 0, 0, 0.92)           # dark
            txt = (1, 1, 1, 1)             # white text

        # Fullscreen overlay
        self.loading_overlay = DirectFrame(parent=self.layer_ui,
                                           frameColor=bg,
                                           frameSize=(-1.5, 1.5, -1.1, 1.1),
                                           pos=(0,0,0))

        # Title + info
        DirectLabel(parent=self.loading_overlay, text="Sleeping...", scale=0.065, pos=(0,0,0.45),
                    frameColor=(0,0,0,0), text_fg=txt, text_align=TextNode.ACenter)
        msg = ("Astronauts experience 16 sunsets every day, which affects their circadian rhythm or sleep cycle.\n"
               "It is important for them to rest so that they can have a good performance.")
        DirectLabel(parent=self.loading_overlay, text=msg, scale=0.05, pos=(0,0,0.2),
                    frameColor=(0,0,0,0), text_fg=txt, text_align=TextNode.ACenter)

        # Sleep bar by images (fallback to simple bar if images not available)
        self.sleep_img = None
        self.loading_back = None
        self.loading_bar  = None

        if self.sleep_images_loaded:
            self.sleep_img = OnscreenImage(parent=self.loading_overlay, image=self.sleep_textures[0])
            self.sleep_img.setTransparency(TransparencyAttrib.M_alpha)
            self.sleep_img.setScale(SLEEP_BAR_SCALE_X, 1, SLEEP_BAR_SCALE_Z)  # long & thin
            self.sleep_img.setPos(0, 0, -0.25)
        else:
            self.loading_back = DirectFrame(
                parent=self.loading_overlay,
                frameColor=(0,0,0,0.15 if SLEEP_OVERLAY_LIGHT else 0.25),
                frameSize=(-SLEEP_BAR_HALF_W, SLEEP_BAR_HALF_W, -SLEEP_BAR_HALF_H, SLEEP_BAR_HALF_H),
                pos=(0,0,-0.25)
            )
            self.loading_bar = DirectFrame(
                parent=self.loading_overlay,
                frameColor=(0.2,0.5,1,0.9),
                frameSize=(
                    -SLEEP_BAR_HALF_W + SLEEP_BAR_MARGIN,  # left
                    -SLEEP_BAR_HALF_W + SLEEP_BAR_MARGIN,  # right (starts empty)
                    -SLEEP_BAR_HALF_H * 0.75,
                     SLEEP_BAR_HALF_H * 0.75
                ),
                pos=(0,0,-0.25)
            )

        self.loading_time = 0.0
        self.loading_duration = SLEEP_DURATION_SECONDS

    def _update_loading(self, dt: float):
        self.loading_time += dt
        t = min(1.0, self.loading_time / self.loading_duration)

        if self.sleep_img is not None:
            idx = min(10, int(round(t * 10)))  # 0..10
            self.sleep_img.setImage(self.sleep_textures[idx])
        elif self.loading_bar is not None:
            left  = -SLEEP_BAR_HALF_W + SLEEP_BAR_MARGIN
            width = (SLEEP_BAR_HALF_W * 2) - (SLEEP_BAR_MARGIN * 2)
            right = left + (width * t)
            self.loading_bar["frameSize"] = (
                left, right,
                -SLEEP_BAR_HALF_H * 0.75,
                 SLEEP_BAR_HALF_H * 0.75
            )

        if self.loading_time >= self.loading_duration:
            # restore energy to 100%
            self.energy_level = 10
            self.walk_accum = 0.0  # opcional: limpia acumulado tras dormir
            self._update_energy_hud()
            # close overlay
            if self.loading_overlay:
                self.loading_overlay.destroy()
                self.loading_overlay = None
            self.sleep_img = None
            self.loading_back = None
            self.loading_bar = None
            self.ui_blocked = False
            self._clear_movement()

    # ----- 3D: enter/exit -----
    def _load_model_any(self):
        if os.path.exists(MODEL_PATH_BAM):
            try:
                return self.loader.loadModel(MODEL_PATH_BAM), False
            except Exception:
                pass
        if os.path.exists(MODEL_PATH_GLB):
            _try_register_gltf_plugin()
            try:
                return self.loader.loadModel(MODEL_PATH_GLB), True
            except Exception as e:
                print("[ERROR] Could not load GLB:", e)
        return self.loader.loadModel("models/box"), False

    def enter_cupola(self):
        self._clear_movement()
        self.state, self.ui_blocked = "cupola3d", False
        self.layer_bg.hide(); self.layer_game.hide()
        self.enableMouse()
        self.cupola_root = self.render.attachNewNode("cupola_root")

        self.cupola_model, used_glb = self._load_model_any()
        if used_glb and self.cupola_model.hasPythonTag("loader-error"):
            used_glb = False

        self.cupola_model.reparentTo(self.cupola_root)
        self.cupola_model.setPos(*MODEL_POS)
        self.cupola_model.setHpr(*MODEL_HPR)
        self.cupola_model.setScale(MODEL_SCALE)

        if used_glb is False and not os.path.exists(MODEL_PATH_BAM) and os.path.exists(MODEL_PATH_GLB):
            DirectLabel(parent=self.layer_ui,
                        text="Could not load GLB.\nTip: convert to BAM:\n.gltf2bam assets/cupola.glb assets/cupola.bam",
                        frameColor=(0,0,0,0.6), pos=(0,0,0.8), scale=0.045)

        # Clickables by name
        for subname, info in OBJ_SUBPARTS_INFO.items():
            np = self.cupola_model.find(f"**/{subname}")
            if not np.isEmpty():
                self._make_clickable(np, info)

        # Invisible markers
        for (x, y, z), radius, info in MARKERS_INFO:
            marker = self.cupola_root.attachNewNode(f"marker_{len(info)}")
            marker.setPos(x, y, z)
            self._make_marker_clickable(marker, radius, info)

        # Picking
        self._setup_picker()

        # Orbit camera
        self.camera_orbit = OrbitCamera(self, self.camera, self.camNode)
        self.camera_orbit.target.setPos(self.cupola_model.getPos(self.render))
        self.camera_orbit.radius = max(3.0, 4.0 * float(self.cupola_model.getScale().x))

        # UI 3D
        self.back_btn = DirectButton(parent=self.layer_ui, text="Back to Map",
                                     scale=0.05, pos=(-1.0, 0, 0.9), command=self.exit_cupola)
        self.info_label = DirectLabel(parent=self.layer_ui, text="",
                                      frameColor=(0,0,0,0.5), frameSize=(-0.8, 0.8, -0.15, 0.15),
                                      pos=(0,0,-0.85), scale=0.055)
        self.accept("mouse1", self._on_click_3d)

    def exit_cupola(self):
        self._clear_movement()
        self.state = "map2d"
        self.disableMouse()
        if self.back_btn: self.back_btn.destroy(); self.back_btn = None
        if self.info_label: self.info_label.destroy(); self.info_label = None
        if self.cupola_root: self.cupola_root.removeNode(); self.cupola_root = None
        self.camera_orbit = None
        self.ignore("mouse1")
        self.layer_bg.show()
        self.layer_game.show()

    # ----- Picking (3D) -----
    def _setup_picker(self):
        self.picker_trav  = CollisionTraverser()
        self.picker_queue = CollisionHandlerQueue()
        self.picker_ray   = CollisionRay()
        picker_node = CollisionNode('mouseRay')
        picker_node.setFromCollideMask(self.click_mask)
        self.picker_np = self.camera.attachNewNode(picker_node)
        picker_node.addSolid(self.picker_ray)
        self.picker_trav.addCollider(self.picker_np, self.picker_queue)

    def _make_clickable(self, nodepath, info_text: str):
        nodepath.setTag("clickable", "1")
        nodepath.setTag("info", info_text)
        minb, maxb = nodepath.getTightBounds()
        radius = (max((maxb - minb).length(), 0.001) * 0.25) if (minb and maxb) else 0.3
        cnode = CollisionNode("col_" + (nodepath.getName() or "part"))
        cnode.addSolid(CollisionSphere(0, 0, 0, radius))
        cnode.setIntoCollideMask(self.click_mask)
        nodepath.attachNewNode(cnode)

    def _make_marker_clickable(self, nodepath, radius: float, info_text: str):
        nodepath.setTag("clickable", "1")
        nodepath.setTag("info", info_text)
        cnode = CollisionNode("col_marker")
        cnode.addSolid(CollisionSphere(0, 0, 0, radius))
        cnode.setIntoCollideMask(self.click_mask)
        nodepath.attachNewNode(cnode)

    def _on_click_3d(self):
        if not self.mouseWatcherNode.hasMouse():
            return
        mpos = self.mouseWatcherNode.getMouse()
        self.picker_ray.setFromLens(self.camNode, mpos.getX(), mpos.getY())
        self.picker_trav.traverse(self.cupola_root)
        if self.picker_queue.getNumEntries() == 0:
            self.info_label["text"] = ""
            return
        self.picker_queue.sortEntries()
        for i in range(self.picker_queue.getNumEntries()):
            entry = self.picker_queue.getEntry(i)
            np = entry.getIntoNodePath()
            target = np
            while not target.isEmpty() and not target.hasNetTag("clickable"):
                target = target.getParent()
            if not target.isEmpty() and target.hasNetTag("info"):
                self.info_label["text"] = target.getNetTag("info")
                break

    # ----- 3D transforms (keys) -----
    def _model_hpr_delta(self, dh, dp, dr):
        if self.state != "cupola3d" or not hasattr(self, "cupola_model"): return
        h, p, r = self.cupola_model.getHpr()
        self.cupola_model.setHpr(h + dh, p + dp, r + dr)
    def _model_pos_delta(self, dx, dy, dz):
        if self.state != "cupola3d" or not hasattr(self, "cupola_model"): return
        x, y, z = self.cupola_model.getPos()
        self.cupola_model.setPos(x + dx, y + dy, z + dz)
        if self.camera_orbit:
            self.camera_orbit.target.setPos(self.cupola_model.getPos(self.render))
    def _model_scale_mul(self, s):
        if self.state != "cupola3d" or not hasattr(self, "cupola_model"): return
        self.cupola_model.setScale(self.cupola_model.getScale() * s)
    def _model_reset(self):
        if self.state != "cupola3d" or not hasattr(self, "cupola_model"): return
        self.cupola_model.setPos(*MODEL_POS)
        self.cupola_model.setHpr(*MODEL_HPR)
        self.cupola_model.setScale(MODEL_SCALE)
        if self.camera_orbit:
            self.camera_orbit.target.setPos(self.cupola_model.getPos(self.render))
            self.camera_orbit.radius = max(3.0, 4.0 * float(self.cupola_model.getScale().x))

    # =================== WALLS (editor) ===================
    def _build_walls_from_config(self):
        for (x,z,w,h) in WALLS:
            self._add_wall(x, z, w, h)
        if not self.show_walls:
            for w in self.walls:
                w["node"].hide()

    def _add_wall(self, x, z, w, h):
        cm = CardMaker("wall"); cm.setFrame(-w/2, w/2, -h/2, h/2)
        np = self.layer_game.attachNewNode(cm.generate())
        np.setTransparency(TransparencyAttrib.M_alpha)
        np.setColor(1, 0, 0, 0.25)  # red translucent
        np.setPos(x, 0, z)
        wall = {"x":x, "z":z, "w":w, "h":h, "node":np}
        self.walls.append(wall)
        return len(self.walls)-1

    def _toggle_wall_editor(self):
        self.wall_edit = not self.wall_edit
        self._clear_movement()
        if self.wall_edit:
            if self.wall_hint is None:
                self.wall_hint = DirectLabel(parent=self.layer_ui, text="", scale=0.045,
                                             frameColor=(0,0,0,0.6), pos=(0,0,0.9))
            self._update_wall_hint()
        else:
            if self.wall_hint:
                self.wall_hint.destroy(); self.wall_hint = None

    def _toggle_wall_visibility(self):
        self.show_walls = not self.show_walls
        for w in self.walls:
            (w["node"].show() if self.show_walls else w["node"].hide())

    def _cycle_wall(self, step):
        if not self.wall_edit or not self.walls: return
        self.wall_sel = (self.wall_sel + step) % len(self.walls)
        self._highlight_selected()
        self._update_wall_hint()

    def _add_wall_here(self):
        if not self.wall_edit: return
        x, z = self.player.get_pos()
        idx = self._add_wall(x, z, 0.3, 0.3)
        self.wall_sel = idx
        self._highlight_selected()
        self._update_wall_hint()

    def _delete_wall(self):
        if not self.wall_edit or self.wall_sel < 0 or not self.walls: return
        w = self.walls.pop(self.wall_sel)
        w["node"].removeNode()
        self.wall_sel = max(-1, min(self.wall_sel, len(self.walls)-1))
        self._highlight_selected()
        self._update_wall_hint()

    def _nudge_wall(self, dx, dz):
        if not self.wall_edit or self.wall_sel < 0: return
        w = self.walls[self.wall_sel]
        w["x"] += dx; w["z"] += dz
        w["node"].setPos(w["x"], 0, w["z"])
        self._update_wall_hint()

    def _resize_wall(self, dw, dh):
        if not self.wall_edit or self.wall_sel < 0: return
        w = self.walls[self.wall_sel]
        w["w"] = max(0.05, w["w"] + dw)
        w["h"] = max(0.05, w["h"] + dh)
        # rebuild card
        w["node"].removeNode()
        cm = CardMaker("wall"); cm.setFrame(-w["w"]/2, w["w"]/2, -w["h"]/2, w["h"]/2)
        np = self.layer_game.attachNewNode(cm.generate())
        np.setTransparency(TransparencyAttrib.M_alpha)
        np.setColor(1, 0, 0, 0.25)
        np.setPos(w["x"], 0, w["z"])
        w["node"] = np
        self._highlight_selected()
        self._update_wall_hint()

    def _highlight_selected(self):
        for i, w in enumerate(self.walls):
            w["node"].setColor(1, 0, 0, 0.45 if i == self.wall_sel else 0.25)

    def _update_wall_hint(self):
        if not self.wall_hint: return
        if self.wall_sel < 0 or not self.walls:
            self.wall_hint["text"] = ("WALL EDITOR (F8 to exit)\n"
                                      "N=new  Tab/Shift+Tab=select  Delete=remove\n"
                                      "Arrows=move  [ ]=width  ; '=height  Enter=print WALLS")
        else:
            w = self.walls[self.wall_sel]
            self.wall_hint["text"] = (f"Sel {self.wall_sel+1}/{len(self.walls)}  "
                                      f"x={w['x']:.3f} z={w['z']:.3f} w={w['w']:.3f} h={w['h']:.3f}")

    def _print_walls_constant(self):
        if not self.wall_edit: return
        items = ",\n    ".join([f"({w['x']:.3f}, {w['z']:.3f}, {w['w']:.3f}, {w['h']:.3f})" for w in self.walls])
        print("WALLS = [\n    " + items + "\n]")
        self._update_wall_hint()

    # =================== BED (sleep) EDITOR ===================
    def _toggle_bed_editor(self):
        self.bed_edit = not self.bed_edit
        self._clear_movement()
        # asegúrate de que el hitbox sea visible mientras editas
        self.sleep_trigger.set_visible(True)
        if self.bed_icon:
            self.bed_icon.show()
        if self.bed_edit:
            if self.bed_hint is None:
                self.bed_hint = DirectLabel(parent=self.layer_ui, text="", scale=0.045,
                                            frameColor=(0,0,0,0.6), pos=(0,0,0.8))
            self._update_bed_hint()
        else:
            if self.bed_hint:
                self.bed_hint.destroy(); self.bed_hint = None

    def _update_bed_hint(self):
        if not self.bed_hint: return
        self.bed_hint["text"] = (
            "BED EDITOR (F9 to exit)  |  Arrows=move  [ ]=width  ; '=height  |  B=print constants\n"
            f"center=({self.sleep_trigger.x:.3f}, {self.sleep_trigger.z:.3f})  "
            f"size=({self.sleep_trigger.w:.3f}, {self.sleep_trigger.h:.3f})"
        )

    def _bed_nudge(self, dx, dz):
        if not self.bed_edit: return
        x = self.sleep_trigger.x + dx
        z = self.sleep_trigger.z + dz
        self.sleep_trigger.set_center(x, z)
        if self.bed_icon:
            self.bed_icon.set_pos(x, z)
        self._update_bed_hint()

    def _bed_resize(self, dw, dh):
        if not self.bed_edit: return
        w = self.sleep_trigger.w + dw
        h = self.sleep_trigger.h + dh
        self.sleep_trigger.set_size(w, h)
        self._update_bed_hint()

    def _print_bed_trigger_constant(self):
        print(f"SLEEP_TRIGGER_CENTER = ({self.sleep_trigger.x:.3f}, {self.sleep_trigger.z:.3f})")
        print(f"SLEEP_TRIGGER_SIZE   = ({self.sleep_trigger.w:.3f}, {self.sleep_trigger.h:.3f})")

    # =================== ENERGY HUD ===================
    def _load_energy_icons(self):
        self.energy_textures = []
        ok = True
        if len(ENERGY_ICON_PATHS) != 11:
            print("[WARN] ENERGY_ICON_PATHS must have 11 items (100..0).")
            return False
        for p in ENERGY_ICON_PATHS:
            try:
                self.energy_textures.append(self.loader.loadTexture(p))
            except Exception:
                print(f"[WARN] Could not load energy icon: {p}")
                ok = False
        return ok

    def _build_energy_hud(self):
        # Top HUD: long & thin image bar
        if self.energy_icons_loaded:
            self.energy_img = OnscreenImage(parent=self.layer_ui, image=self.energy_textures[0])
            self.energy_img.setTransparency(TransparencyAttrib.M_alpha)
            self.energy_img.setScale(ENERGY_HUD_SCALE_X, 1, ENERGY_HUD_SCALE_Z)  # largo X, alto Z
            self.energy_img.setPos(*ENERGY_HUD_POS)
            self._update_energy_hud()
        else:
            self.energy_lbl = DirectLabel(parent=self.layer_ui,
                                          text=f"Energy: {self.energy_level}/10",
                                          scale=0.055, pos=(-1.05,0,0.9),
                                          frameColor=(0,0,0,0.4))

    def _update_energy_hud(self):
        # energy_level 10..0  → idx 0..10  (100..0)
        idx = max(0, min(10, 10 - self.energy_level))
        if self.energy_img is not None and self.energy_icons_loaded:
            self.energy_img.setImage(self.energy_textures[idx])
        elif self.energy_lbl is not None:
            self.energy_lbl["text"] = f"Energy: {self.energy_level}/10"

    # =================== SLEEP BAR IMAGES ===================
    def _load_sleep_bar_images(self):
        self.sleep_textures = []
        ok = True
        if len(SLEEP_BAR_IMAGE_PATHS) != 11:
            print("[WARN] SLEEP_BAR_IMAGE_PATHS must have 11 items (0..100).")
            return False
        for p in SLEEP_BAR_IMAGE_PATHS:
            try:
                self.sleep_textures.append(self.loader.loadTexture(p))
            except Exception:
                print(f"[WARN] Could not load sleep bar image: {p}")
                ok = False
        return ok

if __name__ == "__main__":
    Game().run()
