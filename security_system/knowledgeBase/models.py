# -*- coding:utf-8 -*-
from __future__ import unicode_literals

from django.db import models


class vendor(models.Model):
    name = models.CharField(max_length=255, primary_key=True)
    country = models.CharField(max_length=255, null=True)
    url = models.CharField(max_length=255, null=True)


class VulnerabilityDevice(models.Model):
    name = models.CharField(max_length=255, primary_key=True)
    vendor = models.CharField(max_length=255, null=True)
    deviceType = models.CharField(max_length=255, null=True)


class instance(models.Model):
    name = models.CharField(max_length=255, primary_key=True)
    vendor = models.CharField(max_length=255, null=True, verbose_name='厂商')
    ins_type = models.CharField(max_length=255, null=True, verbose_name='协议')
    ip = models.CharField(max_length=255, null=True)
    city = models.CharField(max_length=255, null=True)
    country = models.CharField(max_length=255, null=True)
    continent = models.CharField(max_length=255, null=True, verbose_name='洲')
    asn = models.CharField(max_length=255, null=True)
    lat = models.CharField(max_length=255, null=True, verbose_name='纬度')
    lon = models.CharField(max_length=255, null=True, verbose_name='经度')
    hostname = models.CharField(max_length=255, null=True)
    service = models.CharField(max_length=255, null=True)
    os = models.CharField(max_length=255, null=True, verbose_name='操作系统类型')
    app = models.CharField(max_length=255, null=True)
    extrainfo = models.CharField(max_length=255, null=True)
    version = models.CharField(max_length=255, null=True)
    port = models.CharField(max_length=255, null=True)
    banner = models.TextField(null=True)
    timestamp = models.CharField(max_length=255, null=True)
    type_index = models.CharField(max_length=255, null=True)
    organization = models.CharField(max_length=30, blank=True, null=True)
    isp = models.CharField(max_length=30, blank=True, null=True)
    add_time = models.DateTimeField(verbose_name='首次添加时间')
    from_scan = models.IntegerField(blank=True, null=True, verbose_name='来自扫描')  # 0 -> False, 1 -> True
    from_spider = models.IntegerField(blank=True, null=True, verbose_name='来自爬虫')  # 0 -> False, 1 -> True


class vulnerability(models.Model):
    name = models.CharField(max_length=255, primary_key=True)
    vendor = models.CharField(max_length=255, null=True)
    level = models.CharField(max_length=255, null=True)
    description = models.CharField(max_length=1024, null=True)
    url = models.CharField(max_length=255, null=True)
    mitigation = models.CharField(max_length=255, null=True)
    provider = models.CharField(max_length=255, null=True)
    date = models.CharField(max_length=255, null=True)


class dev2vul(models.Model):
    name = models.CharField(max_length=255, primary_key=True)
    device = models.CharField(max_length=255)
    vulnerability = models.CharField(max_length=255)
