# NSW Property Price Forecasting Project

## Overview
This project focuses on forecasting New South Wales (NSW) property prices using historical property data and various economic indicators. The goal is to provide accurate and actionable insights into property market trends to assist in investment decisions.

## Key Features
- **Advanced Forecasting Model**: Integrated historical property data with economic indicators such as GDP, CPI, crime rates, and cash rates using Python.
- **Statistical and Machine Learning Techniques**: Utilized Vector Autoregression (VAR) and XGBoost to forecast future property prices, leveraging historical data and economic factors.
- **Data Management and Analysis**: Managed extensive datasets within a SQLite database, ensuring data integrity and precision through complex transformations and cleaning processes.
- **Time Series Analysis**: Implemented rigorous stationarity testing and time series model fitting to understand and forecast the dynamics of property prices.
- **Data Visualization and Reporting**: Developed insightful visualizations, including NSW growth heatmaps, to demonstrate trends and predictions, enhancing decision-making for real estate investments.

## Data Sources
- **Domain Data**: Property sales data including features like sale type, date, price, and property specifics (bedrooms, baths, parking, etc.).
- **Economic Indicators**:
  - **GDP**: Gross Domestic Product changes and impacts.
  - **CPI**: Consumer Price Index as a measure of inflation.
  - **Crime Rates**: Local crime statistics by postcode.
  - **Cash Rates**: Interest rates set by the Reserve Bank of Australia.
- **Social Indicators**:
  - **Crime Rates**: Crime rates per suburb.
  - **Census Data**: Census data per LGA Area.

## Tools and Technologies
- **Python**: Primary programming language used for data analysis and model building.
- **SQLite**: Database used for storing and managing structured data.
- **Pandas**: Python library for data manipulation and analysis.
- **Statsmodels**: Used for statistical modeling and econometric analysis.
- **XGBoost**: Gradient boosting framework used for building efficient models.
- **Matplotlib** and **Seaborn**: Used for creating static, interactive, and animated visualizations.
