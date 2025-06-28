from django import template
from urllib.parse import urlparse

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Gets an item from a dictionary safely"""
    return dictionary.get(key, 0) 

@register.filter
def domain_only(url):
    """Extract just the domain from a URL"""
    if not url:
        return ""
    
    # Add scheme if not present
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
        
    # Parse and return just the domain
    parsed = urlparse(url)
    return parsed.netloc

@register.filter
def ensure_https(url):
    """Make sure URL starts with https"""
    if not url:
        return ""
        
    # Add scheme if not present
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    # Convert http to https
    if url.startswith('http://'):
        url = 'https://' + url[7:]
        
    return url 