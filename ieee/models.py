from django.db import models


class BaseModel(models.Model):

    class Meta:
        abstract = True

    created_at = models.DateTimeField(null=False, auto_now_add=True)
    modified_at = models.DateTimeField(null=False, auto_now=True)
