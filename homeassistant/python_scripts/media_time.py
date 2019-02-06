TV_ENTITY = 'media_player.tv'
PROJECTOR_ENTITY = 'switch.projector'
COVER_ENTITY = 'cover.projector_screen'

PLAYER = 'media_player.apple_tv'
REMOTE = 'remote.apple_tv'

enable_tv = data.get('source', 'tv') == 'tv'


def call(hass, service, entity_id, **kwargs):
    kwargs['entity_id'] = entity_id
    hass.services.call(entity_id.split('.')[0], service, kwargs, False)


# Put receiver in correct state and wake up Apple TV
call(hass, 'turn_on', 'media_player.receiver')


was_playing = (hass.states.get(PLAYER).state == 'playing')
if was_playing:
    call(hass, 'send_command', REMOTE, command=['pause'])

# Turn on TV or projector depending on what was asked for
if enable_tv:
    hass.services.call('script', 'tv_and_hdmi1')

    if hass.states.get(PROJECTOR_ENTITY).state != 'off':
        call(hass, 'turn_off', PROJECTOR_ENTITY)
        call(hass, 'open_cover', COVER_ENTITY)
else:
    call(hass, 'turn_on', PROJECTOR_ENTITY)
    call(hass, 'close_cover', COVER_ENTITY)

    data = {'entity_id': 'group.cinema_lights'}
    hass.services.call('switch', 'turn_off', data, False)
    
    call(hass, 'turn_off', TV_ENTITY)

if was_playing:
    call(hass, 'send_command', REMOTE, command=['play'])
else:
    call(hass, 'send_command', REMOTE, command=['top_menu'])

# Output to correct device (TV or projector)
call(hass, 'yamaha_enable_output', 'media_player.receiver',
     port='hdmi1', enabled=enable_tv)
call(hass, 'yamaha_enable_output', 'media_player.receiver',
    port='hdmi2', enabled=not enable_tv)

call(hass, 'select_source', 'media_player.receiver', source='HDMI2')
call(hass, 'select_source', 'media_player.receiver', source='HDMI2')
