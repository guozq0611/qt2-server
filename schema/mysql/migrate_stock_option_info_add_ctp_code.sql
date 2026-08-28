-- 迁移: stock_option_info 表新增 ctp_code 字段
-- 用法:
--   mysql -h 127.0.0.1 -P 21707 -u root -p xquant < schema/mysql/migrate_stock_option_info_add_ctp_code.sql
--
-- 说明:
--   CTP 股票期权柜台使用数字格式的 InstrumentID（如 10011031）订阅行情，
--   而非可读的 instrument_id（如 588000C2609M01750）。
--   ctp_code 来源于 Tushare ts_code 的数字部分。

USE xquant;

-- 1. 新增 ctp_code 列（先允许 NULL，便于旧数据过渡）
ALTER TABLE stock_option_info
  ADD COLUMN ctp_code VARCHAR(20) NULL COMMENT 'CTP柜台订阅代码, 如 10011031 (Tushare ts_code 数字部分)'
  AFTER instrument_id;

-- 2. 新增唯一索引（ctp_code + exchange_id）
ALTER TABLE stock_option_info
  ADD UNIQUE KEY uk_ctp_code (ctp_code, exchange_id);

-- 注：旧数据需重新同步以填充 ctp_code（run_sync_data.py --stock-option-info）
