import tkinter as tk  # for gui stuff
from tkinter import ttk, filedialog, Menu  # use dropdown and file menu
from PIL import Image, ImageTk  # image show inside gui
import cv2  # use for image read and edit
import os  # file name and path handle


# main class for app
class ImageProcessingApp:
    def __init__(self, root):
        """Start app window and set variable"""
        self.root = root
        self.root.title("Image Processing Application")  # name on top bar
        self.root.geometry("1200x700")  # window size

        # image hold here
        self.original_image = None
        self.displayed_image = None
        self.cropped_image = None
        self.current_image = None
        self.temp_image = None

        # crop mouse drag variable
        self.start_x = None
        self.start_y = None
        self.end_x = None
        self.end_y = None
        self.crop_rectangle = None
        self.is_drawing = False

        # undo redo history
        self.history = []
        self.history_position = -1
        self.max_history = 10  # max how many undo

        # file path for save
        self.current_file_path = None

        # setup GUI
        self.setup_menu()  # top menu
        self.setup_ui()  # buttons and canvas

    def setup_menu(self):
        """top menu bar"""
        menubar = Menu(self.root)
        self.root.config(menu=menubar)

        # file menu
        file_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(
            label="Open", command=self.load_image, accelerator="Ctrl+O"
        )
        file_menu.add_command(
            label="Save", command=self.save_image, accelerator="Ctrl+S"
        )
        file_menu.add_command(label="Save As", command=self.save_image_as)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

        # edit menu (undo redo)
        edit_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Undo", command=self.undo, accelerator="Ctrl+Z")
        edit_menu.add_command(label="Redo", command=self.redo, accelerator="Ctrl+Y")

        # keyboard shortcut
        self.root.bind("<Control-o>", lambda event: self.load_image())
        self.root.bind("<Control-s>", lambda event: self.save_image())
        self.root.bind("<Control-z>", lambda event: self.undo())
        self.root.bind("<Control-y>", lambda event: self.redo())

    def setup_ui(self):
        """Make layout on window"""
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # left part for original image
        self.left_frame = ttk.LabelFrame(main_frame, text="Original Image")
        self.left_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        self.original_canvas = tk.Canvas(
            self.left_frame, bg="lightgray", width=500, height=500
        )
        self.original_canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # mouse use for crop on original image
        self.original_canvas.bind("<ButtonPress-1>", self.start_crop)
        self.original_canvas.bind("<B1-Motion>", self.update_crop)
        self.original_canvas.bind("<ButtonRelease-1>", self.end_crop)

        # right part for result image
        self.right_frame = ttk.LabelFrame(main_frame, text="Processed Image")
        self.right_frame.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")

        self.processed_canvas = tk.Canvas(
            self.right_frame, bg="lightgray", width=500, height=500
        )
        self.processed_canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # bottom part controls
        self.controls_frame = ttk.LabelFrame(main_frame, text="Controls")
        self.controls_frame.grid(
            row=1, column=0, columnspan=2, padx=5, pady=5, sticky="ew"
        )

        # load image button
        self.load_btn = ttk.Button(
            self.controls_frame, text="Load Image", command=self.load_image
        )
        self.load_btn.grid(row=0, column=0, padx=5, pady=5)

        # save image button
        self.save_btn = ttk.Button(
            self.controls_frame, text="Save Image", command=self.save_image
        )
        self.save_btn.grid(row=0, column=1, padx=5, pady=5)

        # reset crop
        self.reset_crop_btn = ttk.Button(
            self.controls_frame, text="Reset Crop", command=self.reset_crop
        )
        self.reset_crop_btn.grid(row=0, column=2, padx=5, pady=5)

        # apply crop button
        self.apply_crop_btn = ttk.Button(
            self.controls_frame, text="Apply Crop", command=self.apply_crop
        )
        self.apply_crop_btn.grid(row=0, column=3, padx=5, pady=5)

        # resize slider
        ttk.Label(self.controls_frame, text="Resize:").grid(
            row=1, column=0, padx=5, pady=5
        )
        self.resize_slider = ttk.Scale(
            self.controls_frame,
            from_=10,
            to=200,
            orient="horizontal",
            length=300,
            value=100,
            command=self.resize_image,
        )
        self.resize_slider.grid(
            row=1, column=1, columnspan=3, padx=5, pady=5, sticky="ew"
        )

        # brightness slider
        ttk.Label(self.controls_frame, text="Brightness:").grid(
            row=2, column=0, padx=5, pady=5
        )
        self.brightness_slider = ttk.Scale(
            self.controls_frame,
            from_=-100,
            to=100,
            orient="horizontal",
            length=300,
            value=0,
            command=self.adjust_brightness,
        )
        self.brightness_slider.grid(
            row=2, column=1, columnspan=3, padx=5, pady=5, sticky="ew"
        )

        # status bar bottom
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        self.status_bar = ttk.Label(
            self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # make window resize friendly
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=0)

    def load_image(self):
        """open file and show image"""
        file_path = filedialog.askopenfilename(
            filetypes=[
                ("Image files", "*.jpg *.jpeg *.png *.bmp *.gif"),
                ("All files", "*.*"),
            ]
        )

        if file_path:
            try:
                self.current_file_path = file_path
                self.original_image = cv2.imread(file_path)
                self.original_image = cv2.cvtColor(
                    self.original_image, cv2.COLOR_BGR2RGB
                )
                self.displayed_image = self.original_image.copy()
                self.current_image = self.displayed_image.copy()

                # remove old crop rectangle
                if self.crop_rectangle:
                    self.original_canvas.delete(self.crop_rectangle)
                    self.crop_rectangle = None

                # show image in both side
                self.show_image(self.original_image, self.original_canvas)
                self.show_image(self.original_image, self.processed_canvas)

                # reset slider to default
                self.resize_slider.set(100)
                self.brightness_slider.set(0)

                # clear undo/redo
                self.history = [self.original_image.copy()]
                self.history_position = 0

                self.status_var.set(f"Loaded image: {os.path.basename(file_path)}")
            except Exception as e:
                self.status_var.set(f"Error loading image: {str(e)}")

    def show_image(self, image, canvas):
        """show image in canvas area"""
        if image is None:
            return

        canvas_width = canvas.winfo_width()
        canvas_height = canvas.winfo_height()
        if canvas_width <= 1 or canvas_height <= 1:
            canvas_width = 500
            canvas_height = 500

        img_height, img_width = image.shape[:2]
        scaling = min(canvas_width / img_width, canvas_height / img_height)
        new_width = int(img_width * scaling)
        new_height = int(img_height * scaling)

        display_image = cv2.resize(image, (new_width, new_height))
        photo = ImageTk.PhotoImage(image=Image.fromarray(display_image))

        canvas.config(width=new_width, height=new_height)
        canvas.delete("all")
        canvas.create_image(
            new_width // 2, new_height // 2, image=photo, anchor=tk.CENTER
        )
        canvas.image = photo  # don't delete by python garbage

    def start_crop(self, event):
        """mouse start draw"""
        if self.original_image is None:
            return

        self.start_x = self.original_canvas.canvasx(event.x)
        self.start_y = self.original_canvas.canvasy(event.y)

        if self.crop_rectangle:
            self.original_canvas.delete(self.crop_rectangle)

        self.crop_rectangle = self.original_canvas.create_rectangle(
            self.start_x,
            self.start_y,
            self.start_x,
            self.start_y,
            outline="red",
            width=2,
        )
        self.is_drawing = True

    def update_crop(self, event):
        """while dragging mouse"""
        if not self.is_drawing or self.original_image is None:
            return

        self.end_x = self.original_canvas.canvasx(event.x)
        self.end_y = self.original_canvas.canvasy(event.y)

        self.original_canvas.coords(
            self.crop_rectangle, self.start_x, self.start_y, self.end_x, self.end_y
        )

        self.preview_crop()  # show small preview right side

    def end_crop(self, event):
        """mouse release"""
        if not self.is_drawing or self.original_image is None:
            return

        self.is_drawing = False
        self.end_x = self.original_canvas.canvasx(event.x)
        self.end_y = self.original_canvas.canvasy(event.y)

        self.original_canvas.coords(
            self.crop_rectangle, self.start_x, self.start_y, self.end_x, self.end_y
        )
        self.preview_crop()

    def preview_crop(self):
        """show small image of selected part"""
        if self.original_image is None or self.start_x is None or self.end_x is None:
            return

        canvas_width = self.original_canvas.winfo_width()
        canvas_height = self.original_canvas.winfo_height()
        if canvas_width <= 1 or canvas_height <= 1:
            canvas_width = 500
            canvas_height = 500

        img_height, img_width = self.original_image.shape[:2]
        scale_x = img_width / canvas_width
        scale_y = img_height / canvas_height

        x1 = max(0, int(min(self.start_x, self.end_x) * scale_x))
        y1 = max(0, int(min(self.start_y, self.end_y) * scale_y))
        x2 = min(img_width, int(max(self.start_x, self.end_x) * scale_x))
        y2 = min(img_height, int(max(self.start_y, self.end_y) * scale_y))

        self.temp_image = self.original_image[y1:y2, x1:x2].copy()

        if self.temp_image.size > 0:
            self.show_image(self.temp_image, self.processed_canvas)

    def apply_crop(self):
        """apply crop image"""
        if self.temp_image is None or self.temp_image.size == 0:
            self.status_var.set("No valid crop selection")
            return

        self.current_image = self.temp_image.copy()
        self.add_to_history(self.current_image)
        self.show_image(self.current_image, self.processed_canvas)
        self.status_var.set("Crop applied")

    def reset_crop(self):
        """remove crop and back to normal"""
        if self.crop_rectangle:
            self.original_canvas.delete(self.crop_rectangle)
            self.crop_rectangle = None

        self.start_x = None
        self.start_y = None
        self.end_x = None
        self.end_y = None

        if self.original_image is not None:
            self.show_image(self.original_image, self.processed_canvas)
            self.current_image = self.original_image.copy()

        self.status_var.set("Crop selection reset")

    def resize_image(self, value):
        """resize image using slider"""
        if self.current_image is None:
            return

        percentage = float(value)
        if self.history_position >= 0 and self.history_position < len(self.history):
            base_image = self.history[self.history_position].copy()

            if percentage == 100:
                self.show_image(base_image, self.processed_canvas)
                return

            height, width = base_image.shape[:2]
            new_width = int(width * percentage / 100)
            new_height = int(height * percentage / 100)

            resized = cv2.resize(
                base_image, (new_width, new_height), interpolation=cv2.INTER_AREA
            )

            self.show_image(resized, self.processed_canvas)
            self.temp_image = resized
            self.status_var.set(f"Resized to {percentage:.0f}%")

    def adjust_brightness(self, value):
        """change brightness"""
        if self.current_image is None or self.history_position < 0:
            return

        brightness = float(value)
        base_image = self.history[self.history_position].copy()

        adjusted = base_image.copy()
        adjusted = cv2.convertScaleAbs(adjusted, alpha=1, beta=brightness)

        self.show_image(adjusted, self.processed_canvas)
        self.temp_image = adjusted
        self.status_var.set(f"Brightness adjusted: {brightness:.0f}")

    def save_image(self, event=None):
        """save image to file"""
        if self.current_image is None and self.temp_image is None:
            self.status_var.set("No image to save")
            return

        save_image = (
            self.temp_image if self.temp_image is not None else self.current_image
        )

        if save_image is None:
            self.status_var.set("No image to save")
            return

        if self.current_file_path:
            directory, filename = os.path.split(self.current_file_path)
            name, ext = os.path.splitext(filename)
            default_path = os.path.join(directory, f"{name}_edited{ext}")
        else:
            default_path = "untitled.png"

        self.save_image_as(default_path)

    def save_image_as(self, default_path=None):
        """save image as new file name"""
        if self.current_image is None and self.temp_image is None:
            self.status_var.set("No image to save")
            return

        save_image = (
            self.temp_image if self.temp_image is not None else self.current_image
        )

        if default_path is None:
            default_path = "untitled.png"

        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[
                ("PNG files", "*.png"),
                ("JPEG files", "*.jpg"),
                ("All files", "*.*"),
            ],
            initialfile=os.path.basename(default_path),
        )

        if file_path:
            try:
                save_image_bgr = cv2.cvtColor(save_image, cv2.COLOR_RGB2BGR)
                cv2.imwrite(file_path, save_image_bgr)
                self.status_var.set(f"Image saved as {os.path.basename(file_path)}")
            except Exception as e:
                self.status_var.set(f"Error saving image: {str(e)}")

    def add_to_history(self, image):
        """keep image in undo list"""
        if self.history_position < len(self.history) - 1:
            self.history = self.history[: self.history_position + 1]

        self.history.append(image.copy())

        if len(self.history) > self.max_history:
            self.history.pop(0)

        self.history_position = len(self.history) - 1

    def undo(self, event=None):
        """go back one step"""
        if self.history_position > 0:
            self.history_position -= 1
            self.current_image = self.history[self.history_position].copy()
            self.show_image(self.current_image, self.processed_canvas)
            self.status_var.set("Undo")
        else:
            self.status_var.set("Nothing to undo")

    def redo(self, event=None):
        """go forward one step"""
        if self.history_position < len(self.history) - 1:
            self.history_position += 1
            self.current_image = self.history[self.history_position].copy()
            self.show_image(self.current_image, self.processed_canvas)
            self.status_var.set("Redo")
        else:
            self.status_var.set("Nothing to redo")


if __name__ == "__main__":
    root = tk.Tk()
    app = ImageProcessingApp(root)
    root.mainloop()
