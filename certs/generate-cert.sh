#!/bin/bash
# SSL certificate generation script with CA support
# This script generates a CA certificate and server certificate signed by the CA
# Clients can import ca.crt to their root certificate store to trust the server

CERT_DIR="${CERT_DIR:-/certs}"
CA_KEY="$CERT_DIR/ca.key"
CA_CERT="$CERT_DIR/ca.crt"
SERVER_KEY="$CERT_DIR/server.key"
SERVER_CERT="$CERT_DIR/server.crt"
SERVER_CSR="$CERT_DIR/server.csr"
EXTFILE="$CERT_DIR/server.ext"

# Check if server certificates already exist
if [ -f "$SERVER_CERT" ] && [ -f "$SERVER_KEY" ]; then
    echo "SSL certificates already exist."
    echo "CA Certificate: $CA_CERT"
    echo "Server Certificate: $SERVER_CERT"
    echo "Server Key: $SERVER_KEY"
    exit 0
fi

echo "============================================"
echo "Generating SSL certificates..."
echo "============================================"

# Step 1: Generate CA certificate (if not exists)
if [ ! -f "$CA_CERT" ]; then
    echo ""
    echo "[1/4] Generating CA certificate (Root Certificate)..."
    openssl req -x509 -nodes -days 3650 -newkey rsa:4096 \
        -keyout "$CA_KEY" \
        -out "$CA_CERT" \
        -subj "/C=JP/ST=Tokyo/L=Tokyo/O=AI Describer Medical/OU=IT Department/CN=AI Describer Medical Root CA"
    
    chmod 600 "$CA_KEY"
    chmod 644 "$CA_CERT"
    echo "✓ CA certificate generated: $CA_CERT"
    echo "  → Distribute this file to clients for importing to root certificate store"
else
    echo ""
    echo "[1/4] CA certificate already exists: $CA_CERT"
fi

# Step 2: Generate server private key
echo ""
echo "[2/4] Generating server private key..."
openssl genrsa -out "$SERVER_KEY" 2048
chmod 600 "$SERVER_KEY"
echo "✓ Server private key generated: $SERVER_KEY"

# Step 3: Build SubjectAltName extension
echo ""
echo "[3/4] Configuring Subject Alternative Names..."
SAN="DNS:localhost,DNS:*.localhost,IP:127.0.0.1"

# Add additional IP addresses from SERVER_IPS environment variable
# Format: SERVER_IPS="192.168.1.100,10.0.0.50"
if [ ! -z "$SERVER_IPS" ]; then
    echo "Adding additional IP addresses: $SERVER_IPS"
    IFS=',' read -ra IPS <<< "$SERVER_IPS"
    for ip in "${IPS[@]}"; do
        # Trim whitespace
        ip=$(echo "$ip" | xargs)
        if [ ! -z "$ip" ]; then
            SAN="$SAN,IP:$ip"
        fi
    done
fi

echo "SubjectAltName: $SAN"

# Create extension file for SAN
cat > "$EXTFILE" <<EOF
subjectAltName=$SAN
keyUsage=digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth
EOF

# Step 4: Generate CSR and sign with CA
echo ""
echo "[4/4] Generating Certificate Signing Request and signing with CA..."
openssl req -new -key "$SERVER_KEY" \
    -out "$SERVER_CSR" \
    -subj "/C=JP/ST=Tokyo/L=Tokyo/O=AI Describer Medical/OU=IT Department/CN=localhost"

openssl x509 -req -days 365 \
    -in "$SERVER_CSR" \
    -CA "$CA_CERT" \
    -CAkey "$CA_KEY" \
    -CAcreateserial \
    -out "$SERVER_CERT" \
    -extfile "$EXTFILE"

chmod 644 "$SERVER_CERT"
echo "✓ Server certificate signed by CA: $SERVER_CERT"

# Cleanup
rm -f "$SERVER_CSR" "$EXTFILE"

echo ""
echo "============================================"
echo "SSL certificates generated successfully!"
echo "============================================"
echo ""
echo "Files created:"
echo "  - CA Certificate:     $CA_CERT  ← Import to client root certificate store"
echo "  - CA Private Key:     $CA_KEY   ← Keep secure, do not distribute"
echo "  - Server Certificate: $SERVER_CERT"
echo "  - Server Private Key: $SERVER_KEY"
echo ""
echo "To trust this certificate:"
echo "  1. Import $CA_CERT to your client's root certificate store"
echo "  2. Windows: certmgr.msc → Trusted Root Certification Authorities"
echo "  3. macOS: Keychain Access → System → Import → Always Trust"
echo "  4. Linux: Copy to /usr/local/share/ca-certificates/ and run update-ca-certificates"
echo ""
echo "Alternative: Use your organization's CA to sign server certificate"
echo "  → Replace server.crt and server.key with certificates signed by your internal CA"
echo ""
