"""No-resurrection blocklist for manifest/tools.yaml (KA-05.1).

The deliberate exclusions of plan §3.7 are policy, not history: the
manifest validator refuses tooling from these classes even if a later
lane lands a row for it. AGENTS.md calls this the "no-resurrection
guard". This module is the data-driven blocklist constant the validator
consumes; extend it when the owning census lane amends the canon —
never add a name without a plan ref.

Excluded classes (plan §3.7 "Deliberate exclusions"):

- hardware / RF / radio tooling: wifi attack suites, Bluetooth stacks,
  general hardware-hacking, USB/pcap device and RF-transmission tools.
  The sole radio-adjacent concession is the opt-in C-7 SDR data-pack
  (categories.yaml `c-07-signal-sdr`, §4.1) — its tools (gnuradio,
  gqrx, hackrf and the DSP/audio libraries) stay OUTSIDE this list but
  also OUT of tools.yaml under a non-`data` packaging status.
- paid / commercial licences: per plan §3.7; `kailash doctor <tool>`
  is the licensing surface (unbuilt at this rev).
- unmaintained, cloud-only and duplicate-scope classes are doctrinal
  and NOT enumerated yet: their per-name grounds arrive with the
  KA-04.4 exclusions ledger (kailash-os#73). Extend the appropriate
  tuple only from that ledger, with its entry cited in the comment.
"""

# §3.7 wifi attack suites — hardware/RF & radio class.
BLOCK_WIFI = (
    "aircrack-ng",
    "airgeddon",
    "wifite",
    "kismet",
    "reaver",
    "bully",
    "pixiewps",
    "hcxdumptool",
    "hcxtools",
    "wifiphisher",
    "fern",
    "asleap",
    "cowpatty",
    "crackle",
    "wifi-honey",
    "wash",
)

# §3.7 Bluetooth stacks — hardware/RF & radio class.
BLOCK_BLUETOOTH = (
    "ubertooth",
    "bluelog",
    "bluesnarfer",
    "btscanner",
    "blueranger",
    "spooftooph",
    "rfcat",
    "fang",
    "chirp",
)

# §3.7 paid/commercial licences (the doctor class). "paid IDA" is the
# proprietary binary; the Free edition of IDA remains out of scope for
# a different reason (platform surface, C-6) — both spellings blocked.
BLOCK_PAID = (
    "nessus",
    "cobalt strike",
    "cobaltstrike",
    "ida-pro",
    "ida-pro-free",
)

# Blocked tool ids (slug spellings) of the same hardware/RF class —
# Kali's 14-Hardware Hacking category is excluded whole (§3.7).
BLOCK_HW_IDS = (
    "hardware-hacking",
    "usb-tooling",
    "pcap-device-tooling",
    "rf-transmission",
)

# Hardware/RF & radio class, as one set — the id/name spellings above
# are all this one §3.7 class; the split tuples only keep the plan's
# bullet shape.
EXCLUDED_HARDWARE_RF = BLOCK_WIFI + BLOCK_BLUETOOTH + BLOCK_PAID + BLOCK_HW_IDS

NO_RESURRECTION = set(EXCLUDED_HARDWARE_RF)
