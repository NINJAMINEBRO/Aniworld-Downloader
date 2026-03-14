import tkinter as tk
from Colors import Colors as color


class Root:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Aniworld Downloader by NMB")
        self.root.configure(bg=color.bg)
        self.root.resizable(False, False)
        self.root.geometry("800x500")

        for i in range(201):
            self.root.rowconfigure(i, weight=1)
        self.root.columnconfigure(0, weight=1)

        self.root.bind("<Button-1>", lambda x: self.focus_out())  #needs to be lambda for some reason

    def focus_out(self):
        x, y = self.root.winfo_pointerxy()
        widget = self.root.winfo_containing(x, y)
        if ".!entry" not in str(widget):
            self.root.focus()
