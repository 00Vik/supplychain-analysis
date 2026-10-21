supply_chain_project/
│
├── config.py
├── download.py
├── clean.py
├── analysis.py
├── database.py
├── run.py
│
├── data/
│   ├── raw/
|   |   ├── raw_China_854142.csv
│   |   └── raw_China_854143.csv
│   ├── processed/
|   |   ├── China_854142/
│   │   |   └── trade_clean.csv
│   |   └── China_854143/
│   |       └── trade_clean.csv
│   └── output/
|       ├── China_854142/
|       │   ├── global_trade.csv
|       │   └── ...
|       └── China_854143/
|           └── ...
│
└── requirements.txt