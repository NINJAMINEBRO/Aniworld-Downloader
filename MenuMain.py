import tkinter as tk
from Colors import Colors as Color
from Fonts import Fonts as Font
from SupportedWebsites import SupportedWebsites
from webbrowser import open as webopen
from urllib.request import urlopen
from os import getcwd, rename, startfile
from zipfile import ZipFile
from io import BytesIO
from bs4 import BeautifulSoup
import logger


class MenuMain:
    types = ["Episodes", "Movies"]
    hostWebsite = ""
    current_downloads = ["Current Downloads"]
    seasons = 0
    episodes = []
    movies = 0

    def __init__(self, root, network, version, newestVersion, settingsMenu, settings, configureMenu):
        self.configureMenu = configureMenu
        self.settings = settings
        self.settingsMenu = settingsMenu
        self.version = version
        self.newestVersion = newestVersion
        self.root = root
        self.link_entry = tk.Entry(self.root, width=70, bg=Color.bg_2nd, fg=Color.fg, font=Font.font15)
        self.link_entry.bind("<FocusIn>", lambda x: self.entry_focus_in(self.link_entry))
        self.link_entry.bind("<FocusOut>", lambda x: self.entry_focus_out(self.link_entry))
        if network:
            self.link_entry.bind("<Key>", self.get_event)

        self.name_label = tk.Label(self.root, text="ANIWORLD DOWNLOADER", bg=Color.bg, fg=Color.bg_2nd,
                                   font=Font.font30)
        self.type_label = tk.Label(self.root, text="Type", bg=Color.bg, fg=Color.bg_2nd, font=Font.font15,
                                   width=8)
        self.typev = tk.StringVar()
        self.typev.set("Episodes")
        self.type_menu = tk.OptionMenu(self.root, self.typev, *self.types)
        self.type_menu.configure(bg=Color.bg_2nd, fg=Color.fg, border=0, borderwidth=0, highlightthickness=0,
                                 activeforeground=Color.fg, font=Font.font15, activebackground=Color.bg_2nd,
                                 indicatoron=False, width=8)
        self.type_menu["menu"].configure(bg=Color.bg_2nd, fg=Color.fg, border=0, borderwidth=0,
                                         activeforeground=Color.fg,
                                         font=Font.font15, activebackground=Color.bg)
        self.confirm_button = tk.Button(self.root, text="Confirm", bg=Color.bg_2nd, width=10, border=0, fg=Color.fg,
                                        height=1, font=Font.font15,
                                        command=lambda: self.confirm_link(self.link_entry.get()))
        self.downloads = tk.StringVar()
        self.downloads.set("Current Downloads")
        self.downloads_list = tk.OptionMenu(self.root, self.downloads, *self.current_downloads)
        self.downloads_list.configure(bg=Color.bg_2nd, fg=Color.fg, border=0, borderwidth=0, highlightthickness=0,
                                      activeforeground=Color.fg, font=Font.font15, activebackground=Color.bg_2nd,
                                      indicatoron=False)
        self.downloads_list["menu"].configure(bg=Color.bg_2nd, fg=Color.fg, border=0, borderwidth=0,
                                              activeforeground=Color.fg, font=Font.font15,
                                              activebackground=Color.bg)
        self.website_button = tk.Button(self.root, text="Itch", bg=Color.bg_2nd, width=9, border=0, fg=Color.fg,
                                        height=1, font=Font.font15,
                                        command=lambda: webopen("https://ninjaminebro.itch.io/aniworld-downloader"))
        self.logo_label = tk.Label(self.root, width=12, height=1, text="Made by NMB", bg=Color.bg, fg="#8EA1BD",
                                   font=Font.font15)
        self.update_button = tk.Button(self.root, text="Update", bg=Color.bg_2nd, fg=Color.fg, font=Font.font25,
                                       command=self.update)
        self.logo_label.grid(row=201, column=0, sticky="w", padx=6)
        self.gear_button = tk.Button(self.root, text="⚙", bg=Color.bg_2nd, fg=Color.fg, font=Font.font15,
                                     command=lambda: self.placeMenuSetting(), border=0, pady=0, padx=0)

        self.filtered_anime = tk.StringVar()
        self.filtered_anime_list = tk.OptionMenu(self.root, self.filtered_anime, "Temp")

    def get_event(self, event):
        self.input_handler(event, self.link_entry)

    def entry_focus_in(self, entry):
        if entry.get() == "Link: https://aniworld.to/anime/stream/monogatari":
            entry.delete(0, "end")

    def entry_focus_out(self, entry):
        if not entry.get():
            entry.insert(0, "Link: https://aniworld.to/anime/stream/monogatari")
            try:
                self.filtered_anime_list.destroy()
            except Exception as e:
                pass

    def confirm_link(self, link):
        link = self.linkValidator(link)
        if link:
            self.resetVariables()
            if self.typev.get() == "Episodes":
                self.seasons = self.get_season(link)
                if self.seasons:
                    self.episodes.clear()
                    for i in range(self.seasons):
                        self.episodes.append(self.get_episodes(link, i + 1))
                    self.forgetMenu()
                    self.configureMenu.placeMenu(link)
                else:
                    logger.info(f"Anime/Series not found")

            elif self.typev.get() == "Movies":
                self.movies = self.get_movies(link)
                if self.movies:
                    self.forgetMenu()
                    self.configureMenu.placeMenu(link)
                else:
                    logger.info(f"Anime/Series not found")
        else:
            logger.info(f"That Link is invalid")

    def linkValidator(self, link):
        supported = False
        if link[:6] != "Link: ":
            for website in SupportedWebsites.supportedWebsites:
                if website in link:
                    supported = True

            if link[-1] != "/":
                link += "/"

        if supported:
            return link
        return ""

    def resetVariables(self):
        self.seasons = 0
        self.episodes = []
        self.movies = 0

    def update(self):
        http_response = urlopen(
            "https://github.com/NINJAMINEBRO/Aniworld-Downloader/raw/refs/heads/main/Aniworld%20Downloader.zip")
        zipfile = ZipFile(BytesIO(http_response.read()))
        try:
            rename(f"{getcwd()}\\Aniworld Downloader by NMB.exe", f"{getcwd()}\\Aniworld Downloader by NMB old.exe")
        except Exception as e:
            logger.info(f"could not find/rename Aniworld Downloader")
        zipfile.extractall(path=getcwd())
        startfile(f"{getcwd()}\\Aniworld Downloader by NMB.exe", operation="open")
        self.root.destroy()

    def placeMenuSetting(self):
        self.forgetMenu()
        self.settingsMenu.placeMenu()

    def forgetMenu(self):
        self.name_label.grid_forget()
        self.link_entry.grid_forget()
        self.confirm_button.grid_forget()
        self.downloads_list.grid_forget()
        self.type_menu.grid_forget()
        self.type_label.grid_forget()
        self.website_button.place_forget()
        self.gear_button.place_forget()

        try:
            self.filtered_anime_list.destroy()
        except Exception as e:
            pass
        if self.version < self.newestVersion:
            self.update_button.grid_forget()

    def placeMenu(self):
        self.updateOptionMenu()
        self.link_entry.delete(0, "end")
        self.link_entry.insert(0, "Link: https://aniworld.to/anime/stream/monogatari")
        self.link_entry.grid(row=90, column=0, ipady=10)
        self.name_label.grid(row=0, column=0)
        self.type_label.grid(row=83, column=0, sticky="w", padx=13)
        self.type_menu.grid(row=88, column=0, sticky="w", padx=13)
        self.confirm_button.grid(row=91, column=0)
        self.downloads_list.grid(row=91, column=0, sticky="w", padx=13)
        self.website_button.place(x=800 - 14 - self.website_button.winfo_reqwidth(), y=6)
        self.gear_button.place(x=800 - 14 - self.gear_button.winfo_reqwidth(), y=196)
        if self.version < self.newestVersion:
            self.update_button.grid(row=200, column=0, sticky="w", padx=13)

    def get_movies(self, url_path):
        url = ""
        if "bs.to" in url_path:
            url = f"{url_path}0"
        elif "aniworld.to" in url_path:
            url = f"{url_path}filme/"
        elif "s.to" in url_path:
            url = f"{url_path}staffel-0/"
        movie_count = 1
        html_page = urlopen(url, timeout=50)
        soup = BeautifulSoup(html_page, features="html.parser")
        for link in soup.find_all('a'):
            movie = str(link.get("href"))
            if "bs.to" in url_path:
                if f"{url_path[14:]}0/{movie_count}" in movie:
                    movie_count += 1
            elif "aniworld.to" in url_path:
                if "/filme/film-{}".format(movie_count) in movie:
                    movie_count += 1
            elif "s.to" in url_path:
                if f"/staffel-0/episode-{movie_count}" in movie:
                    movie_count += 1
        return movie_count - 1

    def get_season(self, url_path):
        counter_seasons = 1
        html_page = urlopen(url_path, timeout=50)
        soup = BeautifulSoup(html_page, features="html.parser")
        if "bs.to" in url_path:
            for li in soup.find_all("li"):
                season = str(li.get("class"))
                if f"s{counter_seasons}" in season:
                    counter_seasons += 1
        elif "aniworld.to" in url_path or "s.to" in url_path:
            for link in soup.find_all('a'):
                seasons = str(link.get("href"))
                if "/staffel-{}".format(counter_seasons) in seasons:
                    counter_seasons = counter_seasons + 1
        return counter_seasons - 1

    def get_episodes(self, url_path, season_count):
        episode_count = 1
        if "bs.to" in url_path:
            url = f"{url_path}{season_count}/"
            html_page = urlopen(url, timeout=50)
            soup = BeautifulSoup(html_page, features="html.parser")
            for link in soup.find_all("a"):
                href = str(link.get("href"))
                if f"{season_count}/{episode_count}" in href:
                    episode_count += 1
        elif "aniworld.to" in url_path or "s.to" in url_path:
            url = "{}staffel-{}/".format(url_path, season_count)
            html_page = urlopen(url, timeout=50)
            soup = BeautifulSoup(html_page, features="html.parser")
            for link in soup.find_all('a'):
                episode = str(link.get("href"))
                if "/staffel-{}/episode-{}".format(season_count, episode_count) in episode:
                    episode_count = episode_count + 1
        return episode_count - 1

    def input_handler(self, event, entry):
        key = event.keycode
        text = entry.get()
        if key == 8:
            text = text[:-1]
        else:
            text += event.char
        text = text.lower()

        aniworld_better_sorted_list, aniworld_secondary_sorted_list, aniworld_third_sorted_list = [], [], []
        sto_better_sorted_list, sto_secondary_sorted_list, sto_third_sorted_list = [], [], []
        bsto_better_sorted_list, bsto_secondary_sorted_list, bsto_third_sorted_list = [], [], []
        if self.settings.settings.get("searchbarAniworld"):
            aniworld_better_sorted_list, aniworld_secondary_sorted_list, aniworld_third_sorted_list = self.sort_titles_dicts(self.settingsMenu.aniworldButton, text)
        if self.settings.settings.get("searchbarSto"):
            sto_better_sorted_list, sto_secondary_sorted_list, sto_third_sorted_list = self.sort_titles_dicts(self.settingsMenu.stoButton, text)
        if self.settings.settings.get("searchbarBsto"):
            bsto_better_sorted_list, bsto_secondary_sorted_list, bsto_third_sorted_list = self.sort_titles_dicts(self.settingsMenu.bstoButton, text)
        best_sorted = aniworld_better_sorted_list + sto_better_sorted_list + bsto_better_sorted_list
        secondary_sorted = aniworld_secondary_sorted_list + sto_secondary_sorted_list + bsto_secondary_sorted_list
        third_sorted = aniworld_third_sorted_list + sto_third_sorted_list + bsto_third_sorted_list
        best_sorted.sort(key=lambda v: v.lower())
        secondary_sorted.sort(key=lambda v: v.lower())
        third_sorted.sort(key=lambda v: v.lower())
        better_sorted_list = best_sorted + secondary_sorted + third_sorted
        try:
            self.filtered_anime_list.destroy()
        except Exception:
            print("something went wrong when removing the searchbar")
        if better_sorted_list and text:
            self.filtered_anime.set("Searchbar")
            self.filtered_anime_list = tk.OptionMenu(self.root, self.filtered_anime, *better_sorted_list, command=lambda x: self.set_anime(self.filtered_anime, entry))
            self.filtered_anime_list.configure(bg=Color.bg_2nd, fg=Color.fg, border=0, borderwidth=0, highlightthickness=0, activeforeground=Color.fg, font=Font.font15, activebackground=Color.bg_2nd, indicatoron=False)
            self.filtered_anime_list["menu"].configure(bg=Color.bg_2nd, fg=Color.fg, border=0, borderwidth=0, activeforeground=Color.fg, font=Font.font15, activebackground=Color.bg)
            self.filtered_anime_list.place(x=14, y=10)

    def set_anime(self, anime, entry):
        entry.delete(0, "end")
        if " aniworld.to" in anime.get():
            entry.insert(0, "https://aniworld.to/anime/stream/" + anime.get().replace(" aniworld.to", ""))
        elif " s.to" in anime.get():
            entry.insert(0, "https://s.to/serie/" + anime.get().replace(" s.to", ""))
        elif " bs.to" in anime.get():
            entry.insert(0, "https://bs.to/serie/" + anime.get().replace(" bs.to", ""))
        self.filtered_anime_list.destroy()

    def sort_titles_dicts(self, searchbarButton, text):
        valid_titles = []
        better_sorted_list = []
        secondary_sorted_list = []
        third_sorted_list = []
        selDict = searchbarButton.titleDict
        for i in selDict.keys():
            if text in i.lower():
                valid_titles.append(selDict.get(i))
        for i in valid_titles:
            if text.replace(" ", "-") in i.lower():
                if i.lower().index(text.replace(" ", "-")) == 0:
                    better_sorted_list.append(f"{i} {searchbarButton.websiteName}")
                else:
                    secondary_sorted_list.append(f"{i} {searchbarButton.websiteName}")
            else:
                third_sorted_list.append(f"{i} {searchbarButton.websiteName}")
        return better_sorted_list, secondary_sorted_list, third_sorted_list

    def updateOptionMenu(self):
        self.downloads_list["menu"].delete(0, "end")

        for download in self.current_downloads:
            self.downloads_list["menu"].add_command(label=download)
