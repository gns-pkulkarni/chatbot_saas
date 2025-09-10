def normalize_site_url(url: str) -> str:
    return url.replace("https://", "").replace("http://", "").rstrip("/")

def get_file_extension(filename: str) -> str:
    """Get file extension from filename"""
    return filename.split('.')[-1].lower() if '.' in filename else ''

def is_valid_document_type(filename: str) -> bool:
    """Check if uploaded file is a supported document type"""
    valid_extensions = ['pdf', 'docx', 'doc', 'txt', 'xlsx', 'xls', 'csv']
    return get_file_extension(filename) in valid_extensions
