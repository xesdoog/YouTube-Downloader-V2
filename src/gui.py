import glfw
import numpy as np
import OpenGL.GL as gl

from cv2        import cvtColor, imread, COLOR_BGR2RGBA, IMREAD_UNCHANGED
from pathlib    import Path
from PIL        import Image
from src        import utils

PARENT_PATH = Path(__file__).parent
ASSETS_PATH = PARENT_PATH / Path(r"assets")
LOG         = utils.LOGGER()


def relative_path(path: str):
    return ASSETS_PATH / Path(path)


def draw_image(path):
    try:
        img  = imread(path, IMREAD_UNCHANGED)
        img  = cvtColor(img, COLOR_BGR2RGBA)
        h, w = img.shape[:2]

        img_data = np.ascontiguousarray(img, dtype=np.uint8)
        texture  = gl.glGenTextures(1)
        gl.glBindTexture(gl.GL_TEXTURE_2D, texture)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
        gl.glPixelStorei(gl.GL_UNPACK_ALIGNMENT, 1)
        gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, w, h, 0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, img_data)
        gl.glBindTexture(gl.GL_TEXTURE_2D, 0)
        return texture, w, h
    except Exception as e:
        LOG.error(f"Unhandled exception in function draw_image(): {e}")
        return None, 0, 0


def fb_to_window_factor(window):
    """
    Frame buffer to window factor.
    """
    win_w, win_h = glfw.get_window_size(window)
    fb_w, fb_h = glfw.get_framebuffer_size(window)

    return max(float(fb_w) / win_w, float(fb_h) / win_h)


def new_window(title: str, width: int, height: int, resizable: bool) -> tuple[object, object, object]:

    if not glfw.init():
        raise Exception("Failed to initialize OpenGL context!")

    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.RESIZABLE, gl.GL_TRUE if resizable else gl.GL_FALSE)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
    glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, gl.GL_TRUE)

    monitor = glfw.get_primary_monitor()
    vidMode = glfw.get_video_mode(monitor)
    pos_x   = vidMode.size.width
    pos_y   = vidMode.size.height

    window       = glfw.create_window(int(width), int(height), title, None, None)
    ibeam_cursor = glfw.create_standard_cursor(glfw.IBEAM_CURSOR)
    hand_cursor  = glfw.create_standard_cursor(glfw.POINTING_HAND_CURSOR)
    icon         = Image.open(relative_path("img/ytd_icon.ico"))
    icon         = icon.convert("RGBA")
    icon_data    = np.array(icon, dtype=np.uint8)
    icon_struct  = [
        icon.width,
        icon.height,
        icon_data
    ]
    glfw.set_window_pos(window, int(pos_x / 2 - width / 2), int(pos_y / 2 - height / 2))
    glfw.set_window_icon(window, 1, icon_struct)
    glfw.make_context_current(window)

    if not window:
        glfw.terminate()
        raise Exception("Failed to initialize window!")

    return window, ibeam_cursor, hand_cursor


def set_cursor(window, cursor):
    glfw.set_cursor(window, cursor)


def set_window_size(window: object, width: int, height: int):
    glfw.set_window_size(window, width, height)


class Icons:
    Search    = "\uf002"
    User      = "\uf007"
    Close     = "\uf00d"
    Gear      = "\uf013"
    Download  = "\uf019"
    Views     = "\uf06e"
    Calendar  = "\uf073"
    Folder    = "\uf07c"
    GitHub    = "\uf09b"
    Spinner   = "\uf110"
    YouTube   = "\uf167"

