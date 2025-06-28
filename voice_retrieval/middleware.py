

class MobileAPICsrfExemptMiddleware:
    """
    Middleware to exempt mobile API routes from CSRF protection
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if the request is for a mobile API endpoint
        if request.path.startswith('/auth/api/mobile/') or \
            request.path.startswith('/file_management/api/mobile/') or \
            request.path.startswith('/storage/api/mobile/') or \
            request.path.startswith('/payment/api/mobile/') or \
            request.path.startswith('/voice/api/mobile/') or \
            request.path.startswith('/password_management/api/'):
            # Mark the request as CSRF exempt
            setattr(request, '_dont_enforce_csrf_checks', True)
        
        response = self.get_response(request)
        return response
    

class MobileAuthenticationMiddleware:
    """
    Middleware to handle various authentication header formats
    from the React Native app
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check for different auth header formats
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        
        if auth_header:
            # Handle different token formats
            if auth_header.startswith('Bearer '):
                # Already in the correct format
                pass
            elif auth_header.startswith('Token '):
                # Convert from Token to Bearer format
                token = auth_header.split(' ')[1]
                request.META['HTTP_AUTHORIZATION'] = f'Bearer {token}'
            elif len(auth_header.split(' ')) == 1:
                # Just a raw token without prefix
                request.META['HTTP_AUTHORIZATION'] = f'Bearer {auth_header}'
        
        # Also check if token is in a custom header or cookies
        token = request.META.get('HTTP_X_AUTH_TOKEN') or request.COOKIES.get('auth_token')
        if token and not auth_header:
            request.META['HTTP_AUTHORIZATION'] = f'Bearer {token}'
            
        response = self.get_response(request)
        return response
    

