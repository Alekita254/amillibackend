from rest_framework.response import Response

def custom_response(success=True, message="", data=None, status_code=200):
    return Response(
        {
            "success": success,
            "message": message,
            "data": data
        },
        status=status_code
    )
