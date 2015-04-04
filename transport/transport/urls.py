from django.conf.urls import patterns, include, url
from transport.views import *
from transport import settings
from django.views.decorators.csrf import csrf_exempt

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    (r'^media/(?P<path>.*)$', 'django.views.static.serve',
    {'document_root': settings.MEDIA_ROOT}),
)


urlpatterns += patterns('',
    url(r'^$', Frontpage.as_view(), name="frontpage"),
    url(r'^get_way$', csrf_exempt(GetWay.as_view()), name="get_way"),
)

