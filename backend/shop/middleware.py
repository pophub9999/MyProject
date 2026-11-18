import hashlib
from datetime import timedelta
from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from .models import LoginAttempt

class LoginThrottleMiddleware:
    def __init__(self,get_response): self.get_response=get_response
    def __call__(self,request):
        if request.method!="POST" or request.path not in ("/admin/login/","/setup/"): return self.get_response(request)
        client=request.META.get("HTTP_X_REAL_IP",request.META.get("REMOTE_ADDR","unknown"))
        username=request.POST.get("username","").casefold()[:150]
        keys=[hashlib.sha256(("ip:"+client).encode()).hexdigest()]
        if username: keys.append(hashlib.sha256(("user:"+username).encode()).hexdigest())
        now=timezone.now()
        with transaction.atomic():
            LoginAttempt.objects.filter(started_at__lt=now-timedelta(hours=24)).delete()
            for key in keys:
                row,_=LoginAttempt.objects.get_or_create(key=key)
                if row.started_at<now-timedelta(minutes=15): row.attempts,row.started_at=0,now
                if row.attempts>=10:
                    response=HttpResponse("Demasiadas tentativas. Tenta novamente dentro de 15 minutos.",status=429)
                    response["Retry-After"]="900"
                    return response
                row.attempts+=1
                row.save()
        response=self.get_response(request)
        if response.status_code==302 and request.user.is_authenticated: LoginAttempt.objects.filter(key__in=keys).delete()
        return response
