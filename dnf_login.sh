#!/bin/bash

uid="1"
private_key="/Users/liujing59/Downloads/privatekey.pem"

data=$(printf "%08x010101010101010101010101010101010101010101010101010101010101010155914510010403030101" "$uid")
data=$(echo -n "$data" | xxd -r -p)
encrypted=$(echo -n "$data" | openssl rsautl -encrypt -inkey "$private_key" -pkcs)
encrypted=$(echo -n "$encrypted" | base64)

echo "$encrypted"
