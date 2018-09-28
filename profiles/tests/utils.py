from io import BytesIO

from PIL import Image


def get(api_client, url, status_code=200):
    response = api_client.get(url)
    assert response.status_code == status_code, 'Expected status code {} but got {} with data {}'.format(
        status_code, response.status_code, response.data)
    return response.data


def put_update(api_client, url, data=None, status_code=200):
    response = api_client.put(url, data)
    assert response.status_code == status_code, 'Expected status code {} but got {} with data {}'.format(
        status_code, response.status_code, response.data)
    return response.data


def post_create(api_client, url, data=None, status_code=201):
    response = api_client.post(url, data)
    assert response.status_code == status_code, 'Expected status code {} but got {} with data {}'.format(
        status_code, response.status_code, response.data)
    return response.data


def delete(api_client, url, status_code=204):
    response = api_client.delete(url)
    assert response.status_code == status_code, 'Expected status code {} but got {} with data {}'.format(
        status_code, response.status_code, response.data)
    return response.data


def create_in_memory_image_file(name='test_image', image_format='png', size=(512, 256), color=(128, 128, 128)):
    image = Image.new('RGBA', size=size, color=color)
    file = BytesIO()
    file.name = '{}.{}'.format(name, image_format)
    image.save(file, format=image_format)
    file.seek(0)
    return file
