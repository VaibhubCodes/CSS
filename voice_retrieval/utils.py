from rest_framework.response import Response
from rest_framework import status
from functools import wraps
from rest_framework.response import Response

def api_response(data=None, message=None, errors=None, status_code=status.HTTP_200_OK):
    response = {
        'status': 'success' if status_code < 400 else 'error',
        'message': message,
        'data': data,
        'errors': errors
    }
    
    # Remove None values
    response = {k: v for k, v in response.items() if v is not None}
    
    return Response(response, status=status_code)


def mobile_api_view(view_func):
    """
    Decorator for mobile API views to standardize response format
    """
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        try:
            response = view_func(request, *args, **kwargs)
            
            # If it's already a Response object, get its data
            if isinstance(response, Response):
                data = response.data
                status_code = response.status_code
                
                # Check if it's already in our format
                if isinstance(data, dict) and 'success' in data:
                    return response
                
                # Format response based on status code
                success = status_code < 400
                
                formatted_response = {
                    'success': success,
                    'data': data
                }
                
                # If not successful and there's error info, include it
                if not success and isinstance(data, dict) and 'detail' in data:
                    formatted_response['error'] = data['detail']
                
                return Response(formatted_response, status=status_code)
            
            # If it's a regular value, wrap it
            return Response({
                'success': True,
                'data': response
            })
            
        except Exception as e:
            # Handle unexpected errors
            return Response({
                'success': False,
                'error': str(e)
            }, status=500)
            
    return wrapped_view

def custom_exception_handler(exc, context):
    from rest_framework.views import exception_handler  # Lazy import
    response = exception_handler(exc, context)
    return response

def custom_exception_handler(exc, context):
    """
    Custom exception handler for DRF that formats errors consistently.
    """
    from rest_framework.views import exception_handler
    from rest_framework.exceptions import APIException, ValidationError
    
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)
    
    # If this is a CSRF error but the view has @csrf_exempt, we should ignore it
    if hasattr(exc, 'detail') and 'CSRF Failed' in str(exc.detail):
        request = context.get('request')
        if hasattr(request, '_dont_enforce_csrf_checks') and request._dont_enforce_csrf_checks:
            # This is a CSRF error that should be ignored
            from rest_framework.response import Response
            return Response({'success': True, 'data': None}, status=200)
    
    # If we have a response (a handled exception), format it
    if response is not None:
        data = response.data
        response.data = {}
        response.data['success'] = False
        
        if isinstance(data, dict):
            # For validation errors and other dict-based errors
            if 'detail' in data:
                response.data['error'] = data['detail']
            else:
                response.data['errors'] = data
        elif isinstance(data, list):
            # For list-based errors
            response.data['errors'] = data
        else:
            # For string errors
            response.data['error'] = str(data)
    
    return response

def custom_exception_handler(exc, context):
    from rest_framework.views import exception_handler  # Lazy import
    response = exception_handler(exc, context)
    return response
