# MHT to Markdown Converter - Web Application

A modern, beautiful web application for converting Windows Step Recorder MHT files to Markdown format with image extraction and enhanced viewing capabilities.

## ✨ Features

- 🎯 **Drag & Drop Interface** - Modern, intuitive file upload
- 🖼️ **Image Processing** - Extracts and converts images from MHT files  
- 📝 **Markdown Generation** - Creates clean, well-formatted documentation
- 🌐 **Web Viewer** - Beautiful HTML preview with image zoom
- 📦 **Bulk Operations** - Download all processed files as ZIP
- 🔄 **Real-time Processing** - Progress indicators and status updates
- 🎨 **Modern UI** - Responsive design with gradient themes
- 🐳 **Docker Ready** - Easy deployment with Docker

## 🚀 Quick Start

### Using Docker Compose (Recommended)

1. **Clone or download** this repository
2. **Navigate** to the `Docker_Build` directory
3. **Run the build script**:

   **Windows:**
   ```cmd
   build.bat
   ```

   **Linux/Mac:**
   ```bash
   chmod +x build.sh
   ./build.sh
   ```

4. **Access** the application at [http://localhost:5674](http://localhost:5674)

### Manual Docker Build

```bash
# Build the image
docker build -t mht2md:latest .

# Run the container
docker run -d -p 5674:80 --name mht2md-webapp mht2md:latest
```

### Using Docker Compose Manually

```bash
# Start the application
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the application
docker-compose down
```

## 🛠️ Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FLASK_ENV` | `production` | Flask environment |
| `PYTHONUNBUFFERED` | `1` | Enable Python output buffering |

### Volume Mounts

- `/app/uploads` - Temporary file storage
- `/app/outputs` - Processed file output

### Port Configuration

- **Default Port:** 5674 (mapped to container port 80)
- **Health Check:** Available at `/health` endpoint

## 📁 Project Structure

```
Docker_Build/
├── app.py                 # Main Flask application
├── Dockerfile            # Docker image configuration
├── docker-compose.yml    # Docker Compose configuration
├── requirements.txt      # Python dependencies
├── build.sh             # Linux/Mac build script
├── build.bat            # Windows build script
├── templates/
│   ├── index.html       # Main interface
│   └── error.html       # Error page
└── README.md           # This file
```

## 🎨 User Interface

### Main Features
- **Gradient Background** - Modern visual design
- **File Drag & Drop** - Intuitive file upload
- **Progress Indicators** - Real-time processing feedback
- **Responsive Design** - Works on desktop and mobile
- **Bootstrap Integration** - Professional styling

### Supported Operations
- ✅ Upload MHT files (up to 100MB)
- ✅ Convert to Markdown with images
- ✅ View generated documentation
- ✅ Download individual results
- ✅ Download all files as ZIP
- ✅ Browse output directory
- ✅ Clear all data

## 🔧 API Endpoints

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

## 🐳 Docker Details

### Image Information
- **Base Image:** `python:3.9-slim`
- **Size:** ~200MB (optimized)
- **Architecture:** Multi-platform support
- **Security:** Non-root user execution

### Health Checks
The container includes built-in health checks:
- **Interval:** 30 seconds
- **Timeout:** 10 seconds
- **Retries:** 3 attempts

### Performance Optimizations
- ✅ Multi-stage build process
- ✅ Layer caching optimization
- ✅ Minimal system dependencies
- ✅ Python package optimization

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

### Code Structure
- **Flask Backend** - RESTful API for file processing
- **Bootstrap Frontend** - Responsive user interface
- **Image Processing** - PIL/Pillow for image conversion
- **Markdown Generation** - BeautifulSoup for HTML parsing

## 📊 Monitoring

### Health Check
Monitor application health at: `http://localhost:5674/health`

Response includes:
- Application status
- Configuration details
- Feature flags
- Timestamp information

### Logs
View application logs:
```bash
docker-compose logs -f mht2md
```

## 🚨 Troubleshooting

### Common Issues

**Application won't start:**
- Check if port 5674 is available
- Verify Docker is running
- Check container logs

**File upload fails:**
- Ensure file is valid MHT format
- Check file size (max 100MB)
- Verify disk space

**Processing errors:**
- Check file format integrity
- Review application logs
- Ensure sufficient memory

### Log Analysis
```bash
# View recent logs
docker logs mht2md-webapp --tail 50

# Follow logs in real-time
docker logs mht2md-webapp -f

# View all container information
docker inspect mht2md-webapp
```

## 📄 License

This project is part of the MHT2MD converter suite by Kevin C. Jones.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📞 Support

- **GitHub:** [https://github.com/jonesckevin/mht2md.git](https://github.com/jonesckevin/mht2md.git)
- **Email:** jonesckevin@proton.me

---

*Built with ❤️ using Flask, Docker, and Bootstrap*
