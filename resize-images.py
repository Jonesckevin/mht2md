import os
from tkinter import Tk, filedialog, Scrollbar, Canvas, Frame, messagebox
from PIL import Image, ImageTk
import tkinter as tk

MAX_HEIGHT = 1080

def resize_image(image):
    if image.height > MAX_HEIGHT:
        ratio = MAX_HEIGHT / image.height
        new_width = int(image.width * ratio)
        image = image.resize((new_width, MAX_HEIGHT), Image.LANCZOS)
    return image

def select_crop_area(image_path):
    try:
        root = Tk()
        root.title("Select Crop Area")

        img = Image.open(image_path)
        img = resize_image(img)
        tk_img = ImageTk.PhotoImage(img)

        frame = Frame(root)
        frame.pack(fill=tk.BOTH, expand=True)

        canvas = Canvas(frame, width=img.width, height=img.height)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Vertical scrollbar
        vbar = Scrollbar(frame, orient=tk.VERTICAL, command=canvas.yview)
        vbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Horizontal scrollbar
        hbar = Scrollbar(root, orient=tk.HORIZONTAL, command=canvas.xview)
        hbar.pack(side=tk.BOTTOM, fill=tk.X)

        # Configure canvas to use scrollbars
        canvas.config(xscrollcommand=hbar.set, yscrollcommand=vbar.set)
        canvas.create_image(0, 0, anchor=tk.NW, image=tk_img)
        canvas.config(scrollregion=canvas.bbox(tk.ALL))

        crop_coords = []

        def on_mouse_down(event):
            crop_coords.clear()
            crop_coords.append((event.x, event.y))

        def on_mouse_up(event):
            crop_coords.append((event.x, event.y))
            root.quit()

        def on_close():
            messagebox.showinfo("Info", "User stopped the GUI.")
            root.quit()
            root.destroy()
            exit(0)

        canvas.bind("<ButtonPress-1>", on_mouse_down)
        canvas.bind("<ButtonRelease-1>", on_mouse_up)
        root.protocol("WM_DELETE_WINDOW", on_close)

        root.mainloop()
        root.destroy()

        if len(crop_coords) == 2:
            return crop_coords
        else:
            messagebox.showerror("Error", "Failed to select crop area.")
            return None
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {e}")
        return None

def crop_images_in_folder(folder_path, crop_coords, original_size, resized_size):
    try:
        for filename in os.listdir(folder_path):
            if filename.endswith((".png", ".jpg", ".jpeg")):
                image_path = os.path.join(folder_path, filename)
                img = Image.open(image_path)
                
                # Scale crop coordinates back to original image size
                scale_x = original_size[0] / resized_size[0]
                scale_y = original_size[1] / resized_size[1]
                scaled_crop_coords = (
                    int(crop_coords[0][0] * scale_x),
                    int(crop_coords[0][1] * scale_y),
                    int(crop_coords[1][0] * scale_x),
                    int(crop_coords[1][1] * scale_y)
                )
                
                cropped_img = img.crop(scaled_crop_coords)
                cropped_img.save(image_path)
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred while cropping images: {e}")

def main():
    try:
        folder_path = filedialog.askdirectory(title="Select Folder Containing Images")
        if not folder_path:
            messagebox.showinfo("Info", "No folder selected.")
            return
        first_image_path = None
        for filename in os.listdir(folder_path):
            if filename.endswith((".png", ".jpg", ".jpeg")):
                first_image_path = os.path.join(folder_path, filename)
                break

        if not first_image_path:
            messagebox.showinfo("Info", "No images found in the selected folder.")
            return

        img = Image.open(first_image_path)
        original_size = img.size
        img = resize_image(img)
        resized_size = img.size
        crop_coords = select_crop_area(first_image_path)
        if crop_coords:
            root = Tk()
            root.title("Confirm Crop Area")

            img = Image.open(first_image_path)
            img = resize_image(img)
            tk_img = ImageTk.PhotoImage(img)

            frame = Frame(root)
            frame.pack(fill=tk.BOTH, expand=True)

            canvas = Canvas(frame, width=img.width, height=img.height)
            canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

            vbar = Scrollbar(frame, orient=tk.VERTICAL, command=canvas.yview)
            vbar.pack(side=tk.RIGHT, fill=tk.Y)

            # Horizontal scrollbar
            hbar = Scrollbar(root, orient=tk.HORIZONTAL, command=canvas.xview)
            hbar.pack(side=tk.BOTTOM, fill=tk.X)

            # Configure canvas to use scrollbars
            canvas.config(xscrollcommand=hbar.set, yscrollcommand=vbar.set)
            canvas.create_image(0, 0, anchor=tk.NW, image=tk_img)
            canvas.create_rectangle(crop_coords[0][0], crop_coords[0][1], crop_coords[1][0], crop_coords[1][1], outline="red", width=2)
            canvas.config(scrollregion=canvas.bbox(tk.ALL))

            def on_confirm():
                crop_images_in_folder(folder_path, crop_coords, original_size, resized_size)
                messagebox.showinfo("Success", "Images cropped successfully.")
                root.quit()

            def on_cancel():
                messagebox.showinfo("Info", "Crop area selection cancelled.")
                root.quit()

            def on_close():
                messagebox.showinfo("Info", "User stopped the GUI.")
                root.quit()
                root.destroy()
                exit(0)

            confirm_button = tk.Button(root, text="Confirm", command=on_confirm)
            confirm_button.pack(side=tk.LEFT, padx=10, pady=10)

            cancel_button = tk.Button(root, text="Cancel", command=on_cancel)
            cancel_button.pack(side=tk.RIGHT, padx=10, pady=10)

            root.protocol("WM_DELETE_WINDOW", on_close)

            root.mainloop()
            root.destroy()
        else:
            messagebox.showinfo("Info", "Crop area selection cancelled.")
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {e}")

if __name__ == "__main__":
    main()
