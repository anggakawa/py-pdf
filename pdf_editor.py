import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
from pathlib import Path
from pypdf import PdfWriter, PdfReader
from PIL import Image, ImageTk
import tempfile
import threading
from pdf2image import convert_from_path

class DragDropFrame(tk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.parent = parent
        self.drag_data = {"x": 0, "y": 0, "item": None}
        
    def start_drag(self, event, item_widget):
        self.drag_data["item"] = item_widget
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y
        
    def on_drag(self, event, item_widget):
        if self.drag_data["item"] == item_widget:
            # Calculate new position
            x = item_widget.winfo_x() + event.x - self.drag_data["x"]
            y = item_widget.winfo_y() + event.y - self.drag_data["y"]
            item_widget.place(x=x, y=y)
            
    def end_drag(self, event, item_widget):
        if self.drag_data["item"] == item_widget:
            # Find drop position and reorder
            self.parent.handle_drop(item_widget, event.x_root, event.y_root)
            self.drag_data["item"] = None

class FileItem(tk.Frame):
    def __init__(self, parent, file_path, index, on_remove, editor_ref, **kwargs):
        super().__init__(parent, relief="raised", bd=1, **kwargs)
        self.file_path = file_path
        self.index = index
        self.on_remove = on_remove
        self.parent = parent
        self.editor = editor_ref
        
        self.setup_ui()
        self.setup_drag()
        
    def setup_ui(self):
        # Main container
        self.configure(width=120, height=140, bg="white")
        self.pack_propagate(False)
        
        # Icon label
        self.icon_label = tk.Label(self, bg="white", width=10, height=6)
        self.icon_label.pack(pady=5)
        
        # Filename label
        filename = os.path.basename(self.file_path)
        if len(filename) > 15:
            filename = filename[:12] + "..."
        self.name_label = tk.Label(self, text=filename, bg="white", 
                                  font=("Arial", 8), wraplength=100)
        self.name_label.pack()
        
        # Remove button
        self.remove_btn = tk.Button(self, text="×", font=("Arial", 12, "bold"),
                                   fg="red", bg="white", bd=0, cursor="hand2",
                                   command=self.remove_item)
        self.remove_btn.place(x=100, y=5, width=15, height=15)
        
        # Load icon in background
        threading.Thread(target=self.load_icon, daemon=True).start()
        
    def setup_drag(self):
        # Make the entire item draggable
        for widget in [self, self.icon_label, self.name_label]:
            widget.bind("<Button-1>", self.start_drag)
            widget.bind("<B1-Motion>", self.on_drag)
            widget.bind("<ButtonRelease-1>", self.end_drag)
            widget.configure(cursor="hand2")
    
    def start_drag(self, event):
        self.drag_data = {"x": event.x, "y": event.y}
        self.configure(relief="sunken")
        
    def on_drag(self, event):
        x = self.winfo_x() + event.x - self.drag_data["x"]
        y = self.winfo_y() + event.y - self.drag_data["y"]
        self.place(x=x, y=y)
        
    def end_drag(self, event):
        self.configure(relief="raised")
        # Get absolute coordinates
        abs_x = event.x_root
        abs_y = event.y_root
        self.editor.handle_drop(self, abs_x, abs_y)
    
    def load_icon(self):
        try:
            if self.file_path.lower().endswith('.pdf'):
                icon = self.create_pdf_icon()
            else:
                icon = self.create_image_icon()
            
            # Update UI in main thread
            self.after(0, lambda: self.icon_label.configure(image=icon))
            self.icon = icon  # Keep reference
        except Exception as e:
            print(f"Error loading icon for {self.file_path}: {e}")
            self.after(0, self.set_default_icon)
    
    def create_pdf_icon(self):
        try:
            # Convert first page of PDF to image
            pages = convert_from_path(self.file_path, first_page=1, last_page=1, dpi=50)
            if pages:
                img = pages[0]
                img.thumbnail((80, 80), Image.Resampling.LANCZOS)
                return ImageTk.PhotoImage(img)
        except:
            pass
        return self.create_default_pdf_icon()
    
    def create_image_icon(self):
        with Image.open(self.file_path) as img:
            img.thumbnail((80, 80), Image.Resampling.LANCZOS)
            return ImageTk.PhotoImage(img)
    
    def create_default_pdf_icon(self):
        # Create a simple PDF icon
        img = Image.new('RGB', (80, 80), 'lightgray')
        return ImageTk.PhotoImage(img)
    
    def set_default_icon(self):
        img = Image.new('RGB', (80, 80), 'lightblue')
        icon = ImageTk.PhotoImage(img)
        self.icon_label.configure(image=icon)
        self.icon = icon
    
    def remove_item(self):
        self.on_remove(self)

class PDFEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Editor - Drag & Drop Interface")
        self.root.geometry("1000x700")
        self.root.configure(bg="#f0f0f0")
        
        self.files_list = []
        self.file_items = []
        self.setup_ui()
    
    def setup_ui(self):
        # Header
        header_frame = tk.Frame(self.root, bg="#2c3e50", height=60)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)
        
        title_label = tk.Label(header_frame, text="PDF Editor", 
                              font=("Arial", 20, "bold"), fg="white", bg="#2c3e50")
        title_label.pack(pady=15)
        
        # Toolbar
        toolbar = tk.Frame(self.root, bg="#ecf0f1", height=50)
        toolbar.pack(fill=tk.X)
        toolbar.pack_propagate(False)
        
        btn_style = {"font": ("Arial", 10), "padx": 15, "pady": 5, "cursor": "hand2"}
        
        tk.Button(toolbar, text="📄 Add PDFs", command=self.add_pdfs, 
                 bg="#3498db", fg="white", **btn_style).pack(side=tk.LEFT, padx=5, pady=10)
        tk.Button(toolbar, text="🖼️ Add Images", command=self.add_images,
                 bg="#e74c3c", fg="white", **btn_style).pack(side=tk.LEFT, padx=5, pady=10)
        tk.Button(toolbar, text="🗑️ Clear All", command=self.clear_all,
                 bg="#95a5a6", fg="white", **btn_style).pack(side=tk.LEFT, padx=5, pady=10)
        tk.Button(toolbar, text="📋 Combine PDF", command=self.combine_files,
                 bg="#27ae60", fg="white", **btn_style).pack(side=tk.RIGHT, padx=5, pady=10)
        
        # Main content area with scrollable canvas
        self.setup_canvas()
        
        # Instructions
        instructions = tk.Label(self.root, 
                               text="Drag files to reorder • Click × to remove • Add PDFs and images to combine",
                               font=("Arial", 9), fg="#7f8c8d", bg="#f0f0f0")
        instructions.pack(pady=5)
    
    def setup_canvas(self):
        # Create canvas with scrollbar
        canvas_frame = tk.Frame(self.root)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.canvas = tk.Canvas(canvas_frame, bg="white", highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg="white")
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Bind mousewheel to canvas
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
    
    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    def add_pdfs(self):
        """Add PDF files to the list"""
        files = filedialog.askopenfilenames(
            title="Select PDF files",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        for file in files:
            if file not in self.files_list:
                self.add_file_item(file)
    
    def add_images(self):
        """Add image files to the list"""
        files = filedialog.askopenfilenames(
            title="Select image files",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.gif *.bmp *.tiff"),
                ("PNG files", "*.png"),
                ("JPEG files", "*.jpg *.jpeg"),
                ("All files", "*.*")
            ]
        )
        for file in files:
            if file not in self.files_list:
                self.add_file_item(file)
    
    def add_file_item(self, file_path):
        """Add a file item to the interface"""
        self.files_list.append(file_path)
        
        # Create file item widget
        item = FileItem(self.scrollable_frame, file_path, len(self.file_items), 
                       self.remove_file_item, self, width=120, height=140)
        self.file_items.append(item)
        
        self.refresh_layout()
    
    def remove_file_item(self, item):
        """Remove a file item"""
        if item in self.file_items:
            index = self.file_items.index(item)
            self.file_items.remove(item)
            del self.files_list[index]
            item.destroy()
            self.refresh_layout()
    
    def clear_all(self):
        """Clear all files from the list"""
        for item in self.file_items:
            item.destroy()
        self.file_items.clear()
        self.files_list.clear()
        self.refresh_layout()
    
    def refresh_layout(self):
        """Refresh the grid layout of file items"""
        cols = max(1, (self.canvas.winfo_width() - 20) // 130)  # Calculate columns based on width
        
        for i, item in enumerate(self.file_items):
            row = i // cols
            col = i % cols
            item.grid(row=row, column=col, padx=5, pady=5, sticky="nw")
        
        # Update scroll region
        self.root.after(100, lambda: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
    
    def handle_drop(self, dragged_item, x, y):
        """Handle drop operation for reordering"""
        if dragged_item not in self.file_items:
            return
            
        # Find the item under the drop position
        drop_target = None
        for item in self.file_items:
            if item != dragged_item:
                item_x = item.winfo_rootx()
                item_y = item.winfo_rooty()
                item_w = item.winfo_width()
                item_h = item.winfo_height()
                
                if (item_x <= x <= item_x + item_w and 
                    item_y <= y <= item_y + item_h):
                    drop_target = item
                    break
        
        if drop_target:
            # Reorder the items
            old_index = self.file_items.index(dragged_item)
            new_index = self.file_items.index(drop_target)
            
            # Move in both lists
            self.file_items.insert(new_index, self.file_items.pop(old_index))
            self.files_list.insert(new_index, self.files_list.pop(old_index))
        
        # Refresh layout
        self.refresh_layout()
    
    def image_to_pdf_page(self, image_path):
        """Convert an image to a PDF page"""
        try:
            with Image.open(image_path) as img:
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
                temp_pdf.close()
                
                img.save(temp_pdf.name, "PDF", resolution=100.0)
                return temp_pdf.name
        except Exception as e:
            messagebox.showerror("Error", f"Failed to convert image {image_path}: {str(e)}")
            return None
    
    def combine_files(self):
        """Combine all files into a single PDF"""
        if not self.files_list:
            messagebox.showwarning("Warning", "Please add some files first!")
            return
        
        output_file = filedialog.asksaveasfilename(
            title="Save combined PDF as",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        
        if not output_file:
            return
        
        # Show progress dialog
        progress_window = tk.Toplevel(self.root)
        progress_window.title("Combining Files...")
        progress_window.geometry("300x100")
        progress_window.transient(self.root)
        progress_window.grab_set()
        
        progress_label = tk.Label(progress_window, text="Processing files...")
        progress_label.pack(pady=20)
        
        progress_bar = ttk.Progressbar(progress_window, mode='indeterminate')
        progress_bar.pack(pady=10, padx=20, fill=tk.X)
        progress_bar.start()
        
        def combine_in_background():
            try:
                pdf_writer = PdfWriter()
                temp_files = []
                
                for i, file_path in enumerate(self.files_list):
                    progress_label.config(text=f"Processing file {i+1}/{len(self.files_list)}...")
                    
                    if file_path.lower().endswith('.pdf'):
                        try:
                            pdf_reader = PdfReader(file_path)
                            for page in pdf_reader.pages:
                                pdf_writer.add_page(page)
                        except Exception as e:
                            print(f"Error reading PDF {file_path}: {e}")
                            continue
                            
                    elif file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff')):
                        temp_pdf = self.image_to_pdf_page(file_path)
                        if temp_pdf:
                            temp_files.append(temp_pdf)
                            try:
                                pdf_reader = PdfReader(temp_pdf)
                                for page in pdf_reader.pages:
                                    pdf_writer.add_page(page)
                            except Exception as e:
                                print(f"Error processing image {file_path}: {e}")
                                continue
                
                with open(output_file, 'wb') as output_pdf:
                    pdf_writer.write(output_pdf)
                
                # Clean up
                for temp_file in temp_files:
                    try:
                        os.unlink(temp_file)
                    except:
                        pass
                
                # Close progress window and show success
                progress_window.destroy()
                messagebox.showinfo("Success", f"PDF created successfully!\nSaved as: {output_file}")
                
            except Exception as e:
                progress_window.destroy()
                messagebox.showerror("Error", f"Failed to create PDF: {str(e)}")
        
        # Start background thread
        threading.Thread(target=combine_in_background, daemon=True).start()

def main():
    root = tk.Tk()
    
    # Configure window
    root.minsize(800, 600)
    
    # Handle window resize for responsive layout
    def on_resize(event):
        if hasattr(app, 'refresh_layout'):
            app.refresh_layout()
    
    app = PDFEditor(root)
    root.bind('<Configure>', on_resize)
    root.mainloop()

if __name__ == "__main__":
    main()