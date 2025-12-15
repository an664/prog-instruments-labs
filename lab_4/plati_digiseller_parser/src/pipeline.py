from pathlib import Path

from src.config import AppConfig
from src.data_processing.data_processor import process_data
from src.utils.logging_config import setup_logging
from src.visualisation.data_visualisation import (
    plot_sales_data,
    create_data_table,
    plot_comparison,
    plot_changes,
)

logger = setup_logging("pipeline")


def run_pipeline(config_path: Path = Path("config/config.yaml")) -> None:
    config = AppConfig.from_file(config_path)

    logger.info("Running data pipeline")
    process_data(config)

    plot_sales_data(
        config.database_path,
        config.visualization.start_date,
        config.visualization.end_date,
    )
    df_plati, df_digiseller = create_data_table(
        config.database_path,
        config.visualization.start_date,
        config.visualization.end_date,
    )
    df_plati.to_csv(
        Path("data/processed/plati_market_data.csv"),
        index=False,
    )
    df_digiseller.to_csv(
        Path("data/processed/digiseller_data.csv"),
        index=False,
    )
    plot_comparison(
        config.database_path,
        config.visualization.start_date,
        config.visualization.end_date,
    )
    plot_changes({
        "visualization": {
            "start_date": config.visualization.start_date,
            "end_date": config.visualization.end_date,
        }
    })
    logger.info("Pipeline finished")


if __name__ == "__main__":
    run_pipeline()
