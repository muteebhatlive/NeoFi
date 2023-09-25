from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from .serializers import RegistrationSerializer
from django.contrib.auth import authenticate, login, logout
from rest_framework.authtoken.models import Token
from django.http import HttpRequest
from django.contrib.auth.models import User
from .models import UserProfile
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json
from django.http import JsonResponse




@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    if request.method == 'POST':
        serializer = RegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()

            # Create an authentication token for the registered user
            token, created = Token.objects.get_or_create(user=user)

            response_data = {
                'message': 'Registration successful',
                'token': token.key  # Include the token key in the response
            }
            return Response(response_data, status=status.HTTP_201_CREATED)
        else:
            # Check for specific validation errors and handle them
            if 'username' in serializer.errors or 'email' in serializer.errors:
                return Response({'message': 'Username/Email is already taken.'}, status=status.HTTP_400_BAD_REQUEST)
            else:
                errors = serializer.errors
                response_data = {'message': 'Registration failed', 'errors': errors}
                return Response(response_data, status=status.HTTP_400_BAD_REQUEST)
        
@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    if request.method == 'POST':
        username= request.data.get('username')
        password = request.data.get('password')

        if not (username and password):
            return Response({'message': 'Both username/email and password are required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Determine if the provided input is a username or email
        if '@' in username:
            # Provided input is an email
            user = authenticate(request=request, email=username, password=password)
        else:
            # Provided input is a username
            user = authenticate(request=request, username=username, password=password)

        if user is not None:
            # User is authenticated; create or retrieve an authentication token
            auth_login(request, user) 
            token, created = Token.objects.get_or_create(user=user)
            user_profile, created = UserProfile.objects.get_or_create(user=user)
            user_profile.set_online()
            response_data = {
                'message': 'Login successful',
                'token': token.key,
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email
                }
            }
            return Response(response_data, status=status.HTTP_200_OK)
        else:
            # Authentication failed
            return Response({'message': 'Invalid credentials. Please check your username/email and password.'}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    if request.method == 'POST':
        # Get the user's authentication token from the request
        auth_token = request.auth
        print('USER:   ',request.user)
        print('AUTH:   ',request.auth)
        
        if auth_token:
            # Delete the user's authentication token
            user_profile = UserProfile.objects.get(user= request.user)
            print(user_profile)
            user_profile.set_offline()
            auth_logout(request)
            auth_token.delete()
            
            # Update user's online status
            # Optionally, you can perform other logout-related tasks here, if needed

            return Response({'message': 'Logout successful'}, status=status.HTTP_200_OK)
    
    # If no authentication token was provided in the request, return an error
    return Response({'message': 'Authentication token required'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def online_users(request):
    online_users = UserProfile.objects.filter(is_online=True).values('user__username')
    response_data = {
        'online_users': list(online_users)
    }
    return Response(response_data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start(request):
    receiver_username = request.data.get('receiver_username')
    print('1: ',receiver_username)
    try:
        recipient_profile = UserProfile.objects.get(user__username=receiver_username)
        
        if recipient_profile.is_online == True:

            return Response({'message': 'Chat initiated successfully'}, status=status.HTTP_200_OK)
        else:
            return Response({'message': 'Recipient is offline or unavailable'}, status=status.HTTP_400_BAD_REQUEST)
    except UserProfile.DoesNotExist:
        return Response({'message': 'Recipient not found'}, status=status.HTTP_404_NOT_FOUND)
    



@api_view(['POST'])
def send(request):
    print(request)
    if request.method == "POST":
        recipient_name = request.POST.get("recipient_name")
        message = request.POST.get("message")
        print('R:  ', recipient_name)
        # Retrieve the recipient's UserProfile based on their username
        try:
            recipient_profile = UserProfile.objects.get(user__username=recipient_name)
        except UserProfile.DoesNotExist:
            return Response({"status": "error", "message": "Recipient not found."}, status=404)

        # Check if the recipient is online and available
        if recipient_profile.is_online == True:
            # Send the message to the recipient's WebSocket consumer
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.send)(f"user_{recipient_profile.user.username}", {
                "type": "chat.message",
                "message": message,
            })
            return Response({"status": "success", "message": "Message sent successfully."})

        else:
            return Response({"status": "error", "message": "Recipient is offline or unavailable. Message not sent."}, status=400)

    return Response({"status": "error", "message": "Invalid request method."}, status=405)





