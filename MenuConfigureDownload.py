import tkinter as tk
from Colors import Colors as Color
from Fonts import Fonts as Font


class MenuConfigureDownload:
    def __init__(self, menuMain, downloadLogic):
        self.settings = menuMain.settings
        self.provider_prio = self.settings.provider_priority.copy()
        self.language_prio = self.settings.languages
        self.menuMain = menuMain
        self.downloadLogic = downloadLogic
        self.seasons = menuMain.seasons
        self.episodes = menuMain.episodes.copy()
        self.movies = menuMain.movies
        self.url = None  # gets set in placeMenu
        self.root = menuMain.root
        self.series_name_label = tk.Label(self.root, text="placeholder", font=Font.font30, fg=Color.bg_2nd,
                                          bg=Color.bg)
        self.season_start = tk.StringVar()
        self.season_end = tk.StringVar()
        self.episode_start = tk.StringVar()
        self.episode_end = tk.StringVar()
        self.movie_start = tk.StringVar()
        self.movie_end = tk.StringVar()
        self.start_label = tk.Label(self.root, text="Start from", font=Font.font15, fg=Color.bg_2nd, bg=Color.bg,
                                    width=11)
        self.end_label = tk.Label(self.root, text="End at", font=Font.font15, fg=Color.bg_2nd, bg=Color.bg,
                                  width=11)
        self.provider_label = tk.Label(self.root, text="Provider", font=Font.font15, fg=Color.bg_2nd, bg=Color.bg,
                                       width=15)
        self.providerv = tk.StringVar()
        self.provider_menu = tk.OptionMenu(self.root, self.providerv, *self.provider_prio)
        self.provider_menu.configure(bg=Color.bg_2nd, fg=Color.fg, border=0, borderwidth=0, highlightthickness=0,
                                     activeforeground=Color.fg, font=Font.font15, activebackground=Color.bg_2nd,
                                     indicatoron=False, width=15)
        self.provider_menu["menu"].configure(bg=Color.bg_2nd, fg=Color.fg, activeforeground=Color.fg,
                                             font=Font.font15, activebackground=Color.bg)
        self.options_label = tk.Label(self.root, text="Options", font=Font.font15, fg=Color.bg_2nd, bg=Color.bg,
                                      width=10)
        self.shutdown_button = tk.Button(self.root, text="Shutdown", font=Font.font15, fg=Color.fg,
                                         bg=Color.bg_2nd, width=10, bd=False, height=1,
                                         command=lambda: self.shutdown_setting())
        self.language_label = tk.Label(self.root, text="Language\npriority", font=Font.font15, fg=Color.bg_2nd,
                                       bg=Color.bg, width=12, bd=False, height=2)
        self.return_button = tk.Button(self.root, text="←", font=Font.font25, fg=Color.bg_2nd, bg=Color.bg,
                                       width=3, bd=False, height=1, command=lambda: self.return_menu())
        self.language_prio_1 = tk.StringVar()
        self.language_prio_2 = tk.StringVar()
        self.language_prio_3 = tk.StringVar()
        self.language_prio_4 = tk.StringVar()
        self.language_menu_1 = tk.OptionMenu(self.root, self.language_prio_1, *self.language_prio,
                                             command=lambda x: self.language_prio_set(1))
        self.language_menu_2 = tk.OptionMenu(self.root, self.language_prio_2, *self.language_prio,
                                             command=lambda x: self.language_prio_set(2))
        self.language_menu_3 = tk.OptionMenu(self.root, self.language_prio_3, *self.language_prio,
                                             command=lambda x: self.language_prio_set(3))
        self.language_menu_4 = tk.OptionMenu(self.root, self.language_prio_4, *self.language_prio,
                                             command=lambda x: self.language_prio_set(4))
        self.language_menu_1.configure(bg=Color.bg_2nd, fg=Color.fg, border=0, borderwidth=0, highlightthickness=0,
                                       activeforeground=Color.fg, font=Font.font15, activebackground=Color.bg_2nd,
                                       indicatoron=False, width=12)
        self.language_menu_2.configure(bg=Color.bg_2nd, fg=Color.fg, border=0, borderwidth=0, highlightthickness=0,
                                       activeforeground=Color.fg, font=Font.font15, activebackground=Color.bg_2nd,
                                       indicatoron=False, width=12)
        self.language_menu_3.configure(bg=Color.bg_2nd, fg=Color.fg, border=0, borderwidth=0, highlightthickness=0,
                                       activeforeground=Color.fg, font=Font.font15, activebackground=Color.bg_2nd,
                                       indicatoron=False, width=12)
        self.language_menu_4.configure(bg=Color.bg_2nd, fg=Color.fg, border=0, borderwidth=0, highlightthickness=0,
                                       activeforeground=Color.fg, font=Font.font15, activebackground=Color.bg_2nd,
                                       indicatoron=False, width=12)
        self.language_menu_1["menu"].configure(bg=Color.bg_2nd, fg=Color.fg, activeforeground=Color.fg,
                                               font=Font.font15, activebackground=Color.bg)
        self.language_menu_2["menu"].configure(bg=Color.bg_2nd, fg=Color.fg, activeforeground=Color.fg,
                                               font=Font.font15, activebackground=Color.bg)
        self.language_menu_3["menu"].configure(bg=Color.bg_2nd, fg=Color.fg, activeforeground=Color.fg,
                                               font=Font.font15, activebackground=Color.bg)
        self.language_menu_4["menu"].configure(bg=Color.bg_2nd, fg=Color.fg, activeforeground=Color.fg,
                                               font=Font.font15, activebackground=Color.bg)
        self.create_thread_button = tk.Button(self.root, text="Start", font=Font.font15, fg=Color.fg,
                                              bg=Color.bg_2nd, width=17, bd=False, height=1,
                                              command=lambda: self.downloadLogic.createDownloadThread(self.url))

        self.season_start_menu = tk.OptionMenu(self.root, tk.StringVar(), "Temp")
        self.season_end_menu = tk.OptionMenu(self.root, tk.StringVar(), "Temp")
        self.episode_start_menu = tk.OptionMenu(self.root, tk.StringVar(), "Temp")
        self.episode_end_menu = tk.OptionMenu(self.root, tk.StringVar(), "Temp")
        self.movie_start_menu = tk.OptionMenu(self.root, tk.StringVar(), "Temp")
        self.movie_end_menu = tk.OptionMenu(self.root, tk.StringVar(), "Temp")

    def forgetMenu(self, typ):
        if typ == "Episodes":
            self.season_start_menu.destroy()
            self.season_end_menu.destroy()
            self.episode_start_menu.destroy()
            self.episode_end_menu.destroy()
        elif typ == "Movies":
            self.movie_start_menu.destroy()
            self.movie_end_menu.destroy()
        self.shutdown_button.grid_forget()
        self.create_thread_button.grid_forget()
        self.provider_menu.grid_forget()
        self.series_name_label.grid_forget()
        self.start_label.grid_forget()
        self.end_label.grid_forget()
        self.provider_label.grid_forget()
        self.options_label.grid_forget()
        self.language_menu_1.grid_forget()
        self.language_menu_2.grid_forget()
        self.language_menu_3.grid_forget()
        self.language_menu_4.grid_forget()
        self.language_label.grid_forget()

    def placeMenu(self, url):
        self.series_name_label.config(text=self.getTitle(url))
        self.series_name_label.grid(row=0, column=0)

        self.language_prio = self.settings.languages
        self.seasons = self.menuMain.seasons
        self.episodes = self.menuMain.episodes.copy()
        self.movies = self.menuMain.movies
        self.url = url

        if self.seasons != 0:
            seasonsv = ["Season: " + str(i + 1) for i in range(self.seasons)]
            episodesv = ["Episode: " + str(i + 1) for i in range(self.episodes[0])]
            self.season_start.set(seasonsv[0])
            self.season_end.set(seasonsv[0])
            self.episode_start.set(episodesv[0])
            self.episode_end.set(episodesv[-1])

            self.season_start_menu = tk.OptionMenu(self.root, self.season_start, *seasonsv,
                                                   command=lambda x: self.from_season())
            self.season_start_menu.configure(bg=Color.bg_2nd, fg=Color.fg, border=0, borderwidth=0,
                                             highlightthickness=0,
                                             activeforeground=Color.fg, font=Font.font15,
                                             activebackground=Color.bg_2nd, indicatoron=False, width=11)
            self.season_start_menu["menu"].configure(bg=Color.bg_2nd, fg=Color.fg, activeforeground=Color.fg,
                                                     font=Font.font15, activebackground=Color.bg)
            self.season_end_menu = tk.OptionMenu(self.root, self.season_end, *seasonsv,
                                                 command=lambda x: self.to_season())
            self.season_end_menu.configure(bg=Color.bg_2nd, fg=Color.fg, border=0, borderwidth=0, highlightthickness=0,
                                           activeforeground=Color.fg, font=Font.font15,
                                           activebackground=Color.bg_2nd,
                                           indicatoron=False, width=11)
            self.season_end_menu["menu"].configure(bg=Color.bg_2nd, fg=Color.fg, activeforeground=Color.fg,
                                                   font=Font.font15, activebackground=Color.bg)
            self.episode_start_menu = tk.OptionMenu(self.root, self.episode_start, *episodesv,
                                                    command=lambda x: self.from_episode())
            self.episode_start_menu.configure(bg=Color.bg_2nd, fg=Color.fg, border=0, borderwidth=0,
                                              highlightthickness=0,
                                              activeforeground=Color.fg, font=Font.font15,
                                              activebackground=Color.bg_2nd, indicatoron=False, width=11)
            self.episode_start_menu["menu"].configure(bg=Color.bg_2nd, fg=Color.fg, activeforeground=Color.fg,
                                                      font=Font.font15, activebackground=Color.bg)
            self.episode_end_menu = tk.OptionMenu(self.root, self.episode_end, *episodesv,
                                                  command=lambda x: self.to_episode())
            self.episode_end_menu.configure(bg=Color.bg_2nd, fg=Color.fg, border=0, borderwidth=0, highlightthickness=0,
                                            activeforeground=Color.fg, font=Font.font15,
                                            activebackground=Color.bg_2nd,
                                            indicatoron=False, width=11)
            self.episode_end_menu["menu"].configure(bg=Color.bg_2nd, fg=Color.fg, activeforeground=Color.fg,
                                                    font=Font.font15, activebackground=Color.bg)
            self.season_start_menu.grid(row=30, column=0, sticky="w", padx=30)
            self.season_end_menu.grid(row=30, column=0, sticky="w", padx=187)
            self.episode_start_menu.grid(row=35, column=0, sticky="w", padx=30)
            self.episode_end_menu.grid(row=35, column=0, sticky="w", padx=187)

        elif self.movies != 0:
            moviesv = ["Movie: " + str(i + 1) for i in range(self.movies)]
            self.movie_start.set(moviesv[0])
            self.movie_end.set(moviesv[-1])

            self.movie_start_menu = tk.OptionMenu(self.root, self.movie_start, *moviesv,
                                                  command=lambda x: self.from_movie())
            self.movie_start_menu.configure(bg=Color.bg_2nd, fg=Color.fg, border=0, borderwidth=0, highlightthickness=0,
                                            activeforeground=Color.fg, font=Font.font15,
                                            activebackground=Color.bg_2nd,
                                            indicatoron=False, width=11)
            self.movie_start_menu["menu"].configure(bg=Color.bg_2nd, fg=Color.fg, activeforeground=Color.fg,
                                                    font=Font.font15, activebackground=Color.bg)
            self.movie_end_menu = tk.OptionMenu(self.root, self.movie_end, *moviesv, command=lambda x: self.to_movie())
            self.movie_end_menu.configure(bg=Color.bg_2nd, fg=Color.fg, border=0, borderwidth=0, highlightthickness=0,
                                          activeforeground=Color.fg, font=Font.font15,
                                          activebackground=Color.bg_2nd,
                                          indicatoron=False, width=11)
            self.movie_end_menu["menu"].configure(bg=Color.bg_2nd, fg=Color.fg, activeforeground=Color.fg,
                                                  font=Font.font15, activebackground=Color.bg)
            self.movie_start_menu.grid(row=30, column=0, sticky="w", padx=30)
            self.movie_end_menu.grid(row=30, column=0, sticky="w", padx=187)

        self.start_label.grid(row=25, column=0, sticky="w", padx=30, ipadx=2)
        self.end_label.grid(row=25, column=0, sticky="w", padx=60 + 127, ipadx=2)
        self.provider_label.grid(row=25, column=0, sticky="w", padx=217 + self.end_label.winfo_reqwidth())

        self.providerv.set(self.settings.provider_priority[0])
        self.provider_menu.grid(row=30, column=0, sticky="w", padx=217 + self.end_label.winfo_reqwidth())
        self.options_label.grid(row=25, column=0, sticky="e", padx=200)
        if self.settings.settings.get("shutdown"):
            self.shutdown_button["fg"] = Color.bg
        else:
            self.shutdown_button["fg"] = Color.fg
        self.shutdown_button.grid(row=30, column=0, sticky="e", padx=200)
        self.language_label.grid(row=20, column=0, sticky="e", padx=30, rowspan=6)
        self.return_button.grid(row=0, column=0, sticky="w")

        self.language_prio_1.set(self.language_prio[0])
        self.language_prio_2.set(self.language_prio[1])
        self.language_prio_3.set(self.language_prio[2])
        self.language_prio_4.set(self.language_prio[3])
        self.language_menu_1.grid(row=30, column=0, sticky="e", padx=30)
        self.language_menu_2.grid(row=35, column=0, sticky="e", padx=30)
        self.language_menu_3.grid(row=41, column=0, sticky="e", padx=30)
        self.language_menu_4.grid(row=47, column=0, sticky="e", padx=30)

        self.create_thread_button.grid(row=150, column=0)

    def return_menu(self):
        self.return_button.grid_forget()
        self.forgetMenu("Episodes" if self.seasons > 0 else "Movies")
        self.menuMain.placeMenu()

    def shutdown_setting(self):
        if self.settings.settings.get("shutdown"):
            self.shutdown_button["fg"] = Color.fg
        else:
            self.shutdown_button["fg"] = Color.bg
        self.settings.settings.update({"shutdown": int(not self.settings.settings.get("shutdown"))})

    def language_prio_set(self, set_b):
        lang_1 = self.language_prio_1.get()
        lang_2 = self.language_prio_2.get()
        lang_3 = self.language_prio_3.get()
        lang_4 = self.language_prio_4.get()
        languages_prios = [self.language_prio_1, self.language_prio_2, self.language_prio_3, self.language_prio_4]

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

        self.settings.languages = [self.language_prio_1.get(), self.language_prio_2.get(),
                                   self.language_prio_3.get(), self.language_prio_4.get()]

    def from_season(self):
        from_season = int(self.season_start.get()[8:])
        to_season = int(self.season_end.get()[8:])
        if from_season > to_season:
            to_season = from_season
            self.season_end.set("Season: " + str(to_season))

        self.episode_start_menu.destroy()
        self.episode_start_menu = tk.OptionMenu(self.root, self.episode_start,
                                                *["Episode: " + str(x + 1) for x in
                                                  range(self.episodes[from_season - 1])],
                                                command=lambda x: self.from_episode())
        self.episode_start_menu.configure(bg=Color.bg_2nd, fg=Color.fg, border=0, borderwidth=0, highlightthickness=0,
                                          activeforeground=Color.fg, font=Font.font15, activebackground=Color.bg_2nd,
                                          indicatoron=False, width=11)
        self.episode_start_menu["menu"].configure(bg=Color.bg_2nd, fg=Color.fg, activeforeground=Color.fg,
                                                  font=Font.font15, activebackground=Color.bg)
        self.episode_start_menu.grid(row=35, column=0, sticky="w", padx=30)
        episode_range = [x + 1 for x in range(self.episodes[from_season - 1])]
        from_episodev = int(self.episode_start.get()[9:])
        if from_episodev not in episode_range:
            from_episodev = "Episode: " + str(episode_range[-1])
            self.episode_start.set(from_episodev)

        self.episode_end_menu.destroy()
        self.episode_end_menu = tk.OptionMenu(self.root, self.episode_end,
                                              *["Episode: " + str(x + 1) for x in range(self.episodes[to_season - 1])],
                                              command=lambda x: self.to_episode())
        self.episode_end_menu.configure(bg=Color.bg_2nd, fg=Color.fg, border=0, borderwidth=0, highlightthickness=0,
                                        activeforeground=Color.fg, font=Font.font15, activebackground=Color.bg_2nd,
                                        indicatoron=False, width=11)
        self.episode_end_menu["menu"].configure(bg=Color.bg_2nd, fg=Color.fg, activeforeground=Color.fg,
                                                font=Font.font15, activebackground=Color.bg)
        self.episode_end_menu.grid(row=35, column=0, sticky="w", padx=60 + 127)
        episode_range = [x + 1 for x in range(self.episodes[to_season - 1])]
        to_episodev = int(self.episode_end.get()[9:])
        if to_episodev not in episode_range:
            to_episodev = "Episode: " + str(episode_range[-1])
            self.episode_end.set(to_episodev)
        self.from_episode()

    def to_season(self):
        from_season = int(self.season_start.get()[8:])
        to_season = int(self.season_end.get()[8:])
        if from_season > to_season:
            from_season = to_season
            self.season_start.set("Season: " + str(from_season))

        self.episode_end_menu.destroy()
        self.episode_end_menu = tk.OptionMenu(self.root, self.episode_end,
                                              *["Episode: " + str(x + 1) for x in range(self.episodes[to_season - 1])],
                                              command=lambda x: self.to_episode())
        self.episode_end_menu.configure(bg=Color.bg_2nd, fg=Color.fg, border=0, borderwidth=0, highlightthickness=0,
                                        activeforeground=Color.fg, font=Font.font15, activebackground=Color.bg_2nd,
                                        indicatoron=False, width=11)
        self.episode_end_menu["menu"].configure(bg=Color.bg_2nd, fg=Color.fg, activeforeground=Color.fg,
                                                font=Font.font15, activebackground=Color.bg)
        self.episode_end_menu.grid(row=35, column=0, sticky="w", padx=60 + 127)
        episode_range = [x + 1 for x in range(self.episodes[to_season - 1])]
        to_episodev = int(self.episode_end.get()[9:])
        if to_episodev not in episode_range:
            to_episodev = "Episode: " + str(episode_range[-1])
            self.episode_end.set(to_episodev)

        self.episode_start_menu.destroy()
        self.episode_start_menu = tk.OptionMenu(self.root, self.episode_start,
                                                *["Episode: " + str(x + 1) for x in
                                                  range(self.episodes[from_season - 1])],
                                                command=lambda x: self.from_episode())
        self.episode_start_menu.configure(bg=Color.bg_2nd, fg=Color.fg, border=0, borderwidth=0, highlightthickness=0,
                                          activeforeground=Color.fg, font=Font.font15, activebackground=Color.bg_2nd,
                                          indicatoron=False, width=11)
        self.episode_start_menu["menu"].configure(bg=Color.bg_2nd, fg=Color.fg, activeforeground=Color.fg,
                                                  font=Font.font15, activebackground=Color.bg)
        self.episode_start_menu.grid(row=35, column=0, sticky="w", padx=30)
        episode_range = [x + 1 for x in range(self.episodes[from_season - 1])]
        from_episodev = int(self.episode_start.get()[9:])
        if from_episodev not in episode_range:
            from_episodev = "Episode: " + str(episode_range[-1])
            self.episode_start.set(from_episodev)
        self.to_episode()

    def from_episode(self):
        from_seasonv = self.season_start.get()[8:]
        to_seasonv = self.season_end.get()[8:]
        from_episodev = int(self.episode_start.get()[9:])
        to_episodev = int(self.episode_end.get()[9:])
        if from_seasonv == to_seasonv and from_episodev > to_episodev:
            to_episodev = from_episodev
            self.episode_end.set("Episode: " + str(to_episodev))

    def to_episode(self):
        from_seasonv = self.season_start.get()[8:]
        to_seasonv = self.season_end.get()[8:]
        from_episodev = int(self.episode_start.get()[9:])
        to_episodev = int(self.episode_end.get()[9:])
        if from_seasonv == to_seasonv and from_episodev > to_episodev:
            from_episodev = to_episodev
            self.episode_start.set("Episode: " + str(from_episodev))

    def from_movie(self):
        from_moviev = int(self.movie_start.get()[7:])
        to_moviev = int(self.movie_end.get()[7:])
        if from_moviev > to_moviev:
            to_moviev = from_moviev
            self.movie_end.set("Movie: " + str(to_moviev))

    def to_movie(self):
        from_moviev = int(self.movie_start.get()[7:])
        to_moviev = int(self.movie_end.get()[7:])
        if from_moviev > to_moviev:
            from_moviev = to_moviev
            self.movie_start.set("Movie: " + str(from_moviev))

    def getTitle(self, link):
        title = ""
        hostWebsite = self.getHostWebsite(link)
        if hostWebsite in ["bs.to", "s.to"]:
            title = link[link.index("serie/") + 6:-1]
        elif hostWebsite in ["aniworld.to"]:
            title = link[link.index("stream/") + 7:-1].replace("-", " ").upper()
        return title

    def getHostWebsite(self, link):
        subLink = link[8:]  #remove https://
        return subLink[:subLink.index("/")]
