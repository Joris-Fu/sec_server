# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2017-04-16 10:11
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('tests', '0002_auto_20170416_1007'),
    ]

    operations = [
        migrations.AlterField(
            model_name='myuser',
            name='authLevel',
            field=models.IntegerField(),
        ),
        migrations.AlterField(
            model_name='myuser',
            name='gender',
            field=models.IntegerField(),
        ),
    ]