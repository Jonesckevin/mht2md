# Import necessary modules
import os  # For file and directory operations
import email  # For parsing html/text from MHT files
import re  # For extracting and cleaning step text using regular expressions
from email import policy  # For handling email parsing policies
from bs4 import BeautifulSoup  # For parsing and manipulating HTML content
from PIL import Image  # For image conversion
import subprocess  # For running external scripts

__author__ = "Kevin C. Jones"
__email__ = "jonesckevin@proton.me"
__site__ = "https://github.com/jonesckevin/mht2md.git"

print(f"File Name: {os.path.basename(__file__)}")
print(f"Author: {__author__}")
print(f"Email: {__email__}")
print(f"Site: {__site__}")

## Set the flag to convert images to PNG format. 
# True: Convert images to PNG format
# False: Keep images in their original format (JPEG)
convert_to_png = False
print(f"Converting to PNG is slower but produces higher quality images.")
print(f"Convert images to PNG: {convert_to_png}")

def extract_images_and_convert_to_md(mht_file, convert_to_png):
    # Get the base name of the MHT file and create an output directory
    base_name = os.path.splitext(os.path.basename(mht_file))[0]
    output_dir = os.path.join(os.path.dirname(mht_file), base_name)
    os.makedirs(output_dir, exist_ok=True)

    # Open the MHT file and parse it like an email message
    with open(mht_file, 'rb') as f:
        msg = email.message_from_binary_file(f, policy=policy.default)

    # Extract the HTML part from the "email" message
    html_part = next((part.get_payload(decode=True).decode(part.get_content_charset())
                      for part in msg.walk() if part.get_content_type() == 'text/html'), None)
    if not html_part:
        raise ValueError("No HTML part found in the MHT file")

    # Parse the HTML content using BeautifulSoup
    soup = BeautifulSoup(html_part, 'html.parser')
    image_paths = {}

    # Extract images from the MHT/email message and save them to the output file name directory
    for part in msg.walk():
        if part.get_content_type().startswith('image/'):
            image_data = part.get_payload(decode=True)
            image_filename = os.path.basename(part.get('Content-Location'))
            image_path = os.path.join(output_dir, image_filename)
            with open(image_path, 'wb') as img_file:
                img_file.write(image_data)
            # Update the image source in the HTML content
            img_tag = soup.find('img', {'src': part.get('Content-Location')})
            if img_tag:
                img_tag['src'] = image_filename
                image_paths[part.get('Content-Location')] = image_filename

    steps_text = {}
    # Extract and clean step text from the HTML content
    for text in soup.stripped_strings:
        match = re.match(r'^Step (\d+):', text)
        if match and not re.search(r'\(?\d{2}/\d{2}/\d{4} \d{1,2}:\d{2}:\d{2} [APM]{2}\)?', text):
            step_number = int(match.group(1))
            clean_text = re.sub(r'^Step \d+:|\(?\d{2}/\d{2}/\d{4} \d{1,2}:\d{2}:\d{2} [APM]{2}\)?|[^\x00-\x7F]+', '', text)
            steps_text[step_number] = steps_text.get(step_number, '') + ' ' + clean_text.strip()

    # Generate markdown content from the extracted steps
    markdown_content = '\n'.join(f"## Step {step_number}\n{step}\n### Comment:\n![Image](screenshot{step_number:04d}{'.png' if convert_to_png else '.JPEG'})\n"
                                 for step_number, step in sorted(steps_text.items()))

    # Save the markdown content to a file
    md_file_path = os.path.join(output_dir, f'{base_name}.md')
    with open(md_file_path, 'w', encoding='utf-8') as md_file:
        md_file.write(markdown_content)

    # Convert all jpeg images to png if convert_to_png is True
    if convert_to_png:
        for image_filename in os.listdir(output_dir):
            if image_filename.endswith('.JPEG'):
                jpeg_path = os.path.join(output_dir, image_filename)
                png_path = os.path.splitext(jpeg_path)[0] + '.png'
                with Image.open(jpeg_path) as img:
                    img.save(png_path, 'png')
                os.remove(jpeg_path)

    print(f"Markdown file and images have been saved to {output_dir}")

if __name__ == "__main__":
    # Get the working folder and find all MHT files in it
    working_folder = os.path.dirname(os.path.abspath(__file__))
    mht_files = [os.path.join(working_folder, f) for f in os.listdir(working_folder) if f.endswith('.mht')]

    if not mht_files:
        print("No MHT files found in the working folder.")
    else:
        # Process each MHT file
        for mht_file in mht_files:
            extract_images_and_convert_to_md(mht_file, convert_to_png)

        # Prompt the user if they want to run the resize-images.py script
        run_resize = input("Do you want to run the resize-images.py script to crop all the photos? (yes/no): ").strip().lower()
        if run_resize.lower() in ['yes', 'y', 'ye', 'yeah', 'yep', 'yup', 'sure', 'ok', 'okay']:
            subprocess.run(['python', 'resize-images.py'])
