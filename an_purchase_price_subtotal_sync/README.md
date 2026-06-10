# Purchase Price Subtotal Sync

## Overview
This module adds bidirectional synchronization between price_unit and price_subtotal in Purchase Orders for Odoo 18.

## Key Features
- Automatically updates price_subtotal when price_unit or product_qty changes
- Automatically recalculates price_unit when price_subtotal is manually updated
- Error handling for scenarios with zero quantity
- Seamless integration with Odoo's native Purchase module

## Installation
1. Download the module
2. Add the module to your Odoo addons path
3. Update the app list in Odoo
4. Install the module

## Usage
After installation, the functionality is automatically available in all purchase order forms. No additional configuration is required.

1. **Update Price Unit**: Enter a new price unit, and the subtotal will automatically update based on the quantity.
2. **Update Quantity**: Change the product quantity, and the subtotal will automatically update while keeping the unit price constant.
3. **Update Subtotal**: Manually change the subtotal, and the unit price will automatically recalculate based on the quantity.

## Technical Details
This module extends the `purchase.order.line` model to enable bidirectional synchronization:
- Overrides the `price_subtotal` field to make it writable
- Implements the `_inverse_price_subtotal` method to update unit price when subtotal changes
- Uses `@api.onchange` decorators to ensure real-time updates in the UI
- Implements proper error handling for edge cases

## Compatibility
- Odoo 18.0 Community and Enterprise Editions

## Author
Ahmed Nour (ahmednour@outlook.com)

## Website
http://www.odoosa.net

## License
AGPL-3

## Support
For any questions or support, please contact:
- Email: ahmednour@outlook.com
- Website: www.odoosa.net
