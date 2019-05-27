ENTITIES = ['switch.projector', 'media_player.apple_tv',
            'media_player.receiver', 'media_player.tv']
PROJECTOR_SCREEN = 'cover.projector_screen'


def call(hass, service, entity_id, **kwargs):
    kwargs['entity_id'] = entity_id
    hass.services.call(entity_id.split('.')[0], service, kwargs, False)


# Restore TV as output as the receiver loses sync with output source otherwise
call(hass, 'yamaha_enable_output', 'media_player.receiver',
     port='hdmi1', enabled=True)
call(hass, 'yamaha_enable_output', 'media_player.receiver',
     port='hdmi2', enabled=False)


#if hass.states.get('input_boolean.cinema_lights_turned_off') == 'on':
data = {'entity_id': 'group.cinema_lights'}
hass.services.call('switch', 'turn_on', data, False)


# Media players and switches here
for ent in ENTITIES:
    call(hass, 'turn_off', ent)


# Projector screen is different
call(hass, 'close_cover', PROJECTOR_SCREEN)
