#!/bin/sh
set -e

# CORP_CA_B64 holds a base64-encoded PEM bundle of corporate CA certificates.
install_corporate_ca() {
    [ -n "$CORP_CA_B64" ] || return 0

    bundle=/usr/local/share/ca-certificates/corp-ca.crt
    raw=/tmp/corp-ca-raw.pem
    clean=/tmp/corp-ca-clean.pem

    # tr strips the CRLF line endings that Windows-generated PEM carries.
    if ! echo "$CORP_CA_B64" | base64 -d 2>/dev/null | tr -d '\r' > "$raw"; then
        echo "CORP_CA_B64 is not valid base64; skipping CA install" >&2
        rm -f "$raw"
        return 0
    fi

    mkdir -p /root/.pki/nssdb
    certutil -d sql:/root/.pki/nssdb -N --empty-password 2>/dev/null || true

    rm -f /tmp/corp-ca-[0-9]*.pem /tmp/corp-ca-[0-9]*.der "$clean"
    awk '
        /-----BEGIN CERTIFICATE-----/ { n++; inblock=1; f=sprintf("/tmp/corp-ca-%02d.pem", n) }
        inblock { print > f }
        /-----END CERTIFICATE-----/  { if (inblock) { close(f); inblock=0 } }
    ' "$raw"

    accepted=0
    for cert in /tmp/corp-ca-[0-9]*.pem; do
        [ -s "$cert" ] || continue
        subject=$(openssl x509 -in "$cert" -noout -subject 2>/dev/null) || {
            echo "  skipping malformed certificate block: $cert"
            continue
        }
        # A leaf certificate is not a trust anchor and would poison the bundle.
        if ! openssl x509 -in "$cert" -noout -ext basicConstraints 2>/dev/null | grep -q "CA:TRUE"; then
            echo "  skipping non-CA certificate: $subject"
            continue
        fi
        openssl x509 -in "$cert" >> "$clean"
        accepted=$((accepted + 1))
        if openssl x509 -in "$cert" -outform DER -out "$cert.der" 2>/dev/null \
           && certutil -d sql:/root/.pki/nssdb -A -t "C,," -n "$(basename "$cert" .pem)" -i "$cert.der"; then
            echo "  trusted $subject"
        else
            echo "  could not add to NSS store: $subject"
        fi
    done
    rm -f /tmp/corp-ca-[0-9]*.pem /tmp/corp-ca-[0-9]*.der "$raw"

    if [ "$accepted" -eq 0 ]; then
        echo "No usable CA certificates in CORP_CA_B64; leaving trust stores untouched" >&2
        rm -f "$clean"
        return 0
    fi

    cp "$clean" "$bundle"
    update-ca-certificates

    # Python HTTP libraries use certifi's bundle, not the system store.
    certifi_bundle=$(python -c "import certifi; print(certifi.where())" 2>/dev/null || true)
    if [ -n "$certifi_bundle" ] && [ -f "$certifi_bundle" ]; then
        [ -f "$certifi_bundle.orig" ] || cp "$certifi_bundle" "$certifi_bundle.orig"
        cat "$certifi_bundle.orig" "$clean" > "$certifi_bundle"
        if python -c "import ssl,sys; ssl.create_default_context(cafile=sys.argv[1])" "$certifi_bundle"; then
            echo "Corporate CA appended to certifi bundle at $certifi_bundle"
        else
            echo "certifi bundle failed to parse after append; restoring original" >&2
            cp "$certifi_bundle.orig" "$certifi_bundle"
        fi
    fi
    rm -f "$clean"

    export SSL_CERT_FILE="$certifi_bundle"
    export REQUESTS_CA_BUNDLE="$certifi_bundle"

    echo "Corporate CA certificates installed ($accepted)"
}

install_corporate_ca

exec uvicorn app:app --host 0.0.0.0 --port "${PORT:-8000}"
