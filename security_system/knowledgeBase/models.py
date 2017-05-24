from __future__ import unicode_literals

from django.db import models

class vendor(models.Model):
    name = models.CharField(max_length=256, primary_key=True)
    country = models.CharField(max_length=256, null=True)
    url = models.CharField(max_length=256, null=True)

class device(models.Model):
    name = models.CharField(max_length=256, primary_key=True)
    vendor = models.CharField(max_length=256, null=True)
    deviceType = models.CharField(max_length=256, null=True)

class instance(models.Model):
    name = models.CharField(max_length=256, primary_key=True)
    vendor = models.CharField(max_length=256, null=True)
    ins_type = models.CharField(max_length=256, null=True)
    ip = models.CharField(max_length=256, null=True)
    city = models.CharField(max_length=256, null=True)
    country = models.CharField(max_length=256, null=True)
    continent = models.CharField(max_length=256, null=True)
    asn = models.CharField(max_length=256, null=True)
    lat = models.CharField(max_length=256, null=True)
    lon = models.CharField(max_length=256, null=True)
    hostname = models.CharField(max_length=256, null=True)
    service = models.CharField(max_length=256, null=True)
    os = models.CharField(max_length=256, null=True)
    app = models.CharField(max_length=256, null=True)
    extrainfo = models.CharField(max_length=256, null=True)
    version = models.CharField(max_length=256, null=True)
    port = models.CharField(max_length=256, null=True)
    banner = models.CharField(max_length=1024, null=True)
    timestamp = models.CharField(max_length=256, null=True)
    type_index = models.CharField(max_length=256, null=True)

class vulnerability(models.Model):
    name = models.CharField(max_length=256, primary_key=True)
    vendor = models.CharField(max_length=256, null=True)
    level = models.CharField(max_length=256, null=True)
    description = models.CharField(max_length=1024, null=True)
    url = models.CharField(max_length=256, null=True)
    mitigation = models.CharField(max_length=256, null=True)
    provider = models.CharField(max_length=256, null=True)
    date = models.CharField(max_length=256, null=True)

class dev2vul(models.Model):
    name = models.CharField(max_length=256, primary_key=True)
    device = models.CharField(max_length=256)
    vulnerability = models.CharField(max_length=256)