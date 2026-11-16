from rest_framework.throttling import AnonRateThrottle


class PhoneCodeThrottle(AnonRateThrottle):
    rate = "5/hour"


class VerifyCodeThrottle(AnonRateThrottle):
    rate = "5/minute"
