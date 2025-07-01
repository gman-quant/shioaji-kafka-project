# Shioaji Kafka Bridge

一個健壯、可投入生產環境的服務，用於接收台灣期貨交易所的即時報價 (Tick data)，並將其發佈到 Apache Kafka 叢集中。本專案透過 Shioaji API 獲取資料，並設計了完整的高可用性與容錯機制。

---

## 核心功能

* **📈 即時資料流**: 穩定接收 Shioaji API 推播的台指期貨（TXF）逐筆報價。
* **🧩 模組化架構**: 採用現代化的專案結構，將設定、連線管理、業務邏輯等完全分離，易於維護與擴展。
* **🔄 智慧自動重連**: 能自動偵測並處理網路中斷、API Session 失效等問題，實現服務的自我修復。
* **🗓️ 假日/休市偵測**: 在長時間未收到報價時，能智慧地區分是「連線問題」還是「市場休市」，避免不必要的資源浪費和錯誤警報。
* **⚡️ 高效能 Producer**: 透過批次傳送 (`batch.size`, `linger.ms`) 與訊息壓縮 (`compression.type`)，優化了 Kafka Producer 的效能，適合高流量的資料場景。
* **📝 清晰的日誌監控**: 在服務啟動、市場狀態轉換（開盤/收盤）、發生錯誤時，都會打印出清晰、易讀的日誌，方便維運人員監控。
* **🔑 設定檔驅動**: 所有的敏感金鑰與環境配置都透過 `.env` 檔案管理，確保程式碼的安全性與可攜性。

## 系統架構

本專案在系統中扮演「橋樑」的角色，其資料流如下：

```
+--------------+      +-------------------------+      +-------------------------+
| Shioaji API  | <--> |  Shioaji Kafka Bridge   | ---> |   Apache Kafka Server   |
|   (Quote)    |      |        (Service)        |      |  (Streamming Platform)  |
+--------------+      +-------------------------+      +-------------------------+
```

## 事前準備

在開始之前，請確保您已準備好以下環境：

1.  **Python**: 建議版本 3.9 或以上。
2.  **Apache Kafka**: 一個正在運行的 Kafka 叢集 (及 Zookeeper)。
3.  **Shioaji 帳戶**: 一組有效的永豐期貨 Shioaji API Key 及 Secret Key。

## 安裝與設定

請依照以下步驟來設定您的開發環境：

1.  **複製專案倉庫**:
    ```bash
    git clone <your-repository-url>
    cd shioaji-kafka-project
    ```

2.  **建立並啟用 Python 虛擬環境**:
    ```bash
    # 建立虛擬環境
    python -m venv venv

    # 在 Windows 上啟用
    .\venv\Scripts\activate

    # 在 macOS/Linux 上啟用
    source venv/bin/activate
    ```

3.  **安裝專案依賴**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **設定環境變數**:
    專案根目錄中包含一個 `.gitignore` 檔案，它會忽略 `.env` 檔案以保護您的金鑰。請手動建立此檔案：

    ```bash
    # 建立 .env 檔案
    touch .env
    ```

    然後將以下內容填入 `.env` 檔案，並換成您自己的設定：

    ```ini
    # .env

    # --- Shioaji API Credentials ---
    SHIOAJI_API_KEY="YOUR_API_KEY"
    SHIOAJI_SECRET_KEY="YOUR_SECRET_KEY"

    # --- Kafka Configuration ---
    KAFKA_BROKER="your_kafka_broker_ip:9092"
    KAFKA_TOPIC="your_target_topic_name"
    ```

## 執行服務

完成設定後，您可以透過以下指令啟動服務：

```bash
python src/main.py
```

服務啟動後，您會在終端機中看到詳細的日誌輸出，包括初始的市場狀態、連線狀況等。要停止服務，請按 `Ctrl+C`，程式會執行優雅的關閉程序。

## 組態設定

除了 `.env` 中的設定，一些行為參數可以在 `src/shioaji_kafka_bridge/config.py` 中進行調整：

* `MONITOR_INTERVAL`: 健康檢查的間隔秒數（預設 30 秒）。
* `TIMEOUT_SECONDS`: 判斷為 Tick 中斷的秒數（預設 360 秒）。
* `MAX_TIMEOUT_RETRIES`: 在觸發假日偵測前的重試次數（預設 3 次）。
* `TRADING_BUFFER_MIN`: 在開盤/收盤時間前後的緩衝分鐘數（預設 1 分鐘）。

## 授權 (License)

本專案採用 MIT 授權。詳情請見 `LICENSE` 檔案。
