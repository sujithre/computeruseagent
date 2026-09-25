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

    rm -f /tmp/corp-ca-*
    awk '/-----BEGIN CERTIFICATE-----/{n++} n>0{print > sprintf("/tmp/corp-ca-%02d.pem", n)}' "$bundle"
    for cert in /tmp/corp-ca-*.pem; do
        [ -s "$cert" ] || continue
        if openssl x509 -in "$cert" -outform DER -out "$cert.der" 2>/dev/null; then
            if certutil -d sql:/root/.pki/nssdb -A -t "C,," -n "$(basename "$cert" .pem)" -i "$cert.der"; then
                echo "  trusted $(openssl x509 -in "$cert" -noout -subject)"
            else
                echo "  could not add to NSS store: $cert"
            fi
        else
            echo "  skipping malformed certificate block: $cert"
        fi
    done
    rm -f /tmp/corp-ca-*

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
