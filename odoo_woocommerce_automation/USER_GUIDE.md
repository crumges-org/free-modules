# WooCommerce Automation Module - User Guide

**Version:** 18.0.1.0.0  
**Developed by:** ECOSIRE (PRIVATE) LIMITED  
**Website:** https://www.ecosire.com/  
**Support:** info@ecosire.com

---

## Table of Contents

1. [Overview](#overview)
2. [Installation & Setup](#installation--setup)
3. [Getting Started](#getting-started)
4. [Configuration](#configuration)
5. [Dashboard](#dashboard)
6. [Synchronization](#synchronization)
7. [Tools & Wizards](#tools--wizards)
8. [Reports & Monitoring](#reports--monitoring)
9. [Troubleshooting](#troubleshooting)
10. [Best Practices](#best-practices)

---

## Overview

The WooCommerce Automation module provides comprehensive integration between Odoo 18 and WooCommerce stores. It enables bidirectional synchronization of products, orders, customers, and inventory, with automated workflows and real-time monitoring.

### Key Features

- **Bidirectional Product Synchronization** - Sync products between Odoo and WooCommerce
- **Order Management** - Import orders from WooCommerce and update statuses
- **Customer Synchronization** - Keep customer data synchronized between systems
- **Inventory Management** - Real-time inventory synchronization
- **Automated Workflows** - Scheduled synchronization with configurable frequency
- **Advanced Mapping** - Custom mapping between Odoo and WooCommerce entities
- **Comprehensive Reporting** - Detailed sync logs and analytics
- **Multi-store Support** - Manage multiple WooCommerce stores

---

## Installation & Setup

### Prerequisites

1. **Odoo 18** - Ensure you have Odoo 18 installed
2. **WooCommerce Store** - Active WooCommerce store with REST API enabled
3. **API Credentials** - WooCommerce Consumer Key and Secret
4. **Required Dependencies**:
   - Python `requests>=2.25.1`
   - Python `woocommerce>=3.0.0`

### Installation Steps

1. **Install the Module**
   - Go to Apps → Search for "WooCommerce Automation"
   - Click Install
   - Wait for installation to complete

2. **Access the Module**
   - Navigate to WooCommerce menu in the main menu
   - The module will be available under the WooCommerce section

---

## Getting Started

### First-Time Setup

1. **Access Dashboard**
   - Go to WooCommerce → Dashboard
   - You'll see the main dashboard with connection status

2. **Create Configuration**
   - Click on Configuration → Configurations
   - Click "Create" to add your first WooCommerce configuration

3. **Configure Connection**
   - Enter your WooCommerce store details
   - Test the connection
   - Save the configuration

---

## Configuration

### Creating a WooCommerce Configuration

#### Step 1: Basic Information

1. **Configuration Name**
   - Enter a descriptive name (e.g., "Main Store", "Test Store")
   - This helps identify different configurations

#### Step 2: Connection Settings

1. **WooCommerce Store URL**
   - Enter your store's main URL (e.g., `https://myshop.com`)
   - Must include `https://` protocol
   - Should be accessible from your Odoo server

2. **Consumer Key**
   - Found in WooCommerce → Settings → Advanced → REST API → Add Key
   - Copy the Consumer Key from the generated API key

3. **Consumer Secret**
   - Found in the same location as Consumer Key
   - Copy the Consumer Secret from the generated API key

4. **API Version**
   - Usually "wc/v3" for WooCommerce 3.0+
   - Leave as default if unsure

5. **Connection Timeout**
   - Maximum time to wait for API responses
   - Default: 30 seconds

#### Step 3: Synchronization Settings

1. **Sync Options**
   - **Sync Products**: Enable to synchronize product information
   - **Sync Orders**: Enable to import orders from WooCommerce
   - **Sync Customers**: Enable to synchronize customer data
   - **Sync Inventory**: Enable to keep stock levels synchronized

2. **Auto Sync Settings**
   - **Auto Sync Products**: Enable automatic product synchronization
   - **Auto Sync Orders**: Enable automatic order import
   - **Auto Sync Customers**: Enable automatic customer sync
   - **Sync Frequency**: Set how often to run automatic sync (e.g., "1 hour", "30 minutes")

#### Step 4: Test Connection

1. Click the "Test Connection" button in the header
2. Verify the connection is successful
3. Check for any error messages if connection fails

### Managing Multiple Configurations

You can create multiple configurations for:
- Different WooCommerce stores
- Test and production environments
- Different sync strategies

---

## Dashboard

### Overview

The dashboard provides a comprehensive view of your WooCommerce integration status and performance.

### Key Sections

#### 1. Connection Status
- **Connected**: Green indicator when connection is active
- **Error**: Red indicator when connection issues exist
- **Disconnected**: Yellow indicator when no connection is established

#### 2. Sync Statistics
- **Products Synced**: Total number of products synchronized
- **Orders Synced**: Total number of orders imported
- **Customers Synced**: Total number of customers synchronized
- **Sync Errors**: Number of errors in the last 24 hours

#### 3. Quick Actions
- **Import Products**: Open import wizard
- **Export Products**: Open export wizard
- **Mapping Wizard**: Configure data mappings
- **Settings**: Access configuration settings

#### 4. Recent Activity
- Timeline of recent synchronization activities
- Success/failure indicators
- Timestamps for each activity

---

## Synchronization

### Manual Synchronization

#### Product Synchronization

1. **From Dashboard**
   - Click "Import Products" quick action
   - Or go to WooCommerce → Tools → Import Wizard

2. **Configure Import**
   - Select configuration
   - Choose import options
   - Set limits if needed
   - Click "Start Import"

#### Order Synchronization

1. **Import Orders**
   - Go to WooCommerce → Tools → Import Wizard
   - Select "Import Orders" option
   - Configure import settings

2. **Update Order Status**
   - Orders are automatically updated with status changes
   - Manual status updates are also supported

#### Customer Synchronization

1. **Sync Customers**
   - Use the import wizard for customer data
   - Configure customer mapping options
   - Handle duplicate customers appropriately

### Automated Synchronization

#### Setting Up Auto Sync

1. **Enable Auto Sync**
   - In configuration, enable desired auto sync options
   - Set appropriate sync frequency

2. **Monitor Automation**
   - Check dashboard for automation status
   - Review sync logs for any issues

#### Sync Frequency Options

- **Every 5 minutes**: For high-frequency updates
- **Every 15 minutes**: Balanced approach
- **Every 30 minutes**: Standard frequency
- **Every hour**: Lower frequency for stable systems
- **Daily**: For less critical updates

---

## Tools & Wizards

### Import Wizard

#### Purpose
Import data from WooCommerce to Odoo

#### Features
- **Product Import**: Import products with images and variants
- **Order Import**: Import orders with line items
- **Customer Import**: Import customer information
- **Inventory Import**: Import stock levels

#### Usage
1. Go to WooCommerce → Tools → Import Wizard
2. Select configuration
3. Choose import type
4. Configure options
5. Start import

### Export Wizard

#### Purpose
Export data from Odoo to WooCommerce

#### Features
- **Product Export**: Export products to WooCommerce
- **Order Export**: Export orders (if applicable)
- **Customer Export**: Export customer data
- **Inventory Export**: Update stock levels

#### Usage
1. Go to WooCommerce → Tools → Export Wizard
2. Select configuration
3. Choose export type
4. Configure options
5. Start export

### Mapping Wizard

#### Purpose
Configure data mappings between Odoo and WooCommerce

#### Mapping Types
- **Product Categories**: Map Odoo categories to WooCommerce categories
- **Order Statuses**: Map Odoo order states to WooCommerce statuses
- **Payment Methods**: Map payment methods between systems
- **Shipping Methods**: Map shipping methods
- **Customer Groups**: Map customer groups/segments
- **Product Attributes**: Map product attributes and variants

#### Usage
1. Go to WooCommerce → Tools → Mapping Wizard
2. Select configuration
3. Choose mapping type
4. Configure mappings
5. Save mappings

### Test Connection Wizard

#### Purpose
Test and verify WooCommerce connection settings

#### Features
- **Connection Testing**: Verify API credentials
- **Store Information**: Display store details
- **Configuration Saving**: Save working configurations

#### Usage
1. Go to WooCommerce → Tools → Test Connection
2. Enter connection details
3. Test connection
4. Save configuration if successful

---

## Reports & Monitoring

### Sync Logs

#### Access
- Go to WooCommerce → Reports → Sync Logs

#### Information Available
- **Sync Type**: Product, Order, Customer, Inventory
- **Operation**: Import, Export, Update
- **Status**: Success, Error, Warning, In Progress
- **Timing**: Start time, end time, duration
- **Records**: Processed, created, updated, failed
- **Error Details**: Specific error messages

#### Filtering Options
- **Status**: Filter by success, error, warning
- **Sync Type**: Filter by data type
- **Date Range**: Filter by time period
- **Configuration**: Filter by specific configuration

### Sync Reports

#### Access
- Go to WooCommerce → Reports → Sync Report

#### Report Types
- **Performance Reports**: Sync speed and efficiency
- **Error Reports**: Detailed error analysis
- **Trend Reports**: Historical sync patterns
- **Configuration Reports**: Settings and mapping status

---

## Troubleshooting

### Common Issues

#### Connection Issues

**Problem**: Cannot connect to WooCommerce store
**Solutions**:
1. Verify store URL is correct and accessible
2. Check Consumer Key and Secret are valid
3. Ensure REST API is enabled in WooCommerce
4. Verify firewall/network connectivity

#### Sync Failures

**Problem**: Synchronization fails with errors
**Solutions**:
1. Check sync logs for specific error messages
2. Verify data mapping is correct
3. Ensure required fields are populated
4. Check for duplicate records

#### Performance Issues

**Problem**: Slow synchronization or timeouts
**Solutions**:
1. Increase connection timeout in configuration
2. Reduce sync batch sizes
3. Schedule syncs during off-peak hours
4. Check server resources

### Error Messages

#### "Invalid API Credentials"
- Verify Consumer Key and Secret
- Regenerate API credentials if needed
- Check API permissions in WooCommerce

#### "Store URL Not Accessible"
- Verify URL is correct
- Check network connectivity
- Ensure HTTPS is used

#### "Data Mapping Required"
- Configure mappings using Mapping Wizard
- Verify all required mappings are set
- Check for missing field mappings

### Getting Help

#### Support Resources
- **Documentation**: This user guide
- **Logs**: Check sync logs for detailed error information
- **Configuration**: Verify all settings are correct
- **ECOSIRE Support**: Contact info@ecosire.com

#### Debug Information
When reporting issues, provide:
1. Error messages from sync logs
2. Configuration settings (without sensitive data)
3. WooCommerce version and setup
4. Odoo version and environment details

---

## Best Practices

### Configuration Best Practices

1. **Use Descriptive Names**
   - Name configurations clearly (e.g., "Production Store", "Test Environment")
   - Include store URL or purpose in name

2. **Secure API Credentials**
   - Store credentials securely
   - Use read/write permissions appropriately
   - Regularly rotate API keys

3. **Test Before Production**
   - Always test configurations in a test environment
   - Verify mappings before full synchronization
   - Start with small data sets

### Synchronization Best Practices

1. **Start Small**
   - Begin with a few products or orders
   - Gradually increase sync volume
   - Monitor performance and errors

2. **Schedule Appropriately**
   - Avoid peak business hours for large syncs
   - Use appropriate sync frequencies
   - Monitor sync performance

3. **Regular Monitoring**
   - Check sync logs regularly
   - Monitor for errors and warnings
   - Review sync statistics

### Data Management Best Practices

1. **Backup Before Major Changes**
   - Backup data before large imports/exports
   - Test changes in non-production environment
   - Have rollback plans ready

2. **Handle Duplicates**
   - Configure duplicate handling strategies
   - Use unique identifiers for mapping
   - Regular cleanup of duplicate records

3. **Maintain Data Quality**
   - Regular validation of synchronized data
   - Monitor for data inconsistencies
   - Implement data quality checks

### Performance Optimization

1. **Optimize Sync Frequency**
   - Balance between real-time and performance
   - Use appropriate batch sizes
   - Monitor server resources

2. **Efficient Mappings**
   - Use efficient mapping strategies
   - Minimize unnecessary field mappings
   - Optimize data transformation rules

3. **Resource Management**
   - Monitor server CPU and memory usage
   - Optimize database queries
   - Use appropriate timeouts

---

## Advanced Features

### Custom Mappings

#### Creating Custom Mappings
1. Use the Mapping Wizard
2. Define custom field mappings
3. Set transformation rules
4. Test mappings thoroughly

#### Mapping Strategies
- **Direct Mapping**: Simple field-to-field mapping
- **Transformation Mapping**: Data transformation rules
- **Conditional Mapping**: Rules-based mapping
- **Default Value Mapping**: Fallback values

### Multi-Store Management

#### Managing Multiple Stores
1. Create separate configurations for each store
2. Use descriptive names for easy identification
3. Monitor each store independently
4. Configure store-specific mappings

#### Best Practices for Multi-Store
- **Centralized Management**: Use Odoo as central management point
- **Store-Specific Settings**: Configure each store appropriately
- **Independent Monitoring**: Monitor each store separately
- **Consistent Naming**: Use consistent naming conventions

---

## Conclusion

The WooCommerce Automation module provides powerful integration capabilities between Odoo and WooCommerce. By following this user guide and best practices, you can effectively manage your e-commerce operations with automated synchronization and comprehensive monitoring.

### Support & Updates

For support, updates, and additional features:
- **Website**: https://www.ecosire.com/
- **Email**: info@ecosire.com
- **Documentation**: Check for updated guides and tutorials

### Version Information

- **Module Version**: 18.0.1.0.0
- **Odoo Compatibility**: Odoo 18.0+
- **WooCommerce Compatibility**: WooCommerce 3.0+
- **Last Updated**: August 2024

---

*This user guide is provided by ECOSIRE (PRIVATE) LIMITED. For technical support and questions, please contact info@ecosire.com.*
