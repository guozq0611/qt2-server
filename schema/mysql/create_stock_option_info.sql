-- qt2-server 股票期权基础信息表
-- 股票 ETF 期权（上交所 SSE / 深交所 SZSE），通过 CTP 股票期权柜台接收行情
--
-- 用法:
--   mysql -h 127.0.0.1 -P 21707 -u root -p xquant < schema/mysql/create_stock_option_info.sql
--
-- 说明:
--   - 数据来源: Tushare opt_basic 接口（exchange=SSE/SZSE）
--   - instrument_id: 可读合约代码（Tushare symbol 字段），如 510050C2603M02500
--   - ctp_code: CTP 股票期权柜台订阅用的数字 InstrumentID（Tushare ts_code 数字部分），如 10011031
--     注意：CTP 股票期权柜台只能用 ctp_code 订阅行情，不能用 instrument_id

USE xquant;

CREATE TABLE IF NOT EXISTS stock_option_info (
  instrument_id varchar(30) NOT NULL COMMENT '可读合约代码, 如 510050C2603M02500',
  ctp_code varchar(20) NOT NULL COMMENT 'CTP柜台订阅代码, 如 10011031 (Tushare ts_code 数字部分)',
  exchange_id enum('SSE','SZSE') NOT NULL COMMENT '交易所',

  instrument_name varchar(80) NOT NULL COMMENT '合约名称',
  underlying_symbol varchar(20) NOT NULL COMMENT '标的证券代码, 如 510050',
  contract_type char(1) NOT NULL COMMENT '期权类型: C=认购(看涨), P=认沽(看跌)',
  strike_price decimal(20,4) NOT NULL COMMENT '行权价',
  multiplier decimal(10,2) NOT NULL DEFAULT '10000' COMMENT '合约单位(乘数)',
  tick_size decimal(10,6) NOT NULL DEFAULT '0.0001' COMMENT '最小价格波幅',

  delivery_month int DEFAULT NULL COMMENT '交割月份 (YYYYMM)',
  expiry_date date DEFAULT NULL COMMENT '到期日',
  list_date date DEFAULT NULL COMMENT '上市日期',
  delist_date date DEFAULT NULL COMMENT '最后交易日',

  currency varchar(10) DEFAULT 'CNY' COMMENT '币种',
  status tinyint DEFAULT '1' COMMENT '1:正常 0:停止交易',
  created_at datetime DEFAULT CURRENT_TIMESTAMP,
  updated_at datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  PRIMARY KEY (instrument_id, exchange_id),
  UNIQUE KEY uk_ctp_code (ctp_code, exchange_id),
  INDEX idx_underlying (underlying_symbol),
  INDEX idx_product_status (contract_type, status),
  INDEX idx_expiry (expiry_date),
  INDEX idx_delist (delist_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='股票期权基础信息表';
