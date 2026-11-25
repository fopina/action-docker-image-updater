from functools import lru_cache

import requests


def _requests():
    # Keep the historical entrypoint.requests patch point working.
    import sys

    entrypoint = sys.modules.get('entrypoint')
    return getattr(entrypoint, 'requests', requests)


@lru_cache
def get_tags(registry, repository):
    tag_url = f'https://{registry}/v2/{repository}/tags/list'
    headers = {}
    r = _requests().get(tag_url)
    if r.status_code == 401:
        # Check WWW-Authenticate header for authentication realm and parameters
        auth_header = r.headers.get('WWW-Authenticate')
        if auth_header and auth_header.startswith('Bearer '):
            # Parse the authentication parameters
            auth_params = {}
            for param in auth_header[len('Bearer ') :].split(','):
                key, _, value = param.strip().partition('=')
                auth_params[key] = value.strip('"')

            # Get authentication token from the realm
            auth_url = auth_params.get('realm')
            if auth_url:
                token_r = _requests().get(
                    auth_url, params={'service': auth_params.get('service'), 'scope': auth_params.get('scope')}
                )
                token_r.raise_for_status()
                token = token_r.json()['token']

                # Retry the request with authentication
                headers = {'Authorization': f'Bearer {token}'}
                r = _requests().get(tag_url, headers=headers)
            else:
                raise ValueError(f'No authentication realm found in WWW-Authenticate header: {auth_header}')
        else:
            raise ValueError(f'Unsupported authentication mechanism in WWW-Authenticate header: {auth_header}')
    elif r.status_code == 200:
        # Some registries don't require authentication
        pass
    else:
        r.raise_for_status()

    tags = r.json()['tags']
    link = r.headers.get('Link', '')
    while 'rel="next"' in link:
        start = link.find('<') + 1
        end = link.find('>')
        tag_url = link[start:end]
        if tag_url[0] == '/':
            tag_url = f'https://{registry}{tag_url}'
        r = _requests().get(tag_url, headers=headers)
        tags.extend(r.json()['tags'])
        link = r.headers.get('Link', '')

    return tags

