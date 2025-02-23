Installation Guide
=================

This guide will help you get PulsarNet up and running on your system.

Prerequisites
------------

* Python 3.8 or higher
* pip (Python package installer)
* Git (for cloning the repository)

Installation Steps
----------------

1. Clone the Repository
   
   .. code-block:: bash

      git clone https://github.com/yourusername/pulsarnet.git
      cd pulsarnet

2. Install Dependencies
   
   .. code-block:: bash

      pip install -r requirements.txt

   This will install all required packages including:

   * PyQt6 - GUI framework
   * Netmiko - Network device communication
   * Various protocol libraries (TFTP, SFTP, etc.)
   * Development and testing tools

3. Configure the Application

   a. Create a copy of the example environment file:

      .. code-block:: bash

         cp .env.example .env

   b. Edit the .env file with your specific settings:
      
      * Backup server details
      * Default protocols
      * Storage locations
      * Logging preferences

4. Run the Application

   .. code-block:: bash

      python main.py

Troubleshooting
--------------

Common Issues
~~~~~~~~~~~~

1. **Missing Dependencies**
   
   If you encounter missing dependency errors, try:

   .. code-block:: bash

      pip install --upgrade -r requirements.txt

2. **Permission Issues**
   
   Ensure you have appropriate permissions for:
   
   * Network device access
   * Backup storage locations
   * Configuration file directories

3. **Protocol Errors**
   
   Verify that:
   
   * Required ports are open
   * Server credentials are correct
   * Network connectivity is available

Next Steps
----------

After installation, refer to the :doc:`user_guide/index` for:

* Basic usage instructions
* Configuration options
* Advanced features
* Best practices