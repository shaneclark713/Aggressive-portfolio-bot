from config.filter_presets import FILTER_PRESETS
from .control_panel import preset_keyboard, mode_keyboard

async def handle_control_panel_callback(update, context, config_service, settings_repo):
    query=update.callback_query; await query.answer(); data=query.data or ''
    if data=='cp|presets': await query.edit_message_text('Select preset', reply_markup=preset_keyboard(list(FILTER_PRESETS.keys())))
    elif data=='cp|mode': await query.edit_message_text('Select execution mode', reply_markup=mode_keyboard())
    elif data.startswith('cpreset|'):
        preset=data.split('|',1)[1]; config_service.set_active_preset(preset); await query.edit_message_text(f'Active preset changed to {preset}')
    elif data.startswith('cmode|'):
        mode=data.split('|',1)[1]; config_service.set_execution_mode(mode); await query.edit_message_text(f'Execution mode changed to {mode}')
