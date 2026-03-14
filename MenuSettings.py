import logger
from Colors import Colors as Color
from Fonts import Fonts as Font
import tkinter as tk
from tkinter import filedialog
from ButtonSearchbar import ButtonSearchbar


class MenuSettings:
    def __init__(self, menuMain):
        self.menuMain = menuMain
        self.settings = menuMain.settings
        self.root = menuMain.root
        self.searchbar_label = tk.Label(self.root, text="Searchbars:", font=Font.font15, fg=Color.bg_2nd,
                                        bg=Color.bg)

        self.aniworldButton = ButtonSearchbar("https://aniworld.to/animes", self.root, self.settings)
        self.stoButton = ButtonSearchbar("https://s.to/serien", self.root, self.settings)
        self.bstoButton = ButtonSearchbar("https://bs.to/andere-serien", self.root, self.settings)

        self.setDownloadPathButton = tk.Button(self.root, text="set", font=Font.font15,
                                               fg=Color.fg, bg=Color.bg_2nd, width=3, bd=False, height=1,
                                               command=lambda: self.OpenFiledialogAndSetDownloadPath())
        self.downloadPathLabel = tk.Label(self.root, text=self.settings.settings.get("pathDownload"), font=Font.font15,
                                          fg=Color.fg, bg=Color.bg)
        self.pathLabel = tk.Label(self.root, text="Download Folder:", font=Font.font15, fg=Color.bg_2nd, bg=Color.bg)

        self.downloadLimitLabel = tk.Label(self.root, text=self.settings.settings.get("limitDownload"),
                                           font=Font.font15, fg=Color.fg, bg=Color.bg)
        self.increaseLimitButton = tk.Button(self.root, text="+", font=Font.font15,
                                             fg=Color.fg, bg=Color.bg_2nd, width=2, bd=False, height=1,
                                             command=lambda: self.ChangeLimit(1))
        self.decreaseLimitButton = tk.Button(self.root, text="-", font=Font.font15,
                                             fg=Color.fg, bg=Color.bg_2nd, width=2, bd=False, height=1,
                                             command=lambda: self.ChangeLimit(-1))
        self.LimitLabel = tk.Label(self.root, text="simultaneous downloads:", font=Font.font15, fg=Color.bg_2nd, bg=Color.bg)

        self.return_button = tk.Button(self.root, text="←", font=Font.font25, fg=Color.bg_2nd, bg=Color.bg, width=3,
                                       bd=False, height=1, command=lambda: self.returnMenu())

    def placeMenu(self):
        self.return_button.grid(row=0, column=0, sticky="w")
        self.searchbar_label.grid(row=1, column=0, sticky="w", padx=30)

        self.aniworldButton.button.grid(row=2, column=0, sticky="w", padx=30)
        self.stoButton.button.grid(row=3, column=0, sticky="w", padx=30)
        self.bstoButton.button.grid(row=4, column=0, sticky="w", padx=30)

        self.pathLabel.grid(row=1, column=0, sticky="w", padx=40 + self.aniworldButton.button.winfo_reqwidth())
        self.setDownloadPathButton.grid(row=2, column=0, sticky="w", padx=40 + self.stoButton.button.winfo_reqwidth())
        self.downloadPathLabel.grid(row=2, column=0, sticky="w",
                                    padx=45 + self.stoButton.button.winfo_reqwidth() + self.setDownloadPathButton.winfo_reqwidth())

        self.LimitLabel.grid(row=5, column=0, sticky="w", padx=30)
        self.decreaseLimitButton.grid(row=6, column=0, sticky="w", padx=30)
        self.downloadLimitLabel.grid(row=6, column=0, sticky="w", padx=30 + self.decreaseLimitButton.winfo_reqwidth())
        self.increaseLimitButton.grid(row=6, column=0, sticky="w",
                                      padx=30 + self.decreaseLimitButton.winfo_reqwidth() + self.downloadLimitLabel.winfo_reqwidth())

    def forgetMenu(self):
        self.searchbar_label.grid_forget()
        self.aniworldButton.button.grid_forget()
        self.stoButton.button.grid_forget()
        self.bstoButton.button.grid_forget()
        self.return_button.grid_forget()
        self.setDownloadPathButton.grid_forget()
        self.pathLabel.grid_forget()
        self.setDownloadPathButton.grid_forget()
        self.downloadPathLabel.grid_forget()
        self.LimitLabel.grid_forget()
        self.decreaseLimitButton.grid_forget()
        self.downloadLimitLabel.grid_forget()
        self.increaseLimitButton.grid_forget()

    def returnMenu(self):
        self.forgetMenu()
        self.menuMain.placeMenu()

    def OpenFiledialogAndSetDownloadPath(self):
        if len(self.menuMain.current_downloads) >= 2:
            logger.warning("Changing the Download Path while downloading is not allowed")
        else:
            filePath = filedialog.askdirectory()
            if filePath:
                self.settings.settings.update({"pathDownload": filePath})
                self.settings.updateSettings("w")
                self.downloadPathLabel.configure(text=self.settings.settings.get("pathDownload"))

    def ChangeLimit(self, amount):
        if (self.settings.settings.get("limitDownload") + amount <= 20 and amount > 0 or
                self.settings.settings.get("limitDownload") + amount >= 1 and amount < 0):
            self.settings.settings.update({"limitDownload": self.settings.settings.get("limitDownload") + amount})
            self.settings.updateSettings("w")
            self.downloadLimitLabel.configure(text=self.settings.settings.get("limitDownload"))
            self.increaseLimitButton.grid_forget()
            self.increaseLimitButton.grid(row=6, column=0, sticky="w",
                                          padx=30 + self.decreaseLimitButton.winfo_reqwidth() + self.downloadLimitLabel.winfo_reqwidth())
