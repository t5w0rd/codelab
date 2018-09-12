#!/bin/sh
while :; do
    ssh -TnNR 25565:0.0.0.0:25565 t5w0rd@mc.tutils.com -p56022 -o GatewayPorts=yes
    sleep 1
done

