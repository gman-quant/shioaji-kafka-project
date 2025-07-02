# Shioaji Kafka Bridge

A robust, production-ready service designed to consume real-time tick data from the Taiwan Futures Exchange (TAIFEX) and publish it to an Apache Kafka cluster. This project utilizes the Shioaji API to fetch data and is built with high availability and fault tolerance in mind.

---

## Core Features

* **📈 Real-time Data Stream**: Stably consumes real-time tick-by-tick quote data for Taiwan Stock Index Futures (TXF) pushed by the Shioaji API.
* **🧩 Modular Architecture**: Adopts a modern project structure that completely separates configuration, connection management, and business logic for easy maintenance and expansion.
* **🔄 Intelligent Auto-Reconnect**: Automatically detects and handles issues like network interruptions and API session failures, enabling service self-healing.
* **🗓️ Holiday/Market Close Detection**: Intelligently distinguishes between connection issues and market holidays during long periods of no data, preventing unnecessary resource waste and false alarms.
* **⚡️ High-Performance Producer**: The Kafka producer is optimized for high-traffic scenarios through message batching (`batch.size`, `linger.ms`) and compression (`compression.type`).
* **📝 Clear Log Monitoring**: Provides clear, human-readable logs for service startup, market state transitions (open/close), and error events, facilitating easy monitoring by operators.
* **🔑 Configuration-Driven**: All sensitive keys and environmental configurations are managed via a `.env` file, ensuring code security and portability.

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

1.  **Python**: Version 3.8 or higher is recommended.
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

    # Activate on macOS/Linux
    source venv/bin/activate
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
