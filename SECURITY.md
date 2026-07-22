# Security Policy

## Reporting a Vulnerability

This repository is a showcase that runs entirely on local infrastructure
(Atlas, local Ollama, and other local services). It is not a deployed service
and holds no production data, but security reports are still welcome.

Please report suspected vulnerabilities privately by opening a private security
advisory on the repository (the preferred channel). Do not open a public issue
for a security-sensitive report.

Include a description of the issue, a reproduction or proof of concept, and the
commit you tested against. You will receive an acknowledgement within a few
days. Coordinated disclosure is appreciated.

## Scope

The showcase plugin, its scripts, the consumer manifest, and the documentation
are in scope. The vendored `infra/` Atlas submodule is a separate project —
report issues found there to the Atlas project directly.
