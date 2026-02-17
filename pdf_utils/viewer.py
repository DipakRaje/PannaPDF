# pdf_utils/viewer.py - Core PDF viewing logic

import fitz  # PyMuPDF
import os
from tkinter import Frame, Scrollbar, Canvas, Button, filedialog, messagebox
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
        """
        Parent must have exactly two direct children after this call:
        thumb_frame and viewer_frame. No spacer frames, no grid on parent.
        """
        self.container = parent

        # Thumbnail frame: fixed-width panel (170px) that does not expand horizontally.
        self.thumb_frame = Frame(parent, width=170)
        self.thumb_frame.pack_propagate(False)  # Prevent frame from resizing based on content
        self.thumb_frame.pack(side='left', fill='y')

        self.thumb_canvas = Canvas(self.thumb_frame)
        self.thumb_scroll = Scrollbar(self.thumb_frame, orient='vertical', command=self.thumb_canvas.yview)
        self.thumb_inner = Frame(self.thumb_canvas)

        self.thumb_inner.bind("<Configure>", lambda e: self.thumb_canvas.configure(scrollregion=self.thumb_canvas.bbox("all")))
        self.thumb_canvas.create_window((0, 0), window=self.thumb_inner, anchor='nw')
        self.thumb_canvas.configure(yscrollcommand=self.thumb_scroll.set)
        # Canvas fills remaining width in frame (frame width - scrollbar width)
        self.thumb_canvas.pack(side='left', fill='both', expand=True)
        self.thumb_scroll.pack(side='right', fill='y')

        # Viewer frame: fills all remaining space. No fixed width, no padding.
        self.viewer_frame = Frame(parent, bg='#87CEEB')
        self.viewer_frame.pack(side='left', fill='both', expand=True)

        self.view_canvas = Canvas(self.viewer_frame, highlightthickness=0, bg='#87CEEB')
        self.v_scroll = Scrollbar(self.viewer_frame, orient='vertical', command=self.view_canvas.yview)
        self.h_scroll = Scrollbar(self.viewer_frame, orient='horizontal', command=self.view_canvas.xview)

        self.view_canvas.configure(yscrollcommand=self.v_scroll.set, xscrollcommand=self.h_scroll.set)

        self.view_canvas.pack(side='left', fill='both', expand=True)
        self.v_scroll.pack(side='right', fill='y')
        self.h_scroll.pack(side='bottom', fill='x')

        self._page_image_id = None
        self.tk_img = None
        self._page_width = 0
        self._page_height = 0

        self.view_canvas.bind('<Configure>', lambda e: self._on_canvas_resize(e))

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

    def _viewport_size(self):
        """Return (width, height) of the visible canvas area."""
        w = self.view_canvas.winfo_width()
        h = self.view_canvas.winfo_height()
        return (max(1, w), max(1, h))

    def _update_canvas_layout(self):
        """Update scroll region and image position: page is top-left aligned (no centering)."""
        if self._page_image_id is None or self.tk_img is None:
            return
        vw, vh = self._viewport_size()
        pw, ph = self._page_width, self._page_height
        total_w = max(pw, vw)
        total_h = max(ph, vh)
        self.view_canvas.configure(scrollregion=(0, 0, total_w, total_h))
        self.view_canvas.coords(self._page_image_id, 0, 0)

    def _on_canvas_resize(self, event):
        """On resize: recalculate fit-to-width zoom and re-render so the page fills viewer width."""
        if self.doc is not None:
            self.show_page(self.current_page_index)

    def show_page(self, index):
        if not self.doc:
            return
        self.current_page_index = index
        vw, vh = self._viewport_size()
        page_rect = self.doc[index].rect
        self.zoom_level = vw / page_rect.width if page_rect.width > 0 else 1.0
        pix = self.doc[index].get_pixmap(matrix=fitz.Matrix(self.zoom_level, self.zoom_level))
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        self.tk_img = ImageTk.PhotoImage(img)
        self._page_width = pix.width
        self._page_height = pix.height

        if self._page_image_id is not None:
            self.view_canvas.delete(self._page_image_id)
        vw, vh = self._viewport_size()
        total_w = max(self._page_width, vw)
        total_h = max(self._page_height, vh)
        self.view_canvas.configure(scrollregion=(0, 0, total_w, total_h))
        self._page_image_id = self.view_canvas.create_image(
            0, 0, image=self.tk_img, anchor='nw'
        )
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
            self.viewer_frame.pack(side='left', fill='both', expand=True)

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

    def _widget_inside(self, widget, ancestor):
        """Return True if widget is ancestor or is inside ancestor's hierarchy."""
        w = widget
        while w:
            if w == ancestor:
                return True
            try:
                w = w.master
            except AttributeError:
                break
        return False

    def handle_wheel(self, event):
        """
        Handle mouse wheel over the viewer: scroll the canvas if content is scrollable.
        Return True if the event was consumed (canvas scrolled), False so the caller can flip page.
        """
        if not self.doc or self._page_image_id is None:
            return False
        if not self._widget_inside(event.widget, self.view_canvas):
            return False
        try:
            region = self.view_canvas.cget('scrollregion').split()
        except Exception:
            return False
        if len(region) < 4:
            return False
        total_h = int(region[3]) - int(region[1])
        viewport_h = self.view_canvas.winfo_height()
        if total_h <= viewport_h:
            return False
        before = self.view_canvas.yview()[0]
        self.view_canvas.yview_scroll(-event.delta, 'units')
        after = self.view_canvas.yview()[0]
        return before != after
