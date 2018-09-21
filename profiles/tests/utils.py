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
