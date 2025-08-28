# Odoo WooCommerce Automation

A comprehensive WooCommerce integration module for Odoo 18, developed by ECOSIRE (PRIVATE) LIMITED.

## 🚀 Features

### Core Functionality
- **Bidirectional Product Synchronization**: Import/export products between Odoo and WooCommerce
- **Order Management**: Automatic order import and status synchronization
- **Customer Data Sync**: Bidirectional customer information synchronization
- **Inventory Management**: Real-time inventory updates
- **Advanced Configuration**: Multiple store support with customizable settings

### Technical Features
- **REST API Integration**: Full WooCommerce REST API v3 support
- **Automated Scheduling**: Configurable sync intervals and automated workflows
- **Error Handling**: Comprehensive error tracking and retry mechanisms
- **Logging & Monitoring**: Detailed sync logs and performance metrics
- **Webhook Support**: Real-time event processing
- **Dashboard Analytics**: Real-time monitoring and reporting

## 📋 Requirements

### System Requirements
- **Odoo Version**: 18.0 or higher
- **Python Version**: 3.8 or higher
- **Database**: PostgreSQL 12.0 or higher
- **WooCommerce**: 5.0 or higher

### Python Dependencies
```bash
pip install requests>=2.25.1
pip install woocommerce>=3.0.0
```

## 🛠️ Installation

### 1. Module Installation
1. Copy the `odoo_woocommerce_automation` folder to your Odoo addons directory
2. Update the addons list in Odoo
3. Install the module from the Apps menu

### 2. WooCommerce Setup
1. In your WooCommerce store, go to **WooCommerce > Settings > Advanced > REST API**
2. Click **Add Key**
3. Set permissions to **Read/Write**
4. Copy the **Consumer Key** and **Consumer Secret**

### 3. Module Configuration
1. Go to **WooCommerce > Configuration**
2. Create a new configuration with your WooCommerce store details
3. Test the connection using the "Test Connection" button
4. Configure sync settings according to your needs

## 🔧 Configuration

### Basic Configuration
- **Store URL**: Your WooCommerce store URL (e.g., https://yourstore.com)
- **Consumer Key**: WooCommerce REST API Consumer Key
- **Consumer Secret**: WooCommerce REST API Consumer Secret
- **API Version**: WC v3 (recommended)

### Sync Settings
- **Sync Products**: Enable/disable product synchronization
- **Sync Orders**: Enable/disable order synchronization
- **Sync Customers**: Enable/disable customer synchronization
- **Sync Inventory**: Enable/disable inventory synchronization
- **Auto Sync**: Enable automatic synchronization on changes
- **Sync Frequency**: Set sync intervals (5min to daily)

## 📊 Dashboard

The WooCommerce Dashboard provides:
- **Connection Status**: Real-time connection monitoring
- **Sync Statistics**: Products, orders, and customers synced
- **Error Tracking**: Recent sync errors and issues
- **Quick Actions**: One-click sync operations
- **Performance Metrics**: Sync duration and success rates

## 🔄 Synchronization

### Product Sync
- **Import**: Import products from WooCommerce to Odoo
- **Export**: Export Odoo products to WooCommerce
- **Update**: Sync product changes bidirectionally
- **Inventory**: Real-time stock level synchronization

### Order Sync
- **Import**: Import new orders from WooCommerce
- **Status Updates**: Sync order status changes
- **Customer Data**: Link orders with customer information
- **Payment Status**: Track payment and fulfillment status

### Customer Sync
- **Import**: Import customers from WooCommerce
- **Export**: Export Odoo contacts to WooCommerce
- **Address Sync**: Synchronize billing and shipping addresses
- **Order History**: Link customer order history

## 🛡️ Security

### API Security
- **OAuth 1.0a Authentication**: Secure API communication
- **HTTPS Required**: All connections use SSL/TLS
- **API Key Management**: Secure storage of credentials
- **Access Control**: Role-based permissions

### Data Protection
- **Encrypted Storage**: Sensitive data encryption
- **Audit Logging**: Complete sync history tracking
- **Error Handling**: Secure error reporting
- **Data Validation**: Input validation and sanitization

## 📈 Monitoring & Logs

### Sync Logs
- **Detailed Logging**: Complete sync operation history
- **Error Tracking**: Failed operations with error details
- **Performance Metrics**: Sync duration and throughput
- **Retry Mechanisms**: Automatic retry for failed operations

### Dashboard Monitoring
- **Real-time Status**: Live connection and sync status
- **Performance Analytics**: Sync performance metrics
- **Error Alerts**: Immediate notification of issues
- **Historical Data**: Long-term sync statistics

## 🔌 API Endpoints

### REST API
- `GET /woocommerce/api/status` - Get connection status
- `POST /woocommerce/api/sync` - Trigger synchronization
- `GET /woocommerce/dashboard/data` - Get dashboard data

### Webhooks
- `POST /woocommerce/webhook` - Handle WooCommerce webhooks
- Supports product, order, and customer webhooks
- Real-time event processing

## 🚨 Troubleshooting

### Common Issues

#### Connection Issues
1. **Invalid URL**: Ensure WooCommerce URL is correct and accessible
2. **API Credentials**: Verify Consumer Key and Secret are correct
3. **SSL Certificate**: Ensure HTTPS is properly configured
4. **Firewall**: Check if firewall blocks API connections

#### Sync Issues
1. **Rate Limiting**: WooCommerce API rate limits exceeded
2. **Data Validation**: Invalid data format or missing required fields
3. **Permissions**: Insufficient API permissions
4. **Network Issues**: Temporary network connectivity problems

### Error Codes
- **401 Unauthorized**: Invalid API credentials
- **403 Forbidden**: Insufficient permissions
- **429 Too Many Requests**: Rate limit exceeded
- **500 Internal Server Error**: WooCommerce server error

## 📝 Development

### Extending the Module
The module is designed for easy extension:
- **Custom Sync Logic**: Override sync methods for custom behavior
- **Additional Fields**: Extend models for custom fields
- **Custom Reports**: Create custom reporting and analytics
- **API Extensions**: Add custom API endpoints

### Code Structure
```
odoo_woocommerce_automation/
├── models/                 # Data models
├── views/                  # UI views and forms
├── wizard/                 # Wizard dialogs
├── controllers/            # API controllers
├── security/              # Access control
├── data/                  # Initial data
├── demo/                  # Demo data
├── static/                # Static assets
└── tools.py              # Utility functions
```

## 📞 Support

### Contact Information
- **Company**: ECOSIRE (PRIVATE) LIMITED
- **Website**: https://www.ecosire.com/
- **Email**: info@ecosire.com
- **Official Number**: 0923130168262

### Documentation
- **User Guide**: Available in the module documentation
- **API Reference**: REST API documentation
- **Troubleshooting**: Common issues and solutions
- **Video Tutorials**: Step-by-step setup guides

## 📄 License

This module is licensed under LGPL-3.0 and is compatible with both Odoo Community and Enterprise editions.

## 🔄 Version History

### Version 18.0.1.0.0
- Initial release for Odoo 18
- Full WooCommerce REST API v3 support
- Comprehensive dashboard and monitoring
- Advanced configuration options
- Complete documentation and support

## 🤝 Contributing

We welcome contributions to improve this module:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📋 Changelog

### 18.0.1.0.0 (2024-01-XX)
- Initial release
- WooCommerce REST API v3 integration
- Product, order, and customer synchronization
- Dashboard and monitoring features
- Comprehensive error handling and logging
- Security and performance optimizations

---

**Developed with ❤️ by ECOSIRE (PRIVATE) LIMITED**

For more information, visit: https://www.ecosire.com/ 