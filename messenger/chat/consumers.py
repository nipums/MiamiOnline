import json
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model
from .models import Message, ChatRoom, UserProfile
from channels.db import database_sync_to_async
from django.utils import timezone
from .models import Ban

User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            
            if data.get('type') == 'delete_message':
                message = await self.get_message(data['message_id'])
                if message and (self.scope['user'] == message.sender or 
                               self.scope['user'] == message.room.created_by):
                    await self.delete_message(message)
                    
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            'type': 'message_deleted',
                            'message_id': message.id,
                            'deleted_by': self.scope['user'].username
                        }
                    )
                return
                
            # Handle regular messages
            if 'content' in data:
                if not data['content']:
                    raise ValueError("Message content is required")
                
                message_obj = await self.save_message(data['content'])
                avatar_url = await self.get_user_avatar_url(message_obj.sender)
                
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_message',
                        'message_id': message_obj.id,
                        'sender': message_obj.sender.username,
                        'content': message_obj.content,
                        'timestamp': message_obj.timestamp.isoformat(),
                        'avatar_url': avatar_url,
                    }
                )
                
        except Exception as e:
            await self.send(text_data=json.dumps({'error': str(e)}))

    async def message_deleted(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message_deleted',
            'message_id': event['message_id'],
            'deleted_by': event['deleted_by']
        }))

    @database_sync_to_async
    def get_message(self, message_id):
        return Message.objects.filter(id=message_id).first()

    async def message_deleted(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message_deleted',
            'message_id': event['message_id'],
            'deleted_by': event['deleted_by']
        }))

    async def connect(self):
        if self.scope["user"].is_anonymous:
            await self.close()
            return

        try:
            ban = await database_sync_to_async(Ban.objects.get)(user=self.scope["user"], is_active=True)
            if ban.expires_at is None or ban.expires_at > timezone.now():
                await self.close()
                return
        except Ban.DoesNotExist:
            pass

    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'
        
        if isinstance(self.scope["user"], AnonymousUser):
            await self.close()
            return

        # Проверка существования комнаты
        if not await self.room_exists():
            await self.close()
            return

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

        async def chat_message(self, event):
            await self.send(text_data=json.dumps({
                'type': 'message',
                'message_id': event['message_id'],
                'sender': event['sender'],
                'content': event['content'],
                'timestamp': event['timestamp'],
                'avatar_url': event.get('avatar_url', ''),
                'file_url': event.get('file_url', None),
                'file_name': event.get('file_name', None),
                'file_icon': event.get('file_icon', None)
            }))

        async def receive(self, text_data):
            try:
                data = json.loads(text_data)
                
                # Обработка текстовых сообщений
                if 'content' in data:
                    if not data['content']:
                        raise ValueError("Message content is required")
                    
                    message_obj = await self.save_message(data['content'])
                    avatar_url = await self.get_user_avatar_url(message_obj.sender)
                    
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            'type': 'chat_message',
                            'message_id': message_obj.id,
                            'sender': message_obj.sender.username,
                            'content': message_obj.content,
                            'timestamp': message_obj.timestamp.isoformat(),
                            'avatar_url': avatar_url,
                        }
                    )
                    
            except Exception as e:
                await self.send(text_data=json.dumps({'error': str(e)}))

    @database_sync_to_async
    def room_exists(self):
        return ChatRoom.objects.filter(id=self.room_id).exists()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message = data.get('content')
            
            if not message:
                raise ValueError("Message content is required")
            
            # Сохраняем сообщение в БД
            message_obj = await self.save_message(message)
            
            # Получаем URL аватарки отправителя
            avatar_url = await self.get_user_avatar_url(message_obj.sender)
            
            # Отправляем сообщение в группу
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message_id': message_obj.id,
                    'sender': message_obj.sender.username,
                    'content': message_obj.content,
                    'timestamp': message_obj.timestamp.isoformat(),
                    'avatar_url': avatar_url,
                }
            )
        except Exception as e:
            await self.send(text_data=json.dumps({
                'error': str(e)
            }))

    @database_sync_to_async
    def save_message(self, content):
        return Message.objects.create(
            room_id=self.room_id,
            sender=self.scope['user'],
            content=content
        )
    
    @database_sync_to_async
    def get_user_avatar_url(self, user):
        try:
            profile = UserProfile.objects.get(user=user)
            if profile.avatar:
                return profile.avatar.url
        except UserProfile.DoesNotExist:
            pass
        return '/static/chat/img/default_avatar.png'

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message_id': event['message_id'],
            'sender': event['sender'],
            'content': event['content'],
            'timestamp': event['timestamp'],
            'avatar_url': event['avatar_url'],
        }))