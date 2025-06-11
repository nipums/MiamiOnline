from .models import UserProfile

def online_users(request):
    if request.user.is_authenticated:
        users = UserProfile.objects.exclude(user=request.user)
        return {'online_users': users}
    return {}