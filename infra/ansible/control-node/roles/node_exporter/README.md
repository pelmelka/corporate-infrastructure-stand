# Role: node_exporter

Installs and verifies Prometheus node_exporter on managed nodes.

Responsibilities:
- ensure prometheus-node-exporter package is installed;
- ensure prometheus-node-exporter.service is enabled and running;
- verify local /metrics endpoint.

This role does not configure Prometheus scrape targets and does not manage firewall rules.
