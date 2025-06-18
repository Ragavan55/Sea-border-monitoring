from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from .models import Device
from .forms import RegisterForm, LoginForm, DeviceForm
import requests
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt

def navigate(request):
    # If the user is already logged in, redirect to the home page
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        ship_name = request.POST.get('ship_name', '')
        owner_name = request.POST.get('owner_name', '')
        
        if not ship_name or not owner_name:
            return render(request, 'devices/navigate.html', {'error': 'Ship name and owner name are required.'})
        
        try:
            device = Device.objects.get(ship_name__iexact=ship_name, owner_name__iexact=owner_name)
            url = f"https://api.thingspeak.com/channels/{device.channel_id}/feeds.json?api_key={device.read_key}&results=1"
            response = requests.get(url, timeout=5)
            data = response.json()
            
            if not data.get('feeds'):
                return render(request, 'devices/navigate.html', {'error': 'No location data available.'})
            
            feed = data['feeds'][0]
            lat = float(feed.get('field1', 0))
            lon = float(feed.get('field2', 0))
            time = feed.get('created_at', '')
            
            context = {
                'ship_name': ship_name,
                'owner': owner_name,
                'lat': lat,
                'lon': lon,
                'time': time,
                'channel_id': device.channel_id,
                'read_key': device.read_key,
            }
            return render(request, 'devices/navigate.html', context)
        
        except Device.DoesNotExist:
            return render(request, 'devices/navigate.html', {'error': 'Device not found.'})
        except Exception as e:
            print(f"Error fetching data for device {ship_name}: {str(e)}")
            return render(request, 'devices/navigate.html', {'error': 'An error occurred while fetching data.'})
    
    return render(request, 'devices/navigate.html')

@login_required
def navigate_end(request):
    start_lat = request.GET.get('start_lat')
    start_lon = request.GET.get('start_lon')
    end_lat = request.GET.get('end_lat')
    end_lon = request.GET.get('end_lon')

    if not all([start_lat, start_lon, end_lat, end_lon]):
        return redirect('navigate')

    context = {
        'start_lat': start_lat,
        'start_lon': start_lon,
        'end_lat': end_lat,
        'end_lon': end_lon,
    }
    return render(request, 'devices/navigate_end.html', context)
def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = RegisterForm()
    return render(request, 'devices/register.html', {'form': form})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('home')
    else:
        form = LoginForm()
    return render(request, 'devices/login.html', {'form': form})

@login_required
def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def home_view(request):
    return render(request, 'devices/home.html')

@login_required
def get_device_locations(request):
    devices = Device.objects.all()
    device_locations = []
    
    for device in devices:
        url = f"https://api.thingspeak.com/channels/{device.channel_id}/feeds.json?api_key={device.read_key}&results=1"
        try:
            response = requests.get(url)
            data = response.json()
            if 'feeds' in data and len(data['feeds']) > 0:
                feed = data['feeds'][0]
                lat = float(feed.get('field1', 0))
                lon = float(feed.get('field2', 0))
                device_locations.append({
                    'ship_name': device.ship_name,
                    'owner_name': device.owner_name,
                    'lat': lat,
                    'lon': lon,
                    'id': device.id
                })
        except Exception as e:
            print(f"Error fetching data for device {device.ship_name}: {e}")
            continue
    
    return JsonResponse({'locations': device_locations})

@login_required
def search_ship(request):
    ship_name = request.GET.get('ship_name', '').strip()
    location = None
    if ship_name:
        try:
            device = Device.objects.get(ship_name__iexact=ship_name)
            # Fetch data from ThingSpeak API (up to 10 feeds)
            url = f"https://api.thingspeak.com/channels/{device.channel_id}/feeds.json?api_key={device.read_key}&results=10"
            response = requests.get(url, timeout=5)
            response.raise_for_status()  # Raise an error for HTTP errors
            data = response.json()
            
            # Check if 'feeds' key exists and has data
            if not data.get('feeds'):
                return JsonResponse({'error': 'No data available for this ship'}, status=404)
            
            # Iterate through feeds to find the most recent valid entry
            for feed in data['feeds']:
                lat = feed.get('field1')
                lon = feed.get('field2')
                time = feed.get('created_at', '')
                
                if lat is not None and lon is not None:
                    try:
                        lat = float(lat)
                        lon = float(lon)
                        location = {
                            'ship_name': device.ship_name,
                            'owner': device.owner_name,
                            'lat': lat,
                            'lon': lon,
                            'time': time,
                            # 'status': feed.get('field3', 'N/A'), 
                            'status': 'Outside',  # Status (Inside/Outside)# Status (Inside/Outside)
                            'exit_time': feed.get('field4', 'N/A'),  # Last Exit Time
                            'return_time': feed.get('field5', 'N/A'),  # Last Return Time
                        }
                        break  # Stop after finding the first valid entry
                    except ValueError:
                        print(f"Invalid latitude or longitude for device {device.ship_name}")
                        continue
            
            if location is None:
                return JsonResponse({'error': 'Missing latitude or longitude for this ship in all feeds'}, status=400)
        
        except Device.DoesNotExist:
            return JsonResponse({'error': 'Device not found'}, status=404)
        except requests.exceptions.RequestException as e:
            return JsonResponse({'error': f'Error fetching data: {e}'}, status=500)
        except ValueError as e:
            return JsonResponse({'error': f'Error parsing data: {e}'}, status=500)
        except Exception as e:
            return JsonResponse({'error': f'Unexpected error: {e}'}, status=500)
    
    return render(request, 'devices/search.html', {
        'ship_name': ship_name,
        'location': location
    })
    
def get_all_ship_locations(request):
    if request.method != 'GET':
        return JsonResponse({'error': 'Invalid request method.'}, status=405)
    
    devices = Device.objects.all()
    locations = []
    
    for device in devices:
        try:
            # Fetch data from ThingSpeak API (up to 10 feeds)
            url = f"https://api.thingspeak.com/channels/{device.channel_id}/feeds.json?api_key={device.read_key}&results=10"
            response = requests.get(url, timeout=5)
            response.raise_for_status()  # Raise an error for HTTP errors
            data = response.json()
            
            # Check if 'feeds' key exists and has data
            if not data.get('feeds'):
                print(f"No feeds available for device {device.ship_name}")
                continue
            
            # Iterate through feeds to find the most recent valid entry
            for feed in data['feeds']:
                lat = feed.get('field1')
                lon = feed.get('field2')
                time = feed.get('created_at', '')
                
                if lat is not None and lon is not None:
                    try:
                        lat = float(lat)
                        lon = float(lon)
                        locations.append({
                            'ship_name': device.ship_name,
                            'owner_name': device.owner_name,
                            'lat': lat,
                            'lon': lon,
                            'time': time,
                        })
                        break  # Stop after finding the first valid entry
                    except ValueError:
                        print(f"Invalid latitude or longitude for device {device.ship_name}")
                        continue
            
            if lat is None or lon is None:
                print(f"Missing latitude or longitude for device {device.ship_name} in all feeds")
        
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data for {device.ship_name}: {e}")
        except ValueError as e:
            print(f"Error parsing location data for {device.ship_name}: {e}")
        except Exception as e:
            print(f"Unexpected error for {device.ship_name}: {e}")
    
    return JsonResponse({'locations': locations})

    
@csrf_exempt
@login_required
def get_weather_data(request):
    if request.method == 'GET':
        lat = request.GET.get('lat')
        lon = request.GET.get('lon')
        
        if not lat or not lon:
            return JsonResponse({'error': 'Latitude and longitude required'}, status=400)
        
        try:
            # Using One Call API 3.0
            url = f"https://api.openweathermap.org/data/3.0/onecall?lat={lat}&lon={lon}&exclude=minutely,hourly,daily,alerts&appid={settings.OPENWEATHER_API_KEY}&units=metric"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('cod'):
                return JsonResponse({'error': data.get('message', 'Unknown error')}, status=400)
            
            current = data.get('current', {})
            return JsonResponse({
                'temp': current.get('temp'),
                'pressure': current.get('pressure'),
                'humidity': current.get('humidity'),
                'wind_speed': current.get('wind_speed'),
                'sea_level': current.get('sea_level'),
                'grnd_level': current.get('grnd_level'),
                'lat': lat,
                'lon': lon,
                'weather': current.get('weather', [{}])[0].get('description')
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=400)

@login_required
def delete_device(request, device_id):
    try:
        device = get_object_or_404(Device, id=device_id)
        if request.method == 'POST':
            device.delete()
            return redirect('list_devices')
        return render(request, 'devices/confirm_delete.html', {'device': device})
    except Exception as e:
        print(f"Error deleting device: {str(e)}")
        return redirect('list_devices')

@login_required
def list_devices(request):
    devices = Device.objects.all() 
    return render(request, 'devices/list_devices.html', {'devices': devices})

@login_required
def add_device(request):
    if request.method == 'POST':
        form = DeviceForm(request.POST)
        if form.is_valid():
            device = form.save(commit=False)
            device.created_by = request.user
            device.save()
            return redirect('list_devices')
    else:
        form = DeviceForm()
    return render(request, 'devices/add_device.html', {'form': form})

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from .models import Device
import requests

@csrf_exempt
def get_live_ship_location(request):
    ship_name = request.GET.get('ship_name', '').strip()
    if not ship_name:
        return JsonResponse({'error': 'Ship name is required'}, status=400)
    
    try:
        # Fetch the device by ship name
        device = Device.objects.get(ship_name__iexact=ship_name)
        
        # Fetch data from ThingSpeak API (up to 10 feeds)
        url = f"https://api.thingspeak.com/channels/{device.channel_id}/feeds.json?api_key={device.read_key}&results=10"
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Raise an error for HTTP errors
        data = response.json()
        
        # Check if 'feeds' key exists and has data
        if not data.get('feeds'):
            return JsonResponse({'error': 'No data available for this ship'}, status=404)
        
        # Iterate through feeds to find the most recent valid entry
        for feed in data['feeds']:
            lat = feed.get('field1')
            lon = feed.get('field2')
            time = feed.get('created_at', '')
            
            if lat is not None and lon is not None:
                try:
                    lat = float(lat)
                    lon = float(lon)
                    return JsonResponse({
                        'ship_name': device.ship_name,
                        'owner_name': device.owner_name,
                        'lat': lat,
                        'lon': lon,
                        'time': time,
                    })
                except ValueError:
                    print(f"Invalid latitude or longitude for device {device.ship_name}")
                    continue
        
        # If no valid entry is found
        return JsonResponse({'error': 'Missing latitude or longitude for this ship in all feeds'}, status=400)
    
    except Device.DoesNotExist:
        return JsonResponse({'error': 'Ship not found'}, status=404)
    except requests.exceptions.RequestException as e:
        return JsonResponse({'error': f'Error fetching data: {e}'}, status=500)
    except ValueError as e:
        return JsonResponse({'error': f'Error parsing data: {e}'}, status=500)
    except Exception as e:
        return JsonResponse({'error': f'Unexpected error: {e}'}, status=500)
  
# from datetime import datetime
# from django.shortcuts import render
# import requests
# from .models import Device

# def ship_status(request):
#     ship_name_query = request.GET.get('ship_name', '')
#     device = Device.objects.filter(name=ship_name_query).first()

#     location = None
#     history = []

#     if device:
#         try:
#             # Latest data
#             url_last = f"https://api.thingspeak.com/channels/{device.channel_id}/feeds.json?api_key={device.read_key}&results=1"
#             response = requests.get(url_last)
#             data = response.json()
#             raw_location = data.get('field3', '')
#             location_value = raw_location if raw_location not in [None, '', 'null'] else 'Unknown'

#             location = {
#                 'lat': float(data.get('field1', 0)),
#                 'lon': float(data.get('field2', 0)),
#                 'location': location_value,
#                 'ship_name': device.name,
#                 'owner': device.owner,
#                 'channel_id': device.channel_id,
#                 'read_api_key': device.read_api,
#                 'time': data.get('created_at', 'Unknown'),
#                 'exit_time': device.exit_time,
#                 'return_time': device.return_time,
#             }
#             # History - last 10 entries
#             history_url = f"https://api.thingspeak.com/channels/{device.channel_id}/feeds.json?api_key={device.read_api}&results=10"
#             history_response = requests.get(history_url)
#             history_data = history_response.json()

#             for entry in history_data.get('feeds', []):
#                 history.append({
#                     'lat': float(entry.get('field1', 0)),
#                     'lon': float(entry.get('field2', 0)),
#                     'time': entry.get('created_at', 'Unknown'),
#                 })

#         except Exception as e:
#             print("Error fetching ThingSpeak data:", e)

#     return render(request, 'devices/ship_status.html', {
#         'ship_name': ship_name_query,
#         'location': location,
#         'history': history,
#     })


