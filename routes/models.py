from django.db import models
from django.core.validators import MinValueValidator


class FuelStation(models.Model):
    """Model to store fuel station data from the CSV file."""

    opis_truckstop_id = models.IntegerField(db_index=True)
    truckstop_name = models.CharField(max_length=255)
    address = models.CharField(max_length=500)
    city = models.CharField(max_length=100, db_index=True)
    state = models.CharField(max_length=2, db_index=True)
    rack_id = models.IntegerField()
    retail_price = models.DecimalField(
        max_digits=6,
        decimal_places=5,
        validators=[MinValueValidator(0)]
    )

    # Geocoded coordinates (will be populated)
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        db_index=True
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        db_index=True
    )

    class Meta:
        ordering = ['retail_price']
        indexes = [
            models.Index(fields=['state', 'city']),
            models.Index(fields=['retail_price']),
            models.Index(fields=['latitude', 'longitude']),
        ]

    def __str__(self):
        return f"{self.truckstop_name} - {self.city}, {self.state} (${self.retail_price})"
