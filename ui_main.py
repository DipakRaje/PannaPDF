# ui_main.py - Main GUI layout and tab loading

import tkinter as tk
from tkinter import ttk
from tabs.view_tab import ViewTab


def launch_app():
    root = tk.Tk()
    root.title("PannaPDF")
    root.geometry("1024x768")

    notebook = ttk.Notebook(root)
    notebook.pack(fill=tk.BOTH, expand=True)

    # Use tk.Frame so no ttk padding is applied (ttk.Frame adds padding that creates a gap).
    view_tab_frame = tk.Frame(notebook)
    ViewTab(view_tab_frame)
    notebook.add(view_tab_frame, text="View/Edit PDF")

    # Placeholder tabs for now
    ttk.Frame(notebook).pack()
    notebook.add(ttk.Frame(notebook), text="Split PDF")
    notebook.add(ttk.Frame(notebook), text="Merge PDFs")
    notebook.add(ttk.Frame(notebook), text="Compress PDF")

    root.mainloop()
