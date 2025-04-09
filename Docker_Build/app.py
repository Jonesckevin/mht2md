from flask import Flask, request, render_template, jsonify, send_from_directory, Response
import os
import shutil
import markdown
import zipfile  # Add this import for handling zip files

# Variables
convert_to_png = True  # Set to True to convert JPEG images to PNG

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'outputs'

def extract_images_and_convert_to_md(file_path, convert_to_png=True):
    """
    Extract images and convert MHT file to Markdown.
    This implementation processes the MHT file, extracts images, converts them to PNG, 
    and saves the Markdown file in the output directory.
    """
    import email
    from email import policy
    from bs4 import BeautifulSoup
    from PIL import Image
    import re
    import io

    # Create a directory under 'uploads' for the output
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    output_dir = os.path.join(os.path.dirname(file_path), base_name)
    os.makedirs(output_dir, exist_ok=True)

    # Open the MHT file and parse it like an email message
    with open(file_path, 'rb') as f:
        msg = email.message_from_binary_file(f, policy=policy.default)

    # Extract the HTML part from the "email" message
    html_part = next((part.get_payload(decode=True).decode(part.get_content_charset())
                      for part in msg.walk() if part.get_content_type() == 'text/html'), None)
    if not html_part:
        raise ValueError("No HTML part found in the MHT file")

    # Parse the HTML content using BeautifulSoup
    soup = BeautifulSoup(html_part, 'html.parser')

    # Extract images from the MHT/email message and save them to the output directory
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

    steps_text = {}
    # Extract and clean step text from the HTML content
    for text in soup.stripped_strings:
        match = re.match(r'^Step (\d+):', text)
        if match:
            step_number = int(match.group(1))
            clean_text = re.sub(r'^Step \d+:', '', text).strip()
            steps_text[step_number] = steps_text.get(step_number, '') + ' ' + clean_text

    # Generate Markdown content from the extracted steps
    markdown_content = '\n'.join(
        f"## Step {step_number}\n{step}\n![Image](image_{step_number:04d}.png)\n"
        for step_number, step in sorted(steps_text.items())
    )

    # Save the Markdown content to a file
    md_file_path = os.path.join(output_dir, f"{base_name}.md")
    with open(md_file_path, 'w', encoding='utf-8') as md_file:
        md_file.write(markdown_content)

    # Convert all JPEG images to PNG if convert_to_png is True
    if convert_to_png:
        for image_filename in os.listdir(output_dir):
            if image_filename.lower().endswith('.jpeg'):
                jpeg_path = os.path.join(output_dir, image_filename)
                png_path = os.path.splitext(jpeg_path)[0] + '.png'
                with Image.open(jpeg_path) as img:
                    img.save(png_path, 'PNG')
                os.remove(jpeg_path)

    return output_dir, md_file_path

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    if file and file.filename.endswith('.mht'):
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)
        file.save(file_path)
        try:
            output_dir, markdown_file_path = extract_images_and_convert_to_md(file_path, convert_to_png=convert_to_png)
            
            # Move the uploaded MHT file to the output directory
            shutil.move(file_path, os.path.join(output_dir, os.path.basename(file_path)))
            
            zip_path = os.path.join(app.config['OUTPUT_FOLDER'], f"{os.path.basename(output_dir)}.zip")
            shutil.make_archive(output_dir, 'zip', output_dir)
            shutil.move(f"{output_dir}.zip", zip_path)
            return jsonify({
                "message": "File processed successfully",
                "view_file": f"/view/{file.filename}",
                "view_html": f"/view_html/{os.path.basename(output_dir)}",
                "download_data": f"/download/{os.path.basename(output_dir)}",
                "markdown_file": markdown_file_path
            }), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    return jsonify({"error": "Invalid file type. Please upload an MHT file."}), 400

@app.route('/view_html/<output_dir>')
def view_html(output_dir):
    output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_dir)
    if os.path.exists(output_path):
        # Locate the Markdown file
        md_file_path = next((os.path.join(output_path, f) for f in os.listdir(output_path) if f.endswith('.md')), None)
        if md_file_path:
            with open(md_file_path, 'r', encoding='utf-8') as md_file:
                markdown_content = md_file.read()
            html_content = markdown.markdown(markdown_content)
            # Embed CSS for responsive images
            html_with_styles = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Markdown Viewer</title>
                <style>
                    img {{
                        max-width: 100%;
                        height: auto;
                    }}
                    body {{
                        font-family: Arial, sans-serif;
                        margin: 20px;
                    }}
                </style>
            </head>
            <body>
                {html_content}
            </body>
            </html>
            """
            return Response(html_with_styles, mimetype='text/html')
    return jsonify({"error": "Converted directory not found."}), 404

@app.route('/download/<output_dir>')
def download_data(output_dir):
    output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_dir)
    if os.path.exists(output_path):
        zip_path = shutil.make_archive(output_path, 'zip', output_path)
        return send_from_directory(os.path.dirname(zip_path), os.path.basename(zip_path), as_attachment=True)
    return jsonify({"error": "Extracted directory not found."}), 404

@app.route('/download_all', methods=['GET'])
def download_all():
    try:
        # Check if the outputs folder exists and contains data
        if not os.path.exists(app.config['OUTPUT_FOLDER']) or not os.listdir(app.config['OUTPUT_FOLDER']):
            return render_template('error.html', message="No data available to download. Please upload and process a file first."), 404

        # Create a zip file for all data in the outputs folder
        zip_path = os.path.join(app.config['OUTPUT_FOLDER'], 'all_data.zip')
        if os.path.exists(zip_path):
            os.remove(zip_path)  # Remove existing zip file if it exists

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(app.config['OUTPUT_FOLDER']):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, app.config['OUTPUT_FOLDER'])
                    if arcname != 'all_data.zip':  # Exclude the zip file itself
                        zipf.write(file_path, arcname)

        return send_from_directory(app.config['OUTPUT_FOLDER'], 'all_data.zip', as_attachment=True)
    except Exception as e:
        return jsonify({"error": f"Failed to create zip file: {str(e)}"}), 500

@app.route('/browse_output', defaults={'path': ''})
@app.route('/browse_output/<path:path>')
def browse_output(path):
    base_path = app.config['UPLOAD_FOLDER']
    target_path = os.path.join(base_path, path)

    if not os.path.exists(target_path):
        # Redirect to an error page if the folder does not exist
        return render_template('error.html', message="The output directory does not exist. Please upload and process a file first."), 404

    if os.path.isfile(target_path):
        # Handle .mht files for viewing in the browser
        if target_path.endswith('.mht'):
            with open(target_path, 'r', encoding='utf-8', errors='ignore') as file:
                content = file.read()
            return Response(content, mimetype='text/plain')
        # Open other files for viewing
        return send_from_directory(os.path.dirname(target_path), os.path.basename(target_path), as_attachment=False)

    # If it's a directory, list its contents
    items = os.listdir(target_path)
    links = []

    # Add a link to the parent directory
    if path:
        parent_path = os.path.dirname(path)
        links.append(f'<li><a href="/browse_output/{parent_path}">.</a></li>')

    for item in items:
        item_path = os.path.join(path, item) if path else item
        if os.path.isdir(os.path.join(base_path, item_path)):
            links.append(f'<li><a href="/browse_output/{item_path}">[DIR] {item}</a></li>')
        else:
            links.append(f'<li><a href="/browse_output/{item_path}">{item}</a></li>')

    html_template = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Browse Output</title>
        <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
        <style>
            .list-group-item {{
                padding: 0;
            }}
        </style>
    </head>
    <body>
        <div class="container mt-5">
            <h1 class="text-center">Browse Output Directory</h1>
            <ul class="list-group mt-4">
                {''.join(f'<li class="list-group-item">{link}</li>' for link in links)}
            </ul>
            <div class="mt-4 text-center">
                <a href="/" class="btn btn-primary">Back to Home</a>
            </div>
        </div>
    </body>
    </html>
    """
    return Response(html_template, mimetype='text/html')

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/purge', methods=['POST'])
def purge_data():
    try:
        upload_count = 0
        output_count = 0

        # Count and delete files in the uploads folder
        if os.path.exists(app.config['UPLOAD_FOLDER']):
            upload_count = sum(len(files) for _, _, files in os.walk(app.config['UPLOAD_FOLDER']))
            shutil.rmtree(app.config['UPLOAD_FOLDER'])

        # Count and delete files in the outputs folder
        if os.path.exists(app.config['OUTPUT_FOLDER']):
            output_count = sum(len(files) for _, _, files in os.walk(app.config['OUTPUT_FOLDER']))
            shutil.rmtree(app.config['OUTPUT_FOLDER'])

        total_deleted = upload_count + output_count

        # If no files were deleted, redirect to the error page
        if total_deleted == 0:
            return render_template('error.html', message="No data to purge. The directories are already empty."), 404

        return jsonify({"message": f"All data has been purged successfully. {total_deleted} files were deleted."}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to purge data: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)