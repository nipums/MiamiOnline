from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import os

def user_avatar_path(instance, filename):
    # Файл будет загружен в MEDIA_ROOT/user_<id>/avatar/<filename>
    return f'user_{instance.user.id}/avatar/{filename}'

class Ban(models.Model):
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='ban',
        verbose_name="Пользователь"
    )
    reason = models.TextField(verbose_name="Причина")
    banned_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='bans_given',
        verbose_name="Забанен"
    )
    banned_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата бана")
    expires_at = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name="Истекает"
    )
    is_active = models.BooleanField(default=True, verbose_name="Активен")

    class Meta:
        verbose_name = "Бан"
        verbose_name_plural = "Баны"
        db_table = "chat_bans"  # Явно указываем имя таблицы

    def __str__(self):
        return f"Бан {self.user.username} ({'активен' if self.is_active else 'неактивен'})"

    @property
    def is_permanent(self):
        return self.expires_at is None

    @property
    def remaining_time(self):
        if not self.is_active:
            return "истёк"
        if self.is_permanent:
            return "перманентно"
        remaining = self.expires_at - timezone.now()
        if remaining.total_seconds() <= 0:
            self.is_active = False
            self.save()
            return "истёк"
        days = remaining.days
        hours, remainder = divmod(remaining.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        return f"{days}д {hours}ч {minutes}м"

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to=user_avatar_path, null=True, blank=True)
    bio = models.TextField(max_length=500, blank=True)
    last_activity = models.DateTimeField(default=timezone.now)

    def is_online(self):
        if not self.last_activity:
            return False
        delta = timezone.now() - self.last_activity
        return delta.total_seconds() < 10  # 10 seconds

    def __str__(self):
        return f"{self.user.username}'s profile"
    
    def get_avatar_url(self):
        if self.avatar and hasattr(self.avatar, 'url'):
            return self.avatar.url
        return '/static/chat/img/default_avatar.png'


# chat/models.py
class ChatRoom(models.Model):
    name = models.CharField(max_length=100)
    members = models.ManyToManyField(User, related_name='chat_rooms')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_rooms')
    created_at = models.DateTimeField(auto_now_add=True)
    is_global = models.BooleanField(default=False)  # Добавляем это поле
    
    class Meta:
        ordering = ['-created_at']

class Invitation(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='invitations')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_invitations')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_invitations')
    created_at = models.DateTimeField(auto_now_add=True)
    is_accepted = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ('room', 'recipient')  # Одно приглашение на комнату для пользователя

class Message(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        related_name='sent_messages'
    )
    content = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    file = models.FileField(upload_to='chat_files/%Y/%m/%d/', blank=True, null=True)
    file_name = models.CharField(max_length=255, blank=True, null=True)
    is_visible = models.BooleanField(default=True)  # Добавьте это поле
    deleted_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='deleted_messages'
    )

    def __str__(self):
        return f"{self.sender}: {self.content[:20] if self.content else 'File'}..."

    def get_file_icon(self):
        if not self.file:
            return None
        ext = os.path.splitext(self.file.name)[1].lower()
        icons = {
            '.pdf': 'fa-file-pdf',
            '.doc': 'fa-file-word',
            '.docx': 'fa-file-word',
            '.xls': 'fa-file-excel',
            '.xlsx': 'fa-file-excel',
            '.jpg': 'fa-file-image',
            '.jpeg': 'fa-file-image',
            '.png': 'fa-file-image',
            '.gif': 'fa-file-image',
            '.zip': 'fa-file-archive',
            '.rar': 'fa-file-archive',
            '.mp3': 'fa-file-audio',
            '.mp4': 'fa-file-video',
        }
        return icons.get(ext, 'fa-file')