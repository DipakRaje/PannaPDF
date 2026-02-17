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
        self.viewer_frame = Frame(parent)
        self.viewer_frame.pack(side='left', fill='both', expand=True)

        self.view_canvas = Canvas(self.viewer_frame, highlightthickness=0)
        self.v_scroll = Scrollbar(self.viewer_frame, orient='vertical', command=self.view_canvas.yview)
        self.h_scroll = Scrollbar(self.viewer_frame, orient='horizontal', command=self.view_canvas.xview)

        self.view_canvas.configure(yscrollcommand=self.v_scroll.set, xscrollcommand=self.h_scroll.set)

        self.view_canvas.pack(side='left', fill='both', expand=True)
        self.v_scroll.pack(side='right', fill='y')
        self.h_scroll.pack(side='bottom', fill='x')

        self._page_image_ids = []  # List of canvas image IDs for all pages
        self._page_images = []      # List of PhotoImage objects (prevent garbage collection)
        self._page_y_positions = [] # List of y-coordinates for each page
        self.PAGE_SPACING = 10      # Vertical spacing between pages in pixels

        self.view_canvas.bind('<Configure>', lambda e: self._on_canvas_resize(e))

    def load_pdf(self, path):
        self.pdf_path = path
        self.doc = fitz.open(path)
        self.render_thumbnails()
        self.render_all_pages()

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

    def render_all_pages(self):
        """Render all PDF pages vertically stacked in the canvas."""
        if not self.doc:
            return
        
        # Clear existing page images
        for img_id in self._page_image_ids:
            self.view_canvas.delete(img_id)
        self._page_image_ids.clear()
        self._page_images.clear()
        self._page_y_positions.clear()
        
        # Calculate zoom level based on viewport width (fit-to-width)
        vw, vh = self._viewport_size()
        if len(self.doc) > 0:
            page_rect = self.doc[0].rect
            self.zoom_level = vw / page_rect.width if page_rect.width > 0 else 1.0
        
        # Render each page and calculate vertical positions
        current_y = 0
        max_width = vw
        
        for i in range(len(self.doc)):
            # Render page at current zoom level
            pix = self.doc[i].get_pixmap(matrix=fitz.Matrix(self.zoom_level, self.zoom_level))
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            tk_img = ImageTk.PhotoImage(img)
            
            # Store y-position for this page
            self._page_y_positions.append(current_y)
            
            # Create canvas image at calculated position
            img_id = self.view_canvas.create_image(0, current_y, image=tk_img, anchor='nw')
            self._page_image_ids.append(img_id)
            self._page_images.append(tk_img)  # Keep reference to prevent garbage collection
            
            # Update max width and move to next page position
            max_width = max(max_width, pix.width)
            current_y += pix.height + self.PAGE_SPACING
        
        # Set scroll region to cover all pages
        total_height = current_y - self.PAGE_SPACING  # Remove last spacing
        total_width = max(max_width, vw)
        self.view_canvas.configure(scrollregion=(0, 0, total_width, total_height))
        
        # Highlight current page thumbnail
        self.highlight_thumbnail(self.current_page_index)

    def _on_canvas_resize(self, event):
        """On resize: recalculate fit-to-width zoom and re-render all pages."""
        if self.doc is not None:
            self.render_all_pages()

    def _scroll_to_page(self, index):
        """Scroll canvas to show the specified page."""
        if index < 0 or index >= len(self._page_y_positions):
            return
        try:
            page_y = self._page_y_positions[index]
            vw, vh = self._viewport_size()
            # Center the page in the viewport
            scroll_y = max(0, page_y - vh // 2)
            region = self.view_canvas.cget('scrollregion').split()
            if len(region) >= 4:
                total_h = float(region[3]) - float(region[1])
                if total_h > 0:
                    self.view_canvas.yview_moveto(scroll_y / total_h)
        except Exception:
            pass

    def show_page(self, index):
        """Update current page index, re-render all pages, and scroll to the requested page."""
        if not self.doc or index < 0 or index >= len(self.doc):
            return
        self.current_page_index = index
        self.render_all_pages()
        # Scroll to show the requested page after rendering
        self._scroll_to_page(index)

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
        self.current_page_index = new_index
        self.render_thumbnails()
        self.render_all_pages()

    def undo_delete(self):
        if not self.deleted_stack:
            return

        tmp_path = "__undo_tmp__.pdf"
        with open(tmp_path, "wb") as f:
            f.write(self.deleted_stack.pop())

        self.doc = fitz.open(tmp_path)  # Reload into memory
        self.render_thumbnails()
        self.render_all_pages()

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
        self.render_all_pages()

    def zoom_out(self):
        self.zoom_level /= 1.25
        self.render_all_pages()

    def save_as(self):
        if not self.doc:
            return
        path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")])
        if path:
            self.doc.save(path)
            messagebox.showinfo("Saved", f"PDF saved to: {path}")

    def show_next_page(self):
        """Scroll to next page in the continuous view."""
        if self.current_page_index + 1 < len(self.doc):
            self.current_page_index += 1
            self.highlight_thumbnail(self.current_page_index)
            self._scroll_to_page(self.current_page_index)

    def show_previous_page(self):
        """Scroll to previous page in the continuous view."""
        if self.current_page_index > 0:
            self.current_page_index -= 1
            self.highlight_thumbnail(self.current_page_index)
            self._scroll_to_page(self.current_page_index)

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
        if not self.doc or len(self._page_image_ids) == 0:
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
