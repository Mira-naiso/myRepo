import hvac
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

# Конфигурация Vault-инстансов
VAULT_INSTANCES = [
    {"name": "vault1", "url": "https://vault-app.prod.euce1.aws.indrive.tech/"},
    {"name": "vault2", "url": "https://vault-app.prod.eu.euce1.aws.indrive.tech/"},
    {"name": "vault3", "url": "https://vault-app.prod.sea.apse3.aws.indrive.tech/"},
    {"name": "vault4", "url": "https://vault-app.prod.latam-br.saea1.aws.indrive.tech/"},
    {"name": "vault5", "url": "https://vault-app.prod.latam.saea1.aws.indrive.tech/"},
    {"name": "vault6", "url": "https://vault-app.prod.latam-mx.usea1.aws.indrive.tech/"},
    {"name": "vault7", "url": "https://vault-app.prod.latam-pe.saea1.aws.indrive.tech/"},
    {"name": "vault8", "url": "https://vault-app.prod.latam-co.saea1.aws.indrive.tech/"},
    {"name": "vault9", "url": "https://vault-app.prod.sa.apso1.aws.indrive.tech/"},
    {"name": "vault10", "url": "https://vault-app.prod.sa-in.apso1.aws.indrive.tech/"},
    {"name": "vault11", "url": "https://vault-app.prod.mena.meso1.aws.indrive.tech/"},
    {"name": "vault12", "url": "https://vault-app.prod.mena-eg.meso1.aws.indrive.tech/"},
    {"name": "vault13", "url": "https://vault-app.prod.africa.afso1.aws.indrive.tech/"},
    {"name": "vault14", "url": "https://vault-app.prod.cis.euce1.aws.indrive.tech/"},
    {"name": "vault15", "url": "https://vault-app.prod.usa.usea2.aws.indrive.tech/"},
    {"name": "vault16", "url": "https://vault-app.prod.fr1.baremetal.indrive.tech/"}
]

OIDC_CALLBACK_PORT = 8250
OIDC_REDIRECT_URI = f"http://localhost:{OIDC_CALLBACK_PORT}/oidc/callback"
ROLE = "editor"

SELF_CLOSING_PAGE = '''
<!doctype html>
<html>
<head>
<script>
window.onload = function load() {
  window.open('', '_self', '');
  window.close();
};
</script>
</head>
<body>
  <p>Authentication successful, you can close the browser now.</p>
  <script>
    setTimeout(function() {
          window.close()
    }, 5000);
  </script>
</body>
</html>
'''

def login_oidc_get_token():
    class HttpServ(HTTPServer):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.token = None

    class AuthHandler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            return

        def do_GET(self):
            params = urllib.parse.parse_qs(self.path.split('?')[1])
            self.server.token = params.get('code', [None])[0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(SELF_CLOSING_PAGE.encode())

    server_address = ('', OIDC_CALLBACK_PORT)
    httpd = HttpServ(server_address, AuthHandler)
    httpd.handle_request()
    return httpd.token

def authenticate_with_oidc(client):
    auth_url_response = client.auth.oidc.oidc_authorization_url_request(
        role=ROLE,
        redirect_uri=OIDC_REDIRECT_URI
    )
    auth_url = auth_url_response['data']['auth_url']
    
    webbrowser.open(auth_url)
    token = login_oidc_get_token()

    params = urllib.parse.parse_qs(auth_url.split('?')[1])
    auth_url_nonce = params.get('nonce', [None])[0]
    auth_url_state = params.get('state', [None])[0]

    auth_result = client.auth.oidc.oidc_callback(
        code=token,
        path='oidc',
        nonce=auth_url_nonce,
        state=auth_url_state,
    )

    client.token = auth_result['auth']['client_token']

def get_mounts(client):
    try:
        return list(client.sys.list_mounted_secrets_engines().keys())
    except Exception:
        return []

def search_secrets(client, mounts, search_for):
    found_mounts = []
    for mount in mounts:
        try:
            secret = client.secrets.kv.v2.read_secret_version(
                path="config", mount_point=mount.rstrip('/'), raise_on_deleted_version=True
            )
            if search_for in str(secret['data']['data']):
                found_mounts.append(mount)
        except Exception:
            pass
    return found_mounts

def main():
    search_for = input("Enter token to search: ")
    
    for vault in VAULT_INSTANCES:
        client = hvac.Client(url=vault["url"])
        
        try:
            authenticate_with_oidc(client)
            found_mounts = search_secrets(client, get_mounts(client), search_for)
        except Exception:
            found_mounts = []

        print(f"\nSecret find in {vault['url']}:" if found_mounts else f"\nSecret find in {vault['name']}:\nnot found")
        for mount in found_mounts:
            print(mount)

if __name__ == "__main__":
    main()
