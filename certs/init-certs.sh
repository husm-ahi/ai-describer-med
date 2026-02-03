#!/bin/bash
set -e

# ================================================
# SSL/TLS Certificate Auto-Generation Script
# ================================================
# This script automatically generates self-signed certificates
# if they don't already exist or if custom certificate paths
# are not provided via environment variables.
#
# Environment Variables:
#   SSL_CERT_PATH: Path to custom server certificate (optional)
#   SSL_KEY_PATH: Path to custom server key (optional)
#   SERVER_NAME: Server hostname for SubjectAltName (default: localhost)
#   SERVER_IPS: Comma-separated IP addresses for SubjectAltName (optional)
#   CERT_DIR: Directory to store generated certificates (default: /certs)

CERT_DIR="${CERT_DIR:-/certs}"
CA_KEY="${CERT_DIR}/ca.key"
CA_CERT="${CERT_DIR}/ca.crt"
SERVER_KEY="${CERT_DIR}/server.key"
SERVER_CERT="${CERT_DIR}/server.crt"
SERVER_CSR="${CERT_DIR}/server.csr"
EXTFILE="${CERT_DIR}/v3.ext"

SERVER_NAME="${SERVER_NAME:-localhost}"

echo "=========================================="
echo "SSL/TLS Certificate Initialization"
echo "=========================================="

# Check if custom certificates are provided via environment variables
if [ -n "$SSL_CERT_PATH" ] && [ -n "$SSL_KEY_PATH" ]; then
    echo "✓ Custom certificate paths provided:"
    echo "  - Certificate: $SSL_CERT_PATH"
    echo "  - Private Key: $SSL_KEY_PATH"
    
    # Copy custom certificates to expected location
    if [ -f "$SSL_CERT_PATH" ] && [ -f "$SSL_KEY_PATH" ]; then
        cp "$SSL_CERT_PATH" "$SERVER_CERT"
        cp "$SSL_KEY_PATH" "$SERVER_KEY"
        chmod 644 "$SERVER_CERT"
        chmod 600 "$SERVER_KEY"
        echo "✓ Custom certificates copied successfully"
        echo ""
        echo "No CA certificate generation required (using organizational CA)"
        exit 0
    else
        echo "✗ Error: Custom certificate files not found"
        echo "  Please check the paths in SSL_CERT_PATH and SSL_KEY_PATH"
        exit 1
    fi
fi

# Check if certificates already exist
if [ -f "$SERVER_CERT" ] && [ -f "$SERVER_KEY" ] && [ -f "$CA_CERT" ]; then
    echo "✓ Certificates already exist, skipping generation"
    echo "  - CA Certificate: $CA_CERT"
    echo "  - Server Certificate: $SERVER_CERT"
    echo "  - Server Key: $SERVER_KEY"
    exit 0
fi

echo "⚙ Generating self-signed certificates..."
echo ""

# ================================================
# Step 1: Generate CA Certificate
# ================================================
echo "Step 1/4: Generating CA (Certificate Authority) certificate..."

openssl req -x509 -nodes -days 3650 -newkey rsa:4096 \
    -keyout "$CA_KEY" \
    -out "$CA_CERT" \
    -subj "/C=JP/ST=Shizuoka/L=Hamamatsu/O=AI Describer Medical/OU=Development/CN=AI Describer Medical Root CA" \
    2>/dev/null

chmod 600 "$CA_KEY"
chmod 644 "$CA_CERT"

echo "✓ CA certificate generated (valid for 10 years)"
echo "  - CA Certificate: $CA_CERT"
echo "  - CA Private Key: $CA_KEY (keep secure!)"
echo ""

# ================================================
# Step 2: Generate Server Private Key
# ================================================
echo "Step 2/4: Generating server private key..."

openssl genrsa -out "$SERVER_KEY" 2048 2>/dev/null
chmod 600 "$SERVER_KEY"

echo "✓ Server private key generated"
echo "  - Server Key: $SERVER_KEY"
echo ""

# ================================================
# Step 3: Create OpenSSL Configuration for SubjectAltName
# ================================================
echo "Step 3/4: Creating certificate configuration..."

# Build SubjectAltName
SAN="DNS:localhost,DNS:*.localhost,IP:127.0.0.1"

# Add custom server name if provided
if [ -n "$SERVER_NAME" ] && [ "$SERVER_NAME" != "localhost" ]; then
    SAN="${SAN},DNS:${SERVER_NAME},DNS:*.${SERVER_NAME}"
fi

# Add custom IP addresses if provided
if [ -n "$SERVER_IPS" ]; then
    # Split comma-separated IPs and add to SAN
    IFS=',' read -ra IP_ARRAY <<< "$SERVER_IPS"
    for ip in "${IP_ARRAY[@]}"; do
        # Trim whitespace
        ip=$(echo "$ip" | xargs)
        if [ -n "$ip" ]; then
            SAN="${SAN},IP:${ip}"
        fi
    done
fi

# Create v3.ext file for SubjectAltName
cat > "$EXTFILE" << EOF
authorityKeyIdentifier=keyid,issuer
basicConstraints=CA:FALSE
keyUsage = digitalSignature, nonRepudiation, keyEncipherment, dataEncipherment
subjectAltName = ${SAN}
EOF

echo "✓ Certificate configuration created"
echo "  SubjectAltName: ${SAN}"
echo ""

# ================================================
# Step 4: Generate Certificate Signing Request and Sign with CA
# ================================================
echo "Step 4/4: Generating and signing server certificate..."

# Generate CSR
openssl req -new -key "$SERVER_KEY" -out "$SERVER_CSR" \
    -subj "/C=JP/ST=Shizuoka/L=Hamamatsu/O=AI Describer Medical/OU=Development/CN=${SERVER_NAME}" \
    2>/dev/null

# Sign the certificate with CA
openssl x509 -req -days 365 \
    -in "$SERVER_CSR" \
    -CA "$CA_CERT" \
    -CAkey "$CA_KEY" \
    -CAcreateserial \
    -out "$SERVER_CERT" \
    -extfile "$EXTFILE" \
    2>/dev/null

chmod 644 "$SERVER_CERT"

# Cleanup temporary files
rm -f "$SERVER_CSR" "$EXTFILE" "${CERT_DIR}/ca.srl"

echo "✓ Server certificate generated and signed (valid for 1 year)"
echo "  - Server Certificate: $SERVER_CERT"
echo ""

# ================================================
# Summary and Instructions
# ================================================
echo "=========================================="
echo "✓ Certificate Generation Complete!"
echo "=========================================="
echo ""
echo "Generated files:"
echo "  1. ca.crt         - CA certificate (distribute to clients)"
echo "  2. ca.key         - CA private key (keep secure!)"
echo "  3. server.crt     - Server certificate (for Nginx)"
echo "  4. server.key     - Server private key (for Nginx)"
echo ""
echo "To trust the self-signed certificate on client devices:"
echo ""
echo "Windows:"
echo "  1. Copy 'certs/ca.crt' to client machine"
echo "  2. Double-click ca.crt → Install Certificate"
echo "  3. Store Location: Local Machine"
echo "  4. Place in: Trusted Root Certification Authorities"
echo ""
echo "macOS:"
echo "  1. Copy 'certs/ca.crt' to client machine"
echo "  2. Double-click ca.crt → Add to 'System' keychain"
echo "  3. Open Keychain Access, find the certificate"
echo "  4. Double-click → Trust → Always Trust"
echo ""
echo "Linux (Ubuntu/Debian):"
echo "  sudo cp certs/ca.crt /usr/local/share/ca-certificates/ai-describer-med-ca.crt"
echo "  sudo update-ca-certificates"
echo ""
echo "=========================================="
