from telegram.ext import CommandHandler


def build_outcome_handlers(repo):
    async def setup_performance_command(update, context):
        summary = repo.setup_performance_summary(limit=250)
        await update.message.reply_text(str(summary))

    async def confidence_calibration_command(update, context):
        summary = repo.confidence_calibration_summary(limit=500)
        await update.message.reply_text(str(summary))

    return [
        CommandHandler('setup_performance', setup_performance_command),
        CommandHandler('confidence_calibration', confidence_calibration_command),
    ]
