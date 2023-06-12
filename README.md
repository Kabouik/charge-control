`charge-control` allows controlling battery charge to avoid overstressing the battery with full charges or full discharges. The script requires root permissions.

## How to use
Just download the script and make it executable with `chmod +x /path/to/charge-control`, then run it with `sudo`:

```
Usage: sudo ./charge-control [-d DEACTIVATION] [-r REACTIVATION] [-f FREQUENCY] [-p POWEROFF]

Options:
  -d DEACTIVATION: battery percentage at which charge is disabled (default: 90)
  -r REACTIVATION: battery percentage at which charge is enabled (default: 75)
  -f FREQUENCY: monitoring frequency of battery level (default: 10s)
  -p POWEROFF: battery percentage at which the device is powered off (default: 5)
  -h: show this help

All arguments are optional. Values can be provided as positional arguments in that order
if not prefixed with flags, or can be provided in any order if prefixed with flags.
```

## Example output
```
● Charge control enabled
  Charge deactivation level: 90%
  Charge reactivation level: 75%
  Monitoring frequency: 10
  Auto power off level: 10%
  ▪ Charge enabled until battery reaches 90% (20:29)
  ▪ Charge disabled until battery drops to 75% (21:02)  
  ⣷ Monitoring battery level...
```

