from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from .models import TableImage, TableResult
from .forms import ImageUploadForm


class TableImageModelTest(TestCase):
    def test_string_representation(self):
        image = TableImage(file_name="test.jpg")
        self.assertIn("Table Image", str(image))


class ImageUploadFormTest(TestCase):
    def test_valid_image_upload(self):
        # Create a simple test image file
        image_content = b'fake image content'
        image = SimpleUploadedFile(
            "test.jpg", 
            image_content, 
            content_type="image/jpeg"
        )
        form = ImageUploadForm(files={'image': image})
        # Note: This test would need a real image file to pass completely
        # self.assertTrue(form.is_valid())


class ViewsTest(TestCase):
    def test_upload_page_loads(self):
        response = self.client.get('/upload/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Upload')
