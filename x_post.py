#!/usr/bin/env python3
"""Posta no X (conta Radar Mundo Money) pela API v2 com OAuth 1.0a.

Uso:
  python x_post.py "texto do post"            só mostra o que seria postado (teste)
  python x_post.py "texto do post" --publicar  publica de verdade

Segredos (GitHub > Settings > Secrets > Actions): X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET."""
import os
import sys

LIMITE = 280


def postar(texto):
    from requests_oauthlib import OAuth1Session
    chaves = [os.environ.get(k) for k in ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET")]
    if not all(chaves):
        sys.exit("faltam segredos X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET")
    s = OAuth1Session(*chaves)
    r = s.post("https://api.x.com/2/tweets", json={"text": texto}, timeout=30)
    print(r.status_code, r.text[:300])
    r.raise_for_status()


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    texto = (a[0] if a else "").strip()
    if not texto: sys.exit(__doc__)
    if len(texto) > LIMITE: sys.exit(f"texto com {len(texto)} caracteres (limite {LIMITE})")
    print(f"--- post ({len(texto)} caracteres) ---\n{texto}\n---")
    if "--publicar" in sys.argv: postar(texto)
    else: print("modo teste: nada foi publicado")
