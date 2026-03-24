from __future__ import annotations
from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler, filters
from .callbacks import handle_trade_callback
from .keyboards import VALID_FILTER_CATEGORIES, build_control_panel_keyboard, build_filter_profile_menu_keyboard, build_filter_categories_keyboard, build_filter_fields_keyboard, build_mode_keyboard, build_presets_keyboard, build_strategies_keyboard
from .formatters import format_catalyst_scan, format_event_scan, format_full_scan_summary, format_news_scan, format_scan_status

def _format_filter_category(profile:str, category:str, values:dict)->str:
    lines=[f"{profile.title()} / {category.title()} Filters",""]; [lines.append(f"- {k}: {v}") for k,v in values.items()]; lines += ["","Tap a field below to edit it."]; return "\n".join(lines)
async def start_command(update, context): await update.message.reply_text("Bot online.")
async def panel_command(update, context): await update.message.reply_text("Control Panel", reply_markup=build_control_panel_keyboard())
async def config_command(update, context, config_service):
    profile_map=config_service.get_profile_preset_map()
    await update.message.reply_text(f"Overall preset: {config_service.get_active_preset()}\nExecution mode: {config_service.get_execution_mode()}\nFilter profile: {config_service.get_active_filter_profile()}\nPremarket preset: {profile_map['premarket']}\nMidday preset: {profile_map['midday']}\nOvernight preset: {profile_map['overnight']}")
async def cancel_command(update, context): context.user_data.pop("pending_filter_edit", None); await update.message.reply_text("Canceled.")

def build_handlers(app_services, config_service, admin_chat_id:int):
    async def _config(update, context): await config_command(update, context, config_service)
    async def _auth(update): 
        if update.effective_chat.id != admin_chat_id: 
            await update.message.reply_text("Unauthorized."); return False
        return True
    async def _run_lane(update, context, method_name:str, label:str):
        if not await _auth(update): return
        scanner=app_services.get("scanner")
        if scanner is None: await update.message.reply_text("Scanner service not available."); return
        await update.message.reply_text(f"Running {label}...")
        result=await getattr(scanner, method_name)()
        await update.message.reply_text(format_scan_status(result["stats"]) + f"\n\nCandidates returned: {len(result['candidates'])}", parse_mode="HTML")
    async def _scan(update, context):
        if not await _auth(update): return
        scanner=app_services.get("scanner")
        if scanner is None: await update.message.reply_text("Scanner service not available."); return
        await update.message.reply_text("Running full scan..."); summary=await scanner.scan_full_overview(); await update.message.reply_text(format_full_scan_summary(summary), parse_mode="HTML")
    async def _scan_market(update, context): await _run_lane(update, context, "scan_market_overview", "market scan")
    async def _scan_premarket(update, context): await _run_lane(update, context, "scan_premarket_overview", "premarket scan")
    async def _scan_midday(update, context): await _run_lane(update, context, "scan_midday_overview", "midday scan")
    async def _scan_overnight(update, context): await _run_lane(update, context, "scan_overnight_overview", "overnight scan")
    async def _scan_news(update, context):
        if not await _auth(update): return
        scanner=app_services.get("scanner")
        if scanner is None: await update.message.reply_text("Scanner service not available."); return
        await update.message.reply_text("Running news scan..."); await update.message.reply_text(format_news_scan(await scanner.scan_news_overview()), parse_mode="HTML")
    async def _scan_events(update, context):
        if not await _auth(update): return
        scanner=app_services.get("scanner")
        if scanner is None: await update.message.reply_text("Scanner service not available."); return
        await update.message.reply_text("Running events scan..."); await update.message.reply_text(format_event_scan(await scanner.scan_events_overview()), parse_mode="HTML")
    async def _scan_catalyst(update, context):
        if not await _auth(update): return
        scanner=app_services.get("scanner")
        if scanner is None: await update.message.reply_text("Scanner service not available."); return
        await update.message.reply_text("Running catalyst scan..."); await update.message.reply_text(format_catalyst_scan(await scanner.scan_catalyst_overview()), parse_mode="HTML")
    async def _scan_status(update, context):
        if not await _auth(update): return
        scanner=app_services.get("scanner")
        if scanner is None: await update.message.reply_text("Scanner service not available."); return
        await update.message.reply_text(format_scan_status(scanner.get_last_scan_stats()), parse_mode="HTML")
    async def _pending_text(update, context):
        pending=context.user_data.get("pending_filter_edit")
        if not pending: return
        if update.effective_chat.id != admin_chat_id:
            await update.message.reply_text("Unauthorized."); context.user_data.pop("pending_filter_edit", None); return
        profile, category, field = pending["profile"], pending["category"], pending["field"]
        try: new_value=config_service.set_filter_value(category, field, (update.message.text or "").strip(), profile=profile)
        except Exception as exc:
            await update.message.reply_text(f"Could not update {profile}.{category}.{field}: {exc}\nSend a new value or /cancel."); return
        context.user_data.pop("pending_filter_edit", None); values=config_service.get_filter_fields(category, profile=profile)
        await update.message.reply_text(f"Updated {profile}.{category}.{field} to {new_value}.", reply_markup=build_filter_fields_keyboard(profile, category, values))
    async def _guarded_callback(update, context):
        query=update.callback_query; await query.answer()
        if update.effective_chat.id != admin_chat_id: await query.answer("Unauthorized", show_alert=True); return
        data=query.data or ""
        if data.startswith(("a|","p|","r|")): await handle_trade_callback(update, context, app_services); return
        if data=="cp|back": context.user_data.pop("pending_filter_edit", None); await query.edit_message_text("Control Panel", reply_markup=build_control_panel_keyboard()); return
        if data=="cp|presets": await query.edit_message_text(f"Select Overall Preset\nCurrent: {config_service.get_active_preset()}", reply_markup=build_presets_keyboard(config_service.get_available_presets(), config_service.get_active_preset())); return
        if data=="cp|mode": await query.edit_message_text(f"Select Mode\nCurrent: {config_service.get_execution_mode()}", reply_markup=build_mode_keyboard(config_service.get_execution_mode())); return
        if data=="cp|strategies": await query.edit_message_text("Strategies", reply_markup=build_strategies_keyboard(config_service.get_strategy_states())); return
        if data=="cp|filters": await query.edit_message_text("Choose which scan preset you want to edit.", reply_markup=build_filter_profile_menu_keyboard(config_service.get_profile_preset_map(), config_service.get_active_filter_profile())); return
        if data.startswith("fprofile|"):
            profile=data.split("|",1)[1].lower(); config_service.set_active_filter_profile(profile); await query.edit_message_text(f"Preset Menu → {profile.title()}", reply_markup=build_filter_categories_keyboard(config_service.resolve_filters(profile=profile), profile)); return
        if data.startswith("fcat|"):
            _, profile, category = data.split("|",2); values=config_service.get_filter_fields(category, profile=profile); context.user_data.pop("pending_filter_edit", None); await query.edit_message_text(_format_filter_category(profile, category, values), reply_markup=build_filter_fields_keyboard(profile, category, values)); return
        if data.startswith("fedit|"):
            _, profile, category, field = data.split("|",3); current=config_service.get_filter_value(category, field, profile=profile); context.user_data["pending_filter_edit"]={"profile":profile,"category":category,"field":field}; await query.message.reply_text(f"Send new value for {profile}.{category}.{field}\nCurrent: {current}\nUse /cancel to stop."); return
        if data=="freset|all": config_service.reset_all_filter_overrides(); context.user_data.pop("pending_filter_edit", None); await query.edit_message_text("All filter overrides cleared.", reply_markup=build_filter_profile_menu_keyboard(config_service.get_profile_preset_map(), config_service.get_active_filter_profile())); return
        if data.startswith("freset_profile|"):
            profile=data.split("|",1)[1].lower(); config_service.reset_filter_overrides(profile=profile); await query.edit_message_text(f"Reset all filter overrides for {profile}.", reply_markup=build_filter_profile_menu_keyboard(config_service.get_profile_preset_map(), profile)); return
        if data.startswith("freset|"):
            _, profile, category = data.split("|",2); config_service.reset_filter_overrides(category=category, profile=profile); values=config_service.get_filter_fields(category, profile=profile); context.user_data.pop("pending_filter_edit", None); await query.edit_message_text(f"Reset {profile}.{category} overrides.", reply_markup=build_filter_fields_keyboard(profile, category, values)); return
        if data.startswith("set|preset|"): config_service.set_active_preset(data.split("|",2)[2]); await query.edit_message_text(f"Overall preset updated to: {data.split('|',2)[2]}", reply_markup=build_control_panel_keyboard()); return
        if data.startswith("set|mode|"): config_service.set_execution_mode(data.split("|",2)[2]); await query.edit_message_text(f"Execution mode updated to: {data.split('|',2)[2]}", reply_markup=build_control_panel_keyboard()); return
        if data.startswith("toggle|strategy|"):
            strategy_name=data.split("|",2)[2]; states=config_service.get_strategy_states(); current=bool(states.get(strategy_name, True)); config_service.settings_repo.set_strategy_state(strategy_name, not current); await query.edit_message_text("Strategies updated", reply_markup=build_strategies_keyboard(config_service.get_strategy_states())); return
        await query.edit_message_text("Unknown control panel action.", reply_markup=build_control_panel_keyboard())
    return [CommandHandler("start", start_command),CommandHandler("panel", panel_command),CommandHandler("config", _config),CommandHandler("status", _config),CommandHandler("scan", _scan),CommandHandler("scan_market", _scan_market),CommandHandler("scan_premarket", _scan_premarket),CommandHandler("scan_midday", _scan_midday),CommandHandler("scan_overnight", _scan_overnight),CommandHandler("scan_news", _scan_news),CommandHandler("scan_events", _scan_events),CommandHandler("scan_catalyst", _scan_catalyst),CommandHandler("scan_status", _scan_status),CommandHandler("cancel", cancel_command),MessageHandler(filters.TEXT & ~filters.COMMAND, _pending_text),CallbackQueryHandler(_guarded_callback)]
