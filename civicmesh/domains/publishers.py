class CrimePublisher:

    def __init__(
        self,
        commune,
        generator,
        perception,
        publish,
        rumor_provider,
    ):
        self.commune = commune
        self.generator = generator
        self.perception = perception
        self.publish = publish
        self.rumor_provider = (
            rumor_provider
        )

    def tick(self, timestamp):

        events = (
            self.generator.generate_step(
                self.commune,
                timestamp,
            )
        )

        # 1. Publicar ground truth
        for event in events:
            self.publish(
                self.commune,
                "objective",
                event,
            )

        total = sum(
            event["count"]
            for event in events
        )

        # 2. Calcular percepción
        subjective = (
            self.perception.step(
                ground_truth=total,
                gossip_values=(
                    self.rumor_provider(
                        self.commune
                    )
                ),
                timestamp=timestamp,
            )
        )

        # 3. Publicar percepción
        self.publish(
            self.commune,
            "subjective",
            subjective,
        )

        return events, subjective


class AirQualityPublisher:

    def __init__(
        self,
        commune,
        replay,
        perception,
        publish,
        rumor_provider,
        pollutant="pm2_5",
    ):

        if pollutant not in {
            "pm2_5",
            "pm10",
        }:
            raise ValueError(
                "pollutant must be "
                "pm2_5 or pm10"
            )

        self.commune = commune
        self.replay = replay
        self.perception = perception
        self.publish = publish
        self.rumor_provider = (
            rumor_provider
        )
        self.pollutant = pollutant

    def tick(self):

        # 1. Leer siguiente muestra real
        sample = (
            self.replay.next_sample()
        )

        objective = (
            sample.to_payload()
        )

        # 2. Publicar ground truth
        self.publish(
            self.commune,
            "objective",
            objective,
        )

        value = getattr(
            sample,
            self.pollutant,
        )

        # 3. Calcular percepción
        subjective = (
            self.perception.step(
                value=value,
                gossip_values=(
                    self.rumor_provider(
                        self.commune
                    )
                ),
                timestamp=(
                    sample.timestamp
                ),
            )
        )

        subjective["pollutant"] = (
            self.pollutant
        )

        subjective["unit"] = "ug/m3"

        # 4. Publicar percepción
        self.publish(
            self.commune,
            "subjective",
            subjective,
        )

        return objective, subjective
