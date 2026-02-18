"""
Infrastructure — 資料庫連線與 Session 管理。
使用 SQLite (透過 SQLModel / SQLAlchemy)。
"""

import os
from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from logging_config import get_logger

logger = get_logger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///data/radar.db")

# SQLite 需要 check_same_thread=False 以支援多執行緒存取
connect_args = {"check_same_thread": False}
engine = create_engine(DATABASE_URL, echo=False, connect_args=connect_args)

logger.info("資料庫連線位置：%s", DATABASE_URL)


def _run_migrations() -> None:
    """執行資料庫遷移：為既有資料表新增缺少的欄位。"""
    from sqlalchemy import text

    migrations = [
        "ALTER TABLE stock ADD COLUMN current_tags VARCHAR DEFAULT '';",
        "ALTER TABLE thesislog ADD COLUMN tags VARCHAR DEFAULT '';",
        "ALTER TABLE stock ADD COLUMN display_order INTEGER DEFAULT 0;",
        "ALTER TABLE stock ADD COLUMN last_scan_signal VARCHAR DEFAULT 'NORMAL';",
        # Phase: ETF -> Trend_Setter 分類遷移（新五類分類系統）
        "UPDATE stock SET category = 'Trend_Setter' WHERE category = 'ETF';",
        # Holding: 新增券商欄位
        "ALTER TABLE holding ADD COLUMN broker VARCHAR;",
        # Holding: 新增幣別欄位
        "ALTER TABLE holding ADD COLUMN currency VARCHAR DEFAULT 'USD';",
        # Holding: 根據 ticker 後綴回填幣別
        "UPDATE holding SET currency = 'TWD' WHERE ticker LIKE '%.TW' AND currency = 'USD';",
        "UPDATE holding SET currency = 'JPY' WHERE ticker LIKE '%.T' AND currency = 'USD';",
        "UPDATE holding SET currency = 'HKD' WHERE ticker LIKE '%.HK' AND currency = 'USD';",
        # Holding: 現金持倉以 ticker 作為幣別
        "UPDATE holding SET currency = ticker WHERE is_cash = 1 AND currency = 'USD';",
        # Holding: 新增帳戶類型欄位
        "ALTER TABLE holding ADD COLUMN account_type VARCHAR;",
        # ScanLog: 新增市場情緒原因說明欄位
        "ALTER TABLE scanlog ADD COLUMN market_status_details VARCHAR DEFAULT '';",
        # UserInvestmentProfile: 新增本幣欄位（用於匯率曝險計算）
        "ALTER TABLE userinvestmentprofile ADD COLUMN home_currency VARCHAR DEFAULT 'TWD';",
        # UserPreferences: 新增通知偏好 JSON 欄位
        "ALTER TABLE userpreferences ADD COLUMN notification_preferences VARCHAR DEFAULT '{}';",
        # UserPreferences: 新增語言偏好欄位 (i18n support)
        "ALTER TABLE userpreferences ADD COLUMN language VARCHAR DEFAULT 'zh-TW';",
        # FX Watch: 新增獨立切換開關與欄位重命名
        "ALTER TABLE fxwatchconfig ADD COLUMN alert_on_recent_high BOOLEAN DEFAULT 1;",
        "ALTER TABLE fxwatchconfig ADD COLUMN alert_on_consecutive_increase BOOLEAN DEFAULT 1;",
        "ALTER TABLE fxwatchconfig ADD COLUMN recent_high_days INTEGER DEFAULT 30;",
        "UPDATE fxwatchconfig SET recent_high_days = lookback_days WHERE recent_high_days = 30;",
        # Stock: 新增 is_etf 欄位（ETF 不參與市場情緒計算）
        "ALTER TABLE stock ADD COLUMN is_etf BOOLEAN DEFAULT 0;",
        # 回填已知 ETF
        "UPDATE stock SET is_etf = 1 WHERE ticker IN ('VTI', 'VT', 'SOXX');",
    ]

    with engine.connect() as conn:
        for sql in migrations:
            try:
                conn.execute(text(sql))
                conn.commit()
                logger.info("Migration 成功：%s", sql.strip())
            except Exception:
                # SQLite 會在欄位已存在時拋出 OperationalError，靜默跳過
                conn.rollback()


def _load_system_personas() -> None:
    """從 JSON 檔案載入系統預設投資人格範本（upsert）。"""
    import json
    import pathlib

    from domain.entities import SystemTemplate

    persona_path = (
        pathlib.Path(__file__).parent.parent / "config" / "system_personas.json"
    )
    if not persona_path.exists():
        logger.warning("system_personas.json 不存在，跳過載入。")
        return

    with open(persona_path, encoding="utf-8") as f:
        personas = json.load(f)

    with Session(engine) as session:
        for p in personas:
            existing = session.get(SystemTemplate, p["id"])
            if existing:
                existing.name = p["name"]
                existing.description = p["description"]
                existing.quote = p["quote"]
                existing.is_empty = p.get("isEmpty", False)
                existing.default_config = json.dumps(p["defaultConfig"])
            else:
                session.add(
                    SystemTemplate(
                        id=p["id"],
                        name=p["name"],
                        description=p["description"],
                        quote=p["quote"],
                        is_empty=p.get("isEmpty", False),
                        default_config=json.dumps(p["defaultConfig"]),
                    )
                )
        session.commit()
    logger.info("系統人格範本載入完成（%d 筆）。", len(personas))


def _encrypt_plaintext_tokens() -> None:
    """
    加密遷移：將 UserTelegramSettings.custom_bot_token 的明文改為加密存儲。

    僅在 FERNET_KEY 環境變數已設定時執行。已加密的 token 不會重複加密。
    """
    import os

    # Skip if FERNET_KEY not set (encryption not enabled)
    if not os.getenv("FERNET_KEY"):
        logger.debug("FERNET_KEY 未設定，跳過 Token 加密遷移。")
        return

    try:
        from domain.entities import UserTelegramSettings
        from infrastructure.crypto import encrypt_token, is_encrypted

        with Session(engine) as session:
            settings_list = session.query(UserTelegramSettings).all()
            encrypted_count = 0

            for settings in settings_list:
                if settings.custom_bot_token and not is_encrypted(
                    settings.custom_bot_token
                ):
                    # Token is plaintext, encrypt it
                    try:
                        encrypted = encrypt_token(settings.custom_bot_token)
                        settings.custom_bot_token = encrypted
                        encrypted_count += 1
                        logger.info("Token 加密完成：user_id=%s", settings.user_id)
                    except Exception as e:
                        logger.error(
                            "Token 加密失敗：user_id=%s, error=%s",
                            settings.user_id,
                            e,
                        )

            if encrypted_count > 0:
                session.commit()
                logger.info("Token 加密遷移完成：%d 筆。", encrypted_count)
            else:
                logger.debug("無需加密的明文 Token。")

    except Exception as e:
        logger.error("Token 加密遷移失敗：%s", e, exc_info=True)


def create_db_and_tables() -> None:
    """建立所有 SQLModel 定義的資料表（若不存在），並執行遷移與資料載入。"""
    # 確保所有 Entity 已被 import，SQLModel metadata 才會完整
    import domain.entities  # noqa: F401

    logger.info("建立資料表（若不存在）...")
    SQLModel.metadata.create_all(engine)
    logger.info("資料表就緒。")

    logger.info("執行資料庫遷移...")
    _run_migrations()
    logger.info("遷移完成。")

    logger.info("載入系統人格範本...")
    _load_system_personas()
    logger.info("人格範本就緒。")

    logger.info("執行 Token 加密遷移...")
    _encrypt_plaintext_tokens()
    logger.info("Token 加密遷移完成。")


def get_session() -> Generator[Session, None, None]:
    """FastAPI Dependency：提供一個 DB Session，結束後自動關閉。"""
    with Session(engine) as session:
        yield session
