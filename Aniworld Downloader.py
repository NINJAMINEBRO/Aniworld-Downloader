import tkinter as tk
from urllib.request import Request as Rqst, urlopen
from bs4 import BeautifulSoup
from os import getcwd, path, remove, system, rename, startfile, listdir, mkdir
import sys
from re import compile, search, DOTALL, match
from threading import Thread
from time import time, sleep
import subprocess
from zipfile import ZipFile
from io import BytesIO
from webbrowser import open as webopen
from urllib.parse import urlsplit, urlunsplit
from random import choices
from string import ascii_letters, digits
from seleniumbase import SB
from base64 import b64decode
import json
from colorama import Fore, Style

VOE_PATTERNS = [compile(r"'hls': '(?P<url>.+)'"),
                compile(r'prompt\("Node",\s*"(?P<url>[^"]+)"'),
                compile(r"window\.location\.href = '(?P<url>[^']+)'")]
STREAMTAPE_PATTERN = compile(r'get_video\?id=[^&\'\s]+&expires=[^&\'\s]+&ip=[^&\'\s]+&token=[^&\'\s]+\'')
DOODSTREAM_PATTERN = compile(r"/pass_md5/[\w-]+/(?P<token>[\w-]+)")
VIDMOLY_PATTERN = compile(r"sources: \[{file:\"(?P<url>.*?)\"}]")
SPEEDFILES_PATTERN = compile(r"var _0x5opu234 = \"(?P<content>.*?)\";")


class ProviderError(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class LanguageError(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


def get_redirect_link_by_provider(site, internal_link, language, provider, season, episode):
    try:
        return get_redirect_link(site, internal_link, language, provider, season, episode)
    except ProviderError:
        if provider_priority.index(provider) == len(provider_priority):
            print(f"{Fore.RED}Provider {provider} failed. Can not download episode.{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}Provider {provider} failed. Trying next provider.{Style.RESET_ALL}")


def get_redirect_link(site, html_link, language, provider, season, episode):
    if "bs.to" in site:
        href_value = get_bs_href_by_language(html_link, language, provider, season, episode)
        parsed_url = urlsplit(url)
        base_url = urlunsplit((parsed_url.scheme, parsed_url.hostname, "", "", ""))
        link_to_episode = base_url + href_value
        link_to_episode = find_bs_link_to_episode(link_to_episode, provider)
        return link_to_episode
    else:
        html_response = urlopen(html_link)
        href_value = get_href_by_language(html_response, language, provider)
        link_to_redirect = site + href_value
        return link_to_redirect


def find_bs_link_to_episode(url, provider):
    with SB(uc=True, headless2=True, extension_dir=find_and_unzip_crx()) as sb:
        sb.open(url)
        sb.click('.cc-compliance a')
        sb.click('.hoster-player .play')
        if provider == "VOE":
            content_link = sb.wait_for_element_visible('.hoster-player a', timeout=120).get_attribute("href")
        elif provider == "Doodstream":
            sb.switch_to_tab(1, timeout=120)
            html = sb.get_page_source()
            soup = BeautifulSoup(html, features="html.parser")
            iframe_src = soup.find("iframe").get("src")
            content_link = f"https://d000d.com{iframe_src}"
        elif provider in ["Streamtape", "Vidoza"]:
            content_link = sb.wait_for_element_visible('.hoster-player iframe', timeout=120).get_attribute("src")
    return content_link


def find_and_unzip_crx():
    crx_file_path = getcwd() + "/recaptcha-solver.crx"
    with ZipFile(crx_file_path, 'r') as zip_ref:
        zip_ref.extractall(getcwd())
    return getcwd()


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
    change_language_div = soup.find("div", class_="changeLanguageBox")
    if change_language_div:
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
    lang_key = lang_key_mapping.get(language)
    if lang_key is None:
        raise LanguageError(print(f"{Fore.LIGHTBLUE_EX}Invalid language input. Supported languages: "
                                  f"{list(lang_key_mapping.keys())}{Style.RESET_ALL}"))
    matching_li_elements = soup.find_all("li", {"data-lang-key": lang_key})
    matching_li_element = next((li_element for li_element in matching_li_elements if li_element.find("h4").get_text() == provider), None)
    if matching_li_element:
        href = matching_li_element.get("data-link-target", "")
        return href
    raise ProviderError


def get_bs_href_by_language(url, language, provider, season, episode):
    bs_language_mapping = {
        "German": "de",
        "Ger-Sub": "des",
        "Eng-Sub": "jps",
        "English": "en"}
    html_response = urlopen(f"{url}{season}/{bs_language_mapping.get(language)}")
    soup = BeautifulSoup(html_response, "html.parser")
    episode_has_language = False
    links = soup.find_all('i', class_='hoster')
    for link in links:
        href = str(link.parent.get("href"))
        if f"{season}/{episode}-" in href:
            episode_has_language = True
            parts = href.split("/")
            link_provider = parts[-1]
            if link_provider == provider:
                return "/" + href
    if not episode_has_language:
        raise LanguageError()
    raise ProviderError()


def find_script_element_voenew(raw_html):
    soup = BeautifulSoup(raw_html, features="html.parser")
    MKGMa_pattern = r'MKGMa="(.*?)"'
    matches = search(MKGMa_pattern, str(soup), DOTALL)

    if not matches:
        MKGMa_pattern=r'<script type="application/json">.*\[(.*?)\]</script>'
        matches = search(MKGMa_pattern, str(soup), DOTALL)
    if matches:
        raw_MKGMa = matches.group(1)

        def rot13_decode(s: str) -> str:
            result = []
            for c in s:
                if 'A' <= c <= 'Z':
                    result.append(chr((ord(c) - ord('A') + 13) % 26 + ord('A')))
                elif 'a' <= c <= 'z':
                    result.append(chr((ord(c) - ord('a') + 13) % 26 + ord('a')))
                else:
                    result.append(c)
            return ''.join(result)

        def shift_characters(s: str, offset: int) -> str:
            return ''.join(chr(ord(c) - offset) for c in s)

        try:
            step1 = rot13_decode(raw_MKGMa)
            step2 = step1.replace('_', '')
            step3 = b64decode(step2).decode('utf-8')
            step4 = shift_characters(step3, 3)
            step5 = step4[::-1]

            decoded = b64decode(step5).decode('utf-8')
            try:
                parsed_json = json.loads(decoded)

                if 'direct_access_url' in parsed_json:
                    source_json = {"mp4": parsed_json['direct_access_url']}
                elif 'source' in parsed_json:
                    source_json = {"hls": parsed_json['source']}
            except json.JSONDecodeError:
                pass

                mp4_match = search(r'(https?://[^\s"]+\.mp4[^\s"]*)', decoded)
                m3u8_match = search(r'(https?://[^\s"]+\.m3u8[^\s"]*)', decoded)

                if mp4_match:
                    source_json = {"mp4": mp4_match.group(1)}
                elif m3u8_match:
                    source_json = {"hls": m3u8_match.group(1)}
        except Exception as e:
            pass
        try:
            if "mp4" in source_json:
                link = source_json["mp4"]
                # Check if the link is base64 encoded
                if isinstance(link, str) and (link.startswith("eyJ") or match(r'^[A-Za-z0-9+/=]+$', link)):
                    try:
                        link = b64decode(link).decode("utf-8")
                    except Exception as e:
                        pass

                # Ensure the link is a complete URL
                if link.startswith("//"):
                    link = "https:" + link
                return link

            elif "hls" in source_json:
                link = source_json["hls"]
                # Check if the link is base64 encoded
                if isinstance(link, str) and (link.startswith("eyJ") or match(r'^[A-Za-z0-9+/=]+$', link)):
                    try:
                        link = b64decode(link).decode("utf-8")
                    except Exception as e:
                        pass

                # Ensure the link is a complete URL
                if link.startswith("//"):
                    link = "https:" + link
                return link
        except KeyError as e:
            pass
    return None


def find_content_url(url, provider):
    global cache_url_attempts
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
    req = Rqst(url, headers=headers)
    decoded_html = urlopen(req).read().decode("utf-8")
    try:
        if provider == "Vidoza":
            soup = BeautifulSoup(decoded_html, features="html.parser")
            content_link = soup.find("source").get("src")
        elif provider == "VOE":
            html_page = urlopen(url)
            html_page = html_page.read().decode('utf-8')
            ## New Version of VOE 2025-05-01
            cache_url = find_script_element_voenew(html_page)
            if cache_url:
                return cache_url
            try:
                b64_match = search(r"var a168c='([^']+)'", html_page)
                if b64_match:
                    html_page = b64decode(b64_match.group(1)).decode('utf-8')[::-1]
                    html_page = json.loads(html_page)
                    html_page = html_page["source"]
                    return html_page
            except AttributeError:
                pass

            for VOE_PATTERN in VOE_PATTERNS:
                matches = VOE_PATTERN.search(html_page)
                if matches:
                    if matches.group(0).startswith("window.location.href"):
                        return find_content_url(matches.group(1), provider)
                    cache_link = matches.group(1)
                    cache_link = b64decode(cache_link).decode('utf-8')
                    if cache_link and cache_link.startswith("https://"):
                        return cache_link
            return 0
        elif provider == "Streamtape":
            content_link = STREAMTAPE_PATTERN.search(decoded_html)
            if content_link is None:
                return find_content_url(url, provider)
            content_link = "https://" + provider + ".com/" + content_link.group()[:-1]
        elif provider == "Doodstream":
            pattern_match = DOODSTREAM_PATTERN.search(decoded_html)
            pass_md5 = pattern_match.group()
            token = pattern_match.group("token")
            headers['Referer'] = 'https://d0000d.com/'
            req = Rqst(f"https://d0000d.com{pass_md5}", headers=headers)
            response_page = urlopen(req)
            content_link = f"{response_page.read().decode('utf-8')}{''.join(choices(ascii_letters + digits, k=10))}?token={token}&expiry={int(time() * 1000)}"
        elif provider == "Vidmoly":
            matches = VIDMOLY_PATTERN.search(decoded_html)
            if matches is None:
                return 0
            content_link = matches.group("url")
            if content_link is None:
                print(f"{Fore.YELLOW}Failed to find the video link of provider Vidmoly{Style.RESET_ALL}")
            else:
                sleep(2)
        elif provider == "SpeedFiles":
            matches = SPEEDFILES_PATTERN.search(decoded_html)
            if matches is None:
                return 0
            content = matches.group("content")
            content = b64decode(content).decode()
            content = content.swapcase()
            content = ''.join(reversed(content))
            content = b64decode(content).decode()
            content = ''.join(reversed(content))
            next_content = ""
            for i in range(0, len(content), 2):
                next_content += chr(int(content[i:i + 2], 16))
            content_link = ""
            for char in next_content:
                content_link += chr(ord(char) - 3)
            content_link = content_link.swapcase()
            content_link = ''.join(reversed(content_link))
            content_link = b64decode(content_link).decode()
    except AttributeError as e:
        print(f"{Fore.YELLOW}ERROR: {e}{Style.RESET_ALL}")
        print(f"{Fore.LIGHTBLUE_EX}Trying again...{Style.RESET_ALL}")
        if cache_url_attempts < 3:
            cache_url_attempts += 1
            return find_content_url(url, provider)
        else:
            print(f"{Fore.YELLOW}Could not find cache url for {provider}{Style.RESET_ALL}")
            return 0
    return content_link


def download_episode(url, file_name, provider):
    print(f"{Fore.LIGHTBLUE_EX}File not downloaded. Downloading: {file_name}{Style.RESET_ALL}")
    try:
        current_downloads.append(file_name)
        try:
            update_option_menu(downloads_list)
        except Exception as e:
            pass
        ffmpeg_cmd = ["ffmpeg", "-i", url, "-c", "copy", "-nostdin", file_name]
        if provider == "Doodstream":
            ffmpeg_cmd.insert(1, "Referer: https://d0000d.com/")
            ffmpeg_cmd.insert(1, "-headers")
        elif provider == "Vidmoly":
            ffmpeg_cmd.insert(1, "Referer: https://vidmoly.to/")
            ffmpeg_cmd.insert(1, "-headers")
        subprocess.run(ffmpeg_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        print(f"{Fore.LIGHTGREEN_EX}Finished download of {file_name}{Style.RESET_ALL}")
        current_downloads.remove(file_name)
    except subprocess.CalledProcessError as e:
        remove(file_name) if path.exists(file_name) else None
        print(f"{Fore.RED}{str(e)}{Style.RESET_ALL}")
        print(f"{Fore.RED}Error while downloading {file_name}. Retrying...{Style.RESET_ALL}")
        current_downloads.remove(file_name)
        r_t = create_new_download_thread(url, file_name, provider)
        if r_t is not None:
            pending_queue.append(r_t)
    update_option_menu(downloads_list)
    if pending_queue:
        pending_queue[0].start()
        pending_queue.pop(0)
    if len(current_downloads) == 1 and shutdown:
        system('shutdown -s')


def update_option_menu(menu):
    menu = menu["menu"]
    menu.delete(0, "end")
    for download in current_downloads:
        menu.add_command(label=download)


def get_latest_version():  # get latest version
    network = True
    try:
        file = urlopen("https://raw.githubusercontent.com/NINJAMINEBRO/Aniworld-Downloader/main/version")
        lines = ""
        for line in file:
            lines += line.decode("utf-8")
        lines = float(lines[:-1])
    except Exception as e:
        network = False
        if "urlopen error" in str(e):
            print(f"{Fore.RED}No Network connection{Style.RESET_ALL}")
        lines = version
    if lines > version:
        print(f"{Fore.LIGHTBLUE_EX}Update available\ncurrent version: {version}\nlatest version: {lines}\nDownload latest version on: https://ninjaminebro.itch.io/aniworld-downloader\n{Style.RESET_ALL}")
    return lines, network


def get_titles_dict(url):  # for aniworld and streamseries
    try:
        html_response = urlopen(url)
        soup = BeautifulSoup(html_response, "html.parser")
        matching_li_elements = str(soup.find_all("li")).split("</a></li>, <li><a ")
        index_list = []
        for i in matching_li_elements:
            if "data-alternative-title" not in i:
                index_list.append(matching_li_elements.index(i))
        index_list = sorted(index_list, reverse=True)
        for i in index_list:
            matching_li_elements.pop(i)
        title_link_dict = {}
        for i in range(len(matching_li_elements)):
            matching_li_elements[i] = matching_li_elements[i][24:]
        for i in matching_li_elements:
            title_link_dict.update({i[i.index('" title') + 9:i.index(" Stream anschauen")] + "," + i[:i.index('"')]: i[i.index('href="') + 20: i.index('" title')]})
        return title_link_dict
    except Exception as e:
        if "urlopen error" in str(e):
            print(f"{Fore.RED}Disabled {url[8:url.index(".to")+3]} Searchbar{Style.RESET_ALL}")
        return {}


def get_titles_dict_2(url):  # for burningseries
    try:
        html_response = urlopen(url)
        soup = BeautifulSoup(html_response, "html.parser")
        title_link_dict = {}
        matching_li_elements = str(soup.find_all("ul")).split("</a></li>\n<li><a ")
        del matching_li_elements[:31]
        matching_li_elements[0] = matching_li_elements[0][91:]
        del matching_li_elements[-4:]
        matching_li_elements[-1] = matching_li_elements[-1][:87]
        for i in matching_li_elements:
            title_link_dict.update({i[i.index('title=')+7:]: i[i.index('href="')+12: i.index('" title')]})
        return title_link_dict
    except Exception as e:
        print(str(e))
        if "urlopen error" in str(e):
            print(f"{Fore.RED}Disabled {url[8:url.index(".to") + 3]} Searchbar{Style.RESET_ALL}")
        return {}


def update():
    http_response = urlopen("https://github.com/NINJAMINEBRO/Aniworld-Downloader/raw/refs/heads/main/Aniworld%20Downloader.zip")
    zipfile = ZipFile(BytesIO(http_response.read()))
    try:
        rename(f"{getcwd()}\\Aniworld Downloader by NMB.exe", f"{getcwd()}\\Aniworld Downloader by NMB old.exe")
    except Exception as e:
        print(f"{Fore.LIGHTBLUE_EX}could not find Aniworld Downloader{Style.RESET_ALL}")
    zipfile.extractall(path=getcwd())
    startfile(f"{getcwd()}\\Aniworld Downloader by NMB")
    root.destroy()


def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = path.abspath(".")
    return path.join(base_path, relative_path)


def update_settings_file():
    try:
        with open(resource_path("aniworld settings.txt"), "w") as s:
            s.write(f"Searchbars (These settings have high impact on startup time):\n")
            s.write(f"aniworld.to: {searchbar_aniworld}\n")
            s.write(f"s.to: {searchbar_sto}\n")
            s.write(f"bs.to: {searchbar_bsto}")
    except Exception as e:
        print(f"{Fore.RED}Error while updating settings file: {e}{Style.RESET_ALL}")


if "ffmpeg.exe" not in listdir(getcwd()):
    print(f"{Fore.RED}WARNING: ffmpeg is not installed or not in this folder\nThis program will not work unless ffmpeg is in the same folder as this program{Style.RESET_ALL}")
if "Aniworld Downloader by NMB old.exe" in listdir(getcwd()):
    try:
        remove(f"{getcwd()}\\Aniworld Downloader by NMB old.exe")
    except Exception as e:
        print(f"{Fore.YELLOW}could not remove old version\n{e}{Style.RESET_ALL}")

try:
    with open(resource_path("aniworld settings.txt"), "r") as s:
        text = s.read()
        text = text.split("\n")
        searchbar_aniworld = int(text[1][-1])
        searchbar_sto = int(text[2][-1])
        searchbar_bsto = int(text[3][-1])
except Exception as e:
    print("There was an error while reading the settings file")
    print("ERROR: " + str(e))
    searchbar_aniworld = 1
    searchbar_sto = 0
    searchbar_bsto = 0

provider_priority = ["Vidmoly", "VOE", "SpeedFiles", "Vidoza", "Doodstream", "Streamtape"]

bg = "#121C22"
bg_2nd = "#637CF9"
fg = "#FFFFFF"
episodes = []
seasons = 0
movies = 0
current_downloads = ["Current Downloads"]
pending_queue = []
active_queue_checker = False
types = ["Episodes", "Movies"]
shutdown = False
languages = ["German", "Ger-Sub", "Eng-Sub", "English"]
providers = ["Vidmoly", "VOE", "SpeedFiles", "Vidoza", "Doodstream", "Streamtape"]
c_menu = 0

version = 1.32
latest_version, network_status = get_latest_version()
if searchbar_aniworld:
    aniworld_titles_dict = get_titles_dict("https://aniworld.to/animes")
else:
    aniworld_titles_dict = {}
if searchbar_sto:
    sto_titles_dict = get_titles_dict("https://s.to/serien")
else:
    sto_titles_dict = {}
if searchbar_bsto:
    bsto_titles_dict = get_titles_dict_2("https://bs.to/andere-serien")
else:
    bsto_titles_dict = {}
root = tk.Tk()
root.title("Aniworld Downloader by NMB")
root.configure(bg=bg)
root.resizable(False, False)
root.geometry("800x500")

for i in range(201):
    root.rowconfigure(i, weight=1)
root.columnconfigure(0, weight=1)


def entry_focus_in(entry):
    text = entry.get()
    if text == "Link: https://aniworld.to/anime/stream/monogatari":
        entry.delete(0, "end")


def entry_focus_out(entry):
    text = entry.get()
    if not text:
        entry.insert(0, "Link: https://aniworld.to/anime/stream/monogatari")
        try:
            filtered_anime_list.destroy()
        except Exception as e:
            pass


def focus_out():
    x, y = root.winfo_pointerxy()
    widget = root.winfo_containing(x, y)
    if ".!entry" not in str(widget):
        root.focus()


def sort_titles_dicts(sel_dict, site, text):
    valid_titles = []
    better_sorted_list = []
    secondary_sorted_list = []
    third_sorted_list = []
    for i in sel_dict.keys():
        if text in i.lower():
            valid_titles.append(sel_dict.get(i))
    for i in valid_titles:
        if text.replace(" ", "-") in i.lower():
            if i.lower().index(text.replace(" ", "-")) == 0:
                better_sorted_list.append(i + site)
            else:
                secondary_sorted_list.append(i + site)
        else:
            third_sorted_list.append(i + site)
    return better_sorted_list, secondary_sorted_list, third_sorted_list


def get_event(event):
    input_handler(event, link_entry)


def input_handler(event, entry):
    key = event.keycode
    global filtered_anime_list
    text = entry.get()
    if key == 8:
        text = text[:-1]
    else:
        text += event.char
    text = text.lower()

    aniworld_better_sorted_list, aniworld_secondary_sorted_list, aniworld_third_sorted_list = [], [], []
    sto_better_sorted_list, sto_secondary_sorted_list, sto_third_sorted_list = [], [], []
    bsto_better_sorted_list, bsto_secondary_sorted_list, bsto_third_sorted_list = [], [], []
    if searchbar_aniworld:
        aniworld_better_sorted_list, aniworld_secondary_sorted_list, aniworld_third_sorted_list = sort_titles_dicts(aniworld_titles_dict, " Aniworld", text)
    if searchbar_sto:
        sto_better_sorted_list, sto_secondary_sorted_list, sto_third_sorted_list = sort_titles_dicts(sto_titles_dict, " s.to", text)
    if searchbar_bsto:
        bsto_better_sorted_list, bsto_secondary_sorted_list, bsto_third_sorted_list = sort_titles_dicts(bsto_titles_dict, " bs.to", text)
    best_sorted = aniworld_better_sorted_list + sto_better_sorted_list + bsto_better_sorted_list
    secondary_sorted = aniworld_secondary_sorted_list + sto_secondary_sorted_list + bsto_secondary_sorted_list
    third_sorted = aniworld_third_sorted_list + sto_third_sorted_list + bsto_third_sorted_list
    best_sorted.sort(key=lambda v: v.lower())
    secondary_sorted.sort(key=lambda v: v.lower())
    third_sorted.sort(key=lambda v: v.lower())
    better_sorted_list = best_sorted + secondary_sorted + third_sorted
    try:
        filtered_anime_list.destroy()
    except Exception as e:
        pass
    if better_sorted_list and text:
        filtered_anime = tk.StringVar()
        filtered_anime.set("Searchbar")
        filtered_anime_list = tk.OptionMenu(root, filtered_anime, *better_sorted_list, command=lambda x: set_anime(filtered_anime, entry))
        filtered_anime_list.configure(bg=bg_2nd, fg=fg, border=0, borderwidth=0, highlightthickness=0, activeforeground=fg, font=("Open Sans", 15), activebackground=bg_2nd, indicatoron=False)
        filtered_anime_list["menu"].configure(bg=bg_2nd, fg=fg, border=0, borderwidth=0, activeforeground=fg, font=("Open Sans", 15), activebackground=bg)
        filtered_anime_list.place(x=14, y=10)


def set_anime(anime, entry):
    entry.delete(0, "end")
    if " Aniworld" in anime.get():
        entry.insert(0, "https://aniworld.to/anime/stream/" + anime.get().replace(" Aniworld", ""))
    elif " s.to" in anime.get():
        entry.insert(0, "https://s.to/serie/stream/" + anime.get().replace(" s.to", ""))
    elif " bs.to" in anime.get():
        entry.insert(0, "https://bs.to/serie/" + anime.get().replace(" bs.to", ""))
    filtered_anime_list.destroy()


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
        if "bs.to" in link:
            title = link[link.index("serie/") + 6:-1]
        else:
            title = link[link.index("stream/") + 7:-1].replace("-", " ").upper()
        if seasons != 0:
            episodes = []
            for i in range(seasons):
                episodes.append(get_episodes(link, i + 1))
            forget_menu()
            place_menu_2(title)
        elif movies != 0:
            forget_menu()
            place_menu_2(title)
        else:
            print(f"{Fore.LIGHTBLUE_EX}Anime/Series not found{Style.RESET_ALL}")
    else:
        print(f"{Fore.LIGHTBLUE_EX}That Link is invalid{Style.RESET_ALL}")


def link_validator(link):
    if link[:6] != "Link: ":
        if "https://aniworld.to/" in link or "https://s.to/" in link or "https://bs.to/" in link:
            if link[-1] != "/":
                link += "/"
            sub_link = link[33:]
            if "bs.to" in link:
                sub_link = link[20:]
            elif "s.to" in link:
                sub_link = link[26:]
            sub_link = sub_link[:sub_link.index("/")]
            sub_link = link[:link.index(sub_link) + len(sub_link) + 1]
            return sub_link
    return False


def get_movies(url_path):
    url = "{}filme/".format(url_path)
    movie_count = 1
    html_page = urlopen(url, timeout=50)
    soup = BeautifulSoup(html_page, features="html.parser")
    for link in soup.find_all('a'):
        movie = str(link.get("href"))
        if "/filme/film-{}".format(movie_count) in movie:
            movie_count = movie_count + 1
    return movie_count - 1


def get_season(url_path):
    counter_seasons = 1
    html_page = urlopen(url_path, timeout=50)
    soup = BeautifulSoup(html_page, features="html.parser")
    if "bs.to" in url_path:
        for li in soup.find_all("li"):
            season = str(li.get("class"))
            if f"s{counter_seasons}" in season:
                counter_seasons += 1
    else:
        for link in soup.find_all('a'):
            seasons = str(link.get("href"))
            if "/staffel-{}".format(counter_seasons) in seasons:
                counter_seasons = counter_seasons + 1
    return counter_seasons - 1


def get_episodes(url_path, season_count):
    episode_count = 1
    if "bs.to" in url_path:
        url = f"{url_path}{season_count}/"
        html_page = urlopen(url, timeout=50)
        soup = BeautifulSoup(html_page, features="html.parser")
        for link in soup.find_all("a"):
            href = str(link.get("href"))
            if f"{season_count}/{episode_count}" in href:
                episode_count += 1
    else:
        url = "{}staffel-{}/".format(url_path, season_count)
        html_page = urlopen(url, timeout=50)
        soup = BeautifulSoup(html_page, features="html.parser")
        for link in soup.find_all('a'):
            episode = str(link.get("href"))
            if "/staffel-{}/episode-{}".format(season_count, episode_count) in episode:
                episode_count = episode_count + 1
    return episode_count - 1


def from_season():
    global episode_start_menu, episode_end_menu
    from_season = int(season_start.get()[8:])
    to_season = int(season_end.get()[8:])
    if from_season > to_season:
        to_season = from_season
        season_end.set("Season: " + str(to_season))

    episode_start_menu.destroy()
    episode_start_menu = tk.OptionMenu(root, episode_start, *["Episode: " + str(x + 1) for x in range(episodes[from_season - 1])], command=lambda x: from_episode())
    episode_start_menu.configure(bg=bg_2nd, fg=fg, border=0, borderwidth=0, highlightthickness=0, activeforeground=fg, font=("Open Sans", 15), activebackground=bg_2nd, indicatoron=False, width=11)
    episode_start_menu["menu"].configure(bg=bg_2nd, fg=fg, activeforeground=fg, font=("Open Sans", 15), activebackground=bg)
    episode_start_menu.grid(row=35, column=0, sticky="w", padx=30)
    episode_range = [x + 1 for x in range(episodes[from_season - 1])]
    from_episodev = int(episode_start.get()[9:])
    if from_episodev not in episode_range:
        from_episodev = "Episode: " + str(episode_range[-1])
        episode_start.set(from_episodev)
    episode_end_menu.destroy()
    episode_end_menu = tk.OptionMenu(root, episode_end, *["Episode: " + str(x + 1) for x in range(episodes[to_season - 1])], command=lambda x: to_episode())
    episode_end_menu.configure(bg=bg_2nd, fg=fg, border=0, borderwidth=0, highlightthickness=0, activeforeground=fg, font=("Open Sans", 15), activebackground=bg_2nd, indicatoron=False, width=11)
    episode_end_menu["menu"].configure(bg=bg_2nd, fg=fg, activeforeground=fg, font=("Open Sans", 15), activebackground=bg)
    episode_end_menu.grid(row=35, column=0, sticky="w", padx=60 + 127)
    episode_range = [x + 1 for x in range(episodes[to_season - 1])]
    to_episodev = int(episode_end.get()[9:])
    if to_episodev not in episode_range:
        to_episodev = "Episode: " + str(episode_range[-1])
        episode_end.set(to_episodev)
    from_episode()


def to_season():
    global episode_end_menu, episode_start_menu
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
    episode_range = [x + 1 for x in range(episodes[to_season - 1])]
    to_episodev = int(episode_end.get()[9:])
    if to_episodev not in episode_range:
        to_episodev = "Episode: " + str(episode_range[-1])
        episode_end.set(to_episodev)
    episode_start_menu.destroy()
    episode_start_menu = tk.OptionMenu(root, episode_start, *["Episode: " + str(x + 1) for x in range(episodes[from_season - 1])], command=lambda x: from_episode())
    episode_start_menu.configure(bg=bg_2nd, fg=fg, border=0, borderwidth=0, highlightthickness=0, activeforeground=fg, font=("Open Sans", 15), activebackground=bg_2nd, indicatoron=False, width=11)
    episode_start_menu["menu"].configure(bg=bg_2nd, fg=fg, activeforeground=fg, font=("Open Sans", 15), activebackground=bg)
    episode_start_menu.grid(row=35, column=0, sticky="w", padx=30)
    episode_range = [x + 1 for x in range(episodes[from_season - 1])]
    from_episodev = int(episode_start.get()[9:])
    if from_episodev not in episode_range:
        from_episodev = "Episode: " + str(episode_range[-1])
        episode_start.set(from_episodev)
    to_episode()


def from_episode():
    from_seasonv = season_start.get()[8:]
    to_seasonv = season_end.get()[8:]
    from_episodev = int(episode_start.get()[9:])
    to_episodev = int(episode_end.get()[9:])
    if from_seasonv == to_seasonv and from_episodev > to_episodev:
        to_episodev = from_episodev
        episode_end.set("Episode: " + str(to_episodev))


def to_episode():
    from_seasonv = season_start.get()[8:]
    to_seasonv = season_end.get()[8:]
    from_episodev = int(episode_start.get()[9:])
    to_episodev = int(episode_end.get()[9:])
    if from_seasonv == to_seasonv and from_episodev > to_episodev:
        from_episodev = to_episodev
        episode_start.set("Episode: " + str(from_episodev))


def from_movie():
    from_moviev = movie_start.get()[7:]
    to_moviev = movie_end.get()[7:]
    if from_moviev > to_moviev:
        to_moviev = from_moviev
        movie_end.set("Movie: " + str(to_moviev))


def to_movie():
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
    return_button.grid_forget()
    forget_settings()
    try:
        forget_menu_2("Episodes" if seasons > 0 else "Movies")
    except Exception as e:
        pass
    place_menu()


def language_prio_set(set_b):
    lang_1 = language_prio_1.get()
    lang_2 = language_prio_2.get()
    lang_3 = language_prio_3.get()
    lang_4 = language_prio_4.get()
    languages_prios = [language_prio_1, language_prio_2, language_prio_3, language_prio_4]

    missing = str({"Ger-Sub", "German", "Eng-Sub", "English"} - {lang_1, lang_2, lang_3, lang_4})[2:-2]
    if len(missing) > 1:
        multiple = [lang_1, lang_2, lang_3, lang_4]
        multiple.sort()
        if multiple.count(multiple[0]) == 2:
            multiple = multiple[0]
        else:
            multiple = multiple[2]
        for i in range(len(languages_prios)):
            if languages_prios[i].get() in multiple and i + 1 != set_b:
                languages_prios[i].set(str(missing))


def create_new_download_thread(url, file_name, provider) -> Thread:
    t = Thread(target=download_episode, args=(url, file_name, provider))
    if len(current_downloads) <= 10:
        t.start()
    else:
        return t


def create_download_thread():
    stop = False
    language_l = [language_prio_1.get(), language_prio_2.get(), language_prio_3.get(), language_prio_4.get()]
    if not "bs.to" in url:
        language_l[language_l.index("Eng-Sub")] = "English"
        language_l.reverse()
        language_l.remove("English")
        language_l.reverse()

    # get series name and create folder
    site = url[:url.index(".to/") + 3]
    provider = providerv.get()
    if "bs.to" in url:
        name = url[url.index("serie/") + 6:-1]
    else:
        name = url[url.index("stream/") + 7:-1]
    if name not in listdir():
        mkdir(name)

    # create queue to download
    queue = []
    if seasons > 0:
        starting_season = int(season_start.get()[8:])
        starting_episode = int(episode_start.get()[9:]) - 1
        last_season = int(season_end.get()[8:])
        last_episode = int(episode_end.get()[9:])
        for i in range(last_season - starting_season + 1):
            if "Season " + str(starting_season + i) not in listdir(name):  # create season folder
                mkdir(name + "/Season " + str(starting_season + i))
            eps = episodes[i + starting_season - 1] - starting_episode
            if i + starting_season == last_season:
                eps -= (episodes[i + starting_season - 1] - last_episode)
            for x in range(eps):
                queue.append("S{}E{}".format(i + starting_season, x + starting_episode + 1))
        for i in range(len(queue)):
            season_override = queue[0][1:queue[0].index("E")]
            episode_override = queue[0][queue[0].index("E") + 1:]
            if "bs.to" in url:
                link = url + "{}/{}-".format(season_override, episode_override)
            else:
                link = url + "staffel-{}/episode-{}".format(season_override, episode_override)
            for language in language_l:
                try:
                    cache_url, provider = looping_providers(provider, link, language, site, season_override, episode_override)
                    file_name = "{}/Season {}/S{}-E{}-{}.mp4".format(name, season_override, season_override, episode_override, name)
                    if check_create_download(file_name, provider, cache_url, language):
                        break
                except Exception as e:
                    pass
            queue.pop(0)

    elif movies > 0:
        starting_movie = int(movie_start.get()[7:])
        last_movie = int(movie_end.get()[7:])
        movie_queue = [i for i in range(last_movie - starting_movie + 1)]
        if "Movies" not in listdir(name):
            mkdir(name + "/Movies")

        for i in movie_queue:
            link = url + "filme/film-{}".format(i + starting_movie)
            for language in language_l:
                try:
                    cache_url, provider = looping_providers(provider, link, language, site, 0, i + starting_movie)
                    file_name = "{}/Movies/Movie {}-{}.mp4".format(name, i + starting_movie, name)
                    if check_create_download(file_name, provider, cache_url, language):
                        break
                except Exception as e:
                    pass
            movie_queue.pop(0)

    return_button.grid_forget()
    forget_menu_2("Episodes" if seasons > 0 else "Movies")
    place_menu()


def looping_providers(provider, link, language, site, season, episode):
    global cache_url_attempts
    local_provider_priority = provider_priority.copy()
    local_provider_priority.remove(provider)
    local_provider_priority.insert(0, provider)
    for x in local_provider_priority:
        redirect_link = get_redirect_link_by_provider(site, link, language, x, season, episode)
        if redirect_link is not None:
            cache_url_attempts = 0
            cache_url = find_content_url(redirect_link, x)
            if cache_url:
                provider = x
                break
    return cache_url, provider


def check_create_download(file_name, provider, cache_url, language):
    if path.exists(file_name):
        print(f"{Fore.LIGHTBLUE_EX}Episode {file_name} already downloaded.{Style.RESET_ALL}")
    elif cache_url:
        print(f"{Fore.LIGHTBLUE_EX}Provider {provider} - File {file_name} added to queue{Style.RESET_ALL}")
        r_t = create_new_download_thread(cache_url, file_name, provider)
        if r_t is not None:
            pending_queue.append(r_t)
    else:
        print(f"{Fore.RED}Episode {file_name} coudn't be downloaded in {language}.{Style.RESET_ALL}")
        raise Exception("language change")
    return True


def enable_disable_searchbar(name):
    global searchbar_aniworld, searchbar_sto, searchbar_bsto
    global aniworld_titles_dict, sto_titles_dict, bsto_titles_dict
    if name == "Aniworld":
        if searchbar_aniworld:
            searchbar_aniworld = 0
            aniworld_button["fg"] = fg
        else:
            searchbar_aniworld = 1
            aniworld_button["fg"] = bg
            if not aniworld_titles_dict:
                aniworld_titles_dict = get_titles_dict("https://aniworld.to/animes")
    elif name == "Sto":
        if searchbar_sto:
            searchbar_sto = 0
            sto_button["fg"] = fg
        else:
            searchbar_sto = 1
            sto_button["fg"] = bg
            if not sto_titles_dict:
                sto_titles_dict = get_titles_dict("https://s.to/serien")
    elif name == "BSto":
        if searchbar_bsto:
            searchbar_bsto = 0
            bsto_button["fg"] = fg
        else:
            searchbar_bsto = 1
            bsto_button["fg"] = bg
            if not bsto_titles_dict:
                bsto_titles_dict = get_titles_dict_2("https://bs.to/andere-serien")
    update_settings_file()


def place_menu_setting():
    global c_menu
    c_menu = 2
    forget_menu()

    return_button.grid(row=0, column=0, sticky="w")
    searchbar_label.grid(row=1, column=0, sticky="w", padx=30)
    aniworld_button.grid(row=2, column=0, sticky="w", padx=30)
    sto_button.grid(row=3, column=0, sticky="w", padx=30)
    bsto_button.grid(row=4, column=0, sticky="w", padx=30)


def place_menu_2(title):
    global c_menu
    global episode_start_menu, episode_end_menu, season_start_menu, season_end_menu, movie_start_menu, movie_end_menu
    c_menu = 1

    series_name_label.config(text=title)
    series_name_label.grid(row=0, column=0)

    if seasons != 0:
        seasonsv = ["Season: " + str(i + 1) for i in range(seasons)]
        episodesv = ["Episode: " + str(i + 1) for i in range(episodes[0])]
        season_start.set(seasonsv[0])
        season_end.set(seasonsv[0])
        episode_start.set(episodesv[0])
        episode_end.set(episodesv[-1])

        season_start_menu = tk.OptionMenu(root, season_start, *seasonsv, command=lambda x: from_season())
        season_start_menu.configure(bg=bg_2nd, fg=fg, border=0, borderwidth=0, highlightthickness=0, activeforeground=fg, font=("Open Sans", 15), activebackground=bg_2nd, indicatoron=False, width=11)
        season_start_menu["menu"].configure(bg=bg_2nd, fg=fg, activeforeground=fg, font=("Open Sans", 15), activebackground=bg)
        season_end_menu = tk.OptionMenu(root, season_end, *seasonsv, command=lambda x: to_season())
        season_end_menu.configure(bg=bg_2nd, fg=fg, border=0, borderwidth=0, highlightthickness=0, activeforeground=fg, font=("Open Sans", 15), activebackground=bg_2nd, indicatoron=False, width=11)
        season_end_menu["menu"].configure(bg=bg_2nd, fg=fg, activeforeground=fg, font=("Open Sans", 15), activebackground=bg)
        episode_start_menu = tk.OptionMenu(root, episode_start, *episodesv, command=lambda x: from_episode())
        episode_start_menu.configure(bg=bg_2nd, fg=fg, border=0, borderwidth=0, highlightthickness=0, activeforeground=fg, font=("Open Sans", 15), activebackground=bg_2nd, indicatoron=False, width=11)
        episode_start_menu["menu"].configure(bg=bg_2nd, fg=fg, activeforeground=fg, font=("Open Sans", 15), activebackground=bg)
        episode_end_menu = tk.OptionMenu(root, episode_end, *episodesv, command=lambda x: to_episode())
        episode_end_menu.configure(bg=bg_2nd, fg=fg, border=0, borderwidth=0, highlightthickness=0, activeforeground=fg, font=("Open Sans", 15), activebackground=bg_2nd, indicatoron=False, width=11)
        episode_end_menu["menu"].configure(bg=bg_2nd, fg=fg, activeforeground=fg, font=("Open Sans", 15), activebackground=bg)
        season_start_menu.grid(row=30, column=0, sticky="w", padx=30)
        season_end_menu.grid(row=30, column=0, sticky="w", padx=187)
        episode_start_menu.grid(row=35, column=0, sticky="w", padx=30)
        episode_end_menu.grid(row=35, column=0, sticky="w", padx=187)

    elif movies != 0:
        moviesv = ["Movie: " + str(i + 1) for i in range(movies)]
        movie_start.set(moviesv[0])
        movie_end.set(moviesv[-1])

        movie_start_menu = tk.OptionMenu(root, movie_start, *moviesv, command=lambda x: from_movie())
        movie_start_menu.configure(bg=bg_2nd, fg=fg, border=0, borderwidth=0, highlightthickness=0, activeforeground=fg, font=("Open Sans", 15), activebackground=bg_2nd, indicatoron=False, width=11)
        movie_start_menu["menu"].configure(bg=bg_2nd, fg=fg, activeforeground=fg, font=("Open Sans", 15), activebackground=bg)
        movie_end_menu = tk.OptionMenu(root, movie_end, *moviesv, command=lambda x: to_movie())
        movie_end_menu.configure(bg=bg_2nd, fg=fg, border=0, borderwidth=0, highlightthickness=0, activeforeground=fg, font=("Open Sans", 15), activebackground=bg_2nd, indicatoron=False, width=11)
        movie_end_menu["menu"].configure(bg=bg_2nd, fg=fg, activeforeground=fg, font=("Open Sans", 15), activebackground=bg)
        movie_start_menu.grid(row=30, column=0, sticky="w", padx=30)
        movie_end_menu.grid(row=30, column=0, sticky="w", padx=187)

    start_label.grid(row=25, column=0, sticky="w", padx=30, ipadx=2)
    end_label.grid(row=25, column=0, sticky="w", padx=60 + 127, ipadx=2)
    provider_label.grid(row=25, column=0, sticky="w", padx=217 + end_label.winfo_reqwidth())

    providerv.set("Vidmoly")
    provider_menu.grid(row=30, column=0, sticky="w", padx=217 + end_label.winfo_reqwidth())
    options_label.grid(row=25, column=0, sticky="e", padx=200)
    if shutdown:
        shutdown_button["fg"] = bg
    else:
        shutdown_button["fg"] = fg
    shutdown_button.grid(row=30, column=0, sticky="e", padx=200)
    language_label.grid(row=20, column=0, sticky="e", padx=30, rowspan=6)
    return_button.grid(row=0, column=0, sticky="w")

    language_prio_1.set(languages[1])
    language_prio_2.set(languages[0])
    language_prio_3.set(languages[2])
    language_prio_4.set(languages[3])
    language_menu_1.grid(row=30, column=0, sticky="e", padx=30)
    language_menu_2.grid(row=35, column=0, sticky="e", padx=30)
    language_menu_3.grid(row=41, column=0, sticky="e", padx=30)
    language_menu_4.grid(row=47, column=0, sticky="e", padx=30)

    create_thread_button.grid(row=150, column=0)


def place_menu():
    global c_menu
    c_menu = 0
    link_entry.delete(0, "end")
    link_entry.insert(0, "Link: https://aniworld.to/anime/stream/monogatari")
    link_entry.grid(row=90, column=0, ipady=10)
    name_label.grid(row=0, column=0)
    type_label.grid(row=83, column=0, sticky="w", padx=13)
    type_menu.grid(row=88, column=0, sticky="w", padx=13)
    confirm_button.grid(row=91, column=0)
    downloads_list.grid(row=91, column=0, sticky="w", padx=13)
    website_button.place(x=800 - 14 - website_button.winfo_reqwidth(), y=6)
    gear_button.place(x=800 - 14 - gear_button.winfo_reqwidth(), y=196)
    if version < latest_version:
        update_button.grid(row=200, column=0, sticky="w", padx=13)


def forget_settings():
    searchbar_label.grid_forget()
    aniworld_button.grid_forget()
    sto_button.grid_forget()
    bsto_button.grid_forget()


def forget_menu():
    name_label.grid_forget()
    link_entry.grid_forget()
    confirm_button.grid_forget()
    downloads_list.grid_forget()
    type_menu.grid_forget()
    type_label.grid_forget()
    website_button.place_forget()
    gear_button.place_forget()
    try:
        filtered_anime_list.destroy()
    except Exception as e:
        pass
    if version < latest_version:
        update_button.grid_forget()


def forget_menu_2(*args):
    if "Episodes" in args:
        season_start_menu.destroy()
        season_end_menu.destroy()
        episode_start_menu.destroy()
        episode_end_menu.destroy()
    elif "Movies" in args:
        movie_start_menu.destroy()
        movie_end_menu.destroy()
    shutdown_button.grid_forget()
    create_thread_button.grid_forget()
    provider_menu.grid_forget()
    series_name_label.grid_forget()
    start_label.grid_forget()
    end_label.grid_forget()
    provider_label.grid_forget()
    options_label.grid_forget()
    language_menu_1.grid_forget()
    language_menu_2.grid_forget()
    language_menu_3.grid_forget()
    language_menu_4.grid_forget()
    language_label.grid_forget()


def initiate_menus():
    global link_entry, name_label, type_label, type_menu, confirm_button, downloads_list, website_button, update_button, typev
    global series_name_label, season_start, season_end, episode_start, episode_end
    global movie_start, movie_end, start_label, end_label, provider_label, providerv, provider_menu
    global options_label, shutdown_button, language_label, return_button, create_thread_button, gear_button
    global language_prio_1, language_prio_2, language_prio_3, language_prio_4, language_menu_1, language_menu_2, language_menu_3, language_menu_4
    global searchbar_label, aniworld_button, sto_button, bsto_button
    # menu 1
    link_entry = tk.Entry(root, width=70, bg=bg_2nd, fg=fg, font=("Open Sans", 15))
    link_entry.bind("<FocusIn>", lambda x: entry_focus_in(link_entry))
    link_entry.bind("<FocusOut>", lambda x: entry_focus_out(link_entry))
    if network_status:
        link_entry.bind("<Key>", get_event)
    name_label = tk.Label(root, text="ANIWORLD DOWNLOADER", bg=bg, fg=bg_2nd, font=("Open Sans", 30))
    type_label = tk.Label(root, text="Type", bg=bg, fg=bg_2nd, font=("Open Sans", 15), width=8)
    typev = tk.StringVar()
    typev.set("Episodes")
    type_menu = tk.OptionMenu(root, typev, *types)
    type_menu.configure(bg=bg_2nd, fg=fg, border=0, borderwidth=0, highlightthickness=0, activeforeground=fg, font=("Open Sans", 15), activebackground=bg_2nd, indicatoron=False, width=8)
    type_menu["menu"].configure(bg=bg_2nd, fg=fg, border=0, borderwidth=0, activeforeground=fg, font=("Open Sans", 15), activebackground=bg)
    confirm_button = tk.Button(root, text="Confirm", bg=bg_2nd, width=10, border=0, fg=fg, height=1, font=("Open Sans", 15), command=lambda: confirm_link(link_entry.get()))
    downloads = tk.StringVar()
    downloads.set("Current Downloads")
    downloads_list = tk.OptionMenu(root, downloads, *current_downloads)
    downloads_list.configure(bg=bg_2nd, fg=fg, border=0, borderwidth=0, highlightthickness=0, activeforeground=fg, font=("Open Sans", 15), activebackground=bg_2nd, indicatoron=False)
    downloads_list["menu"].configure(bg=bg_2nd, fg=fg, border=0, borderwidth=0, activeforeground=fg, font=("Open Sans", 15), activebackground=bg)
    website_button = tk.Button(root, text="Itch", bg=bg_2nd, width=9, border=0, fg=fg, height=1, font=("Open Sans", 15), command=lambda: webopen("https://ninjaminebro.itch.io/aniworld-downloader"))
    logo_label = tk.Label(root, width=12, height=1, text="Made by NMB", bg=bg, fg="#8EA1BD", font=("Open Sans", 15))
    update_button = tk.Button(root, text="Update", bg=bg_2nd, fg=fg, font=("Open Sans", 25), command=update)
    logo_label.grid(row=201, column=0, sticky="w", padx=6)
    gear_button = tk.Button(root, text="⚙", bg=bg_2nd, fg=fg, font=("Open Sans", 15), command=lambda: place_menu_setting(), border=0, pady=0, padx=0)
    # menu 2
    series_name_label = tk.Label(root, text="placeholder", font=("Open Sans", 30), fg=bg_2nd, bg=bg)
    season_start = tk.StringVar()
    season_end = tk.StringVar()
    episode_start = tk.StringVar()
    episode_end = tk.StringVar()
    movie_start = tk.StringVar()
    movie_end = tk.StringVar()
    start_label = tk.Label(root, text="Start from", font=("Open Sans", 15), fg=bg_2nd, bg=bg, width=11)
    end_label = tk.Label(root, text="End at", font=("Open Sans", 15), fg=bg_2nd, bg=bg, width=11)
    provider_label = tk.Label(root, text="Provider", font=("Open Sans", 15), fg=bg_2nd, bg=bg, width=15)
    providerv = tk.StringVar()
    provider_menu = tk.OptionMenu(root, providerv, *providers)
    provider_menu.configure(bg=bg_2nd, fg=fg, border=0, borderwidth=0, highlightthickness=0, activeforeground=fg, font=("Open Sans", 15), activebackground=bg_2nd, indicatoron=False, width=15)
    provider_menu["menu"].configure(bg=bg_2nd, fg=fg, activeforeground=fg, font=("Open Sans", 15), activebackground=bg)
    options_label = tk.Label(root, text="Options", font=("Open Sans", 15), fg=bg_2nd, bg=bg, width=10)
    shutdown_button = tk.Button(root, text="Shutdown", font=("Open Sans", 15), fg=fg, bg=bg_2nd, width=10, bd=False, height=1, command=lambda: shutdown_setting())
    language_label = tk.Label(root, text="Language\npriority", font=("Open Sans", 15), fg=bg_2nd, bg=bg, width=12, bd=False, height=2)
    return_button = tk.Button(root, text="←", font=("Open Sans", 25), fg=bg_2nd, bg=bg, width=3, bd=False, height=1, command=lambda: return_menu())
    language_prio_1 = tk.StringVar()
    language_prio_2 = tk.StringVar()
    language_prio_3 = tk.StringVar()
    language_prio_4 = tk.StringVar()
    language_menu_1 = tk.OptionMenu(root, language_prio_1, *languages, command=lambda x: language_prio_set(1))
    language_menu_2 = tk.OptionMenu(root, language_prio_2, *languages, command=lambda x: language_prio_set(2))
    language_menu_3 = tk.OptionMenu(root, language_prio_3, *languages, command=lambda x: language_prio_set(3))
    language_menu_4 = tk.OptionMenu(root, language_prio_4, *languages, command=lambda x: language_prio_set(4))
    language_menu_1.configure(bg=bg_2nd, fg=fg, border=0, borderwidth=0, highlightthickness=0, activeforeground=fg, font=("Open Sans", 15), activebackground=bg_2nd, indicatoron=False, width=12)
    language_menu_2.configure(bg=bg_2nd, fg=fg, border=0, borderwidth=0, highlightthickness=0, activeforeground=fg, font=("Open Sans", 15), activebackground=bg_2nd, indicatoron=False, width=12)
    language_menu_3.configure(bg=bg_2nd, fg=fg, border=0, borderwidth=0, highlightthickness=0, activeforeground=fg, font=("Open Sans", 15), activebackground=bg_2nd, indicatoron=False, width=12)
    language_menu_4.configure(bg=bg_2nd, fg=fg, border=0, borderwidth=0, highlightthickness=0, activeforeground=fg, font=("Open Sans", 15), activebackground=bg_2nd, indicatoron=False, width=12)
    language_menu_1["menu"].configure(bg=bg_2nd, fg=fg, activeforeground=fg, font=("Open Sans", 15), activebackground=bg)
    language_menu_2["menu"].configure(bg=bg_2nd, fg=fg, activeforeground=fg, font=("Open Sans", 15), activebackground=bg)
    language_menu_3["menu"].configure(bg=bg_2nd, fg=fg, activeforeground=fg, font=("Open Sans", 15), activebackground=bg)
    language_menu_4["menu"].configure(bg=bg_2nd, fg=fg, activeforeground=fg, font=("Open Sans", 15), activebackground=bg)
    create_thread_button = tk.Button(root, text="Start", font=("Open Sans", 15), fg=fg, bg=bg_2nd, width=17, bd=False, height=1, command=lambda: create_download_thread())
    # settings
    # return button from menu 2
    searchbar_label = tk.Label(root, text="Searchbars:", font=("Open Sans", 15), fg=bg_2nd, bg=bg)
    aniworld_button = tk.Button(root, text="Aniworld", font=("Open Sans", 15), fg=bg if searchbar_aniworld else fg, bg=bg_2nd, width=10, bd=False, height=1, command=lambda: enable_disable_searchbar("Aniworld"))
    sto_button = tk.Button(root, text="s.to", font=("Open Sans", 15), fg=bg if searchbar_sto else fg, bg=bg_2nd, width=10, bd=False, height=1, command=lambda: enable_disable_searchbar("Sto"))
    bsto_button = tk.Button(root, text="Bs.to", font=("Open Sans", 15), fg=bg if searchbar_bsto else fg, bg=bg_2nd, width=10, bd=False, height=1, command=lambda: enable_disable_searchbar("BSto"))


initiate_menus()
place_menu()
root.bind("<Button-1>", lambda x: focus_out())
root.mainloop()
