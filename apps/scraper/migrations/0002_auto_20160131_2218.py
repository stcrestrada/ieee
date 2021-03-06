# -*- coding: utf-8 -*-
# Generated by Django 1.9.1 on 2016-01-31 22:18
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scraper', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ScrapeHistory',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('state', models.CharField(choices=[(b'added', b'added'), (b'done', b'done'), (b'error', b'error'), (b'processing', b'processing')], max_length=256)),
                ('pub_year', models.IntegerField(null=True)),
                ('seq_number', models.IntegerField()),
                ('limit', models.IntegerField(default=1000)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AlterField(
            model_name='articlemodel',
            name='article_id',
            field=models.CharField(max_length=256),
        ),
    ]
