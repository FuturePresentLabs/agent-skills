#!/usr/bin/env python3
"""
Package tracking lookup script for USPS, UPS, FedEx, and Ward.
Uses Playwright with headless Chromium for JS-heavy sites (USPS, Ward).
"""

import argparse
import json
import re
import sys
import subprocess
from urllib.parse import quote

# Optional Playwright import - graceful fallback if not installed
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

def install_playwright():
    """Install playwright and chromium browser."""
    print("Playwright not installed. Installing...", file=sys.stderr)
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright", "-q"])
        subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
        print("Playwright installed. Please restart the script.", file=sys.stderr)
        sys.exit(0)
    except subprocess.CalledProcessError as e:
        print(f"Failed to install Playwright: {e}", file=sys.stderr)
        sys.exit(1)

def identify_carrier(tracking_number):
    """Identify carrier from tracking number format."""
    tn = tracking_number.strip().upper()
    
    # USPS patterns
    if re.match(r'^(94|93|92|90)\d{20,22}$', tn):
        return 'usps'
    if re.match(r'^[A-Z]{2}\d{9}[A-Z]{2}$', tn):
        return 'usps'
    if re.match(r'^\d{20,22}$', tn) and len(tn) >= 20:
        return 'usps'
    
    # UPS patterns
    if tn.startswith('1Z') and len(tn) == 18:
        return 'ups'
    if re.match(r'^\d{12}$', tn):
        return 'ups'
    
    # FedEx patterns
    if re.match(r'^\d{12}$', tn):
        return 'fedex'
    if re.match(r'^\d{15}$', tn):
        return 'fedex'
    if re.match(r'^\d{20}$', tn):
        return 'fedex'
    
    # Ward patterns - typically 7-10 digit PRO numbers
    if re.match(r'^\d{7,10}$', tn):
        return 'ward'
    
    return 'unknown'

def get_tracking_url(carrier, tracking_number):
    """Get tracking URL for carrier."""
    tn = quote(tracking_number.strip())
    
    urls = {
        'usps': f'https://tools.usps.com/go/TrackConfirmAction?tLabels={tn}',
        'ups': f'https://www.ups.com/track?tracknum={tn}',
        'fedex': f'https://www.fedex.com/apps/fedextrack/?tracknumbers={tn}',
        'ward': f'https://wardtlctools.com/wardtrucking/traceshipment/create'
    }
    
    return urls.get(carrier, urls['usps'])

def lookup_with_playwright(url, extract_fn, tracking_number, carrier_name):
    """Use Playwright to fetch tracking details from JS-heavy sites."""
    if not PLAYWRIGHT_AVAILABLE:
        return {
            'error': 'Playwright not installed. Run: pip install playwright && playwright install chromium',
            'carrier': carrier_name,
            'tracking_number': tracking_number,
            'url': url,
            'status': 'Unknown'
        }
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent='Mozilla/5.0 (compatible; PackageTracker/1.0)'
            )
            page = context.new_page()
            
            try:
                # Use domcontentloaded for faster loading, then wait for JS
                page.goto(url, wait_until='domcontentloaded', timeout=30000)
                
                # Extract data using provided function
                result = extract_fn(page, tracking_number)
                
                browser.close()
                return result
                
            except PWTimeoutError:
                browser.close()
                return {
                    'error': 'Page load timeout',
                    'carrier': carrier_name,
                    'tracking_number': tracking_number,
                    'url': url,
                    'status': 'Unknown'
                }
            except Exception as e:
                browser.close()
                return {
                    'error': str(e),
                    'carrier': carrier_name,
                    'tracking_number': tracking_number,
                    'url': url,
                    'status': 'Unknown'
                }
                
    except Exception as e:
        return {
            'error': f'Playwright error: {e}',
            'carrier': carrier_name,
            'tracking_number': tracking_number,
            'url': url,
            'status': 'Unknown'
        }

def extract_usps_data(page, tracking_number):
    """Extract tracking data from USPS page."""
    result = {
        'carrier': 'USPS',
        'tracking_number': tracking_number,
        'url': page.url,
        'status': 'Unknown',
        'details': [],
        'estimated_delivery': None
    }
    
    try:
        # Wait longer for USPS to load
        page.wait_for_timeout(8000)
        
        # Try to scroll to load lazy content
        page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        page.wait_for_timeout(2000)
        
        # Look for status text - try multiple patterns
        status_patterns = [
            'delivered',
            'in transit',
            'out for delivery',
            'picked up',
            'shipped',
            'arrived',
            'departed'
        ]
        
        content = page.content().lower()
        for pattern in status_patterns:
            if pattern in content:
                result['status'] = pattern.title()
                break
        
        # Look for delivery date with regex
        import re
        date_patterns = [
            r'(?:January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2},? \d{4}',
            r'\d{1,2}/\d{1,2}/\d{4}',
            r'\d{1,2}-\d{1,2}-\d{4}'
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, page.content())
            if matches:
                result['estimated_delivery'] = matches[0]
                break
        
        # Look for tracking events/history
        try:
            # USPS often uses specific class names
            event_selectors = [
                '.tracking-event',
                '.history-event', 
                '.event-row',
                '[class*="event"]',
                '[class*="history"]',
                'tr',  # Table rows as fallback
                'li'   # List items as fallback
            ]
            
            for selector in event_selectors:
                try:
                    events = page.locator(selector).all()
                    for event in events[:5]:
                        try:
                            text = event.inner_text().strip()
                            if text and len(text) > 10 and text not in result['details']:
                                # Filter out header/footer text
                                if any(keyword in text.lower() for keyword in ['delivered', 'transit', 'shipped', 'arrived', 'departed', 'processed']):
                                    result['details'].append(text)
                        except:
                            continue
                    if result['details']:
                        break
                except:
                    continue
        except:
            pass
        
        # If still no status, check page title
        if result['status'] == 'Unknown':
            try:
                title = page.title()
                if title:
                    result['page_title'] = title
                    # Try to extract status from title
                    for pattern in status_patterns:
                        if pattern in title.lower():
                            result['status'] = pattern.title()
                            break
            except:
                pass
        
        # Get any error messages
        try:
            error_elem = page.locator('.error-message, .alert-error, [class*="error"]').first
            if error_elem.is_visible():
                result['error_message'] = error_elem.inner_text().strip()
        except:
            pass
        
    except Exception as e:
        result['error'] = str(e)
    
    return result

def extract_ward_data(page, tracking_number):
    """Extract tracking data from Ward Trucking page."""
    result = {
        'carrier': 'Ward Trucking',
        'tracking_number': tracking_number,
        'url': page.url,
        'status': 'Unknown',
        'details': [],
        'locations': []
    }
    
    try:
        # Wait for page to load
        page.wait_for_load_state('domcontentloaded')
        page.wait_for_timeout(1000)
        
        # Fill in the tracking form
        try:
            # Ward uses specific field names: TraceShipmentProNumber[0][NUMBER]
            pro_input = page.locator('input[name="TraceShipmentProNumber[0][NUMBER]"]').first
            
            if pro_input.is_visible():
                pro_input.fill(tracking_number)
                result['debug'] = f"Filled PRO number: {tracking_number}"
            else:
                result['debug'] = "Could not find PRO input field"
            
            # Look for submit button - Ward uses "Trace Shipments"
            submit_btn = page.locator('input[type="submit"][value="Trace Shipments"]').first
            
            if submit_btn.is_visible():
                submit_btn.click()
                result['debug'] = result.get('debug', '') + " | Clicked Trace Shipments button"
                
                # Wait for results to load
                page.wait_for_load_state('networkidle')
                page.wait_for_timeout(5000)  # Give extra time for JS to render
            else:
                result['debug'] = result.get('debug', '') + " | Could not find submit button"
                
        except Exception as e:
            result['debug'] = f"Form error: {str(e)}"
        
        # Look for status information after form submission
        status_selectors = [
            '.status',
            '.shipment-status',
            '.tracking-status',
            '[class*="status"]',
            'h2:has-text("Status")',
            'h3:has-text("Status")',
            '.result-status',
            '.shipment-result'
        ]
        
        for selector in status_selectors:
            try:
                element = page.locator(selector).first
                if element.is_visible():
                    result['status'] = element.inner_text().strip()
                    break
            except:
                continue
        
        # Look for shipment details table/rows
        try:
            # Try to find data rows (not header rows)
            rows = page.locator('table tbody tr, .shipment-row, .tracking-row, .result-row').all()
            for row in rows[:10]:
                try:
                    text = row.inner_text().strip()
                    # Skip header/form rows
                    if text and len(text) > 10 and 'Ward Pro' not in text and 'Type' not in text:
                        result['details'].append(text.replace('\n', ' | '))
                except:
                    continue
        except:
            pass
        
        # Look for location information
        try:
            location_elems = page.locator('.location, .facility, .terminal, [class*="location"], .origin, .destination').all()
            for loc in location_elems[:5]:
                try:
                    text = loc.inner_text().strip()
                    if text and len(text) < 100:
                        result['locations'].append(text)
                except:
                    continue
        except:
            pass
        
        # If still no data, try to get any table data
        if not result['details']:
            try:
                all_tables = page.locator('table').all()
                for table in all_tables:
                    try:
                        text = table.inner_text().strip()
                        if text and len(text) > 50:
                            result['raw_table'] = text[:500]  # First 500 chars
                            break
                    except:
                        continue
            except:
                pass
        
    except Exception as e:
        result['error'] = str(e)
    
    return result

def lookup_usps_tracking(tracking_number):
    """Look up USPS tracking using Playwright."""
    url = get_tracking_url('usps', tracking_number)
    return lookup_with_playwright(url, extract_usps_data, tracking_number, 'USPS')

def lookup_ward_tracking(tracking_number):
    """Look up Ward Trucking tracking using Playwright."""
    url = get_tracking_url('ward', tracking_number)
    return lookup_with_playwright(url, extract_ward_data, tracking_number, 'Ward Trucking')

def format_tracking_info(carrier, tracking_number, details=None):
    """Format tracking information for display."""
    carrier_name = {
        'usps': 'USPS',
        'ups': 'UPS',
        'fedex': 'FedEx',
        'ward': 'Ward Trucking'
    }.get(carrier, carrier.upper())
    
    url = get_tracking_url(carrier, tracking_number)
    
    # If we have detailed tracking info
    if details:
        lines = [
            f"Carrier: {carrier_name}",
            f"Tracking Number: {tracking_number}",
            f"Status: {details.get('status', 'Unknown')}",
            f"Tracking URL: {url}"
        ]
        
        if details.get('estimated_delivery'):
            lines.append(f"Estimated Delivery: {details['estimated_delivery']}")
        
        if details.get('details'):
            lines.append("\nTracking History:")
            for detail in details['details'][:5]:
                lines.append(f"  - {detail}")
        
        if details.get('locations'):
            lines.append(f"\nLocations: {', '.join(details['locations'])}")
        
        if details.get('error') and not details.get('status'):
            lines.append(f"\nError: {details['error']}")
            lines.append("\nNote: Install Playwright for full tracking: pip install playwright && playwright install chromium")
        
        if details.get('error_message'):
            lines.append(f"\nMessage: {details['error_message']}")
        
        return '\n'.join(lines)
    
    # Standard format for other carriers (or fallback)
    info = f"""Carrier: {carrier_name}
Tracking Number: {tracking_number}
Tracking URL: {url}"""
    
    # Add carrier-specific notes
    if carrier in ('usps', 'ward'):
        info += f"\n\nNote: Install Playwright for full tracking details:"
        info += f"\n  pip install playwright"
        info += f"\n  playwright install chromium"
    elif carrier == 'usps':
        info += "\n\nNote: USPS tracking may take 1-3 business days to populate after shipment."
    
    return info

def extract_tracking_numbers(text):
    """Extract potential tracking numbers from text."""
    patterns = [
        (r'\b(94|93|92|90)\d{20,22}\b', 'usps'),
        (r'\b1Z[A-Z0-9]{16}\b', 'ups'),
        (r'\b\d{12}\b', 'unknown'),
        (r'\b\d{15}\b', 'fedex'),
        (r'\b\d{20}\b', 'fedex'),
        (r'\b\d{7,10}\b', 'ward'),
    ]
    
    found = []
    for pattern, carrier in patterns:
        matches = re.findall(pattern, text.upper())
        for match in matches:
            if isinstance(match, tuple):
                match = match[0] if match[0] else ''.join(match)
            if match not in [t[0] for t in found]:
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
    parser.add_argument('--install', action='store_true',
                        help='Install Playwright and Chromium browser')
    
    args = parser.parse_args()
    
    if args.install:
        install_playwright()
        return
    
    if args.extract:
        text = args.number if args.number else sys.stdin.read()
        tracking_numbers = extract_tracking_numbers(text)
        
        if not tracking_numbers:
            print("No tracking numbers found.", file=sys.stderr)
            sys.exit(1)
        
        for tn, carrier in tracking_numbers:
            details = None
            if carrier == 'usps':
                details = lookup_usps_tracking(tn)
            elif carrier == 'ward':
                details = lookup_ward_tracking(tn)
            
            info = format_tracking_info(carrier, tn, details)
            print(info)
            print()
    
    elif args.number:
        carrier = args.carrier or identify_carrier(args.number)
        
        details = None
        if carrier == 'usps':
            details = lookup_usps_tracking(args.number)
        elif carrier == 'ward':
            details = lookup_ward_tracking(args.number)
        
        if carrier == 'unknown':
            print(f"Could not identify carrier for {args.number}", file=sys.stderr)
            print("Checking USPS, UPS, and FedEx...", file=sys.stderr)
            print()
            for c in ['usps', 'ups', 'fedex']:
                print(format_tracking_info(c, args.number))
                print()
        else:
            print(format_tracking_info(carrier, args.number, details))
    
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == '__main__':
    main()
