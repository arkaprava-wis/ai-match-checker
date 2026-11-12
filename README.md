# Math Table Checker - Django Web Application

A modern web application that uses Google's Gemini AI to automatically check math table answers from uploaded images.

## Features

- 🖼️ **Image Upload**: Drag & drop or click to upload math table images
- 🤖 **AI Processing**: Uses Google Gemini AI for OCR and number extraction
- ✅ **Automatic Checking**: Calculates column sums and compares with given answers
- 📊 **Detailed Results**: Shows Right/Wrong status for each column with statistics
- 📱 **Responsive Design**: Works perfectly on desktop, tablet, and mobile devices
- 📁 **Export Results**: Download results as CSV file
- 🎨 **Modern UI**: Clean, professional interface with animations

## Screenshots

*Upload your math table images easily with our modern interface*

## Installation

### Prerequisites

- Python 3.8+
- pip package manager

### Setup

1. **Clone or extract the project**
   ```bash
   cd math_checker_django
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv

   # On Windows
   venv\Scripts\activate

   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure API Key**
   - Copy `.env.example` to `.env`
   - Get your Gemini API key from [Google AI Studio](https://aistudio.google.com/)
   - Add your API key to `.env`:
     ```
     GEMINI_API_KEY=your-actual-api-key-here
     ```

5. **Setup Database**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

6. **Create Admin User** (optional)
   ```bash
   python manage.py createsuperuser
   ```

7. **Run Development Server**
   ```bash
   python manage.py runserver
   ```

8. **Open in Browser**
   Visit: http://127.0.0.1:8000/

## Usage

1. **Upload Image**: Navigate to the homepage and upload a math table image
2. **Analyze**: Click "Start Analysis" to process the image with AI
3. **View Results**: See detailed results showing Right/Wrong for each column
4. **Export**: Download results as CSV for record keeping

## Supported Image Formats

- PNG
- JPG/JPEG
- Maximum file size: 10MB

## API Configuration

This application requires a Google Gemini API key. To get one:

1. Go to [Google AI Studio](https://aistudio.google.com/)
2. Sign in with your Google account
3. Create a new API key
4. Add the key to your `.env` file

### API Usage Notes

- The free tier includes generous limits for testing
- Processing time: 30-60 seconds per image
- Rate limiting is built-in to respect API limits

## Project Structure

```
math_checker_django/
├── math_checker/          # Django project settings
│   └── math_checker/
│       ├── settings.py    # Main configuration
│       ├── urls.py        # URL routing
│       └── wsgi.py        # WSGI config
├── checker/               # Main Django app
│   ├── models.py         # Database models
│   ├── views.py          # View logic with Gemini AI
│   ├── forms.py          # Form definitions
│   ├── urls.py           # App URL routing
│   └── admin.py          # Admin interface
├── templates/            # HTML templates
│   └── checker/
│       ├── base.html     # Base template
│       ├── upload.html   # Upload page
│       ├── analyze.html  # Analysis page
│       └── results.html  # Results page
├── static/              # CSS, JS, Images
│   ├── css/style.css    # Custom styles
│   └── js/app.js        # JavaScript functionality
├── media/               # Uploaded files (created automatically)
├── requirements.txt     # Python dependencies
└── manage.py           # Django management script
```

## Development

### Adding New Features

1. **Models**: Modify `checker/models.py` for database changes
2. **Views**: Add new views in `checker/views.py`
3. **Templates**: Create HTML templates in `templates/checker/`
4. **Static Files**: Add CSS/JS to `static/` directory

### Running Tests

```bash
python manage.py test
```

### Database Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

## Deployment

### Production Settings

1. Set `DEBUG = False` in settings.py
2. Configure `ALLOWED_HOSTS`
3. Set up proper database (PostgreSQL recommended)
4. Configure static files serving
5. Set secure `SECRET_KEY`

### Environment Variables

Create a `.env` file with:

```env
SECRET_KEY=your-production-secret-key
DEBUG=False
ALLOWED_HOSTS=yourdomain.com
GEMINI_API_KEY=your-gemini-api-key
DATABASE_URL=your-database-url
```

## Troubleshooting

### Common Issues

1. **API Key Error**: Make sure your Gemini API key is correctly set in `.env`
2. **Import Error**: Ensure all dependencies are installed with `pip install -r requirements.txt`
3. **Database Error**: Run migrations with `python manage.py migrate`
4. **File Upload Error**: Check file permissions in the `media/` directory

### Support

For issues and questions:
1. Check the console logs for detailed error messages
2. Verify your API key has sufficient quota
3. Ensure uploaded images are clear and contain readable numbers

## License

This project is created for educational purposes. Please ensure you comply with Google's Gemini API terms of service.

## Acknowledgments

- Google Gemini AI for OCR capabilities
- Django framework for web development
- Bootstrap for UI components
- Font Awesome for icons

---

**Note**: This application processes images using Google's Gemini AI service. Please ensure your images don't contain sensitive information.
