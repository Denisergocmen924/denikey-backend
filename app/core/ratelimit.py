from starlette.requests import Request
from slowapi.util import get_remote_address


def get_client_ip(request: Request) -> str:
    """Rate limiting ve denetim kaydı için gerçek istemci IP'sini döndürür.

    Fly.io proxy'si her istekte `Fly-Client-IP` başlığını gerçek istemci IP'siyle
    ÜZERİNE YAZAR; istemci bu değeri spoof edemez. Buna karşılık `X-Forwarded-For`
    istemci tarafından doldurulabildiği için rate-limit anahtarı olarak güvenilmez
    (spoof edilerek limit baypası yapılabilir).

    Fly dışı ortamda (yerel geliştirme) başlık yoksa soket adresine düşülür.
    """
    fly_ip = request.headers.get("Fly-Client-IP")
    if fly_ip:
        return fly_ip.strip()
    return get_remote_address(request)
