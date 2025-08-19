# MHT to Markdown Converter - Web Application

A modern, beautiful web application for converting Windows Step Recorder MHT files to Markdown format with image extraction and enhanced viewing capabilities.

## 🚀 Quick Start
**Access** the application at [http://localhost:5674](http://localhost:5674)

### Manual Docker Build

```bash
# Build the image
docker build -t mht2md:latest .

# Run the container
docker run -d -p 5674:80 --name mht2md-webapp mht2md:latest
```

### Pull Docker Hub

```bash
docker run -d -p 5674:80 --name mht2md-webapp jonesckevin/mht2md:latest
```

##  Relevant Directories

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main application interface |
| `/upload` | POST | Upload and process MHT file |
| `/view_html/<dir>` | GET | View processed Markdown as HTML |
| `/download/<dir>` | GET | Download processed files as ZIP |
| `/download_all` | GET | Download all processed files |
| `/browse_output` | GET | Browse output directory |
| `/purge` | POST | Clear all processed data |
| `/health` | GET | Health check endpoint |

## 🔧 Development

### Local Development Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the application:**
   ```bash
   export FLASK_APP=app.py
   export FLASK_ENV=development
   flask run --host=0.0.0.0 --port=5000
   ```

3. **Access:** [http://localhost:5000](http://localhost:5000)

### Logs
View application logs:
```bash
docker-compose logs -f mht2md
```
