# Use absolute import from the app name
from portfolio.models import Notification

def unread_notifications(request):
    """
    Adds the count of unread notifications to the template context
    for authenticated users.
    """
    count = 0
    if request.user.is_authenticated:
        try:
            count = Notification.objects.filter(user=request.user, is_read=False).count()
        except Exception as e:
            print(f"Error fetching notification count for user {request.user.id}: {e}")
            count = 0
    return {'unread_notification_count': count}