# Home Assistant Configuration
Here is the start of my Home Assistant configuration. More details to come...

## Software and devices

**HW/SW Platform**
* Raspberry PI 3 + Rassbian
* Home Assistant
* Aeon Labs Z-Wave Stick (Gen 5)
* Telldus Net
* Let's Encrypt

**Devices and Sensors:**
* Amazon Echo Dot Gen 2
* Apple Devices - iPhone 6, iPhone 6+, iPhone 7+, iPad Mini 2, Apple TV 3rd gen
* Benq W100+ Projector _(not configured yet)_
* Broadlink RM Pro 2
* D-Link DCH-S150 Motion Sensor
* Kingping KP200 Screen (unsupported protocol)
* Homemade garage port controller with temp sensor (MQTT)
* Panasonic TH50PZ70E
* Plex Media Server
* SonOff switch _(not configured yet)_
* Sonos Play:1
* Telldus Plug-In Switch
* Viking Thermometer (433MHz)
* Yamaha Receiver

**Custom Components**
Here are some of the custom components I have implemented:

* _svtplay_dl_ - Play streams on a media player using svtplay_dl script
* _media_watcher_ - Create sensors based on tv shows and/or sections in Plex (does not work with plexapi 2.0.2 or earlier)
* _dlink_motion_sensor_ - Support for D-Link DCH-S150 motion sensor

## Automations

**Alexa**
Things exposed through emulated_hue:

* _Alexa, turn on television_ - Turns on TV and receiver set to HDMI2 (Apple TV)
* _Alexa, turn on morning news_ - Turns on TV, receiver, fetches link to "Nyhetsmorgon" and plays it on the Apple TV via _media_play_.
* _Alexa, turn on sonos_ - Well... turns on the Sonos and plays some music

**Automatic stuff**
Various things that happens automatically:

* Lights are turned on/off according to the sun
* Music is started on Sonos when motion is detected in the kitchen (with some conditions)
