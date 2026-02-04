# Package Tracking Reference

## Carrier-Specific Details

### USPS (United States Postal Service)

**Tracking Formats:**
- 20-22 digit numbers (most common)
- Often starts with 94, 93, 92, or 90
- International: Two letters + 9 digits + "US" (e.g., EA123456789US)

**Services:**
- First Class Mail (1-5 days)
- Priority Mail (1-3 days)
- Priority Mail Express (1-2 days, overnight in many cases)
- Ground Advantage (2-5 days) - formerly Parcel Select

**Tracking Notes:**
- Labels may take 1-3 business days to show movement after creation
- "Pre-shipment" status means label created, not yet scanned
- Delays common during holidays (Nov-Dec)
- Saturday delivery included for most services

**API:**
- Requires USPS Web Tools API registration
- Free for most use cases
- Rate limited

---

### UPS (United Parcel Service)

**Tracking Formats:**
- 1Z + 6 chars (shipper) + 2 chars (service) + 8 digits (package) + check digit
- 12 digit numeric (alternate format for some services)

**Services:**
- Ground (1-5 business days)
- 3 Day Select
- 2nd Day Air
- Next Day Air

**Tracking Notes:**
- Updates in real-time as package moves
- "Exception" status means delay (weather, address issue, etc.)
- UPS My Choice for delivery management

**API:**
- UPS Developer Kit requires registration
- OAuth 2.0 authentication
- Tracking API available

---

### FedEx

**Tracking Formats:**
- 12 digits (most common)
- 15 digits (FedEx Ground)
- 20 digits (some international)
- 9 digits (Door Tag)

**Services:**
- Ground (1-5 business days)
- Express Saver (3 business days)
- 2Day
- Standard Overnight
- Priority Overnight
- First Overnight

**Tracking Notes:**
- Real-time updates
- "Operational delay" common during peak times
- FedEx Delivery Manager for holds and redirects

**API:**
- FedEx Web Services requires developer account
- REST API available
- Tracking API included

---

### Ward Trucking

**Overview:**
Regional LTL (Less Than Truckload) carrier serving the Mid-Atlantic and Northeast United States.

**Coverage Area:**
- PA, NJ, NY, MD, DE, VA, WV, OH

**Services:**
- LTL Freight
- Guaranteed services
- Expedited shipping

**Tracking:**
- Web portal: https://www.wardtrucking.com/tracking
- Requires PRO number (progressive number)
- Format varies (typically 8-10 digits)
- May require customer login for detailed tracking

**Contact:**
- Customer Service: 1-800-927-9333
- Main: (717) 492-2200

---

## Third-Party Tracking Services

When carrier APIs are unavailable, these services can sometimes provide tracking data:

### ParcelApp
- https://parcelsapp.com
- Supports most major carriers
- Free tier available

### 17TRACK
- https://www.17track.net
- 800+ carriers worldwide
- Free for personal use

### AfterShip
- https://www.aftership.com
- API available
- Paid service for high volume

### PackageRadar
- https://packageradar.com
- Simple tracking interface

---

## Common Status Codes

| Status | Meaning |
|--------|---------|
| Label Created | Shipping label generated, not yet in transit |
| Picked Up | Carrier has package |
| In Transit | Moving through network |
| Out for Delivery | On truck for final delivery |
| Delivered | Package delivered |
| Exception | Problem/delay (weather, address, customs, etc.) |
| Attempted Delivery | Delivery attempted, failed |
| Held at Location | Package at facility for pickup |

---

## Delivery Time Guidelines

### Ground Shipping (Cross-Country)
- USPS: 5-7 business days
- UPS Ground: 4-5 business days
- FedEx Ground: 4-6 business days

### Regional (Same Coast)
- USPS: 2-3 business days
- UPS Ground: 1-3 business days
- FedEx Ground: 1-3 business days

### Express Options
- Overnight: All carriers
- 2-Day: All carriers
- 3-Day: UPS & FedEx

---

## Troubleshooting

### Tracking Not Found
1. Check number was entered correctly
2. Wait 24 hours (USPS especially)
3. Contact shipper to verify number
4. Check with carrier customer service

### Package Stuck
- "In Transit" for 3+ days: Normal for ground
- No update for 5+ days: Contact carrier
- "Exception" status: Check details for reason

### Delivery Issues
- Wrong address: Contact carrier immediately
- Not delivered but marked delivered: Check around property, ask neighbors
- Damaged: File claim with carrier
