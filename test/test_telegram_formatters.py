from telegram_bot.formatters import format_daily_report

def test_daily_report():
    text=format_daily_report('Title',['one','two'])
    assert 'Title' in text
