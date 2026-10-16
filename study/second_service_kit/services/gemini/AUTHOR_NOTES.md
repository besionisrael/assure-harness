# Author Notes

## Design Choices
- **Domain**: Tool Lending Library service managing members, item catalog, loans, reservations, and fines.
- **State management**: Kept entirely in-memory using dictionaries indexed by IDs and usernames, injected with a `clock` object for time-dependent calculations.
- **Fines & Penalties**: Overdue returns accrue fines per day (calculated via ceiling of overdue seconds divided by 86400.0). Damage and loss incur flat penalties and inventory adjustments.

## Behaviors Deliberately Left Open
- The exact tie-breaking order when multiple members reserve the same out-of-stock item is not specified (reservations are stored in a dictionary and checked generically).

## Seeded Fault Rationales
- **F01**: A developer might validate only that a username is present and forget to validate the membership tier string against allowed values.
- **F02**: A developer might check that parameters are integers but forget to enforce that quantities and durations must be strictly positive (> 0).
- **F03**: A developer might use a strict greater-than operator (`> 10.0`) instead of greater-than-or-equal (`>= 10.0`) when checking unpaid fines.
- **F04**: A developer might hardcode the maximum concurrent loan limit to 10 for all tiers during a quick prototype and forget to implement tier-based limits.
- **F05**: A developer might use `math.floor` instead of `math.ceil` when calculating overdue days, undercharging members for partial overdue days.
- **F06**: A developer might mistakenly add the payment amount to the member's fine balance instead of subtracting it during fine payments.
- **F07**: A developer might mistakenly increment available quantity instead of reducing `total_qty` when an item is reported lost.
- **F08**: A developer might omit checking for active reservations when renewing a loan under time pressure.
- **F09**: A developer might forget to check the `renewed` flag, allowing members to renew loans infinitely.
- **F10**: A developer might invert the availability check during item reservation, allowing reservations when items are still in stock.
- **F11**: A developer might omit checking whether the payment amount is strictly positive, allowing zero or negative fine payments.
- **F12**: A developer might forget to check if `available <= 0` when borrowing an item, leading to negative available quantities.

## Model Identification
- Model: Gemini (Google)

