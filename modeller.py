import sqlite3
import pandas as pd
from statsmodels.tsa.api import VAR
import xgboost as xgb
import sklearn.linear_model
import sklearn.model_selection
import sklearn.metrics
from Domain_Scraper import SydneyPostcodes

### Connect to the SQLite database ###
connection = sqlite3.connect(
    "NSW_Property_Projection_Personal_Project/property_data.db"
)

### Load Domain data ###
df = pd.read_sql_query("SELECT * FROM Domain", connection)

### Convert sale_date to datetime ###
df["sale_date"] = pd.to_datetime(df["sale_date"], format="%d %b %Y")

### Drop unnecessary columns & remove whitespaces ###
df = df.drop(["id", "sales_page_href"], axis=1).replace(" ", "_", regex=True)

### Extract quarter & year ###
df["year"] = df["sale_date"].dt.year
df["quarter"] = df["sale_date"].dt.quarter
print(df.head(5))

### Aggregate data ###
aggregated_df = (
    df.groupby(["year", "quarter", "postcode"])
    .agg(
        {
            "price": [
                "mean",
                "count",
            ],  # Aggregate price by mean and count
            "bedrooms": "mean",  # Average number of bedrooms
            "baths": "mean",  # Average number of baths
            "parking": "mean",  # Average number of parking spaces
            "area": "mean",  # Average area
        }
    )
    .reset_index()
)

# Flatten the MultiIndex columns
aggregated_df.columns = [
    "year",
    "quarter",
    "postcode",
    "mean_price",
    "sales_count",
    "average_bedrooms",
    "average_baths",
    "average_parking",
    "average_area",
]

# Count occurrences of different sale types
sale_type_counts = (
    df.groupby(["year", "quarter", "postcode", "sale_type"])
    .size()
    .unstack(fill_value=0)
    .reset_index()
)

# Merge the sale type counts with the aggregated data
domain_df = pd.merge(
    aggregated_df, sale_type_counts, on=["year", "quarter", "postcode"], how="left"
)

domain_df = domain_df.sort_values(by=["year", "quarter", "postcode"])

# Display the first few rows of the final DataFrame
print(domain_df.dtypes)
print(domain_df.shape)
print(domain_df)


print(domain_df["postcode"].sort_values().unique())
# Identifying missing values & erroneous values
print(
    len(
        domain_df.loc[
            (domain_df["mean_price"].isnull()) | (domain_df["mean_price"] == 0)
        ]
    )
)
print(
    domain_df.loc[(domain_df["mean_price"].isnull()) | (domain_df["mean_price"] == 0)]
)

domain_df = domain_df.dropna(subset=["mean_price"])

print(len(domain_df.loc[~domain_df["postcode"].isin(SydneyPostcodes)]))
domain_df = domain_df[domain_df["postcode"].isin(SydneyPostcodes)]

print(domain_df.shape)

### Format data ###
# Split into Dependent & Independent variables
X = domain_df.drop("mean_price", axis=1).copy()
y = domain_df["mean_price"].copy()

### Build prelimary model ###
X_train, X_test, y_train, y_test = sklearn.model_selection.train_test_split(X, y)

# XGBoost
xgb_model = xgb.XGBRegressor(
    n_estimators=1000, early_stopping_rounds=10, eval_metric="mphe"
)
xgb_model.fit(
    X_train,
    y_train,
    verbose=True,
    eval_set=[(X_test, y_test)],
)
# validation_0-mphe:340030.63102

# Customise data for Linear Regression
lm_df = domain_df.dropna()
X_2 = lm_df.drop("mean_price", axis=1).copy()
y_2 = lm_df.mean_price.copy()
X_tr2, X_te2, y_tr2, y_te2 = sklearn.model_selection.train_test_split(X_2, y_2)

# Create and fit the Linear Regression model
lm_model = sklearn.linear_model.LinearRegression()
lm_model.fit(X_tr2, y_tr2)

# Predict on the test set
y_pred = lm_model.predict(X_te2)

# Evaluate the model
print(f"Mean Absolute Error: {sklearn.metrics.mean_absolute_error(y_te2, y_pred)}")
print(f"Mean Squared Error: {sklearn.metrics.mean_squared_error(y_te2, y_pred)}")
print(f"R^2 Score: {sklearn.metrics.r2_score(y_te2, y_pred)}")


##### Adding supplementary data #####

##### Vector Autoregression #####
var_domain_df = lm_df.set_index(["year", "quarter"])

# Fit a VAR model
model = VAR(var_domain_df.drop(columns=["mean_price"]))
fitted_model = model.fit(maxlags=15, ic="aic")

# Forecasting
lag_order = fitted_model.k_ar
forecast_input = lm_df.drop(columns=["mean_price"]).values[-lag_order:]
forecast = fitted_model.forecast(y=forecast_input, steps=4)
forecast_df = pd.DataFrame(
    forecast,
    index=pd.date_range(start=lm_df.index[-1][0], periods=4, freq="Q"),
    columns=lm_df.drop(columns=["mean_price"]).columns,
)

print(forecast_df)
