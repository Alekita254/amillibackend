from unittest import mock
from django.test import TestCase, override_settings
from django.core import mail
from api.models import User
@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend', ALLOWED_HOSTS=['testserver'])
class T(TestCase):
    def test_flow(self):
        r = self.client.post('/api/register/', {'username':'bob','email':'Bob@x.com','password':'pass12345'}, content_type='application/json')
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('/api/verify-email/', mail.outbox[0].body)
        tok = r.json()['data']['tokens']['access']
        p = self.client.get('/api/profile/', HTTP_AUTHORIZATION='Bearer '+tok)
        self.assertEqual(p.status_code, 200, p.content)
        self.assertEqual(self.client.post('/api/token/', {'email':'bob@x.com','password':'pass12345'}, content_type='application/json').status_code, 400)
        mail.outbox.clear()
        for e in ('nobody@x.com','bob@x.com'):
            self.assertEqual(self.client.post('/api/password-reset/', {'email':e}, content_type='application/json').status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('reset-password?uid=', mail.outbox[0].body)
        j = self.client.post('/api/joinus/submit/', {'email':'bad'}, content_type='application/json')
        self.assertEqual(j.status_code, 400, j.content)


import json
from django.core import mail as _mail
from api.models import Author, Blog, Comment
from cohorts.models import Cohort
from rest_framework.test import APIClient


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend', ALLOWED_HOSTS=['testserver'])
class ContentAccessTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user('staff', 'staff@x.com', 'pass12345', is_staff=True, email_verified=True)
        self.author = Author.objects.create(name='A', email='a@x.com')
        self.anon = APIClient()
        self.admin = APIClient()
        self.admin.force_authenticate(self.staff)

    def post_blog(self, client, title='Hello World'):
        return client.post('/api/blogs/', {'data': json.dumps({
            'title': title, 'description': 'd', 'content': 'c',
            'author_id': self.author.pk, 'category': 'c', 'tags': 't'})}, format='multipart')

    def test_writes_need_staff(self):
        self.assertEqual(self.post_blog(self.anon).status_code, 401)
        self.assertEqual(self.anon.delete('/api/authors/%d/' % self.author.pk).status_code, 401)
        self.assertEqual(self.anon.post('/api/cohorts/', {'title': 'x'}, format='json').status_code, 401)
        self.assertEqual(self.anon.get('/api/blogs/').status_code, 200)

    def test_create_slug_and_response(self):
        r1, r2 = self.post_blog(self.admin), self.post_blog(self.admin)
        self.assertEqual((r1.status_code, r2.status_code), (201, 201), r2.content)
        self.assertEqual(r1.json()['data']['slug'], 'hello-world')
        self.assertEqual(r2.json()['data']['slug'], 'hello-world-2')
        bad = self.admin.post('/api/blogs/', {'data': '{nope'}, format='multipart')
        self.assertEqual(bad.status_code, 400)

    def test_views_and_private_author_email(self):
        slug = self.post_blog(self.admin).json()['data']['slug']
        self.anon.get('/api/blogs/%s/' % slug)
        d = self.anon.get('/api/blogs/%s/' % slug).json()['data']
        self.assertEqual(d['views'], 2)
        self.assertNotIn('email', d['author'])
        self.assertIn('email', self.admin.get('/api/blogs/%s/' % slug).json()['data']['author'])

    def test_comments(self):
        b = Blog.objects.create(title='B', description='d', content='c', author=self.author, category='c', tags='t')
        b2 = Blog.objects.create(title='B2', description='d', content='c', author=self.author, category='c', tags='t')
        top = self.anon.post('/api/comments/', {'name': 'n', 'email': 'e@x.com', 'message': 'm', 'blog': b.pk}, format='json')
        self.assertEqual(top.status_code, 201)
        self.assertNotIn('email', top.json()['data'])
        pid = top.json()['data']['id']
        wrong = self.anon.post('/api/comments/', {'name': 'n', 'message': 'm', 'blog': b2.pk, 'parent': pid}, format='json')
        self.assertEqual(wrong.status_code, 400)
        self.anon.post('/api/comments/', {'name': 'n', 'message': 'r', 'blog': b.pk, 'parent': pid}, format='json')
        lst = self.anon.get('/api/comments/blog/%d/' % b.pk).json()['data']['comments']
        self.assertEqual(len(lst), 1)
        self.assertEqual(len(lst[0]['replies']), 1)
        self.anon.post('/api/comments/%d/like/' % pid)
        self.assertEqual(Comment.objects.get(pk=pid).likes, 1)
        self.assertEqual(self.anon.delete('/api/comments/%d/' % pid).status_code, 401)

    def test_cohort_drafts_hidden(self):
        Cohort.objects.create(title='Draft', published=False)
        Cohort.objects.create(title='Live', published=True)
        self.assertEqual(len(self.anon.get('/api/cohorts/').json()['data']), 1)
        self.assertEqual(self.anon.get('/api/cohorts/draft/').status_code, 404)
        self.assertEqual(len(self.admin.get('/api/cohorts/').json()['data']), 2)

    def test_send_email_staff_only_and_bad_token_is_anonymous(self):
        body = {'subject': 's', 'message': 'm', 'recipients': ['r@x.com']}
        self.assertEqual(self.anon.post('/api/send-email/', body, format='json').status_code, 401)
        self.assertEqual(self.admin.post('/api/send-email/', body, format='json').status_code, 200)
        self.assertEqual(len(_mail.outbox), 1)
        stale = APIClient(HTTP_AUTHORIZATION='Bearer not-a-real-token')
        self.assertEqual(stale.get('/api/blogs/').status_code, 200)


class TokenRefreshTests(TestCase):
    def test_refresh_returns_new_access_token(self):
        User.objects.create_user('ann', 'ann@x.com', 'pass12345', email_verified=True)
        c = APIClient()
        tokens = c.post('/api/token/', {'email': 'ann@x.com', 'password': 'pass12345'}, format='json').json()['data']['tokens']
        r = c.post('/api/token/refresh/', {'refresh': tokens['refresh']}, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        self.assertIn('access', r.json())
        self.assertEqual(c.post('/api/token/refresh/', {'refresh': 'garbage'}, format='json').status_code, 401)


import io
import shutil
import tempfile
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile

_MEDIA = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=_MEDIA, ALLOWED_HOSTS=['testserver'])
class ImageUploadTests(TestCase):
    """Exercises Pillow through Django's ImageField (guards dependency upgrades)."""

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(_MEDIA, ignore_errors=True)

    def png(self):
        buf = io.BytesIO()
        Image.new('RGB', (8, 8), 'green').save(buf, 'PNG')
        return SimpleUploadedFile('cover.png', buf.getvalue(), content_type='image/png')

    def test_blog_cover_upload_and_rejection_of_non_image(self):
        staff = User.objects.create_user('s', 's@x.com', 'pass12345', is_staff=True)
        author = Author.objects.create(name='A', email='a@x.com')
        c = APIClient()
        c.force_authenticate(staff)
        data = json.dumps({'title': 'T', 'description': 'd', 'content': 'c',
                           'author_id': author.pk, 'category': 'c', 'tags': 't'})
        ok = c.post('/api/blogs/', {'data': data, 'cover_image': self.png()}, format='multipart')
        self.assertEqual(ok.status_code, 201, ok.content)
        self.assertTrue(ok.json()['data']['cover_image'].endswith('.png'))
        bad = c.post('/api/blogs/', {'data': data, 'cover_image': SimpleUploadedFile('x.png', b'not an image')}, format='multipart')
        self.assertEqual(bad.status_code, 400)


from django.test import Client
from django.urls import reverse


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend', ALLOWED_HOSTS=['testserver'])
class AdminTestEmailTests(TestCase):
    def setUp(self):
        self.url = reverse('admin:send_test_email')
        self.staff = User.objects.create_user('st', 'staff@x.com', 'pass12345', is_staff=True)
        self.boss = User.objects.create_superuser('su', 'boss@x.com', 'pass12345')

    def login(self, user):
        c = Client()
        c.force_login(user)
        return c

    def test_only_staff_can_open_it(self):
        self.assertEqual(Client().get(self.url).status_code, 302)  # to the admin login
        plain = User.objects.create_user('p', 'p@x.com', 'pass12345')
        self.assertEqual(self.login(plain).get(self.url).status_code, 302)
        r = self.login(self.staff).get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Send test email')

    def test_staff_always_send_to_their_own_address(self):
        r = self.login(self.staff).post(self.url, {'to': 'victim@example.com'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['staff@x.com'])  # the field is ignored for non-superusers
        self.assertContains(r, 'staff@x.com')

    def test_superuser_can_pick_the_recipient(self):
        self.login(self.boss).post(self.url, {'to': 'other@example.com'})
        self.assertEqual(mail.outbox[0].to, ['other@example.com'])
        self.login(self.boss).post(self.url, {})  # blank means themselves
        self.assertEqual(mail.outbox[1].to, ['boss@x.com'])

    def test_bad_recipient_or_no_address_sends_nothing(self):
        self.assertContains(self.login(self.boss).post(self.url, {'to': 'not-an-email'}), 'valid email')
        no_email = User.objects.create_user('ne', '', 'pass12345', is_staff=True)
        self.assertContains(self.login(no_email).post(self.url, {}), 'no email address')
        self.assertEqual(len(mail.outbox), 0)

    def test_a_mail_server_failure_is_shown_not_a_500(self):
        with mock.patch('api.admin.send_mail', side_effect=OSError('smtp down')):
            r = self.login(self.staff).post(self.url, {})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'smtp down')

    def test_the_admin_sidebar_links_to_it(self):
        self.assertContains(self.login(self.boss).get(reverse('admin:index')), 'send-test-email')
