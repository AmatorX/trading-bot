# from pydantic_settings import BaseSettings
# from typing import Literal
#
#
# class Settings(BaseSettings):
#     # Webhook
#     webhook_secret_token: str = "test_token_change_in_production"
#     trade_signal_token: str
#
#     # Exchange defaults
#     exchange: Literal["binance", "okx", "bybit", "bitget"] = "bybit"
#     contract_type: Literal["USDT-M", "COIN-M"] = "USDT-M"
#
#     # Position defaults
#     size_position: float = 100.0
#     default_leverage: int = 35
#     order_type: Literal["market", "limit"] = "market"  # Тип ордера для входа: market или limit
#
#     # ATR settings
#     atr_period: int = 5  # Стандартный период ATR (обычно 14)
#     atr_timeframe: str = "1d"  # Таймфрейм для расчета ATR (5m, 15m, 1h, 4h, 1d)
#     stop_loss_rate: float = 0.10
#     take_profit_rate: float = 0.30
#
#     # Risk limits
#     max_position_size: float = 1000.0
#
#     # Binance
#     binance_api_key: str = ""
#     binance_api_secret: str = ""
#     binance_sandbox: bool = False
#
#     # OKX
#     okx_api_key: str = ""
#     okx_api_secret: str = ""
#     okx_passphrase: str = ""
#     okx_sandbox: bool = False
#
#     # BYBIT
#     bybit_api_key: str = ""
#     bybit_api_secret: str = ""
#     bybit_sandbox: bool = False
#
#     # Bitget
#     bitget_api_key: str = ""
#     bitget_api_secret: str = ""
#     bitget_passphrase: str = ""
#     bitget_sandbox: bool = False
#
#     class Config:
#         env_file = ".env"
#         env_file_encoding = "utf-8"
#         case_sensitive = False
#         extra = "ignore"  # Игнорировать лишние переменные
#
#
# settings = Settings()
#
# from pydantic_settings import BaseSettings, SettingsConfigDict
# from typing import Literal
#
#
# class Settings(BaseSettings):
#     # Webhook
#     webhook_secret_token: str
#     trade_signal_token: str  # обязательный (берётся из .env)
#
#     # Exchange defaults
#     exchange: Literal["binance", "okx", "bybit", "bitget"] = "bybit"
#     contract_type: Literal["USDT-M", "COIN-M"] = "USDT-M"
#
#     # Position defaults
#     size_position: float = 100.0
#     default_leverage: int = 35
#     order_type: Literal["market", "limit"] = "market"
#
#     # ATR settings
#     atr_period: int = 5
#     atr_timeframe: str = "1d"
#     stop_loss_rate: float = 0.10
#     take_profit_rate: float = 0.30
#
#     # Risk limits
#     max_position_size: float = 1000.0
#
#     # Binance
#     binance_api_key: str = ""
#     binance_api_secret: str = ""
#     binance_sandbox: bool = False
#
#     # OKX
#     okx_api_key: str = ""
#     okx_api_secret: str = ""
#     okx_passphrase: str = ""
#     okx_sandbox: bool = False
#
#     # BYBIT
#     bybit_api_key: str = ""
#     bybit_api_secret: str = ""
#     bybit_sandbox: bool = False
#
#     # Bitget
#     bitget_api_key: str = ""
#     bitget_api_secret: str = ""
#     bitget_passphrase: str = ""
#     bitget_sandbox: bool = False
#
#     model_config = SettingsConfigDict(
#         env_file=".env",
#         env_file_encoding="utf-8",
#         case_sensitive=False,
#         extra="ignore",
#     )
#
#
# settings = Settings()

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal


class Settings(BaseSettings):
    # --------------------------------------------------
    # Webhook
    # --------------------------------------------------
    webhook_secret_token: str
    trade_signal_token: str

    # --------------------------------------------------
    # Exchange defaults
    # --------------------------------------------------
    exchange: Literal["binance", "okx", "bybit", "bitget"] = "bybit"
    contract_type: Literal["USDT-M", "COIN-M"] = "USDT-M"

    # --------------------------------------------------
    # Order / position defaults
    # --------------------------------------------------
    size_position: float = 100.0          # USDT (для fixed_size)
    default_leverage: int = 35
    order_type: Literal["market", "limit"] = "market"

    # --------------------------------------------------
    # Risk mode (NEW)
    # --------------------------------------------------
    risk_mode: Literal["fixed_size", "fixed_risk_atr"] = "fixed_risk_atr"

    # --------------------------------------------------
    # ATR settings
    # --------------------------------------------------
    atr_period: int = 5
    atr_timeframe: str = "1d"

    # --- fixed_size mode ---
    stop_loss_rate: float = 0.10          # % от ATR
    take_profit_rate: float = 0.30        # % от ATR

    # --- fixed_risk_atr mode (NEW) ---
    risk_per_trade: float = 1.0           # USDT
    atr_multiplier: float = 1.0
    risk_reward_ratio: float = 3.0

    # --------------------------------------------------
    # Safety limits (NEW)
    # --------------------------------------------------
    max_position_usdt: float = 300.0
    min_position_usdt: float = 30.0

    # --------------------------------------------------
    # Binance
    # --------------------------------------------------
    binance_api_key: str = ""
    binance_api_secret: str = ""
    binance_sandbox: bool = False

    # --------------------------------------------------
    # OKX
    # --------------------------------------------------
    okx_api_key: str = ""
    okx_api_secret: str = ""
    okx_passphrase: str = ""
    okx_sandbox: bool = False

    # --------------------------------------------------
    # BYBIT
    # --------------------------------------------------
    bybit_api_key: str = ""
    bybit_api_secret: str = ""
    bybit_sandbox: bool = False

    # --------------------------------------------------
    # Bitget
    # --------------------------------------------------
    bitget_api_key: str = ""
    bitget_api_secret: str = ""
    bitget_passphrase: str = ""
    bitget_sandbox: bool = False

    # --------------------------------------------------
    # Pydantic config
    # --------------------------------------------------
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
