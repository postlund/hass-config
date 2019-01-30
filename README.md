# Home Assistant Configuration

This is my Home Assistant configuration so far. It is updated
every once in a while.

![Alt text](/screenshots/main.png?raw=true "Main Screen")

## Software and devices

**HW/SW Platform**
* Raspberry PI 3 + Rassbian
* Home Assistant + Lovelace + custom theme (based on darkblue)
* Aeon Labs Z-Wave Stick (Gen 5)
* RFLink
* Let's Encrypt + custom domain
* IR Receiver (LIRC)

**Devices and Sensors:**
* Amazon Echo Dot Gen 2
* Apple Devices - iPhone X, Apple TV 4K
* Benq W100+ Projector
* Broadlink RM Pro 2
* D-Link DCH-S150 Motion Sensor
* Kingpin KP200 Screen
* Homemade garage port controller with temp sensor (esphomelib)
* Panasonic TH50PZ70E (CEC)
* Emby
* SonOff Basic switch for bedroom light
* Sonos Play:1
* Various 433MHz sockets
* Viking Thermometer (433MHz)
* Yamaha RX-V773 Receiver
* Anova Sous Vide Precision Cooker BT+WiFi *(not added yet)*

**Custom Components**
Here are some of the custom components I have implemented:

* _dlink_motion_sensor_ - Support for D-Link DCH-S150 motion sensor (currently not used)
* _food_planning_ - Fetches weekly food planning from Google Drive and presents as sensors with markdown as UI
* _tv_cec_ - Component to turn on/off my TV and report state (deals with shortcomings of CEC in my TV)

Feel free to use the components and send a PR if you have any changes to share.
Please note that I have written these for my own needs and do _not_ give any support
when using them.

***Deprecated***

These components are deprecated:

* _svtplay_dl_ - Play streams on a media player using svtplay_dl script
* _media_watcher_ - Create sensors based on tv shows and/or sections in Plex (does not work with plexapi 2.0.2 or earlier)

## Automations

**Alexa**
Things exposed through emulated_hue:

* _Alexa, turn on television_ - Turns on TV and receiver set to HDMI2 (Apple TV)
* _Alexa, turn on cinema_ - Turns on projector, brings down screens sets correct inputs/outputs.
* _Alexa, turn on sonos_ - Well... turns on the Sonos and plays some music

**Engine Heater**

There is an engine heater package that automatically turn on/off the engine pre-heater.

**Automatic stuff**
Various things that happens automatically:

* Lights are turned on/off according to the sun

