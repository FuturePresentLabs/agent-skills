---
name: package-tracking
description: Look up package tracking information for FedEx, UPS, USPS, and Ward trucking/logistics carriers. Use when users need to check shipping status, delivery estimates, or track packages by tracking number. Supports extracting tracking numbers from emails, checking delivery status across multiple carriers, and providing direct tracking links. For USPS and Ward, uses Playwright with headless Chromium to render JavaScript-heavy tracking pages.
---

# Package Tracking

Look up package tracking information across major carriers.

## Supported Carriers

- **USPS** - United States Postal Service (via Playwright/headless browser)
- **UPS** - United Parcel Service (API-based)
- **FedEx** - Federal Express (API-based)
- **Ward** - Ward Trucking/Logistics (via Playwright/headless browser)

## Installation

### Basic (URLs only)
No additional dependencies required.

### Full Tracking with Playwright (Recommended)
For USPS and Ward tracking details, install Playwright:

```bash
pip install playwright
playwright install chromium
```

Or use the built-in installer:
```bash
./scripts/track_package.py --install
```

## Usage Patterns

### Direct Tracking Number Lookup

When given a tracking number, identify the carrier and look up status:

```bash
./scripts/track_package.py --number 1Z999AA10123456784
```

### Extract from Email

Extract tracking numbers from email text:

```bash
./scripts/track_package.py --extract --number "Your order shipped! Track: 1Z999..."
```

### Force Specific Carrier

```bash
./scripts/track_package.py --carrier usps --number 9400111899223456789012
./scripts/track_package.py --carrier ward --number 0210355075
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
| Ward | 0210355075 | 7-10 digit PRO number |

## Quick Reference

**Direct tracking URLs:**
- USPS: https://tools.usps.com/go/TrackConfirmAction?tLabels=<NUMBER>
- UPS: https://www.ups.com/track?tracknum=<NUMBER>
- FedEx: https://www.fedex.com/apps/fedextrack/?tracknumbers=<NUMBER>
- Ward: https://wardtlctools.com/wardtrucking/traceshipment/create

## Delivery Time Estimates

Typical ground shipping times (business days):

| From/To | USPS Ground | UPS Ground | FedEx Ground |
|---------|-------------|------------|--------------|
| Same region | 2-3 days | 1-2 days | 1-2 days |
| Cross-country | 5-7 days | 4-5 days | 4-6 days |

**Note:** USPS tracking may take 1-3 business days to populate in their system after label creation.

## How It Works

### USPS & Ward (JavaScript-Heavy Sites)
Uses Playwright with headless Chromium to:
1. Load the tracking page
2. Wait for JavaScript to render tracking data
3. Extract status, delivery estimates, and tracking history

### UPS & FedEx (API-Based)
Provides direct tracking URLs. Full API integration can be added with carrier API keys.

## Troubleshooting

**"Playwright not installed" error:**
```bash
pip install playwright
playwright install chromium
```

**Slow performance:** First run downloads Chromium (~110MB). Subsequent runs are fast.

**No tracking data found:**
1. Check that the tracking number is correct
2. Wait 24 hours for USPS labels to activate
3. For Ward, verify the PRO number with the shipper
