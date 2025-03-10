#!/usr/bin/env python3.10

from pomo_stat import stat


pomos = stat()
content = (
    "[POMO] "
    + {
        "ACTIVE": "Active-%(combo)s: %(desc)s",
        "INTERRUPT": "Interrupt-%(combo)s: %(desc)s",
        "COMPLETE": "Complete. Achieved: %(achieved)d, Combo: %(combo)d",
        "INACTIVE": "Inactive. Achieved: %(achieved)d, MaxCombo: %(max_combo)d",
    }.get(pomos["status"], "%(status)s, Combo: %(combo)d")
    % pomos
)
print(content)
