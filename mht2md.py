# Import necessary modules
import os  # For file and directory operations
import email  # For parsing html/text from MHT files
import re  # For extracting and cleaning step text using regular expressions
import sys  # For system-specific parameters and functions
import argparse  # For command-line argument parsing
import logging  # For enhanced logging
import json  # For configuration and metadata
from pathlib import Path  # For modern path handling
from email import policy  # For handling email parsing policies
from bs4 import BeautifulSoup  # For parsing and manipulating HTML content
from PIL import Image  # For image conversion
import subprocess  # For running external scripts
from datetime import datetime  # For adding timestamps
import io  # For handling byte streams
from typing import Dict, List, Tuple, Optional  # For type hints
import zipfile  # For creating archives
import shutil  # For file operations

# Application metadata
__author__ = "Kevin C. Jones"
__email__ = "jonesckevin@proton.me"
__site__ = "https://github.com/jonesckevin/mht2md.git"
__version__ = "2.0.0"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('mht2md.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

def print_banner():
    """Print application banner with styling."""
    banner = rf"""
{'='*80}
  __  __ _   _ _____   _____    __  __       _         _                      
 |  \/  | | | |_   _| |_   _|__|  \/  | __ _| |_ _ __ | | _____ ___  ___ _ __ 
 | |\/| | |_| | | |     | ||__||  \/  |/ _` | __| '_ \| |/ / __/ _ \/ _ \ '__|
 | |  | |  _  | | |     | |     | |  | | (_| | |_| | | |   < (_| (_) \__/ |   
 |_|  |_|_| |_| |_|     |_|     |_|  |_|\__,_|\__|_| |_|_|\_\___\___/____/|_|   
                                                                              
{'='*80}
📄 Windows Step Recorder (.mht) to Markdown Converter
📧 Author: {__author__}
📧 Email: {__email__}
🌐 Site: {__site__}
🔖 Version: {__version__}
{'='*80}
"""
    print(banner)
    logger.info(f"MHT2MD Converter v{__version__} started")

class MHTConverter:
    """Enhanced MHT to Markdown converter with better error handling and features."""
    
    def __init__(self, convert_to_png: bool = False, output_quality: int = 95):
        """
        Initialize the converter.
        
        Args:
            convert_to_png (bool): Whether to convert images to PNG format
            output_quality (int): JPEG quality for output images (1-100)
        """
        self.convert_to_png = convert_to_png
        self.output_quality = max(1, min(100, output_quality))
        self.stats = {
            'files_processed': 0,
            'files_success': 0,
            'files_failed': 0,
            'total_images': 0,
            'total_steps': 0
        }
        
        logger.info(f"🎨 Converter initialized:")
        logger.info(f"   Convert to PNG: {'✅ Yes' if convert_to_png else '❌ No (keeping JPEG)'}")
        logger.info(f"   Image Quality: {self.output_quality}%")
    
    def extract_images_and_convert_to_md(self, mht_file: str) -> str:
        """
        Extract images and convert MHT file to Markdown with enhanced error handling.
        
        Args:
            mht_file (str): Path to the MHT file
        
        Returns:
            str: Path to the output directory containing converted files
        """
        mht_path = Path(mht_file)
        if not mht_path.exists():
            raise FileNotFoundError(f"MHT file not found: {mht_file}")
        
        logger.info(f"📁 Processing: {mht_path.name}")
        
        try:
            # Create output directory
            base_name = mht_path.stem
            output_dir = mht_path.parent / base_name
            output_dir.mkdir(exist_ok=True)
            logger.info(f"📂 Output directory: {output_dir}")

            # Parse MHT file
            with open(mht_file, 'rb') as f:
                msg = email.message_from_binary_file(f, policy=policy.default)

            # Extract HTML content
            html_part = self._extract_html_content(msg)
            soup = BeautifulSoup(html_part, 'html.parser')

            # Extract images
            image_count = self._extract_images(msg, output_dir)
            
            # Extract step text
            steps_text = self._extract_step_text(soup)
            
            # Generate markdown
            markdown_content = self._generate_markdown(base_name, mht_path.name, steps_text)
            
            # Save markdown file
            md_file_path = output_dir / f'{base_name}.md'
            md_file_path.write_text(markdown_content, encoding='utf-8')
            
            # Create metadata file
            self._create_metadata(output_dir, mht_path.name, image_count, len(steps_text))
            
            # Update statistics
            self.stats['files_success'] += 1
            self.stats['total_images'] += image_count
            self.stats['total_steps'] += len(steps_text)
            
            logger.info(f"✅ Processing completed successfully!")
            logger.info(f"   📄 Markdown: {md_file_path.name}")
            logger.info(f"   🖼️  Images: {image_count}")
            logger.info(f"   📝 Steps: {len(steps_text)}")
            logger.info(f"   📁 Output: {output_dir}")
            
            return str(output_dir)

        except Exception as e:
            self.stats['files_failed'] += 1
            logger.error(f"❌ Error processing {mht_path.name}: {str(e)}")
            
            # Clean up on error
            if output_dir.exists():
                shutil.rmtree(output_dir)
                logger.info(f"🧹 Cleaned up incomplete output directory")
            
            raise e
        finally:
            self.stats['files_processed'] += 1
    
    def _extract_html_content(self, msg) -> str:
        """Extract HTML content from email message."""
        html_part = next(
            (part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8', errors='ignore')
             for part in msg.walk() if part.get_content_type() == 'text/html'), 
            None
        )
        if not html_part:
            raise ValueError("❌ No HTML part found in the MHT file")
        return html_part
    
    def _extract_images(self, msg, output_dir: Path) -> int:
        """Extract images from MHT message."""
        logger.info(f"🖼️  Extracting images...")
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
                logger.info(f"  💾 Saved: {image_filename}")
                image_count += 1
        
        logger.info(f"✅ Extracted {image_count} images")
        return image_count
    
    def _extract_step_number(self, content_location: Optional[str], default: int) -> int:
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
                # Enhance image quality
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                img.save(image_path, 'PNG', optimize=True)
        else:
            # Save as original format, but optimize JPEG quality
            if content_type in ['image/jpeg', 'image/jpg'] and not self.convert_to_png:
                with Image.open(io.BytesIO(image_data)) as img:
                    img.save(image_path, 'JPEG', quality=self.output_quality, optimize=True)
            else:
                image_path.write_bytes(image_data)
    
    def _extract_step_text(self, soup) -> Dict[int, str]:
        """Extract step text from HTML content."""
        logger.info(f"📝 Extracting step text...")
        steps_text = {}
        
        for text in soup.stripped_strings:
            match = re.match(r'^Step (\d+):', text)
            if match and not re.search(r'\(?\d{2}/\d{2}/\d{4} \d{1,2}:\d{2}:\d{2} [APM]{2}\)?', text):
                step_number = int(match.group(1))
                clean_text = re.sub(
                    r'^Step \d+:|\(?\d{2}/\d{2}/\d{4} \d{1,2}:\d{2}:\d{2} [APM]{2}\)?|[^\x00-\x7F]+', 
                    '', text
                ).strip()
                
                if clean_text:  # Only add non-empty text
                    if step_number in steps_text:
                        steps_text[step_number] += ' ' + clean_text
                    else:
                        steps_text[step_number] = clean_text
        
        logger.info(f"✅ Found {len(steps_text)} steps with content")
        return steps_text
    
    def _generate_markdown(self, base_name: str, original_filename: str, steps_text: Dict[int, str]) -> str:
        """Generate enhanced markdown content."""
        extension = '.png' if self.convert_to_png else '.JPEG'
        
        content = [
            f"# {base_name} - Step Recorder Documentation",
            "",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ",
            f"**Original File:** `{original_filename}`  ",
            f"**Total Steps:** {len(steps_text)}  ",
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
            f"This documentation was automatically generated from a Windows Step Recorder file using **MHT2MD Converter v{__version__}**.",
            "",
            f"- **Generated on:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"- **Converter:** [MHT2MD]({__site__})",
            f"- **Author:** {__author__}",
            ""
        ])
        
        return "\n".join(content)
    
    def _create_metadata(self, output_dir: Path, original_filename: str, image_count: int, step_count: int):
        """Create metadata file for the conversion."""
        metadata = {
            "conversion_info": {
                "original_file": original_filename,
                "converted_on": datetime.now().isoformat(),
                "converter_version": __version__,
                "image_format": "PNG" if self.convert_to_png else "JPEG",
                "image_quality": self.output_quality if not self.convert_to_png else 100
            },
            "statistics": {
                "total_images": image_count,
                "total_steps": step_count
            },
            "files": {
                "markdown": f"{output_dir.name}.md",
                "images": [f"screenshot{i:04d}.{'png' if self.convert_to_png else 'JPEG'}" 
                          for i in range(1, image_count + 1)]
            }
        }
        
        metadata_path = output_dir / "conversion_metadata.json"
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding='utf-8')

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Convert Windows Step Recorder (.mht) files to Markdown format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  {sys.argv[0]}                          # Convert all .mht files in current directory
  {sys.argv[0]} --png                    # Convert with PNG image format
  {sys.argv[0]} --quality 85            # Set JPEG quality to 85%
  {sys.argv[0]} --input file.mht        # Convert specific file
  {sys.argv[0]} --output ./converted    # Set output directory
  {sys.argv[0]} --zip                   # Create ZIP archives
  {sys.argv[0]} --no-resize-prompt      # Skip resize prompt
        """
    )
    
    parser.add_argument('--version', action='version', version=f'MHT2MD v{__version__}')
    parser.add_argument('--input', '-i', help='Specific MHT file to convert')
    parser.add_argument('--output', '-o', help='Output directory (default: same as input)')
    parser.add_argument('--png', action='store_true', help='Convert images to PNG format')
    parser.add_argument('--quality', type=int, default=95, help='JPEG quality 1-100 (default: 95)')
    parser.add_argument('--zip', action='store_true', help='Create ZIP archives of output')
    parser.add_argument('--no-resize-prompt', action='store_true', help='Skip resize script prompt')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    return parser.parse_args()

def create_zip_archive(output_dir: Path) -> Path:
    """Create a ZIP archive of the output directory."""
    zip_path = output_dir.with_suffix('.zip')
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in output_dir.rglob('*'):
            if file_path.is_file():
                arcname = file_path.relative_to(output_dir.parent)
                zipf.write(file_path, arcname)
    return zip_path

def main():
    """Main application entry point."""
    args = parse_arguments()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    print_banner()
    
    # Initialize converter
    converter = MHTConverter(
        convert_to_png=args.png,
        output_quality=args.quality
    )
    
    try:
        # Determine input files
        if args.input:
            if not Path(args.input).exists():
                logger.error(f"❌ Input file not found: {args.input}")
                return 1
            mht_files = [args.input]
            working_folder = Path(args.input).parent
        else:
            working_folder = Path.cwd()
            mht_files = list(working_folder.glob('*.mht'))
        
        if not mht_files:
            logger.error("❌ No MHT files found.")
            logger.info(f"📁 Working folder: {working_folder}")
            logger.info("💡 Please place your MHT files in the current directory or specify with --input")
            return 1
        
        logger.info(f"📁 Working folder: {working_folder}")
        logger.info(f"🔍 Found {len(mht_files)} MHT file(s):")
        for mht_file in mht_files:
            logger.info(f"  • {Path(mht_file).name}")
        
        output_dirs = []
        
        # Process each MHT file
        for mht_file in mht_files:
            try:
                output_dir = converter.extract_images_and_convert_to_md(str(mht_file))
                output_dirs.append(Path(output_dir))
                
                # Create ZIP if requested
                if args.zip:
                    zip_path = create_zip_archive(Path(output_dir))
                    logger.info(f"📦 Created archive: {zip_path.name}")
                    
            except Exception as e:
                logger.error(f"❌ Failed to process {Path(mht_file).name}: {str(e)}")
        
        # Print summary
        stats = converter.stats
        logger.info(f"\n{'='*80}")
        logger.info(f"📊 CONVERSION SUMMARY:")
        logger.info(f"✅ Successful: {stats['files_success']}")
        logger.info(f"❌ Failed: {stats['files_failed']}")
        logger.info(f"📁 Total files: {stats['files_processed']}")
        logger.info(f"🖼️  Total images: {stats['total_images']}")
        logger.info(f"📝 Total steps: {stats['total_steps']}")
        logger.info(f"{'='*80}")
        
        # Offer resize script
        if stats['files_success'] > 0 and not args.no_resize_prompt:
            resize_script_path = working_folder / 'resize-images.py'
            if resize_script_path.exists():
                logger.info(f"\n🖼️  IMAGE PROCESSING OPTIONS:")
                response = input("Do you want to run the resize-images.py script to crop photos? (yes/no): ").strip().lower()
                if response in ['yes', 'y', 'ye', 'yeah', 'yep', 'yup', 'sure', 'ok', 'okay']:
                    try:
                        subprocess.run([sys.executable, str(resize_script_path)], check=True)
                        logger.info(f"✅ Image resizing completed!")
                    except subprocess.CalledProcessError as e:
                        logger.error(f"❌ Error running resize script: {e}")
                    except FileNotFoundError:
                        logger.error(f"❌ Python not found in PATH")
                else:
                    logger.info(f"⏭️  Skipping image resizing.")
        
        return 0 if stats['files_failed'] == 0 else 1
        
    except KeyboardInterrupt:
        logger.info(f"\n⏹️  Operation cancelled by user")
        return 1
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        if not sys.stdin.isatty():  # Not in interactive mode
            sys.exit(exit_code)
        else:
            input(f"\n🎉 Processing complete! Press Enter to exit...")
            sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n⏹️  Goodbye!")
        sys.exit(1)


