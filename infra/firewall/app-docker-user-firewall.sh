#!/usr/bin/env bash
set -euo pipefail

# DOCKER-USER rules for published ports on the app node.
# These rules restrict direct access to Docker-published backend and bot metrics ports.
# Review interface name and IP plan before applying in another environment.

APP_IFACE="ens18"
WEB_IP="192.168.85.131"
MONITOR_IP="192.168.85.137"
ADMIN_IP="192.168.85.129"

iptables -C DOCKER-USER -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT 2>/dev/null ||   iptables -I DOCKER-USER 1 -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT

iptables -C DOCKER-USER -s "$WEB_IP" -i "$APP_IFACE" -p tcp --dport 8080 -j ACCEPT 2>/dev/null ||   iptables -A DOCKER-USER -s "$WEB_IP" -i "$APP_IFACE" -p tcp --dport 8080 -j ACCEPT

iptables -C DOCKER-USER -s "$MONITOR_IP" -i "$APP_IFACE" -p tcp --dport 8080 -j ACCEPT 2>/dev/null ||   iptables -A DOCKER-USER -s "$MONITOR_IP" -i "$APP_IFACE" -p tcp --dport 8080 -j ACCEPT

iptables -C DOCKER-USER -s "$ADMIN_IP" -i "$APP_IFACE" -p tcp --dport 8080 -j ACCEPT 2>/dev/null ||   iptables -A DOCKER-USER -s "$ADMIN_IP" -i "$APP_IFACE" -p tcp --dport 8080 -j ACCEPT

iptables -C DOCKER-USER -s "$MONITOR_IP" -i "$APP_IFACE" -p tcp --dport 8090 -j ACCEPT 2>/dev/null ||   iptables -A DOCKER-USER -s "$MONITOR_IP" -i "$APP_IFACE" -p tcp --dport 8090 -j ACCEPT

iptables -C DOCKER-USER -s "$ADMIN_IP" -i "$APP_IFACE" -p tcp --dport 8090 -j ACCEPT 2>/dev/null ||   iptables -A DOCKER-USER -s "$ADMIN_IP" -i "$APP_IFACE" -p tcp --dport 8090 -j ACCEPT

iptables -C DOCKER-USER -i "$APP_IFACE" -p tcp --dport 8080 -j DROP 2>/dev/null ||   iptables -A DOCKER-USER -i "$APP_IFACE" -p tcp --dport 8080 -j DROP

iptables -C DOCKER-USER -i "$APP_IFACE" -p tcp --dport 8090 -j DROP 2>/dev/null ||   iptables -A DOCKER-USER -i "$APP_IFACE" -p tcp --dport 8090 -j DROP
