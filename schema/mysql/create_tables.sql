-- qt2-server 基础表建表脚本
-- 包含建库 + 建表（future_info 和 trade_calendar）
--
-- 用法:
--   mysql -h 127.0.0.1 -P 21707 -u root -p < schema/mysql/create_tables.sql
--
-- 说明:
--   - future_info: 期货合约信息（通过 Tushare fut_basic 同步）
--   - trade_calendar: 交易日历（通过 Tushare trade_cal 同步）

-- ==========================================================
-- 0. 创建数据库
-- ==========================================================
CREATE DATABASE IF NOT EXISTS qt2
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_0900_ai_ci;

USE qt2;

-- ==========================================================
-- 1. 期货基础信息主表
-- ==========================================================
CREATE TABLE IF NOT EXISTS future_info (
  instrument_id varchar(10) NOT NULL COMMENT '合约代码, 如 IF2602',
  exchange_id enum('CFFEX','SHFE','DCE','CZCE','INE','GFEX') NOT NULL COMMENT '交易所',

  unique_symbol varchar(20) GENERATED ALWAYS AS (concat(instrument_id,'.',exchange_id)) STORED COMMENT '全局唯一标识',
  instrument_name varchar(50) NOT NULL COMMENT '合约名字',
  product_id varchar(10) NOT NULL COMMENT '品种代码, 如 IF, IC, SA',
  currency varchar(10) DEFAULT 'CNY' COMMENT '币种',
  settle_type varchar(10) DEFAULT 'PHYSICAL' COMMENT '交割方式: CASH=现金, PHYSICAL=实物',

  multiplier decimal(10,2) NOT NULL COMMENT '合约乘数',
  tick_size decimal(10,4) NOT NULL COMMENT '最小变动价位',
  has_night_session tinyint DEFAULT '0' COMMENT '0:无夜盘 1:有夜盘',
  max_limit_order_vol int DEFAULT '500' COMMENT '单笔最大报单手数',

  delivery_date date DEFAULT NULL COMMENT '交割日',
  delivery_month int DEFAULT NULL COMMENT '交割月份 (YYYYMM)',
  list_date date DEFAULT NULL COMMENT '上市日期',
  delist_date date DEFAULT NULL COMMENT '最后交易日',

  margin_rate decimal(6,4) DEFAULT '0.1200' COMMENT '保证金率',
  fee_type enum('RATIO', 'FIXED') DEFAULT 'RATIO' COMMENT '费率类型：按比例 vs 按固定金额/手',
  open_fee decimal(10,6) DEFAULT '0.000023' COMMENT '开仓费率',
  close_fee decimal(10,6) DEFAULT '0.000023' COMMENT '平仓费率 (平昨仓)',
  close_today_fee decimal(10,6) DEFAULT '0.00023' COMMENT '平今仓费率',

  status tinyint DEFAULT '1' COMMENT '1:正常 0:停止交易',
  created_at datetime DEFAULT CURRENT_TIMESTAMP,
  updated_at datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  PRIMARY KEY (instrument_id, exchange_id),
  KEY idx_product_status (product_id, status),
  KEY idx_delivery (delivery_month),
  KEY idx_symbol (unique_symbol)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='期货基础信息主表';


-- ==========================================================
-- 2. 交易日历表
-- ==========================================================
CREATE TABLE IF NOT EXISTS trade_calendar (
  exchange VARCHAR(10) NOT NULL COMMENT '交易所代码',
  trade_date DATE NOT NULL COMMENT '日历日期',
  is_open TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否交易日: 0=休市, 1=交易',
  prev_trade_date DATE NULL COMMENT '上一个交易日',

  PRIMARY KEY (exchange, trade_date),
  INDEX idx_trade_date (trade_date),
  INDEX idx_is_open (is_open),
  INDEX idx_prev_trade_date (prev_trade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='交易日历';
