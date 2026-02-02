from django.contrib import admin
from routes.models import FuelStation, IPLog


@admin.register(FuelStation)
class FuelStationAdmin(admin.ModelAdmin):
    list_display = ('truckstop_name', 'city', 'state', 'retail_price', 'latitude', 'longitude')
    list_filter = ('state', 'city')
    search_fields = ('truckstop_name', 'city', 'state', 'address')


@admin.register(IPLog)
class IPLogAdmin(admin.ModelAdmin):
    list_display = ('ip_address', 'ip_location', 'timestamp', 'start_location', 'end_location')
    list_filter = ('timestamp', 'ip_country')
    search_fields = ('ip_address', 'start_location', 'end_location', 'ip_city', 'ip_country')
    readonly_fields = ('ip_address', 'timestamp', 'start_location', 'end_location', 'user_agent', 'ip_city', 'ip_region', 'ip_country')
    ordering = ('-timestamp',)

    def ip_location(self, obj):
        """Display IP location in list view."""
        if obj.ip_city and obj.ip_country:
            return f"{obj.ip_city}, {obj.ip_country}"
        elif obj.ip_country:
            return obj.ip_country
        return "-"
    ip_location.short_description = 'IP Location'
