import sys
from os import path, getcwd
from colorama import Style, Fore
import logger


class Settings:
    settings = {"searchbarAniworld": 1,
                "searchbarSto": 0,
                "searchbarBsto": 0,
                "shutdown": 0,
                "limitDownload": 10,
                "pathDownload": getcwd(),
                }
    provider_priority = ["VOE", "Vidmoly", "SpeedFiles", "Vidoza", "Doodstream", "Streamtape"]
    languages = ["Ger-Sub", "German", "Eng-Sub", "English"]

    def __init__(self):
        try:
            with open(self.resource_path("aniworld settings.txt"), "r") as s:
                text = s.read()
                text = text.split("\n")
                text.pop(0)  # remove info text
                for i in text:
                    key = i[:i.index(":")]
                    value = i[i.index(":")+2:]  # +2 to skip : and empty space
                    if key == "pathDownload":
                        self.settings.update({key: str(value)})
                    else:
                        self.settings.update({key: int(value)})

                if self.settings.get("pathDownload") == "" or not path.exists(self.settings.get("pathDownload")):  # standard is empty string which is not a valid path and catch not existent
                    self.settings.update({"pathDownload": getcwd()})
                    logger.warning("The saved path does not exist -> automatically changed Download path to program path")
        except Exception as e:
            print(f"There was an error reading the settings file\n{str(e)}")

    def resource_path(self, relative_path):
        """ Get absolute path to resource, works for dev and for PyInstaller """
        try:
            # PyInstaller creates a temp folder and stores path in _MEIPASS
            base_path = sys._MEIPASS
        except Exception:
            base_path = path.abspath(".")
        return path.join(base_path, relative_path)

    def updateSettings(self):
        try:
            with open(self.resource_path("aniworld settings.txt"), "w") as s:
                s.write(f"Searchbars have high impact on startup time!\n")
                s.write(f"searchbarAniworld: {self.settings.get('searchbarAniworld')}\n")
                s.write(f"searchbarSto: {self.settings.get('searchbarSto')}\n")
                s.write(f"searchbarBsto: {self.settings.get('searchbarBsto')}\n")
                s.write(f"limitDownload: {self.settings.get('limitDownload')}\n")
                s.write(f"pathDownload: {self.settings.get('pathDownload')}")
        except Exception as e:
            print(f"{Fore.RED}Error while updating settings file: {e}{Style.RESET_ALL}")
