from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()

class SignUpViewTests(TestCase):
    def setUp(self):
        self.signup_url = reverse('accounts:sign-up') 
        self.login_url = reverse('accounts:login')

    def test_successful_signup(self):
        form_data = {
            'username': 'newuser',
            'password1': 'StrongSecurePass123!',
            'password2': 'StrongSecurePass123!',
        }
        response = self.client.post(self.signup_url, data=form_data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.login_url)
        self.assertTrue(User.objects.filter(username='newuser').exists())
        
        user = User.objects.get(username='newuser')
        self.assertTrue(user.check_password('StrongSecurePass123!'))

    def test_failed_signup_passwords_dont_match(self):
        form_data = {
            'username': 'baduser',
            'password1': 'StrongSecurePass123!',
            'password2': 'DifferentPassword123!',
        }
        response = self.client.post(self.signup_url, data=form_data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='baduser').exists())
        self.assertFalse(response.context['form'].is_valid())

    def test_failed_signup_duplicate_username(self):
        User.objects.create_user(username='existinguser', password='Password123!')
        form_data = {
            'username': 'existinguser',
            'password1': 'NewPassword123!',
            'password2': 'NewPassword123!',
        }
        response = self.client.post(self.signup_url, data=form_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.filter(username='existinguser').count(), 1)
        self.assertIn('username', response.context['form'].errors)
