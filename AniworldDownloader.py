from urllib.request import Request as Rqst
from bs4 import BeautifulSoup
from os import getcwd, remove, system, listdir, mkdir, path
from re import compile, search, DOTALL, match
from threading import Thread
from time import time, sleep
import subprocess
from zipfile import ZipFile
from random import choices
from string import ascii_letters, digits
from seleniumbase import SB
from base64 import b64decode
import json
from urllib.request import urlopen
import logger

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


class Download:
    pending_queue = []
    active_queue_checker = False
    url = ""  # gets set in create_download_thread
    cache_url_attempts = 0

    def __init__(self, configMenu):
        self.configMenu = configMenu
        self.menuMain = configMenu.menuMain
        self.settings = configMenu.settings

    def getRedirectLinkByProvider(self, internal_link, language, provider, season, episode):
        try:
            return self.getRedirectLink(internal_link, language, provider, season, episode)
        except ProviderError:
            if self.configMenu.provider_prio.index(provider) == len(self.configMenu.provider_prio):
                logger.error(f"Provider {provider} failed. Can not download episode.")
            else:
                logger.warning(f"Provider {provider} failed. Trying next provider.")

    def getRedirectLink(self, html_link, language, provider, season, episode):
        link_to_redirect = None
        site = "https://" + self.configMenu.getHostWebsite(self.url)
        if "bs.to" in self.url:
            href_value = self.getBsHrefByLanguage(html_link, language, provider, season, episode)
            link_to_episode = site + href_value
            link_to_redirect = self.findBsLinkToEpisode(link_to_episode, provider)
        elif "aniworld.to" in self.url:
            href_value = self.getHrefByLanguageAniworld(html_link, language, provider)
            link_to_redirect = site + href_value
        elif "s.to" in self.url:
            href_value = self.getHrefByLanguageSto(html_link, language, provider)
            link_to_redirect = site + href_value
        return link_to_redirect

    def findBsLinkToEpisode(self, url, provider):
        try:
            with SB(uc=True, headless2=True,
                    extension_dir=self.findAndUnzipCrx()) as sb:
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
        except Exception as e:
            if "Chrome not found!" in str(e):
                logger.error("To download from burning Series you need to have chrome installed")
        print(content_link)
        return content_link

    def findAndUnzipCrx(self):
        crx_file_path = getcwd() + "/recaptcha-solver.crx"
        with ZipFile(crx_file_path, 'r') as zip_ref:
            zip_ref.extractall(getcwd())
        return getcwd()

    def restructureDict(self, given_dict):
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

    def extractLangKeyMapping(self, soup):
        lang_key_mapping = {}
        change_language_div = soup.find("div", class_="changeLanguageBox")
        if change_language_div:
            lang_elements = change_language_div.find_all("img")
            for lang_element in lang_elements:
                language = lang_element.get("alt", "") + "," + lang_element.get("title", "")
                data_lang_key = lang_element.get("data-lang-key", "")
                if language and data_lang_key:
                    lang_key_mapping[language] = data_lang_key
        return self.restructureDict(lang_key_mapping)

    def getHrefByLanguageAniworld(self, url, language, provider):
        html_content = urlopen(url)
        soup = BeautifulSoup(html_content, "html.parser")
        lang_key_mapping = self.extractLangKeyMapping(soup)
        lang_key = lang_key_mapping.get(language)
        if lang_key is None:
            raise LanguageError(logger.info(f"Invalid language input. Supported languages: "
                                            f"{list(lang_key_mapping.keys())}"))
        matching_li_elements = soup.find_all("li", {"data-lang-key": lang_key})
        matching_li_element = next(
            (li_element for li_element in matching_li_elements if li_element.find("h4").get_text() == provider), None)
        if matching_li_element:
            href = matching_li_element.get("data-link-target", "")
            return href
        raise ProviderError

    def getHrefByLanguageSto(self, url, language, provider):
        html_content = urlopen(url)
        soup = BeautifulSoup(html_content, "html.parser")
        sto_language_mapping = {
            "German": "Deutsch",
            "Ger-Sub": "Ger-Sub",
            "Eng-Sub": "jps",
            "English": "English"}
        lang_key = sto_language_mapping.get(language)
        matching_li_elements = soup.find("button", {"data-language-label": lang_key, "data-provider-name": provider})
        if matching_li_elements:
            href = matching_li_elements.get("data-play-url", "")
            return href

    def getBsHrefByLanguage(self, url, language, provider, season, episode):
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

    def findScriptElementVoenew(self, raw_html):
        soup = BeautifulSoup(raw_html, features="html.parser")
        MKGMa_pattern = r'MKGMa="(.*?)"'
        matches = search(MKGMa_pattern, str(soup), DOTALL)

        if not matches:
            MKGMa_pattern = r'<script type="application/json">.*\[(.*?)\]</script>'
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

    def findContentUrl(self, url, provider):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
        req = Rqst(url, headers=headers)
        decoded_html = urlopen(req).read().decode("utf-8")
        content_link = ""
        try:
            if provider == "Vidoza":
                soup = BeautifulSoup(decoded_html, features="html.parser")
                content_link = soup.find("source").get("src")
            elif provider == "VOE":
                html_page = urlopen(url)
                html_page = html_page.read().decode('utf-8')
                ## New Version of VOE 2025-05-01
                cache_url = self.findScriptElementVoenew(html_page)
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
                            return self.findContentUrl(matches.group(1), provider)
                        cache_link = matches.group(1)
                        cache_link = b64decode(cache_link).decode('utf-8')
                        if cache_link and cache_link.startswith("https://"):
                            return cache_link
                return 0
            elif provider == "Streamtape":
                content_link = STREAMTAPE_PATTERN.search(decoded_html)
                if content_link is None:
                    return self.findContentUrl(url, provider)
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
                    logger.warning(f"Failed to find the video link of provider Vidmoly")
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
                for char in next_content:
                    content_link += chr(ord(char) - 3)
                content_link = content_link.swapcase()
                content_link = ''.join(reversed(content_link))
                content_link = b64decode(content_link).decode()
        except AttributeError as e:
            logger.warning(f"ERROR: {e}")  # only warning because it will just try again
            logger.info(f"Trying again...")
            if self.cache_url_attempts < 3:
                self.cache_url_attempts += 1
                return self.findContentUrl(url, provider)
            else:
                logger.warning(f"Could not find cache url for {provider}")
                return 0
        return content_link

    def downloadEpisode(self, url, fileName, provider):
        displayName = fileName[fileName.index("/") + 1:-4]
        displayName = displayName[displayName.index("/") + 1:]
        logger.info(f"File not downloaded. Downloading: {displayName}")
        try:
            self.menuMain.current_downloads.append(displayName)
            if self.menuMain.downloads_list.grid_info():
                self.menuMain.updateOptionMenu()

            ffmpeg_cmd = ["ffmpeg", "-i", url, "-c", "copy", "-nostdin", f"{self.settings.settings.get('pathDownload')}/{fileName}"]
            if provider == "Doodstream":
                ffmpeg_cmd.insert(1, "Referer: https://d0000d.com/")
                ffmpeg_cmd.insert(1, "-headers")
            elif provider == "Vidmoly":
                ffmpeg_cmd.insert(1, "Referer: https://vidmoly.to/")
                ffmpeg_cmd.insert(1, "-headers")
            subprocess.run(ffmpeg_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            logger.success(f"Finished download of {displayName}")
            self.menuMain.current_downloads.remove(displayName)
            self.menuMain.updateOptionMenu()
        except subprocess.CalledProcessError as e:
            remove(f"{self.settings.settings.get('pathDownload')}/{fileName}") if path.exists(
                f"{self.settings.settings.get('pathDownload')}/{fileName}") else None
            logger.error(f"{str(e)}")
            logger.error(f"Error while downloading {displayName}. Retrying...")
            self.menuMain.current_downloads.remove(displayName)
            self.menuMain.updateOptionMenu()
            self.createNewDownloadThread(url, fileName, provider)
        if self.pending_queue:
            self.pending_queue.pop(0).start()
        if len(self.menuMain.current_downloads) == 1 and self.settings.settings.get('shutdown'):
            system('shutdown -s')

    def createNewDownloadThread(self, url, fileName, provider):
        t = Thread(target=self.downloadEpisode, args=(url, fileName, provider))
        if len(self.pending_queue) > 0 or len(self.menuMain.current_downloads) > self.settings.settings.get("limitDownload"):
            self.pending_queue.append(t)
        else:
            t.start()

    def createDownloadThread(self, url):
        self.url = url
        languages = [self.configMenu.language_prio_1.get(), self.configMenu.language_prio_2.get(),
                     self.configMenu.language_prio_3.get(), self.configMenu.language_prio_4.get()]
        if "bs.to" not in self.url:
            languages[languages.index("Eng-Sub")] = "English"
            languages.reverse()
            languages.remove("English")
            languages.reverse()

        # get series name and create folder
        provider = self.configMenu.providerv.get()
        name = ""
        if "bs.to" in self.url or "s.to" in self.url:
            name = self.url[self.url.index("serie/") + 6:-1]
        elif "aniworld.to" in self.url:
            name = self.url[self.url.index("stream/") + 7:-1]
        if name not in listdir(self.settings.settings.get('pathDownload')):
            mkdir(f"{self.settings.settings.get('pathDownload')}/{name}")

        # create queue to download
        queue = []
        if self.configMenu.seasons > 0:
            starting_season = int(self.configMenu.season_start.get()[8:])
            starting_episode = int(self.configMenu.episode_start.get()[9:]) - 1
            last_season = int(self.configMenu.season_end.get()[8:])
            last_episode = int(self.configMenu.episode_end.get()[9:])
            for i in range(last_season - starting_season + 1):
                if "Season " + str(starting_season + i) not in listdir(
                        f"{self.settings.settings.get('pathDownload')}/{name}"):  # create season folder
                    mkdir(f"{self.settings.settings.get('pathDownload')}/{name}/Season {str(starting_season + i)}")
                eps = self.configMenu.episodes[i + starting_season - 1] - starting_episode
                if i + starting_season == last_season:
                    eps -= (self.configMenu.episodes[i + starting_season - 1] - last_episode)
                for x in range(eps):
                    queue.append("S{}E{}".format(i + starting_season, x + starting_episode + 1))
            for i in range(len(queue)):
                season_override = queue[0][1:queue[0].index("E")]
                episode_override = queue[0][queue[0].index("E") + 1:]
                if "bs.to" in self.url:
                    link = self.url + "{}/{}-".format(season_override, episode_override)
                else:
                    link = self.url + "staffel-{}/episode-{}".format(season_override, episode_override)
                for language in languages:
                    try:
                        cache_url, provider = self.loopingProviders(provider, link, language, season_override,
                                                                    episode_override)
                        file_name = "{}/Season {}/S{}-E{}-{}.mp4".format(name, season_override, season_override,
                                                                         episode_override, name)
                        if self.checkCreateDownload(file_name, provider, cache_url, language):
                            break
                    except Exception as e:
                        pass
                queue.pop(0)

        elif self.configMenu.movies > 0:
            starting_movie = int(self.configMenu.movie_start.get()[7:])
            last_movie = int(self.configMenu.movie_end.get()[7:])
            movie_queue = [i for i in range(last_movie - starting_movie + 1)]
            if "Movies" not in listdir(f"{self.settings.settings.get('pathDownload')}/{name}"):
                mkdir(f"{self.settings.settings.get('pathDownload')}/{name}/Movies")

            for i in range(len(movie_queue)):
                link = ""
                if "bs.to" in self.url:
                    link = self.url + f"0/{movie_queue[0] + starting_movie}-S"
                if "aniworld.to" in self.url:
                    link = self.url + "filme/film-{}".format(movie_queue[0] + starting_movie)
                elif "s.to" in self.url:
                    link = f"{self.url}staffel-0/episode-{movie_queue[0] + starting_movie}"
                for language in languages:
                    try:
                        cache_url, provider = self.loopingProviders(provider, link, language, 0,
                                                                    movie_queue[0] + starting_movie)
                        file_name = "{}/Movies/Movie {}-{}.mp4".format(name, movie_queue[0] + starting_movie, name)
                        if self.checkCreateDownload(file_name, provider, cache_url, language):
                            break
                    except Exception as e:
                        if "bs.to" in self.url:
                            link = self.url + f"0/{movie_queue[0] + starting_movie}-M"
                            try:
                                cache_url, provider = self.loopingProviders(provider, link, language, 0,
                                                                            movie_queue[0] + starting_movie)
                                file_name = "{}/Movies/Movie {}-{}.mp4".format(name, movie_queue[0] + starting_movie,
                                                                               name)
                                if self.checkCreateDownload(file_name, provider, cache_url, language):
                                    break
                            except Exception as e:
                                pass
                        else:
                            logger.error(str(e))
                movie_queue.pop(0)

        self.configMenu.return_button.grid_forget()
        self.configMenu.forgetMenu("Episodes" if self.configMenu.seasons > 0 else "Movies")
        self.menuMain.placeMenu()

    def loopingProviders(self, provider, link, language, season, episode):
        local_provider_priority = self.configMenu.provider_prio.copy()
        local_provider_priority.remove(provider)  # move selected provider to the highest priority
        local_provider_priority.insert(0, provider)  # hand in hand with above
        for x in local_provider_priority:
            redirect_link = self.getRedirectLinkByProvider(link, language, x, season, episode)
            if redirect_link is not None:
                self.cache_url_attempts = 0
                cache_url = self.findContentUrl(redirect_link, x)
                if cache_url:
                    provider = x
                    break
        return cache_url, provider

    def checkCreateDownload(self, fileName, provider, cache_url, language):
        if path.exists(f"{self.settings.settings.get('pathDownload')}/{fileName}"):
            logger.info(f"{fileName} is already downloaded.")
        elif cache_url:
            logger.info(f"Provider {provider} - File {fileName} added to queue")
            self.createNewDownloadThread(cache_url, fileName, provider)
        else:
            logger.error(f"Episode {fileName} couldn't be downloaded in {language}.")
            raise Exception("language change")
        return True
