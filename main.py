import os, sys
if getattr(sys, 'frozen', False):
    import pyi_splash # type: ignore

from win32gui import FindWindow, SetForegroundWindow
from src      import gui, utils
from pathlib  import Path

LOG         = utils.LOGGER()
PARENT_PATH = Path(__file__).parent
ASSETS_PATH = PARENT_PATH / Path(r"src/assets")
this_window = FindWindow(None, "YouTube Downloader")

if this_window != 0:
    LOG.warning("YTD is aleady running! Only one instance can be launched at once.\n")
    SetForegroundWindow(this_window)
    sys.exit(0)
LOG.OnStart(PARENT_PATH)

import atexit
import imgui
import requests
import subprocess
import webbrowser

from datetime                import datetime, timedelta
from imgui.integrations.glfw import GlfwRenderer
from pytubefix               import YouTube as YT, Channel, Playlist
from threading               import Thread
from time                    import sleep

DOWNLOAD_PATH  = './YTDownloads'
THUMBNAIL_PATH = './.thumbnail'
RESOLUTIONS    = ["Auto",
                 "144p", 
                 "240p",
                 "360p",
                 "480p",
                 "720p",
                 "1080p",
                 "1440p",
                 "2160p",
                ]

Icons                = gui.Icons
res_index            = 0
video_link           = ""
current_filepath     = ""
task_status          = "Idle."
is_available         = False
is_playlist          = False
thumb_downloaded     = False
audio_only           = False
download_in_progress = False
thumb_texture        = None
current_filesize     = 0
progress_value       = 0
video_info           = {
    "title": "",
    "thumbnail": "",
    "duration": "",
    "views": "",
    "channel_url": "",
    "channel_name": "",
    "date": "",
    "video_count": 0,
}


def execute_once(func):
    def wrapper(*args, **kwargs):
        if not wrapper.has_run:
            wrapper.has_run = True
            return func(*args, **kwargs)
    wrapper.has_run = False
    return wrapper


def remove_thumbnails_folder():
    if os.path.exists(THUMBNAIL_PATH):
        if os.path.isfile(f"{THUMBNAIL_PATH}/temp.jpg"):
            os.remove(f"{THUMBNAIL_PATH}/temp.jpg")
        os.rmdir(THUMBNAIL_PATH)
remove_thumbnails_folder()


def open_download_folder():
    subprocess.Popen(f"explorer {DOWNLOAD_PATH}")


def res_path(path: str) -> Path:
    return ASSETS_PATH / Path(path)


def set_cursor(window, cursor):
    if imgui.is_item_hovered():
        gui.set_cursor(window, cursor)


def reset_cursor(window):
    gui.set_cursor(window, None)


def format_time(s: int):
    return str(timedelta(seconds = s))


def get_date_diff(video_date: datetime) -> str:
    now = datetime.today().date()
    vid = video_date.date()
    years  = now.year - vid.year
    months = now.month - vid.month
    days   = now.day - vid.day
    if years > 0:
       return str(years) + (" years ago." if years > 1 else " year ago.")
    elif months > 0:
        return str(months) + (" months ago." if months > 1 else " month ago.")
    else:
        return str(days) + (" days ago." if days > 1 else " day ago.")


def is_valid_url(url) -> bool:
    try:
        _ = YT(url)
        return True
    except:
        return False


def is_playlist_url(url) -> bool:
    try:
        return str(url).find("list=") != -1
    except:
        return False


def is_video_available(url) -> bool:
    try:
        video = YT(url)
        video.check_availability() 
        return True
    except:
        return False


def clear_info_table():
    global video_info
    video_info = {
        "title": "",
        "thumbnail": "",
        "duration": "",
        "views": "",
        "channel_url": "",
        "channel_name": "",
        "date": "",
        "video_count": 0,
    }


def get_video_info():
    global task_status
    global video_info
    global video_link
    global is_available
    global is_playlist

    if len(video_link) > 0:
        if is_valid_url(video_link):
            is_playlist = is_playlist_url(video_link)
            task_status = f"{Icons.Spinner} Loading information..."
            LOG.info(f"Loading information from {video_link}")
            thumbnail_thread()
            if not is_playlist:
                try:
                    video = YT(video_link)
                    if is_video_available(video_link):
                        is_available = True
                        video_info["title"]        = video.title
                        video_info["thumbnail"]    = video.thumbnail_url
                        video_info["duration"]     = format_time(video.length)
                        video_info["views"]        = f"{video.views:,}"
                        video_info["date"]         = get_date_diff(video.publish_date)
                        video_info["channel_url"]  = Channel(video.channel_url)
                        video_info["channel_name"] = Channel(video.channel_url).channel_name
                        LOG.info(f"The link provided is a YouTube video from {video_info["channel_name"]} with {video_info["views"]} total views.")
                        task_status = "Done."
                    else:
                        is_available = False
                        task_status = "This video is unavailable!"
                        clear_info_table()
                        LOG.info("This video is unavailable!")
                except Exception as e:
                    clear_info_table()
                    task_status = f"An error occured. Check the log for more information."
                    LOG.error(f"An error occured while trying to get information from YouTube: {e}")
            else:
                duration_count = 0
                playlist = Playlist(video_link)
                is_available = True
                video_info["title"] = playlist.title
                video_info["thumbnail"] = playlist.thumbnail_url
                video_info["views"] = f"{playlist.views:,}"
                video_info["date"] = ""
                video_info["channel_url"]  = Channel(playlist.owner_url)
                video_info["channel_name"] = Channel(playlist.owner_url).channel_name
                for vid in playlist.videos:
                    video_info["video_count"] += 1
                    duration_count += vid.length
                video_info["duration"] = format_time(duration_count)
                task_status = "Done."
                LOG.info(f"The link provided is a YouTube playlist with {video_info["video_count"]} videos totaling {video_info["duration"]} of watch time.")
        else:
            is_available = False
            task_status = "Invalid link."
            LOG.warning("Failed to get information! The link provided is invalid.")
            clear_info_table()
    else:
        is_available = False
        clear_info_table()
    sleep(3)
    task_status = "Ready."


def download_thumbnail():
    global thumb_downloaded
    thumb_downloaded = False

    while not is_valid_title():
        sleep(0.1)

    try:
        LOG.info("Downloading YouTube Thumbnail...")
        url = video_info["thumbnail"]
        response = requests.get(url, stream = True)
        if response.status_code == 200:
            if not os.path.exists(THUMBNAIL_PATH):
                os.makedirs(THUMBNAIL_PATH)
                # if os.name == "nt":
                #     os.system(f'attrib +h "{THUMBNAIL_PATH}"')

            img_path = Path(THUMBNAIL_PATH) / "temp.jpg"
            with open(img_path, "wb") as file:
                LOG.info("Writing thumbnail image to disk...")
                for chunk in response.iter_content(1024):
                    file.write(chunk)
                file.close()
                thumb_downloaded = True
                LOG.info(f"Thumbnail image saved to {os.path.abspath(THUMBNAIL_PATH)}")
    except Exception as e:
        thumb_downloaded = False
        LOG.error(f"Failed to download thumbnail image: {e}")
        pass


def is_valid_title() -> bool:
    global video_info
    try:
        return is_available and len(video_info) > 0 and len(video_info["title"]) > 0 and video_info["title"] != "Invalid link."
    except:
        return False


def thumbnail_thread():
    Thread(target = download_thumbnail, daemon = True).start()


def colored_button(label: str, color: list, hovered_color: list, active_color: list) -> bool:
    imgui.push_style_color(imgui.COLOR_BUTTON, color[0], color[1], color[2])
    imgui.push_style_color(imgui.COLOR_BUTTON_ACTIVE, hovered_color[0], hovered_color[1], hovered_color[2])
    imgui.push_style_color(imgui.COLOR_BUTTON_HOVERED, active_color[0], active_color[1], active_color[2])
    retbool = imgui.button(label)
    imgui.pop_style_color(3)
    return retbool


def download_video():
    global video_link
    global res_index
    global task_status
    global audio_only
    global current_filesize
    global current_filepath
    global download_in_progress
    global progress_value
    global is_playlist

    try:
        download_in_progress = True
        progress_value = 0
        yt = YT(video_link)
        if not os.path.exists(DOWNLOAD_PATH):
            os.makedirs(DOWNLOAD_PATH)

        try:
            if not audio_only:
                task_status = f"{Icons.Spinner} Fetching video stream..."
                if res_index > 0:
                    stream = yt.streams.filter(
                        res = RESOLUTIONS[res_index], 
                        file_extension = 'mp4', 
                        progressive = True
                        ).first()
                else:
                    stream = yt.streams.get_highest_resolution()
            else:
                task_status = f"{Icons.Spinner} Fetching audio stream..."
                stream = yt.streams.get_audio_only()
        except Exception as e:
            task_status = "Unable to get stream."
            LOG.error(f"Unable to get stream: {e}")
            pass

        try:
            LOG.info("Starting download...")
            current_filesize = stream.filesize
            LOG.info(f"File size: {round(current_filesize / 1024)} KB")
            current_filepath = Path(os.path.abspath(DOWNLOAD_PATH)) / Path(os.path.basename(stream.get_file_path(stream.default_filename)))
            task_status = "Downloading..."
            with open(current_filepath, "wb") as f:
                for chunk in stream.iter_chunks(65536):
                    f.write(chunk)
                    progress_value += len(chunk)
                    sleep(0.001)

            if audio_only:
                old_file = str(current_filepath).replace(".m4a", ".mp3")
                if os.path.exists(old_file):
                    os.remove(old_file)
                base, _ = os.path.splitext(current_filepath)
                os.rename(current_filepath, base + '.mp3')
            task_status = "Download complete."
            LOG.info("Download complete.")
            sleep(3)
            progress_value = 0
            task_status = "Ready."
            download_in_progress = False
        except Exception as e:
            task_status = "Download failed. Check the log for more info."
            LOG.error(f"Download failed: {e}")
            sleep(2)
            task_status = "Ready."
            download_in_progress = False

    except Exception as e:
        task_status = f"An exception has occured! Check the log for more info."
        LOG.error(f"Download failed: {e}")
        sleep(2)
        task_status = "Ready."
        download_in_progress = False


def download_playlist():
    global video_link
    global res_index
    global task_status
    global audio_only
    global current_filesize
    global current_filepath
    global download_in_progress
    global progress_value
    global is_playlist
    global video_info

    playlist_path    = Path(DOWNLOAD_PATH) / Path(video_info["title"])
    streams          = []
    current_stream   = 0
    current_download = 0
    progress_value   = 0

    try:
        download_in_progress = True
        yt = Playlist(video_link)
        if not os.path.exists(DOWNLOAD_PATH):
            os.makedirs(DOWNLOAD_PATH)

        if not os.path.exists(playlist_path):
            os.makedirs(playlist_path)

        if not audio_only:
            for vid in yt.videos:
                current_stream += 1
                try:
                    task_status = f"Getting video stream ({current_stream}/{len(yt.videos)})"
                    LOG.info(f"({current_stream}/{len(yt.videos)}) Getting video stream...")
                    if res_index > 0:
                        stream = vid.streams.filter(
                            res = RESOLUTIONS[res_index], 
                            file_extension = 'mp4', 
                            progressive = True
                        ).first()
                        streams.append(stream)
                    else:
                        stream = vid.streams.get_highest_resolution()
                        streams.append(stream)
                except Exception as e:
                    task_status = "Unable to get video stream! Skipping this video."
                    LOG.warning(f"({({current_stream}/{len(yt.videos)})}): Unable to get video stream! Skipping this video. Traceback: {e}")
                    continue
        else:
            for vid in yt.videos:
                current_stream += 1
                try:
                    task_status = f"Getting audio stream ({current_stream}/{len(yt.videos)})"
                    LOG.info(f"({current_stream}/{len(yt.videos)}) Getting audio stream...")
                    stream = vid.streams.get_audio_only()
                    streams.append(stream)
                except Exception as e:
                    task_status = "Unable to get audio stream! Skipping this video."
                    LOG.warning(f"({({current_stream}/{len(yt.videos)})}): Unable to get audio stream! Skipping this video. Traceback: {e}")
                    continue

        LOG.info("Starting download...")
        for stream in streams:
            current_download += 1
            LOG.info(f"({current_download}/{len(streams)}) Downloading...")
            try:
                current_filesize = stream.filesize
                current_filepath = Path(os.path.abspath(playlist_path)) / Path(os.path.basename(stream.get_file_path(stream.default_filename)))
                task_status = f"Downloading... ({current_download}/{len(streams)})"
                with open(current_filepath, "wb") as f:
                    for chunk in stream.iter_chunks(65536):
                        f.write(chunk)
                        progress_value += len(chunk)
                        sleep(0.001)

                if audio_only:
                    old_file = str(current_filepath).replace(".m4a", ".mp3")
                    if os.path.exists(old_file):
                        os.remove(old_file)
                    base, _ = os.path.splitext(current_filepath)
                    os.rename(current_filepath, base + '.mp3')
            except Exception as e:
                task_status = "Download failed! Skipping this video."
                LOG.warning(f"({current_download}/{len(streams)}): Download failed! Skipping this video.")
                continue

        task_status = "Download complete."
        LOG.info("Download complete.")
        sleep(3)
        progress_value = 0
        download_in_progress = False
        task_status = "Ready."
    except Exception as e:
        task_status = "An error occured! Check the log for more details."
        LOG.error(f"Failed to download YouTube Playlist! Traceback: {e}")
        sleep(2)
        task_status = "Ready."
        download_in_progress = False


def update_progress_bar():
    global progress_value, current_filesize, current_filepath
    while os.path.exists(current_filepath) and progress_value < current_filesize:
        progress_value = os.path.getsize(current_filepath)
        sleep(0.01)


@execute_once
def progress_bar_thread():
    Thread(target = update_progress_bar, daemon = True).start()


def OnDraw():
    global res_index
    global task_status
    global video_info
    global video_link
    global is_available
    global audio_only
    global current_filesize
    global current_filepath
    global download_in_progress

    imgui.create_context()
    window, text_cursor, hand_cursor = gui.new_window("YouTube Downloader", 640, 480, False)
    impl = GlfwRenderer(window)
    font_scaling_factor = gui.fb_to_window_factor(window)
    io = imgui.get_io()
    io.fonts.clear()
    io.font_global_scale = 1.0 / font_scaling_factor
    font_config = imgui.core.FontConfig(merge_mode = True)
    icons_range = imgui.core.GlyphRanges([0xF001, 0xF002, 0xF006, 0xF007, 0xF00D, 0xF00E, 0xF013, 0xF019, 0xF06E, 0xF073, 0xF07C, 0xF09B, 0xF110, 0xF167, 0])
    
    title_font = io.fonts.add_font_from_file_ttf(
        str(res_path("fonts/Rokkitt-Regular.ttf")), 25 * font_scaling_factor,
    )

    small_font = io.fonts.add_font_from_file_ttf(
        str(res_path("fonts/Rokkitt-Regular.ttf")), 16.0 * font_scaling_factor,
    )

    main_font = io.fonts.add_font_from_file_ttf(
        str(res_path("fonts/Rokkitt-Regular.ttf")), 20 * font_scaling_factor,
    )

    io.fonts.add_font_from_file_ttf(
        str(res_path("fonts/fontawesome-webfont.ttf")), 16 * font_scaling_factor,
        font_config, icons_range
    )

    impl.refresh_font_texture()
    thumb_texture, _, _ = gui.draw_image(res_path("img/ytd_splash.png"))

    while not gui.glfw.window_should_close(window):
        gui.glfw.poll_events()
        impl.process_inputs()
        imgui.new_frame()
        win_w, win_h = gui.glfw.get_window_size(window)
        imgui.set_next_window_size(win_w, win_h)
        imgui.set_next_window_position(0, 0)
        imgui.push_style_color(imgui.COLOR_FRAME_BACKGROUND, 0.1, 0.1, 0.1)
        imgui.push_style_color(imgui.COLOR_FRAME_BACKGROUND_ACTIVE, 0.3, 0.3, 0.3)
        imgui.push_style_color(imgui.COLOR_FRAME_BACKGROUND_HOVERED, 0.5, 0.5, 0.5)
        imgui.push_style_color(imgui.COLOR_HEADER, 0.1, 0.1, 0.1)
        imgui.push_style_color(imgui.COLOR_HEADER_ACTIVE, 0.3, 0.3, 0.3)
        imgui.push_style_color(imgui.COLOR_HEADER_HOVERED, 0.5, 0.5, 0.5)
        imgui.push_style_color(imgui.COLOR_BUTTON, 1.0, 0.0, 0.0)
        imgui.push_style_color(imgui.COLOR_BUTTON_ACTIVE, 0.85, 0.0, 0.0)
        imgui.push_style_color(imgui.COLOR_BUTTON_HOVERED, 0.75, 0.0, 0.0)
        imgui.push_style_var(imgui.STYLE_CHILD_ROUNDING, 5)
        imgui.push_style_var(imgui.STYLE_FRAME_ROUNDING, 5)
        imgui.push_style_var(imgui.STYLE_ITEM_SPACING, (5, 5))
        imgui.push_style_var(imgui.STYLE_ITEM_INNER_SPACING, (10, 10))
        imgui.push_style_var(imgui.STYLE_FRAME_PADDING, (6, 6))
        imgui.begin("Main Window", flags =
                    imgui.WINDOW_NO_TITLE_BAR |
                    imgui.WINDOW_NO_RESIZE |
                    imgui.WINDOW_NO_MOVE
                    )
        imgui.push_font(main_font)

        with imgui.begin_child("##main", 0, 390, True):
            imgui.push_text_wrap_pos(620)
            imgui.set_next_item_width(560)
            link_entered, video_link = imgui.input_text_with_hint(
                "##ytlink", "Enter a YouTube video link", video_link, 128,
                flags = imgui.INPUT_TEXT_CHARS_NO_BLANK | imgui.INPUT_TEXT_ENTER_RETURNS_TRUE
            )
            set_cursor(window, text_cursor)
            imgui.same_line()
            search_button_pressed = colored_button(f"  {Icons.Search}  ", [0.1, 0.1, 0.1], [0.2, 0.2, 0.2], [0.3, 0.3, 0.3])
            if len(video_link) > 0 and (link_entered or search_button_pressed):
                video_info_thread = None
                clear_info_table()
                video_info_thread = Thread(target = get_video_info, daemon = True)
                video_info_thread.start()
            imgui.dummy(1, 15)
            if is_valid_title():
                if thumb_downloaded:
                    with imgui.begin_child("##thumbnail", 320, 220, True):
                        thumb_texture, _, _ = gui.draw_image(Path(THUMBNAIL_PATH) / "temp.jpg")
                        imgui.image(thumb_texture, 300, 200)
                    imgui.same_line()
                
                with imgui.begin_child("##vid_info", -1, 220, False):
                    imgui.push_text_wrap_pos(290)
                    imgui.dummy(1, 10)
                    with imgui.font(title_font):
                        imgui.text(video_info["title"])
                        set_cursor(window, hand_cursor)
                        if imgui.is_item_hovered() and imgui.is_mouse_clicked(0):
                            webbrowser.open(video_link)

                    imgui.dummy(1, 12)
                    imgui.text(f"{Icons.User} {video_info["channel_name"]}")
                    set_cursor(window, hand_cursor)
                    if imgui.is_item_hovered() and imgui.is_mouse_clicked(0):
                        webbrowser.open(video_info["channel_url"])
                    imgui.text(f"{Icons.Views} {video_info["views"]} views.")
                    if not is_playlist:
                        imgui.text(f"{Icons.Calendar} {video_info["date"]}")
                    else:
                        imgui.text(f"{Icons.YouTube} {video_info["video_count"]} videos.")
                    imgui.pop_text_wrap_pos()
                if not video_info_thread.is_alive():
                    imgui.dummy(1, 5)
                    _, audio_only = imgui.checkbox("Audio Only (MP3)", audio_only)
                    if not audio_only:
                        imgui.same_line(spacing=10)
                        imgui.set_next_item_width(200)
                        _, res_index = imgui.combo("Video Resolution", res_index, RESOLUTIONS)
                    imgui.dummy(1, 5)
                    download_label = " Download" if not is_playlist else " Download Playlist"
                    if not download_in_progress:
                        if imgui.button(Icons.Download + download_label):
                            task_status = f"{Icons.Spinner} Starting download..."
                            Thread(target = download_video if not is_playlist else download_playlist, daemon = True).start()
                        imgui.same_line(spacing=10)
                        if imgui.button(f"{Icons.Close} Clear"):
                            clear_info_table()
                            remove_thumbnails_folder()
                            video_link = ""
                            task_status = "Idle."
                    else:
                        imgui.button(Icons.Spinner)

            imgui.pop_text_wrap_pos()
        with imgui.begin_child("##status", -1, 40):
            imgui.push_text_wrap_pos(win_w - 5)
            imgui.text(f"Status: {task_status}")
            imgui.pop_text_wrap_pos()

            if download_in_progress:
                if current_filesize > 0:
                    prgrs = progress_value / current_filesize
                    if is_playlist:
                        prgrs = prgrs / video_info["video_count"]
                    imgui.progress_bar(prgrs, (620, 5))

        imgui.dummy(win_w - 60, 1)
        imgui.same_line()
        imgui.text(Icons.GitHub)
        if imgui.is_item_hovered():
            set_cursor(window, hand_cursor)
            imgui.push_style_var(imgui.STYLE_WINDOW_ROUNDING, 10)
            with imgui.font(small_font):
                imgui.set_tooltip('Click to visit the GitHub repo')
            imgui.pop_style_var()
            if imgui.is_item_clicked():
                webbrowser.open("https://github.com/xesdoog/YouTube-Downloader-V2")
        imgui.pop_font()
        imgui.pop_style_color(9)
        imgui.pop_style_var(5)
        imgui.end()

        gui.gl.glClearColor(1.0, 1.0, 1.0, 1)
        gui.gl.glClear(gui.gl.GL_COLOR_BUFFER_BIT)
        imgui.render()
        if not imgui.is_any_item_hovered():
            reset_cursor(window)
        impl.render(imgui.get_draw_data())
        gui.glfw.swap_buffers(window)
        gui.gl.glDeleteTextures([thumb_texture])

    impl.shutdown()
    gui.glfw.terminate()


@atexit.register
def OnExit():
    LOG.info("Closing application...\n\nFarewell!\n")
    remove_thumbnails_folder()

if __name__ == "__main__":
    if getattr(sys, 'frozen', False):
        pyi_splash.close()
    OnDraw()