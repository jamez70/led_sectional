# Live Sectional Map controller
# Dylan Rush 2017
# dylanhrush.com
# Uses RPi.GPIO library: https://sourceforge.net/p/raspberry-gpio-python/wiki/BasicUsage/

import time
import urllib
import re
from threading import Thread
from neopixel import *

# LED strip configuration:
LED_COUNT      = 50      # Number of LED pixels.
LED_PIN        = 10      # GPIO pin connected to the pixels (10 uses SPI /dev/spidev0.0).
LED_FREQ_HZ    = 500000  # LED signal frequency in hertz (usually 800khz)
LED_DMA        = 10      # DMA channel to use for generating signal (try 10)
LED_BRIGHTNESS = 64     # Set to 0 for darkest and 255 for brightest
LED_INVERT     = True   # True to invert the signal (when using NPN transistor level shift)
LED_CHANNEL    = 0       # set to '1' for GPIOs 13, 19, 41, 45 or 53
LED_STRIP      = ws.WS2811_STRIP_RGB   # Strip type and colour ordering
CONFIG_FILE    = "/root/airports.txt"


airport_pins = {'KORD':0}
#		'KRNT':12,
#        'KSEA':4,
#       'KPLU':5,
#        'KOLM':6,
#        'KTIW':7,
#        'KPWT':15,
    


# Overrides can be used to test different conditions
overrides = {}
#overrides = {'KOLM':'IFR',
#             'KTIW':'MVFR',
#             'KPWT':'INVALID',
#             'KORD':'LIFR'}


colors = {'RED':0xff0000,
          'GREEN':0x00ff00,
          'BLUE':0x0000ff,
		  'MAGENTA':0xff00ff,
		  'DARKGREEN':0x000200,
		  'YELLOW':0x2f2f00,
          'LOW':0}

airport_should_flash = {}
airport_color = {}


def read_config_file():
	global airport_pins
	with open(CONFIG_FILE,"r") as text_file:
		airport_pins = {}
		cnt = 1
		line = text_file.readline()
		while line:
			newl=line.strip()
			spl=newl.split(",")
			print("Split "+spl[0]+" and "+spl[1])
			airport_pins[spl[0]]=int(spl[1])
			print("Line {}: {}".format(cnt, line.strip()))
			line = text_file.readline()
			cnt = cnt + 1
			
	
def get_metar(airport):
  try:
    stream = urllib.urlopen('http://www.aviationweather.gov/metar/data?ids='+airport+'&format=raw&hours=0&taf=off&layout=off&date=0');
    for line in stream:
      if '<!-- Data starts here -->' in line:
        return re.sub('<[^<]+?>', '', stream.readline())
    return 'INVALID'
  except Exception, e:
    print str(e);
    return 'INVALID'
  finally:
    stream.close();
def get_vis(metar):
  match = re.search('( [0-9] )?([0-9]/?[0-9]?SM)', metar)
  if(match == None):
    return 'INVAILD'
  (g1, g2) = match.groups()
  if(g2 == None):
    return 'INVALID'
  if(g1 != None):
    return 'IFR'
  if '/' in g2:
    return 'LIFR'
  vis = int(re.sub('SM','',g2))
  if vis < 3:
    return 'IFR'
  if vis <=5 :
    return 'MVFR'
  return 'VFR'

#def get_vis_category(vis):
#  if vis == 'INVALID':
#    return 'INVALID'
#  if '/' in vis:
#    return 'LIFR'
#  vis_int = int(vis)
#  if vis < 3:
#    return 'IFR'
#  if vis <= 5:
#    return 'MVFR'
#  return 'VFR'
def get_ceiling(metar):
  components = metar.split(' ' );
  minimum_ceiling = 10000
  for component in components:
    if 'BKN' in component or 'OVC' in component:
      ceiling = int(filter(str.isdigit,component)) * 100
      if(ceiling < minimum_ceiling):
        minimum_ceiling = ceiling
  return minimum_ceiling
def get_ceiling_category(ceiling):
  if ceiling < 500:
    return 'LIFR'
  if ceiling < 1000:
    return 'IFR'
  if ceiling < 3000:
    return 'MVFR'
  return 'VFR'
def get_category(metar):
  vis = get_vis(metar)
  ceiling = get_ceiling_category(get_ceiling(metar))
  if(ceiling == 'INVALID'):
    return 'INVALID'
  if(vis == 'LIFR' or ceiling == 'LIFR'):
    return 'LIFR'
  if(vis == 'IFR' or ceiling == 'IFR'):
    return 'IFR'
  if(vis == 'MVFR' or ceiling == 'MVFR'):
    return 'MVFR'
  return 'VFR'



def set_airport_display(airport, category):
  if category == 'VFR':
    airport_should_flash[airport] = False
    airport_color[airport] = 'GREEN'
  elif category == 'MVFR':
    airport_should_flash[airport] = False
    airport_color[airport] = 'BLUE'
  elif category == 'IFR':
    airport_should_flash[airport] = False
    airport_color[airport] = 'RED'
  elif category == 'LIFR':
    airport_should_flash[airport] = False
    airport_color[airport] = 'MAGENTA'
  else:
    airport_should_flash[airport] = True
    airport_color[airport] = 'BLUE'

def refresh_airport_displays():
  for airport in airport_pins:
#    print "Retrieving METAR for "+airport
    metar = get_metar(airport)
    print "METAR for "+airport+" = '"+metar+"'"
    category = get_category(metar)
    if airport in overrides:
      category = overrides[airport]
    print "Category for "+airport+" = "+category+ " index " + str(airport_pins[airport])
    set_airport_display(airport, category)
	
def setLed(airport, color):
  strip.setPixelColor(airport_pins[airport], colors[color])
  strip.show()

def render_airport_displays(airport_flasher):
  for airport in airport_pins:
    if airport_should_flash[airport] and airport_flasher:
      setLed(airport, 'LOW')
    else:
      setLed(airport, airport_color[airport])


def all_airports(color):
  for airport in airport_pins:
    print "Airport " + airport + " Index " + str(airport_pins[airport])
    setLed(airport, color)

endtime = int(time.time()) + 14400

def render_thread():
  print "Starting rendering thread"
  while(time.time() < endtime):
#    print "render"
    render_airport_displays(True)
    time.sleep(0.1)
    render_airport_displays(False)
    time.sleep(0.1)

def refresh_thread():
  print "Starting refresh thread"
  while(time.time() < endtime):
    print "Refreshing categories"
    refresh_airport_displays()
    time.sleep(60)


read_config_file()

for airport in airport_pins:
  airport_should_flash[airport] = False
  airport_color[airport] = 'YELLOW'
	# Create NeoPixel object with appropriate configuration.

strip = Adafruit_NeoPixel(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL, LED_STRIP)
# Intialize the library (must be called once before other functions).
strip.begin()

#turn all the LEDS off
for i in range(strip.numPixels()):
	strip.setPixelColor(i, 0x010101)
strip.show()

time.sleep(2)
# Test LEDS on startup
all_airports('DARKGREEN')

thread1 = Thread(target = render_thread)
thread2 = Thread(target = refresh_thread)
thread1.daemon = True
thread1.start()
thread2.daemon = True
thread2.start()

#thread1.join()
#thread2.join()

while True:
	time.sleep(10000)
