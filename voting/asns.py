"""Starter list of datacenter/hosting/VPN ASNs (docs/voting.md classification).

Ballots from these networks are HELD for review, never silently rejected.
Extend during the vote window if abuse clusters appear (keep the list in git).
"""

DATACENTER_ASNS = frozenset(
    {
        16509,  # Amazon AWS
        14618,  # Amazon AES
        15169,  # Google
        396982,  # Google Cloud
        8075,  # Microsoft Azure
        14061,  # DigitalOcean
        16276,  # OVH
        24940,  # Hetzner
        63949,  # Akamai/Linode
        20473,  # Vultr/Choopa
        45102,  # Alibaba Cloud
        132203,  # Tencent Cloud
        9009,  # M247 (common VPN host)
        212238,  # Datacamp (common VPN host)
    }
)
