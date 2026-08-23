import csv
from pathlib import Path

import requests

from civicmesh.domains.config import (
    load_domain_config,
)


API_URL = (
    "https://air-quality-api."
    "open-meteo.com/v1/air-quality"
)


def main():

    config = load_domain_config()

    output = Path(
        config.air_dataset
    )

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    rows = []

    for commune, coordinates in (
        config.air_locations.items()
    ):

        response = requests.get(
            API_URL,
            params={
                "latitude": (
                    coordinates["latitude"]
                ),
                "longitude": (
                    coordinates["longitude"]
                ),
                "hourly": "pm2_5,pm10",
                "start_date": (
                    config.air_start_date
                ),
                "end_date": (
                    config.air_end_date
                ),
            },
            timeout=60,
        )

        response.raise_for_status()

        hourly = response.json()[
            "hourly"
        ]

        for (
            timestamp,
            pm2_5,
            pm10,
        ) in zip(
            hourly["time"],
            hourly["pm2_5"],
            hourly["pm10"],
        ):

            if (
                pm2_5 is None
                or pm10 is None
            ):
                continue

            rows.append({
                "timestamp": timestamp,
                "commune": commune,
                "pm2_5": pm2_5,
                "pm10": pm10,
                "latitude": (
                    coordinates["latitude"]
                ),
                "longitude": (
                    coordinates["longitude"]
                ),
                "source": "open-meteo",
            })

    with output.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=[
                "timestamp",
                "commune",
                "pm2_5",
                "pm10",
                "latitude",
                "longitude",
                "source",
            ],
        )

        writer.writeheader()
        writer.writerows(rows)

    print(
        f"Dataset guardado en "
        f"{output}: {len(rows)} muestras"
    )


if __name__ == "__main__":
    main()
