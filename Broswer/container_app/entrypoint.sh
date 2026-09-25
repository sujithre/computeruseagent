#!/bin/sh
set -e

# CORP_CA_B64 holds a base64-encoded PEM bundle, supplied via a Key Vault reference.
install_corporate_ca() {
    [ -n "$CORP_CA_B64" ] || return 0

    bundle=/usr/local/share/ca-certificates/corp-ca.crt
    if ! echo "$CORP_CA_B64" | base64 -d > "$bundle" 2>/dev/null; then
        echo "CORP_CA_B64 is not valid base64; skipping CA install" >&2
        rm -f "$bundle"
        return 0
    fi

    update-ca-certificates

    # Chromium reads its own NSS store rather than the system bundle.
    mkdir -p /root/.pki/nssdb
    certutil -d sql:/root/.pki/nssdb -N --empty-password 2>/dev/null || true

    rm -f /tmp/corp-ca-*.pem
    csplit -sz -f /tmp/corp-ca- -b '%02d.pem' "$bundle" '/-----BEGIN CERTIFICATE-----/' '{*}'
    for cert in /tmp/corp-ca-*.pem; do
        certutil -d sql:/root/.pki/nssdb -A -t "C,," -n "$(basename "$cert" .pem)" -i "$cert"
    done
    rm -f /tmp/corp-ca-*.pem

    # Python HTTP libraries use certifi's bundle, not the system store.
    certifi_bundle=$(python -c "import certifi; print(certifi.where())" 2>/dev/null || true)
    if [ -n "$certifi_bundle" ] && [ -f "$certifi_bundle" ]; then
        cat "$bundle" >> "$certifi_bundle"
        echo "Corporate CA appended to certifi bundle at $certifi_bundle"
    fi

    export SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
    export REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

    echo "Corporate CA certificates installed"
}

install_corporate_ca

exec uvicorn app:app --host 0.0.0.0 --port "${PORT:-8000}"
