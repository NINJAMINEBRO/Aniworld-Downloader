from urllib.request import urlopen
from os import listdir, getcwd, remove
from MenuMain import MenuMain
from MenuSettings import MenuSettings
from Settings import Settings
from MenuConfigureDownload import MenuConfigureDownload
from AniworldDownloader import Download
from Root import Root
import logger


def checkForUpdate():  # get latest version
    connection = True
    newest = 0
    try:
        file = urlopen("https://raw.githubusercontent.com/NINJAMINEBRO/Aniworld-Downloader/main/version")
        lines = ""
        for line in file:
            lines += line.decode("utf-8")
        newest = float(lines[:-1])
    except Exception as e:
        connection = False
        if "urlopen error" in str(e):
            logger.error(f"No Network connection")
    if version < newest:
        logger.info(f"Update available\n"
                    f"current version: {version}\n"
                    f"newest version: {newest}\n"
                    f"Download latest version on: https://ninjaminebro.itch.io/aniworld-downloader\n")
    return connection, newest


def checkForOldFilesAndVerifyFfmpeg():
    if "ffmpeg.exe" not in listdir(getcwd()):
        logger.error(f"WARNING: ffmpeg is not installed or not in this folder\n"
                     f"This program will not work unless ffmpeg is in the same folder as this program")
    if "Aniworld Downloader by NMB old.exe" in listdir(getcwd()):
        try:
            remove(f"{getcwd()}\\Aniworld Downloader by NMB old.exe")
        except Exception as e:
            logger.warning(f"could not remove old version\n{e}")


if __name__ == "__main__":
    version = 1.50
    checkForOldFilesAndVerifyFfmpeg()
    network, newestVersion = checkForUpdate()
    root = Root()
    settings = Settings()

    mainMenu = MenuMain(root.root, network, version, newestVersion, None, settings,
                        None)  #None 1 = settingsMenu None 2 = configMenu

    settingsMenu = MenuSettings(mainMenu)
    mainMenu.settingsMenu = settingsMenu  #set missing reference to settingMenu

    configMenu = MenuConfigureDownload(mainMenu, None)  # None = downloadLogic
    mainMenu.configureMenu = configMenu  # set missing reference to configMenu

    downloaderLogic = Download(configMenu)
    configMenu.downloadLogic = downloaderLogic  # set missing reference to downloadLogic

    mainMenu.placeMenu()

    root.root.mainloop()
