from django.conf import settings
from django.conf.urls import url, include, patterns
from django.contrib.auth import login, authenticate
from django.template import Template
from django.utils.encoding import smart_unicode
from testrecorder.settings import AUTH, AUTOLOGIN, TEST_FORM_VALIDATION
from testrecorder.toolbar import toolbar
from testrecorder.utils import replace_insensitive
import testrecorder.urls


_HTML_TYPES = ('text/html', 'application/xhtml+xml')
_STATUS_CODES = (200, 302)


class TestRecorderMiddleware(object):

    def __init__(self):
        self.override_url = True
        self.original_urlconf = settings.ROOT_URLCONF
        self.original_pattern = patterns('', ('', include(self.original_urlconf)),)

    def process_request(self, request):
        if self.override_url:
            testrecorder.urls.urlpatterns += self.original_pattern
            self.override_url = False
            #maybe do it safe-threading for sites with dynamic ROOT_URLCONF
            settings.ROOT_URLCONF = 'testrecorder.urls'

    def process_view(self, request, view_func, view_args, view_kwargs):
        if TEST_FORM_VALIDATION:
            #a little bit of magic
            original_render = Template.render

            def new_render(obj, context):
                if not hasattr(request, '_djtr_context'):
                    request._djtr_context = context
                return original_render(obj, context)

            Template.render = new_render

    def process_response(self, request, response):
        if self._validate_request(request, response):
            toolbar.process_response(request, response)
            if response.status_code == 200 and response['Content-Type'].split(';')[0] in _HTML_TYPES:
                response.content = replace_insensitive(smart_unicode(response.content), u'</body>', smart_unicode(toolbar.render() + u'</body>'))
        return response

    def _validate_request(self, request, response):
        if response.status_code == 304:
            return False
        if testrecorder.urls._PREFIX in request.path:
            return False
        if len(settings.MEDIA_URL) and request.path.startswith(settings.MEDIA_URL):
            return False
        return True


class AutoLoginMiddleware(object):
    logged = False

    def process_request(self, request):
        if not request.user.is_authenticated() and AUTH \
            and AUTOLOGIN and not self.logged:
                self.logged = True
                user = authenticate(**AUTH)
                user and login(request, user)
