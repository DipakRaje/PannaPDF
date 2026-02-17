# pdf_utils/viewer.py - Core PDF viewing logic

import fitz  # PyMuPDF
import os
from tkinter import Frame, Label, Scrollbar, Canvas, Button, filedialog, messagebox
from PIL import Image, ImageTk

class PDFViewer:
    def __init__(self):
        self.pdf_path = None
        self.doc = None
        self.thumbs = []
        self.current_page_index = 0
        self.zoom_level = 1.0
        self.deleted_stack = []

    def init_viewer(self, parent):
        self.container = parent

        self.thumb_frame = Frame(parent, width=150)
        self.thumb_frame.pack(side='left', fill='y')

        self.thumb_canvas = Canvas(self.thumb_frame)
        self.thumb_scroll = Scrollbar(self.thumb_frame, orient='vertical', command=self.thumb_canvas.yview)
        self.thumb_inner = Frame(self.thumb_canvas)

        self.thumb_inner.bind("<Configure>", lambda e: self.thumb_canvas.configure(scrollregion=self.thumb_canvas.bbox("all")))
        self.thumb_canvas.create_window((0, 0), window=self.thumb_inner, anchor='nw')
        self.thumb_canvas.configure(yscrollcommand=self.thumb_scroll.set)
        self.thumb_canvas.pack(side='left', fill='both', expand=True)
        self.thumb_scroll.pack(side='right', fill='y')

        self.viewer = Label(parent)
        self.viewer.pack(side='left', fill='both', expand=True)

    def load_pdf(self, path):
        self.pdf_path = path
        self.doc = fitz.open(path)
        self.render_thumbnails()
        self.show_page(0)

    def render_thumbnails(self):
        for widget in self.thumb_inner.winfo_children():
            widget.destroy()
        self.thumbs.clear()

        for i in range(len(self.doc)):
            pix = self.doc[i].get_pixmap(matrix=fitz.Matrix(0.2, 0.2))
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            thumb = ImageTk.PhotoImage(img)
            btn = Button(self.thumb_inner, image=thumb, command=lambda i=i: self.show_page(i))
            btn.image = thumb
            btn.pack(pady=2)
            self.thumbs.append(btn)
        self.highlight_thumbnail(self.current_page_index)

    def show_page(self, index):
        if not self.doc:
            return
        self.current_page_index = index
        pix = self.doc[index].get_pixmap(matrix=fitz.Matrix(self.zoom_level, self.zoom_level))
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        self.tk_img = ImageTk.PhotoImage(img)
        self.viewer.configure(image=self.tk_img)
        self.highlight_thumbnail(index)

    def highlight_thumbnail(self, index):
        for i, btn in enumerate(self.thumbs):
            btn.configure(relief='sunken' if i == index else 'raised')

    def delete_page(self):
        if not self.doc or len(self.doc) <= 1:
            messagebox.showwarning("Warning", "Cannot delete page.")
            return
        backup = self.doc.write()
        self.deleted_stack.append(backup)
        self.doc.delete_page(self.current_page_index)
        new_index = max(0, self.current_page_index - 1)
        self.render_thumbnails()
        self.show_page(new_index)

    def undo_delete(self):
        if not self.deleted_stack:
            return

        tmp_path = "__undo_tmp__.pdf"
        with open(tmp_path, "wb") as f:
            f.write(self.deleted_stack.pop())

        self.doc = fitz.open(tmp_path)  # Reload into memory
        self.render_thumbnails()
        self.show_page(self.current_page_index)

        try:
            os.remove(tmp_path)  # Just delete the file, don't close doc
        except PermissionError:
            pass



    def toggle_thumbnails(self):
        if self.thumb_frame.winfo_ismapped():
            self.thumb_frame.pack_forget()
        else:
            self.thumb_frame.pack(side='left', fill='y')

    def zoom_in(self):
        self.zoom_level *= 1.25
        self.show_page(self.current_page_index)

    def zoom_out(self):
        self.zoom_level /= 1.25
        self.show_page(self.current_page_index)

    def save_as(self):
        if not self.doc:
            return
        path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")])
        if path:
            self.doc.save(path)
            messagebox.showinfo("Saved", f"PDF saved to: {path}")

    def show_next_page(self):
        if self.current_page_index + 1 < len(self.doc):
            self.show_page(self.current_page_index + 1)

    def show_previous_page(self):
        if self.current_page_index > 0:
            self.show_page(self.current_page_index - 1)
