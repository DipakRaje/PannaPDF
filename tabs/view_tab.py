# tabs/view_tab.py - View/Edit Tab UI

import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
from pdf_utils.viewer import PDFViewer

class ViewTab:
    def __init__(self, parent):
        self.parent = parent
        self.pdf_viewer = PDFViewer()

        self.toolbar = tk.Frame(parent)
        self.toolbar.pack(side=tk.TOP, fill=tk.X)

        self.open_btn = tk.Button(self.toolbar, text="Open PDF", command=self.open_pdf)
        self.open_btn.pack(side=tk.LEFT)

        self.delete_btn = tk.Button(self.toolbar, text="Delete Page", command=self.pdf_viewer.delete_page)
        self.delete_btn.pack(side=tk.LEFT)

        self.undo_btn = tk.Button(self.toolbar, text="Undo (Ctrl+Z)", command=self.pdf_viewer.undo_delete)
        self.undo_btn.pack(side=tk.LEFT)

        self.zoom_in_btn = tk.Button(self.toolbar, text="Zoom In", command=self.pdf_viewer.zoom_in)
        self.zoom_in_btn.pack(side=tk.LEFT)

        self.zoom_out_btn = tk.Button(self.toolbar, text="Zoom Out", command=self.pdf_viewer.zoom_out)
        self.zoom_out_btn.pack(side=tk.LEFT)

        self.toggle_thumb_btn = tk.Button(self.toolbar, text="Toggle Thumbnails", command=self.pdf_viewer.toggle_thumbnails)
        self.toggle_thumb_btn.pack(side=tk.LEFT)

        self.save_btn = tk.Button(self.toolbar, text="Save As", command=self.pdf_viewer.save_as)
        self.save_btn.pack(side=tk.LEFT)

        self.body = tk.Frame(parent)
        self.body.pack(fill=tk.BOTH, expand=True)

        self.pdf_viewer.init_viewer(self.body)
        # Keyboard & mouse bindings
        parent.bind_all('<Control-z>', lambda e: self.pdf_viewer.undo_delete())
        parent.bind_all('<Delete>', lambda e: self.pdf_viewer.delete_page())

        # Page navigation
        parent.bind_all('<Right>', lambda e: self.pdf_viewer.show_next_page())
        parent.bind_all('<Left>', lambda e: self.pdf_viewer.show_previous_page())
        parent.bind_all('<Down>', lambda e: self.pdf_viewer.show_next_page())
        parent.bind_all('<Up>', lambda e: self.pdf_viewer.show_previous_page())

        # Zoom with Ctrl + MouseWheel
        parent.bind_all('<Control-MouseWheel>', self.mouse_zoom)

        # Scroll for page flip
        parent.bind_all('<MouseWheel>', self.scroll_pages)


    def open_pdf(self):
        path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if path:
            self.pdf_viewer.load_pdf(path)

    def scroll_pages(self, event):
        if event.state & 0x4:  # Ctrl is held -> zoom
            self.mouse_zoom(event)
        elif event.delta < 0:
            self.pdf_viewer.show_next_page()
        elif event.delta > 0:
            self.pdf_viewer.show_previous_page()
            
    def mouse_zoom(self, event):
        if event.delta > 0:
            self.pdf_viewer.zoom_in()
        else:
            self.pdf_viewer.zoom_out()
