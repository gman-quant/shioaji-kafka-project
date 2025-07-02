![Python](https://img.shields.io/badge/python-3.9%2B-blue)  
![Apache Kafka](https://img.shields.io/badge/Kafka-required-orange)  
![Shioaji](https://img.shields.io/badge/SHIOAJI-required-orange)  
![License: MIT](https://img.shields.io/badge/License-MIT-green)


# Shioaji Kafka Bridge

Production-ready service streaming real-time Taiwan Futures Exchange (TAIFEX) tick data via Shioaji API to Apache Kafka, built for high availability and modularity.

> Ideal for trading systems or data pipelines needing high-frequency TAIFEX futures data via Shioaji and Kafka.


---

## Features

- **📈 Real-time Tick Streaming**  
  Streams high-frequency TXF tick data from the Shioaji API to Kafka with minimal latency.

- **🧩 Modular Design**  
  Separates config, connection, and logic for easy maintenance and scalability.

- **🔄 Auto-Reconnect**  
  Automatically recovers from network or session failures for uninterrupted operation.

- **🗓️ Market Holiday Detection**  
  Distinguishes between genuine disconnections and market closure to avoid false alerts.

- **⚡️ Kafka Optimization**  
  Uses batching (`batch.size`, `linger.ms`) and compression (`compression.type`) for performance.

- **📝 Transparent Logging**  
  Emits structured, human-readable logs covering market transitions and errors.

- **🔑 `.env`-Driven Configuration**  
  Securely manages credentials and settings through environment variables.

---

## System Architecture

This project acts as a "bridge" in the system, with the following data flow:

```
+----------------+      +------------------------+      +------------------------+
|  Shioaji API   | <--> |  Shioaji Kafka Bridge  | ---> |      Apache Kafka      |
| (Quote Source) |      |     (This Service)     |      |  (Streaming Platform)  |
+----------------+      +------------------------+      +------------------------+
```

---


## Prerequisites

Before you begin, ensure you have the following ready:

1.  **Python**: Version 3.9 or higher.
2.  **Apache Kafka**: A running Kafka cluster.
3.  **Shioaji Account**: A valid set of API Key and Secret Key for SinoPac Futures Shioaji.

---

## Installation and Setup

Follow these steps to set up your development environment:

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/gman-quant/shioaji-kafka-project.git
    ```

2.  **Create and activate a Python virtual environment**:
    ```bash
    # Create the virtual environment
    python -m venv venv
    ```
    ```bash
    # Activate on macOS/Linux
    source venv/bin/activate
    ```
    ```bash
    # Activate on Windows (Git Bash)
    source venv/Scripts/activate
    ```

3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up environment variables**:
    The root directory includes a `.gitignore` file that ignores `.env` to protect your keys. Please create this file manually:

    ```bash
    # Create the .env file
    touch .env
    ```

    Then, add the following content to your `.env` file and replace the placeholders with your own settings:

    ```ini
    # .env

    # --- Shioaji API Credentials ---
    SHIOAJI_API_KEY="YOUR_API_KEY"
    SHIOAJI_SECRET_KEY="YOUR_SECRET_KEY"

    # --- Kafka Configuration ---
    KAFKA_BROKER="your_kafka_broker_address:9092"
    KAFKA_TOPIC="your_target_topic_name"
    ```

---

## Running the Service

Once the setup is complete, you can start the service with the following command:

```bash
python src/main.py
```

After the service starts, you will see detailed log output in your terminal, including the initial market status and connection details. To stop the service, press `Ctrl+C` for a graceful shutdown.

---

## Configuration

In addition to the settings in `.env`, some behavioral parameters can be adjusted in `src/shioaji_kafka_bridge/config.py`:

* `MONITOR_INTERVAL`   : The interval in seconds for health checks (default: 30 seconds).
* `TIMEOUT_SECONDS`    : The duration in seconds to wait before considering a tick stream disconnected (default: 360 seconds).
* `MAX_TIMEOUT_RETRIES`: The number of retries before triggering holiday detection (default: 3).
* `TRADING_BUFFER_MIN` : A buffer in minutes around the market open/close times (default: 1 minute).

---

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
