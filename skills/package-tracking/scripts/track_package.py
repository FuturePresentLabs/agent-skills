#!/usr/bin/env python3
"""
Package tracking lookup script for USPS, UPS, FedEx, and Ward.
"""

import argparse
import re
import sys
from urllib.parse import quote

def identify_carrier(tracking_number):
    """Identify carrier from tracking number format."""
    tn = tracking_number.strip().upper()
    
    # USPS patterns
    if re.match(r'^(94|93|92|90)\d{20,22}$', tn):  # USPS standard
        return 'usps'
    if re.match(r'^[A-Z]{2}\d{9}[A-Z]{2}$', tn):  # USPS international
        return 'usps'
    if re.match(r'^\d{20,22}$', tn) and len(tn) >= 20:  # Generic long number, likely USPS
        return 'usps'
    
    # UPS patterns
    if tn.startswith('1Z') and len(tn) == 18:
        return 'ups'
    if re.match(r'^\d{12}$', tn):  # UPS alternate format
        return 'ups'
    
    # FedEx patterns
    if re.match(r'^\d{12}$', tn):
        return 'fedex'
    if re.match(r'^\d{15}$', tn):
        return 'fedex'
    if re.match(r'^\d{20}$', tn):
        return 'fedex'
    
    return 'unknown'

def get_tracking_url(carrier, tracking_number):
    """Get tracking URL for carrier."""
    tn = quote(tracking_number.strip())
    
    urls = {
        'usps': f'https://tools.usps.com/go/TrackConfirmAction?tLabels={tn}',
        'ups': f'https://www.ups.com/track?tracknum={tn}',
        'fedex': f'https://www.fedex.com/apps/fedextrack/?tracknumbers={tn}',
        'ward': 'https://www.wardtrucking.com/tracking'
    }
    
    return urls.get(carrier, urls['usps'])

def format_tracking_info(carrier, tracking_number):
    """Format tracking information for display."""
    carrier_name = {
        'usps': 'USPS',
        'ups': 'UPS',
        'fedex': 'FedEx',
        'ward': 'Ward Trucking'
    }.get(carrier, carrier.upper())
    
    url = get_tracking_url(carrier, tracking_number)
    
    info = f"""Carrier: {carrier_name}
Tracking Number: {tracking_number}
Tracking URL: {url}
"""
    
    # Add carrier-specific notes
    if carrier == 'usps':
        info += "\nNote: USPS tracking may take 1-3 business days to populate after shipment."
    elif carrier == 'ward':
        info += "\nNote: Ward Trucking requires login. Contact customer service or use their portal."
    
    return info

def extract_tracking_numbers(text):
    """Extract potential tracking numbers from text."""
    patterns = [
        (r'\b(94|93|92|90)\d{20,22}\b', 'usps'),  # USPS
        (r'\b1Z[A-Z0-9]{16}\b', 'ups'),  # UPS
        (r'\b\d{12}\b', 'unknown'),  # Could be UPS or FedEx
        (r'\b\d{15}\b', 'fedex'),  # FedEx
        (r'\b\d{20}\b', 'fedex'),  # FedEx
    ]
    
    found = []
    for pattern, carrier in patterns:
        matches = re.findall(pattern, text.upper())
        for match in matches:
            if isinstance(match, tuple):
                match = match[0] if match[0] else ''.join(match)
            if match not in [t[0] for t in found]:
                # For ambiguous patterns, try to identify
                if carrier == 'unknown':
                    carrier = identify_carrier(match)
                found.append((match, carrier))
    
    return found

def main():
    parser = argparse.ArgumentParser(description='Look up package tracking information')
    parser.add_argument('--carrier', '-c', choices=['usps', 'ups', 'fedex', 'ward'],
                        help='Carrier name (auto-detected if not specified)')
    parser.add_argument('--number', '-n', help='Tracking number')
    parser.add_argument('--extract', '-e', action='store_true',
                        help='Extract tracking numbers from input text')
    parser.add_argument('--json', '-j', action='store_true',
                        help='Output as JSON')
    
    args = parser.parse_args()
    
    if args.extract:
        # Read from stdin or use provided text
        text = args.number if args.number else sys.stdin.read()
        tracking_numbers = extract_tracking_numbers(text)
        
        if not tracking_numbers:
            print("No tracking numbers found.", file=sys.stderr)
            sys.exit(1)
        
        for tn, carrier in tracking_numbers:
            print(format_tracking_info(carrier, tn))
            print()
    
    elif args.number:
        carrier = args.carrier or identify_carrier(args.number)
        if carrier == 'unknown':
            print(f"Could not identify carrier for {args.number}", file=sys.stderr)
            print("Checking USPS, UPS, and FedEx...", file=sys.stderr)
            print()
            for c in ['usps', 'ups', 'fedex']:
                print(format_tracking_info(c, args.number))
                print()
        else:
            print(format_tracking_info(carrier, args.number))
    
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == '__main__':
    main()
