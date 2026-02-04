---
name: package-tracking
description: Look up package tracking information for FedEx, UPS, USPS, and Ward trucking/logistics carriers. Use when users need to check shipping status, delivery estimates, or track packages by tracking number. Supports extracting tracking numbers from emails, checking delivery status across multiple carriers, and providing direct tracking links.
---

# Package Tracking

Look up package tracking information across major carriers.

## Supported Carriers

- **USPS** - United States Postal Service
- **UPS** - United Parcel Service  
- **FedEx** - Federal Express
- **Ward** - Ward Trucking/Logistics

## Usage Patterns

### Direct Tracking Number Lookup

When given a tracking number, identify the carrier and look up status:

```
Track package 1Z999AA10123456784
```

### Extract from Email

When given an email or message containing tracking info, extract the tracking number and look it up:

```
Find the tracking number in this email and check status
```

### Check Multiple Carriers

For ambiguous tracking numbers, check multiple carriers:

```
Track 9400111899223456789012
```

## Tracking Number Patterns

| Carrier | Format Example | Pattern |
|---------|----------------|---------|
| USPS | 9400111899223456789012 | 20-22 digits, often starts with 94 |
| USPS | 9434650206217168190787 | 22 digits (Ground Advantage) |
| UPS | 1Z999AA10123456784 | 1Z + 16 alphanumeric |
| UPS | 123456789012 | 12 digits (alternate) |
| FedEx | 123456789012 | 12 digits |
| FedEx | 1234567890123456 | 15 digits |
| Ward | Various | Contact Ward directly |

## Quick Reference

**Direct tracking URLs:**
- USPS: https://tools.usps.com/go/TrackConfirmAction?tLabels=<NUMBER>
- UPS: https://www.ups.com/track?tracknum=<NUMBER>
- FedEx: https://www.fedex.com/apps/fedextrack/?tracknumbers=<NUMBER>
- Ward: https://www.wardtrucking.com/tracking (requires login)

## Using the Lookup Script

For programmatic tracking lookups:

```bash
./scripts/track_package.py --carrier usps --number 9400111899223456789012
./scripts/track_package.py --carrier ups --number 1Z999AA10123456784
./scripts/track_package.py --carrier fedex --number 123456789012
```

## Delivery Time Estimates

Typical ground shipping times (business days):

| From/To | USPS Ground | UPS Ground | FedEx Ground |
|---------|-------------|------------|--------------|
| Same region | 2-3 days | 1-2 days | 1-2 days |
| Cross-country | 5-7 days | 4-5 days | 4-6 days |

**Note:** USPS tracking may take 1-3 business days to populate in their system after label creation.

## When Tracking Data Isn't Available

1. **Label created, no movement** - Package dropped off but not yet scanned
2. **No data yet** - USPS often takes 1-3 days to show tracking updates
3. **Delivered** - Check mailbox/porch, may not show "delivered" status
4. **Invalid number** - Double-check the tracking number with sender

For Ward trucking, contact their customer service directly at 1-800-沃德 or use their portal.
