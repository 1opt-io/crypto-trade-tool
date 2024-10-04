# crypto-exchange-tool

# Re-constructed Structure:
```
src/
│
├── strategies/            # Strategy implementations
│   ├── __init__.py        # Make it a package
│   ├── abstract_strategy   
│   ├── grid_strategy.py   # gird implementation
│   └── other_strategy.py   
│
├── config/                # Configuration files
│   ├── config.json
│   ├── user_api_key.json
│   └── testnet.json       
│
├── exchange/              # Separate directory for exchange interactions
│   ├── __init__.py
│   ├── abstract_exchange        
│   └── exchange.py        # exchange implement with ccxt
│
├── utils/                 # dev utils
│   ├── __init__.py        
│   ├── logger.py
│   ├── utils.py
│   └── edge_cases_handler.py      
│
├── routes/                # Separate directory for Flask routes
│   ├── __init__.py        
│   ├── main_routes.py     # General routes
│   └── config_routes.py   # Routes related to configurations
│
├── forms/                 # Forms for handling user inputs
│   ├── __init__.py        
│   └── user_forms.py      # Rename to be more descriptive
│
├── templates/             # HTML templates
│   ├── index.html
│   ├── data.html
│   ├── set_config.html
│   └── ...
│
└── app.py                 # Main entry point for the application
```
