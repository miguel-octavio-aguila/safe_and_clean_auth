from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage


class StaticStorage(S3Boto3Storage):
    location = 'static'
    custom_domain = settings.AWS_S3_DOMAIN
    default_acl = None
    querystring_auth = False


class MediaStorage(S3Boto3Storage):
    location = 'media'
    custom_domain = settings.AWS_S3_CUSTOM_DOMAIN
    default_acl = None
    file_overwrite = False
