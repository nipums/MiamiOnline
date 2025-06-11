from django.utils import timezone
from .models import UserProfile, Ban
from django.shortcuts import redirect
from django.urls import reverse

class BanCheckMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Исключаем страницу бана, статические файлы и API из проверки
        excluded_paths = [
            reverse('banned_page'),
            '/static/',
            '/media/',
            '/admin/',
            '/api/',
            '/logout/'
        ]
        
        if any(request.path.startswith(path) for path in excluded_paths):
            return self.get_response(request)

        if request.user.is_authenticated:
            try:
                ban = Ban.objects.get(user=request.user, is_active=True)
                if ban.expires_at is None or ban.expires_at > timezone.now():
                    # Перенаправляем на страницу бана только если мы еще не на ней
                    if not request.path == reverse('banned_page'):
                        return redirect('banned_page')
            except Ban.DoesNotExist:
                pass
        
        return self.get_response(request)


class OnlineStatusMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            profile, created = UserProfile.objects.get_or_create(user=request.user)
            profile.last_activity = timezone.now()
            profile.save(update_fields=['last_activity'])
        
        response = self.get_response(request)
        return response