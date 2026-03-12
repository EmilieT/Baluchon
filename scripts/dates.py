# scripts/dates.py
from datetime import datetime

def register_template_filters(app):
    @app.template_filter('date')
    def format_date(timestamp):
        """Formate un timestamp en date lisible (ex: 25/12/2024 14:30)."""
        return datetime.fromtimestamp(timestamp).strftime('%d/%m/%Y %H:%M')

    @app.template_filter('format_datetime')
    def format_datetime(value, format='%d/%m/%Y %H:%M'):
        """Formate un objet datetime selon le format spécifié."""
        if value is None:
            return ""
        return value.strftime(format)
