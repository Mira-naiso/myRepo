import hvac
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

# Конфигурация Vault и OIDC
VAULT_ADDRESS = "https://vault-app.prod.sa.apso1.aws.indrive.tech" #Вставь сюда ссылку на нужный регион
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
    """Авторизация через OIDC и получение токена"""
    class HttpServ(HTTPServer):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.token = None

    class AuthHandler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            return  # Отключаем логи сервера

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
    """Получение токена Vault через OIDC"""
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
    """Получаем список точек монтирования"""
    return list(client.sys.list_mounted_secrets_engines().keys())

def search_secrets(client, mounts, search_for):
    """Поиск значения в секретах"""
    found_mounts = []
    for mount in mounts:
        try:
            secret = client.secrets.kv.v2.read_secret_version(
                path="config", mount_point=mount.rstrip('/'), raise_on_deleted_version=True
            )
            if search_for in str(secret['data']['data']):
                found_mounts.append(mount)
        except Exception:
            pass  # Игнорируем ошибки доступа
    return found_mounts

def main():
    search_for = input("Введите токен для поиска: ")
    client = hvac.Client(url=VAULT_ADDRESS)

    # Авторизация через OIDC
    authenticate_with_oidc(client)

    # Ищем секреты
    found_mounts = search_secrets(client, get_mounts(client), search_for)

    if found_mounts:
        print("\nSecret find in:")
        for mount in found_mounts:
            print(mount)
    else:
        print("\nSecret not found.")

if __name__ == "__main__":
    main()
