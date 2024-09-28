import tkinter as tk
import urllib.request
from typing import Union
from bs4 import BeautifulSoup
from urllib.error import URLError
import logging
import sys
import os
import re
from threading import Thread
import requests
import time
import subprocess
import platform
from zipfile import ZipFile
from io import BytesIO


def setup_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    # Prevent passing events to the handlers of higher severity
    logger.propagate = False
    # Set formatter for the logger.
    handler = logging.StreamHandler()
    handler.setFormatter(CustomFormatter())
    logger.addHandler(handler)
    return logger


LOADING = 24
SUCCESS = 25


class CustomFormatter(logging.Formatter):
    green = "\033[1;92m"
    yellow = "\033[1;93m"
    red = "\033[1;31m"
    blue = "\033[1;94m"
    reset = "\033[0m"
    format = "%(asctime)s - %(levelname)s - %(name)s - %(message)s "

    FORMATS = {
        logging.DEBUG: blue + format + reset,
        logging.INFO: blue + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: red + format + reset,
        LOADING: yellow + format + reset,
        SUCCESS: green + format + reset,
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt="%Y-%m-%d %H:%M:%S")
        return formatter.format(record)


logger = setup_logger(__name__)
logging.addLevelName(LOADING, "LOADING")
logging.addLevelName(SUCCESS, "SUCCESS")
VOE_PATTERNS = [re.compile(r"'hls': '(?P<url>.+)'"),
                re.compile(r'prompt\("Node",\s*"(?P<url>[^"]+)"'),
                re.compile(r"window\.location\.href = '([^']+)'")]
STREAMTAPE_PATTERN = re.compile(r'get_video\?id=[^&\'\s]+&expires=[^&\'\s]+&ip=[^&\'\s]+&token=[^&\'\s]+\'')


class ProviderError(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class LanguageError(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


def loading(self, message, *args, **kwargs):
    if self.isEnabledFor(LOADING):
        self._log(LOADING, message, args, **kwargs)


def success(self, message, *args, **kwargs):
    if self.isEnabledFor(SUCCESS):
        self._log(SUCCESS, message, args, **kwargs)


def get_redirect_link_by_provider(site_url, internal_link, language, provider):
    local_provider_priority = provider_priority.copy()
    local_provider_priority.remove(provider)
    try:
        return get_redirect_link(site_url, internal_link, language, provider)
    except ProviderError:
        logger.info(f"Provider {provider} failed. Trying {local_provider_priority[0]} next.")
        try:
            return get_redirect_link(site_url, internal_link, language, local_provider_priority[0])
        except ProviderError:
            logger.info(f"Provider {local_provider_priority[0]} failed. Trying {local_provider_priority[1]} next.")
            return get_redirect_link(site_url, internal_link, language, local_provider_priority[1])


def get_redirect_link(site_url, html_link, language, provider):
    # if you encounter issues with captchas use this line below
    # html_link = open_captcha_window(html_link)
    html_response = urllib.request.urlopen(html_link)
    href_value = get_href_by_language(html_response, language, provider)
    link_to_redirect = site_url + href_value
    logger.debug("Link to redirect is: " + link_to_redirect)
    return link_to_redirect, provider


def restructure_dict(given_dict):
    new_dict = {}
    already_seen = set()
    for key, value in given_dict.items():
        new_dict[value] = set([element.strip() for element in key.split(',')])
    return_dict = {}
    for key, values in new_dict.items():
        for value in values:
            if value in already_seen and value in return_dict:
                del return_dict[value]
                continue
            if value not in already_seen and value not in return_dict:
                return_dict[value] = key
                already_seen.add(value)
    return return_dict


def extract_lang_key_mapping(soup):
    lang_key_mapping = {}
    # Find the div with class "changeLanguageBox"
    change_language_div = soup.find("div", class_="changeLanguageBox")
    if change_language_div:
        # Find all img tags inside the div to extract language and data-lang-key
        lang_elements = change_language_div.find_all("img")
        for lang_element in lang_elements:
            language = lang_element.get("alt", "") + "," + lang_element.get("title", "")
            data_lang_key = lang_element.get("data-lang-key", "")
            if language and data_lang_key:
                lang_key_mapping[language] = data_lang_key
    return restructure_dict(lang_key_mapping)


def get_href_by_language(html_content, language, provider):
    soup = BeautifulSoup(html_content, "html.parser")
    lang_key_mapping = extract_lang_key_mapping(soup)

    # Debug logs
    logger.debug(f"Language mapping: {lang_key_mapping}")
    logger.debug(f"Given language: {language}")

    # Find the data-lang-key value based on the input language
    lang_key = lang_key_mapping.get(language)
    if lang_key is None:
        raise LanguageError(logger.error(f"Invalid language input. Supported languages: "
                                         f"{list(lang_key_mapping.keys())}"))
    # Find all <li> elements with the given data-lang-key value and h4=provider
    matching_li_elements = soup.find_all("li", {"data-lang-key": lang_key})
    matching_li_element = next((li_element for li_element in matching_li_elements
                                if li_element.find("h4").get_text() == provider), None)
    # Check if any matching elements were found and return the corresponding href
    if matching_li_element:
        href = matching_li_element.get("data-link-target", "")
        return href
    raise ProviderError(logger.error(f"No matching download found for language '{language}' and provider '{provider}'"))


def parse_cli_arguments(default: Union[str, int], position: int) -> Union[str, int]:
    try:
        cli_argument: str = sys.argv[position]
        logger.debug(f"cli argument detected on position:{position} with value:{cli_argument}")
        if type(default) is int:
            cli_argument: int = int(cli_argument)
        return cli_argument
    except IndexError:
        logger.debug(f"no cli argument detected on position:{position}. Using default value:{default}")
        return default


def find_cache_url(url, provider):
    global cache_url_attempts
    logger.debug("Enterd {} to cache".format(provider))
    try:
        html_page = urllib.request.urlopen(url)
    except URLError as e:
        logger.warning(f"{e}")
        logger.info("Trying again to read HTML Element...")
        if cache_url_attempts < 5:
            return find_cache_url(url, provider)
        else:
            logger.error("Could not find cache url HTML for {}.".format(provider))
            return 0
    try:
        if provider == "Vidoza":
            soup = BeautifulSoup(html_page, features="html.parser")
            cache_link = soup.find("source").get("src")
        elif provider == "VOE":
            html_page = html_page.read().decode('utf-8')
            for VOE_PATTERN in VOE_PATTERNS:
                match = VOE_PATTERN.search(html_page)
                if match:
                    if match.group(0).startswith("window.location.href"):
                        logger.info("Found window.location.href. Redirecting...")
                        return find_cache_url(match.group(1), provider)
                    cache_link = match.group(1)
                    if cache_link and cache_link.startswith("https://"):
                        return cache_link
            logger.error("Could not find cache url for {}.".format(provider))
            return 0
        elif provider == "Streamtape":
            cache_link = STREAMTAPE_PATTERN.search(html_page.read().decode('utf-8'))
            if cache_link is None:
                return find_cache_url(url, provider)
            cache_link = "https://" + provider + ".com/" + cache_link.group()[:-1]
            logger.debug(f"This is the found video link of {provider}: {cache_link}")
    except AttributeError as e:
        logger.error(f"ERROR: {e}")
        logger.info("Trying again...")
        if cache_url_attempts < 5:
            cache_url_attempts += 1
            return find_cache_url(url, provider)
        else:
            logger.error("Could not find cache url for {}.".format(provider))
            return 0

    logger.debug("Exiting {} to Cache".format(provider))
    return cache_link


def download_and_convert_hls_stream(hls_url, file_name):
    global downloads_list
    if os.path.exists("ffmpeg.exe"):
        ffmpeg_path = "ffmpeg.exe"
    elif os.path.exists("src/ffmpeg.exe"):
        ffmpeg_path = "src/ffmpeg.exe"
    else:
        ffmpeg_path = "ffmpeg"
    try:
        current_downloads.append(file_name)
        ffmpeg_cmd = [ffmpeg_path, '-i', hls_url, '-c', 'copy', file_name]
        if platform.system() == "Windows":
            subprocess.run(ffmpeg_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        else:
            subprocess.run(ffmpeg_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        logger.success("Finished download of {}.".format(file_name))
    except subprocess.CalledProcessError as e:
        logger.error("Server error. Could not download {}. Please manually download it later.".format(file_name))
        remove_file(file_name)
    current_downloads.remove(file_name)
    if len(current_downloads) == 1 and shutdown:
        os.system('shutdown -s')
    downloads_list.destroy()
    downloads_list = tk.OptionMenu(root, downloads, *current_downloads)
    downloads_list.configure(bg=bg_2nd, fg=fg, border=0, borderwidth=0, highlightthickness=0, activeforeground=fg, font=("Open Sans", 15), activebackground=bg_2nd, indicatoron=False)
    downloads_list["menu"].configure(bg=bg_2nd, fg=fg, border=0, borderwidth=0, activeforeground=fg, font=("Open Sans", 15), activebackground=bg)
    downloads_list.grid(row=91, column=0, sticky="w", padx=13)


def download(link, file_name):
    global downloads_list
    retry_count = 0
    current_downloads.append(file_name)
    while True:
        logger.debug("Entered download with these vars: Link: {}, File_Name: {}".format(link, file_name))
        r = requests.get(link, stream=True)
        with open(file_name, 'wb') as f:
            for chunk in r.iter_content(1024):
                f.write(chunk)
        if os.path.getsize(file_name) != 0:
            logger.success("Finished download of {}.".format(file_name))
            break
        elif retry_count == 1:
            logger.error("Server error. Could not download {}. Please manually download it later.".format(file_name))
            remove_file(file_name)
            break
        else:
            logger.info("Download did not complete! File {} will be retryd in a few seconds.".format(file_name))
            logger.debug("URL: {}, filename {}".format(link, file_name))
            time.sleep(20)
            retry_count = 1
    current_downloads.remove(file_name)
    if len(current_downloads) == 1 and shutdown:
        os.system('shutdown -s')
    downloads_list.destroy()
    downloads_list = tk.OptionMenu(root, downloads, *current_downloads)
    downloads_list.configure(bg=bg_2nd, fg=fg, border=0, borderwidth=0, highlightthickness=0, activeforeground=fg, font=("Open Sans", 15), activebackground=bg_2nd, indicatoron=False)
    downloads_list["menu"].configure(bg=bg_2nd, fg=fg, border=0, borderwidth=0, activeforeground=fg, font=("Open Sans", 15), activebackground=bg)
    downloads_list.grid(row=91, column=0, sticky="w", padx=13)


def remove_file(path):
    logger.debug("Removing {path}")
    if os.path.exists(path):
        os.remove(path)
        logger.info(f"Removed {path}")
    else:
        logger.error(f"Could not remove {path}")


def get_latest_version():  # get latest version
    file = urllib.request.urlopen("https://raw.githubusercontent.com/NINJAMINEBRO/Aniworld-Downloader/main/version")
    lines = ""
    for line in file:
        lines += line.decode("utf-8")
    if float(lines[:-1]) > version:
        print(f"Update available\ncurrent version: {version}\nlatest version: {lines}Download latest version on: https://ninjaminebro.itch.io/aniworld-downloader\n")
    return float(lines[:-1])


def update():
    http_response = urllib.request.urlopen("https://github.com/NINJAMINEBRO/Aniworld-Downloader/raw/main/Aniworld-Downloader.zip")
    zipfile = ZipFile(BytesIO(http_response.read()))
    try:
        os.rename(f"{os.getcwd()}\\Aniworld Downloader by NMB.exe", f"{os.getcwd()}\\Aniworld Downloader by NMB old.exe")
    except Exception as e:
        print(f"coudn't find Aniworld Downloader")
    zipfile.extractall(path=os.getcwd())
    print("downloaded newest version and unziped in current folder")
    os.startfile(f"{os.getcwd()}\\Aniworld Downloader by NMB")
    root.destroy()


if "ffmpeg.exe" not in os.listdir(os.getcwd()):
    print(f"WARNING: ffmpeg is not installed or not in this folder, VOE will not work unless ffmpeg is in the same folder as Aniworld-Downloader")
if "Aniworld-Downloader by NMB old.exe" in os.listdir(os.getcwd()):
    try:
        os.remove(f"{os.getcwd()}\\Aniworld-Downloader by NMB old.exe")
    except Exception as e:
        print(f"something went wrong\n{e}")

logging.Logger.loading = loading
logging.Logger.success = success
logging.basicConfig(level=logging.INFO)
provider_priority = ["VOE", "Vidoza", "Streamtape"]
site_url = {"serie": "https://s.to", "anime": "https://aniworld.to"}

bg = "#121C22"
bg_2nd = "#637CF9"
fg = "#FFFFFF"
episodes = []
seasons = 0
movies = 0
current_downloads = ["Current Downloads"]
types = ["Episodes", "Movies"]
shutdown = False
languages = ["German", "Ger-Sub", "Eng-Sub"]

version = 1.00
latest_version = get_latest_version()
root = tk.Tk()
root.title("Aniworld Downloader")
root.configure(bg=bg)
root.resizable(False, False)
root.geometry("800x500")

for i in range(201):
    root.rowconfigure(i, weight=1)
root.columnconfigure(0, weight=1)


def entry_focus_in(entry):
    text = entry.get()
    if text == "Link: ":
        entry.delete(0, "end")


def entry_focus_out(entry):
    text = entry.get()
    if not text:
        entry.insert(0, "Link: ")


def focus_out():
    x, y = root.winfo_pointerxy()
    widget = root.winfo_containing(x, y)
    if ".!entry" not in str(widget):
        root.focus()


def confirm_link(link):
    global seasons, episodes, url, movies
    seasons, movies = 0, 0
    link = link_validator(link)
    url = link
    if link:
        if typev.get() == "Episodes":
            seasons = get_season(link)
        elif typev.get() == "Movies":
            movies = get_movies(link)
        if seasons != 0:
            episodes = []
            for i in range(seasons):
                episodes.append(get_episodes(link, i+1))
            build_menu_2(link[link.index("stream/")+7:-1].replace("-", " ").upper())
        elif movies != 0:
            build_menu_2(link[link.index("stream/")+7:-1].replace("-", " ").upper())
        else:
            print("Anime/Series not found")
    else:
        print("That Link is invalid")


def link_validator(link):
    if "https://aniworld.to/" in link or "https://s.to/" in link or "https://bs.to/" in link:
        if link[-1] != "/":
            link += "/"
        return link
    return False


def get_movies(url_path):
    logger.debug("Entered get_movies")
    url = "{}filme/".format(url_path)
    movie_count = 1
    html_page = urllib.request.urlopen(url, timeout=50)
    soup = BeautifulSoup(html_page, features="html.parser")
    for link in soup.findAll('a'):
        movie = str(link.get("href"))
        if "/filme/film-{}".format(movie_count) in movie:
            movie_count = movie_count + 1
    logger.debug("Now leaving Function get_movies")
    return movie_count - 1


def get_season(url_path):
    counter_seasons = 1
    html_page = urllib.request.urlopen(url_path, timeout=50)
    soup = BeautifulSoup(html_page, features="html.parser")
    for link in soup.findAll('a'):
        seasons = str(link.get("href"))
        if "/staffel-{}".format(counter_seasons) in seasons:
            counter_seasons = counter_seasons + 1
    return counter_seasons - 1


def get_episodes(url_path, season_count):
    url = "{}staffel-{}/".format(url_path, season_count)
    episode_count = 1
    html_page = urllib.request.urlopen(url, timeout=50)
    soup = BeautifulSoup(html_page, features="html.parser")
    for link in soup.findAll('a'):
        episode = str(link.get("href"))
        if "/staffel-{}/episode-{}".format(season_count, episode_count) in episode:
            episode_count = episode_count + 1
    return episode_count - 1


def from_season():
    global season_start, season_end, episode_start_menu, episode_end_menu, episode_end
    from_season = int(season_start.get()[8:])
    to_season = int(season_end.get()[8:])
    if from_season > to_season:
        to_season = from_season
        season_end.set("Season: " + str(to_season))

    episode_start_menu.destroy()
    episode_start_menu = tk.OptionMenu(root, episode_start, *["Episode: " + str(x + 1) for x in range(episodes[from_season-1])], command=lambda x: from_episode())
    episode_start_menu.configure(bg=bg_2nd, fg=fg, border=0, borderwidth=0, highlightthickness=0, activeforeground=fg, font=("Open Sans", 15), activebackground=bg_2nd, indicatoron=False, width=11)
    episode_start_menu["menu"].configure(bg=bg_2nd, fg=fg, activeforeground=fg, font=("Open Sans", 15), activebackground=bg)
    episode_start_menu.grid(row=35, column=0, sticky="w", padx=30)
    episode_range = [x+1 for x in range(episodes[from_season-1])]
    from_episodev = int(episode_start.get()[9:])
    if from_episodev not in episode_range:
        from_episodev = "Episode: " + str(episode_range[-1])
        episode_start.set(from_episodev)
    episode_end_menu.destroy()
    episode_end_menu = tk.OptionMenu(root, episode_end, *["Episode: " + str(x + 1) for x in range(episodes[to_season - 1])], command=lambda x: to_episode())
    episode_end_menu.configure(bg=bg_2nd, fg=fg, border=0, borderwidth=0, highlightthickness=0, activeforeground=fg, font=("Open Sans", 15), activebackground=bg_2nd, indicatoron=False, width=11)
    episode_end_menu["menu"].configure(bg=bg_2nd, fg=fg, activeforeground=fg, font=("Open Sans", 15), activebackground=bg)
    episode_end_menu.grid(row=35, column=0, sticky="w", padx=60 + 127)
    episode_range = [x+1 for x in range(episodes[to_season-1])]
    to_episodev = int(episode_end.get()[9:])
    if to_episodev not in episode_range:
        to_episodev = "Episode: " + str(episode_range[-1])
        episode_end.set(to_episodev)
    from_episode()


def to_season():
    global season_start, season_end, episode_end_menu, episode_start_menu, episode_start
    from_season = int(season_start.get()[8:])
    to_season = int(season_end.get()[8:])
    if from_season > to_season:
        from_season = to_season
        season_start.set("Season: " + str(from_season))

    episode_end_menu.destroy()
    episode_end_menu = tk.OptionMenu(root, episode_end, *["Episode: " + str(x + 1) for x in range(episodes[to_season - 1])], command=lambda x: to_episode())
    episode_end_menu.configure(bg=bg_2nd, fg=fg, border=0, borderwidth=0, highlightthickness=0, activeforeground=fg, font=("Open Sans", 15), activebackground=bg_2nd, indicatoron=False, width=11)
    episode_end_menu["menu"].configure(bg=bg_2nd, fg=fg, activeforeground=fg, font=("Open Sans", 15), activebackground=bg)
    episode_end_menu.grid(row=35, column=0, sticky="w", padx=60 + 127)
    episode_range = [x+1 for x in range(episodes[to_season-1])]
    to_episodev = int(episode_end.get()[9:])
    if to_episodev not in episode_range:
        to_episodev = "Episode: " + str(episode_range[-1])
        episode_end.set(to_episodev)
    episode_start_menu.destroy()
    episode_start_menu = tk.OptionMenu(root, episode_start, *["Episode: " + str(x + 1) for x in range(episodes[from_season-1])], command=lambda x: from_episode())
    episode_start_menu.configure(bg=bg_2nd, fg=fg, border=0, borderwidth=0, highlightthickness=0, activeforeground=fg, font=("Open Sans", 15), activebackground=bg_2nd, indicatoron=False, width=11)
    episode_start_menu["menu"].configure(bg=bg_2nd, fg=fg, activeforeground=fg, font=("Open Sans", 15), activebackground=bg)
    episode_start_menu.grid(row=35, column=0, sticky="w", padx=30)
    episode_range = [x+1 for x in range(episodes[from_season-1])]
    from_episodev = int(episode_start.get()[9:])
    if from_episodev not in episode_range:
        from_episodev = "Episode: " + str(episode_range[-1])
        episode_start.set(from_episodev)
    to_episode()


def from_episode():
    global episode_start, episode_end, season_start, season_end
    from_seasonv = season_start.get()[8:]
    to_seasonv = season_end.get()[8:]
    from_episodev = int(episode_start.get()[9:])
    to_episodev = int(episode_end.get()[9:])
    if from_seasonv == to_seasonv and from_episodev > to_episodev:
        to_episodev = from_episodev
        episode_end.set("Episode: " + str(to_episodev))


def to_episode():
    global episode_start, episode_end, season_start, season_end
    from_seasonv = season_start.get()[8:]
    to_seasonv = season_end.get()[8:]
    from_episodev = int(episode_start.get()[9:])
    to_episodev = int(episode_end.get()[9:])
    if from_seasonv == to_seasonv and from_episodev > to_episodev:
        from_episodev = to_episodev
        episode_start.set("Episode: " + str(from_episodev))


def from_movie():
    global movie_start, movie_end
    from_moviev = movie_start.get()[7:]
    to_moviev = movie_end.get()[7:]

    if from_moviev > to_moviev:
        to_moviev = from_moviev
        movie_end.set("Movie: " + str(to_moviev))


def to_movie():
    global movie_start, movie_end
    from_moviev = movie_start.get()[7:]
    to_moviev = movie_end.get()[7:]

    if from_moviev > to_moviev:
        from_moviev = to_moviev
        movie_start.set("Movie: " + str(from_moviev))


def shutdown_setting():
    global shutdown
    if shutdown:
        shutdown = False
        shutdown_button["fg"] = fg
    else:
        shutdown = True
        shutdown_button["fg"] = bg


def return_menu():
    build_menu("Episodes" if seasons > 0 else "Movies")


def language_prio_set(set_b):
    lang_1 = language_prio_1.get()
    lang_2 = language_prio_2.get()
    lang_3 = language_prio_3.get()

    languages_prios = [language_prio_1, language_prio_2, language_prio_3]

    missing = str({"Ger-Sub", "German", "Eng-Sub"} - {lang_1, lang_2, lang_3})[2:-2]
    if len(missing) > 1:
        multiple = [lang_1, lang_2, lang_3]
        multiple.sort()
        if multiple.count(multiple[0]) == 2:
            multiple = multiple[0]
        else:
            multiple = multiple[2]

        for i in range(len(languages_prios)):
            if languages_prios[i].get() in multiple and i+1 != set_b:
                languages_prios[i].set(str(missing))


def create_new_download_thread(url, file_name, provider) -> Thread:
    logger.debug("Entered Downloader.")
    t = None
    if provider in ["Vidoza", "Streamtape"]:
        t = Thread(target=download, args=(url, file_name))
        t.start()
    elif provider == "VOE":
        t = Thread(target=download_and_convert_hls_stream, args=(url, file_name))
        t.start()
    logger.loading("Provider {} - File {} added to queue.".format(provider, file_name))
    return t


def create_download_thread():
    global providerv, url, episodes
    global season_start, season_end, episode_start, episode_end, movie_start, movie_end
    trys = 0
    limit = len(languages)
    lang = language_prio_1.get()
    while trys < limit:
        try:
            trys += 1
            if "aniworld.to" in url:
                type_of_media = parse_cli_arguments("anime", 1)
            elif "s.to" in url:
                type_of_media = parse_cli_arguments("serie", 1)
            if lang == "Eng-Sub":
                lang = "English"
            language = parse_cli_arguments(lang, 3)  # language to download with
            dlMode = parse_cli_arguments("Series", 4)  # Options: Movies, Series, All
            if movies != 0:
                dlMode = parse_cli_arguments("Movies", 4)
            provider = parse_cli_arguments(providerv.get(), 6)  # provider
            name = parse_cli_arguments(url[url.index("stream/")+7:-1], 2)  # anime name like in the link
            url = "{}/{}/stream/{}/".format(site_url[type_of_media], type_of_media, name)
            if name not in os.listdir():  # create anime folder if name not exist
                os.mkdir(name)

            queue = []
            if seasons > 0:
                starting_season = int(season_start.get()[8:])
                starting_episode = int(episode_start.get()[9:])-1
                last_season = int(season_end.get()[8:])
                last_episode = int(episode_end.get()[9:])

                for i in range(last_season - starting_season + 1):
                    if "Season " + str(starting_season + i) not in os.listdir(name):  # create season folder
                        os.mkdir(name + "/Season " + str(starting_season + i))
                    eps = episodes[i + starting_season - 1] - starting_episode
                    if i + starting_season == last_season:
                        eps -= (episodes[i + starting_season - 1] - last_episode)
                    for x in range(eps):
                        queue.append("S{}E{}".format(i + starting_season, x + starting_episode + 1))
                    starting_episode = 0
                print("set episodes list")
                for i in range(len(queue)):  # range season left
                    season_override = parse_cli_arguments(queue[i][1:queue[i].index("E")], 5)  # season to download
                    episode_override = queue[i][queue[i].index("E") + 1:]
                    link = url + "staffel-{}/episode-{}".format(season_override, episode_override)
                    redirect_link, provider = get_redirect_link_by_provider(site_url[type_of_media], link, language, provider)
                    cache_url = find_cache_url(redirect_link, provider)
                    file_name = "{}/Season {}/S{}-E{}-{}.mp4".format(name, season_override, season_override, episode_override, name)
                    print("about to download")
                    if os.path.exists(file_name):
                        logger.info("Episode {} already downloaded.".format(file_name))
                    else:
                        logger.info("File not downloaded. Downloading: {}".format(file_name))
                        create_new_download_thread(cache_url, file_name, provider)
                        trys = len(languages)

            elif movies > 0:
                starting_movie = int(movie_start.get()[7:])
                last_movie = int(movie_end.get()[7:])
                if "Movies" not in os.listdir(name):  # create season folder
                    os.mkdir(name + "/Movies")
                for i in range(starting_movie-last_movie+1):
                    link = url + "filme/film-{}".format(i+starting_movie)
                    redirect_link, provider = get_redirect_link_by_provider(site_url[type_of_media], link, language, provider)
                    cache_url = find_cache_url(redirect_link, provider)
                    file_name = "{}/Movies/Movie {}-{}.mp4".format(name, i+starting_movie, name)
                    if os.path.exists(file_name):
                        logger.info("Episode {} already downloaded.".format(file_name))
                    else:
                        logger.info("File not downloaded. Downloading: {}".format(file_name))
                        create_new_download_thread(cache_url, file_name, provider)
                        trys = len(languages)

        except Exception as e:
            if trys == 1:
                lang = language_prio_2.get()
            elif trys == 2:
                lang = language_prio_3.get()
    build_menu("Episodes" if seasons > 0 else "Movies")


def build_menu_2(title):
    global name_label, link_entry, confirm_button, downloads_list, type_menu, type_label
    global shutdown_button, create_thread_button, return_button
    global provider_menu, language_menu_1, language_menu_2, language_menu_3
    global series_name_label, start_label, end_label, provider_label, options_label, language_label
    global season_start_menu, season_end_menu, episode_start_menu, episode_end_menu, movie_start_menu, movie_end_menu
    global season_start, season_end, episode_start, episode_end, movie_start, movie_end
    global providerv, language_prio_1, language_prio_2, language_prio_3
    name_label.destroy()
    link_entry.destroy()
    confirm_button.destroy()
    downloads_list.destroy()
    type_menu.destroy()
    type_label.destroy()
    if version < latest_version:
        update_button.destroy()

    series_name_label = tk.Label(root, text=title, font=("Open Sans", 30), fg=bg_2nd, bg=bg)
    series_name_label.grid(row=0, column=0)

    if seasons != 0:
        seasonsv = ["Season: " + str(i+1) for i in range(seasons)]
        episodesv = ["Episode: " + str(i+1) for i in range(episodes[0])]
        season_start = tk.StringVar()
        season_start.set(seasonsv[0])
        season_end = tk.StringVar()
        season_end.set(seasonsv[0])
        episode_start = tk.StringVar()
        episode_start.set(episodesv[0])
        episode_end = tk.StringVar()
        episode_end.set(episodesv[-1])

        season_start_menu = tk.OptionMenu(root, season_start, *seasonsv, command=lambda x: from_season())
        season_start_menu.configure(bg=bg_2nd, fg=fg, border=0, borderwidth=0, highlightthickness=0, activeforeground=fg, font=("Open Sans", 15), activebackground=bg_2nd, indicatoron=False, width=11)
        season_start_menu["menu"].configure(bg=bg_2nd, fg=fg, activeforeground=fg, font=("Open Sans", 15), activebackground=bg)
        season_start_menu.grid(row=30, column=0, sticky="w", padx=30)
        season_end_menu = tk.OptionMenu(root, season_end, *seasonsv, command=lambda x: to_season())
        season_end_menu.configure(bg=bg_2nd, fg=fg, border=0, borderwidth=0, highlightthickness=0, activeforeground=fg, font=("Open Sans", 15), activebackground=bg_2nd, indicatoron=False, width=11)
        season_end_menu["menu"].configure(bg=bg_2nd, fg=fg, activeforeground=fg, font=("Open Sans", 15), activebackground=bg)
        season_end_menu.grid(row=30, column=0, sticky="w", padx=187)

        episode_start_menu = tk.OptionMenu(root, episode_start, *episodesv, command=lambda x: from_episode())
        episode_start_menu.configure(bg=bg_2nd, fg=fg, border=0, borderwidth=0, highlightthickness=0, activeforeground=fg, font=("Open Sans", 15), activebackground=bg_2nd, indicatoron=False, width=11)
        episode_start_menu["menu"].configure(bg=bg_2nd, fg=fg, activeforeground=fg, font=("Open Sans", 15), activebackground=bg)
        episode_start_menu.grid(row=35, column=0, sticky="w", padx=30)
        episode_end_menu = tk.OptionMenu(root, episode_end, *episodesv, command=lambda x: to_episode())
        episode_end_menu.configure(bg=bg_2nd, fg=fg, border=0, borderwidth=0, highlightthickness=0, activeforeground=fg, font=("Open Sans", 15), activebackground=bg_2nd, indicatoron=False, width=11)
        episode_end_menu["menu"].configure(bg=bg_2nd, fg=fg, activeforeground=fg, font=("Open Sans", 15), activebackground=bg)
        episode_end_menu.grid(row=35, column=0, sticky="w", padx=187)

    elif movies != 0:
        moviesv = ["Movie: " + str(i+1) for i in range(movies)]
        movie_start = tk.StringVar()
        movie_start.set(moviesv[0])
        movie_end = tk.StringVar()
        movie_end.set(moviesv[-1])

        movie_start_menu = tk.OptionMenu(root, movie_start, *moviesv, command=lambda x: from_movie())
        movie_start_menu.configure(bg=bg_2nd, fg=fg, border=0, borderwidth=0, highlightthickness=0, activeforeground=fg, font=("Open Sans", 15), activebackground=bg_2nd, indicatoron=False, width=11)
        movie_start_menu["menu"].configure(bg=bg_2nd, fg=fg, activeforeground=fg, font=("Open Sans", 15), activebackground=bg)
        movie_start_menu.grid(row=30, column=0, sticky="w", padx=30)
        movie_end_menu = tk.OptionMenu(root, movie_end, *moviesv, command=lambda x: to_movie())
        movie_end_menu.configure(bg=bg_2nd, fg=fg, border=0, borderwidth=0, highlightthickness=0, activeforeground=fg, font=("Open Sans", 15), activebackground=bg_2nd, indicatoron=False, width=11)
        movie_end_menu["menu"].configure(bg=bg_2nd, fg=fg, activeforeground=fg, font=("Open Sans", 15), activebackground=bg)
        movie_end_menu.grid(row=30, column=0, sticky="w", padx=187)

    start_label = tk.Label(root, text="Start from", font=("Open Sans", 15), fg=bg_2nd, bg=bg, width=11)
    start_label.grid(row=25, column=0, sticky="w", padx=30, ipadx=2)
    end_label = tk.Label(root, text="End at", font=("Open Sans", 15), fg=bg_2nd, bg=bg, width=11)
    end_label.grid(row=25, column=0, sticky="w", padx=60+127, ipadx=2)

    provider_label = tk.Label(root, text="Provider", font=("Open Sans", 15), fg=bg_2nd, bg=bg, width=15)
    provider_label.grid(row=25, column=0, sticky="w", padx=217+end_label.winfo_reqwidth())

    providerv = tk.StringVar()
    providerv.set("VOE")
    providers = ["VOE", "Vidoza", "Streamtape"]
    provider_menu = tk.OptionMenu(root, providerv, *providers)
    provider_menu.configure(bg=bg_2nd, fg=fg, border=0, borderwidth=0, highlightthickness=0, activeforeground=fg, font=("Open Sans", 15), activebackground=bg_2nd, indicatoron=False, width=15)
    provider_menu["menu"].configure(bg=bg_2nd, fg=fg, activeforeground=fg, font=("Open Sans", 15), activebackground=bg)
    provider_menu.grid(row=30, column=0, sticky="w", padx=217+end_label.winfo_reqwidth())

    options_label = tk.Label(root, text="Options", font=("Open Sans", 15), fg=bg_2nd, bg=bg, width=10)
    options_label.grid(row=25, column=0, sticky="e", padx=200)

    shutdown_button = tk.Button(root, text="Shutdown", font=("Open Sans", 15), fg=fg, bg=bg_2nd, width=10, bd=False, height=1, command=lambda: shutdown_setting())
    if shutdown:
        shutdown_button["fg"] = bg
    shutdown_button.grid(row=30, column=0, sticky="e", padx=200)

    language_label = tk.Label(root, text="Language\npriority", font=("Open Sans", 15), fg=bg_2nd, bg=bg, width=12, bd=False, height=2)
    language_label.grid(row=20, column=0, sticky="e", padx=30, rowspan=6)

    return_button = tk.Button(root, text="←", font=("Open Sans", 25), fg=bg_2nd, bg=bg, width=3, bd=False, height=1, command=lambda: return_menu())
    return_button.grid(row=0, column=0, sticky="w")

    language_prio_1 = tk.StringVar()
    language_prio_2 = tk.StringVar()
    language_prio_3 = tk.StringVar()
    language_menu_1 = tk.OptionMenu(root, language_prio_1, *languages, command=lambda x: language_prio_set(1))
    language_menu_2 = tk.OptionMenu(root, language_prio_2, *languages, command=lambda x: language_prio_set(2))
    language_menu_3 = tk.OptionMenu(root, language_prio_3, *languages, command=lambda x: language_prio_set(3))
    language_menu_1.configure(bg=bg_2nd, fg=fg, border=0, borderwidth=0, highlightthickness=0, activeforeground=fg, font=("Open Sans", 15), activebackground=bg_2nd, indicatoron=False, width=12)
    language_menu_1["menu"].configure(bg=bg_2nd, fg=fg, activeforeground=fg, font=("Open Sans", 15), activebackground=bg)
    language_menu_2.configure(bg=bg_2nd, fg=fg, border=0, borderwidth=0, highlightthickness=0, activeforeground=fg, font=("Open Sans", 15), activebackground=bg_2nd, indicatoron=False, width=12)
    language_menu_2["menu"].configure(bg=bg_2nd, fg=fg, activeforeground=fg, font=("Open Sans", 15), activebackground=bg)
    language_menu_3.configure(bg=bg_2nd, fg=fg, border=0, borderwidth=0, highlightthickness=0, activeforeground=fg, font=("Open Sans", 15), activebackground=bg_2nd, indicatoron=False, width=12)
    language_menu_3["menu"].configure(bg=bg_2nd, fg=fg, activeforeground=fg, font=("Open Sans", 15), activebackground=bg)
    language_menu_1.grid(row=30, column=0, sticky="e", padx=30)
    language_menu_2.grid(row=35, column=0, sticky="e", padx=30)
    language_menu_3.grid(row=42, column=0, sticky="e", padx=30)
    language_prio_1.set(languages[1])
    language_prio_2.set(languages[0])
    language_prio_3.set(languages[2])

    create_thread_button = tk.Button(root, text="Start", font=("Open Sans", 15), fg=fg, bg=bg_2nd, width=17, bd=False, height=1, command=lambda: create_download_thread())
    create_thread_button.grid(row=150, column=0)


def build_menu(*args):
    global link_entry, confirm_button, downloads_list, name_label, downloads, update_button, type_menu, type_label, typev
    global shutdown_button, create_thread_button, return_button
    global provider_menu, language_menu_1, language_menu_2, language_menu_3, language_menu_4
    global series_name_label, start_label, end_label, provider_label, options_label, language_label
    global season_start_menu, season_end_menu, episode_start_menu, episode_end_menu, movie_start_menu, movie_end_menu
    if args:
        if "Episodes" in args:
            season_start_menu.destroy()
            season_end_menu.destroy()
            episode_start_menu.destroy()
            episode_end_menu.destroy()
        elif "Movies" in args:
            movie_start_menu.destroy()
            movie_end_menu.destroy()
        shutdown_button.destroy()
        create_thread_button.destroy()
        provider_menu.destroy()
        series_name_label.destroy()
        start_label.destroy()
        end_label.destroy()
        provider_label.destroy()
        options_label.destroy()
        language_menu_1.destroy()
        language_menu_2.destroy()
        language_menu_3.destroy()
        language_label.destroy()
        return_button.destroy()
    link_entry = tk.Entry(root, width=70, bg=bg_2nd, fg=fg, font=("Open Sans", 15))
    link_entry.grid(row=90, column=0, ipady=10)
    link_entry.insert(0, "Link: ")
    link_entry.bind("<FocusIn>", lambda x: entry_focus_in(link_entry))
    link_entry.bind("<FocusOut>", lambda x: entry_focus_out(link_entry))

    name_label = tk.Label(root, text="ANIWORLD DOWNLOADER", bg=bg, fg=bg_2nd, font=("Open Sans", 30))
    name_label.grid(row=0, column=0)

    type_label = tk.Label(root, text="Type", bg=bg, fg=bg_2nd, font=("Open Sans", 15), width=8)
    type_label.grid(row=83, column=0, sticky="w", padx=13)

    typev = tk.StringVar()
    typev.set("Episodes")
    type_menu = tk.OptionMenu(root, typev, *types)
    type_menu.configure(bg=bg_2nd, fg=fg, border=0, borderwidth=0, highlightthickness=0, activeforeground=fg, font=("Open Sans", 15), activebackground=bg_2nd, indicatoron=False, width=8)
    type_menu["menu"].configure(bg=bg_2nd, fg=fg, border=0, borderwidth=0, activeforeground=fg, font=("Open Sans", 15), activebackground=bg)
    type_menu.grid(row=88, column=0, sticky="w", padx=13)

    confirm_button = tk.Button(root, text="Confirm", bg=bg_2nd, width=10, border=0, fg=fg, height=1, font=("Open Sans", 15), command=lambda: confirm_link(link_entry.get()))
    confirm_button.grid(row=91, column=0)

    downloads = tk.StringVar()
    downloads.set("Current Downloads")
    downloads_list = tk.OptionMenu(root, downloads, *current_downloads)
    downloads_list.configure(bg=bg_2nd, fg=fg, border=0, borderwidth=0, highlightthickness=0, activeforeground=fg, font=("Open Sans", 15), activebackground=bg_2nd, indicatoron=False)
    downloads_list["menu"].configure(bg=bg_2nd, fg=fg, border=0, borderwidth=0, activeforeground=fg, font=("Open Sans", 15), activebackground=bg)
    downloads_list.grid(row=91, column=0, sticky="w", padx=13)

    logo_label = tk.Label(root, width=12, height=1, text="Made by NMB", bg=bg, fg="#8EA1BD", font=("Open Sans", 15))
    logo_label.grid(row=201, column=0, sticky="w", padx=6)

    if version < latest_version:
        update_button = tk.Button(root, text="Update", bg=bg_2nd, fg=fg, font=("Open Sans", 25), command=update)
        update_button.grid(row=200, column=0, sticky="w", padx=13)


build_menu()
root.bind("<Button-1>", lambda x: focus_out())
root.mainloop()
