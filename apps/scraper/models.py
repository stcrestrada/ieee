from django.db import models
from django.contrib.postgres.fields import JSONField

from ieee.models import BaseModel

"""

"""

class ScrapeHistory(BaseModel):
    SORT_FIELD = 'ti'
    LIMIT = 1000

    STATE_ADDED = 'added'
    STATE_ERROR = 'error'
    STATE_PROCESSING = 'processing'
    STATE_DONE = 'done'

    STATE_CHOICES = (STATE_ADDED, STATE_DONE, STATE_ERROR, STATE_PROCESSING)

    state = models.CharField(max_length=256, choices=zip(*[STATE_CHOICES] * 2))
    pub_year = models.IntegerField(null=True)
    seq_number = models.IntegerField()
    limit = models.IntegerField(default=LIMIT)


class ArticleModel(BaseModel):

    article_id = models.CharField(max_length=256)
    article_data = JSONField()
