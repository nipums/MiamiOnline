from datetime import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.contrib import messages
from .forms import MessageForm, RegisterForm, AddUserForm, ProfileForm
from .models import ChatRoom, Message, UserProfile, Invitation, Ban
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Q
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.http import JsonResponse
from django.utils.html import escape

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def online_users_api(request):
    users = UserProfile.objects.exclude(user=request.user)
    data = [
        {
            'username': profile.user.username,
            'is_online': profile.is_online(),
            'avatar_url': profile.get_avatar_url(),
        }
        for profile in users
    ]
    return Response({'users': data})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def update_activity(request):
    UserProfile.objects.filter(user=request.user).update(
        last_activity=timezone.now()
    )
    return Response({'status': 'success'})

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone
from django.http import JsonResponse
from django.shortcuts import get_object_or_404

@login_required
def delete_message(request, message_id):
    message = get_object_or_404(Message, id=message_id)
    if request.user == message.sender or request.user == message.room.created_by:
        message.is_visible = False
        message.deleted_by = request.user
        message.save()
        
        return JsonResponse({
            'status': 'ok',
            'message_id': message.id,
            'deleted_by': request.user.username
        })
    return JsonResponse({'status': 'error'}, status=403)

@login_required
def banned_page(request):
    try:
        ban = request.user.ban
        context = {
            'reason': ban.reason,
            'banned_by': ban.banned_by.username if ban.banned_by else 'Система',
            'banned_at': ban.banned_at.strftime("%d.%m.%Y %H:%M"),
            'is_permanent': ban.is_permanent,
            'remaining_time': ban.remaining_time,
        }
        return render(request, 'chat/banned.html', context)
    except:
        return redirect('home')
    
@login_required
def leave_room(request, room_id):
    room = get_object_or_404(ChatRoom, id=room_id)
    if request.user == room.created_by:
        messages.error(request, "Creator can't leave their own room. You can only delete it.")
        return redirect('manage_room', room_id=room.id)
    if request.method == "POST":
        room.members.remove(request.user)
        messages.success(request, f'You have left the room "{room.name}".')
        return redirect('chat_rooms')  # или на главную, или куда нужно
    return redirect('manage_room', room_id=room.id)

@login_required
def invitations_list(request):
    # Получаем все приглашения текущего пользователя
    invitations = Invitation.objects.filter(
        recipient=request.user,
        is_accepted=False
    ).select_related('room', 'sender')
    
    return render(request, 'chat/invitations.html', {
        'invitations': invitations
    })

@login_required
def handle_invitation(request, invitation_id):
    invitation = get_object_or_404(Invitation, id=invitation_id, recipient=request.user)
    if request.method == "POST":
        action = request.POST.get('action')
        if action == "accept":
            invitation.is_accepted = True
            invitation.save()
            invitation.room.members.add(request.user)
            messages.success(request, f'You joined "{invitation.room.name}"')
        elif action == "decline":
            invitation.delete()
            messages.info(request, 'Invitation declined.')
        return redirect('invitations_list')
    return render(request, 'chat/handle_invitation.html', {'invitation': invitation})


@login_required
def global_chat(request):
    # Получаем или создаем общий чат
    global_room, created = ChatRoom.objects.get_or_create(
        name='Global Chat',
        defaults={
            'created_by': request.user,
            'is_global': True
        }
    )
    
    # Добавляем пользователя в участники, если его там нет
    if request.user not in global_room.members.all():
        global_room.members.add(request.user)
    
    return render(request, 'chat/room_detail.html', {
        'room': global_room,
        'messages': global_room.messages.order_by('timestamp')[:100],
    })

class MessageList(APIView):
    def get(self, request):
        room_id = request.GET.get('room_id')
        messages = Message.objects.filter(
            room_id=room_id, 
            is_visible=True  # Теперь это поле существует в модели
        ).order_by('timestamp')
            
        messages = Message.objects.filter(room_id=room_id).order_by('timestamp')
        data = [
            {
                'message_id': msg.id,
                'sender': msg.sender.username,
                'content': msg.content,
                'timestamp': msg.timestamp.isoformat(),
                'avatar_url': msg.sender.profile.get_avatar_url() if hasattr(msg.sender, 'profile') else '/static/chat/img/default_avatar.png',
                'file_url': msg.file.url if msg.file else None,
                'file_name': msg.file_name,
                'file_icon': msg.get_file_icon(),
            }
            for msg in messages
        ]
        return Response(data)
'''
def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('chat_rooms')
    else:
        form = RegisterForm()
    return render(request, 'registration/register.html', {'form': form})
'''
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings

from django.utils.http import urlsafe_base64_decode
from django.contrib.auth.tokens import default_token_generator

def activate_account(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        login(request, user)
        messages.success(request, 'Ваш аккаунт успешно активирован!')
        return redirect('chat_rooms')
    else:
        messages.error(request, 'Ссылка активации недействительна!')
        return redirect('login')

from django.utils.http import urlsafe_base64_encode
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes

def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False  # Пользователь не активен до подтверждения
            user.save()
            
            # Generate token and uid
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            # Отправка email
            subject = 'Подтверждение регистрации'
            html_message = render_to_string('registration/email_confirmation.html', {
                'user': user,
                'domain': request.get_host(),
                'uid': uid,
                'token': token,
            })
            plain_message = strip_tags(html_message)
            from_email = settings.DEFAULT_FROM_EMAIL
            to_email = form.cleaned_data.get('email')
            
            send_mail(subject, plain_message, from_email, [to_email], html_message=html_message)
            
            messages.success(request, 'Письмо с подтверждением отправлено на вашу почту.')
            return redirect('login')
    else:
        form = RegisterForm()
    return render(request, 'registration/register.html', {'form': form})

@login_required
def profile_view(request):
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Профиль успешно обновлен")
            return redirect('profile')
    else:
        form = ProfileForm(instance=profile)
    
    return render(request, 'chat/profile.html', {
        'form': form,
        'profile': profile
    })

@login_required
def search_users(request):
    query = request.GET.get('q', '')
    room_id = request.GET.get('room_id')
    
    if not query:
        return JsonResponse({'users': []})
    
    try:
        room = ChatRoom.objects.get(id=room_id)
        # Исключаем уже добавленных пользователей и создателя
        excluded_ids = list(room.members.values_list('id', flat=True)) + [room.created_by.id]
        users = User.objects.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query)
        ).exclude(id__in=excluded_ids)[:10]  # Ограничиваем результаты
        
        results = [{
            'id': user.id,
            'username': user.username,
            'full_name': f"{user.first_name} {user.last_name}".strip() or user.username
        } for user in users]
        
        return JsonResponse({'users': results})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
def remove_member(request, room_id, user_id):
    room = get_object_or_404(ChatRoom, id=room_id)
    if not room.is_creator(request.user):
        messages.error(request, "Только создатель может управлять комнатой")
        return redirect('room_detail', room_id=room.id)
    
    try:
        user = User.objects.get(id=user_id)
        room.remove_member(user)
        messages.success(request, f"{user.username} удален из комнаты")
    except User.DoesNotExist:
        messages.error(request, "Пользователь не найден")
    
    return redirect('manage_room', room_id=room.id)

@login_required
def delete_room(request, room_id):
    room = get_object_or_404(ChatRoom, id=room_id)
    
    # Проверяем, что пользователь - создатель комнаты
    if room.created_by != request.user:
        messages.error(request, "Вы не можете удалить эту комнату")
        return redirect('room_detail', room_id=room.id)
    
    if request.method == 'POST':
        room_name = room.name
        room.delete()
        messages.success(request, f"Комната '{room_name}' удалена")
        return redirect('chat_rooms')
    
    return redirect('room_detail', room_id=room.id)

@login_required
def manage_room(request, room_id):
    room = get_object_or_404(ChatRoom, id=room_id)
    if request.user != room.created_by:
        return redirect('room_detail', room_id=room.id)
    
    room = get_object_or_404(ChatRoom, id=room_id)
    # Исключаем текущего пользователя из списка участников
    members = room.members.exclude(id=request.user.id)
    # Только активные (непринятые) приглашения
    invitations = Invitation.objects.filter(room=room, is_accepted=False).select_related('recipient')

    if request.method == "POST":
        # AJAX-запрос на приглашение пользователя
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            username = request.POST.get('username', '').strip()
            if not username:
                return JsonResponse({'status': 'error', 'message': 'Operator ID required.'})

            if username.lower() == request.user.username.lower():
                return JsonResponse({'status': 'error', 'message': 'Cannot invite yourself.'})

            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': f'User "{username}" not found.'})

            # Проверяем, не состоит ли уже в комнате
            if room.members.filter(id=user.id).exists():
                return JsonResponse({'status': 'error', 'message': f'User "{username}" is already a member.'})

            # Проверяем, нет ли уже активного приглашения
            if Invitation.objects.filter(room=room, recipient=user, is_accepted=False).exists():
                return JsonResponse({'status': 'error', 'message': f'Invitation to "{username}" already sent.'})

            # На всякий случай удаляем старые принятые приглашения (если вдруг остались)
            Invitation.objects.filter(room=room, recipient=user, is_accepted=True).delete()

            Invitation.objects.create(room=room, sender=request.user, recipient=user)
            return JsonResponse({'status': 'success', 'message': f'Invitation sent to "{username}".'})

        # Обычный POST (например, удаление пользователя)
        elif 'remove_user' in request.POST:
            user_id = request.POST.get('user_id')
            if user_id:
                try:
                    user_to_remove = User.objects.get(id=user_id)
                    # Только создатель комнаты может удалять других, и не себя
                    if request.user == room.created_by and user_to_remove != request.user:
                        room.members.remove(user_to_remove)
                        # Удаляем все приглашения в эту комнату для этого пользователя
                        Invitation.objects.filter(room=room, recipient=user_to_remove).delete()
                        messages.success(request, f'User "{user_to_remove.username}" removed from the room.')
                        return redirect('manage_room', room_id=room.id)
                except User.DoesNotExist:
                    messages.error(request, 'User not found.')
            else:
                messages.error(request, 'No user specified for removal.')
            # Если что-то пошло не так - просто перерисуем страницу с сообщением

    return render(request, 'chat/manage_room.html', {
        'room': room,
        'members': members,  # уже без текущего пользователя
        'invitations': invitations,
    })
    
@login_required
def chat_rooms(request):
    rooms = request.user.chat_rooms.all()
    
    # Обновляем активность ТОЛЬКО текущего пользователя
    if request.user.is_authenticated:
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        profile.last_activity = timezone.now()
        profile.save(update_fields=['last_activity'])
    
    users = User.objects.exclude(id=request.user.id).select_related('profile')
    return render(request, 'chat/rooms.html', {
        'rooms': rooms,
        'users': users
    })


@login_required
def room_detail(request, room_id):
    room = get_object_or_404(ChatRoom, id=room_id)
    if request.user != room.created_by and request.user not in room.members.all():
        return redirect('chat_rooms')
        
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        form = MessageForm(request.POST, request.FILES)
        if form.is_valid():
            message = form.save(commit=False)
            message.room_id = room_id
            message.sender = request.user
            if message.file:
                message.file_name = message.file.name
            # Экранируем HTML в содержимом сообщения
            if message.content:
                message.content = escape(message.content)
            message.save()
            
            # Получаем URL аватарки
            avatar_url = message.sender.profile.get_avatar_url()
            
            return JsonResponse({
                'status': 'ok',
                'message': {
                    'message_id': message.id,
                    'sender': message.sender.username,
                    'content': message.content,
                    'timestamp': message.timestamp.isoformat(),
                    'file_url': message.file.url if message.file else None,
                    'file_name': message.file_name,
                    'file_icon': message.get_file_icon(),
                    'avatar_url': avatar_url
                }
            })
        return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
    return render(request, 'chat/room.html', {'room': get_object_or_404(ChatRoom, id=room_id)})

@login_required
def create_room(request):
    if request.method == 'POST':
        room_name = request.POST.get('room_name')
        user_ids = request.POST.getlist('users')
        
        # Add created_by=request.user when creating the room
        room = ChatRoom.objects.create(name=room_name, created_by=request.user)
        room.members.add(request.user)
        for user_id in user_ids:
            user = User.objects.get(id=user_id)
            room.members.add(user)
        
        return redirect('room_detail', room_id=room.id)
    
    users = User.objects.exclude(id=request.user.id)
    return render(request, 'chat/create_room.html', {'users': users})
