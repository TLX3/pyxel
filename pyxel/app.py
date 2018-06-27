import math
import time
import glfw
from .renderer import Renderer
from .key import KEY_LEFT_BUTTON, KEY_MIDDLE_BUTTON, KEY_RIGHT_BUTTON

CAPTION = 'Pyxel Window'
SCALE = 4
PALETTE = [
    0x000000, 0x1d2b53, 0x7e2553, 0x008751, 0xab5236, 0x5f574f, 0xc2c3c7,
    0xfff1e8, 0xff004d, 0xffa300, 0xffec27, 0x00e436, 0x29adff, 0x83769c,
    0xff77a8, 0xffccaa
]
FPS = 30
BORDER_WIDTH = 0
BORDER_COLOR = 0x101018

PERF_MEASURE_COUNT = 10


class App:
    def __init__(self,
                 width,
                 height,
                 *,
                 caption=CAPTION,
                 scale=SCALE,
                 palette=PALETTE,
                 fps=FPS,
                 border_width=BORDER_WIDTH,
                 border_color=BORDER_COLOR):
        self._width = width
        self._height = height
        self._caption = caption
        self._scale = scale
        self._palette = palette[:]
        self._fps = fps
        self._border_width = border_width
        self._border_color = border_color

        self._key_state = {}
        self._mouse_x = 0
        self._mouse_y = 0

        self._frame_count = 0
        self._next_update_time = 0
        self._one_frame_time = 1 / fps

        self._perf_monitor_is_enabled = False
        self._perf_fps_count = 0
        self._perf_fps_start_time = 0
        self._perf_fps = 0
        self._perf_update_count = 0
        self._perf_update_total_time = 0
        self._perf_update_time = 0
        self._perf_draw_count = 0
        self._perf_draw_total_time = 0
        self._perf_draw_time = 0

        # initialize window
        if not glfw.init():
            exit()

        self._window = glfw.create_window(width * scale + border_width,
                                          height * scale + border_width,
                                          caption, None, None)
        if not self._window:
            glfw.terminate()
            exit()

        glfw.make_context_current(self._window)
        glfw.set_window_size_limits(self._window, width, height,
                                    glfw.DONT_CARE, glfw.DONT_CARE)
        self._hidpi_scale = (glfw.get_framebuffer_size(self._window)[0] /
                             glfw.get_window_size(self._window)[0])
        self._update_viewport()

        glfw.set_key_callback(self._window, self._key_callback)
        glfw.set_cursor_pos_callback(self._window, self._cursor_pos_callback)
        glfw.set_mouse_button_callback(self._window,
                                       self._mouse_button_callback)

        # initialize renderer
        self._renderer = Renderer(width, height)
        self.bank = self._renderer.bank
        self.clip = self._renderer.clip
        self.pal = self._renderer.pal
        self.cls = self._renderer.cls
        self.pix = self._renderer.pix
        self.line = self._renderer.line
        self.rect = self._renderer.rect
        self.rectb = self._renderer.rectb
        self.circ = self._renderer.circ
        self.circb = self._renderer.circb
        self.blt = self._renderer.blt
        self.text = self._renderer.text

    @property
    def width(self):
        return self._width

    @property
    def height(self):
        return self._height

    @property
    def frame_count(self):
        return self._frame_count

    @property
    def mouse_x(self):
        return self._mouse_x

    @property
    def mouse_y(self):
        return self._mouse_y

    def btn(self, key):
        return self._key_state.get(key, 0) > 0

    def btnp(self, key, hold=0, period=0):
        press_frame = self._key_state.get(key, 0)

        return (press_frame == self._frame_count
                or press_frame > 0 and period > 0 and
                (self._frame_count - press_frame - hold) % period == 0)

    def btnr(self, key):
        return self._key_state.get(key, 0) == -self.frame_count

    def run(self):
        self._frame_count = 1
        self._next_update_time = self._perf_fps_start_time = time.time()

        while not glfw.window_should_close(self._window):
            glfw.poll_events()

            self._measure_fps()
            self._update_viewport()
            self._update_frame()
            self._draw_frame()

            glfw.swap_buffers(self._window)

        glfw.terminate()

    def update(self):
        pass

    def draw(self):
        pass

    def _key_callback(self, window, key, scancode, action, mods):
        if action == glfw.PRESS:
            self._key_state[key] = self._frame_count
        elif action == glfw.RELEASE:
            self._key_state[key] = -self._frame_count

    def _cursor_pos_callback(self, window, xpos, ypos):
        left = self._viewport_left
        top = self._viewport_top
        scale = self._viewport_scale

        self._mouse_x = int((xpos - left) / scale)
        self._mouse_y = int((ypos - top) / scale)

    def _mouse_button_callback(self, window, button, action, mods):
        if button == glfw.MOUSE_BUTTON_LEFT:
            button = KEY_LEFT_BUTTON
        elif button == glfw.MOUSE_BUTTON_MIDDLE:
            button = KEY_MIDDLE_BUTTON
        elif button == glfw.MOUSE_BUTTON_RIGHT:
            button = KEY_RIGHT_BUTTON
        else:
            return

        if action == glfw.PRESS:
            self._key_state[button] = self._frame_count
        elif action == glfw.RELEASE:
            self._key_state[button] = -self._frame_count

    def _update_viewport(self):
        win_width, win_height = glfw.get_window_size(self._window)
        scale_x = win_width // self._width
        scale_y = win_height // self._height
        scale = min(scale_x, scale_y)

        self._viewport_scale = scale
        self._viewport_width = self._width * scale
        self._viewport_height = self._height * scale
        self._viewport_left = (win_width - self._viewport_width) // 2
        self._viewport_top = (win_height - self._viewport_height) // 2
        self._viewport_bottom = (
            win_height - self._viewport_height - self._viewport_top)

    def _update_frame(self):
        # wait for update time
        while True:
            cur_time = time.time()
            wait_time = self._next_update_time - cur_time

            if wait_time > 0:
                time.sleep(wait_time)
            else:
                break

        update_count = math.floor(-wait_time / self._one_frame_time) + 1
        self._next_update_time += update_count * self._one_frame_time

        # update frame
        for _ in range(update_count):
            update_start_time = time.time()

            self._check_special_input()
            self.update()
            self._frame_count += 1

            self._measure_update_time(update_start_time)

    def _draw_frame(self):
        draw_start_time = time.time()

        self.draw()

        self._draw_perf_monitor()

        hs = self._hidpi_scale
        self._renderer.render(
            self._viewport_left * hs, self._viewport_bottom * hs,
            self._viewport_width * hs, self._viewport_height * hs,
            self._palette, self._border_color)

        self._measure_draw_time(draw_start_time)

    def _check_special_input(self):
        if self.btn(glfw.KEY_LEFT_ALT) or self.btn(glfw.KEY_RIGHT_ALT):
            if self.btnp(glfw.KEY_ENTER):
                monitor = glfw.get_primary_monitor()
                (width, height), _, _ = glfw.get_video_mode(monitor)
                glfw.set_window_monitor(self._window, monitor, 0, 0, width,
                                        height, 0)

            if self.btnp(glfw.KEY_P):
                self._perf_monitor_is_enabled = (
                    not self._perf_monitor_is_enabled)

        if self.btnp(glfw.KEY_ESCAPE):
            glfw.set_window_should_close(self._window, True)

    def _measure_fps(self):
        cur_time = time.time()
        self._perf_fps_count += 1

        if self._perf_fps_count == PERF_MEASURE_COUNT:
            self._perf_fps = self._perf_fps_count / (
                cur_time - self._perf_fps_start_time)
            self._perf_fps_count = 0
            self._perf_fps_start_time = cur_time

    def _measure_update_time(self, update_start_time):
        self._perf_update_count += 1
        self._perf_update_total_time += time.time() - update_start_time

        if self._perf_update_count == PERF_MEASURE_COUNT:
            self._perf_update_time = (
                self._perf_update_total_time / self._perf_update_count) * 1000
            self._perf_update_total_time = 0
            self._perf_update_count = 0

    def _measure_draw_time(self, draw_start_time):
        self._perf_draw_count += 1
        self._perf_draw_total_time += time.time() - draw_start_time

        if self._perf_draw_count == PERF_MEASURE_COUNT:
            self._perf_draw_time = (
                self._perf_draw_total_time / self._perf_draw_count) * 1000
            self._perf_draw_total_time = 0
            self._perf_draw_count = 0

    def _draw_perf_monitor(self):
        if not self._perf_monitor_is_enabled:
            return

        fps = '{:.2f}'.format(self._perf_fps)
        update = '{:.2f}'.format(self._perf_update_time)
        draw = '{:.2f}'.format(self._perf_draw_time)

        self.text(1, 0, fps, 1)
        self.text(0, 0, fps, 9)
        self.text(1, 6, update, 1)
        self.text(0, 6, update, 9)
        self.text(1, 12, draw, 1)
        self.text(0, 12, draw, 9)
