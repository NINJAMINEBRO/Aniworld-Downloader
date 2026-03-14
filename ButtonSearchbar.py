from Colors import Colors as Color
from Fonts import Fonts as Font
from urllib.request import urlopen
from bs4 import BeautifulSoup
import tkinter as tk
import logger


class ButtonSearchbar:
    def __init__(self, link, root, settings):
        self.root = root
        self.settings = settings
        self.titleDict = {}
        self.searchLink = link
        self.websiteName = link[link.index("//") + 2:]
        self.websiteName = self.websiteName[:self.websiteName.index("/")]

        self.isOn = False
        if "bs.to" == self.websiteName:
            self.isOn = self.settings.settings.get("searchbarBsto")
        elif "s.to" == self.websiteName:
            self.isOn = self.settings.settings.get("searchbarSto")
        elif "aniworld.to" == self.websiteName:
            self.isOn = self.settings.settings.get("searchbarAniworld")

        self.button = tk.Button(self.root, text=self.websiteName, font=Font.font15,
                                fg=Color.bg if self.isOn else Color.fg, bg=Color.bg_2nd, width=10,
                                bd=False, height=1, command=self.toggle)

        if self.isOn:
            self.titleDict = self.getTitles()

    def toggle(self):
        if self.isOn:
            self.button["fg"] = Color.fg
        else:
            self.button["fg"] = Color.bg
            if not self.titleDict:
                self.titleDict = self.getTitles()
        self.isOn = not self.isOn

        if "bs.to" == self.websiteName:
            self.settings.settings.update({"searchbarBsto": int(self.isOn)})
        elif "s.to" == self.websiteName:
            self.settings.settings.update({"searchbarSto": int(self.isOn)})
        elif "aniworld.to" == self.websiteName:
            self.settings.settings.update({"searchbarAniworld": int(self.isOn)})

        self.settings.updateSettings("w")

    def getTitles(self):
        try:
            html_response = urlopen(self.searchLink)
            soup = BeautifulSoup(html_response, "html.parser")
            title_link_dict = {}
            index_list = []
            if self.websiteName in ["bs.to"]:
                matching_li_elements = str(soup.find_all("ul")).split("</a></li>\n<li><a ")
                del matching_li_elements[:31]
                matching_li_elements[0] = matching_li_elements[0][91:]
                del matching_li_elements[-4:]
                matching_li_elements[-1] = matching_li_elements[-1][:87]
                for i in matching_li_elements:
                    title_link_dict.update({i[i.index('title=') + 7:]: i[i.index('href="') + 12: i.index('" title')]})
            elif self.websiteName in ["aniworld.to"]:
                matching_li_elements = str(soup.find_all("li")).split("</a></li>, <li><a ")
                for i in matching_li_elements:
                    if "data-alternative-title" not in i:
                        index_list.append(matching_li_elements.index(i))
                index_list = sorted(index_list, reverse=True)
                for i in index_list:
                    matching_li_elements.pop(i)
                for i in range(len(matching_li_elements)):
                    matching_li_elements[i] = matching_li_elements[i][24:]
                for i in matching_li_elements:
                    title_link_dict.update({i[i.index('" title') + 9:i.index(" Stream anschauen")] + "," + i[:i.index(
                        '"')]: i[i.index('href="') + 20: i.index('" title')]})
            elif self.websiteName in ["s.to"]:
                matching_li_elements = str(soup.find_all("li")).split("</a></li>, <li><a ")
                matching_li_elements = matching_li_elements[5].split("series-item\" data-search=\"")

                for i in matching_li_elements:
                    if "/serie/" not in i:
                        index_list.append(matching_li_elements.index(i))
                index_list = sorted(index_list, reverse=True)
                for i in index_list:
                    matching_li_elements.pop(i)

                for i in range(len(matching_li_elements)):
                    matching_li_elements[i] = matching_li_elements[i][matching_li_elements[i].index("<a href=\"/serie/")+16:matching_li_elements[i].index("</a>")]

                for i in matching_li_elements:
                    title_link_dict.update({i[i.index(">")+1:]: i[:i.index("\">")]})
            return title_link_dict
        except Exception as e:
            if "urlopen error" in str(e):
                logger.error(f"Disabled {self.searchLink[8:self.searchLink.index('.to') + 3]} Searchbar")
            return {}
