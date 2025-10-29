# PaperBites: Open Access Research Paper to TikTok Video Converter

PaperBites is an application that converts academic research papers into engaging short-form videos suitable for platforms like TikTok, Instagram, and YouTube. It uses AI to extract key information and generate visually appealing videos with voiceovers and relevant visuals.

## Important Updates

This version includes significant improvements to the paper retrieval system:
- Integration with multiple free, open APIs (arXiv, OpenAlex, Semantic Scholar)
- Proper license checking for public display
- Enhanced error handling
- Better fallback mechanisms

## Installation

### Prerequisites

- Python 3.7 or higher
- FFmpeg (for video processing)
- Tesseract OCR (for PDF text extraction)

### Install from source

```bash
# Clone the repository
git clone https://github.com/yourusername/paperbites.git
cd paperbites

# Install dependencies
pip install -r requirements.txt

# Install the package
pip install -e .
```

## Usage

### Command Line Interface

Search for papers and create videos:

```bash
# Search for papers on a topic and convert to videos
python cli.py search "machine learning" --papers 3

# Process a specific paper by arXiv ID
python cli.py id 2104.08653

# Process a specific paper by DOI
python cli.py id 10.1145/3458817.3476195

# Process a local PDF
python cli.py pdf my_paper.pdf
```

### API Server

Start the API server to browse and search for papers:

```bash
# Start the server
python api_server.py
```

The API will be available at http://localhost:8000 with the following endpoints:

- GET `/api/videos` - List all videos
- GET `/api/videos/{video_id}` - Get a specific video
- GET `/api/topics` - List popular topics
- GET `/api/search?query=keyword` - Search for papers
- GET `/api/paper/{paper_id}` - Get paper information

## Configuration

Edit `config.json` to customize behavior:

```json
{
  "api": {
    "pexels_key": "YOUR_PEXELS_API_KEY",
    "email": "your-email@example.com"
  },
  "paper_search": {
    "sources": [
      "arxiv",
      "openalex",
      "semantic_scholar"
    ],
    "max_papers": 3,
    "open_access_only": true
  },
  "video": {
    "formats": {
      "tiktok": {"width": 1080, "height": 1920},
      "instagram": {"width": 1080, "height": 1080},
      "youtube": {"width": 1920, "height": 1080}
    },
    "default_format": "tiktok",
    "fps": 30
  },
  "storage": {
    "cloudinary": {
      "cloud_name": "",
      "api_key": "",
      "api_secret": ""
    }
  },
  "paths": {
    "temp_dir": "temp_assets",
    "output_dir": "videos",
    "tesseract_cmd": "path/to/tesseract" 
  }
}
```

## API Requirements

1. **Email for APIs**: The application uses APIs that benefit from having a valid email address for "polite pool" access. You must provide a valid email address in the config file.

2. **All APIs are Free and Unrestricted**: This version uses only free, unrestricted APIs that do not have commercial limitations:
   - arXiv API (academic papers in physics, math, CS, etc.)
   - OpenAlex API (comprehensive open access scholarly materials)
   - Semantic Scholar API (AI-enhanced research paper access)

3. **Pexels API Key (Optional)**: For stock videos and images, obtain a free API key from [Pexels](https://www.pexels.com/api/).

## License Compliance

PaperBites is designed to respect copyright and licensing:

1. It only processes and displays papers with appropriate open access licenses that allow redistribution.
2. Papers are checked against the following licenses:
   - Creative Commons (CC-BY, CC0, CC-BY-SA)
   - Open Access specific licenses
   - Public Domain
   - arXiv default license

For public display, proper attribution is always included.

## Supported Paper IDs

The system can retrieve papers using multiple ID formats:
- arXiv IDs (e.g., "2104.08653")
- DOIs (e.g., "10.1145/3458817.3476195")
- Semantic Scholar IDs (with "SS-" prefix)
- OpenAlex IDs (usually starting with "W")

## Troubleshooting

If you encounter issues:

1. Check that all dependencies are installed
2. Verify that FFmpeg and Tesseract are in your PATH
3. Ensure your email is correctly set in `config.json`
4. Check the logs in the `logs` directory

For more help, please open an issue on GitHub.