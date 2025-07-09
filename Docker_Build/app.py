from flask import Flask, request, render_template, jsonify, send_from_directory, Response, abort, redirect, url_for
import os
import shutil
import markdown
import zipfile
import email
from email import policy
from bs4 import BeautifulSoup
from PIL import Image
import re
import io
import json
import logging
import math
from datetime import datetime
from pathlib import Path
from werkzeug.utils import secure_filename
import math

# Application configuration
app = Flask(__name__)
app.config.update(
    UPLOAD_FOLDER='uploads',
    OUTPUT_FOLDER='outputs',
    MAX_CONTENT_LENGTH=500 * 1024 * 1024,  # 500MB max file size
    SECRET_KEY='mht2md-secret-key-change-in-production',
    SEND_FILE_MAX_AGE_DEFAULT=86400  # Cache static files for 24 hours
)

# Enable compression and caching for better performance
@app.after_request
def after_request(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    # Add caching headers for static assets
    if request.endpoint == 'static':
        response.cache_control.max_age = 86400  # 24 hours
        response.cache_control.public = True
    
    return response

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Application metadata
APP_VERSION = "2.0.0"
APP_NAME = "MHT to Markdown Converter"

def formatFileSize(bytes):
    """Format file size in human readable format."""
    if bytes == 0:
        return "0 B"
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = int(math.floor(math.log(bytes, 1024)))
    p = math.pow(1024, i)
    s = round(bytes / p, 2)
    return f"{s} {size_names[i]}"

# Variables
convert_to_png = True  # Set to True to convert JPEG images to PNG
image_quality = 95     # JPEG quality (1-100)

class MHTProcessor:
    """Enhanced MHT processor with better error handling and features."""
    
    def __init__(self, convert_to_png: bool = True, quality: int = 95):
        self.convert_to_png = convert_to_png
        self.quality = max(1, min(100, quality))
        
    def process_file(self, file_path: str) -> tuple:
        """
        Process MHT file and return output directory and markdown file path.
        
        Returns:
            tuple: (output_dir, markdown_file_path, stats)
        """
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            raise FileNotFoundError(f"MHT file not found: {file_path}")
        
        logger.info(f"Processing MHT file: {file_path_obj.name}")
        
        try:
            # Create output directory
            base_name = file_path_obj.stem
            output_dir = file_path_obj.parent / base_name
            output_dir.mkdir(exist_ok=True)

            # Parse MHT file
            with open(file_path, 'rb') as f:
                msg = email.message_from_binary_file(f, policy=policy.default)

            # Extract HTML content
            html_part = self._extract_html_content(msg)
            soup = BeautifulSoup(html_part, 'html.parser')

            # Extract images
            image_count = self._extract_images(msg, output_dir)
            
            # Extract step text
            steps_text = self._extract_step_text(soup)
            
            # Generate markdown
            markdown_content = self._generate_markdown(base_name, file_path_obj.name, steps_text, image_count)
            
            # Save markdown file
            md_file_path = output_dir / f'{base_name}.md'
            md_file_path.write_text(markdown_content, encoding='utf-8')
            
            # Create metadata
            metadata = self._create_metadata(file_path_obj.name, image_count, len(steps_text))
            metadata_path = output_dir / "conversion_info.json"
            metadata_path.write_text(json.dumps(metadata, indent=2), encoding='utf-8')
            
            stats = {
                'images': image_count,
                'steps': len(steps_text),
                'file_size': file_path_obj.stat().st_size
            }
            
            logger.info(f"Successfully processed {file_path_obj.name}: {image_count} images, {len(steps_text)} steps")
            return str(output_dir), str(md_file_path), stats
            
        except Exception as e:
            logger.error(f"Error processing {file_path_obj.name}: {str(e)}")
            # Clean up on error
            if output_dir.exists():
                shutil.rmtree(output_dir)
            raise e
    
    def _extract_html_content(self, msg) -> str:
        """Extract HTML content from email message."""
        html_part = next(
            (part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8', errors='ignore')
             for part in msg.walk() if part.get_content_type() == 'text/html'), 
            None
        )
        if not html_part:
            raise ValueError("No HTML part found in the MHT file")
        return html_part
    
    def _extract_images(self, msg, output_dir: Path) -> int:
        """Extract images from MHT message."""
        image_count = 0
        
        for part in msg.walk():
            if part.get_content_type().startswith('image/'):
                image_data = part.get_payload(decode=True)
                if not image_data:
                    continue
                
                # Determine step number
                content_location = part.get('Content-Location')
                step_number = self._extract_step_number(content_location, image_count + 1)
                
                # Generate filename
                extension = '.png' if self.convert_to_png else '.JPEG'
                image_filename = f"screenshot{step_number:04d}{extension}"
                image_path = output_dir / image_filename
                
                # Save and potentially convert image
                self._save_image(image_data, image_path, part.get_content_type())
                image_count += 1
        
        return image_count
    
    def _extract_step_number(self, content_location: str, default: int) -> int:
        """Extract step number from content location."""
        if content_location:
            step_match = re.search(r'(\d+)', content_location)
            if step_match:
                return int(step_match.group(1))
        return default
    
    def _save_image(self, image_data: bytes, image_path: Path, content_type: str):
        """Save image with optional conversion."""
        if self.convert_to_png and content_type in ['image/jpeg', 'image/jpg']:
            # Convert JPEG to PNG
            with Image.open(io.BytesIO(image_data)) as img:
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                img.save(image_path, 'PNG', optimize=True)
        else:
            # Save as original format, but optimize JPEG quality
            if content_type in ['image/jpeg', 'image/jpg'] and not self.convert_to_png:
                with Image.open(io.BytesIO(image_data)) as img:
                    img.save(image_path, 'JPEG', quality=self.quality, optimize=True)
            else:
                image_path.write_bytes(image_data)
    
    def _extract_step_text(self, soup) -> dict:
        """Extract step text from HTML content."""
        steps_text = {}
        
        for text in soup.stripped_strings:
            match = re.match(r'^Step (\d+):', text)
            if match and not re.search(r'\(?\d{2}/\d{2}/\d{4} \d{1,2}:\d{2}:\d{2} [APM]{2}\)?', text):
                step_number = int(match.group(1))
                clean_text = re.sub(
                    r'^Step \d+:|\(?\d{2}/\d{2}/\d{4} \d{1,2}:\d{2}:\d{2} [APM]{2}\)?|[^\x00-\x7F]+', 
                    '', text
                ).strip()
                
                if clean_text:
                    if step_number in steps_text:
                        steps_text[step_number] += ' ' + clean_text
                    else:
                        steps_text[step_number] = clean_text
        
        return steps_text
    
    def _generate_markdown(self, base_name: str, original_filename: str, steps_text: dict, image_count: int) -> str:
        """Generate enhanced markdown content."""
        extension = '.png' if self.convert_to_png else '.JPEG'
        
        content = [
            f"# {base_name} - Step Recorder Documentation",
            "",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ",
            f"**Original File:** `{original_filename}`  ",
            f"**Total Steps:** {len(steps_text)}  ",
            f"**Total Images:** {image_count}  ",
            f"**Image Format:** {'PNG' if self.convert_to_png else 'JPEG'}",
            "",
            "---",
            "",
            "## Table of Contents",
            ""
        ]
        
        # Add table of contents
        for step_number in sorted(steps_text.keys()):
            if steps_text[step_number].strip():
                content.append(f"- [Step {step_number}](#step-{step_number})")
        
        content.extend(["", "---", ""])
        
        # Add steps content
        for step_number, step in sorted(steps_text.items()):
            if step.strip():
                content.extend([
                    f"## Step {step_number}",
                    "",
                    f"**Action:** {step.strip()}",
                    "",
                    "### Screenshot:",
                    f"![Step {step_number} Screenshot](screenshot{step_number:04d}{extension})",
                    "",
                    "---",
                    ""
                ])
        
        # Add footer
        content.extend([
            "## About This Document",
            "",
            f"This documentation was automatically generated from a Windows Step Recorder file using **{APP_NAME} v{APP_VERSION}**.",
            "",
            f"- **Generated on:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"- **Converter Version:** {APP_VERSION}",
            ""
        ])
        
        return "\n".join(content)
    
    def _create_metadata(self, original_filename: str, image_count: int, step_count: int) -> dict:
        """Create metadata for the conversion."""
        return {
            "conversion_info": {
                "original_file": original_filename,
                "converted_on": datetime.now().isoformat(),
                "converter_version": APP_VERSION,
                "image_format": "PNG" if self.convert_to_png else "JPEG",
                "image_quality": self.quality if not self.convert_to_png else 100
            },
            "statistics": {
                "total_images": image_count,
                "total_steps": step_count
            }
        }

# Initialize processor
processor = MHTProcessor(convert_to_png=convert_to_png, quality=image_quality)

def get_folder_stats():
    """Get statistics about uploaded and converted files."""
    stats = {
        'total_files': 0,
        'total_size': 0,
        'converted_files': 0,
        'last_upload': None
    }
    
    # Check uploads folder
    uploads_path = Path(app.config['UPLOAD_FOLDER'])
    if uploads_path.exists():
        for item in uploads_path.rglob('*'):
            if item.is_file():
                stats['total_files'] += 1
                stats['total_size'] += item.stat().st_size
                if item.suffix.lower() == '.md':
                    stats['converted_files'] += 1
                # Get last modification time
                mtime = datetime.fromtimestamp(item.stat().st_mtime)
                if not stats['last_upload'] or mtime > stats['last_upload']:
                    stats['last_upload'] = mtime
    
    return stats

@app.route('/')
def index():
    """Enhanced home page with statistics."""
    stats = get_folder_stats()
    return render_template('index.html', stats=stats, app_version=APP_VERSION)

@app.route('/convert', methods=['POST'])
def convert_file():
    """Alias for upload_file to maintain compatibility."""
    return upload_file()

@app.route('/browse')
def browse_files():
    """Alias for browse_output to maintain compatibility."""
    return browse_output()

@app.route('/upload', methods=['POST'])
def upload_file():
    """Enhanced file upload with better error handling and validation."""
    try:
        # Validate request
        if 'file' not in request.files:
            return jsonify({"error": "No file part in the request"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        # Validate file extension
        if not file.filename.lower().endswith('.mht'):
            return jsonify({"error": "Invalid file type. Please upload an MHT file."}), 400
        
        # Secure filename
        filename = secure_filename(file.filename)
        if not filename.endswith('.mht'):
            filename += '.mht'
        
        # Create directories
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)
        
        # Save uploaded file
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        logger.info(f"File uploaded: {filename}")
        
        # Process the MHT file
        output_dir, markdown_file_path, stats = processor.process_file(file_path)
        
        # Move the uploaded MHT file to the output directory for reference
        shutil.move(file_path, os.path.join(output_dir, filename))
        
        # Create a zip file for download
        base_name = os.path.basename(output_dir)
        zip_path = os.path.join(app.config['OUTPUT_FOLDER'], f"{base_name}.zip")
        shutil.make_archive(os.path.splitext(zip_path)[0], 'zip', output_dir)
        
        response_data = {
            "message": "File processed successfully! ✅",
            "details": f"Extracted {stats['images']} images and {stats['steps']} steps from {filename}",
            "view_html": f"/view/{base_name}",
            "download_data": f"/download/{base_name}",
            "markdown_file": os.path.basename(markdown_file_path),
            "output_dir": base_name,
            "stats": stats
        }
        
        logger.info(f"File processed successfully: {filename}")
        return jsonify(response_data), 200
        
    except ValueError as ve:
        logger.error(f"File processing error: {str(ve)}")
        return jsonify({"error": f"File processing error: {str(ve)}"}), 400
    except Exception as e:
        logger.error(f"Unexpected error during upload: {str(e)}")
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500

@app.route('/view/<output_dir>')
def view_documentation(output_dir):
    """Enhanced documentation viewer with better styling and features."""
    output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_dir)
    if not os.path.exists(output_path):
        return render_template('error.html', message="Documentation not found. The file may have been deleted or moved."), 404
    
    # Find the Markdown file
    md_file_path = next((os.path.join(output_path, f) for f in os.listdir(output_path) if f.endswith('.md')), None)
    if not md_file_path:
        return render_template('error.html', message="Markdown file not found in the output directory."), 404
    
    try:
        with open(md_file_path, 'r', encoding='utf-8') as md_file:
            markdown_content = md_file.read()
        
        # Convert markdown to HTML with extensions
        html_content = markdown.markdown(
            markdown_content, 
            extensions=['fenced_code', 'tables', 'toc', 'codehilite']
        )
        
        # Load metadata if available
        metadata_path = os.path.join(output_path, 'conversion_info.json')
        metadata = {}
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
        
        # Enhanced HTML template with modern styling
        html_template = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>📋 Step Recorder Documentation - {output_dir}</title>
            <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.24.1/themes/prism.min.css">
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.24.1/plugins/line-numbers/prism-line-numbers.min.css">
            <style>
                :root {{
                    --primary-color: #667eea;
                    --secondary-color: #764ba2;
                    --accent-color: #f093fb;
                    --text-color: #333;
                    --bg-color: #f8f9fa;
                    --card-bg: #ffffff;
                    --border-color: #e9ecef;
                }}
                
                body {{
                    font-family: 'Inter', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    line-height: 1.7;
                    color: var(--text-color);
                    background: linear-gradient(135deg, var(--primary-color) 0%, var(--secondary-color) 100%);
                    min-height: 100vh;
                }}
                
                .main-container {{
                    max-width: 1200px;
                    margin: 2rem auto;
                    background: var(--card-bg);
                    border-radius: 20px;
                    box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                    overflow: hidden;
                }}
                
                .header-section {{
                    background: linear-gradient(135deg, var(--primary-color) 0%, var(--secondary-color) 100%);
                    color: white;
                    padding: 2rem;
                    text-align: center;
                    position: relative;
                }}
                
                .header-section::before {{
                    content: '';
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 20"><defs><radialGradient id="a" cx="50%" cy="50%"><stop offset="0%" stop-color="rgba(255,255,255,.1)"/><stop offset="100%" stop-color="rgba(255,255,255,0)"/></radialGradient></defs><rect width="100" height="20" fill="url(%23a)"/>') repeat;
                    opacity: 0.1;
                }}
                
                .header-content {{
                    position: relative;
                    z-index: 1;
                }}
                
                .content-section {{
                    padding: 2rem;
                }}
                
                .toolbar {{
                    position: sticky;
                    top: 0;
                    background: rgba(255, 255, 255, 0.95);
                    backdrop-filter: blur(10px);
                    border-bottom: 1px solid var(--border-color);
                    padding: 1rem;
                    margin: -2rem -2rem 2rem -2rem;
                    z-index: 100;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    flex-wrap: wrap;
                    gap: 1rem;
                }}
                
                .btn-custom {{
                    background: linear-gradient(135deg, var(--primary-color) 0%, var(--secondary-color) 100%);
                    border: none;
                    padding: 0.5rem 1rem;
                    border-radius: 25px;
                    color: white;
                    font-weight: 500;
                    transition: all 0.3s ease;
                    text-decoration: none;
                    display: inline-flex;
                    align-items: center;
                    gap: 0.5rem;
                }}
                
                .btn-custom:hover {{
                    transform: translateY(-2px);
                    box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
                    color: white;
                    text-decoration: none;
                }}
                
                .btn-secondary-custom {{
                    background: linear-gradient(135deg, #6c757d 0%, #495057 100%);
                    border: none;
                    padding: 0.5rem 1rem;
                    border-radius: 25px;
                    color: white;
                    font-weight: 500;
                    transition: all 0.3s ease;
                    text-decoration: none;
                    display: inline-flex;
                    align-items: center;
                    gap: 0.5rem;
                }}
                
                .btn-secondary-custom:hover {{
                    transform: translateY(-2px);
                    color: white;
                    text-decoration: none;
                }}
                
                img {{
                    max-width: 100%;
                    height: auto;
                    border: 2px solid var(--border-color);
                    border-radius: 12px;
                    box-shadow: 0 8px 25px rgba(0,0,0,0.1);
                    margin: 1.5rem 0;
                    transition: all 0.3s ease;
                    cursor: pointer;
                }}
                
                img:hover {{
                    transform: scale(1.02);
                    box-shadow: 0 12px 30px rgba(0,0,0,0.15);
                }}
                
                h1 {{
                    color: var(--primary-color);
                    border-bottom: 3px solid var(--primary-color);
                    padding-bottom: 1rem;
                    margin-bottom: 2rem;
                    font-weight: 300;
                }}
                
                h2 {{
                    background: linear-gradient(135deg, var(--primary-color) 0%, var(--secondary-color) 100%);
                    color: white;
                    padding: 1rem 1.5rem;
                    border-radius: 12px;
                    margin: 2rem 0 1.5rem 0;
                    box-shadow: 0 4px 15px rgba(102, 126, 234, 0.2);
                    position: relative;
                    overflow: hidden;
                }}
                
                h2::before {{
                    content: '';
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background: linear-gradient(45deg, rgba(255,255,255,0.1) 25%, transparent 25%, transparent 75%, rgba(255,255,255,0.1) 75%);
                    background-size: 30px 30px;
                }}
                
                h3 {{
                    color: var(--secondary-color);
                    margin: 1.5rem 0 1rem 0;
                    font-size: 1.2em;
                    font-weight: 600;
                    display: flex;
                    align-items: center;
                    gap: 0.5rem;
                }}
                
                h3::before {{
                    content: '📸';
                    font-size: 1.2em;
                }}
                
                p {{
                    margin-bottom: 1.2rem;
                    text-align: justify;
                }}
                
                .step-content {{
                    background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
                    padding: 1.5rem;
                    border-radius: 12px;
                    margin-bottom: 2rem;
                    border-left: 5px solid var(--primary-color);
                    box-shadow: 0 4px 15px rgba(0,0,0,0.05);
                }}
                
                .metadata-info {{
                    background: var(--bg-color);
                    padding: 1rem;
                    border-radius: 8px;
                    margin-bottom: 1rem;
                    border: 1px solid var(--border-color);
                }}
                
                .image-modal {{
                    display: none;
                    position: fixed;
                    z-index: 2000;
                    left: 0;
                    top: 0;
                    width: 100%;
                    height: 100%;
                    background-color: rgba(0,0,0,0.95);
                    animation: fadeIn 0.3s ease;
                }}
                
                .modal-content {{
                    margin: auto;
                    display: block;
                    width: 90%;
                    max-width: 1200px;
                    max-height: 90%;
                    object-fit: contain;
                    border-radius: 8px;
                }}
                
                .close {{
                    position: absolute;
                    top: 20px;
                    right: 35px;
                    color: #f1f1f1;
                    font-size: 40px;
                    font-weight: bold;
                    cursor: pointer;
                    transition: color 0.3s ease;
                }}
                
                .close:hover {{
                    color: var(--accent-color);
                }}
                
                .toc {{
                    background: var(--bg-color);
                    padding: 1.5rem;
                    border-radius: 12px;
                    border: 1px solid var(--border-color);
                    margin: 1.5rem 0;
                }}
                
                .toc h3 {{
                    margin-top: 0;
                    color: var(--primary-color);
                }}
                
                .toc ul {{
                    margin: 0;
                    padding-left: 1.5rem;
                }}
                
                .toc a {{
                    color: var(--text-color);
                    text-decoration: none;
                    padding: 0.25rem 0;
                    display: block;
                    transition: color 0.3s ease;
                }}
                
                .toc a:hover {{
                    color: var(--primary-color);
                    text-decoration: none;
                }}
                
                @keyframes fadeIn {{
                    from {{ opacity: 0; }}
                    to {{ opacity: 1; }}
                }}
                
                @media print {{
                    .toolbar, .image-modal {{ display: none !important; }}
                    .main-container {{ 
                        box-shadow: none; 
                        margin: 0; 
                        border-radius: 0;
                    }}
                    body {{ 
                        background: white !important; 
                        color: black !important;
                    }}
                    h2 {{
                        background: none !important;
                        color: black !important;
                        border: 2px solid black;
                    }}
                }}
                
                @media (max-width: 768px) {{
                    .main-container {{
                        margin: 1rem;
                        border-radius: 12px;
                    }}
                    .content-section {{
                        padding: 1rem;
                    }}
                    .toolbar {{
                        flex-direction: column;
                        align-items: stretch;
                    }}
                    .toolbar > div {{
                        display: flex;
                        gap: 0.5rem;
                        flex-wrap: wrap;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="main-container">
                <div class="header-section">
                    <div class="header-content">
                        <h1 class="mb-0">📋 Step Recorder Documentation</h1>
                        <p class="mb-0 mt-2 opacity-75">Generated from: <strong>{output_dir}</strong></p>
                    </div>
                </div>
                
                <div class="content-section">
                    <div class="toolbar">
                        <div>
                            <a href="/" class="btn-custom">
                                <i class="fas fa-home"></i> Home
                            </a>
                            <a href="/browse_output" class="btn-secondary-custom">
                                <i class="fas fa-folder"></i> Browse Files
                            </a>
                        </div>
                        <div>
                            <button onclick="window.print()" class="btn-secondary-custom">
                                <i class="fas fa-print"></i> Print
                            </button>
                            <a href="/download/{output_dir}" class="btn-custom">
                                <i class="fas fa-download"></i> Download
                            </a>
                        </div>
                    </div>
                    
                    {"<div class='metadata-info'><small><strong>Conversion Info:</strong> " + json.dumps(metadata.get('conversion_info', {}), indent=2) + "</small></div>" if metadata else ""}
                    
                    <div class="documentation-content">
                        {html_content}
                    </div>
                </div>
            </div>
            
            <!-- Image Modal -->
            <div id="imageModal" class="image-modal">
                <span class="close">&times;</span>
                <img class="modal-content" id="modalImage">
            </div>
            
            <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.24.1/components/prism-core.min.js"></script>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.24.1/plugins/autoloader/prism-autoloader.min.js"></script>
            <script>
                // Enhanced image click functionality
                document.querySelectorAll('img').forEach(img => {{
                    img.addEventListener('click', function() {{
                        const modal = document.getElementById('imageModal');
                        const modalImg = document.getElementById('modalImage');
                        modal.style.display = 'block';
                        modalImg.src = this.src;
                        modalImg.alt = this.alt;
                    }});
                }});
                
                // Close modal functionality
                const modal = document.getElementById('imageModal');
                const closeBtn = document.querySelector('.close');
                
                closeBtn.addEventListener('click', function() {{
                    modal.style.display = 'none';
                }});
                
                modal.addEventListener('click', function(e) {{
                    if (e.target === this) {{
                        this.style.display = 'none';
                    }}
                }});
                
                // Keyboard navigation
                document.addEventListener('keydown', function(e) {{
                    if (e.key === 'Escape' && modal.style.display === 'block') {{
                        modal.style.display = 'none';
                    }}
                }});
                
                // Smooth scrolling for anchor links
                document.querySelectorAll('a[href^="#"]').forEach(anchor => {{
                    anchor.addEventListener('click', function (e) {{
                        e.preventDefault();
                        const target = document.querySelector(this.getAttribute('href'));
                        if (target) {{
                            target.scrollIntoView({{
                                behavior: 'smooth',
                                block: 'start'
                            }});
                        }}
                    }});
                }});
            </script>
        </body>
        </html>
        """
        
        return Response(html_template, mimetype='text/html')
        
    except Exception as e:
        logger.error(f"Error processing documentation view: {str(e)}")
        return render_template('error.html', 
            message=f"Error displaying documentation: {str(e)}"), 500
@app.route('/download/<output_dir>')
def download_data(output_dir):
    """Enhanced download functionality with better error handling."""
    output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_dir)
    if not os.path.exists(output_path):
        return jsonify({"error": "Output directory not found."}), 404
    
    try:
        # Create zip file
        zip_path = shutil.make_archive(output_path, 'zip', output_path)
        return send_from_directory(
            os.path.dirname(zip_path), 
            os.path.basename(zip_path), 
            as_attachment=True,
            download_name=f"{output_dir}_converted.zip"
        )
    except Exception as e:
        logger.error(f"Error creating download: {str(e)}")
        return jsonify({"error": f"Failed to create download: {str(e)}"}), 500

@app.route('/api/stats')
def api_stats():
    """API endpoint for application statistics."""
    try:
        stats = get_folder_stats()
        return jsonify({
            "status": "success",
            "data": stats,
            "app_info": {
                "name": APP_NAME,
                "version": APP_VERSION,
                "timestamp": datetime.now().isoformat()
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
@app.route('/download_all', methods=['GET'])
def download_all():
    """Enhanced download all functionality."""
    try:
        if not os.path.exists(app.config['OUTPUT_FOLDER']) or not os.listdir(app.config['OUTPUT_FOLDER']):
            return render_template('error.html', 
                message="No data available to download. Please upload and process a file first."), 404

        zip_path = os.path.join(app.config['OUTPUT_FOLDER'], 'all_converted_files.zip')
        if os.path.exists(zip_path):
            os.remove(zip_path)

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(app.config['OUTPUT_FOLDER']):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, app.config['OUTPUT_FOLDER'])
                    if arcname != 'all_converted_files.zip':
                        zipf.write(file_path, arcname)

        return send_from_directory(
            app.config['OUTPUT_FOLDER'], 
            'all_converted_files.zip', 
            as_attachment=True,
            download_name=f"all_converted_files_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        )
    except Exception as e:
        logger.error(f"Error in download_all: {str(e)}")
        return jsonify({"error": f"Failed to create download: {str(e)}"}), 500

@app.route('/browse_output', defaults={'path': ''})
@app.route('/browse_output/<path:path>')
def browse_output(path):
    """Enhanced file browser with better UI."""
    base_path = app.config['UPLOAD_FOLDER']
    target_path = os.path.join(base_path, path)

    if not os.path.exists(target_path):
        return render_template('error.html', 
            message="Directory not found. Please upload and process files first."), 404

    if os.path.isfile(target_path):
        if target_path.endswith('.mht'):
            try:
                with open(target_path, 'r', encoding='utf-8', errors='ignore') as file:
                    content = file.read()
                return Response(content, mimetype='text/plain')
            except Exception as e:
                return jsonify({"error": f"Error reading file: {str(e)}"}), 500
        elif target_path.endswith('.md'):
            try:
                with open(target_path, 'r', encoding='utf-8') as file:
                    markdown_content = file.read()
                html_content = markdown.markdown(markdown_content, extensions=['fenced_code', 'tables'])
                return Response(f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>📄 Markdown Preview</title>
                        <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
                        <style>
                            body {{ padding: 2rem; font-family: 'Segoe UI', sans-serif; }}
                            img {{ max-width: 100%; height: auto; border-radius: 8px; margin: 1rem 0; }}
                        </style>
                    </head>
                    <body>
                        <div class="container">
                            <a href="/browse_output/{os.path.dirname(path)}" class="btn btn-secondary mb-3">
                                <i class="fas fa-arrow-left"></i> Back
                            </a>
                            <div class="content">{html_content}</div>
                        </div>
                    </body>
                    </html>
                """, mimetype='text/html')
            except Exception as e:
                return jsonify({"error": f"Error reading markdown: {str(e)}"}), 500
        
        return send_from_directory(os.path.dirname(target_path), os.path.basename(target_path))

    # Directory listing with enhanced UI
    try:
        items = os.listdir(target_path)
        links = []

        if path:
            parent_path = os.path.dirname(path)
            links.append({
                'name': '← Parent Directory',
                'path': f'/browse_output/{parent_path}' if parent_path else '/browse_output',
                'type': 'parent',
                'icon': 'fas fa-level-up-alt'
            })

        for item in items:
            item_path = os.path.join(path, item) if path else item
            full_path = os.path.join(base_path, item_path)
            
            if os.path.isdir(full_path):
                links.append({
                    'name': item,
                    'path': f'/browse_output/{item_path}',
                    'type': 'directory',
                    'icon': 'fas fa-folder'
                })
            else:
                file_info = {
                    'name': item,
                    'path': f'/browse_output/{item_path}',
                    'type': 'file'
                }
                
                if item.endswith('.md'):
                    file_info.update({'icon': 'fas fa-file-alt', 'file_type': 'Markdown'})
                elif item.endswith(('.png', '.jpg', '.jpeg', '.JPEG', '.PNG')):
                    file_info.update({'icon': 'fas fa-image', 'file_type': 'Image'})
                elif item.endswith('.mht'):
                    file_info.update({'icon': 'fas fa-file-code', 'file_type': 'MHT File'})
                elif item.endswith('.zip'):
                    file_info.update({'icon': 'fas fa-file-archive', 'file_type': 'Archive'})
                else:
                    file_info.update({'icon': 'fas fa-file', 'file_type': 'File'})
                
                links.append(file_info)

        return render_template('browse.html', links=links, current_path=path)
    except Exception as e:
        logger.error(f"Error browsing directory: {str(e)}")
        return render_template('error.html', message=f"Error browsing directory: {str(e)}"), 500

@app.route('/purge', methods=['POST'])
def purge_data():
    """Enhanced data purging with better feedback."""
    try:
        upload_count = 0
        output_count = 0

        if os.path.exists(app.config['UPLOAD_FOLDER']):
            upload_count = sum(len(files) for _, _, files in os.walk(app.config['UPLOAD_FOLDER']))
            shutil.rmtree(app.config['UPLOAD_FOLDER'])

        if os.path.exists(app.config['OUTPUT_FOLDER']):
            output_count = sum(len(files) for _, _, files in os.walk(app.config['OUTPUT_FOLDER']))
            shutil.rmtree(app.config['OUTPUT_FOLDER'])

        total_deleted = upload_count + output_count

        if total_deleted == 0:
            return jsonify({"message": "No data to purge. Directories are already clean."}), 200

        logger.info(f"Purged {total_deleted} files ({upload_count} uploads, {output_count} outputs)")
        return jsonify({
            "message": f"Successfully purged {total_deleted} files.",
            "details": f"Uploads: {upload_count}, Outputs: {output_count}"
        }), 200
    except Exception as e:
        logger.error(f"Error purging data: {str(e)}")
        return jsonify({"error": f"Failed to purge data: {str(e)}"}), 500

@app.route('/health')
def health_check():
    """Comprehensive health check endpoint."""
    try:
        stats = get_folder_stats()
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "app_info": {
                "name": APP_NAME,
                "version": APP_VERSION
            },
            "configuration": {
                "convert_to_png": convert_to_png,
                "image_quality": image_quality,
                "max_file_size": app.config.get('MAX_CONTENT_LENGTH', 0),
                "upload_folder": app.config['UPLOAD_FOLDER'],
                "output_folder": app.config['OUTPUT_FOLDER']
            },
            "statistics": stats
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/status')
def system_status():
    """System status dashboard."""
    try:
        import sys
        import platform
        import flask
        
        stats = get_folder_stats()
        uptime = datetime.now().strftime("%H:%M:%S")  # Simplified uptime
        
        status_data = {
            'uptime': uptime,
            'total_files': stats.get('total_files', 0),
            'success_rate': 95,  # Placeholder - could be calculated from logs
            'disk_usage': formatFileSize(stats.get('total_size', 0)),
            'version': APP_VERSION,
            'max_upload_size': '500MB',
            'image_format': 'PNG' if convert_to_png else 'JPEG',
            'image_quality': image_quality,
            'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            'flask_version': flask.__version__,
            'last_restart': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'upload_dir': app.config['UPLOAD_FOLDER'],
            'output_dir': app.config['OUTPUT_FOLDER'],
            'log_level': 'INFO',
            'debug_mode': app.debug,
            'auto_backup': False,  # Placeholder
            'avg_processing_time': '2.3s',  # Placeholder
            'files_per_hour': '25',  # Placeholder
            'memory_usage': '45MB',  # Placeholder
            'cpu_usage': '12%',  # Placeholder
            'recent_logs': [
                f"[{datetime.now().strftime('%H:%M:%S')}] System status requested",
                f"[{datetime.now().strftime('%H:%M:%S')}] Total files processed: {stats.get('total_files', 0)}",
                f"[{datetime.now().strftime('%H:%M:%S')}] Application running normally"
            ]
        }
        
        return render_template('status.html', **status_data)
    except Exception as e:
        logger.error(f"Error loading status page: {str(e)}")
        return render_template('error.html', 
            message=f"Error loading system status: {str(e)}"), 500

# Error handlers
@app.errorhandler(413)
def too_large(e):
    return jsonify({"error": "File too large. Maximum file size is 500MB."}), 413

@app.errorhandler(404)
def not_found(e):
    return render_template('error.html', 
        message="The requested page or resource was not found."), 404

@app.errorhandler(500)
def internal_error(e):
    logger.error(f"Internal server error: {str(e)}")
    return render_template('error.html', 
        message="An internal server error occurred. Please try again later."), 500

if __name__ == '__main__':
    logger.info(f"Starting {APP_NAME} v{APP_VERSION}")
    logger.info(f"Upload folder: {app.config['UPLOAD_FOLDER']}")
    logger.info(f"Output folder: {app.config['OUTPUT_FOLDER']}")
    app.run(host='0.0.0.0', port=80, debug=False)