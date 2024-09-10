import sqlite3
import pandas as pd
import os


def load_valuer_general_data(connection):
    # https://valuation.property.nsw.gov.au/embed/propertySalesInformation/
    data_dir = r"NSW_Property_Projection_Personal_Project\Data\Valuer_General\Data"
    filtered_data = []
    for dat in os.listdir(data_dir):
        with open(os.path.join(data_dir, dat), "r") as file:
            for line in file:
                row = line.split(";")
                if row[0] == "B":
                    filtered_data.append(row)
    # Create a DataFrame from the filtered data, and dropping the New Line column.
    VG_Data = pd.DataFrame(
        filtered_data,
        columns=[
            "Record Type",
            "District Code",
            "Property ID",
            "Sale Counter",
            "Download Date / Time",
            "Property Name",
            "Property Unit Number",
            "Property House Number",
            "Property Street Name",
            "Property Locality",
            "Property Post Code",
            "Area",
            "Area Type",
            "Contract Date",
            "Settlement Date",
            "Purchase Price",
            "Zoning",
            "Nature of Property",
            "Primary Purpose",
            "Strata Lot Number",
            "Component Code",
            "Sale Code",
            "% Interest of Sale",
            "Dealing Number",
            "New Line",
        ],
    ).drop(columns=["New Line"])
    VG_Data.to_sql("Valuer_General", connection, if_exists="replace", index=False)


def load_cash_rate_data(connection):
    # https://www.rba.gov.au/statistics/tables/
    df_cash_rate = pd.read_csv(
        r"NSW_Property_Projection_Personal_Project\Data\Cash_Rate\f1.1-data.csv"
    )
    df_cash_rate.to_sql("Cash_Rate", connection, if_exists="replace", index=False)


def load_cpi_data(connection):
    # https://www.abs.gov.au/statistics/economy/price-indexes-and-inflation/consumer-price-index-australia/mar-quarter-2024/
    df_cpi = pd.read_excel(
        r"NSW_Property_Projection_Personal_Project\Data\Consumer_Price_Index\Cleaned CPI by Group and Capital City.xlsx",
        sheet_name=1,
    )
    df_cpi.to_sql("CPI", connection, if_exists="replace", index=False)


def load_crime_data(connection):
    # https://www.bocsar.nsw.gov.au/Pages/bocsar_datasets/Offence.aspx
    df_crime = pd.read_csv(
        r"NSW_Property_Projection_Personal_Project\Data\Crime\PostcodeData2023.csv"
    )
    melted_df = df_crime.melt(
        id_vars=["Postcode", "Offence category", "Subcategory"],
        var_name="Date",
        value_name="Count",
    )
    melted_df["Date"] = pd.to_datetime(melted_df["Date"], errors="coerce")
    melted_df.to_sql("Crime", connection, if_exists="replace", index=False)


def load_gdp_data(connection):
    # https://www.abs.gov.au/statistics/economy/national-accounts/australian-national-accounts-national-income-expenditure-and-product/latest-release#data-downloads/
    df_gdp = pd.read_excel(
        r"NSW_Property_Projection_Personal_Project\Data\GDP\5206001_Key_Aggregates.xlsx",
        sheet_name=1,
    )
    df_gdp.to_sql("GDP", connection, if_exists="replace", index=False)


def load_census_data(connection):
    # https://www.abs.gov.au/census/find-census-data/datapacks/
    print("Hello world")


def main():
    connection = sqlite3.connect(
        r"NSW_Property_Projection_Personal_Project\property_data.db"
    )

    load_valuer_general_data(connection)
    load_cash_rate_data(connection)
    load_cpi_data(connection)
    load_crime_data(connection)
    load_gdp_data(connection)
    load_census_data(connection)

    connection.commit()
    connection.close()


if __name__ == "__main__":
    main()
