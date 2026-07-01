import logging

from django.conf import settings
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

logger = logging.getLogger(__name__)


def rsa_signer(message):
    private_key = serialization.load_pem_private_key(
        settings.AWS_CLOUDFRONT_KEY,
        password=None,
        backend=default_backend(),
    )
    return private_key.sign(message, padding.PKCS1v15(), hashes.SHA1())
